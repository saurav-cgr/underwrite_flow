"""Strict access tokens, refresh credentials, and rotation decisions.

The service owns two narrow responsibilities: minting and verifying strict
HS256 access tokens, and deciding what one presented refresh credential means
for its stored session row. Persisted rotation state lives in
``refresh_sessions``, so the decision logic here stays pure and can be tested
without a database.
"""

import base64
import binascii
import hashlib
import hmac
import json
import secrets
import time
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from argon2 import PasswordHasher
from argon2.exceptions import (
    InvalidHashError,
    VerificationError,
    VerifyMismatchError,
)
from pydantic import ValidationError

from underwriteflow.auth.schemas import AccessTokenClaims

ACCESS_TOKEN_ALGORITHM = "HS256"
ACCESS_TOKEN_JWT_TYPE = "JWT"
ACCESS_TOKEN_TYPE = "access"
ACCESS_TOKEN_SEGMENTS = 3
AUTHORIZATION_VERSION_LENGTH = 16
REFRESH_CREDENTIAL_BYTES = 32


class RefreshOutcome(StrEnum):
    """What one presented refresh credential means for its session row."""

    ROTATE = "rotate"
    REPLAY = "replay"
    EXPIRED = "expired"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class RefreshSessionRecord:
    """Stored refresh-session state, free of any database session."""

    id: UUID
    user_id: UUID
    expires_at: datetime
    revoked_at: datetime | None
    replaced_by_id: UUID | None


@dataclass(frozen=True)
class RotationPlan:
    """The decision one presented refresh credential produced."""

    outcome: RefreshOutcome
    session_id: UUID | None = None
    user_id: UUID | None = None


