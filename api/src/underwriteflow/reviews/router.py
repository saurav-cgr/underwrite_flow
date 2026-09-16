"""Authenticated human-review start and resume endpoints."""

from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from langgraph.types import Command
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from underwriteflow.audit.events import build_audit_event
from underwriteflow.auth.dependencies import require_permission, require_role
from underwriteflow.auth.schemas import Permission, UserRole
from underwriteflow.cases.service import missing_document_codes
from underwriteflow.database import get_session
from underwriteflow.persistence.models import (
    Case,
    Document,
    ExtractedField,
    ProductVersion,
    Recommendation,
    Review,
    Submission,
    Validation,
)
from underwriteflow.products.schemas import ProductConfiguration
from underwriteflow.reviews.schemas import ReviewCommand, ReviewResponse, ReviewStartResponse
from underwriteflow.workflow.checkpoint import postgres_checkpointer
from underwriteflow.workflow.state import thread_config
from underwriteflow.workflow.triage import (
    build_triage_graph,
    resolve_final_route,
)

router = APIRouter(prefix="/reviews", tags=["reviews"])


# Reconstruct the public response from an idempotent persisted review record.
def review_response_for_record(
    case_id: UUID, review: Review, status: str | None = None
) -> ReviewResponse:
    if status in {"confirmed", "overridden", "needs_information", "manual_review"}:
        review_status = status
    elif review.action == "request_information":
        review_status = "needs_information"
    elif review.selected_route is None:
        review_status = "manual_review"
    elif review.action == "override":
        review_status = "overridden"
    else:
        review_status = "confirmed"
    return ReviewResponse(
        case_id=case_id,
        action=review.action,
        selected_route=review.selected_route,
        status=review_status,
    )


# Require a configured specialist label when the resolved route is specialist.
def require_specialist_label(
    command: ReviewCommand,
    recommended_route: str | None,
    configuration: ProductConfiguration | None,
) -> None:
    route, _ = resolve_final_route(command, recommended_route)
    if route != "specialist":
        return
    if not command.specialist_label:
        raise HTTPException(
            status_code=422,
            detail="A specialist label is required for specialist review",
        )
    if (
        configuration is not None
        and command.specialist_label not in configuration.specialist_labels
    ):
        raise HTTPException(
            status_code=422,
            detail="Specialist label is not configured for this product",
        )


# Return the persisted pending review without starting any workflow work.
@router.post("/{case_id}/start", response_model=ReviewStartResponse)
async def start_review(
    case_id: UUID,
    operator: dict[str, str] = Depends(require_permission(Permission.REVIEW_WRITE)),
    session: AsyncSession = Depends(get_session),
) -> ReviewStartResponse:
    case = await session.scalar(select(Case).where(Case.id == case_id))
    submission = await session.scalar(
        select(Submission).where(Submission.case_id == case_id)
    )
    if case is None or submission is None:
        raise HTTPException(status_code=404, detail="Case not found")
    if case.status != "underwriter_review":
        raise HTTPException(
            status_code=409,
            detail="Case is not awaiting human review",
        )
    recommendation = await session.scalar(
        select(Recommendation).where(Recommendation.case_id == case_id)
    )
    product_version = await session.scalar(
        select(ProductVersion).where(
            ProductVersion.id == case.product_version_id
        )
    )
    if recommendation is None or product_version is None:
        raise HTTPException(
            status_code=409,
            detail="Case recommendation is unavailable",
        )
    try:
        configuration = ProductConfiguration.model_validate(
            product_version.configuration
        )
    except ValidationError:
        # An unreadable pinned configuration still opens for human review
        # with no derived requirements and no selectable specialist labels.
        configuration = None
    documents = list(
        await session.scalars(
            select(Document).where(Document.case_id == case_id)
        )
    )
    extracted_fields = list(
        await session.scalars(
            select(ExtractedField).where(ExtractedField.case_id == case_id)
        )
    )
    failures = list(
        await session.scalars(
            select(Validation).where(
                Validation.case_id == case_id,
                Validation.status == "error",
            )
        )
    )
    summary = dict(recommendation.summary or {})
    application = submission.payload.get("application", {})
    evidence = [
        {
            "document_id": str(document.id),
            "filename": document.filename,
            "source_locator": document.storage_key,
            "source_type": "submitted_document",
        }
        for document in documents
    ]
    evidence.extend(
        {
            "document_id": str(field.document_id) if field.document_id else None,
            "field_name": field.field_name,
            "value": field.value,
            "source_locator": field.source_locator,
            "source_type": "extracted_field",
        }
        for field in extracted_fields
    )
    return ReviewStartResponse(
        case_id=case_id,
        status="awaiting_human_review",
        recommendation=summary.get(
            "recommendation",
            # A recommendation row can outlive the summary that produced it,
            # so the served shape stays the same on every path.
            {"route": recommendation.route, "factors": []},
        ),
        summary=summary.get("summary", {}),
        evidence=evidence,
        conflicts=[
            {
                "field_name": field.field_name,
                "value": field.value,
                "document_id": (
                    str(field.document_id) if field.document_id else None
                ),
                "source_locator": field.source_locator,
                "conflict_status": field.conflict_status,
            }
            for field in extracted_fields
            if field.conflict_status != "clear"
        ],
        missing_information=(
            []
            if configuration is None
            else missing_document_codes(
                configuration,
                [
                    document.document_code
                    for document in documents
                    if document.document_code
                ],
                application,
            )
        ),
        extraction_failures=[
            {"rule_code": failure.rule_code, "details": failure.details}
            for failure in failures
        ],
        specialist_options=(
            []
            if configuration is None
            else list(configuration.specialist_labels)
        ),
    )


