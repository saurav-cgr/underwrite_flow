"""Append-only audit events carry the full decision and provenance chain."""

from uuid import uuid4

import psycopg
from fastapi.testclient import TestClient
from fixtures.synthetic_pdf import (
    IDENTITY_ONLY_LINES,
    MOTOR_EVIDENCE_LINES,
    text_pdf,
)

from underwriteflow.app import create_app
from underwriteflow.audit.events import (
    MAX_ITEMS,
    MAX_STRING_CHARS,
    SENSITIVE_KEY_PATTERN,
)
from underwriteflow.config import Settings

DATABASE_URL = (
    "postgresql://underwriteflow:synthetic-local-password@"
    "db:5433/underwriteflow"
)

APPLICANT = ("applicant@synthetic.test", "underwriteflow-demo-applicant")
UNDERWRITER = ("underwriter@synthetic.test", "underwriteflow-demo-underwriter")
ADMIN = (
    "administrator@synthetic.test",
    "underwriteflow-demo-administrator",
)


# Set one built-in synthetic product active for the audit journey.
def set_motor_status(status: str) -> None:
    with psycopg.connect(DATABASE_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE product_versions
                SET status = %s
                WHERE product_id = (SELECT id FROM products WHERE code = %s)
                """,
                (status, "motor-private-car"),
            )
            cursor.execute(
                "UPDATE products SET status = %s WHERE code = %s",
                (status, "motor-private-car"),
            )


# Log in one fictional demo role and return bearer headers.
def login(client: TestClient, credentials: tuple[str, str]) -> dict[str, str]:
    email, password = credentials
    response = client.post(
        "/api/v1/auth/session",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['token']}"}


# Read the sanitized audit trail for one case keyed by event type.
def audit_by_type(
    client: TestClient, case_id: str, headers: dict[str, str]
) -> dict:
    response = client.get(f"/api/v1/audit/cases/{case_id}", headers=headers)
    assert response.status_code == 200, response.text
    return {event["event_type"]: event["details"] for event in response.json()}


# Verify the audit trail records identity, provenance, decisions, and handoff.
def test_audit_events_record_the_full_decision_chain() -> None:
    set_motor_status("active")
    try:
        with TestClient(
            create_app(Settings(generation_provider="fake"))
        ) as client:
            applicant = login(client, APPLICANT)
            underwriter = login(client, UNDERWRITER)
            admin = login(client, ADMIN)
            created = client.post(
                "/api/v1/cases",
                json={
                    "product_code": "motor-private-car",
                    "idempotency_key": str(uuid4()),
                    "payload": {
                        "vehicle_age": 2,
                        "vehicle_use": "personal",
                        "prior_claims": 0,
                    },
                    "document_codes": ["identity_record", "vehicle_record"],
                },
                headers=applicant,
            )
            assert created.status_code == 200, created.text
            case_id = created.json()["id"]

            for code, lines in (
                ("identity_record", IDENTITY_ONLY_LINES),
                ("vehicle_record", MOTOR_EVIDENCE_LINES),
            ):
                uploaded = client.post(
                    f"/api/v1/cases/{case_id}/documents",
                    files={
                        "document": (
                            "synthetic.pdf",
                            text_pdf(lines),
                            "application/pdf",
                        )
                    },
                    data={"document_code": code},
                    headers=applicant,
                )
                assert uploaded.status_code == 200, uploaded.text

            submitted = client.post(
                f"/api/v1/cases/{case_id}/submit", headers=applicant
            )
            assert submitted.status_code == 200, submitted.text
            assert client.post(
                f"/api/v1/reviews/{case_id}/start", headers=underwriter
            ).status_code == 200
            assert client.post(
                f"/api/v1/reviews/{case_id}",
                json={
                    "action": "override",
                    "selected_route": "specialist",
                    "specialist_label": "motor inspection",
                    "reason": "Synthetic demonstration override",
                    "evidence_acknowledged": True,
                },
                headers=underwriter,
            ).status_code == 200
            completed = client.post(
                f"/api/v1/completion/{case_id}", headers=underwriter
            )
            assert completed.status_code == 200, completed.text

            audit = audit_by_type(client, case_id, admin)

    finally:
        set_motor_status("draft")

    created_details = audit["case_created"]
    assert created_details["product_version_id"]
    assert created_details["product_version"]
    assert created_details["product_content_hash"]
    assert created_details["rulebook_version_id"]
    assert created_details["rulebook_content_hash"]

    uploaded_details = audit["document_uploaded"]
    assert uploaded_details["document_id"]
    assert uploaded_details["content_hash"]
    assert uploaded_details["byte_size"] > 0

    cycle = audit["case_submitted"]
    assert cycle["recommendation"] == "expedited"
    assert cycle["review_cycle"] == 0
    assert cycle["workflow_version"] == "evidence-v1"
    assert {item["field_name"] for item in cycle["evidence_provenance"]} >= {
        "vehicle_age",
        "vehicle_use",
        "prior_claims",
    }
    assert all(
        item["source_locator"] for item in cycle["evidence_provenance"]
    )
    assert len(cycle["documents"]) == 2
    assert all(item["content_hash"] for item in cycle["documents"])
    assert cycle["rulebook_version_id"]
    assert cycle["missing_information"] == []
    assert cycle["conflicts"] == []

    review = audit["underwriter_reviewed"]
    assert review["review_id"]
    assert review["review_cycle"] == 0
    assert review["action"] == "override"
    assert review["recommended_route"] == "expedited"
    assert review["selected_route"] == "specialist"
    assert review["specialist_label"] == "motor inspection"
    assert review["reason"] == "Synthetic demonstration override"

    completion = audit["case_completed"]
    assert completion["handoff_id"]
    assert completion["destination"] == "completed_queue"
    assert completion["idempotency_key"]
    assert completion["route"] == "specialist"
    assert completion["specialist_label"] == "motor inspection"
    assert completion["review_id"] == review["review_id"]


# Verify the audit trail reports real conflicts and gaps, not placeholders.
def test_audit_records_detected_conflicts_and_missing_fields() -> None:
    set_motor_status("active")
    try:
        with TestClient(
            create_app(Settings(generation_provider="fake"))
        ) as client:
            applicant = login(client, APPLICANT)
            admin = login(client, ADMIN)
            created = client.post(
                "/api/v1/cases",
                json={
                    "product_code": "motor-private-car",
                    "idempotency_key": str(uuid4()),
                    "payload": {
                        "vehicle_age": 2,
                        "vehicle_use": "personal",
                        "prior_claims": 0,
                    },
                    "document_codes": ["identity_record", "vehicle_record"],
                },
                headers=applicant,
            )
            assert created.status_code == 200, created.text
            case_id = created.json()["id"]

            uploads = (
                ("identity_record", IDENTITY_ONLY_LINES),
                ("vehicle_record", ["vehicle_age: 2", "vehicle_use: personal"]),
                ("vehicle_record", ["vehicle_age: 9", "vehicle_use: personal"]),
            )
            for code, lines in uploads:
                uploaded = client.post(
                    f"/api/v1/cases/{case_id}/documents",
                    files={
                        "document": (
                            "synthetic.pdf",
                            text_pdf(lines),
                            "application/pdf",
                        )
                    },
                    data={"document_code": code},
                    headers=applicant,
                )
                assert uploaded.status_code == 200, uploaded.text

            submitted = client.post(
                f"/api/v1/cases/{case_id}/submit", headers=applicant
            )
            assert submitted.status_code == 200, submitted.text
            audit = audit_by_type(client, case_id, admin)
    finally:
        set_motor_status("draft")

    cycle = audit["case_submitted"]
    assert "vehicle_age" in cycle["conflicts"]
    assert "prior_claims" in cycle["missing_information"]
    assert cycle["recommendation"] == "needs_information"
    assert len(cycle["documents"]) == 3
    assert cycle["evidence_provenance"]


# Verify every persisted value stays bounded and free of secret-shaped keys.
def test_persisted_events_are_bounded_and_secret_free() -> None:
    set_motor_status("active")
    try:
        with TestClient(
            create_app(Settings(generation_provider="fake"))
        ) as client:
            applicant = login(client, APPLICANT)
            admin = login(client, ADMIN)
            created = client.post(
                "/api/v1/cases",
                json={
                    "product_code": "motor-private-car",
                    "idempotency_key": str(uuid4()),
                    "payload": {
                        "vehicle_age": 2,
                        "vehicle_use": "personal",
                        "prior_claims": 0,
                    },
                    "document_codes": ["identity_record", "vehicle_record"],
                },
                headers=applicant,
            )
            case_id = created.json()["id"]
            for code, lines in (
                ("identity_record", IDENTITY_ONLY_LINES),
                ("vehicle_record", MOTOR_EVIDENCE_LINES),
            ):
                client.post(
                    f"/api/v1/cases/{case_id}/documents",
                    files={
                        "document": (
                            "synthetic.pdf",
                            text_pdf(lines),
                            "application/pdf",
                        )
                    },
                    data={"document_code": code},
                    headers=applicant,
                )
            assert client.post(
                f"/api/v1/cases/{case_id}/submit", headers=applicant
            ).status_code == 200
            response = client.get(
                f"/api/v1/audit/cases/{case_id}", headers=admin
            )
            assert response.status_code == 200, response.text
            events = response.json()
    finally:
        set_motor_status("draft")

    assert events
    for event in events:
        _assert_bounded_and_secret_free(event["details"])


# Walk one detail tree asserting the sanitization bound and key policy.
def _assert_bounded_and_secret_free(details: object) -> None:
    if isinstance(details, str):
        assert len(details) <= MAX_STRING_CHARS + 1, details[:80]
        return
    if isinstance(details, list):
        assert len(details) <= MAX_ITEMS
        for item in details:
            _assert_bounded_and_secret_free(item)
        return
    if isinstance(details, dict):
        assert len(details) <= MAX_ITEMS
        for key, value in details.items():
            assert not SENSITIVE_KEY_PATTERN.search(str(key)), key
            _assert_bounded_and_secret_free(value)
