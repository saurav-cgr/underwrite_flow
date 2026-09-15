"""Validation and lifecycle service for product configurations."""

import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

import yaml
from fastapi import UploadFile
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from underwriteflow.persistence.models import (
    AuditEvent,
    Product,
    ProductVersion,
    ReferenceDocument,
    RulebookVersion,
)
from underwriteflow.persistence.repositories import AuditRepository
from underwriteflow.products.repository import ProductRepository
from underwriteflow.products.schemas import ProductConfiguration
from underwriteflow.storage import StorageValidationError, UploadStorage

LOGGER = logging.getLogger(__name__)


class ProductConfigurationError(ValueError):
    """Raised when product configuration content is invalid or inconsistent."""


class ProductConflictError(ProductConfigurationError):
    """Raised when a concurrent activation change loses its race."""


# Parse and validate one YAML document against the product contract.
def load_configuration(yaml_text: str) -> ProductConfiguration:
    try:
        raw = yaml.safe_load(yaml_text)
        return ProductConfiguration.model_validate(raw)
    except (yaml.YAMLError, TypeError, ValidationError) as error:
        raise ProductConfigurationError("invalid product configuration") from error


# Produce a stable JSON payload for persistence and hashing.
def configuration_payload(configuration: ProductConfiguration) -> dict[str, Any]:
    return configuration.model_dump(mode="json")


# Hash normalized configuration content for immutable version identity.
def configuration_hash(configuration: ProductConfiguration) -> str:
    payload = json.dumps(
        configuration_payload(configuration), sort_keys=True, separators=(",", ":")
    ).encode()
    return hashlib.sha256(payload).hexdigest()


class ProductService:
    """Apply versioned product configuration lifecycle rules."""

    def __init__(
        self,
        repository: ProductRepository | None = None,
        audit_repository: AuditRepository | None = None,
    ) -> None:
        self.repository = repository or ProductRepository()
        self.audit_repository = audit_repository or AuditRepository()

    # Summarize validated configuration impact without persisting it.
    def preview(self, configuration: ProductConfiguration) -> dict[str, Any]:
        return {
            "product_code": configuration.product_code,
            "version": configuration.version,
            "status": configuration.status,
            "field_count": len(configuration.fields),
            "document_count": len(configuration.documents),
            "routing_rule_count": len(configuration.routing_rules),
            "specialist_labels": configuration.specialist_labels,
        }

    # Import one validated configuration as an immutable draft version.
    async def import_configuration(
        self,
        session: AsyncSession,
        configuration: ProductConfiguration,
        actor_user_id: UUID | None = None,
    ) -> ProductVersion:
        content_hash = configuration_hash(configuration)
        product = await self.repository.find_product(session, configuration.product_code)
        if product is None:
            product = Product(
                code=configuration.product_code,
                title=configuration.title,
                family=configuration.family,
                status="draft",
            )
            session.add(product)
            await session.flush()
        elif product.family != configuration.family:
            raise ProductConfigurationError("product family cannot change")
        existing = await self.repository.find_version(
            session, configuration.product_code, configuration.version
        )
        if existing is not None:
            if existing.content_hash != content_hash:
                raise ProductConfigurationError("version identity already exists")
            return existing
        payload = configuration_payload(configuration)
        version = ProductVersion(
            product_id=product.id,
            version=configuration.version,
            configuration=payload,
            content_hash=content_hash,
            status="draft",
        )
        session.add(version)
        await session.flush()
        session.add(
            RulebookVersion(
                product_version_id=version.id,
                version=configuration.version,
                rules={
                    "routing_rules": [
                        rule.model_dump(mode="json") for rule in configuration.routing_rules
                    ],
                    "specialist_labels": configuration.specialist_labels,
                },
                content_hash=content_hash,
            )
        )
        self.audit_repository.append(
            session,
            AuditEvent(
                actor_user_id=actor_user_id,
                event_type="configuration_imported",
                details={
                    "product_code": configuration.product_code,
                    "version": configuration.version,
                    "content_hash": content_hash,
                },
            ),
        )
        await session.commit()
        return version

    # Activate one version and retire its previous active sibling.
    async def activate(
        self,
        session: AsyncSession,
        code: str,
        version: str,
        actor_user_id: UUID,
    ) -> ProductVersion:
        product = await self.repository.find_product_for_update(session, code)
        target = await self.repository.find_version(session, code, version)
        if product is None or target is None:
            raise ProductConfigurationError("product version not found")
        for sibling in await self.repository.list_product_versions(session, product.id):
            if sibling.id != target.id and sibling.status == "active":
                sibling.status = "retired"
        target.status = "active"
        target.activated_at = datetime.now(timezone.utc)
        target.activated_by_user_id = actor_user_id
        product.status = "active"
        self.audit_repository.append(
            session,
            AuditEvent(
                actor_user_id=actor_user_id,
                event_type="configuration_activated",
                details={"product_code": code, "version": version},
            ),
        )
        # The active-version index rejects a second active sibling, so a lost
        # race is reported as a configuration conflict rather than a failure.
        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
            raise ProductConflictError(
                "another version is already active"
            ) from None
        return target

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
            AuditEvent(
                actor_user_id=actor_user_id,
                event_type="reference_document_added",
                details={
                    "product_code": code,
                    "version": version,
                    "content_hash": stored.content_hash,
                    "byte_size": stored.byte_size,
                },
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
            AuditEvent(
                actor_user_id=actor_user_id,
                event_type="reference_document_removed",
                details={
                    "product_code": code,
                    "reference_id": str(reference_id),
                },
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

    # Retire one version and record the administrator action.
    async def retire(
        self,
        session: AsyncSession,
        code: str,
        version: str,
        actor_user_id: UUID,
    ) -> ProductVersion:
        product = await self.repository.find_product(session, code)
        target = await self.repository.find_version(session, code, version)
        if product is None or target is None:
            raise ProductConfigurationError("product version not found")
        target.status = "retired"
        siblings = await self.repository.list_product_versions(session, product.id)
        if not any(sibling.status == "active" for sibling in siblings if sibling.id != target.id):
            product.status = "draft"
        self.audit_repository.append(
            session,
            AuditEvent(
                actor_user_id=actor_user_id,
                event_type="configuration_retired",
                details={"product_code": code, "version": version},
            ),
        )
        await session.commit()
        return target
