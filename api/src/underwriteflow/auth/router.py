"""Authentication and credential endpoints.

Login and refresh return the same credential payload. Refresh rotates the
presented credential, and a replayed credential revokes its whole replacement
chain instead of issuing anything new. Every attempt is audited without ever
recording a credential value.
"""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from underwriteflow.auth import repository
from underwriteflow.auth.dependencies import get_current_session
from underwriteflow.auth.schemas import (
    AccessTokenResponse,
    CurrentUser,
    LoginRequest,
    RefreshRequest,
    RoleSummary,
    SessionResponse,
)
from underwriteflow.auth.service import AuthService, RefreshError
from underwriteflow.audit.events import build_audit_event
from underwriteflow.database import get_session
from underwriteflow.errors import ApiError

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


# Append one sanitized authentication event and persist it immediately.
async def record_auth_event(
    session: AsyncSession,
    event_type: str,
    details: dict,
    actor_user_id=None,
) -> None:
    session.add(
        build_audit_event(event_type, details, actor_user_id=actor_user_id)
    )
    await session.commit()


# Build the credential payload that both login and refresh return.
def credential_response(
    auth: AuthService,
    user_id,
    role_code: str,
    permissions,
    request: Request,
    refresh_token: str,
) -> AccessTokenResponse:
    settings = request.app.state.settings
    return AccessTokenResponse(
        access_token=auth.issue_access_token(
            user_id,
            role_code,
            permissions,
            settings.access_token_ttl_seconds,
        ),
        refresh_token=refresh_token,
        expires_in=settings.access_token_ttl_seconds,
        refresh_expires_in=settings.refresh_token_ttl_seconds,
    )


# Authenticate one synthetic user and issue both credentials.
@router.post("/login", response_model=AccessTokenResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> AccessTokenResponse:
    auth = build_auth_service(request)
    email = payload.email.strip().casefold()
    candidate = await repository.find_user_by_email(session, email)
    if candidate is None or not auth.verify_password(
        candidate.password_hash, payload.password
    ):
        await record_auth_event(
            session, "login_denied", {"reason": "invalid_credentials"}
        )
        raise ApiError(
            401, "invalid_credentials", "Invalid credentials"
        ) from None
    if not candidate.is_active:
        await record_auth_event(
            session,
            "login_denied",
            {"reason": "inactive_user"},
            actor_user_id=candidate.id,
        )
        raise ApiError(403, "inactive_user", "User is inactive") from None
    resolved = await repository.find_user_role_and_scopes(
        session, candidate.id
    )
    if resolved is None:
        await record_auth_event(
            session,
            "login_denied",
            {"reason": "no_active_role"},
            actor_user_id=candidate.id,
        )
        raise ApiError(
            403, "user_not_authorized", "User is not authorized"
        ) from None
    role, permissions = resolved
    refresh_token = await auth.start_refresh_session(
        session,
        candidate.id,
        request.app.state.settings.refresh_token_ttl_seconds,
    )
    await record_auth_event(
        session,
        "login_succeeded",
        {"role_code": role.code},
        actor_user_id=candidate.id,
    )
    return credential_response(
        auth,
        candidate.id,
        role.code,
        permissions,
        request,
        refresh_token,
    )


# Rotate one refresh credential and re-issue the access token.
@router.post("/refresh", response_model=AccessTokenResponse)
async def refresh(
    payload: RefreshRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> AccessTokenResponse:
    auth = build_auth_service(request)
    try:
        user_id, refresh_token = await auth.rotate_refresh_session(
            session,
            payload.refresh_token,
            request.app.state.settings.refresh_token_ttl_seconds,
        )
    except RefreshError as error:
        await record_auth_event(
            session,
            "refresh_denied",
            {"reason": error.code},
            actor_user_id=error.user_id,
        )
        raise ApiError(
            401, error.code, "Refresh credential is not valid"
        ) from None
    user = await repository.find_user(session, user_id)
    if user is None or not user.is_active:
        raise ApiError(403, "inactive_user", "User is inactive") from None
    resolved = await repository.find_user_role_and_scopes(session, user.id)
    if resolved is None:
        raise ApiError(
            403, "user_not_authorized", "User is not authorized"
        ) from None
    role, permissions = resolved
    await record_auth_event(
        session,
        "refresh_succeeded",
        {"role_code": role.code},
        actor_user_id=user.id,
    )
    return credential_response(
        auth, user.id, role.code, permissions, request, refresh_token
    )


# Serve the legacy session route for the current web client.
@router.post("/session", response_model=SessionResponse)
async def create_session(
    payload: LoginRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> SessionResponse:
    issued = await login(payload, request, session)
    return SessionResponse(
        token=issued.access_token, expires_in=issued.expires_in
    )


# Return the authenticated identity and its current resolved scopes.
@router.get("/me", response_model=CurrentUser)
async def current_user(
    session: dict = Depends(get_current_session),
) -> CurrentUser:
    return CurrentUser(
        id=session["sub"],
        email=session["email"],
        display_name=session["display_name"],
        role=RoleSummary(id=session["role_id"], code=session["role_code"]),
        permissions=list(session["permissions"]),
    )

