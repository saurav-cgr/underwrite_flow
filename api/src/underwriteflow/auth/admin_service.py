"""Transactional user and role administration.

Every mutation here writes its business change and its audit event in one
transaction, and every privileged change is checked against the live database
so the final active holder of ``users:manage`` can never be removed.
"""

import re
from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from underwriteflow.auth import repository
from underwriteflow.auth.schemas import LEGACY_ROLE_VALUES
from underwriteflow.auth.service import AuthService
from underwriteflow.audit.events import build_audit_event
from underwriteflow.errors import ApiError
from underwriteflow.persistence.models import (
    Permission,
    Role,
    RolePermission,
    User,
    UserRoleMapping,
)

USERS_MANAGE_SCOPE = "users:manage"

# Stable role codes use lowercase letters, digits, and underscores.
ROLE_CODE_PATTERN = re.compile(r"^[a-z0-9_]{2,64}$")

# Legacy role column width, which still exists during the cutover.
LEGACY_ROLE_WIDTH = 32


# Build the sanitized error a refused administration change returns.
def _refused(status_code: int, code: str, message: str) -> ApiError:
    return ApiError(status_code=status_code, code=code, message=message)


# Append one sanitized access-administration audit event.
def _record(
    session: AsyncSession,
    event_type: str,
    actor_user_id: UUID,
    details: dict,
) -> None:
    session.add(
        build_audit_event(
            event_type, details, actor_user_id=actor_user_id
        )
    )


# Write the legacy role column value that mirrors one configured role.
def _legacy_role_value(role: Role) -> str:
    value = LEGACY_ROLE_VALUES.get(role.code, role.code)
    return value[:LEGACY_ROLE_WIDTH]


# Resolve one assignable active role or refuse the request.
async def _assignable_role(session: AsyncSession, role_id: UUID) -> Role:
    role = await repository.find_role(session, role_id)
    if role is None or not role.is_active:
        raise _refused(422, "unknown_role", "Role is not assignable")
    return role


# Refuse a change that would leave no active holder of `users:manage`.
async def _guard_last_administrator(
    session: AsyncSession,
    user: User,
    next_role: Role | None,
    next_is_active: bool | None,
) -> None:
    current = await repository.find_user_role_and_scopes(session, user.id)
    if current is None or not user.is_active:
        return
    current_role, current_scopes = current
    if USERS_MANAGE_SCOPE not in current_scopes:
        return
    if next_is_active is not False:
        if next_role is None or next_role.id == current_role.id:
            return
        if USERS_MANAGE_SCOPE in await repository.list_role_scopes(
            session, next_role.id
        ):
            return
    remaining = await repository.count_active_users_with_scope(
        session, USERS_MANAGE_SCOPE, exclude_user_id=user.id
    )
    if remaining == 0:
        raise _refused(
            409,
            "last_administrator",
            "At least one active administrator is required",
        )


# Refuse a role change that would strand the final active administrator.
async def _guard_role_change(
    session: AsyncSession,
    role: Role,
    next_is_active: bool | None,
    next_permissions: Sequence[str] | None,
) -> None:
    current_scopes = await repository.list_role_scopes(session, role.id)
    if USERS_MANAGE_SCOPE not in current_scopes:
        return
    loses_capability = next_is_active is False or (
        next_permissions is not None
        and USERS_MANAGE_SCOPE not in set(next_permissions)
    )
    if not loses_capability:
        return
    holders = await repository.list_active_user_ids_with_role(session, role.id)
    if not holders:
        return
    remaining = await repository.count_active_users_with_scope(
        session, USERS_MANAGE_SCOPE, exclude_role_id=role.id
    )
    if remaining == 0:
        raise _refused(
            409,
            "last_administrator",
            "At least one active administrator is required",
        )


# Replace one user's single role mapping transactionally.
async def _replace_role(
    session: AsyncSession,
    user: User,
    role: Role,
    actor_user_id: UUID,
) -> None:
    mapping = await session.scalar(
        select(UserRoleMapping).where(UserRoleMapping.user_id == user.id)
    )
    if mapping is None:
        session.add(
            UserRoleMapping(
                user_id=user.id,
                role_id=role.id,
                assigned_by_user_id=actor_user_id,
            )
        )
    else:
        mapping.role_id = role.id
        mapping.assigned_by_user_id = actor_user_id
    user.role = _legacy_role_value(role)
    _record(
        session,
        "user_role_replaced",
        actor_user_id,
        {"target_user_id": str(user.id), "role_code": role.code},
    )


