"""Renewal journey evidence and submission behaviour end to end."""

from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from fixtures.records import (
    motor_status,
    read_audit,
    remove_case,
    set_motor_status,
)
from fixtures.support import (
    ADMINISTRATOR,
    APPLICANT,
    UNDERWRITER,
    login,
    upload_documents,
)
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


NEW_BUSINESS_PAYLOAD = {"vehicle_age": 4, "vehicle_use": "personal"}

UNSUPPORTED_FIELD_DETAIL = "Unsupported application field: prior_claims"

NEW_BUSINESS_UPLOADS = [
    ("identity_record", text_pdf(IDENTITY_ONLY_LINES)),
    ("vehicle_record", text_pdf(MOTOR_EVIDENCE_LINES)),
    ("registration_certificate", text_pdf(REGISTRATION_CERTIFICATE_LINES)),
]

MOTOR_ASSET_CHECKS = [
    "motor_chassis_match",
    "motor_engine_match",
    "motor_registration_match",
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


# Activate motor v5 for one test and always restore the prior active version.
def activate_motor_v5(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    activated = client.post(
        "/api/v1/products/motor-private-car/activate",
        json={"version": "v5"},
        headers=admin_headers,
    )
    assert activated.status_code == 200, activated.text


# Create one draft case for a journey and return the parsed response.
def create_case(
    client: TestClient,
    headers: dict[str, str],
    journey: str,
    payload: dict[str, object],
    idempotency_key: str,
) -> object:
    return client.post(
        "/api/v1/cases",
        json={
            "product_code": "motor-private-car",
            "idempotency_key": idempotency_key,
            "journey": journey,
            "payload": payload,
            "document_codes": [],
        },
        headers=headers,
    )


# Verify a v5 new-business case never asks for, stores, or reviews claims.
def test_new_business_v5_excludes_prior_claims_end_to_end() -> None:
    prior = motor_status()
    case_id = ""
    try:
        settings = Settings(generation_provider="fake")
        with TestClient(create_app(settings)) as client:
            admin = login(client, ADMINISTRATOR)
            activate_motor_v5(client, admin)
            applicant = login(client, APPLICANT)
            underwriter = login(client, UNDERWRITER)

            catalog = client.get(
                "/api/v1/products/catalog",
                params={"journey": "new_business"},
                headers=applicant,
            )
            assert catalog.status_code == 200, catalog.text
            motor = next(
                entry
                for entry in catalog.json()
                if entry["product_code"] == "motor-private-car"
            )
            assert motor["version"] == "v5"
            assert "prior_claims" not in {
                field["key"] for field in motor["fields"]
            }

            idempotency_key = str(uuid4())
            stale = create_case(
                client,
                applicant,
                "new_business",
                {**NEW_BUSINESS_PAYLOAD, "prior_claims": 0},
                idempotency_key,
            )
            assert stale.status_code == 422, stale.text
            assert (
                stale.json()["error"]["message"]
                == UNSUPPORTED_FIELD_DETAIL
            )

            created = create_case(
                client,
                applicant,
                "new_business",
                NEW_BUSINESS_PAYLOAD,
                idempotency_key,
            )
            assert created.status_code == 200, created.text
            assert created.json()["product_version"] == "v5"
            case_id = created.json()["id"]

            configuration = client.get(
                f"/api/v1/cases/{case_id}/configuration", headers=applicant
            )
            assert configuration.status_code == 200, configuration.text
            body = configuration.json()
            assert "prior_claims" not in {
                field["key"] for field in body["fields"]
            }
            assert body["application"] == NEW_BUSINESS_PAYLOAD

            replaced = client.put(
                f"/api/v1/cases/{case_id}/application",
                json={
                    "payload": {
                        **NEW_BUSINESS_PAYLOAD,
                        "prior_claims": 1,
                    },
                    "document_codes": [],
                },
                headers=applicant,
            )
            assert replaced.status_code == 422, replaced.text
            assert (
                replaced.json()["error"]["message"]
                == UNSUPPORTED_FIELD_DETAIL
            )
            unchanged = client.get(
                f"/api/v1/cases/{case_id}/configuration", headers=applicant
            )
            assert unchanged.json()["application"] == NEW_BUSINESS_PAYLOAD

            upload_documents(
                client, applicant, case_id, NEW_BUSINESS_UPLOADS
            )
            submitted = client.post(
                f"/api/v1/cases/{case_id}/submit", headers=applicant
            )
            assert submitted.status_code == 200, submitted.text
            assert submitted.json()["status"] == "underwriter_review"

            reviewed = client.post(
                f"/api/v1/reviews/{case_id}/start", headers=underwriter
            )
            assert reviewed.status_code == 200, reviewed.text
            review = reviewed.json()
            assert [
                fact["field_name"] for fact in review["submitted_facts"]
            ] == ["vehicle_age", "vehicle_use"]
            assert [
                check["check_code"] for check in review["reconciliation"]
            ] == MOTOR_ASSET_CHECKS
            assert review["missing_information"] == []
            assert all(
                item.get("field_name") != "prior_claims"
                for item in review["evidence"]
            )
            event_types = [
                event_type
                for _, event_type, _ in read_audit(UUID(case_id))
            ]
            assert event_types.count("case_created") == 1
    finally:
        if case_id:
            remove_case(case_id)
        set_motor_status("active", "v1")
        set_motor_status(prior, "v1")


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
