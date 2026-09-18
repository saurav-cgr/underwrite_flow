"""Typed contracts for local extraction and model-assisted extraction."""

from typing import Any, Literal

from pydantic import BaseModel, Field

ValueType = Literal[
    "text", "integer", "number", "date", "boolean", "enum"
]


class FieldSpecification(BaseModel):
    """One requested field with the value shape the configuration declares."""

    field_key: str = Field(min_length=1, max_length=200)
    value_type: ValueType
    allowed_values: list[str] = Field(default_factory=list, max_length=50)


class ProviderUsage(BaseModel):
    """Token usage an adapter could report, or an unavailable marker."""

    model: str | None = Field(default=None, max_length=200)
    prompt_tokens: int | None = Field(default=None, ge=0)
    completion_tokens: int | None = Field(default=None, ge=0)
    unavailable: bool = True


class DocumentPage(BaseModel):
    """Text extracted from one document page with a stable locator."""

    page_number: int = Field(ge=1)
    text: str
    source_locator: str = Field(min_length=1, max_length=500)


class ExtractionRequest(BaseModel):
    """Untrusted document content and explicit fields requested by the application."""

    document_name: str = Field(min_length=1, max_length=500)
    content: str = Field(max_length=10_000_000)
    requested_fields: list[str] = Field(max_length=50)
    reference_content: str = Field(default="", max_length=100_000)
    field_specifications: list[FieldSpecification] = Field(
        default_factory=list, max_length=50
    )
    pages: list[DocumentPage] = Field(default_factory=list, max_length=200)


class ExtractedField(BaseModel):
    """One normalized value with a source locator and confidence score."""

    field_name: str = Field(min_length=1, max_length=200)
    value: Any
    source_locator: str = Field(min_length=1, max_length=500)
    confidence: float = Field(ge=0, le=1)
    extraction_method: str = "provider"


class ExtractionResult(BaseModel):
    """Schema-validated extraction output from a provider."""

    fields: list[ExtractedField] = Field(default_factory=list, max_length=50)
    warnings: list[str] = Field(default_factory=list, max_length=20)
    usage: ProviderUsage = Field(default_factory=ProviderUsage)
    result_hash: str = Field(default="", max_length=64)
    request_hash: str = Field(default="", max_length=64)


class LocalDocument(BaseModel):
    """Local document text and the method used to obtain it."""

    pages: list[DocumentPage] = Field(min_length=1)
    method: Literal["pdf_text", "ocr"]
