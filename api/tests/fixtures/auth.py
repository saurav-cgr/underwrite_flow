"""Shared helpers for the authentication and authorization test suites.

Minting a well-formed token is easy; minting a deliberately malformed one is
not, so the forging helpers live here instead of being rebuilt in each suite.
"""

import base64
import hashlib
import hmac
import json
import time
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from underwriteflow.auth.schemas import LEGACY_ROLE_VALUES, Permission
from underwriteflow.auth.service import AuthService, RefreshSessionRecord
from underwriteflow.config import Settings

SECRET = "synthetic-test-secret"
PEPPER = "synthetic-refresh-pepper"

# The scopes each seeded role grants, mirroring revision 07's seed data.
ROLE_SCOPES: dict[str, tuple[str, ...]] = {
    "applicant": ("cases:read", "cases:write"),
    "underwriter": (
        "cases:override",
        "cases:read",
        "reviews:read",
        "reviews:write",
    ),
    "administrator": tuple(sorted(scope.value for scope in Permission)),
}

# The exact claim names one access token may carry.
CLAIM_KEYS = {
    "sub",
    "role",
    "permissions",
    "typ",
    "iat",
    "exp",
    "iss",
    "aud",
    "jti",
    "authz_version",
}


# Build a service with explicit synthetic token settings.
def build_service(
    secret: str = SECRET,
    issuer: str = "underwriteflow",
    audience: str = "underwriteflow-web",
    pepper: str = PEPPER,
) -> AuthService:
    return AuthService(
        secret,
        issuer=issuer,
        audience=audience,
        refresh_pepper=pepper,
    )


# Build the token service configured exactly like the default application.
def app_service() -> AuthService:
    settings = Settings()
    return AuthService(
        settings.session_secret,
        issuer=settings.jwt_issuer,
        audience=settings.jwt_audience,
        refresh_pepper=settings.refresh_token_pepper,
    )


# Decode one JWT segment without verifying its signature.
def decode_segment(segment: str) -> dict:
    padded = segment + "=" * (-len(segment) % 4)
    return json.loads(base64.urlsafe_b64decode(padded))


# Re-sign a forged header and payload with a chosen secret.
def sign(header: dict, payload: dict, secret: str = SECRET) -> str:
    # Encode one JWT segment the way RFC 7515 requires.
    def encode(value: dict) -> str:
        raw = json.dumps(value, separators=(",", ":")).encode()
        return base64.urlsafe_b64encode(raw).decode().rstrip("=")

    header_part = encode(header)
    payload_part = encode(payload)
    signature = hmac.new(
        secret.encode(),
        f"{header_part}.{payload_part}".encode(),
        hashlib.sha256,
    ).digest()
    return (
        f"{header_part}.{payload_part}."
        f"{base64.urlsafe_b64encode(signature).decode().rstrip('=')}"
    )


# Build one signed payload for the negative access-token tests.
def signed_payload(**overrides: object) -> str:
    return sign({"alg": "HS256", "typ": "JWT"}, claim_payload(**overrides))


# Build one minimal access payload for the negative claim tests.
def claim_payload(**overrides: object) -> dict:
    payload: dict[str, object] = {
        "sub": str(uuid4()),
        "role": "applicant",
        "permissions": ["cases:read"],
        "typ": "access",
        "iat": int(time.time()),
        "exp": int(time.time()) + 900,
        "iss": "underwriteflow",
        "aud": "underwriteflow-web",
        "jti": str(uuid4()),
        "authz_version": "synthetic-version",
    }
    payload.update(overrides)
    return payload


# Build the resolved session payload one seeded role produces.
def session_for(role_code: str, user_id: str | None = None) -> dict:
    return {
        "sub": user_id or str(uuid4()),
        "role": LEGACY_ROLE_VALUES[role_code],
        "role_code": role_code,
        "permissions": list(ROLE_SCOPES[role_code]),
    }


# Build the stored refresh-session state one credential resolves to.
def refresh_record(
    expires_in: timedelta = timedelta(hours=8),
    revoked_at: datetime | None = None,
    replaced_by_id: UUID | None = None,
) -> RefreshSessionRecord:
    return RefreshSessionRecord(
        id=uuid4(),
        user_id=uuid4(),
        expires_at=datetime.now(timezone.utc) + expires_in,
        revoked_at=revoked_at,
        replaced_by_id=replaced_by_id,
    )
