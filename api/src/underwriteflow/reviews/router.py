"""Authenticated human-review start and resume endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from langgraph.types import Command
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from underwriteflow.auth.dependencies import require_permission, require_role
from underwriteflow.auth.schemas import Permission, UserRole
from underwriteflow.database import get_session
from underwriteflow.persistence.models import (
    AuditEvent,
    Case,
    Document,
    ExtractedField,
    ProductVersion,
    Recommendation,
    Review,
    Submission,
)
from underwriteflow.products.rules import condition_matches
from underwriteflow.products.schemas import ProductConfiguration
from underwriteflow.reviews.schemas import ReviewCommand, ReviewResponse, ReviewStartResponse
from underwriteflow.workflow.checkpoint import postgres_checkpointer
from underwriteflow.workflow.product_subgraphs import build_product_subgraph
from underwriteflow.workflow.state import thread_config
from underwriteflow.workflow.triage import build_triage_graph

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


# Start the selected product and triage graphs for a persisted case.
@router.post("/{case_id}/start", response_model=ReviewStartResponse)
async def start_review(
    case_id: UUID,
    request: Request,
    operator: dict[str, str] = Depends(require_permission(Permission.REVIEW_WRITE)),
    session: AsyncSession = Depends(get_session),
) -> ReviewStartResponse:
    case = await session.scalar(select(Case).where(Case.id == case_id))
    submission = await session.scalar(select(Submission).where(Submission.case_id == case_id))
    if case is None or submission is None:
        raise HTTPException(status_code=404, detail="Case not found")
    if case.status != "new":
        raise HTTPException(status_code=409, detail="Case review is already complete or active")
    product_version = await session.scalar(
        select(ProductVersion).where(ProductVersion.id == case.product_version_id)
    )
    if product_version is None:
        raise HTTPException(status_code=409, detail="Case configuration is unavailable")
    configuration = ProductConfiguration.model_validate(product_version.configuration)
    documents = list(await session.scalars(select(Document).where(Document.case_id == case_id)))
    extracted_fields = list(
        await session.scalars(select(ExtractedField).where(ExtractedField.case_id == case_id))
    )
    application = submission.payload.get("application", {})
    required_documents = [
        document.code
        for document in configuration.documents
        if document.requirement == "required"
        or (
            document.requirement == "conditional"
            and condition_matches(document.condition or {}, application)
        )
    ]
    missing_information = required_documents[len(documents) :]
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
    conflicts = [
        {
            "field_name": field.field_name,
            "source_locator": field.source_locator,
            "conflict_status": field.conflict_status,
        }
        for field in extracted_fields
        if field.conflict_status != "clear"
    ]
    product_result = await build_product_subgraph(configuration).ainvoke(
        {
            "product_code": configuration.product_code,
            "payload": application,
            "rule_results": [],
        }
    )
    state = {
        "case_id": str(case_id),
        "evidence": evidence,
        "conflicts": conflicts,
        "missing_information": missing_information,
        "low_confidence": any(
            field.confidence is not None and field.confidence < 0.8
            for field in extracted_fields
        ),
        "validations": product_result.get("validations", []),
        "risk_signals": product_result.get("risk_signals", []),
    }
    config = thread_config(str(case_id))
    async with postgres_checkpointer(request.app.state.settings.database_url) as checkpointer:
        graph = build_triage_graph(checkpointer=checkpointer)
        if (await graph.aget_state(config)).next:
            raise HTTPException(status_code=409, detail="Case review has already started")
        result = await graph.ainvoke(state, config=config)
    case.status = "underwriter_review"
    session.add(
        AuditEvent(
            case_id=case_id,
            actor_user_id=UUID(operator["sub"]),
            event_type="workflow_started",
            details={
                "product_code": configuration.product_code,
                "product_version": product_version.version,
                "recommendation": result["recommendation"]["route"],
            },
        )
    )
    await session.commit()
    return ReviewStartResponse(
        case_id=case_id,
        status="awaiting_human_review",
        recommendation=result["recommendation"],
    )


# Resume only an underwriter's pending checkpoint and persist the decision once.
@router.post("/{case_id}", response_model=ReviewResponse)
async def resume_review(
    case_id: UUID,
    command: ReviewCommand,
    request: Request,
    reviewer: dict[str, str] = Depends(require_role(UserRole.UNDERWRITER.value)),
    session: AsyncSession = Depends(get_session),
) -> ReviewResponse:
    case = await session.scalar(select(Case).where(Case.id == case_id))
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")
    existing_review = await session.scalar(
        select(Review).where(Review.case_id == case_id).order_by(Review.created_at.desc())
    )
    if existing_review is not None:
        return review_response_for_record(case_id, existing_review, case.status)
    config = thread_config(str(case_id))
    async with postgres_checkpointer(request.app.state.settings.database_url) as checkpointer:
        graph = build_triage_graph(checkpointer=checkpointer)
        snapshot = await graph.aget_state(config)
        if "human_review" in snapshot.next:
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
        recommendation = snapshot.values.get("recommendation", {})
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
        case_id=case_id,
        reviewer_user_id=UUID(reviewer["sub"]),
        action=command_to_persist.action,
        selected_route=result.get("final_route"),
        override_reason=command_to_persist.reason,
    )
    session.add(review)
    session.add(
        AuditEvent(
            case_id=case_id,
            actor_user_id=UUID(reviewer["sub"]),
            event_type="underwriter_reviewed",
            details={
                "action": command_to_persist.action,
                "selected_route": result.get("final_route"),
                "status": result["review_status"],
                "reason": command_to_persist.reason,
            },
        )
    )
    case.status = result["review_status"]
    await session.commit()
    return review_response_for_record(case_id, review, result["review_status"])
