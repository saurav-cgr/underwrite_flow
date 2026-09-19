"""Scoped user, role, and permission administration routes.

Every route requires the `users:manage` scope. Responses never carry password
hashes, credential values, or authorization state beyond the resolved scopes
an administrator needs to reason about access.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from underwriteflow.auth import admin_service, repository
from underwriteflow.auth.dependencies import require_permission
from underwriteflow.auth.router import build_auth_service
from underwriteflow.auth.schemas import (
    CreateRoleRequest,
    CreateUserRequest,
    Permission,
    PermissionSummary,
    RoleRecord,
    RoleSummary,
    UpdateRoleRequest,
    UpdateUserRequest,
    UserRecord,
)
from underwriteflow.database import get_session
from underwriteflow.errors import ApiError
from underwriteflow.persistence.models import Role, User

router = APIRouter(prefix="/admin", tags=["access administration"])

DEFAULT_LIMIT = 50
MAX_LIMIT = 100


# Build one administrable user record from its stored state.
def user_record(user: User, role: Role | None) -> UserRecord:
    return UserRecord(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        is_active=user.is_active,
        role=(
            None
            if role is None
            else RoleSummary(id=role.id, code=role.code)
        ),
        created_at=user.created_at,
    )


# Build one role record with its resolved permission scopes.
async def role_record(session: AsyncSession, role: Role) -> RoleRecord:
    scopes = await repository.list_role_scopes(session, role.id)
    return RoleRecord(
        id=role.id,
        code=role.code,
        title=role.title,
        description=role.description,
        is_active=role.is_active,
        is_system=role.is_system,
        permissions=list(scopes),
    )


# List administrable users with optional status filtering and paging.
@router.get("/users", response_model=list[UserRecord])
async def list_users(
    status: str | None = None,
    limit: int = Query(default=DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
    cursor: str | None = None,
    _: dict = Depends(require_permission(Permission.USERS_MANAGE)),
    session: AsyncSession = Depends(get_session),
) -> list[UserRecord]:
    rows = await repository.list_users(session, status, limit, cursor)
    return [user_record(user, role) for user, role in rows]


# Create one active synthetic user with a single role assignment.
@router.post("/users", response_model=UserRecord, status_code=201)
async def create_user(
    payload: CreateUserRequest,
    request: Request,
    operator: dict = Depends(require_permission(Permission.USERS_MANAGE)),
    session: AsyncSession = Depends(get_session),
) -> UserRecord:
    user = await admin_service.create_user(
        session,
        build_auth_service(request),
        email=payload.email,
        display_name=payload.display_name,
        password=payload.password,
        role_id=payload.role_id,
        actor_user_id=UUID(operator["sub"]),
    )
    return user_record(user, await repository.find_user_role(session, user.id))


# Change one user's display name, active state, or role.
@router.patch("/users/{user_id}", response_model=UserRecord)
async def update_user(
    user_id: UUID,
    payload: UpdateUserRequest,
    operator: dict = Depends(require_permission(Permission.USERS_MANAGE)),
    session: AsyncSession = Depends(get_session),
) -> UserRecord:
    user = await repository.find_user(session, user_id)
    if user is None:
        raise ApiError(404, "user_not_found", "User not found")
    updated = await admin_service.update_user(
        session,
        user=user,
        display_name=payload.display_name,
        is_active=payload.is_active,
        role_id=payload.role_id,
        actor_user_id=UUID(operator["sub"]),
    )
    role = await repository.find_user_role(session, updated.id)
    return user_record(updated, role)


# List every configured role with its sorted permission scopes.
@router.get("/roles", response_model=list[RoleRecord])
async def list_roles(
    _: dict = Depends(require_permission(Permission.USERS_MANAGE)),
    session: AsyncSession = Depends(get_session),
) -> list[RoleRecord]:
    roles = await repository.list_roles(session)
    return [await role_record(session, role) for role in roles]


# Create one configurable role and its permission mappings.
@router.post("/roles", response_model=RoleRecord, status_code=201)
async def create_role(
    payload: CreateRoleRequest,
    operator: dict = Depends(require_permission(Permission.USERS_MANAGE)),
    session: AsyncSession = Depends(get_session),
) -> RoleRecord:
    role = await admin_service.create_role(
        session,
        code=payload.code,
        title=payload.title,
        description=payload.description,
        permissions=payload.permissions,
        actor_user_id=UUID(operator["sub"]),
    )
    return await role_record(session, role)


# Change one role's metadata, active state, or complete scope list.
@router.patch("/roles/{role_id}", response_model=RoleRecord)
async def update_role(
    role_id: UUID,
    payload: UpdateRoleRequest,
    operator: dict = Depends(require_permission(Permission.USERS_MANAGE)),
    session: AsyncSession = Depends(get_session),
) -> RoleRecord:
    role = await repository.find_role(session, role_id)
    if role is None:
        raise ApiError(404, "role_not_found", "Role not found")
    updated = await admin_service.update_role(
        session,
        role=role,
        title=payload.title,
        description=payload.description,
        is_active=payload.is_active,
        permissions=payload.permissions,
        actor_user_id=UUID(operator["sub"]),
    )
    return await role_record(session, updated)


# Return the fixed permission catalogue available to compose roles from.
@router.get("/permissions", response_model=list[PermissionSummary])
async def list_permission_catalogue(
    _: dict = Depends(require_permission(Permission.USERS_MANAGE)),
    session: AsyncSession = Depends(get_session),
) -> list[PermissionSummary]:
    records = await repository.list_permissions(session)
    return [
        PermissionSummary(
            code=record.code,
            title=record.title,
            description=record.description,
        )
        for record in records
    ]
