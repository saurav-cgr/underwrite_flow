"""Demo session endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from underwriteflow.auth.dependencies import get_current_session
from underwriteflow.auth.schemas import LoginRequest, SessionResponse
from underwriteflow.auth.service import AuthService
from underwriteflow.database import get_session
from underwriteflow.persistence.models import User

router = APIRouter(prefix="/auth", tags=["auth"])


# Authenticate one persisted fictional demo user.
@router.post("/session", response_model=SessionResponse)
async def create_session(
    login: LoginRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> SessionResponse:
    user = await session.scalar(
        select(User).where(User.email == login.email.strip().casefold(), User.is_active.is_(True))
    )
    auth = AuthService(request.app.state.settings.session_secret)
    if user is None or not auth.verify_password(user.password_hash, login.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    try:
        token = auth.issue_session(
            user.id,
            user.role,
            request.app.state.settings.session_ttl_seconds,
        )
    except ValueError:
        raise HTTPException(status_code=403, detail="User is not authorized") from None
    return SessionResponse(
        token=token,
        expires_in=request.app.state.settings.session_ttl_seconds,
    )


# Return the authenticated session identity for the frontend.
@router.get("/me")
async def current_session(
    session: dict[str, str] = Depends(get_current_session),
) -> dict[str, str]:
    return session
