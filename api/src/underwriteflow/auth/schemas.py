"""Typed authentication contracts."""

from enum import StrEnum

from pydantic import BaseModel, Field


class UserRole(StrEnum):
    """Roles available in the fictional demonstration."""

    APPLICANT = "Applicant"
    UNDERWRITER = "Underwriter"
    ADMINISTRATOR = "Administrator"


class Permission(StrEnum):
    """Backend actions protected by role authorization."""

    CASE_READ = "cases:read"
    CASE_WRITE = "cases:write"
    REVIEW_READ = "reviews:read"
    REVIEW_WRITE = "reviews:write"
    AUDIT_READ = "audit:read"
    PRODUCT_CONFIG_READ = "product_config:read"
    PRODUCT_CONFIG_WRITE = "product_config:write"


class LoginRequest(BaseModel):
    """Synthetic user login payload."""

    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=512)


class SessionResponse(BaseModel):
    """Short-lived bearer session response."""

    token: str
    token_type: str = "bearer"
    expires_in: int
