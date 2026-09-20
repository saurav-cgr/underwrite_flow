"""Authenticated human-review start and resume endpoints."""

from pathlib import Path
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from langgraph.types import Command
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from underwriteflow.audit.events import build_audit_event, supersedes_details
from underwriteflow.auth.dependencies import (
    require_permission,
    require_underwriter,
)
from underwriteflow.auth.schemas import Permission
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
from underwriteflow.persistence.repositories import AuditRepository
from underwriteflow.products.schemas import (
    ProductConfiguration,
    filter_configuration_for_journey,
)
from underwriteflow.reviews.commands import (
    recover_review_command,
    require_specialist_label,
    review_response_for_record,
)
from underwriteflow.reviews.evidence import (
    FALLBACK_SPECIALIST_LABEL,
    build_review_start_response,
)
from underwriteflow.reviews.schemas import (
    ReviewCommand,
    ReviewResponse,
    ReviewStartResponse,
)
from underwriteflow.storage import StorageValidationError, UploadStorage
from underwriteflow.workflow.checkpoint import postgres_checkpointer
from underwriteflow.workflow.state import thread_config
from underwriteflow.workflow.triage import build_triage_graph

# Specialist-label helpers moved to commands.py; re-exported for callers
# that historically imported them from this module.
__all__ = [
    "router",
    "FALLBACK_SPECIALIST_LABEL",
    "recover_review_command",
    "require_specialist_label",
    "review_response_for_record",
]

router = APIRouter(prefix="/reviews", tags=["reviews"])


# Return the persisted pending review without starting any workflow work.
@router.post("/{case_id}/start", response_model=ReviewStartResponse)
async def start_review(
    case_id: UUID,
    operator: dict[str, str] = Depends(
        require_permission(Permission.REVIEW_WRITE)
    ),
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
        # The review view shows only what this case's journey asks for, so a
        # renewal-only field can never appear on a new-business review.
        configuration = filter_configuration_for_journey(
            ProductConfiguration.model_validate(
                product_version.configuration
            ),
            case.journey_type,
        )
    except (ValidationError, ValueError):
        # An unreadable or journey-inapplicable pinned configuration still
        # opens for human review with no derived requirements.
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
    stored_application = submission.payload.get("application", {})
    application = (
        stored_application if isinstance(stored_application, dict) else {}
    )
    reconciliation = list(
        await session.scalars(
            select(Validation)
            .where(
                Validation.case_id == case_id,
                Validation.rule_code.like("reconciliation:%"),
            )
            .order_by(Validation.rule_code)
        )
    )
    return build_review_start_response(
        case_id,
        recommendation,
        application,
        documents,
        extracted_fields,
        failures,
        configuration,
        reconciliation,
        journey=case.journey_type,
    )


# Serve one case-scoped upload only to an authenticated underwriter.
@router.get("/{case_id}/documents/{document_id}")
async def read_review_document(
    case_id: UUID,
    document_id: UUID,
    request: Request,
    reviewer: dict[str, str] = Depends(require_underwriter()),
    _: dict[str, str] = Depends(require_permission(Permission.REVIEW_READ)),
    session: AsyncSession = Depends(get_session),
) -> FileResponse:
    del reviewer
    document = await session.scalar(
        select(Document).where(
            Document.id == document_id,
            Document.case_id == case_id,
        )
    )
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    try:
        path = UploadStorage(
            Path(request.app.state.settings.upload_root)
        ).read_path(document.storage_key)
    except (OSError, StorageValidationError):
        raise HTTPException(
            status_code=404,
            detail="Document not found",
        ) from None
    return FileResponse(
        path,
        media_type=document.content_type,
        filename=document.filename,
        content_disposition_type="inline",
        headers={
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


# Resume one pending checkpoint per case and cycle, and persist it once.
@router.post("/{case_id}", response_model=ReviewResponse)
async def resume_review(
    case_id: UUID,
    command: ReviewCommand,
    request: Request,
    reviewer: dict[str, str] = Depends(require_underwriter()),
    _: dict[str, str] = Depends(
        require_permission(Permission.CASES_OVERRIDE)
    ),
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
        return review_response_for_record(
            case_id, existing_review, case.journey_type, case.status
        )
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
        # Without a readable configuration the label vocabulary is unknown,
        # so only the presence of a label can be enforced.
        configuration = None
    config = thread_config(str(case_id), case.review_cycle)
    async with postgres_checkpointer(
        request.app.state.settings.database_url
    ) as checkpointer:
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
                Command(resume=command.model_dump(exclude_none=True)),
                config=config,
            )
        elif "review_command" in snapshot.values:
            command_to_persist = recover_review_command(
                ReviewCommand.model_validate(
                    snapshot.values["review_command"]
                ),
                command,
                recommendation.get("route"),
                configuration,
            )
            result = {
                "final_route": snapshot.values.get("final_route"),
                "review_status": snapshot.values.get("review_status"),
            }
        else:
            raise HTTPException(
                status_code=409,
                detail="Case is not awaiting human review",
            )
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
    superseded = await AuditRepository().latest_event_id(
        session, ("underwriter_reviewed",), case_id=case_id
    )
    session.add(
        build_audit_event(
            "underwriter_reviewed",
            {
                "review_id": review.id,
                "review_cycle": case.review_cycle,
                "journey": case.journey_type,
                "action": command_to_persist.action,
                "recommended_route": recommendation.get("route"),
                "selected_route": result.get("final_route"),
                "specialist_label": command_to_persist.specialist_label,
                "status": result["review_status"],
                "reason": command_to_persist.reason,
                **supersedes_details(superseded),
            },
            case_id=case_id,
            actor_user_id=UUID(reviewer["sub"]),
        )
    )
    case.status = result["review_status"]
    await session.commit()
    return review_response_for_record(
        case_id, review, case.journey_type, result["review_status"]
    )
