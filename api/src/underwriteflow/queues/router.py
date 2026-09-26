"""Queue views, audit history, and confirmed-case completion."""

from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from underwriteflow.audit.events import build_audit_event
from underwriteflow.auth.dependencies import (
    require_permission,
    require_underwriter,
)
from underwriteflow.auth.schemas import Permission
from underwriteflow.database import get_session
from underwriteflow.persistence.models import (
    AuditEvent,
    Case,
    Handoff,
    Product,
    ProductVersion,
    Recommendation,
    Review,
    Validation,
)
from underwriteflow.queues.schemas import (
    AuditEventResponse,
    CompletionResponse,
    QueueItem,
)
from underwriteflow.workflow.reconciliation import check_applies

queues_router = APIRouter(prefix="/queues", tags=["queues"])
audit_router = APIRouter(prefix="/audit", tags=["audit"])
completion_router = APIRouter(prefix="/completion", tags=["completion"])


# List safe queue summaries with optional status, product, and route filters.
@queues_router.get("", response_model=list[QueueItem])
async def list_queue(
    status: str | None = Query(default=None, max_length=50),
    product_code: str | None = Query(default=None, max_length=100),
    journey: str | None = Query(default=None, max_length=50),
    route: str | None = Query(default=None, max_length=50),
    specialist: bool | None = Query(default=None),
    awaiting_handoff: bool | None = Query(default=None),
    reconciliation_status: str | None = Query(default=None, max_length=50),
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
    if journey is not None:
        statement = statement.where(Case.journey_type == journey)
    if route is not None:
        statement = statement.where(Recommendation.route == route)
    if specialist is True:
        statement = statement.where(Recommendation.route == "specialist")
    elif specialist is False:
        statement = statement.where(
            or_(
                Recommendation.route != "specialist",
                Recommendation.route.is_(None),
            )
        )
    if awaiting_handoff is True:
        statement = statement.where(
            Case.status.in_(("confirmed", "overridden"))
        )
    rows = (await session.execute(statement)).all()
    case_ids = [case.id for case, _product, _recommendation in rows]
    reviews = await latest_reviews(session, case_ids)
    handoffs = await completed_case_ids(session, case_ids)
    checks = await reconciliation_counts(session, case_ids)
    items = [
        QueueItem(
            case_id=case.id,
            product_code=product.code,
            journey=case.journey_type,
            status=case.status,
            route=recommendation.route if recommendation else None,
            selected_route=final_route_for(review),
            specialist_label=review.specialist_label if review else None,
            specialist=bool(
                recommendation and recommendation.route == "specialist"
            ),
            awaiting_handoff=(
                case.status in {"confirmed", "overridden"}
                and case.id not in handoffs
            ),
            reconciliation_status=checks.get(case.id, ("", 0, 0))[0],
            discrepancy_count=checks.get(case.id, ("", 0, 0))[1],
            missing_evidence_count=checks.get(case.id, ("", 0, 0))[2],
        )
        for case, product, recommendation in rows
        for review in [reviews.get(case.id)]
    ]
    if awaiting_handoff is True:
        return [item for item in items if item.awaiting_handoff]
    if reconciliation_status is not None:
        return [
            item
            for item in items
            if item.reconciliation_status == reconciliation_status
        ]
    return items


# Summarize each case's configured check status, discrepancies, and gaps.
async def reconciliation_counts(
    session: AsyncSession, case_ids: list[UUID]
) -> dict[UUID, tuple[str, int, int]]:
    if not case_ids:
        return {}
    rows = await session.execute(
        select(Validation.case_id, Validation.status, Validation.details).where(
            Validation.case_id.in_(case_ids),
            Validation.rule_code.like("reconciliation:%"),
        )
    )
    grouped: dict[UUID, list[str]] = {}
    for case_id, status, details in rows.all():
        # A claim the applicant never made needs no verification.
        if not check_applies(dict(details or {})):
            continue
        grouped.setdefault(case_id, []).append(str(status))
    # Most cautious status wins, matching the pure reconciliation precedence.
    precedence = (
        "missing_evidence",
        "flagged_discrepancy",
        "cleared",
    )
    return {
        case_id: (
            next(
                (
                    status.upper()
                    for status in precedence
                    if status in statuses
                ),
                "",
            ),
            statuses.count("flagged_discrepancy"),
            statuses.count("missing_evidence"),
        )
        for case_id, statuses in grouped.items()
    }


# Return the latest persisted review for each requested case.
async def latest_reviews(
    session: AsyncSession, case_ids: list[UUID]
) -> dict[UUID, Review]:
    if not case_ids:
        return {}
    reviews: dict[UUID, Review] = {}
    for review in await session.scalars(
        select(Review)
        .where(Review.case_id.in_(case_ids))
        .order_by(Review.created_at.asc())
    ):
        reviews[review.case_id] = review
    return reviews


# Return the case ids that already have a completion handoff.
async def completed_case_ids(
    session: AsyncSession, case_ids: list[UUID]
) -> set[UUID]:
    if not case_ids:
        return set()
    return set(
        await session.scalars(
            select(Handoff.case_id).where(Handoff.case_id.in_(case_ids))
        )
    )


# Report a stored route only when it is one of the three final PRD routes.
def final_route_for(review: Review | None) -> str | None:
    if review is None:
        return None
    if review.selected_route in {"specialist", "standard", "expedited"}:
        return review.selected_route
    return None


# Return immutable audit events for an administrator without raw payloads.
@audit_router.get("/cases/{case_id}", response_model=list[AuditEventResponse])
async def list_audit_events(
    case_id: UUID,
    event_type: str | None = Query(default=None, max_length=200),
    limit: int | None = Query(default=None, ge=1, le=500),
    _: dict[str, str] = Depends(require_permission(Permission.AUDIT_READ)),
    session: AsyncSession = Depends(get_session),
) -> list[AuditEventResponse]:
    statement = (
        select(AuditEvent)
        .where(AuditEvent.case_id == case_id)
        .order_by(AuditEvent.occurred_at.asc(), AuditEvent.id.asc())
    )
    if event_type is not None:
        statement = statement.where(AuditEvent.event_type == event_type)
    if limit is not None:
        statement = statement.limit(limit)
    events = await session.scalars(statement)
    return [
        AuditEventResponse.model_validate(event, from_attributes=True)
        for event in events
    ]


# Finalize one confirmed route with an atomic queue and audit handoff.
@completion_router.post("/{case_id}", response_model=CompletionResponse)
async def complete_case(
    case_id: UUID,
    operator: dict[str, str] = Depends(require_underwriter()),
    _: dict[str, str] = Depends(require_permission(Permission.CASES_OVERRIDE)),
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
        raise HTTPException(
            status_code=409,
            detail="Case has no confirmed final route",
        )
    idempotency_key = f"case-{case_id}-completion"
    existing = await session.scalar(
        select(Handoff).where(Handoff.idempotency_key == idempotency_key)
    )
    if existing is not None:
        return CompletionResponse(
            handoff_id=existing.id,
            case_id=case_id,
            journey=case.journey_type,
            route=existing.payload["route"],
            specialist_label=existing.payload.get("specialist_label"),
            status="completed",
        )
    handoff = Handoff(
        id=uuid4(),
        case_id=case_id,
        idempotency_key=idempotency_key,
        status="completed",
        destination="completed_queue",
        payload={
            "case_id": str(case_id),
            "journey": case.journey_type,
            "route": review.selected_route,
            "specialist_label": review.specialist_label,
        },
    )
    session.add(handoff)
    case.status = "completed"
    session.add(
        build_audit_event(
            "case_completed",
            {
                "handoff_id": handoff.id,
                "destination": handoff.destination,
                "idempotency_key": handoff.idempotency_key,
                "journey": case.journey_type,
                "route": review.selected_route,
                "specialist_label": review.specialist_label,
                "review_id": review.id,
                "review_cycle": review.review_cycle,
                "reviewed_at": review.reviewed_at,
                "case_status": case.status,
            },
            case_id=case_id,
            actor_user_id=UUID(operator["sub"]),
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
            journey=case.journey_type,
            route=existing.payload["route"],
            specialist_label=existing.payload.get("specialist_label"),
            status="completed",
        )
    return CompletionResponse(
        handoff_id=handoff.id,
        case_id=case_id,
        journey=case.journey_type,
        route=review.selected_route,
        specialist_label=review.specialist_label,
        status="completed",
    )
