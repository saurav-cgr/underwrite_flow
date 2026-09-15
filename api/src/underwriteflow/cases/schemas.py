"""Typed case intake and document response contracts."""

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class CaseCreate(BaseModel):
    """Synthetic application intake payload."""

    product_code: str = Field(min_length=1, max_length=100)
    idempotency_key: str = Field(min_length=1, max_length=255)
    payload: dict[str, Any]
    document_codes: list[str] = Field(default_factory=list, max_length=10)


class CaseResponse(BaseModel):
    """Safe case identity and pinned configuration response."""

    id: UUID
    product_code: str
    product_version: str
    rulebook_version: str
    status: str


class SubmitResponse(BaseModel):
    """Submission result with the pending human-review recommendation."""

    id: UUID
    status: str
    recommendation: dict[str, Any]


class DocumentResponse(BaseModel):
    """Safe uploaded-document metadata response."""

    id: UUID
    document_code: str | None
    filename: str
    content_type: str
    byte_size: int
    content_hash: str
    page_count: int | None
