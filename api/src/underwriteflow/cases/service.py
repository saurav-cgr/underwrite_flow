"""Case intake and document persistence rules."""

from pathlib import Path
from uuid import UUID, uuid4

from fastapi import UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from underwriteflow.persistence.models import (
    AuditEvent,
    Case,
    Document,
    Product,
    ProductVersion,
    RulebookVersion,
    Submission,
)
from underwriteflow.persistence.repositories import AuditRepository
from underwriteflow.products.rules import condition_matches
from underwriteflow.products.schemas import ProductConfiguration
from underwriteflow.cases.schemas import CaseCreate
from underwriteflow.cases.storage import UploadStorage

MAX_DOCUMENT_COUNT = 10
MAX_DOCUMENT_PAGES = 50


class CaseValidationError(ValueError):
    """Raised when intake data does not satisfy the pinned product."""


# Validate required fields and documents against the selected product version.
def validate_application(
    application: CaseCreate, configuration: ProductConfiguration
) -> None:
    if application.product_code != configuration.product_code:
        raise CaseValidationError("product code does not match configuration")
    for field in configuration.fields:
        visible = field.visible_when is None or condition_matches(field.visible_when, application.payload)
        if field.required and visible:
            if field.key not in application.payload or application.payload[field.key] in (None, ""):
                raise CaseValidationError(f"missing field: {field.key}")
        if field.key in application.payload:
            value = application.payload[field.key]
            if field.type == "integer" and (not isinstance(value, int) or isinstance(value, bool)):
                raise CaseValidationError(f"invalid field type: {field.key}")
            if field.type == "number" and (
                not isinstance(value, (int, float)) or isinstance(value, bool)
            ):
                raise CaseValidationError(f"invalid field type: {field.key}")
            if field.type == "boolean" and not isinstance(value, bool):
                raise CaseValidationError(f"invalid field type: {field.key}")
            if field.type == "enum" and value not in field.options:
                raise CaseValidationError(f"invalid field option: {field.key}")
            minimum = field.validation.get("minimum")
            maximum = field.validation.get("maximum")
            try:
                outside_range = (minimum is not None and value < minimum) or (
                    maximum is not None and value > maximum
                )
            except TypeError:
                outside_range = True
            if outside_range:
                raise CaseValidationError(f"invalid field range: {field.key}")
    provided_documents = set(application.document_codes)
    known_documents = {document.code for document in configuration.documents}
    if not provided_documents.issubset(known_documents):
        raise CaseValidationError("unsupported document code")
    for document in configuration.documents:
        required = document.requirement == "required" or (
            document.requirement == "conditional"
            and condition_matches(document.condition or {}, application.payload)
        )
        if required and document.code not in provided_documents:
            raise CaseValidationError(f"missing document: {document.code}")


class CaseService:
    """Persist cases pinned to exact product and rulebook versions."""

    # Configure storage and append-only audit recording for case operations.
    def __init__(self, storage: UploadStorage, audit: AuditRepository | None = None) -> None:
        self.storage = storage
        self.audit = audit or AuditRepository()

    # Create or return an idempotent case for the authenticated applicant.
    async def create_case(
        self, session: AsyncSession, applicant_id: UUID, application: CaseCreate
    ) -> Case:
        existing = await session.scalar(
            select(Case).where(
                Case.applicant_user_id == applicant_id,
                Case.idempotency_key == application.idempotency_key,
            )
        )
        if existing is not None:
            return existing
        product_version = await session.scalar(
            select(ProductVersion)
            .join(Product, Product.id == ProductVersion.product_id)
            .where(
                ProductVersion.status == "active",
                Product.code == application.product_code,
            )
        )
        if product_version is None:
            raise CaseValidationError("active product configuration not found")
        configuration = ProductConfiguration.model_validate(product_version.configuration)
        validate_application(application, configuration)
        rulebook = await session.scalar(
            select(RulebookVersion).where(
                RulebookVersion.product_version_id == product_version.id,
                RulebookVersion.version == product_version.version,
            )
        )
        if rulebook is None:
            raise CaseValidationError("active rulebook not found")
        case_id = uuid4()
        case = Case(
            id=case_id,
            applicant_user_id=applicant_id,
            product_version_id=product_version.id,
            rulebook_version_id=rulebook.id,
            status="new",
            workflow_thread_id=f"case-{case_id}",
            idempotency_key=application.idempotency_key,
        )
        session.add(case)
        await session.flush()
        session.add(
            Submission(
                case_id=case.id,
                payload={
                    "application": application.payload,
                    "document_codes": application.document_codes,
                },
            )
        )
        self.audit.append(
            session,
            AuditEvent(
                case_id=case.id,
                actor_user_id=applicant_id,
                event_type="case_created",
                details={"product_code": application.product_code},
            ),
        )
        await session.commit()
        return case

    # Upload one bounded document and record only safe metadata in PostgreSQL.
    async def add_document(
        self,
        session: AsyncSession,
        case: Case,
        upload: UploadFile,
        page_count: int | None,
        actor_user_id: UUID,
    ) -> Document:
        count = await session.scalar(
            select(func.count(Document.id)).where(Document.case_id == case.id)
        )
        if count >= MAX_DOCUMENT_COUNT:
            raise CaseValidationError("document count limit exceeded")
        if page_count is not None and not 1 <= page_count <= MAX_DOCUMENT_PAGES:
            raise CaseValidationError("document page limit exceeded")
        stored = await self.storage.save(upload, case.id)
        document = Document(
            case_id=case.id,
            filename=Path(upload.filename or "document").name,
            content_type=upload.content_type or "",
            storage_key=stored.storage_key,
            content_hash=stored.content_hash,
            byte_size=stored.byte_size,
            page_count=page_count,
        )
        session.add(document)
        self.audit.append(
            session,
            AuditEvent(
                case_id=case.id,
                actor_user_id=actor_user_id,
                event_type="document_uploaded",
                details={"content_hash": stored.content_hash, "byte_size": stored.byte_size},
            ),
        )
        await session.commit()
        return document
