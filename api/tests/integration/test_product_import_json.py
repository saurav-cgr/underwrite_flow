"""JSON-format product import and reconciliation-source validation.

Split out of ``test_product_import.py`` to keep that file under the
project's 400-line limit.
"""

import json
from uuid import uuid4

import psycopg
from fastapi.testclient import TestClient

from underwriteflow.app import create_app

DATABASE_URL = (
    "postgresql://underwriteflow:synthetic-local-password@"
    "db:5433/underwriteflow"
)


# Remove the synthetic product and audit event created by this test.
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

# Build one fictional JSON configuration carrying a reconciliation check.
def json_configuration(product_code: str) -> dict:
    return {
        "product_code": product_code,
        "title": "Synthetic JSON Configuration",
        "family": "motor",
        "scope": "Fictional demonstration only",
        "description": "Synthetic product configuration",
        "version": "v1",
        "fields": [
            {
                "key": "claimed_ncb_percent",
                "label": "Claimed NCB percent",
                "type": "integer",
                "required": True,
                "help_text": "Enter a fictional claimed NCB percentage.",
            }
        ],
        "documents": [
            {
                "code": "previous_policy",
                "title": "Synthetic previous policy",
                "requirement": "required",
                "accepted_types": ["application/pdf"],
            }
        ],
        "routing_rules": [
            {
                "code": "standard_review",
                "condition": {
                    "field": "claimed_ncb_percent",
                    "operator": "greater_than",
                    "value": 0,
                },
                "route": "standard",
            }
        ],
        "specialist_labels": ["synthetic review"],
        "reconciliations": [
            {
                "code": "motor_ncb_match",
                "kind": "ncb_match",
                "inputs": {
                    "application": "claimed_ncb_percent",
                    "previous_policy": "ncb_percent",
                },
            }
        ],
    }

# Verify an administrator submits JSON through the same YAML lifecycle.
def test_administrator_can_import_json_configuration() -> None:
    product_code = f"synthetic-json-{uuid4().hex}"
    json_text = json.dumps(json_configuration(product_code))
    with TestClient(create_app()) as client:
        login = client.post(
            "/api/v1/auth/session",
            json={
                "email": "administrator@synthetic.test",
                "password": "underwriteflow-demo-administrator",
            },
        )
        headers = {"Authorization": f"Bearer {login.json()['token']}"}
        preview = client.post(
            "/api/v1/products/preview",
            json={"yaml_text": json_text},
            headers=headers,
        )
        imported = client.post(
            "/api/v1/products/import",
            json={"yaml_text": json_text},
            headers=headers,
        )

    assert login.status_code == 200
    assert preview.status_code == 200, preview.text
    assert preview.json()["reconciliation_count"] == 1
    assert preview.json()["reconciliations"] == [
        {
            "code": "motor_ncb_match",
            "kind": "ncb_match",
            "inputs": {
                "application": "claimed_ncb_percent",
                "previous_policy": "ncb_percent",
            },
            "applies_to": ["new_business"],
        }
    ]
    assert imported.status_code == 200, imported.text
    assert imported.json()["status"] == "draft"
    remove_generated_product(product_code)

# Verify a check that names an undeclared source is refused before import.
def test_reconciliation_with_unknown_source_is_refused() -> None:
    product_code = f"synthetic-invalid-{uuid4().hex}"
    payload = json_configuration(product_code)
    payload["reconciliations"][0]["inputs"]["inspection_photo"] = "ncb_percent"
    with TestClient(create_app()) as client:
        login = client.post(
            "/api/v1/auth/session",
            json={
                "email": "administrator@synthetic.test",
                "password": "underwriteflow-demo-administrator",
            },
        )
        headers = {"Authorization": f"Bearer {login.json()['token']}"}
        response = client.post(
            "/api/v1/products/validate",
            json={"yaml_text": json.dumps(payload)},
            headers=headers,
        )

    assert response.status_code == 422, response.text
    detail = response.json()["error"]["message"]
    assert "unknown input sources" in detail
