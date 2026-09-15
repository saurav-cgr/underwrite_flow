"""Typed human review command and response contracts."""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

ReviewAction = Literal["confirm", "override", "request_information"]
FinalRoute = Literal["specialist", "standard", "expedited"]


class ReviewCommand(BaseModel):
    """Authenticated underwriter action submitted at the review interrupt."""

    action: ReviewAction
    selected_route: FinalRoute | None = None
    specialist_label: str | None = Field(default=None, max_length=200)
    reason: str | None = Field(default=None, max_length=2_000)
    evidence_acknowledged: bool = False

    # Trim a reason and treat whitespace-only text as missing.
    @field_validator("reason")
    @classmethod
    def trim_reason(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None

    # Require acknowledgement and every field the chosen action depends on.
    @model_validator(mode="after")
    def validate_action(self) -> "ReviewCommand":
        if not self.evidence_acknowledged:
            raise ValueError("evidence acknowledgement is required")
        if self.action == "override":
            if self.selected_route is None:
                raise ValueError("override route is required")
            if not self.reason:
                raise ValueError("override reason is required")
        if self.action == "request_information" and not self.reason:
            raise ValueError("information request reason is required")
        if self.selected_route == "specialist" and not self.specialist_label:
            raise ValueError("specialist label is required")
        return self


class ReviewResponse(BaseModel):
    """Safe result of a human review command."""

    case_id: UUID
    action: ReviewAction
    selected_route: FinalRoute | None
    status: Literal["confirmed", "overridden", "needs_information", "manual_review"]


class ReviewStartResponse(BaseModel):
    """Persisted human-review view for one case awaiting a decision."""

    case_id: UUID
    status: Literal["awaiting_human_review"]
    recommendation: dict[str, object]
    summary: dict[str, object]
    evidence: list[dict[str, object]]
    conflicts: list[dict[str, object]]
    missing_information: list[str]
    extraction_failures: list[dict[str, object]]
    specialist_options: list[str]
