"""Validation and lifecycle service for product configurations."""

import hashlib
import json
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import yaml
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from underwriteflow.persistence.models import (
    AuditEvent,
    Product,
    ProductVersion,
    RulebookVersion,
)
from underwriteflow.persistence.repositories import AuditRepository
from underwriteflow.products.repository import ProductRepository
from underwriteflow.products.schemas import ProductConfiguration


class ProductConfigurationError(ValueError):
    """Raised when product configuration content is invalid or inconsistent."""


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
        product = await self.repository.find_product(session, code)
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
        await session.commit()
        return target

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
