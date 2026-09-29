"""Persistence models for versioned knowledge and immutable case pins."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    Computed,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column

from underwriteflow.persistence.models import (
    Base,
    IdentifiedRecord,
    TimestampedRecord,
)
from underwriteflow.persistence.vector import Vector


class KnowledgeVersion(IdentifiedRecord, TimestampedRecord, Base):
    """One immutable guideline or regulation version."""

    __tablename__ = "knowledge_versions"

    scope: Mapped[str] = mapped_column(String(32), nullable=False)
    product_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("products.id")
    )
    version: Mapped[str] = mapped_column(String(100), nullable=False)
    content_type: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    source: Mapped[dict] = mapped_column(JSONB, nullable=False)
    validation: Mapped[dict] = mapped_column(JSONB, nullable=False)
    activated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    activated_by_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id")
    )


class KnowledgePassage(IdentifiedRecord, Base):
    """One citable passage belonging to a knowledge version."""

    __tablename__ = "knowledge_passages"

    version_id: Mapped[UUID] = mapped_column(
        ForeignKey("knowledge_versions.id"), nullable=False
    )
    passage_key: Mapped[str] = mapped_column(String(200), nullable=False)
    product_code: Mapped[str | None] = mapped_column(String(100))
    product_lines: Mapped[list] = mapped_column(JSONB, nullable=False)
    topic: Mapped[str] = mapped_column(String(100), nullable=False)
    topic_tags: Mapped[list] = mapped_column(JSONB, nullable=False)
    suggested_tags: Mapped[list] = mapped_column(JSONB, nullable=False)
    limits: Mapped[list] = mapped_column(JSONB, nullable=False)
    thresholds: Mapped[list] = mapped_column(JSONB, nullable=False)
    age_min: Mapped[int | None] = mapped_column(Integer)
    age_max: Mapped[int | None] = mapped_column(Integer)
    sum_assured_min: Mapped[float | None] = mapped_column(Numeric)
    sum_assured_max: Mapped[float | None] = mapped_column(Numeric)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    label: Mapped[str] = mapped_column(String(64), nullable=False)
    source_locator: Mapped[str | None] = mapped_column(String(500))
    search_vector: Mapped[str] = mapped_column(
        TSVECTOR,
        Computed(
            "to_tsvector('english', "
            "coalesce(passage_key, '') || ' ' || "
            "coalesce(topic, '') || ' ' || "
            "coalesce(title, '') || ' ' || "
            "coalesce(body, ''))",
            persisted=True,
        ),
        nullable=True,
    )
    embedding: Mapped[list[float] | None] = mapped_column(Vector(768))


class CaseKnowledgePin(TimestampedRecord, Base):
    """The first active knowledge versions observed by one case."""

    __tablename__ = "case_knowledge_pins"

    case_id: Mapped[UUID] = mapped_column(
        ForeignKey("cases.id"), primary_key=True
    )
    guideline_version_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("knowledge_versions.id")
    )
    regulation_version_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("knowledge_versions.id")
    )


class CaseGuidance(IdentifiedRecord, TimestampedRecord, Base):
    """Stored explanation for one case review cycle."""

    __tablename__ = "case_guidance"
    __table_args__ = (
        UniqueConstraint(
            "case_id",
            "review_cycle",
            "kind",
            name="uq_case_guidance_cycle_kind",
        ),
    )

    case_id: Mapped[UUID] = mapped_column(
        ForeignKey("cases.id"), nullable=False
    )
    review_cycle: Mapped[int] = mapped_column(Integer, nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    body: Mapped[dict] = mapped_column(JSONB, nullable=False)
    citations: Mapped[list] = mapped_column(JSONB, nullable=False)
    provider: Mapped[str | None] = mapped_column(String(50))
    model: Mapped[str | None] = mapped_column(String(200))
    request_hash: Mapped[str | None] = mapped_column(String(64))
