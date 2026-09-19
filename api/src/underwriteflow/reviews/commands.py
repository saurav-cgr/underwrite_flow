"""Pure review-command validation and idempotent-record helpers.

Split out of ``router.py`` to keep that file under the project's 400-line
limit; these functions hold no session or request state.
"""

from uuid import UUID

from fastapi import HTTPException

from underwriteflow.persistence.models import Review
from underwriteflow.products.schemas import ProductConfiguration
from underwriteflow.reviews.evidence import FALLBACK_SPECIALIST_LABEL
from underwriteflow.reviews.schemas import ReviewCommand, ReviewResponse
from underwriteflow.workflow.triage import resolve_final_route


# Reconstruct the public response from an idempotent persisted review record.
def review_response_for_record(
    case_id: UUID,
    review: Review,
    journey: str,
    status: str | None = None,
) -> ReviewResponse:
    completed_statuses = {
        "confirmed",
        "overridden",
        "needs_information",
        "manual_review",
    }
    if status in completed_statuses:
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
        journey=journey,
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
    allowed_labels = (
        configuration.specialist_labels
        if configuration is not None
        else [FALLBACK_SPECIALIST_LABEL]
    )
    if command.specialist_label not in allowed_labels:
        raise HTTPException(
            status_code=422,
            detail="Specialist label is not configured for this product",
        )


# Repair only invalid specialist metadata from a completed legacy checkpoint.
def recover_review_command(
    stored: ReviewCommand,
    retry: ReviewCommand,
    recommended_route: str | None,
    configuration: ProductConfiguration | None,
) -> ReviewCommand:
    try:
        require_specialist_label(
            stored,
            recommended_route,
            configuration,
        )
        return stored
    except HTTPException:
        repaired = ReviewCommand.model_validate(
            {
                **stored.model_dump(),
                "specialist_label": retry.specialist_label,
            }
        )
        require_specialist_label(
            repaired,
            recommended_route,
            configuration,
        )
        return repaired
