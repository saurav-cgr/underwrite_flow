"""Activation races and exact case pinning for synthetic product versions."""

from concurrent.futures import ThreadPoolExecutor
from uuid import UUID, uuid4

import psycopg
from fastapi.testclient import TestClient
from fixtures.records import remove_case

from underwriteflow.app import create_app

DATABASE_URL = (
    "postgresql://underwriteflow:synthetic-local-password@"
    "db:5433/underwriteflow"
)

ADMIN_EMAIL = "administrator@synthetic.test"
ADMIN_PASSWORD = "underwriteflow-demo-administrator"

APPLICANT_EMAIL = "applicant@synthetic.test"
APPLICANT_PASSWORD = "underwriteflow-demo-applicant"


# Build one fictional product version with a configured asset check.
def product_yaml(code: str, version: str) -> str:
    return f"""
product_code: {code}
title: Synthetic Pinned Product
family: motor
scope: Fictional demonstration only
description: Synthetic pinning configuration
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
  - code: vehicle_record
    title: Synthetic vehicle record
    requirement: required
    accepted_types: [application/pdf]
routing_rules:
  - code: standard_review
    condition: {{field: vehicle_age, operator: greater_than, value: 0}}
    route: standard
specialist_labels: [motor inspection]
reconciliations:
  - code: pinned_asset_match
    kind: asset_match
    inputs:
      identity_record: registration_number
      vehicle_record: registration_number
"""


# Log in one fictional demo identity and return bearer headers.
def login(client: TestClient, email: str, password: str) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/session",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['token']}"}


# Import one fictional product version and return its lifecycle status.
def import_version(
    client: TestClient, headers: dict[str, str], code: str, version: str
) -> str:
    response = client.post(
        "/api/v1/products/import",
        json={"yaml_text": product_yaml(code, version)},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    return response.json()["status"]


# Activate one imported version and return the response status code.
def activate_version(code: str, version: str) -> int:
    with TestClient(create_app()) as client:
        headers = login(client, ADMIN_EMAIL, ADMIN_PASSWORD)
        response = client.post(
            f"/api/v1/products/{code}/activate",
            json={"version": version},
            headers=headers,
        )
    return response.status_code


# Read every currently active version of one synthetic product.
def active_versions(code: str) -> list[str]:
    with psycopg.connect(DATABASE_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT product_versions.version
                FROM product_versions
                JOIN products ON products.id = product_versions.product_id
                WHERE products.code = %s
                  AND product_versions.status = 'active'
                ORDER BY product_versions.version
                """,
                (code,),
            )
            return [row[0] for row in cursor.fetchall()]


# Read the product version one case stays pinned to.
def pinned_version(case_id: str) -> str:
    with psycopg.connect(DATABASE_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT product_versions.version
                FROM cases
                JOIN product_versions
                  ON product_versions.id = cases.product_version_id
                WHERE cases.id = %s
                """,
                (case_id,),
            )
            return cursor.fetchone()[0]


# Remove one synthetic product, its versions, and its configuration audit.
def remove_product(code: str) -> None:
    with psycopg.connect(DATABASE_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "ALTER TABLE audit_events DISABLE TRIGGER "
                "audit_events_append_only"
            )
            try:
                cursor.execute(
                    "DELETE FROM audit_events "
                    "WHERE details ->> 'product_code' = %s",
                    (code,),
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
                    (code,),
                )
                cursor.execute(
                    """
                    DELETE FROM product_versions
                    USING products
                    WHERE product_versions.product_id = products.id
                      AND products.code = %s
                    """,
                    (code,),
                )
                cursor.execute(
                    "DELETE FROM products WHERE code = %s", (code,)
                )
            finally:
                cursor.execute(
                    "ALTER TABLE audit_events ENABLE TRIGGER "
                    "audit_events_append_only"
                )


# Verify two racing activations still leave exactly one active version.
def test_concurrent_activation_keeps_one_active_version() -> None:
    code = f"synthetic-race-{uuid4().hex}"
    try:
        with TestClient(create_app()) as client:
            headers = login(client, ADMIN_EMAIL, ADMIN_PASSWORD)
            assert import_version(client, headers, code, "v1") == "draft"
            assert import_version(client, headers, code, "v2") == "draft"

        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(
                pool.map(
                    lambda version: activate_version(code, version),
                    ("v1", "v2"),
                )
            )

        active = active_versions(code)
        assert set(outcomes) <= {200, 409}
        assert 200 in outcomes
        assert len(active) == 1
    finally:
        remove_product(code)


# Verify a newer active version never repins an existing case.
def test_newer_active_version_does_not_repin_existing_case() -> None:
    code = f"synthetic-pin-{uuid4().hex}"
    case_id = ""
    try:
        with TestClient(create_app()) as client:
            admin = login(client, ADMIN_EMAIL, ADMIN_PASSWORD)
            assert import_version(client, admin, code, "v1") == "draft"

        assert activate_version(code, "v1") == 200

        with TestClient(create_app()) as client:
            applicant = login(client, APPLICANT_EMAIL, APPLICANT_PASSWORD)
            created = client.post(
                "/api/v1/cases",
                json={
                    "product_code": code,
                    "idempotency_key": str(uuid4()),
                    "payload": {"vehicle_age": 5},
                    "document_codes": [
                        "identity_record",
                        "vehicle_record",
                    ],
                },
                headers=applicant,
            )
            assert created.status_code == 200, created.text
            case_id = created.json()["id"]

            pinned = client.get(
                f"/api/v1/cases/{case_id}/configuration",
                headers=applicant,
            )
            assert pinned.json()["product_version"] == "v1"

        with TestClient(create_app()) as client:
            admin = login(client, ADMIN_EMAIL, ADMIN_PASSWORD)
            assert import_version(client, admin, code, "v2") == "draft"

        assert activate_version(code, "v2") == 200

        assert active_versions(code) == ["v2"]
        assert pinned_version(case_id) == "v1"

        with TestClient(create_app()) as client:
            applicant = login(client, APPLICANT_EMAIL, APPLICANT_PASSWORD)
            unchanged = client.get(
                f"/api/v1/cases/{case_id}/configuration",
                headers=applicant,
            )
            assert unchanged.json()["product_version"] == "v1"
    finally:
        if case_id:
            remove_case(UUID(case_id))
        remove_product(code)
