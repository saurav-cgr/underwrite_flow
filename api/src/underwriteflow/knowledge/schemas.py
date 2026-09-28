"""Request and response contracts for administrator knowledge APIs."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class KnowledgeYamlPayload(BaseModel):
    """Accept one guideline corpus document from an administrator."""

    scope: str = "guideline"
    yaml: str = Field(min_length=1)


class ValidationReport(BaseModel):
    """Return deterministic corpus validation results."""

    valid: bool
    issues: list[dict] = Field(default_factory=list)


class KnowledgeVersionResponse(BaseModel):
    """Return one knowledge version without passage text."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    scope: str
    product_code: str | None
    version: str
    status: str
    content_type: str
    passage_count: int
    validation: dict
    activated_at: datetime | None


class KnowledgePreviewPassage(BaseModel):
    """Return one administrator-visible passage and its label."""

    passage_key: str
    title: str
    topic: str
    bands: dict
    label: str
    body: str
    thresholds: list[dict]
    topic_tags: list
    suggested_tags: list
    limits: list


class KnowledgePreviewResponse(BaseModel):
    """Return bounded version metadata and preview passages."""

    version: KnowledgeVersionResponse
    validation: dict
    passages: list[KnowledgePreviewPassage]


class KnowledgeActivationResponse(KnowledgeVersionResponse):
    """Return one activated or retired version."""
