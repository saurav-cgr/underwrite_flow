"""Human override of a flagged reconciliation, finalised exactly once."""

from uuid import UUID, uuid4

import psycopg
from fastapi.testclient import TestClient
from fixtures.records import remove_case, set_motor_status
from fixtures.synthetic_pdf import IDENTITY_ONLY_LINES, text_pdf

from underwriteflow.app import create_app
from underwriteflow.config import Settings

CASE_PAYLOAD = {
    "vehicle_age": 2,
    "vehicle_use": "personal",
    "prior_claims": 2,
    "policy_start_date": "2026-01-15",
}


# Log in one fictional demo account and return bearer headers.
def login(client: TestClient, email: str, password: str) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


# Upload a vehicle record whose NCB claim disagrees with the application.
def upload_disagreeing_vehicle_record(
    client: TestClient, headers: dict[str, str], case_id: str
) -> None:
    items = {
        "identity_record": IDENTITY_ONLY_LINES,
        "vehicle_record": [
            "vehicle_age: 2",
            "vehicle_use: personal",
            "prior_claims: 2",
            "policy_start_date: 2026-01-15",
            "ncb_percent: 0",
            "policy_expiry: 2026-01-05",
        ],
    }
    for code, lines in items.items():
        uploaded = client.post(
            f"/api/v1/cases/{case_id}/documents",
            files={"document": ("synthetic.pdf", text_pdf(lines), "application/pdf")},
            data={"document_code": code},
            headers=headers,
        )
        assert uploaded.status_code == 200, uploaded.text


# Count the persisted handoffs for one case, proving completion ran once.
def handoff_count(case_id: str) -> int:
    with psycopg.connect(
        "postgresql://underwriteflow:synthetic-local-password@"
        "db:5433/underwriteflow"
    ) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT count(*) FROM handoffs WHERE case_id = %s",
                (case_id,),
            )
            return cursor.fetchone()[0]


# Verify a flagged case needs a rationale to override and completes once.
def test_override_of_flagged_case_requires_reason_and_completes_once() -> None:
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
            created = client.post(
                "/api/v1/cases",
                json={
                    "product_code": "motor-private-car",
                    "idempotency_key": str(uuid4()),
                    "payload": CASE_PAYLOAD,
                    "document_codes": ["identity_record", "vehicle_record"],
                },
                headers=applicant,
            )
            assert created.status_code == 200, created.text
            case_id = created.json()["id"]
            upload_disagreeing_vehicle_record(client, applicant, case_id)

            submitted = client.post(
                f"/api/v1/cases/{case_id}/submit", headers=applicant
            )
            assert submitted.status_code == 200, submitted.text
            assert submitted.json()["recommendation"]["route"] == "specialist"

            underwriter = login(
                client,
                "underwriter@synthetic.test",
                "underwriteflow-demo-underwriter",
            )
            pack = client.post(
                f"/api/v1/reviews/{case_id}/start", headers=underwriter
            )
            assert pack.status_code == 200, pack.text
            flagged = pack.json()["reconciliation"]
            assert flagged[0]["check_code"] == "motor_ncb_match"
            assert flagged[0]["status"] == "FLAGGED_DISCREPANCY"
            assert flagged[0]["comparisons"][0]["confidence_source"] == (
                "deterministic"
            )

            without_reason = client.post(
                f"/api/v1/reviews/{case_id}",
                json={
                    "action": "override",
                    "selected_route": "standard",
                    "evidence_acknowledged": True,
                },
                headers=underwriter,
            )
            override = client.post(
                f"/api/v1/reviews/{case_id}",
                json={
                    "action": "override",
                    "selected_route": "standard",
                    "reason": "Synthetic demonstration override.",
                    "evidence_acknowledged": True,
                },
                headers=underwriter,
            )
            completion = client.post(
                f"/api/v1/completion/{case_id}", headers=underwriter
            )
            repeated = client.post(
                f"/api/v1/completion/{case_id}", headers=underwriter
            )

        assert without_reason.status_code == 422, without_reason.text
        assert override.status_code == 200, override.text
        assert override.json()["status"] == "overridden"
        assert override.json()["selected_route"] == "standard"
        assert completion.status_code == 200, completion.text
        assert repeated.json() == completion.json()
        assert handoff_count(case_id) == 1
    finally:
        if case_id:
            remove_case(UUID(case_id))
        set_motor_status("draft")
