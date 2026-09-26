"""Draft visibility, activation visibility, and case pinning for US2.

Verifies the administrator-authored lifecycle an applicant and an existing
case both depend on: a draft stays invisible, an activated version appears,
and an existing case keeps its pinned version after a successor activates.
"""

from uuid import UUID, uuid4

import psycopg
from fastapi.testclient import TestClient

from fixtures.records import remove_case
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
title: Synthetic Lifecycle Product
family: motor
scope: Fictional demonstration only
description: Synthetic lifecycle configuration
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


# Import one synthetic configuration and return its lifecycle status.
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
def activate_version(
    client: TestClient, headers: dict[str, str], code: str, version: str
) -> int:
    response = client.post(
        f"/api/v1/products/{code}/activate",
        json={"version": version},
        headers=headers,
    )
    return response.status_code


# Report whether one product code appears in the applicant catalogue.
def in_catalogue(
    client: TestClient, headers: dict[str, str], code: str
) -> bool:
    response = client.get("/api/v1/products/catalog", headers=headers)
    assert response.status_code == 200, response.text
    return any(item["product_code"] == code for item in response.json())


# Create one applicant-owned case for the given product and return its id.
def create_case(client: TestClient, headers: dict[str, str], code: str) -> str:
    response = client.post(
        "/api/v1/cases",
        json={
            "product_code": code,
            "idempotency_key": str(uuid4()),
            "payload": {"vehicle_age": 5},
            "document_codes": ["identity_record"],
        },
        headers=headers,
    )
    assert response.status_code == 200, response.text
    return response.json()["id"]


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


# Remove one synthetic product, its versions, case, and audit trail.
def remove_product(code: str, case_id: str = "") -> None:
    if case_id:
        remove_case(UUID(case_id))
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
                    "ALTER TABLE audit_events "
                    "ENABLE TRIGGER audit_events_append_only"
                )


# Verify a freshly imported draft never appears in the applicant catalogue.
def test_draft_version_is_hidden_from_applicant_catalogue() -> None:
    code = f"lifecycle-draft-{uuid4().hex[:8]}"
    with TestClient(create_app()) as client:
        admin = login(client, ADMINISTRATOR)
        applicant = login(client, APPLICANT)
        try:
            assert import_version(client, admin, code, "v1") == "draft"
            assert in_catalogue(client, applicant, code) is False
        finally:
            remove_product(code)


# Verify activation makes a version visible to the applicant catalogue.
def test_activated_version_appears_in_applicant_catalogue() -> None:
    code = f"lifecycle-active-{uuid4().hex[:8]}"
    with TestClient(create_app()) as client:
        admin = login(client, ADMINISTRATOR)
        applicant = login(client, APPLICANT)
        try:
            import_version(client, admin, code, "v1")
            assert activate_version(client, admin, code, "v1") == 200
            assert in_catalogue(client, applicant, code) is True
        finally:
            remove_product(code)


# Verify an existing case stays pinned once a successor version activates.
def test_existing_case_stays_pinned_after_successor_activates() -> None:
    code = f"lifecycle-pin-{uuid4().hex[:8]}"
    case_id = ""
    with TestClient(create_app()) as client:
        admin = login(client, ADMINISTRATOR)
        applicant = login(client, APPLICANT)
        try:
            import_version(client, admin, code, "v1")
            activate_version(client, admin, code, "v1")
            case_id = create_case(client, applicant, code)
            assert pinned_version(case_id) == "v1"

            import_version(client, admin, code, "v2")
            assert activate_version(client, admin, code, "v2") == 200
            assert pinned_version(case_id) == "v1"
        finally:
            remove_product(code, case_id)
