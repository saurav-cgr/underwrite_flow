"""End-to-end applicant submission into the bounded evidence workflow."""

from io import BytesIO
from uuid import uuid4

import psycopg
from fastapi.testclient import TestClient
from pypdf import PdfWriter

from underwriteflow.app import create_app
from underwriteflow.config import Settings

DATABASE_URL = (
    "postgresql://underwriteflow:synthetic-local-password@"
    "db:5433/underwriteflow"
)


# Build a minimal single-page synthetic PDF for submission tests.
def synthetic_pdf() -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    buffer = BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


# Set one built-in synthetic product active for the submission test.
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
def login(client: TestClient, email: str, password: str) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/session",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['token']}"}


# Verify submission requires complete evidence and then persists the run.
def test_submission_requires_evidence_and_persists_recommendation() -> None:
    set_motor_status("active")
    try:
        content = synthetic_pdf()
        settings = Settings(generation_provider="fake")
        with TestClient(create_app(settings)) as client:
            headers = login(
                client,
                "applicant@synthetic.test",
                "underwriteflow-demo-applicant",
            )
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
                headers=headers,
            )
            assert created.status_code == 200, created.text
            case_id = created.json()["id"]

            incomplete = client.post(
                f"/api/v1/cases/{case_id}/submit", headers=headers
            )
            assert incomplete.status_code == 422

            for code in ("identity_record", "vehicle_record"):
                uploaded = client.post(
                    f"/api/v1/cases/{case_id}/documents",
                    files={
                        "document": ("synthetic.pdf", content, "application/pdf")
                    },
                    data={"document_code": code},
                    headers=headers,
                )
                assert uploaded.status_code == 200, uploaded.text

            submitted = client.post(
                f"/api/v1/cases/{case_id}/submit", headers=headers
            )
            assert submitted.status_code == 200, submitted.text
            assert submitted.json()["status"] == "underwriter_review"
            assert submitted.json()["recommendation"]["route"] == "expedited"

            with psycopg.connect(DATABASE_URL) as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        "SELECT status, route FROM recommendations "
                        "WHERE case_id = %s",
                        (case_id,),
                    )
                    assert cursor.fetchone() == (
                        "pending_human_review",
                        "expedited",
                    )
                    cursor.execute(
                        "SELECT status FROM cases WHERE id = %s",
                        (case_id,),
                    )
                    assert cursor.fetchone() == ("underwriter_review",)
                    cursor.execute(
                        "SELECT count(*) FROM audit_events "
                        "WHERE case_id = %s AND event_type = %s",
                        (case_id, "case_submitted"),
                    )
                    assert cursor.fetchone()[0] == 1
    finally:
        set_motor_status("draft")


# Verify resubmission opens a new review cycle for the same case.
def test_resubmission_starts_a_new_review_cycle() -> None:
    set_motor_status("active")
    try:
        content = synthetic_pdf()
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
            listing = client.get("/api/v1/cases", headers=applicant)
            assert listing.status_code == 200, listing.text
            assert any(item["id"] == case_id for item in listing.json())
            for code in ("identity_record", "vehicle_record"):
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
            requested = client.post(
                f"/api/v1/reviews/{case_id}",
                headers=underwriter,
                json={
                    "action": "request_information",
                    "reason": "Synthetic extra evidence required",
                    "evidence_acknowledged": True,
                },
            )
            assert requested.status_code == 200, requested.text
            assert requested.json()["status"] == "needs_information"
            resubmitted = client.post(
                f"/api/v1/cases/{case_id}/resubmit", headers=applicant
            )
            assert resubmitted.status_code == 200, resubmitted.text
            assert resubmitted.json()["status"] == "underwriter_review"

            with psycopg.connect(DATABASE_URL) as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        "SELECT status, review_cycle FROM cases WHERE id = %s",
                        (case_id,),
                    )
                    assert cursor.fetchone() == (
                        "underwriter_review",
                        1,
                    )
                    cursor.execute(
                        "SELECT count(*) FROM audit_events "
                        "WHERE case_id = %s AND event_type = %s",
                        (case_id, "case_resubmitted"),
                    )
                    assert cursor.fetchone()[0] == 1
    finally:
        set_motor_status("draft")
