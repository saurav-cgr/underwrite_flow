"""Renewal journey evidence and submission behaviour end to end."""

from uuid import uuid4

from fastapi.testclient import TestClient

from fixtures.records import motor_status, remove_case, set_motor_status
from fixtures.support import ADMINISTRATOR, APPLICANT, login, upload_documents
from fixtures.synthetic_pdf import (
    IDENTITY_ONLY_LINES,
    MOTOR_EVIDENCE_LINES,
    PREVIOUS_POLICY_LINES,
    REGISTRATION_CERTIFICATE_LINES,
    text_pdf,
)
from underwriteflow.app import create_app
from underwriteflow.config import Settings

RENEWAL_PAYLOAD = {
    "vehicle_age": 3,
    "vehicle_use": "personal",
    "prior_claims": 0,
    "claimed_ncb_percent": 20,
    "policy_start_date": "2025-09-01",
}

RENEWAL_CORE_UPLOADS = [
    ("identity_record", text_pdf(IDENTITY_ONLY_LINES)),
    ("vehicle_record", text_pdf(MOTOR_EVIDENCE_LINES)),
    ("registration_certificate", text_pdf(REGISTRATION_CERTIFICATE_LINES)),
]


# Activate motor v4 for one test and always restore the prior active version.
def activate_motor_v4(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    activated = client.post(
        "/api/v1/products/motor-private-car/activate",
        json={"version": "v4"},
        headers=admin_headers,
    )
    assert activated.status_code == 200, activated.text


# Verify a renewal submission is refused without its prior-policy document.
def test_renewal_submission_requires_prior_policy_document() -> None:
    prior = motor_status()
    case_id = ""
    try:
        settings = Settings(generation_provider="fake")
        with TestClient(create_app(settings)) as client:
            admin = login(client, ADMINISTRATOR)
            activate_motor_v4(client, admin)
            applicant = login(client, APPLICANT)
            created = client.post(
                "/api/v1/cases",
                json={
                    "product_code": "motor-private-car",
                    "idempotency_key": str(uuid4()),
                    "journey": "renewal",
                    "payload": RENEWAL_PAYLOAD,
                    "document_codes": [],
                },
                headers=applicant,
            )
            assert created.status_code == 200, created.text
            case_id = created.json()["id"]
            upload_documents(
                client, applicant, case_id, RENEWAL_CORE_UPLOADS
            )

            submitted = client.post(
                f"/api/v1/cases/{case_id}/submit", headers=applicant
            )

            assert submitted.status_code == 422, submitted.text
    finally:
        if case_id:
            remove_case(case_id)
        set_motor_status("active", "v1")
        set_motor_status(prior, "v1")


# Verify a renewal submission proceeds once its prior policy is attached.
def test_renewal_submission_succeeds_with_prior_policy_document() -> None:
    prior = motor_status()
    case_id = ""
    try:
        settings = Settings(generation_provider="fake")
        with TestClient(create_app(settings)) as client:
            admin = login(client, ADMINISTRATOR)
            activate_motor_v4(client, admin)
            applicant = login(client, APPLICANT)
            created = client.post(
                "/api/v1/cases",
                json={
                    "product_code": "motor-private-car",
                    "idempotency_key": str(uuid4()),
                    "journey": "renewal",
                    "payload": RENEWAL_PAYLOAD,
                    "document_codes": [],
                },
                headers=applicant,
            )
            assert created.status_code == 200, created.text
            case_id = created.json()["id"]
            upload_documents(
                client,
                applicant,
                case_id,
                [
                    *RENEWAL_CORE_UPLOADS,
                    ("previous_policy", text_pdf(PREVIOUS_POLICY_LINES)),
                ],
            )

            submitted = client.post(
                f"/api/v1/cases/{case_id}/submit", headers=applicant
            )

            assert submitted.status_code == 200, submitted.text
            assert submitted.json()["status"] == "underwriter_review"
    finally:
        if case_id:
            remove_case(case_id)
        set_motor_status("active", "v1")
        set_motor_status(prior, "v1")


# Verify a new-business case never sees renewal-only requirements.
def test_new_business_configuration_excludes_renewal_only_requirements() -> (
    None
):
    prior = motor_status()
    case_id = ""
    try:
        settings = Settings(generation_provider="fake")
        with TestClient(create_app(settings)) as client:
            admin = login(client, ADMINISTRATOR)
            activate_motor_v4(client, admin)
            applicant = login(client, APPLICANT)
            created = client.post(
                "/api/v1/cases",
                json={
                    "product_code": "motor-private-car",
                    "idempotency_key": str(uuid4()),
                    "journey": "new_business",
                    "payload": {},
                    "document_codes": [],
                },
                headers=applicant,
            )
            assert created.status_code == 200, created.text
            case_id = created.json()["id"]

            configuration = client.get(
                f"/api/v1/cases/{case_id}/configuration", headers=applicant
            )
            assert configuration.status_code == 200, configuration.text
            body = configuration.json()
            field_keys = {field["key"] for field in body["fields"]}
            document_codes = {doc["code"] for doc in body["documents"]}
            assert "claimed_ncb_percent" not in field_keys
            assert "policy_start_date" not in field_keys
            assert "previous_policy" not in document_codes
    finally:
        if case_id:
            remove_case(case_id)
        set_motor_status("active", "v1")
        set_motor_status(prior, "v1")
