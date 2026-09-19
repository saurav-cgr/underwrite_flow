"""Small persistence repositories with explicit audit-only append behavior."""

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from underwriteflow.persistence.models import AuditEvent


class AuditRepository:
    """Append business audit events without update or delete operations."""

    # Add one immutable business event to the current transaction.
    def append(self, session: AsyncSession, event: AuditEvent) -> None:
        session.add(event)

    # Return the newest recorded event that a new event of these types replaces.
    async def latest_event_id(
        self,
        session: AsyncSession,
        event_types: Sequence[str],
        *,
        case_id: UUID | None = None,
        product_code: str | None = None,
    ) -> UUID | None:
        statement = (
            select(AuditEvent.id)
            .where(AuditEvent.event_type.in_(tuple(event_types)))
            .order_by(AuditEvent.occurred_at.desc(), AuditEvent.id.desc())
            .limit(1)
        )
        if case_id is not None:
            statement = statement.where(AuditEvent.case_id == case_id)
        if product_code is not None:
            statement = statement.where(
                AuditEvent.details["product_code"].astext == product_code
            )
        return await session.scalar(statement)
