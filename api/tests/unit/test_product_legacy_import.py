"""Legacy semantic re-import and immutable-hash guards for product import.

Split out of ``test_products.py`` to keep that file under the project's
400-line limit; this suite fails until ``ProductService.import_configuration``
normalizes a legacy stored payload before comparing it against an incoming
configuration hash.
"""

from uuid import uuid4

import pytest

from underwriteflow.persistence.models import Product, ProductVersion
from underwriteflow.products.service import (
    ProductConfigurationError,
    ProductService,
    load_configuration,
)

class FakeSession:
    """Capture service writes without a database connection."""

    def __init__(self) -> None:
        self.added: list[object] = []

    # Capture one model added to the fake transaction.
    def add(self, value: object) -> None:
        self.added.append(value)

    # Complete the fake transaction.
    async def commit(self) -> None:
        return None

class ImportRepository:
    """Return one preset product and existing version for import tests."""

    def __init__(self, product: Product, existing: ProductVersion | None):
        self.product = product
        self.existing = existing

    async def find_product(
        self, session: FakeSession, code: str
    ) -> Product:
        del session, code
        return self.product

    async def find_version(
        self, session: FakeSession, code: str, version: str
    ) -> ProductVersion | None:
        del session, code, version
        return self.existing

# Build one small fictional configuration YAML shared by both scenarios.
def simple_configuration() -> str:
    return """
product_code: synthetic-motor
title: Synthetic Motor
family: motor
scope: Fictional demonstration only
description: Synthetic product configuration
version: v1
fields:
  - key: vehicle_age
    label: Vehicle age
    type: integer
    required: true
    help_text: Enter a fictional vehicle age.
documents:
  - code: synthetic_identity
    title: Synthetic identity record
    requirement: required
    accepted_types: [application/pdf]
routing_rules:
  - code: synthetic_specialist
    condition: {field: vehicle_age, operator: greater_than, value: 12}
    route: specialist
    specialist_label: motor inspection
specialist_labels: [motor inspection]
"""

# Build the legacy stored payload for "v1", stripped of journey keys the
# way a version imported before this feature would have been persisted.
def legacy_stored_payload() -> dict:
    payload = load_configuration(simple_configuration()).model_dump(
        mode="json"
    )
    payload.pop("supported_journeys", None)
    for field in payload["fields"]:
        field.pop("applies_to", None)
    for document in payload["documents"]:
        document.pop("applies_to", None)
        document.pop("required_for", None)
        document.pop("stage", None)
    for rule in payload["routing_rules"]:
        rule.pop("applies_to", None)
    return payload

# Build one product/existing-version pair sharing a common product code.
def product_and_existing(configuration_payload: dict, content_hash: str):
    product = Product(
        id=uuid4(),
        code="synthetic-motor",
        title="Synthetic Motor",
        family="motor",
        status="draft",
    )
    existing = ProductVersion(
        id=uuid4(),
        product_id=product.id,
        version="v1",
        configuration=configuration_payload,
        content_hash=content_hash,
        status="draft",
    )
    return product, existing

# Given a version stored before journey defaults existed, when its
# semantically unchanged YAML is re-imported, then the existing version
# returns unchanged and its original hash is never rewritten.
@pytest.mark.asyncio
async def test_reimporting_unchanged_legacy_configuration_is_idempotent() -> (
    None
):
    configuration = load_configuration(simple_configuration())
    product, existing = product_and_existing(
        legacy_stored_payload(), "legacy-hash-before-journeys"
    )
    service = ProductService(repository=ImportRepository(product, existing))
    session = FakeSession()

    result = await service.import_configuration(session, configuration)

    assert result is existing
    assert result.content_hash == "legacy-hash-before-journeys"
    assert session.added == []

# Given a stored version whose content actually differs, when the same
# version identity is re-imported, then it is still reported as a conflict.
@pytest.mark.asyncio
async def test_reimporting_semantically_different_configuration_conflicts() -> (
    None
):
    configuration = load_configuration(simple_configuration())
    payload = legacy_stored_payload()
    payload["title"] = "A different fictional title"
    product, existing = product_and_existing(payload, "unrelated-hash")
    service = ProductService(repository=ImportRepository(product, existing))
    session = FakeSession()

    with pytest.raises(ProductConfigurationError, match="already exists"):
        await service.import_configuration(session, configuration)
