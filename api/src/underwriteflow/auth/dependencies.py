"""Scope and ownership dependencies for protected API routes.

Authorization is never taken from the token alone. Every protected request
re-verifies the access token, reloads the active user, and resolves the role
and permission scopes that the database currently grants. A token whose role
or authorization version no longer matches that state is refused, so a
permission change takes effect on the next request instead of at expiry.
"""

from dataclasses import dataclass
from uuid import UUID

from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from underwriteflow.auth.schemas import (
    LEGACY_ROLE_VALUES,
    Permission,
    RoleCode,
    UserRole,
)
from underwriteflow.auth.service import AuthService, authorization_version
from underwriteflow.database import get_session
from underwriteflow.persistence.models import Permission as PermissionRecord
from underwriteflow.persistence.models import (
    Role,
    RolePermission,
    User,
    UserRoleMapping,
)


@dataclass(frozen=True)
class ResolvedAuthorization:
    """The current database authorization behind one authenticated user."""

    role_id: UUID
    role_code: str
    permissions: tuple[str, ...]

    # Derive the version a matching access token must already carry.
    @property
    def version(self) -> str:
        return authorization_version(self.role_code, self.permissions)


# Resolve one user's active role and its current permission scopes.
async def load_authorization(
    session: AsyncSession, user_id: UUID
) -> ResolvedAuthorization | None:
    rows = (
        await session.execute(
            select(Role.id, Role.code, PermissionRecord.code)
            .join(UserRoleMapping, UserRoleMapping.role_id == Role.id)
            .outerjoin(RolePermission, RolePermission.role_id == Role.id)
            .outerjoin(
                PermissionRecord,
                PermissionRecord.id == RolePermission.permission_id,
            )
            .where(
                UserRoleMapping.user_id == user_id,
                Role.is_active.is_(True),
            )
        )
    ).all()
    if not rows:
        return None
    scopes = tuple(sorted({row[2] for row in rows if row[2] is not None}))
    return ResolvedAuthorization(rows[0][0], rows[0][1], scopes)


# Read the bearer credential from one Authorization header.
def bearer_token(authorization: str | None) -> str:
    try:
        scheme, token = (authorization or "").split(" ", 1)
        if scheme.lower() != "bearer" or not token:
            raise ValueError("invalid scheme")
        return token
    except (AttributeError, ValueError) as error:
        raise HTTPException(
            status_code=401, detail="Invalid session"
        ) from error


# Verify the bearer token and re-resolve its current authorization.
async def get_current_session(
    request: Request,
    authorization: str | None = Header(default=None),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    settings = request.app.state.settings
    service = AuthService(
        settings.session_secret,
        issuer=settings.jwt_issuer,
        audience=settings.jwt_audience,
        refresh_pepper=settings.refresh_token_pepper,
    )
    try:
        claims = service.read_access_token(bearer_token(authorization))
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid session") from None
    user = await session.scalar(
        select(User).where(
            User.id == claims.sub, User.is_active.is_(True)
        )
    )
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid session")
    resolved = await load_authorization(session, user.id)
    if resolved is None:
        raise HTTPException(status_code=403, detail="Forbidden")
    if (
        resolved.role_code != claims.role
        or resolved.version != claims.authz_version
    ):
        # The snapshot in the token is stale, so a new token is required.
        raise HTTPException(
            status_code=401, detail="Stale authorization"
        ) from None
    return {
        "sub": str(user.id),
        "role": LEGACY_ROLE_VALUES.get(resolved.role_code, resolved.role_code),
        "role_code": resolved.role_code,
        "role_id": str(resolved.role_id),
        "email": user.email,
        "display_name": user.display_name,
        "permissions": list(resolved.permissions),
        "authz_version": resolved.version,
    }


# Require the current role to be the underwriter role itself.
#
# Confirming, overriding, and completing a route stays underwriter-only even
# for broad administrator scope sets, so this is an identity rule rather than
# a permission. The comparison uses the stable role code the database granted,
# never a permission name or a legacy label.
def require_underwriter():
    # Authorize a request that only the underwriter role may perform.
    def dependency(
        session: dict[str, object] = Depends(get_current_session),
    ) -> dict[str, object]:
        if session["role_code"] != RoleCode.UNDERWRITER.value:
            raise HTTPException(status_code=403, detail="Forbidden")
        return session

    return dependency


# Require the resolved database scopes to cover one protected action.
def require_permission(permission: Permission):
    # Authorize a session against its resolved scope list.
    def dependency(
        session: dict[str, object] = Depends(get_current_session),
    ) -> dict[str, object]:
        granted = session.get("permissions") or ()
        if permission.value not in granted:
            raise HTTPException(status_code=403, detail="Forbidden")
        return session

    return dependency


# Let applicants reach only their own case while staff review every case.
def authorize_case_access(
    session: dict[str, object], applicant_user_id: UUID
) -> bool:
    role = session["role"]
    if role in {UserRole.UNDERWRITER.value, UserRole.ADMINISTRATOR.value}:
        return True
    return role == UserRole.APPLICANT.value and session["sub"] == str(
        applicant_user_id
    )

