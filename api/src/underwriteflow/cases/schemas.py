"""Typed case intake and document response contracts."""

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from underwriteflow.products.journey import DocumentStage, JourneyType


class CaseCreate(BaseModel):
    """Synthetic application intake payload.

    A draft may be created with an incomplete payload; only ``submit``
    enforces every journey-required field and document.
    """

    product_code: str = Field(min_length=1, max_length=100)
    idempotency_key: str = Field(min_length=1, max_length=255)
    journey: JourneyType = "new_business"
    payload: dict[str, Any] = Field(default_factory=dict)
    document_codes: list[str] = Field(default_factory=list, max_length=10)


class ApplicationUpdate(BaseModel):
    """Owner-only replacement of a mutable case's stored draft answers."""

    payload: dict[str, Any] = Field(default_factory=dict)
    document_codes: list[str] = Field(default_factory=list, max_length=10)


class CaseResponse(BaseModel):
    """Safe case identity and pinned configuration response."""

    id: UUID
    product_code: str
    product_version: str
    rulebook_version: str
    status: str
    journey: JourneyType


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


class CaseFieldResponse(BaseModel):
    """One applicant-visible product field for a pinned case."""

    key: str
    label: str
    type: str
    required: bool
    help_text: str
    validation: dict[str, Any]
    options: list[str]
    visible_when: dict[str, Any] | None


class CaseDocumentResponse(BaseModel):
    """One document requirement resolved against the application."""

    code: str
    title: str
    requirement: str
    required: bool
    accepted_types: list[str]
    condition: dict[str, Any] | None
    stage: DocumentStage


class CaseConfigurationResponse(BaseModel):
    """Pinned configuration and resolved requirements for one case."""

    case_id: UUID
    product_code: str
    product_version: str
    rulebook_version: str
    journey: JourneyType
    application: dict[str, Any]
    fields: list[CaseFieldResponse]
    documents: list[CaseDocumentResponse]
