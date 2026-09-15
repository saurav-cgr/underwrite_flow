"""Administrator reference-document endpoints for product configuration."""

from io import BytesIO

import psycopg
from fastapi.testclient import TestClient
from pypdf import PdfWriter

from underwriteflow.app import create_app
from underwriteflow.config import Settings

DATABASE_URL = (
    "postgresql://underwriteflow:synthetic-local-password@"
    "db:5433/underwriteflow"
)
PRODUCT_CODE = "motor-private-car"
PRODUCT_VERSION = "v1"


# Build a minimal single-page synthetic PDF for reference-upload tests.
def synthetic_pdf() -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    buffer = BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


# Log in one fictional demo role and return bearer headers.
def login(client: TestClient, email: str, password: str) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/session",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['token']}"}


# Verify only administrators manage versioned product reference documents.
def test_reference_documents_require_administrator_and_round_trip() -> None:
    content = synthetic_pdf()
    settings = Settings(generation_provider="fake")
    with TestClient(create_app(settings)) as client:
        admin = login(
            client,
            "administrator@synthetic.test",
            "underwriteflow-demo-administrator",
        )
        applicant = login(
            client,
            "applicant@synthetic.test",
            "underwriteflow-demo-applicant",
        )
        path = f"/api/v1/products/{PRODUCT_CODE}/references"

        forbidden = client.post(
            path,
            files={"reference": ("reference.pdf", content, "application/pdf")},
            data={"version": PRODUCT_VERSION},
            headers=applicant,
        )
        assert forbidden.status_code == 403

        rejected = client.post(
            path,
            files={"reference": ("bad.txt", b"synthetic", "text/plain")},
            data={"version": PRODUCT_VERSION},
            headers=admin,
        )
        assert rejected.status_code == 422

        uploaded = client.post(
            path,
            files={"reference": ("reference.pdf", content, "application/pdf")},
            data={"version": PRODUCT_VERSION},
            headers=admin,
        )
        assert uploaded.status_code == 200, uploaded.text
        body = uploaded.json()
        assert body["filename"] == "reference.pdf"
        assert body["version"] == PRODUCT_VERSION
        assert body["content_type"] == "application/pdf"
        assert body["page_count"] == 1
        assert body["content_hash"]
        assert body["byte_size"] == len(content)

        listed = client.get(path, headers=admin)
        assert listed.status_code == 200, listed.text
        assert body["id"] in [item["id"] for item in listed.json()]

        removed = client.delete(
            f"{path}/{body['id']}",
            headers=admin,
        )
        assert removed.status_code == 204
        remaining = client.get(path, headers=admin)
        assert remaining.status_code == 200
        assert body["id"] not in [item["id"] for item in remaining.json()]

        with psycopg.connect(DATABASE_URL) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT event_type FROM audit_events WHERE event_type IN "
                    "(%s, %s)",
                    (
                        "reference_document_added",
                        "reference_document_removed",
                    ),
                )
                events = {row[0] for row in cursor.fetchall()}

    assert "reference_document_added" in events
    assert "reference_document_removed" in events
