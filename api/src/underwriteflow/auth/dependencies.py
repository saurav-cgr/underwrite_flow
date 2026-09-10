"""Role and ownership dependencies for protected API routes."""

from uuid import UUID

from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from underwriteflow.auth.schemas import Permission, UserRole
from underwriteflow.auth.service import AuthService
from underwriteflow.database import get_session
from underwriteflow.persistence.models import User


ROLE_PERMISSIONS: dict[UserRole, frozenset[Permission]] = {
    UserRole.APPLICANT: frozenset({Permission.CASE_READ, Permission.CASE_WRITE}),
    UserRole.UNDERWRITER: frozenset(
        {Permission.CASE_READ, Permission.REVIEW_READ, Permission.REVIEW_WRITE}
    ),
    UserRole.ADMINISTRATOR: frozenset(Permission),
}


# Read and validate the configured bearer session.
async def get_current_session(
    request: Request,
    authorization: str | None = Header(default=None),
    session: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    if not authorization:
        raise HTTPException(status_code=401, detail="Invalid session")
    try:
        scheme, token = authorization.split(" ", 1)
        if scheme.lower() != "bearer":
            raise ValueError("invalid scheme")
        signed_session = AuthService(request.app.state.settings.session_secret).read_session(token)
    except (ValueError, TypeError, AttributeError):
        raise HTTPException(status_code=401, detail="Invalid session") from None
    user = await session.scalar(
        select(User).where(User.id == UUID(signed_session["sub"]), User.is_active.is_(True))
    )
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid session")
    try:
        role = UserRole(user.role).value
    except ValueError:
        raise HTTPException(status_code=403, detail="Forbidden") from None
    return {"sub": str(user.id), "role": role}


# Require a signed bearer session with one accepted role.
def require_role(*roles: str):
    accepted_roles = {UserRole(role).value for role in roles}

    # Authorize a request from its bearer session.
    def dependency(
        session: dict[str, str] = Depends(get_current_session),
    ) -> dict[str, str]:
        if session["role"] not in accepted_roles:
            raise HTTPException(status_code=403, detail="Forbidden")
        return session

    return dependency


# Require a role with permission for one protected backend action.
def require_permission(permission: Permission):
    # Authorize a session against the explicit permission matrix.
    def dependency(
        session: dict[str, str] = Depends(get_current_session),
    ) -> dict[str, str]:
        role = UserRole(session["role"])
        if permission not in ROLE_PERMISSIONS[role]:
            raise HTTPException(status_code=403, detail="Forbidden")
        return session

    return dependency


# Allow applicants to access only their own case while staff can review all cases.
def authorize_case_access(session: dict[str, str], applicant_user_id: UUID) -> bool:
    if session["role"] in {UserRole.UNDERWRITER.value, UserRole.ADMINISTRATOR.value}:
        return True
    return session["role"] == UserRole.APPLICANT.value and session["sub"] == str(applicant_user_id)