# Encode one JWT segment as unpadded base64url.
def encode_segment(value: dict) -> str:
    raw = json.dumps(value, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


# Decode one unpadded base64url segment to its raw bytes.
def decode_segment(segment: str) -> bytes:
    return base64.urlsafe_b64decode(segment + "=" * (-len(segment) % 4))


# Derive the authorization version that a token claim must match.
def authorization_version(role_code: str, permissions: Iterable[str]) -> str:
    material = f"{role_code}|{','.join(sorted(set(permissions)))}"
    digest = hashlib.sha256(material.encode()).hexdigest()
    return digest[:AUTHORIZATION_VERSION_LENGTH]


# Decide what one presented refresh credential means for its stored row.
def plan_refresh_rotation(
    record: RefreshSessionRecord | None, now: datetime
) -> RotationPlan:
    if record is None:
        return RotationPlan(RefreshOutcome.UNKNOWN)
    if record.revoked_at is not None:
        return RotationPlan(RefreshOutcome.REPLAY, record.id, record.user_id)
    if record.expires_at <= now:
        return RotationPlan(RefreshOutcome.EXPIRED, record.id, record.user_id)
    return RotationPlan(RefreshOutcome.ROTATE, record.id, record.user_id)


# Collect every later session that a replayed credential must also revoke.
def replacement_chain(
    start: UUID, successors: Mapping[UUID, UUID | None]
) -> tuple[UUID, ...]:
    seen = {start}
    chain: list[UUID] = []
    current = successors.get(start)
    while current is not None and current not in seen:
        chain.append(current)
        seen.add(current)
        current = successors.get(current)
    return tuple(chain)


class AuthService:
    """Issue strict access tokens and rotate refresh credentials."""

    # Initialize password hashing, token signing, and refresh keying.
    def __init__(
        self,
        secret: str,
        issuer: str = "underwriteflow",
        audience: str = "underwriteflow-web",
        refresh_pepper: str = "",
    ) -> None:
        if not secret:
            raise ValueError("session secret is required")
        self.secret = secret.encode()
        self.issuer = issuer
        self.audience = audience
        self.refresh_pepper = refresh_pepper.encode()
        self.hasher = PasswordHasher()

    # Hash a fictional demo password with Argon2.
    def hash_password(self, password: str) -> str:
        return self.hasher.hash(password)

    # Verify a password against its stored Argon2 hash.
    def verify_password(self, password_hash: str, password: str) -> bool:
        try:
            return self.hasher.verify(password_hash, password)
        except (InvalidHashError, VerificationError, VerifyMismatchError):
            return False

    # Issue one strict HS256 access token from resolved authorization.
    def issue_access_token(
        self,
        user_id: UUID,
        role_code: str,
        permissions: Iterable[str],
        ttl_seconds: int = 900,
    ) -> str:
        try:
            subject = str(UUID(str(user_id)))
        except (TypeError, ValueError) as error:
            raise ValueError("invalid access token identity") from error
        scopes = sorted(set(permissions))
        issued_at = int(time.time())
        header = {
            "alg": ACCESS_TOKEN_ALGORITHM,
            "typ": ACCESS_TOKEN_JWT_TYPE,
        }
        claims = {
            "sub": subject,
            "role": role_code,
            "permissions": scopes,
            "typ": ACCESS_TOKEN_TYPE,
            "iat": issued_at,
            "exp": issued_at + ttl_seconds,
            "iss": self.issuer,
            "aud": self.audience,
            "jti": str(uuid4()),
            "authz_version": authorization_version(role_code, scopes),
        }
        header_part = encode_segment(header)
        payload_part = encode_segment(claims)
        signature = hmac.new(
            self.secret,
            f"{header_part}.{payload_part}".encode(),
            hashlib.sha256,
        ).digest()
        encoded_signature = base64.urlsafe_b64encode(signature).decode()
        return f"{header_part}.{payload_part}.{encoded_signature.rstrip('=')}"

    # Verify one strict access token and return its typed claims.
    def read_access_token(self, token: str) -> AccessTokenClaims:
        header, claims = self._verified_segments(token)
        if header.get("alg") != ACCESS_TOKEN_ALGORITHM:
            raise ValueError("unsupported access token algorithm")
        try:
            parsed = AccessTokenClaims.model_validate(claims)
        except ValidationError as error:
            raise ValueError("invalid access token claims") from error
        if parsed.iss != self.issuer:
            raise ValueError("invalid access token issuer")
        if parsed.aud != self.audience:
            raise ValueError("invalid access token audience")
        if parsed.exp <= time.time():
            raise ValueError("expired access token")
        return parsed

    # Issue one random opaque refresh credential.
    def issue_refresh_credential(self) -> str:
        return secrets.token_urlsafe(REFRESH_CREDENTIAL_BYTES)

    # Derive the keyed digest that is stored in place of a credential.
    def refresh_digest(self, credential: str) -> str:
        return hmac.new(
            self.refresh_pepper, credential.encode(), hashlib.sha256
        ).hexdigest()

    # Verify the token signature and decode its header and claims.
    def _verified_segments(self, token: str) -> tuple[dict, dict]:
        parts = token.split(".") if isinstance(token, str) else []
        if len(parts) != ACCESS_TOKEN_SEGMENTS:
            raise ValueError("invalid access token")
        header_part, payload_part, signature_part = parts
        expected = hmac.new(
            self.secret,
            f"{header_part}.{payload_part}".encode(),
            hashlib.sha256,
        ).digest()
        if not hmac.compare_digest(
            self._decode(signature_part), expected
        ):
            raise ValueError("invalid access token signature")
        return self._decode_json(header_part), self._decode_json(payload_part)

    # Decode one segment, refusing any value that is not base64url.
    def _decode(self, segment: str) -> bytes:
        try:
            return decode_segment(segment)
        except (binascii.Error, ValueError) as error:
            raise ValueError("invalid access token") from error

    # Decode one segment as a JSON object.
    def _decode_json(self, segment: str) -> dict:
        try:
            decoded = json.loads(self._decode(segment))
        except (UnicodeDecodeError, ValueError) as error:
            raise ValueError("invalid access token") from error
        if not isinstance(decoded, dict):
            raise ValueError("invalid access token")
        return decoded
