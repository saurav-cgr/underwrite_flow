"""Narrow authentication, authorization, and administration queries.

Every query the auth and administration paths need lives here, so the service
and dependency layers stay free of SQL and each statement is easy to review.
"""

from collections.abc import Iterable, Sequence
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from underwriteflow.persistence.models import (
    Permission,
    RefreshSession,
    Role,
    RolePermission,
    User,
    UserRoleMapping,
)


# Load one user by its already-normalized email, active or not.
async def find_user_by_email(
    session: AsyncSession, email: str
) -> User | None:
    return await session.scalar(
        select(User).where(User.email == email)
    )


# Load one active user by its already-normalized email.
async def find_active_user_by_email(
    session: AsyncSession, email: str
) -> User | None:
    return await session.scalar(
        select(User).where(User.email == email, User.is_active.is_(True))
    )


# Load one user by identifier, regardless of active state.
async def find_user(
    session: AsyncSession, user_id: UUID
) -> User | None:
    return await session.scalar(select(User).where(User.id == user_id))


# Load one role by its stable code.
async def find_role_by_code(
    session: AsyncSession, code: str
) -> Role | None:
    return await session.scalar(select(Role).where(Role.code == code))


# Load one role by identifier.
async def find_role(
    session: AsyncSession, role_id: UUID
) -> Role | None:
    return await session.scalar(select(Role).where(Role.id == role_id))


# Load the role currently mapped to one user, if any.
async def find_user_role(
    session: AsyncSession, user_id: UUID
) -> Role | None:
    return await session.scalar(
        select(Role)
        .join(UserRoleMapping, UserRoleMapping.role_id == Role.id)
        .where(UserRoleMapping.user_id == user_id)
    )


# Load the role and scope codes currently granted to one user.
async def find_user_role_and_scopes(
    session: AsyncSession, user_id: UUID
) -> tuple[Role, tuple[str, ...]] | None:
    role = await find_user_role(session, user_id)
    if role is None:
        return None
    return role, await list_role_scopes(session, role.id)


# List the permission scope codes one role grants, in code order.
async def list_role_scopes(
    session: AsyncSession, role_id: UUID
) -> tuple[str, ...]:
    codes = await session.scalars(
        select(Permission.code)
        .join(
            RolePermission,
            RolePermission.permission_id == Permission.id,
        )
        .where(RolePermission.role_id == role_id)
    )
    return tuple(sorted(codes.all()))


# List every configured role in code order.
async def list_roles(session: AsyncSession) -> list[Role]:
    return list(
        (await session.scalars(select(Role).order_by(Role.code))).all()
    )


# List the fixed permission catalogue in code order.
async def list_permissions(session: AsyncSession) -> list[Permission]:
    return list(
        (
            await session.scalars(
                select(Permission).order_by(Permission.code)
            )
        ).all()
    )


# Load the permission records matching the supplied scope codes.
async def find_permissions_by_codes(
    session: AsyncSession, codes: Sequence[str]
) -> list[Permission]:
    if not codes:
        return []
    found = await session.scalars(
        select(Permission).where(Permission.code.in_(list(codes)))
    )
    return list(found.all())


# List users with their mapped role, filtered and paged by email.
async def list_users(
    session: AsyncSession,
    status: str | None,
    limit: int,
    cursor: str | None,
) -> list[tuple[User, Role | None]]:
    statement = (
        select(User, Role)
        .outerjoin(UserRoleMapping, UserRoleMapping.user_id == User.id)
        .outerjoin(Role, Role.id == UserRoleMapping.role_id)
        .order_by(User.email)
        .limit(limit)
    )
    if status == "active":
        statement = statement.where(User.is_active.is_(True))
    elif status == "inactive":
        statement = statement.where(User.is_active.is_(False))
    if cursor:
        statement = statement.where(User.email > cursor)
    rows = (await session.execute(statement)).all()
    return [(row[0], row[1]) for row in rows]