# Create one active synthetic user with exactly one role assignment.
async def create_user(
    session: AsyncSession,
    auth: AuthService,
    *,
    email: str,
    display_name: str,
    password: str,
    role_id: UUID,
    actor_user_id: UUID,
) -> User:
    normalized = email.strip().casefold()
    existing = await session.scalar(
        select(User).where(User.email == normalized)
    )
    if existing is not None:
        raise _refused(409, "user_exists", "User already exists")
    role = await _assignable_role(session, role_id)
    user = User(
        email=normalized,
        display_name=display_name.strip(),
        role=_legacy_role_value(role),
        password_hash=auth.hash_password(password),
        is_active=True,
    )
    session.add(user)
    await session.flush()
    session.add(
        UserRoleMapping(
            user_id=user.id,
            role_id=role.id,
            assigned_by_user_id=actor_user_id,
        )
    )
    _record(
        session,
        "user_created",
        actor_user_id,
        {"target_user_id": str(user.id), "role_code": role.code},
    )
    await session.commit()
    return user


# Apply one administration change to a user.
async def update_user(
    session: AsyncSession,
    *,
    user: User,
    display_name: str | None,
    is_active: bool | None,
    role_id: UUID | None,
    actor_user_id: UUID,
) -> User:
    role = (
        None
        if role_id is None
        else await _assignable_role(session, role_id)
    )
    await _guard_last_administrator(session, user, role, is_active)
    if role is not None:
        await _replace_role(session, user, role, actor_user_id)
    if display_name is not None:
        user.display_name = display_name.strip()
    if is_active is not None:
        user.is_active = is_active
        if not is_active:
            await repository.revoke_user_refresh_sessions(
                session, user.id, repository.utcnow()
            )
    _record(
        session,
        "user_updated",
        actor_user_id,
        {
            "target_user_id": str(user.id),
            "is_active": user.is_active,
            "display_name": user.display_name,
        },
    )
    await session.commit()
    return user


# Resolve the fixed permission records for a requested scope list.
async def _permission_records(
    session: AsyncSession, codes: Sequence[str]
) -> list[Permission]:
    requested = sorted(set(codes))
    records = await repository.find_permissions_by_codes(session, requested)
    known = {record.code for record in records}
    unknown = sorted(set(requested) - known)
    if unknown:
        raise _refused(
            422,
            "unknown_permissions",
            f"Unknown permission codes: {', '.join(unknown)}",
        )
    return records


# Replace every permission mapping of one role transactionally.
async def _replace_permissions(
    session: AsyncSession,
    role: Role,
    records: Sequence[Permission],
    actor_user_id: UUID,
) -> None:
    existing = (
        await session.scalars(
            select(RolePermission).where(RolePermission.role_id == role.id)
        )
    ).all()
    for pair in existing:
        await session.delete(pair)
    for record in records:
        session.add(
            RolePermission(
                role_id=role.id,
                permission_id=record.id,
                assigned_by_user_id=actor_user_id,
            )
        )


# Apply one administration change to a role and its scope list.
async def update_role(
    session: AsyncSession,
    *,
    role: Role,
    title: str | None,
    description: str | None,
    is_active: bool | None,
    permissions: Sequence[str] | None,
    actor_user_id: UUID,
) -> Role:
    await _guard_role_change(session, role, is_active, permissions)
    if permissions is not None:
        await _replace_permissions(
            session,
            role,
            await _permission_records(session, permissions),
            actor_user_id,
        )
    if title is not None:
        role.title = title.strip()
    if description is not None:
        role.description = description.strip() or None
    if is_active is not None:
        role.is_active = is_active
    _record(
        session,
        "role_updated",
        actor_user_id,
        {
            "target_role_id": str(role.id),
            "role_code": role.code,
            "is_active": role.is_active,
        },
    )
    await session.commit()
    return role


# Create one configurable role with its permission mappings.
async def create_role(
    session: AsyncSession,
    *,
    code: str,
    title: str,
    description: str | None,
    permissions: Sequence[str],
    actor_user_id: UUID,
) -> Role:
    normalized = code.strip().lower()
    if not ROLE_CODE_PATTERN.fullmatch(normalized):
        raise _refused(
            422,
            "invalid_role_code",
            "Role codes use lowercase letters, digits, and underscores",
        )
    if await repository.find_role_by_code(session, normalized) is not None:
        raise _refused(409, "role_exists", "Role already exists")
    records = await _permission_records(session, permissions)
    role = Role(
        code=normalized,
        title=title.strip(),
        description=(description or "").strip() or None,
        is_active=True,
        is_system=False,
        created_by_user_id=actor_user_id,
    )
    session.add(role)
    await session.flush()
    await _replace_permissions(session, role, records, actor_user_id)
    _record(
        session,
        "role_created",
        actor_user_id,
        {
            "target_role_id": str(role.id),
            "role_code": role.code,
            "permission_codes": [record.code for record in records],
        },
    )
    await session.commit()
    return role
