import psycopg
from fastapi.testclient import TestClient
from uuid import uuid4

from underwriteflow.app import create_app


DATABASE_URL = (
    "postgresql://underwriteflow:synthetic-local-password@"
    "db:5433/underwriteflow"
)


# Remove the synthetic product and audit event created by this integration test.
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


# Verify Compose bootstrap imports all three fictional product versions.
def test_bootstrap_imports_builtin_products() -> None:
    connection = psycopg.connect(DATABASE_URL)
    with connection, connection.cursor() as cursor:
        cursor.execute("SELECT code FROM products ORDER BY code")
        products = [row[0] for row in cursor.fetchall()]
        cursor.execute(
            "SELECT COUNT(*) FROM product_versions WHERE status = 'draft'"
        )
        draft_count = cursor.fetchone()[0]

    assert products == [
        "health-individual-family-floater",
        "life-individual-term",
        "motor-private-car",
    ]
    assert draft_count == 3


# Verify the additive migration inserts all fictional demo identities.
def test_migration_inserts_demo_accounts() -> None:
    connection = psycopg.connect(
        "postgresql://underwriteflow:synthetic-local-password@"
        "db:5433/underwriteflow"
    )
    with connection, connection.cursor() as cursor:
        cursor.execute(
            "SELECT email, role, is_active FROM users "
            "WHERE email LIKE %s ORDER BY email",
            ("%synthetic.test",),
        )
        accounts = cursor.fetchall()

    assert accounts == [
        ("administrator@synthetic.test", "Administrator", True),
        ("applicant@synthetic.test", "Applicant", True),
        ("underwriter@synthetic.test", "Underwriter", True),
    ]


# Verify only administrators can browse all configured product versions.
def test_administrator_can_list_products_for_configuration() -> None:
    with TestClient(create_app()) as client:
        admin_login = client.post(
            "/api/v1/auth/session",
            json={
                "email": "administrator@synthetic.test",
                "password": "underwriteflow-demo-administrator",
            },
        )
        applicant_login = client.post(
            "/api/v1/auth/session",
            json={
                "email": "applicant@synthetic.test",
                "password": "underwriteflow-demo-applicant",
            },
        )
        admin_response = client.get(
            "/api/v1/products",
            headers={"Authorization": f"Bearer {admin_login.json()['token']}"},
        )
        applicant_response = client.get(
            "/api/v1/products",
            headers={
                "Authorization": f"Bearer {applicant_login.json()['token']}"
            },
        )

    assert admin_login.status_code == 200
    assert applicant_login.status_code == 200
    assert admin_response.status_code == 200
    assert [item["product_code"] for item in admin_response.json()] == [
        "health-individual-family-floater",
        "life-individual-term",
        "motor-private-car",
    ]
    assert applicant_response.status_code == 403


# Verify administrators can validate, preview, and import a draft via the API.
def test_administrator_can_prepare_product_configuration() -> None:
    product_code = f"synthetic-config-{uuid4().hex}"
    yaml_text = f"""
product_code: {product_code}
title: Synthetic Configuration
family: motor
scope: Fictional demonstration only
description: Synthetic product configuration
version: v1
fields:
  - key: vehicle_age
    label: Vehicle age
    type: integer
    help_text: Enter a fictional vehicle age.
documents:
  - code: identity_record
    title: Synthetic identity record
    requirement: required
    accepted_types: [application/pdf]
routing_rules:
  - code: standard_review
    condition: {{field: vehicle_age}}
    route: standard
specialist_labels: [synthetic review]
"""
    with TestClient(create_app()) as client:
        login = client.post(
            "/api/v1/auth/session",
            json={
                "email": "administrator@synthetic.test",
                "password": "underwriteflow-demo-administrator",
            },
        )
        headers = {"Authorization": f"Bearer {login.json()['token']}"}
        validate_response = client.post(
            "/api/v1/products/validate",
            json={"yaml_text": yaml_text},
            headers=headers,
        )
        preview_response = client.post(
            "/api/v1/products/preview",
            json={"yaml_text": yaml_text},
            headers=headers,
        )
        import_response = client.post(
            "/api/v1/products/import",
            json={"yaml_text": yaml_text},
            headers=headers,
        )
        history_response = client.get(
            f"/api/v1/products/{product_code}/history",
            headers=headers,
        )

    assert login.status_code == 200
    assert validate_response.json() == {
        "product_code": product_code,
        "version": "v1",
    }
    assert preview_response.json()["field_count"] == 1
    assert preview_response.json()["document_count"] == 1
    assert import_response.json()["status"] == "draft"
    assert history_response.json()[0]["version"] == "v1"
    remove_generated_product(product_code)
