"""SQLAlchemy business models for the fresh-schema baseline."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
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

class Role(IdentifiedRecord, TimestampedRecord, Base):
    """Administrator-configurable named permission set."""

    __tablename__ = "roles"

    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(
        default=True, server_default=text("true"), nullable=False
    )
    is_system: Mapped[bool] = mapped_column(
        default=False, server_default=text("false"), nullable=False
    )
    created_by_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id")
    )

class Permission(IdentifiedRecord, TimestampedRecord, Base):
    """Stable scope catalogue enforced by backend dependencies."""

    __tablename__ = "permissions"

    code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500))

class RolePermission(TimestampedRecord, Base):
    """Membership between one role and one permission scope."""

    __tablename__ = "role_permissions"

    role_id: Mapped[UUID] = mapped_column(
        ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True
    )
    permission_id: Mapped[UUID] = mapped_column(
        ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True
    )
    assigned_by_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id")
    )

class UserRoleMapping(TimestampedRecord, Base):
    """Assign exactly one configured role to one user in this MVP."""

    __tablename__ = "user_role_mappings"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    role_id: Mapped[UUID] = mapped_column(
        ForeignKey("roles.id", ondelete="CASCADE"), nullable=False
    )
    assigned_by_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id")
    )

class RefreshSession(IdentifiedRecord, TimestampedRecord, Base):
    """Rotatable refresh credential retained only as a keyed digest."""

    __tablename__ = "refresh_sessions"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    token_digest: Mapped[str] = mapped_column(
        String(128), unique=True, nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    replaced_by_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("refresh_sessions.id")
    )

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
        UniqueConstraint(
            "product_id",
            "version",
            name="uq_product_versions_product_version",
        ),
        Index(
            "uq_product_versions_one_active",
            "product_id",
            unique=True,
            postgresql_where=text("status = 'active'"),
        ),
    )

    product_id: Mapped[UUID] = mapped_column(
        ForeignKey("products.id"),
        nullable=False,
    )
    version: Mapped[str] = mapped_column(String(100), nullable=False)
    configuration: Mapped[dict] = mapped_column(JSONB, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    activated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    activated_by_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id")
    )

class RulebookVersion(IdentifiedRecord, TimestampedRecord, Base):
    """Versioned fictional routing rulebook."""

    __tablename__ = "rulebook_versions"
    __table_args__ = (
        UniqueConstraint(
            "product_version_id",
            "version",
            name="uq_rulebooks_product_version",
        ),
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

    product_id: Mapped[UUID] = mapped_column(
        ForeignKey("products.id"),
        nullable=False,
    )
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    version: Mapped[str] = mapped_column(String(100), nullable=False)
    uploaded_by_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
    )
    content_type: Mapped[str | None] = mapped_column(String(100))
    storage_key: Mapped[str | None] = mapped_column(String(500))
    byte_size: Mapped[int | None] = mapped_column()
    page_count: Mapped[int | None] = mapped_column()

class Case(IdentifiedRecord, TimestampedRecord, Base):
    """Applicant case pinned to product and rulebook versions."""

    __tablename__ = "cases"
    __table_args__ = (
        UniqueConstraint(
            "applicant_user_id",
            "idempotency_key",
            name="uq_cases_applicant_idempotency",
        ),
    )

    applicant_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
    )
    product_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("product_versions.id"), nullable=False
    )
    rulebook_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("rulebook_versions.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    journey_type: Mapped[str] = mapped_column(
        String(32),
        default="new_business",
        server_default=text("'new_business'"),
        nullable=False,
    )
    review_cycle: Mapped[int] = mapped_column(
        default=0, server_default=text("0"), nullable=False
    )
    workflow_thread_id: Mapped[str | None] = mapped_column(
        String(255),
        unique=True,
    )
    idempotency_key: Mapped[str | None] = mapped_column(String(255))

class Submission(IdentifiedRecord, TimestampedRecord, Base):
    """Original structured case submission."""

    __tablename__ = "submissions"

    case_id: Mapped[UUID] = mapped_column(
        ForeignKey("cases.id"),
        nullable=False,
    )
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

class Document(IdentifiedRecord, TimestampedRecord, Base):
    """Uploaded synthetic applicant document metadata."""

    __tablename__ = "documents"

    case_id: Mapped[UUID] = mapped_column(
        ForeignKey("cases.id"),
        nullable=False,
    )
    document_code: Mapped[str | None] = mapped_column(String(100))
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    storage_key: Mapped[str] = mapped_column(
        String(500),
        unique=True,
        nullable=False,
    )
    content_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    byte_size: Mapped[int] = mapped_column(nullable=False)
    page_count: Mapped[int | None] = mapped_column()

class ExtractedField(IdentifiedRecord, TimestampedRecord, Base):
    """Evidence-linked normalized value from a submission or document."""

    __tablename__ = "extracted_fields"

    case_id: Mapped[UUID] = mapped_column(
        ForeignKey("cases.id"),
        nullable=False,
    )
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

    case_id: Mapped[UUID] = mapped_column(
        ForeignKey("cases.id"),
        nullable=False,
    )
    rule_code: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    details: Mapped[dict] = mapped_column(JSONB, nullable=False)
    evidence_locator: Mapped[str | None] = mapped_column(String(500))

class RiskSignal(IdentifiedRecord, TimestampedRecord, Base):
    """Evidence-linked risk-signal observation."""

    __tablename__ = "risk_signals"

    case_id: Mapped[UUID] = mapped_column(
        ForeignKey("cases.id"),
        nullable=False,
    )
    code: Mapped[str] = mapped_column(String(200), nullable=False)
    severity: Mapped[str] = mapped_column(String(50), nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_locator: Mapped[str | None] = mapped_column(String(500))
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)

class Recommendation(IdentifiedRecord, TimestampedRecord, Base):
    """Pre-human triage recommendation."""

    __tablename__ = "recommendations"

    case_id: Mapped[UUID] = mapped_column(
        ForeignKey("cases.id"),
        unique=True,
        nullable=False,
    )
    route: Mapped[str | None] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    summary: Mapped[dict] = mapped_column(JSONB, nullable=False)
    model_identifier: Mapped[str | None] = mapped_column(String(200))
    workflow_version: Mapped[str] = mapped_column(String(100), nullable=False)

class Review(IdentifiedRecord, TimestampedRecord, Base):
    """Human underwriter review decision."""

    __tablename__ = "reviews"

    case_id: Mapped[UUID] = mapped_column(
        ForeignKey("cases.id"),
        nullable=False,
    )
    reviewer_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
    )
    review_cycle: Mapped[int] = mapped_column(
        default=0, server_default=text("0"), nullable=False
    )
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    selected_route: Mapped[str | None] = mapped_column(String(50))
    specialist_label: Mapped[str | None] = mapped_column(String(200))
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

    case_id: Mapped[UUID] = mapped_column(
        ForeignKey("cases.id"),
        nullable=False,
    )
    idempotency_key: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    destination: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
