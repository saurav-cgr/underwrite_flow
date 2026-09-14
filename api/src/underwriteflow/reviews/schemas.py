"""Typed human review command and response contracts."""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

ReviewAction = Literal["confirm", "override", "request_information"]
FinalRoute = Literal["specialist", "standard", "expedited"]


class ReviewCommand(BaseModel):
    """Authenticated underwriter action submitted at the review interrupt."""

    action: ReviewAction
    selected_route: FinalRoute | None = None
    reason: str | None = Field(default=None, max_length=2_000)

    # Require route and reason only for actions that need an explanation.
    @model_validator(mode="after")
    def validate_action(self) -> "ReviewCommand":
        if self.action == "override" and (self.selected_route is None or not self.reason):
            raise ValueError("override route and reason are required")
        if self.action == "request_information" and not self.reason:
            raise ValueError("information request reason is required")
        return self


class ReviewResponse(BaseModel):
    """Safe result of a human review command."""

    case_id: UUID
    action: ReviewAction
    selected_route: FinalRoute | None
    status: Literal["confirmed", "overridden", "needs_information", "manual_review"]


class ReviewStartResponse(BaseModel):
    """Recommendation exposed while a case awaits human review."""

    case_id: UUID
    status: Literal["awaiting_human_review"]
    recommendation: dict[str, object]