# Count active users holding a role that grants one permission scope.
async def count_active_users_with_scope(
    session: AsyncSession,
    scope: str,
    exclude_user_id: UUID | None = None,
    exclude_role_id: UUID | None = None,
) -> int:
    statement = (
        select(func.count(func.distinct(UserRoleMapping.user_id)))
        .select_from(UserRoleMapping)
        .join(User, User.id == UserRoleMapping.user_id)
        .join(Role, Role.id == UserRoleMapping.role_id)
        .join(RolePermission, RolePermission.role_id == Role.id)
        .join(Permission, Permission.id == RolePermission.permission_id)
        .where(
            User.is_active.is_(True),
            Role.is_active.is_(True),
            Permission.code == scope,
        )
    )
    if exclude_user_id is not None:
        statement = statement.where(UserRoleMapping.user_id != exclude_user_id)
    if exclude_role_id is not None:
        statement = statement.where(Role.id != exclude_role_id)
    return int(await session.scalar(statement) or 0)


# List the active users currently mapped to one role.
async def list_active_user_ids_with_role(
    session: AsyncSession, role_id: UUID
) -> list[UUID]:
    rows = (
        await session.execute(
            select(UserRoleMapping.user_id)
            .join(User, User.id == UserRoleMapping.user_id)
            .where(
                UserRoleMapping.role_id == role_id,
                User.is_active.is_(True),
            )
        )
    ).all()
    return [row[0] for row in rows]


# Insert a refresh-session row and return its identifier.
async def create_refresh_session(
    session: AsyncSession,
    *,
    user_id: UUID,
    token_digest: str,
    expires_at: datetime,
) -> UUID:
    record = RefreshSession(
        user_id=user_id,
        token_digest=token_digest,
        expires_at=expires_at,
    )
    session.add(record)
    await session.flush()
    return record.id


# Load the refresh session one presented digest resolves to.
async def find_refresh_session_by_digest(
    session: AsyncSession, token_digest: str
) -> RefreshSession | None:
    return await session.scalar(
        select(RefreshSession).where(
            RefreshSession.token_digest == token_digest
        )
    )


# Map each supplied session to its recorded successor, if one exists.
async def find_replacement_successors(
    session: AsyncSession, session_ids: Sequence[UUID]
) -> dict[UUID, UUID | None]:
    if not session_ids:
        return {}
    rows = (
        await session.execute(
            select(RefreshSession.id, RefreshSession.replaced_by_id).where(
                RefreshSession.id.in_(list(session_ids))
            )
        )
    ).all()
    return {row[0]: row[1] for row in rows}


# Mark the supplied refresh sessions revoked at one moment in time.
async def revoke_refresh_sessions(
    session: AsyncSession,
    session_ids: Iterable[UUID],
    when: datetime,
) -> None:
    identifiers = list(session_ids)
    if not identifiers:
        return
    records = (
        await session.scalars(
            select(RefreshSession).where(
                RefreshSession.id.in_(identifiers),
                RefreshSession.revoked_at.is_(None),
            )
        )
    ).all()
    for record in records:
        record.revoked_at = when


# Mark every live refresh session of one user revoked.
async def revoke_user_refresh_sessions(
    session: AsyncSession, user_id: UUID, when: datetime
) -> None:
    records = (
        await session.scalars(
            select(RefreshSession).where(
                RefreshSession.user_id == user_id,
                RefreshSession.revoked_at.is_(None),
            )
        )
    ).all()
    for record in records:
        record.revoked_at = when


# Record that one session was replaced by its successor.
async def link_refresh_successor(
    session: AsyncSession,
    session_id: UUID,
    successor_id: UUID,
    when: datetime,
) -> None:
    record = await session.get(RefreshSession, session_id)
    if record is not None:
        record.revoked_at = record.revoked_at or when
        record.replaced_by_id = successor_id


# Read the current moment in UTC for refresh-session bookkeeping.
def utcnow() -> datetime:
    return datetime.now(timezone.utc)
