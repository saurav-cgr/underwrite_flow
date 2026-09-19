"""Contract coverage for nontechnical product authoring (US2).

Covers the normalized preview, the administrator-only configuration read and
canonical YAML export, permission enforcement, a corrupt stored payload, and
a YAML export/import round trip.
"""

import psycopg
from fastapi.testclient import TestClient

from fixtures.support import ADMINISTRATOR, APPLICANT, login
from underwriteflow.app import create_app

DATABASE_URL = (
    "postgresql://underwriteflow:synthetic-local-password@"
    "db:5433/underwriteflow"
)


# Build one minimal, valid fictional configuration document.
def product_yaml(code: str, version: str) -> str:
    return f"""
product_code: {code}
title: Synthetic Authoring Product
family: motor
scope: Fictional demonstration only
description: Synthetic authoring configuration
version: {version}
fields:
  - key: vehicle_age
    label: Vehicle age
    type: integer
    required: true
    help_text: Enter a fictional vehicle age.
documents:
  - code: identity_record
    title: Synthetic identity record
    requirement: required
    accepted_types: [application/pdf]
routing_rules:
  - code: standard_review
    condition: {{field: vehicle_age, operator: greater_than, value: 0}}
    route: standard
specialist_labels: [motor inspection]
"""


# Remove one synthetic product and its audit trail after a test.
def remove_generated_product(product_code: str) -> None:
    with psycopg.connect(DATABASE_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "ALTER TABLE audit_events "
                "DISABLE TRIGGER audit_events_append_only"
            )
            try:
                cursor.execute(
                    "DELETE FROM audit_events "
                    "WHERE details ->> 'product_code' = %s",
                    (product_code,),
                )
                cursor.execute(
                    """
                    DELETE FROM rulebook_versions
                    WHERE product_version_id IN (
                        SELECT product_versions.id
                        FROM product_versions
                        JOIN products
                          ON products.id = product_versions.product_id
                        WHERE products.code = %s
                    )
                    """,
                    (product_code,),
                )
                cursor.execute(
                    """
                    DELETE FROM product_versions
                    USING products
                    WHERE product_versions.product_id = products.id
                      AND products.code = %s
                    """,
                    (product_code,),
                )
                cursor.execute(
                    "DELETE FROM products WHERE code = %s",
                    (product_code,),
                )
            finally:
                cursor.execute(
                    "ALTER TABLE audit_events "
                    "ENABLE TRIGGER audit_events_append_only"
                )


# Corrupt one stored configuration payload directly, bypassing validation.
def corrupt_stored_configuration(product_code: str, version: str) -> None:
    with psycopg.connect(DATABASE_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE product_versions
                SET configuration = configuration - 'fields'
                FROM products
                WHERE product_versions.product_id = products.id
                  AND products.code = %s
                  AND product_versions.version = %s
                """,
                (product_code, version),
            )
        connection.commit()


# Import one synthetic configuration and return the parsed response.
def import_version(
    client: TestClient, headers: dict[str, str], code: str, version: str
) -> dict[str, object]:
    response = client.post(
        "/api/v1/products/import",
        json={"yaml_text": product_yaml(code, version)},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    return response.json()


# Verify preview returns the fully normalized configuration, not a summary.
def test_preview_returns_normalized_configuration() -> None:
    with TestClient(create_app()) as client:
        admin = login(client, ADMINISTRATOR)
        response = client.post(
            "/api/v1/products/preview",
            json={"yaml_text": product_yaml("authoring-preview", "v1")},
            headers=admin,
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["status"] == "draft"
        assert body["supported_journeys"] == ["new_business", "renewal"]
        assert body["fields"][0]["key"] == "vehicle_age"
        assert body["fields"][0]["applies_to"] == [
            "new_business",
            "renewal",
        ]
        assert body["documents"][0]["stage"] == "supporting"


# Verify an administrator can read one imported version's configuration.
def test_administrator_can_read_a_version_configuration() -> None:
    code = "authoring-read"
    with TestClient(create_app()) as client:
        admin = login(client, ADMINISTRATOR)
        try:
            import_version(client, admin, code, "v1")
            response = client.get(
                f"/api/v1/products/{code}/versions/v1",
                headers=admin,
            )
            assert response.status_code == 200, response.text
            body = response.json()
            assert body["product_code"] == code
            assert body["version"] == "v1"
        finally:
            remove_generated_product(code)


# Verify an administrator can export one version as canonical YAML.
def test_administrator_can_export_canonical_yaml() -> None:
    code = "authoring-export"
    with TestClient(create_app()) as client:
        admin = login(client, ADMINISTRATOR)
        try:
            import_version(client, admin, code, "v1")
            response = client.get(
                f"/api/v1/products/{code}/versions/v1/export",
                headers=admin,
            )
            assert response.status_code == 200, response.text
            assert response.headers["content-type"].startswith(
                "application/yaml"
            )
            disposition = response.headers["content-disposition"]
            assert "attachment" in disposition
            assert f"{code}-v1.yaml" in disposition
            assert "product_code: " + code in response.text
        finally:
            remove_generated_product(code)


# Verify a non-administrator cannot read or export configuration.
def test_read_and_export_require_administrator_permission() -> None:
    code = "authoring-permission"
    with TestClient(create_app()) as client:
        admin = login(client, ADMINISTRATOR)
        applicant = login(client, APPLICANT)
        try:
            import_version(client, admin, code, "v1")
            read = client.get(
                f"/api/v1/products/{code}/versions/v1",
                headers=applicant,
            )
            export = client.get(
                f"/api/v1/products/{code}/versions/v1/export",
                headers=applicant,
            )
            assert read.status_code == 403
            assert export.status_code == 403
        finally:
            remove_generated_product(code)


# Verify a corrupt stored payload fails safely instead of a server error.
def test_corrupt_stored_configuration_is_reported_safely() -> None:
    code = "authoring-corrupt"
    with TestClient(create_app()) as client:
        admin = login(client, ADMINISTRATOR)
        try:
            import_version(client, admin, code, "v1")
            corrupt_stored_configuration(code, "v1")
            read = client.get(
                f"/api/v1/products/{code}/versions/v1",
                headers=admin,
            )
            export = client.get(
                f"/api/v1/products/{code}/versions/v1/export",
                headers=admin,
            )
            assert read.status_code == 422
            assert export.status_code == 422
        finally:
            remove_generated_product(code)


# Verify exported YAML re-imports as the identical configuration version.
def test_exported_yaml_round_trips_through_import() -> None:
    code = "authoring-roundtrip"
    with TestClient(create_app()) as client:
        admin = login(client, ADMINISTRATOR)
        try:
            imported = import_version(client, admin, code, "v1")
            exported = client.get(
                f"/api/v1/products/{code}/versions/v1/export",
                headers=admin,
            )
            assert exported.status_code == 200, exported.text
            reimported = client.post(
                "/api/v1/products/import",
                json={"yaml_text": exported.text},
                headers=admin,
            )
            assert reimported.status_code == 200, reimported.text
            assert reimported.json()["version"] == imported["version"]
        finally:
            remove_generated_product(code)
