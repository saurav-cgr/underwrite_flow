import pytest
from uuid import uuid4
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from fixtures.auth import session_for

from underwriteflow.app import create_app
from underwriteflow.auth.dependencies import get_current_session
from underwriteflow.persistence.models import AuditEvent, Product, ProductVersion
from underwriteflow.products.schemas import ProductConfiguration
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

    # Provide generated identifiers for pending product records.
    async def flush(self) -> None:
        return None

    # Complete the fake transaction.
    async def commit(self) -> None:
        return None


class ConflictSession(FakeSession):
    """Represent a commit that loses the concurrent activation race."""

    # Fail the commit the way the active-version index does.
    async def commit(self) -> None:
        raise IntegrityError("SELECT 1", {}, Exception("synthetic conflict"))

    # Accept the rollback issued after a lost race.
    async def rollback(self) -> None:
        return None


class FakeRepository:
    """Return one product with a replaceable active version."""

    def __init__(self, product: Product, target: ProductVersion, active: ProductVersion) -> None:
        self.product = product
        self.target = target
        self.active = active
        self.locked: list[str] = []

    # Return the configured product for lifecycle tests.
    async def find_product(self, session: FakeSession, code: str) -> Product:
        del session, code
        return self.product

    # Return the configured product while recording the row-lock request.
    async def find_product_for_update(
        self, session: FakeSession, code: str
    ) -> Product:
        del session
        self.locked.append(code)
        return self.product

    # Return the selected target version for lifecycle tests.
    async def find_version(
        self, session: FakeSession, code: str, version: str
    ) -> ProductVersion:
        del session, code
        return self.target if version == self.target.version else self.active

    # Return all sibling versions for activation replacement.
    async def list_product_versions(
        self, session: FakeSession, product_id: object
    ) -> list[ProductVersion]:
        del session, product_id
        return [self.active, self.target]


# Verify a structured fictional YAML product loads into a typed configuration.
def test_load_configuration_preserves_version_identity() -> None:
    configuration = load_configuration(
        """
product_code: synthetic-motor
title: Synthetic Motor
family: motor
scope: Fictional demonstration only
description: Synthetic product configuration
version: v1
status: draft
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
    )

    assert isinstance(configuration, ProductConfiguration)
    assert configuration.product_code == "synthetic-motor"
    assert configuration.version == "v1"


# Verify incomplete configurations cannot enter the product store.
def test_invalid_configuration_is_rejected() -> None:
    with pytest.raises(ProductConfigurationError):
        load_configuration("product_code: incomplete\n")


# Verify activation retires the old version and records an audit event.
@pytest.mark.asyncio
async def test_activation_replaces_active_version() -> None:
    product_id = uuid4()
    product = Product(
        id=product_id, code="synthetic-motor", title="Synthetic Motor", family="motor", status="active"
    )
    active = ProductVersion(
        id=uuid4(), product_id=product_id, version="v1", configuration={}, content_hash="one", status="active"
    )
    target = ProductVersion(
        id=uuid4(), product_id=product_id, version="v2", configuration={}, content_hash="two", status="draft"
    )
    session = FakeSession()
    repository = FakeRepository(product, target, active)
    service = ProductService(repository=repository)

    result = await service.activate(session, "synthetic-motor", "v2", uuid4())

    assert result is target
    assert repository.locked == ["synthetic-motor"]
    assert active.status == "retired"
    assert target.status == "active"
    assert any(
        isinstance(event, AuditEvent) and event.event_type == "configuration_activated"
        for event in session.added
    )


# Verify a lost activation race becomes a typed configuration conflict.
@pytest.mark.asyncio
async def test_activation_reports_a_lost_concurrent_race() -> None:
    product_id = uuid4()
    product = Product(
        id=product_id,
        code="synthetic-motor",
        title="Synthetic Motor",
        family="motor",
        status="active",
    )
    active = ProductVersion(
        id=uuid4(),
        product_id=product_id,
        version="v1",
        configuration={},
        content_hash="one",
        status="active",
    )
    target = ProductVersion(
        id=uuid4(),
        product_id=product_id,
        version="v2",
        configuration={},
        content_hash="two",
        status="draft",
    )
    service = ProductService(repository=FakeRepository(product, target, active))

    with pytest.raises(ProductConfigurationError, match="already active"):
        await service.activate(
            ConflictSession(), "synthetic-motor", "v2", uuid4()
        )


# Verify only administrators can validate product configuration.
def test_product_validation_is_administrator_only() -> None:
    app = create_app()

    # Supply a synthetic applicant identity to the authorization dependency.
    def applicant_session() -> dict[str, object]:
        return session_for("applicant")

    app.dependency_overrides[get_current_session] = applicant_session
    response = TestClient(app).post(
        "/api/v1/products/validate",
        json={"yaml_text": "product_code: incomplete"},
    )

    assert response.status_code == 403


# Verify administrators can validate a well-formed product without persistence.
def test_administrator_can_validate_product() -> None:
    app = create_app()

    # Supply a synthetic administrator identity to the authorization dependency.
    def administrator_session() -> dict[str, object]:
        return session_for("administrator")

    app.dependency_overrides[get_current_session] = administrator_session
    response = TestClient(app).post(
        "/api/v1/products/validate",
        json={"yaml_text": """
product_code: synthetic-motor
title: Synthetic Motor
family: motor
scope: Fictional demonstration only
description: Synthetic product configuration
version: v1
fields: [{key: age, label: Age, type: integer, help_text: Synthetic age}]
documents: [{code: identity, title: Identity, requirement: required, accepted_types: [application/pdf]}]
routing_rules:
  - code: standard
    condition: {field: age, operator: greater_than, value: 0}
    route: standard
specialist_labels: [synthetic review]
"""},
    )

    assert response.status_code == 200
    assert response.json() == {"product_code": "synthetic-motor", "version": "v1"}


# Verify a configuration cannot advertise an unsupported content type.
def test_configuration_rejects_unsupported_content_types() -> None:
    with pytest.raises(ProductConfigurationError):
        load_configuration(
            """
product_code: synthetic-motor
title: Synthetic Motor
family: motor
scope: Fictional demonstration only
description: Synthetic product configuration
version: v1
fields:
  - key: age
    label: Age
    type: integer
    required: true
    help_text: Synthetic age
documents:
  - code: identity
    title: Identity
    requirement: required
    accepted_types: [text/plain]
routing_rules:
  - code: standard
    condition: {field: age, operator: greater_than, value: 0}
    route: standard
specialist_labels: [synthetic review]
"""
        )
