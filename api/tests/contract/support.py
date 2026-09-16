"""Shared helpers for the API response-contract tests.

Every helper drives the public HTTP surface or the database directly. None of
them construct a response model by hand, so a contract test can only pass when
the served JSON keeps its current shape.
"""

import shutil
from uuid import uuid4

import psycopg
from fastapi.testclient import TestClient
from synthetic_pdf import (
    IDENTITY_ONLY_LINES,
    MOTOR_EVIDENCE_LINES,
    UPLOAD_ROOT,
    text_pdf,
)

DATABASE_URL = (
    "postgresql://underwriteflow:synthetic-local-password@"
    "db:5433/underwriteflow"
)

APPLICANT = ("applicant@synthetic.test", "underwriteflow-demo-applicant")
UNDERWRITER = ("underwriter@synthetic.test", "underwriteflow-demo-underwriter")

MOTOR_PAYLOAD = {
    "vehicle_age": 2,
    "vehicle_use": "personal",
    "prior_claims": 0,
}

DOCUMENT_CODES = ["identity_record", "vehicle_record"]

# The recommendation object the submit and review-start contracts both serve.
RECOMMENDATION_KEYS = {"route", "factors"}


# Log in one fictional demo role and return bearer headers.
def login(client: TestClient, account: tuple[str, str]) -> dict[str, str]:
    email, password = account
    response = client.post(
        "/api/v1/auth/session",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['token']}"}


# Replace one case's persisted recommendation summary with an empty object.
def clear_recommendation_summary(case_id: str) -> None:
    with psycopg.connect(DATABASE_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE recommendations SET summary = '{}'::jsonb "
                "WHERE case_id = %s",
                (case_id,),
            )


# Read the current status of the built-in synthetic motor product.
def motor_status() -> str:
    with psycopg.connect(DATABASE_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT status FROM products WHERE code = %s",
                ("motor-private-car",),
            )
            row = cursor.fetchone()
    return row[0] if row else "draft"


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


# Create one applicant-owned motor case and return the parsed response.
def create_motor_case(
    client: TestClient, headers: dict[str, str]
) -> dict[str, object]:
    created = client.post(
        "/api/v1/cases",
        json={
            "product_code": "motor-private-car",
            "idempotency_key": str(uuid4()),
            "payload": MOTOR_PAYLOAD,
            "document_codes": DOCUMENT_CODES,
        },
        headers=headers,
    )
    assert created.status_code == 200, created.text
    return created.json()


# Upload one synthetic document per (code, content) pair.
def upload_documents(
    client: TestClient,
    headers: dict[str, str],
    case_id: str,
    uploads: list[tuple[str, bytes]],
) -> list[dict[str, object]]:
    responses: list[dict[str, object]] = []
    for code, content in uploads:
        uploaded = client.post(
            f"/api/v1/cases/{case_id}/documents",
            files={"document": ("synthetic.pdf", content, "application/pdf")},
            data={"document_code": code},
            headers=headers,
        )
        assert uploaded.status_code == 200, uploaded.text
        responses.append(uploaded.json())
    return responses


# Build the two motor uploads that agree on every requested field.
def motor_uploads() -> list[tuple[str, bytes]]:
    return [
        ("identity_record", text_pdf(IDENTITY_ONLY_LINES)),
        ("vehicle_record", text_pdf(MOTOR_EVIDENCE_LINES)),
    ]


# Build motor uploads whose identity record disagrees on the vehicle age.
def conflicting_motor_uploads() -> list[tuple[str, bytes]]:
    return [
        ("identity_record", text_pdf(IDENTITY_ONLY_LINES + ["vehicle_age: 9"])),
        ("vehicle_record", text_pdf(MOTOR_EVIDENCE_LINES)),
    ]


# Upload both synthetic motor documents and return the parsed responses.
def upload_motor_documents(
    client: TestClient, headers: dict[str, str], case_id: str
) -> list[dict[str, object]]:
    return upload_documents(client, headers, case_id, motor_uploads())


# Submit a motor case and return the parsed submission response.
def submit_motor_case(
    client: TestClient, headers: dict[str, str], case_id: str
) -> dict[str, object]:
    submitted = client.post(
        f"/api/v1/cases/{case_id}/submit", headers=headers
    )
    assert submitted.status_code == 200, submitted.text
    return submitted.json()


# Open the human review of one submitted case and return the parsed response.
def start_review(
    client: TestClient, headers: dict[str, str], case_id: str
) -> dict[str, object]:
    started = client.post(f"/api/v1/reviews/{case_id}/start", headers=headers)
    assert started.status_code == 200, started.text
    return started.json()


# Delete one uploaded file so its extraction branch fails on the volume.
def remove_upload(case_id: str, document_code: str) -> None:
    with psycopg.connect(DATABASE_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT storage_key FROM documents WHERE case_id = %s "
                "AND document_code = %s",
                (case_id, document_code),
            )
            row = cursor.fetchone()
    assert row is not None
    (UPLOAD_ROOT / row[0]).unlink()


# Remove one synthetic case and every row the workflow wrote for it.
def remove_case(case_id: str) -> None:
    thread_id = f"case-{case_id}:cycle-0"
    with psycopg.connect(DATABASE_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM checkpoint_writes WHERE thread_id = %s",
                (thread_id,),
            )
            cursor.execute(
                "DELETE FROM checkpoint_blobs WHERE thread_id = %s",
                (thread_id,),
            )
            cursor.execute(
                "DELETE FROM checkpoints WHERE thread_id = %s",
                (thread_id,),
            )
            cursor.execute(
                "DELETE FROM handoffs WHERE case_id = %s", (case_id,)
            )
            # Audit events are append-only, so the guard is lifted briefly.
            cursor.execute(
                "ALTER TABLE audit_events DISABLE TRIGGER "
                "audit_events_append_only"
            )
            try:
                cursor.execute(
                    "DELETE FROM audit_events WHERE case_id = %s", (case_id,)
                )
                cursor.execute(
                    "DELETE FROM extracted_fields WHERE case_id = %s",
                    (case_id,),
                )
                cursor.execute(
                    "DELETE FROM validations WHERE case_id = %s", (case_id,)
                )
                cursor.execute(
                    "DELETE FROM risk_signals WHERE case_id = %s", (case_id,)
                )
                cursor.execute(
                    "DELETE FROM reviews WHERE case_id = %s", (case_id,)
                )
                cursor.execute(
                    "DELETE FROM recommendations WHERE case_id = %s",
                    (case_id,),
                )
                cursor.execute(
                    "DELETE FROM documents WHERE case_id = %s", (case_id,)
                )
                cursor.execute(
                    "DELETE FROM submissions WHERE case_id = %s", (case_id,)
                )
                cursor.execute("DELETE FROM cases WHERE id = %s", (case_id,))
            finally:
                cursor.execute(
                    "ALTER TABLE audit_events ENABLE TRIGGER "
                    "audit_events_append_only"
                )
    shutil.rmtree(UPLOAD_ROOT / case_id, ignore_errors=True)
