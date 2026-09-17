"""Typed authentication contracts."""

from datetime import datetime
from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class UserRole(StrEnum):
    """Legacy demonstration role values, retained for the column cutover."""

    APPLICANT = "Applicant"
    UNDERWRITER = "Underwriter"
    ADMINISTRATOR = "Administrator"


class RoleCode(StrEnum):
    """Stable lowercase role codes owned by the database."""

    APPLICANT = "applicant"
    UNDERWRITER = "underwriter"
    ADMINISTRATOR = "administrator"


class Permission(StrEnum):
    """Backend actions protected by permission scopes."""

    CASE_READ = "cases:read"
    CASE_WRITE = "cases:write"
    CASES_OVERRIDE = "cases:override"
    REVIEW_READ = "reviews:read"
    REVIEW_WRITE = "reviews:write"
    AUDIT_READ = "audit:read"
    PRODUCT_CONFIG_READ = "product_config:read"
    PRODUCT_CONFIG_WRITE = "product_config:write"
    USERS_MANAGE = "users:manage"
    SCHEMAS_EDIT = "schemas:edit"
    EVALUATION_RUN = "evaluation:run"


# Every legacy `users.role` value mapped to exactly one stable role code.
ROLE_CODES: dict[str, str] = {
    UserRole.APPLICANT.value: RoleCode.APPLICANT.value,
    UserRole.UNDERWRITER.value: RoleCode.UNDERWRITER.value,
    UserRole.ADMINISTRATOR.value: RoleCode.ADMINISTRATOR.value,
}

# Transitional projection from a stable role code back to the legacy role
# value the current web client still renders. Phase 3 replaces it with the
# typed role object served by `GET /auth/me`.
LEGACY_ROLE_VALUES: dict[str, str] = {
    code: legacy for legacy, code in ROLE_CODES.items()
}


class AccessTokenClaims(BaseModel):
    """Verified claims of one strict HS256 access token."""

    sub: UUID
    role: str = Field(min_length=1, max_length=64)
    permissions: tuple[str, ...]
    typ: Literal["access"]
    iat: int
    exp: int
    iss: str = Field(min_length=1)
    aud: str = Field(min_length=1)
    jti: str = Field(min_length=1)
    authz_version: str = Field(min_length=1)


class LoginRequest(BaseModel):
    """Synthetic user login payload."""

    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=512)


class RefreshRequest(BaseModel):
    """Refresh credential rotation payload."""

    refresh_token: str = Field(min_length=1, max_length=512)


class SessionResponse(BaseModel):
    """Legacy bearer session response, kept for the current web client."""

    token: str
    token_type: str = "bearer"
    expires_in: int


class AccessTokenResponse(BaseModel):
    """Access and refresh credentials issued by login or rotation."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_expires_in: int


class RoleSummary(BaseModel):
    """Stable role identity attached to an authenticated user."""

    id: UUID
    code: str


class CurrentUser(BaseModel):
    """Identity and current authorization served by `GET /auth/me`."""

    id: UUID
    email: str
    display_name: str
    role: RoleSummary
    permissions: list[str]


class UserRecord(BaseModel):
    """Administrable user record carrying no credential material."""

    id: UUID
    email: str
    display_name: str
    is_active: bool
    role: RoleSummary | None
    created_at: datetime


class RoleRecord(BaseModel):
    """Configured role with its resolved permission scopes."""

    id: UUID
    code: str
    title: str
    description: str | None
    is_active: bool
    is_system: bool
    permissions: list[str]


class PermissionSummary(BaseModel):
    """One entry of the fixed permission catalogue."""

    code: str
    title: str
    description: str | None


class CreateUserRequest(BaseModel):
    """Administrator request to create one synthetic user."""

    email: str = Field(min_length=3, max_length=320)
    display_name: str = Field(min_length=1, max_length=200)
    password: str = Field(min_length=8, max_length=512)
    role_id: UUID


class UpdateUserRequest(BaseModel):
    """Administrator request to change one user's mutable fields."""

    display_name: str | None = Field(
        default=None, min_length=1, max_length=200
    )
    is_active: bool | None = None
    role_id: UUID | None = None


class CreateRoleRequest(BaseModel):
    """Administrator request to create one configurable role."""

    code: str = Field(min_length=2, max_length=64)
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=500)
    permissions: list[str] = Field(default_factory=list)


class UpdateRoleRequest(BaseModel):
    """Administrator request to change one role and its scope list."""

    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=500)
    is_active: bool | None = None
    permissions: list[str] | None = None
