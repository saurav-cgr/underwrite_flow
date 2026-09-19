"""Administrator reference-document storage for a product version.

Split out of ``service.py`` to keep that file under the project's 400-line
limit; this mixin expects ``self.repository`` and ``self.audit_repository``
from the combined ``ProductService``.
"""

import logging
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import UploadFile

from underwriteflow.audit.events import build_audit_event, version_details
from underwriteflow.persistence.models import Product, ReferenceDocument
from underwriteflow.products.errors import ProductConfigurationError
from underwriteflow.storage import StorageValidationError, UploadStorage

LOGGER = logging.getLogger(__name__)


class ReferenceDocumentMixin:
    """Add, list, and remove administrator reference documents."""

    # Store one administrator reference document with storage metadata.
    async def add_reference_document(
        self,
        session: AsyncSession,
        code: str,
        version: str,
        upload: UploadFile,
        storage: UploadStorage,
        actor_user_id: UUID,
    ) -> ReferenceDocument:
        product = await self.repository.find_product(session, code)
        target = await self.repository.find_version(session, code, version)
        if product is None or target is None:
            raise ProductConfigurationError("product version not found")
        stored = await storage.save(upload, f"references/{code}/{version}")
        document = ReferenceDocument(
            id=uuid4(),
            product_id=product.id,
            version=version,
            filename=Path(upload.filename or "reference").name,
            content_type=stored.content_type,
            storage_key=stored.storage_key,
            content_hash=stored.content_hash,
            byte_size=stored.byte_size,
            page_count=stored.page_count,
            uploaded_by_user_id=actor_user_id,
        )
        session.add(document)
        self.audit_repository.append(
            session,
            build_audit_event(
                "reference_document_added",
                {
                    "product_code": code,
                    "reference_id": document.id,
                    **version_details(target),
                },
                actor_user_id=actor_user_id,
            ),
        )
        await session.commit()
        return document

    # List administrator reference documents for one product version.
    async def list_reference_documents(
        self,
        session: AsyncSession,
        code: str,
        version: str | None = None,
    ) -> list[ReferenceDocument]:
        statement = (
            select(ReferenceDocument)
            .join(Product, Product.id == ReferenceDocument.product_id)
            .where(Product.code == code)
            .order_by(ReferenceDocument.created_at.desc())
        )
        if version is not None:
            statement = statement.where(ReferenceDocument.version == version)
        return list(await session.scalars(statement))

    # Delete one administrator reference document and its stored file.
    async def remove_reference_document(
        self,
        session: AsyncSession,
        code: str,
        reference_id: UUID,
        storage: UploadStorage,
        actor_user_id: UUID,
    ) -> None:
        document = await session.scalar(
            select(ReferenceDocument)
            .join(Product, Product.id == ReferenceDocument.product_id)
            .where(
                Product.code == code,
                ReferenceDocument.id == reference_id,
            )
        )
        if document is None:
            raise ProductConfigurationError("reference document not found")
        storage_key = document.storage_key
        await session.delete(document)
        self.audit_repository.append(
            session,
            build_audit_event(
                "reference_document_removed",
                {
                    "product_code": code,
                    "product_version": document.version,
                    "reference_id": str(reference_id),
                    "content_hash": document.content_hash,
                },
                actor_user_id=actor_user_id,
            ),
        )
        # Commit first so a failed file removal cannot hide a missing row.
        await session.commit()
        if not storage_key:
            return
        try:
            storage.delete(storage_key)
        except (OSError, StorageValidationError):
            LOGGER.warning(
                "orphaned reference upload retained: %s", storage_key
            )
