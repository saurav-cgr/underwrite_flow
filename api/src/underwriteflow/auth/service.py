"""Password hashing and signed demo sessions."""

import base64
import binascii
import hashlib
import hmac
import json
import time
from uuid import UUID

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from underwriteflow.auth.schemas import UserRole


class AuthService:
    """Issue short-lived signed sessions for fictional users."""

    # Initialize password hashing with an application signing key.
    def __init__(self, secret: str) -> None:
        if not secret:
            raise ValueError("session secret is required")
        self.secret = secret.encode()
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

    # Issue a compact HMAC-signed session token.
    def issue_session(self, user_id: UUID, role: str, ttl_seconds: int = 900) -> str:
        try:
            normalized_role = UserRole(role).value
            normalized_user_id = str(UUID(str(user_id)))
        except (TypeError, ValueError) as error:
            raise ValueError("invalid session identity") from error
        payload = {
            "sub": normalized_user_id,
            "role": normalized_role,
            "exp": int(time.time()) + ttl_seconds,
        }
        encoded = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
        signature = hmac.new(self.secret, encoded.encode(), hashlib.sha256).hexdigest()
        return f"{encoded}.{signature}"

    # Verify a signed unexpired session token.
    def read_session(self, token: str) -> dict[str, str]:
        try:
            encoded, signature = token.rsplit(".", 1)
        except (AttributeError, ValueError) as error:
            raise ValueError("invalid session") from error
        expected = hmac.new(self.secret, encoded.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected):
            raise ValueError("invalid session")
        try:
            payload = json.loads(base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4)))
            user_id = UUID(payload["sub"])
            role = UserRole(payload["role"])
            expires_at = int(payload["exp"])
        except (
            binascii.Error,
            KeyError,
            TypeError,
            UnicodeDecodeError,
            ValueError,
            json.JSONDecodeError,
        ) as error:
            raise ValueError("invalid session") from error
        if expires_at <= time.time():
            raise ValueError("expired session")
        return {"sub": str(user_id), "role": role.value}
