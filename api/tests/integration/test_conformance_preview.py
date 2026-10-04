"""End-to-end rule conformance preview and activation coverage."""

import psycopg
from fastapi.testclient import TestClient

from fixtures.regulation import (
    listed_entry,
    write_document,
    write_manifest,
)


DATABASE_URL = (
    "postgresql://underwriteflow:synthetic-local-password"
    "@db:5433/underwriteflow"
)


# Remove only this test's synthetic product and its dependent rulebooks.
def remove_product() -> None:
    with psycopg.connect(DATABASE_URL) as connection:
        connection.execute(
            "DELETE FROM rulebook_versions WHERE product_version_id IN ("
            "SELECT id FROM product_versions WHERE product_id = ("
            "SELECT id FROM products WHERE code = %s))",
            ("conformance-life",),
        )
        connection.execute(
            "DELETE FROM product_versions WHERE product_id = ("
            "SELECT id FROM products WHERE code = %s)",
            ("conformance-life",),
        )
        connection.execute(
            "DELETE FROM products WHERE code = %s", ("conformance-life",)
        )
        connection.commit()


# Build two versions whose threshold change is visible in the preview.
def product_yaml(version: str, threshold: int) -> str:
    return f"""
product_code: conformance-life
title: Conformance Life
family: life
scope: Fictional demonstration only
description: Synthetic conformance product
version: {version}
fields:
  - key: requested_cover
    label: Requested cover
    type: number
    required: true
    help_text: Synthetic cover
documents:
  - code: income_record
    title: Synthetic income record
    requirement: conditional
    condition:
      field: requested_cover
      operator: greater_than
      value: {threshold}
    accepted_types: [application/pdf]
routing_rules:
  - code: high_cover_standard
    condition:
      field: requested_cover
      operator: greater_than
      value: {threshold}
    route: standard
specialist_labels: [life review]
"""


# Import and activate one regulation clause with an accepted limit.
def activate_regulation(client: TestClient, admin: dict[str, str], root) -> str:
    write_document(
        root,
        "conformance.pdf",
        ["1. Cover amount\nThis clause limits requested cover."],
    )
    write_manifest(root, [listed_entry(root, "conformance.pdf")])
    imported = client.post(
        "/api/v1/knowledge/regulation/import", headers=admin
    )
    assert imported.status_code == 201, imported.text
    version_id = imported.json()["id"]
    accepted = client.put(
        f"/api/v1/knowledge/versions/{version_id}/passages/"
        "conformance%231/tags",
        json={
            "topic_tags": ["cover-amount"],
            "limits": [
                {
                    "field": "requested_cover",
                    "operator": "greater_than",
                    "value": 0,
                }
            ],
        },
        headers=admin,
    )
    assert accepted.status_code == 200, accepted.text
    activated = client.post(
        f"/api/v1/knowledge/versions/{version_id}/activate",
        headers=admin,
    )
    assert activated.status_code == 200, activated.text
    return version_id


# Verify flags inform preview and never block flagged activation.
def test_conformance_preview_and_activation(
    regulation_client: tuple[TestClient, dict[str, str], object],
) -> None:
    remove_product()
    client, admin, root = regulation_client
    regulation_id = activate_regulation(client, admin, root)
    first = client.post(
        "/api/v1/products/import",
        json={"yaml_text": product_yaml("v1", 5_000_000)},
        headers=admin,
    )
    assert first.status_code == 200, first.text
    activated = client.post(
        "/api/v1/products/conformance-life/activate",
        json={"version": "v1"},
        headers=admin,
    )
    assert activated.status_code == 200, activated.text
    preview = client.post(
        "/api/v1/products/preview",
        json={"yaml_text": product_yaml("v2", 10_000_000)},
        headers=admin,
    )

    assert preview.status_code == 200, preview.text
    body = preview.json()
    assert body["conformance"]["regulation_version"]
    assert body["conformance"]["flags"][0]["rule_code"] == (
        "high_cover_standard"
    )
    assert body["change_impact"]["against_version"] == "v1"
    assert body["change_impact"]["changed_thresholds"][0]["to"] == (
        10_000_000
    )
    second = client.post(
        "/api/v1/products/import",
        json={"yaml_text": product_yaml("v2", 10_000_000)},
        headers=admin,
    )
    assert second.status_code == 200, second.text
    activated = client.post(
        "/api/v1/products/conformance-life/activate",
        json={"version": "v2"},
        headers=admin,
    )
    assert activated.status_code == 200, activated.text
    with psycopg.connect(DATABASE_URL) as connection:
        row = connection.execute(
            "SELECT details FROM audit_events WHERE event_type = %s "
            "AND details ->> 'product_code' = %s "
            "AND details ->> 'version' = %s ORDER BY occurred_at DESC LIMIT 1",
            ("conformance_flags_recorded", "conformance-life", "v2"),
        ).fetchone()
    assert row is not None
    assert row[0]["flag_count"] == 1
    assert row[0]["rule_codes"] == ["high_cover_standard"]
    assert row[0]["flags"] == [
        {
            "rule_code": "high_cover_standard",
            "field": "requested_cover",
            "passage_key": "conformance#1",
            "operator": "greater_than",
            "value": 0,
        }
    ]
    assert regulation_id
    remove_product()
