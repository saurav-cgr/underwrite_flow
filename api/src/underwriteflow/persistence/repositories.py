"""Small persistence repositories with explicit audit-only append behavior."""

from sqlalchemy.ext.asyncio import AsyncSession

from underwriteflow.persistence.models import AuditEvent


class AuditRepository:
    """Append business audit events without update or delete operations."""

    # Add one immutable business event to the current transaction.
    def append(self, session: AsyncSession, event: AuditEvent) -> None:
        session.add(event)
