"""Queue views, audit history, and confirmed-case completion."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from underwriteflow.auth.dependencies import require_permission, require_role
from underwriteflow.auth.schemas import Permission, UserRole
from underwriteflow.database import get_session
from underwriteflow.persistence.models import (
    AuditEvent,
    Case,
    Handoff,
    Product,
    ProductVersion,
    Recommendation,
    Review,
)
from underwriteflow.queues.schemas import AuditEventResponse, CompletionResponse, QueueItem

router = APIRouter(tags=["queues"])


# List safe queue summaries with optional status, product, and route filters.
@router.get("/queues", response_model=list[QueueItem])
async def list_queue(
    status: str | None = Query(default=None, max_length=50),
    product_code: str | None = Query(default=None, max_length=100),
    route: str | None = Query(default=None, max_length=50),
    specialist: bool | None = Query(default=None),
    _: dict[str, str] = Depends(require_permission(Permission.REVIEW_READ)),
    session: AsyncSession = Depends(get_session),
) -> list[QueueItem]:
    statement = (
        select(Case, Product, Recommendation)
        .join(ProductVersion, ProductVersion.id == Case.product_version_id)
        .join(Product, Product.id == ProductVersion.product_id)
        .outerjoin(Recommendation, Recommendation.case_id == Case.id)
        .order_by(Case.created_at.desc())
    )
    if status is not None:
        statement = statement.where(Case.status == status)
    if product_code is not None:
        statement = statement.where(Product.code == product_code)
    if route is not None:
        statement = statement.where(Recommendation.route == route)
    if specialist is True:
        statement = statement.where(Recommendation.route == "specialist")
    elif specialist is False:
        statement = statement.where(
            or_(Recommendation.route != "specialist", Recommendation.route.is_(None))
        )
    rows = (await session.execute(statement)).all()
    return [
        QueueItem(
            case_id=case.id,
            product_code=product.code,
            status=case.status,
            route=recommendation.route if recommendation else None,
            specialist=bool(recommendation and recommendation.route == "specialist"),
        )
        for case, product, recommendation in rows
    ]


# Return immutable audit events for an administrator without exposing raw payloads.
@router.get("/audit/cases/{case_id}", response_model=list[AuditEventResponse])
async def list_audit_events(
    case_id: UUID,
    _: dict[str, str] = Depends(require_permission(Permission.AUDIT_READ)),
    session: AsyncSession = Depends(get_session),
) -> list[AuditEventResponse]:
    events = await session.scalars(
        select(AuditEvent)
        .where(AuditEvent.case_id == case_id)
        .order_by(AuditEvent.occurred_at.asc(), AuditEvent.id.asc())
    )
    return [AuditEventResponse.model_validate(event, from_attributes=True) for event in events]


# Finalize one confirmed route exactly once with an atomic queue and audit handoff.
@router.post("/completion/{case_id}", response_model=CompletionResponse)
async def complete_case(
    case_id: UUID,
    operator: dict[str, str] = Depends(require_role(UserRole.UNDERWRITER.value)),
    session: AsyncSession = Depends(get_session),
) -> CompletionResponse:
    case = await session.scalar(select(Case).where(Case.id == case_id))
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")
    review = await session.scalar(
        select(Review)
        .where(Review.case_id == case_id)
        .order_by(Review.created_at.desc())
    )
    if (
        case.status not in {"confirmed", "overridden", "completed"}
        or review is None
        or review.selected_route not in {"specialist", "standard", "expedited"}
    ):
        raise HTTPException(status_code=409, detail="Case has no confirmed final route")
    idempotency_key = f"case-{case_id}-completion"
    existing = await session.scalar(
        select(Handoff).where(Handoff.idempotency_key == idempotency_key)
    )
    if existing is not None:
        return CompletionResponse(
            handoff_id=existing.id,
            case_id=case_id,
            route=existing.payload["route"],
            status="completed",
        )
    handoff = Handoff(
        case_id=case_id,
        idempotency_key=idempotency_key,
        status="completed",
        destination="completed_queue",
        payload={"case_id": str(case_id), "route": review.selected_route},
    )
    session.add(handoff)
    case.status = "completed"
    session.add(
        AuditEvent(
            case_id=case_id,
            actor_user_id=UUID(operator["sub"]),
            event_type="case_completed",
            details={"route": review.selected_route, "destination": "completed_queue"},
        )
    )
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        existing = await session.scalar(
            select(Handoff).where(Handoff.idempotency_key == idempotency_key)
        )
        if existing is None:
            raise
        return CompletionResponse(
            handoff_id=existing.id,
            case_id=case_id,
            route=existing.payload["route"],
            status="completed",
        )
    return CompletionResponse(
        handoff_id=handoff.id,
        case_id=case_id,
        route=review.selected_route,
        status="completed",
    )
