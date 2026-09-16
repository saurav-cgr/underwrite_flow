"""Specialist confirmation requires a configured destination label."""

from typing import Any
from uuid import uuid4

import psycopg
from fastapi.testclient import TestClient
from synthetic_pdf import (
    IDENTITY_ONLY_LINES,
    MOTOR_EVIDENCE_LINES,
    text_pdf,
)

from underwriteflow.app import create_app
from underwriteflow.config import Settings

DATABASE_URL = (
    "postgresql://underwriteflow:synthetic-local-password@"
    "db:5433/underwriteflow"
)

MOTOR_PAYLOAD = {
    "vehicle_age": 2,
    "vehicle_use": "personal",
    "prior_claims": 0,
}

DOCUMENT_CODES = ["identity_record", "vehicle_record"]

SPECIALIST_LABEL = "motor inspection"


# Log in one fictional demo role and return bearer headers.
def login(
    client: TestClient, email: str, password: str
) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/session",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['token']}"}


# Set the built-in synthetic motor product active or back to draft.
def set_motor_status(status: str) -> None:
    with psycopg.connect(DATABASE_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE product_versions SET status = %s WHERE product_id "
                "= (SELECT id FROM products WHERE code = %s)",
                (status, "motor-private-car"),
            )
            cursor.execute(
                "UPDATE products SET status = %s WHERE code = %s",
                (status, "motor-private-car"),
            )


# Create, upload conflicting evidence, and submit a specialist case.
def prepare_specialist_case(
    client: TestClient, applicant: dict[str, str]
) -> str:
    created = client.post(
        "/api/v1/cases",
        json={
            "product_code": "motor-private-car",
            "idempotency_key": str(uuid4()),
            "payload": MOTOR_PAYLOAD,
            "document_codes": DOCUMENT_CODES,
        },
        headers=applicant,
    )
    assert created.status_code == 200, created.text
    case_id = created.json()["id"]
    uploads = [
        (
            "identity_record",
            text_pdf(IDENTITY_ONLY_LINES + ["vehicle_age: 9"]),
        ),
        ("vehicle_record", text_pdf(MOTOR_EVIDENCE_LINES)),
    ]
    for code, content in uploads:
        uploaded = client.post(
            f"/api/v1/cases/{case_id}/documents",
            files={
                "document": (
                    "synthetic.pdf",
                    content,
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
    assert submitted.json()["recommendation"]["route"] == "specialist"
    return case_id


# Read the persisted specialist label of a case's newest review.
def read_review_label(case_id: str) -> str | None:
    with psycopg.connect(DATABASE_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT specialist_label FROM reviews WHERE case_id = %s "
                "ORDER BY review_cycle DESC LIMIT 1",
                (case_id,),
            )
            row = cursor.fetchone()
            return row[0] if row else None


# Read the persisted queue handoff payload for one case.
def read_handoff_payload(case_id: str) -> dict[str, Any]:
    with psycopg.connect(DATABASE_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT payload FROM handoffs WHERE case_id = %s",
                (case_id,),
            )
            row = cursor.fetchone()
            return dict(row[0]) if row else {}


# Verify a specialist recommendation cannot be confirmed without a configured
# label, and that the chosen label reaches the queue handoff payload.
def test_confirming_specialist_requires_configured_label() -> None:
    set_motor_status("active")
    case_id = ""
    try:
        settings = Settings(generation_provider="fake")
        with TestClient(create_app(settings)) as client:
            applicant = login(
                client,
                "applicant@synthetic.test",
                "underwriteflow-demo-applicant",
            )
            underwriter = login(
                client,
                "underwriter@synthetic.test",
                "underwriteflow-demo-underwriter",
            )
            case_id = prepare_specialist_case(client, applicant)

            missing = client.post(
                f"/api/v1/reviews/{case_id}",
                headers=underwriter,
                json={"action": "confirm", "evidence_acknowledged": True},
            )
            assert missing.status_code == 422, missing.text
            assert read_review_label(case_id) is None

            unconfigured = client.post(
                f"/api/v1/reviews/{case_id}",
                headers=underwriter,
                json={
                    "action": "confirm",
                    "specialist_label": "synthetic unconfigured desk",
                    "evidence_acknowledged": True,
                },
            )
            assert unconfigured.status_code == 422, unconfigured.text
            assert read_review_label(case_id) is None

            confirmed = client.post(
                f"/api/v1/reviews/{case_id}",
                headers=underwriter,
                json={
                    "action": "confirm",
                    "specialist_label": SPECIALIST_LABEL,
                    "evidence_acknowledged": True,
                },
            )
            assert confirmed.status_code == 200, confirmed.text
            assert confirmed.json()["status"] == "confirmed"
            assert confirmed.json()["selected_route"] == "specialist"
            assert read_review_label(case_id) == SPECIALIST_LABEL

            completed = client.post(
                f"/api/v1/completion/{case_id}", headers=underwriter
            )
            assert completed.status_code == 200, completed.text
            assert completed.json()["specialist_label"] == SPECIALIST_LABEL

        assert read_handoff_payload(case_id)["specialist_label"] == (
            SPECIALIST_LABEL
        )
    finally:
        set_motor_status("draft")