# Resume one pending checkpoint per case and cycle, and persist it once.
@router.post("/{case_id}", response_model=ReviewResponse)
async def resume_review(
    case_id: UUID,
    command: ReviewCommand,
    request: Request,
    reviewer: dict[str, str] = Depends(require_role(UserRole.UNDERWRITER.value)),
    session: AsyncSession = Depends(get_session),
) -> ReviewResponse:
    # Lock the case row so a second decision waits instead of resuming the
    # same checkpoint concurrently with a different command.
    case = await session.scalar(
        select(Case).where(Case.id == case_id).with_for_update()
    )
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")
    existing_review = await session.scalar(
        select(Review).where(
            Review.case_id == case_id,
            Review.review_cycle == case.review_cycle,
        )
    )
    if existing_review is not None:
        return review_response_for_record(case_id, existing_review, case.status)
    product_version = await session.scalar(
        select(ProductVersion).where(
            ProductVersion.id == case.product_version_id
        )
    )
    if product_version is None:
        raise HTTPException(
            status_code=409,
            detail="Case configuration is unavailable",
        )
    try:
        configuration = ProductConfiguration.model_validate(
            product_version.configuration
        )
    except ValidationError:
        # Without a readable configuration the label vocabulary is unknown, so
        # only the presence of a label can be enforced.
        configuration = None
    config = thread_config(str(case_id), case.review_cycle)
    async with postgres_checkpointer(request.app.state.settings.database_url) as checkpointer:
        graph = build_triage_graph(checkpointer=checkpointer)
        snapshot = await graph.aget_state(config)
        recommendation = snapshot.values.get("recommendation", {})
        if "human_review" in snapshot.next:
            if (
                command.action == "override"
                and command.selected_route == recommendation.get("route")
            ):
                raise HTTPException(
                    status_code=422,
                    detail="Override must change the recommended route",
                )
            require_specialist_label(
                command, recommendation.get("route"), configuration
            )
            command_to_persist = command
            result = await graph.ainvoke(
                Command(resume=command.model_dump(exclude_none=True)), config=config
            )
        elif "review_command" in snapshot.values:
            command_to_persist = ReviewCommand.model_validate(snapshot.values["review_command"])
            result = {
                "final_route": snapshot.values.get("final_route"),
                "review_status": snapshot.values.get("review_status"),
            }
        else:
            raise HTTPException(status_code=409, detail="Case is not awaiting human review")
        if await session.scalar(
            select(Recommendation).where(Recommendation.case_id == case_id)
        ) is None:
            session.add(
                Recommendation(
                    case_id=case_id,
                    route=recommendation.get("route"),
                    status="pending_human_review",
                    summary=snapshot.values.get("summary", {}),
                    workflow_version="triage-v1",
                )
            )
    review = Review(
        id=uuid4(),
        case_id=case_id,
        reviewer_user_id=UUID(reviewer["sub"]),
        review_cycle=case.review_cycle,
        action=command_to_persist.action,
        selected_route=result.get("final_route"),
        specialist_label=command_to_persist.specialist_label,
        override_reason=command_to_persist.reason,
    )
    session.add(review)
    session.add(
        build_audit_event(
            "underwriter_reviewed",
            {
                "review_id": review.id,
                "review_cycle": case.review_cycle,
                "action": command_to_persist.action,
                "recommended_route": recommendation.get("route"),
                "selected_route": result.get("final_route"),
                "specialist_label": command_to_persist.specialist_label,
                "status": result["review_status"],
                "reason": command_to_persist.reason,
            },
            case_id=case_id,
            actor_user_id=UUID(reviewer["sub"]),
        )
    )
    case.status = result["review_status"]
    await session.commit()
    return review_response_for_record(case_id, review, result["review_status"])
