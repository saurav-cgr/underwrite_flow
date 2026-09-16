"""Shared HTTP helpers for the integration and contract suites.

Every helper here drives the public API surface, so a contract test can only
pass when the served JSON keeps its current shape. Direct database and volume
helpers live beside this module in `fixtures.records`.
"""

from uuid import uuid4

from fastapi.testclient import TestClient

from fixtures.synthetic_pdf import (
    IDENTITY_ONLY_LINES,
    MOTOR_EVIDENCE_LINES,
    text_pdf,
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
