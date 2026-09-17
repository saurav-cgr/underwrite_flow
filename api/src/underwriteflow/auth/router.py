"""Demo session endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from underwriteflow.auth.dependencies import (
    get_current_session,
    load_authorization,
)
from underwriteflow.auth.schemas import LoginRequest, SessionResponse
from underwriteflow.auth.service import AuthService
from underwriteflow.database import get_session
from underwriteflow.persistence.models import User

router = APIRouter(prefix="/auth", tags=["auth"])


# Build the token service from configured signing and keying values.
def build_auth_service(request: Request) -> AuthService:
    settings = request.app.state.settings
    return AuthService(
        settings.session_secret,
        issuer=settings.jwt_issuer,
        audience=settings.jwt_audience,
        refresh_pepper=settings.refresh_token_pepper,
    )


# Authenticate one persisted fictional demo user.
@router.post("/session", response_model=SessionResponse)
async def create_session(
    login: LoginRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> SessionResponse:
    settings = request.app.state.settings
    auth = build_auth_service(request)
    user = await session.scalar(
        select(User).where(
            User.email == login.email.strip().casefold(),
            User.is_active.is_(True),
        )
    )
    if user is None or not auth.verify_password(
        user.password_hash, login.password
    ):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    resolved = await load_authorization(session, user.id)
    if resolved is None:
        raise HTTPException(status_code=403, detail="User is not authorized")
    return SessionResponse(
        token=auth.issue_access_token(
            user.id,
            resolved.role_code,
            resolved.permissions,
            settings.access_token_ttl_seconds,
        ),
        expires_in=settings.access_token_ttl_seconds,
    )


# Return the authenticated identity and its current resolved scopes.
@router.get("/me")
async def current_session(
    session: dict[str, object] = Depends(get_current_session),
) -> dict[str, object]:
    return session

