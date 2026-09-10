"""SQLAlchemy business models for the fresh-schema baseline."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base for every business persistence model."""


class IdentifiedRecord:
    """Provide UUID primary keys for business records."""

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)


class TimestampedRecord:
    """Record immutable creation timestamps."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class User(IdentifiedRecord, TimestampedRecord, Base):
    """Authenticated fictional demonstration user."""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(512), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)


class Product(IdentifiedRecord, TimestampedRecord, Base):
    """Supported fictional insurance product."""

    __tablename__ = "products"

    code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    family: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)


class ProductVersion(IdentifiedRecord, TimestampedRecord, Base):
    """Versioned structured product configuration."""

    __tablename__ = "product_versions"
    __table_args__ = (
        UniqueConstraint("product_id", "version", name="uq_product_versions_product_version"),
    )

    product_id: Mapped[UUID] = mapped_column(ForeignKey("products.id"), nullable=False)
    version: Mapped[str] = mapped_column(String(100), nullable=False)
    configuration: Mapped[dict] = mapped_column(JSONB, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    activated_by_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"))


class RulebookVersion(IdentifiedRecord, TimestampedRecord, Base):
    """Versioned fictional routing rulebook."""

    __tablename__ = "rulebook_versions"
    __table_args__ = (
        UniqueConstraint("product_version_id", "version", name="uq_rulebooks_product_version"),
    )

    product_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("product_versions.id"), nullable=False
    )
    version: Mapped[str] = mapped_column(String(100), nullable=False)
    rules: Mapped[dict] = mapped_column(JSONB, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(128), nullable=False)


class ReferenceDocument(IdentifiedRecord, TimestampedRecord, Base):
    """Shared product-reference document metadata."""

    __tablename__ = "reference_documents"

    product_id: Mapped[UUID] = mapped_column(ForeignKey("products.id"), nullable=False)
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    version: Mapped[str] = mapped_column(String(100), nullable=False)
    uploaded_by_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)


class Case(IdentifiedRecord, TimestampedRecord, Base):
    """Applicant case pinned to product and rulebook versions."""

    __tablename__ = "cases"

    applicant_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    product_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("product_versions.id"), nullable=False
    )
    rulebook_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("rulebook_versions.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    workflow_thread_id: Mapped[str | None] = mapped_column(String(255), unique=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(255), unique=True)


class Submission(IdentifiedRecord, TimestampedRecord, Base):
    """Original structured case submission."""

    __tablename__ = "submissions"

    case_id: Mapped[UUID] = mapped_column(ForeignKey("cases.id"), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Document(IdentifiedRecord, TimestampedRecord, Base):
    """Uploaded synthetic applicant document metadata."""

    __tablename__ = "documents"

    case_id: Mapped[UUID] = mapped_column(ForeignKey("cases.id"), nullable=False)
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(500), unique=True, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    byte_size: Mapped[int] = mapped_column(nullable=False)
    page_count: Mapped[int | None] = mapped_column()


class ExtractedField(IdentifiedRecord, TimestampedRecord, Base):
    """Evidence-linked normalized value from a submission or document."""

    __tablename__ = "extracted_fields"

    case_id: Mapped[UUID] = mapped_column(ForeignKey("cases.id"), nullable=False)
    document_id: Mapped[UUID | None] = mapped_column(ForeignKey("documents.id"))
    field_name: Mapped[str] = mapped_column(String(200), nullable=False)
    value: Mapped[dict] = mapped_column(JSONB, nullable=False)
    source_locator: Mapped[str | None] = mapped_column(String(500))
    extraction_method: Mapped[str] = mapped_column(String(50), nullable=False)
    confidence: Mapped[float | None] = mapped_column()
    conflict_status: Mapped[str] = mapped_column(String(50), nullable=False)
    human_verified: Mapped[bool] = mapped_column(default=False, nullable=False)


class Validation(IdentifiedRecord, TimestampedRecord, Base):
    """Deterministic validation outcome."""

    __tablename__ = "validations"

    case_id: Mapped[UUID] = mapped_column(ForeignKey("cases.id"), nullable=False)
    rule_code: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    details: Mapped[dict] = mapped_column(JSONB, nullable=False)
    evidence_locator: Mapped[str | None] = mapped_column(String(500))


class RiskSignal(IdentifiedRecord, TimestampedRecord, Base):
    """Evidence-linked risk-signal observation."""

    __tablename__ = "risk_signals"

    case_id: Mapped[UUID] = mapped_column(ForeignKey("cases.id"), nullable=False)
    code: Mapped[str] = mapped_column(String(200), nullable=False)
    severity: Mapped[str] = mapped_column(String(50), nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_locator: Mapped[str | None] = mapped_column(String(500))
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)


class Recommendation(IdentifiedRecord, TimestampedRecord, Base):
    """Pre-human triage recommendation."""

    __tablename__ = "recommendations"

    case_id: Mapped[UUID] = mapped_column(ForeignKey("cases.id"), unique=True, nullable=False)
    route: Mapped[str | None] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    summary: Mapped[dict] = mapped_column(JSONB, nullable=False)
    model_identifier: Mapped[str | None] = mapped_column(String(200))
    workflow_version: Mapped[str] = mapped_column(String(100), nullable=False)


class Review(IdentifiedRecord, TimestampedRecord, Base):
    """Human underwriter review decision."""

    __tablename__ = "reviews"

    case_id: Mapped[UUID] = mapped_column(ForeignKey("cases.id"), nullable=False)
    reviewer_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    selected_route: Mapped[str | None] = mapped_column(String(50))
    override_reason: Mapped[str | None] = mapped_column(Text)
    reviewed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class AuditEvent(IdentifiedRecord, Base):
    """Append-only inspectable business audit event."""

    __tablename__ = "audit_events"

    case_id: Mapped[UUID | None] = mapped_column(ForeignKey("cases.id"))
    actor_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"))
    event_type: Mapped[str] = mapped_column(String(200), nullable=False)
    details: Mapped[dict] = mapped_column(JSONB, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Handoff(IdentifiedRecord, TimestampedRecord, Base):
    """Idempotent confirmed-route handoff record."""

    __tablename__ = "handoffs"

    case_id: Mapped[UUID] = mapped_column(ForeignKey("cases.id"), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    destination: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
