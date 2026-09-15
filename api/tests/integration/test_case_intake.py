import hashlib
from io import BytesIO
from uuid import uuid4

import psycopg
from fastapi.testclient import TestClient
from pypdf import PdfWriter

from underwriteflow.app import create_app


DATABASE_URL = (
    "postgresql://underwriteflow:synthetic-local-password@"
    "db:5433/underwriteflow"
)


# Build a minimal single-page synthetic PDF for upload tests.
def synthetic_pdf() -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    buffer = BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


# Set one built-in synthetic product active for the intake smoke test.
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


# Verify idempotent intake and safe upload metadata.
def test_case_intake_is_idempotent_and_stores_safe_document_metadata() -> None:
    set_motor_status("active")
    try:
        application = {
            "product_code": "motor-private-car",
            "idempotency_key": str(uuid4()),
            "payload": {
                "vehicle_age": 2,
                "vehicle_use": "personal",
                "prior_claims": 0,
            },
            "document_codes": ["identity_record", "vehicle_record"],
        }
        with TestClient(create_app()) as client:
            login = client.post(
                "/api/v1/auth/session",
                json={
                    "email": "applicant@synthetic.test",
                    "password": "underwriteflow-demo-applicant",
                },
            )
            assert login.status_code == 200
            headers = {"Authorization": f"Bearer {login.json()['token']}"}
            catalog = client.get(
                "/api/v1/products/catalog",
                headers=headers,
            )
            assert catalog.status_code == 200
            assert (
                catalog.json()[0]["product_code"]
                == "motor-private-car"
            )
            assert "routing_rules" not in catalog.json()[0]

            created = client.post(
                "/api/v1/cases",
                json=application,
                headers=headers,
            )
            repeated = client.post(
                "/api/v1/cases",
                json=application,
                headers=headers,
            )

            assert created.status_code == 200
            assert repeated.status_code == 200
            assert repeated.json()["id"] == created.json()["id"]

            content = synthetic_pdf()
            document = client.post(
                f"/api/v1/cases/{created.json()['id']}/documents",
                files={
                    "document": (
                        "synthetic.pdf",
                        content,
                        "application/pdf",
                    )
                },
                data={"document_code": "identity_record"},
                headers=headers,
            )
            assert document.status_code == 200
            assert (
                document.json()["content_hash"]
                == hashlib.sha256(content).hexdigest()
            )
            assert document.json()["filename"] == "synthetic.pdf"

            removed = client.delete(
                f"/api/v1/cases/{created.json()['id']}/documents/"
                f"{document.json()['id']}",
                headers=headers,
            )
            remaining = client.get(
                f"/api/v1/cases/{created.json()['id']}/documents",
                headers=headers,
            )
            assert removed.status_code == 204
            assert remaining.status_code == 200
            assert remaining.json() == []
            with psycopg.connect(DATABASE_URL) as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT event_type
                        FROM audit_events
                        WHERE case_id = %s AND event_type = %s
                        """,
                        (created.json()["id"], "document_removed"),
                    )
                    assert cursor.fetchone() == ("document_removed",)

            replacement = client.post(
                f"/api/v1/cases/{created.json()['id']}/documents",
                files={
                    "document": (
                        "replacement.pdf",
                        content,
                        "application/pdf",
                    )
                },
                data={"document_code": "identity_record"},
                headers=headers,
            )
            with psycopg.connect(DATABASE_URL) as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        "UPDATE cases SET status = %s WHERE id = %s",
                        ("underwriter_review", created.json()["id"]),
                    )
            locked_removal = client.delete(
                f"/api/v1/cases/{created.json()['id']}/documents/"
                f"{replacement.json()['id']}",
                headers=headers,
            )
            locked_upload = client.post(
                f"/api/v1/cases/{created.json()['id']}/documents",
                files={
                    "document": (
                        "late.pdf",
                        content,
                        "application/pdf",
                    )
                },
                data={"document_code": "vehicle_record"},
                headers=headers,
            )
            assert replacement.status_code == 200
            assert locked_removal.status_code == 422
            assert locked_upload.status_code == 422

            rejected = client.post(
                f"/api/v1/cases/{created.json()['id']}/documents",
                files={"document": ("synthetic.txt", content, "text/plain")},
                data={"document_code": "vehicle_record"},
                headers=headers,
            )
            assert rejected.status_code == 422
    finally:
        set_motor_status("draft")


# Verify uploads need a known product code and survive needs-information.
def test_document_upload_requires_a_known_code() -> None:
    set_motor_status("active")
    try:
        application = {
            "product_code": "motor-private-car",
            "idempotency_key": str(uuid4()),
            "payload": {
                "vehicle_age": 2,
                "vehicle_use": "personal",
                "prior_claims": 0,
            },
            "document_codes": ["identity_record", "vehicle_record"],
        }
        content = synthetic_pdf()
        with TestClient(create_app()) as client:
            login = client.post(
                "/api/v1/auth/session",
                json={
                    "email": "applicant@synthetic.test",
                    "password": "underwriteflow-demo-applicant",
                },
            )
            headers = {"Authorization": f"Bearer {login.json()['token']}"}
            created = client.post(
                "/api/v1/cases", json=application, headers=headers
            )
            case_id = created.json()["id"]

            missing_code = client.post(
                f"/api/v1/cases/{case_id}/documents",
                files={
                    "document": ("synthetic.pdf", content, "application/pdf")
                },
                headers=headers,
            )
            unknown_code = client.post(
                f"/api/v1/cases/{case_id}/documents",
                files={
                    "document": ("synthetic.pdf", content, "application/pdf")
                },
                data={"document_code": "not_a_product_document"},
                headers=headers,
            )
            accepted = client.post(
                f"/api/v1/cases/{case_id}/documents",
                files={
                    "document": ("synthetic.pdf", content, "application/pdf")
                },
                data={"document_code": "identity_record"},
                headers=headers,
            )

            assert missing_code.status_code == 422
            assert unknown_code.status_code == 422
            assert accepted.status_code == 200
            assert accepted.json()["document_code"] == "identity_record"
            assert accepted.json()["page_count"] == 1

            with psycopg.connect(DATABASE_URL) as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        "UPDATE cases SET status = %s WHERE id = %s",
                        ("needs_information", case_id),
                    )
            still_open = client.post(
                f"/api/v1/cases/{case_id}/documents",
                files={
                    "document": ("synthetic.pdf", content, "application/pdf")
                },
                data={"document_code": "vehicle_record"},
                headers=headers,
            )
            assert still_open.status_code == 200
    finally:
        set_motor_status("draft")
