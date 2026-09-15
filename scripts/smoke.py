"""Run the deterministic Compose end-to-end demonstration flow."""

from io import BytesIO

from fastapi.testclient import TestClient
from pypdf import PdfWriter

from underwriteflow.app import create_app

SMOKE_KEY = "synthetic-compose-smoke-v1"
SMOKE_DOCUMENTS = (
    ("identity_record", "identity.pdf"),
    ("vehicle_record", "vehicle.pdf"),
)


# Build a minimal single-page synthetic PDF for the smoke flow.
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


# Upload only configured motor documents absent from the case.
def upload_missing_documents(
    client: TestClient, case_id: str, headers: dict[str, str]
) -> None:
    response = client.get(f"/api/v1/cases/{case_id}/documents", headers=headers)
    assert response.status_code == 200, response.text
    attached = {document["document_code"] for document in response.json()}
    content = synthetic_pdf()
    for code, filename in SMOKE_DOCUMENTS:
        if code in attached:
            continue
        response = client.post(
            f"/api/v1/cases/{case_id}/documents",
            headers=headers,
            files={"document": (filename, content, "application/pdf")},
            data={"document_code": code},
        )
        assert response.status_code == 200, response.text


# Resume a fixed-key synthetic case from every valid smoke-flow status.
def recover_case(
    client: TestClient,
    case: dict[str, object],
    applicant: dict[str, str],
    underwriter: dict[str, str],
) -> dict[str, object]:
    case_id = str(case["id"])
    status = case["status"]
    if status == "new":
        upload_missing_documents(client, case_id, applicant)
        start = client.post(
            f"/api/v1/reviews/{case_id}/start", headers=underwriter
        )
        assert start.status_code == 200, start.text
        assert start.json()["recommendation"]["route"] == "expedited"
        status = "underwriter_review"
    if status == "underwriter_review":
        decision = client.post(
            f"/api/v1/reviews/{case_id}",
            headers=underwriter,
            json={"action": "confirm"},
        )
        assert decision.status_code == 200, decision.text
        assert decision.json()["status"] == "confirmed"
        status = "confirmed"
    if status in {"confirmed", "overridden", "completed"}:
        completion = client.post(
            f"/api/v1/completion/{case_id}", headers=underwriter
        )
        assert completion.status_code == 200, completion.text
        assert completion.json()["status"] == "completed"
        return completion.json()
    raise AssertionError(f"Unexpected smoke case status: {status}")


# Run intake, review, completion, retry, and audit assertions.
def run_smoke() -> None:
    with TestClient(create_app()) as client:
        administrator = login(
            client,
            "administrator@synthetic.test",
            "underwriteflow-demo-administrator",
        )
        activation = client.post(
            "/api/v1/products/motor-private-car/activate",
            headers=administrator,
            json={"version": "v1"},
        )
        assert activation.status_code == 200, activation.text
        applicant = login(
            client,
            "applicant@synthetic.test",
            "underwriteflow-demo-applicant",
        )
        case_response = client.post(
            "/api/v1/cases",
            headers=applicant,
            json={
                "product_code": "motor-private-car",
                "idempotency_key": SMOKE_KEY,
                "payload": {
                    "vehicle_age": 4,
                    "vehicle_use": "personal",
                    "prior_claims": 0,
                },
                "document_codes": ["identity_record", "vehicle_record"],
            },
        )
        assert case_response.status_code == 200, case_response.text
        case = case_response.json()
        case_id = case["id"]
        underwriter = login(
            client,
            "underwriter@synthetic.test",
            "underwriteflow-demo-underwriter",
        )
        completion = recover_case(client, case, applicant, underwriter)
        repeated = client.post(
            f"/api/v1/completion/{case_id}",
            headers=underwriter,
        )
        assert repeated.json() == completion
        audit = client.get(
            f"/api/v1/audit/cases/{case_id}",
            headers=administrator,
        )
        assert audit.status_code == 200, audit.text
        event_types = {event["event_type"] for event in audit.json()}
        assert {"case_created", "case_completed"}.issubset(event_types)
    print("Compose smoke passed: intake, review, completion, retry, audit")


if __name__ == "__main__":
    run_smoke()
