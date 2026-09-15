"""Case intake and document persistence rules."""

import logging
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from fastapi import UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from underwriteflow.audit.events import build_audit_event, version_details
from underwriteflow.persistence.models import (
    Case,
    Document,
    Product,
    ProductVersion,
    RulebookVersion,
    Submission,
)
from underwriteflow.persistence.repositories import AuditRepository
from underwriteflow.products.rules import condition_matches
from underwriteflow.products.schemas import (
    ProductConfiguration,
    ProductDocument,
)
from underwriteflow.cases.schemas import CaseCreate
from underwriteflow.storage import StorageValidationError, UploadStorage

LOGGER = logging.getLogger(__name__)

MAX_DOCUMENT_COUNT = 10
MUTABLE_DOCUMENT_STATUSES = frozenset({"new", "needs_information"})


class CaseValidationError(ValueError):
    """Raised when intake data does not satisfy the pinned product."""


# Decide whether one configured document is required for this application.
def document_is_required(
    document: ProductDocument, payload: Mapping[str, Any]
) -> bool:
    if document.requirement == "required":
        return True
    return document.requirement == "conditional" and condition_matches(
        document.condition or {}, payload
    )


# Return the required document codes that are not yet attached to the case.
def missing_document_codes(
    configuration: ProductConfiguration,
    provided_codes: Iterable[str],
    payload: Mapping[str, Any],
) -> list[str]:
    provided = set(provided_codes)
    return sorted(
        document.code
        for document in configuration.documents
        if document_is_required(document, payload)
        and document.code not in provided
    )


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
        if (
            document_is_required(document, application.payload)
            and document.code not in provided_documents
        ):
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
            build_audit_event(
                "case_created",
                {
                    "product_code": application.product_code,
                    **version_details(product_version, rulebook),
                },
                case_id=case.id,
                actor_user_id=applicant_id,
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
        document_code: str,
        actor_user_id: UUID,
    ) -> Document:
        if case.status not in MUTABLE_DOCUMENT_STATUSES:
            raise CaseValidationError(
                "documents cannot change after review starts"
            )
        product_version = await session.scalar(
            select(ProductVersion).where(
                ProductVersion.id == case.product_version_id
            )
        )
        if product_version is None:
            raise CaseValidationError("case configuration is unavailable")
        configuration = ProductConfiguration.model_validate(
            product_version.configuration
        )
        known_codes = {document.code for document in configuration.documents}
        if document_code not in known_codes:
            raise CaseValidationError("unsupported document code")
        count = await session.scalar(
            select(func.count(Document.id)).where(Document.case_id == case.id)
        )
        if count >= MAX_DOCUMENT_COUNT:
            raise CaseValidationError("document count limit exceeded")
        stored = await self.storage.save(upload, case.id)
        document = Document(
            id=uuid4(),
            case_id=case.id,
            document_code=document_code,
            filename=Path(upload.filename or "document").name,
            content_type=stored.content_type,
            storage_key=stored.storage_key,
            content_hash=stored.content_hash,
            byte_size=stored.byte_size,
            page_count=stored.page_count,
        )
        session.add(document)
        self.audit.append(
            session,
            build_audit_event(
                "document_uploaded",
                {
                    "document_id": document.id,
                    "document_code": document_code,
                    "content_hash": stored.content_hash,
                    "byte_size": stored.byte_size,
                },
                case_id=case.id,
                actor_user_id=actor_user_id,
            ),
        )
        await session.commit()
        return document

    # Remove an unlocked document, committing metadata before the stored file.
    async def remove_document(
        self,
        session: AsyncSession,
        case: Case,
        document_id: UUID,
        actor_user_id: UUID,
    ) -> None:
        if case.status not in MUTABLE_DOCUMENT_STATUSES:
            raise CaseValidationError(
                "documents cannot change after review starts"
            )
        document = await session.scalar(
            select(Document).where(
                Document.id == document_id,
                Document.case_id == case.id,
            )
        )
        if document is None:
            raise CaseValidationError("document not found")
        storage_key = document.storage_key
        content_hash = document.content_hash
        await session.delete(document)
        self.audit.append(
            session,
            build_audit_event(
                "document_removed",
                {
                    "document_id": str(document_id),
                    "content_hash": content_hash,
                },
                case_id=case.id,
                actor_user_id=actor_user_id,
            ),
        )
        # Commit first so a failed file removal cannot hide a missing row.
        await session.commit()
        try:
            self.storage.delete(storage_key)
        except (OSError, StorageValidationError):
            # Keep the orphan discoverable so an operator can reclaim it.
            LOGGER.warning("orphaned upload retained: %s", storage_key)
            self.audit.append(
                session,
                build_audit_event(
                    "document_file_orphaned",
                    {
                        "document_id": str(document_id),
                        "storage_key": storage_key,
                    },
                    case_id=case.id,
                    actor_user_id=actor_user_id,
                ),
            )
            await session.commit()
