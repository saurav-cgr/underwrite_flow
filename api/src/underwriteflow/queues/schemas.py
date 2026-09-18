"""Typed queue, audit, and completion response contracts."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, model_validator

from underwriteflow.products.schemas import Route

FinalRoute = Literal["specialist", "standard", "expedited"]


class QueueItem(BaseModel):
    """Safe case summary for an operations queue."""

    case_id: UUID
    product_code: str
    status: str
    route: Route | None
    selected_route: FinalRoute | None = None
    specialist_label: str | None = None
    specialist: bool
    awaiting_handoff: bool = False
    reconciliation_status: str = ""
    discrepancy_count: int = 0
    missing_evidence_count: int = 0


class AuditEventResponse(BaseModel):
    """Immutable safe audit event view."""

    id: UUID
    case_id: UUID | None = None
    actor_user_id: UUID | None
    event_type: str
    details: dict
    occurred_at: datetime
    supersedes_event_id: UUID | None = None

    # Surface the replaced event so a chronology can link its own steps.
    @model_validator(mode="after")
    def read_supersession(self) -> "AuditEventResponse":
        recorded = (self.details or {}).get("supersedes_event_id")
        if recorded is not None:
            try:
                self.supersedes_event_id = UUID(str(recorded))
            except ValueError:
                self.supersedes_event_id = None
        return self


class CompletionResponse(BaseModel):
    """Idempotent confirmed-case completion result."""

    handoff_id: UUID
    case_id: UUID
    route: FinalRoute
    specialist_label: str | None = None
    status: Literal["completed"]
