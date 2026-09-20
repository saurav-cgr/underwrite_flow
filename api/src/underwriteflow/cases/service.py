"""Case intake and document persistence rules."""

import logging
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import UploadFile
from pydantic import ValidationError
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
from underwriteflow.products.schemas import (
    ProductConfiguration,
    filter_configuration_for_journey,
)
from underwriteflow.cases.schemas import ApplicationUpdate, CaseCreate
from underwriteflow.cases.validation import (
    CaseValidationError,
    document_is_required,
    field_is_visible,
    field_specifications,
    missing_document_codes,
    reconciliation_evidence_fields,
    requested_field_keys,
    validate_draft_application,
)
from underwriteflow.storage import StorageValidationError, UploadStorage

__all__ = [
    "CaseService",
    "CaseValidationError",
    "document_is_required",
    "field_is_visible",
    "field_specifications",
    "missing_document_codes",
    "reconciliation_evidence_fields",
    "requested_field_keys",
    "read_stored_configuration",
]

LOGGER = logging.getLogger(__name__)

MAX_DOCUMENT_COUNT = 10
MUTABLE_DOCUMENT_STATUSES = frozenset({"new", "needs_information"})


# Read one stored product configuration or report it as unavailable.
def read_stored_configuration(
    product_version: ProductVersion,
) -> ProductConfiguration:
    try:
        return ProductConfiguration.model_validate(
            product_version.configuration
        )
    except ValidationError:
        # A stored configuration that no longer validates cannot be applied to
        # intake, so the caller is told rather than the request failing open.
        raise CaseValidationError("case configuration is unavailable") from None


class CaseService:
    """Persist cases pinned to exact product and rulebook versions."""

    # Configure storage and append-only audit recording for case operations.
    def __init__(
        self,
        storage: UploadStorage,
        audit: AuditRepository | None = None,
    ) -> None:
        self.storage = storage
        self.audit = audit or AuditRepository()

    # Create or return an idempotent case for the authenticated applicant.
    # `version` is for trusted internal loading of an exact existing
    # configuration version; request intake leaves it unset so only the
    # administrator-activated version is ever selected.
    async def create_case(
        self,
        session: AsyncSession,
        applicant_id: UUID,
        application: CaseCreate,
        version: str | None = None,
    ) -> Case:
        existing = await session.scalar(
            select(Case).where(
                Case.applicant_user_id == applicant_id,
                Case.idempotency_key == application.idempotency_key,
            )
        )
        if existing is not None:
            return existing
        selector = (
            ProductVersion.version == version
            if version is not None
            else ProductVersion.status == "active"
        )
        product_version = await session.scalar(
            select(ProductVersion)
            .join(Product, Product.id == ProductVersion.product_id)
            .where(selector, Product.code == application.product_code)
        )
        if product_version is None:
            raise CaseValidationError("active product configuration not found")
        configuration = read_stored_configuration(product_version)
        if application.journey not in configuration.supported_journeys:
            raise CaseValidationError("unsupported journey")
        filtered = filter_configuration_for_journey(
            configuration, application.journey
        )
        validate_draft_application(
            application.payload, application.document_codes, filtered
        )
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
            journey_type=application.journey,
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
                    "journey": case.journey_type,
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
        configuration = read_stored_configuration(product_version)
        filtered = filter_configuration_for_journey(
            configuration, case.journey_type
        )
        requirement = next(
            (
                item
                for item in filtered.documents
                if item.code == document_code
            ),
            None,
        )
        if requirement is None:
            raise CaseValidationError("unsupported document code")
        count = await session.scalar(
            select(func.count(Document.id)).where(Document.case_id == case.id)
        )
        if count >= MAX_DOCUMENT_COUNT:
            raise CaseValidationError("document count limit exceeded")
        stored = await self.storage.save(
            upload,
            case.id,
            allowed_types=set(requirement.accepted_types),
        )
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
                    "journey": case.journey_type,
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
                    "journey": case.journey_type,
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
                        "journey": case.journey_type,
                    },
                    case_id=case.id,
                    actor_user_id=actor_user_id,
                ),
            )
            await session.commit()

    # Replace an owned, still-mutable case's stored draft answers.
    async def replace_application(
        self,
        session: AsyncSession,
        case: Case,
        application: ApplicationUpdate,
        actor_user_id: UUID,
    ) -> None:
        if case.status not in MUTABLE_DOCUMENT_STATUSES:
            raise CaseValidationError(
                "application cannot change after review starts"
            )
        product_version = await session.scalar(
            select(ProductVersion).where(
                ProductVersion.id == case.product_version_id
            )
        )
        if product_version is None:
            raise CaseValidationError("case configuration is unavailable")
        configuration = read_stored_configuration(product_version)
        filtered = filter_configuration_for_journey(
            configuration, case.journey_type
        )
        validate_draft_application(
            application.payload, application.document_codes, filtered
        )
        submission = await session.scalar(
            select(Submission).where(Submission.case_id == case.id)
        )
        if submission is None:
            raise CaseValidationError("case submission is unavailable")
        submission.payload = {
            "application": application.payload,
            "document_codes": application.document_codes,
        }
        self.audit.append(
            session,
            build_audit_event(
                "application_replaced",
                {
                    "field_keys": sorted(application.payload),
                    "document_codes": sorted(application.document_codes),
                    "journey": case.journey_type,
                },
                case_id=case.id,
                actor_user_id=actor_user_id,
            ),
        )
        await session.commit()
