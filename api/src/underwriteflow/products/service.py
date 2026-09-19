"""Validation and lifecycle service for product configurations."""

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import yaml
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from underwriteflow.audit.events import (
    build_audit_event,
    supersedes_details,
    version_details,
)
from underwriteflow.persistence.models import (
    Product,
    ProductVersion,
    RulebookVersion,
)
from underwriteflow.persistence.repositories import AuditRepository
from underwriteflow.products.errors import (
    ProductConfigurationCorruptError,
    ProductConfigurationError,
    ProductConflictError,
)
from underwriteflow.products.reference_documents import (
    ReferenceDocumentMixin,
)
from underwriteflow.products.repository import ProductRepository
from underwriteflow.products.schemas import ProductConfiguration

LOGGER = logging.getLogger(__name__)

__all__ = [
    "ProductConfigurationCorruptError",
    "ProductConfigurationError",
    "ProductConflictError",
    "ProductService",
    "configuration_from_payload",
    "load_configuration",
]

# Report whether one configuration document begins as a JSON object or array.
def looks_like_json(text: str) -> bool:
    return text.lstrip().startswith(("{", "["))

# Summarize one validation failure without echoing submitted configuration.
def validation_reason(error: Exception) -> str:
    if isinstance(error, ValidationError):
        issues = error.errors()
        if issues:
            issue = issues[0]
            location = ".".join(
                str(part) for part in issue.get("loc", ())
            ) or "configuration"
            message = str(issue.get("msg", "")).removeprefix(
                "Value error, "
            )
            return f"{location}: {message}"[:200]
    return "the document is not valid JSON or YAML"

# Re-read one persisted configuration so activation re-validates references.
def configuration_from_payload(
    payload: dict[str, Any],
) -> ProductConfiguration | None:
    try:
        return ProductConfiguration.model_validate(payload)
    except ValidationError:
        return None

# Parse and validate one configuration document submitted as YAML or JSON.
#
# JSON is parsed on its own so a JSON syntax error reports as one, and the
# accepted formats stay explicit rather than relying on YAML happening to be a
# JSON superset.
def load_configuration(text: str) -> ProductConfiguration:
    try:
        raw = (
            json.loads(text)
            if looks_like_json(text)
            else yaml.safe_load(text)
        )
        return ProductConfiguration.model_validate(raw)
    except (
        json.JSONDecodeError,
        yaml.YAMLError,
        TypeError,
        ValidationError,
    ) as error:
        raise ProductConfigurationError(validation_reason(error)) from error

# Produce a stable JSON payload for persistence and hashing.
def configuration_payload(
    configuration: ProductConfiguration,
) -> dict[str, Any]:
    payload = configuration.model_dump(mode="json")
    for check in payload["reconciliations"]:
        if check.get("parameters") is None:
            check.pop("parameters")
    return payload

# Hash normalized configuration content for immutable version identity.
def configuration_hash(configuration: ProductConfiguration) -> str:
    payload = json.dumps(
        configuration_payload(configuration),
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(payload).hexdigest()

# Compare a stored legacy payload to an incoming hash after normalizing both
# through the current schema. A legacy payload gains journey defaults on
# reload, which can change its hash even when its meaning has not changed;
# this lets that case match without ever rewriting the stored hash.
def stored_content_matches(payload: dict[str, Any], content_hash: str) -> bool:
    normalized = configuration_from_payload(payload)
    return normalized is not None and configuration_hash(normalized) == (
        content_hash
    )

class ProductService(ReferenceDocumentMixin):
    """Apply versioned product configuration lifecycle rules."""

    def __init__(
        self,
        repository: ProductRepository | None = None,
        audit_repository: AuditRepository | None = None,
    ) -> None:
        self.repository = repository or ProductRepository()
        self.audit_repository = audit_repository or AuditRepository()
    # Return the fully normalized configuration, plus its summary counts,
    # without persisting it. The counts stay for the existing expert-YAML
    # preview screen; the normalized fields feed the guided builder.
    def preview(self, configuration: ProductConfiguration) -> dict[str, Any]:
        return {
            **configuration_payload(configuration),
            "field_count": len(configuration.fields),
            "document_count": len(configuration.documents),
            "routing_rule_count": len(configuration.routing_rules),
            "reconciliation_count": len(configuration.reconciliations),
        }

    # Read one persisted version's validated configuration.
    async def read_version(
        self, session: AsyncSession, code: str, version: str
    ) -> ProductConfiguration:
        target = await self.repository.find_version(session, code, version)
        if target is None:
            raise ProductConfigurationError("product version not found")
        configuration = configuration_from_payload(target.configuration)
        if configuration is None:
            raise ProductConfigurationCorruptError(
                "stored configuration is no longer valid"
            )
        return configuration

    # Export one persisted version as canonical YAML text.
    async def export_version(
        self, session: AsyncSession, code: str, version: str
    ) -> str:
        configuration = await self.read_version(session, code, version)
        return yaml.safe_dump(
            configuration_payload(configuration), sort_keys=False
        )
    # Import one validated configuration as an immutable draft version.
    async def import_configuration(
        self,
        session: AsyncSession,
        configuration: ProductConfiguration,
        actor_user_id: UUID | None = None,
    ) -> ProductVersion:
        content_hash = configuration_hash(configuration)
        product = await self.repository.find_product(
            session,
            configuration.product_code,
        )
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
            if existing.content_hash != content_hash and not (
                stored_content_matches(existing.configuration, content_hash)
            ):
                raise ProductConfigurationError(
                    "version identity already exists"
                )
            # Never rewrite a legacy stored payload or hash: a schema-default
            # addition can change the normalized hash of semantically
            # unchanged content, and this preserves the original identity.
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
                        rule.model_dump(mode="json")
                        for rule in configuration.routing_rules
                    ],
                    "specialist_labels": configuration.specialist_labels,
                },
                content_hash=content_hash,
            )
        )
        self.audit_repository.append(
            session,
            build_audit_event(
                "configuration_imported",
                {
                    "product_code": configuration.product_code,
                    **version_details(version),
                },
                actor_user_id=actor_user_id,
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
        # Re-validate stored content so a version whose references stopped
        # resolving can never become the active configuration.
        if configuration_from_payload(target.configuration) is None:
            raise ProductConfigurationError(
                "stored configuration references are no longer valid"
            )
        siblings = await self.repository.list_product_versions(
            session,
            product.id,
        )
        for sibling in siblings:
            if sibling.id != target.id and sibling.status == "active":
                sibling.status = "retired"
        # Flush the retirement first: the one-active-version index must never
        # see two active siblings inside the same transaction.
        await session.flush()
        target.status = "active"
        target.activated_at = datetime.now(timezone.utc)
        target.activated_by_user_id = actor_user_id
        product.status = "active"
        previous = await self.audit_repository.latest_event_id(
            session, ("configuration_activated",), product_code=code
        )
        self.audit_repository.append(
            session,
            build_audit_event(
                "configuration_activated",
                {
                    "product_code": code,
                    **version_details(target),
                    **supersedes_details(previous),
                },
                actor_user_id=actor_user_id,
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
        siblings = await self.repository.list_product_versions(
            session,
            product.id,
        )
        other_active = any(
            sibling.status == "active"
            for sibling in siblings
            if sibling.id != target.id
        )
        if not other_active:
            product.status = "draft"
        self.audit_repository.append(
            session,
            build_audit_event(
                "configuration_retired",
                {"product_code": code, **version_details(target)},
                actor_user_id=actor_user_id,
            ),
        )
        await session.commit()
        return target
