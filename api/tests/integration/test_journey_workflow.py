"""Renewal journey evidence and submission behaviour end to end."""

from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from fixtures.records import (
    motor_status,
    product_version_audit,
    read_audit,
    remove_case,
    set_motor_status,
)
from fixtures.support import (
    ADMINISTRATOR,
    APPLICANT,
    UNDERWRITER,
    activate_motor_version,
    create_case_for_journey,
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

# A v5 renewal record whose every answered field is also evidenced.
RENEWAL_V5_VEHICLE_LINES = [
    "vehicle_age: 3",
    "vehicle_use: personal",
    "prior_claims: 2",
    "claimed_ncb_percent: 0",
    "policy_start_date: 2025-09-01",
    "ncb_percent: 0",
    "policy_expiry: 2025-09-01",
]

# Prior-policy facts that agree with the v5 renewal application above.
RENEWAL_V5_POLICY_LINES = [
    "ncb_percent: 0",
    "policy_expiry: 2025-09-01",
]


# Verify v5 renewal keeps the prior-claims field, rule, and NCB check.
def test_renewal_v5_keeps_prior_claims_handling() -> None:
    prior = motor_status()
    case_ids: list[str] = []
    try:
        settings = Settings(generation_provider="fake")
        with TestClient(create_app(settings)) as client:
            admin = login(client, ADMINISTRATOR)
            activate_motor_version(client, admin, "v5")
            applicant = login(client, APPLICANT)
            underwriter = login(client, UNDERWRITER)

            catalog = client.get(
                "/api/v1/products/catalog",
                params={"journey": "renewal"},
                headers=applicant,
            )
            assert catalog.status_code == 200, catalog.text
            motor = next(
                entry
                for entry in catalog.json()
                if entry["product_code"] == "motor-private-car"
            )
            assert motor["version"] == "v5"
            assert "prior_claims" in {
                field["key"] for field in motor["fields"]
            }

            created = create_case_for_journey(
                client,
                applicant,
                "renewal",
                {
                    **RENEWAL_PAYLOAD,
                    "prior_claims": 2,
                    "claimed_ncb_percent": 0,
                },
                str(uuid4()),
            )
            assert created.status_code == 200, created.text
            assert created.json()["product_version"] == "v5"
            case_id = created.json()["id"]
            case_ids.append(case_id)

            configuration = client.get(
                f"/api/v1/cases/{case_id}/configuration", headers=applicant
            )
            fields = {
                field["key"]: field
                for field in configuration.json()["fields"]
            }
            assert fields["prior_claims"]["required"] is True
            assert fields["prior_claims"]["validation"] == {"minimum": 0}

            upload_documents(
                client,
                applicant,
                case_id,
                [
                    ("identity_record", text_pdf(IDENTITY_ONLY_LINES)),
                    (
                        "vehicle_record",
                        text_pdf(
                            RENEWAL_V5_VEHICLE_LINES
                            + REGISTRATION_CERTIFICATE_LINES
                        ),
                    ),
                    (
                        "registration_certificate",
                        text_pdf(REGISTRATION_CERTIFICATE_LINES),
                    ),
                    (
                        "previous_policy",
                        text_pdf(RENEWAL_V5_POLICY_LINES),
                    ),
                ],
            )
            submitted = client.post(
                f"/api/v1/cases/{case_id}/submit", headers=applicant
            )
            assert submitted.status_code == 200, submitted.text
            assert submitted.json()["status"] == "underwriter_review"
            assert (
                submitted.json()["recommendation"]["route"] == "standard"
            )

            reviewed = client.post(
                f"/api/v1/reviews/{case_id}/start", headers=underwriter
            )
            assert reviewed.status_code == 200, reviewed.text
            review = reviewed.json()
            facts = {
                fact["field_name"]: fact["value"]
                for fact in review["submitted_facts"]
            }
            assert facts["prior_claims"] == 2
            checks = {
                check["check_code"]: check
                for check in review["reconciliation"]
            }
            assert checks["motor_ncb_match"]["status"] == "CLEARED"

            incomplete = create_case_for_journey(
                client,
                applicant,
                "renewal",
                {
                    key: value
                    for key, value in RENEWAL_PAYLOAD.items()
                    if key != "prior_claims"
                },
                str(uuid4()),
            )
            assert incomplete.status_code == 200, incomplete.text
            incomplete_id = incomplete.json()["id"]
            case_ids.append(incomplete_id)

            refused = client.post(
                f"/api/v1/cases/{incomplete_id}/submit", headers=applicant
            )
            assert refused.status_code == 422, refused.text
            assert (
                refused.json()["error"]["message"]
                == "missing field: prior_claims"
            )
    finally:
        for case_id in case_ids:
            remove_case(case_id)
        set_motor_status("active", "v1")
        set_motor_status(prior, "v1")


# Verify v5 activation leaves an earlier pinned case and its history intact.
def test_v5_activation_keeps_an_earlier_case_pinned() -> None:
    prior = motor_status()
    case_ids: list[str] = []
    try:
        settings = Settings(generation_provider="fake")
        with TestClient(create_app(settings)) as client:
            admin = login(client, ADMINISTRATOR)
            activate_motor_version(client, admin, "v4")
            applicant = login(client, APPLICANT)

            pinned = create_case_for_journey(
                client,
                applicant,
                "new_business",
                {
                    "vehicle_age": 3,
                    "vehicle_use": "personal",
                    "prior_claims": 0,
                },
                str(uuid4()),
            )
            assert pinned.status_code == 200, pinned.text
            assert pinned.json()["product_version"] == "v4"
            assert pinned.json()["rulebook_version"] == "v4"
            pinned_id = pinned.json()["id"]
            case_ids.append(pinned_id)
            before = client.get(
                f"/api/v1/cases/{pinned_id}/configuration", headers=applicant
            ).json()
            audit_before = read_audit(UUID(pinned_id))

            imports = product_version_audit("v5")
            activate_motor_version(client, admin, "v5")
            activations = product_version_audit("v5")

            after = client.get(
                f"/api/v1/cases/{pinned_id}/configuration", headers=applicant
            ).json()
            replaced = client.put(
                f"/api/v1/cases/{pinned_id}/application",
                json={"payload": before["application"], "document_codes": []},
                headers=applicant,
            )

            current = create_case_for_journey(
                client,
                applicant,
                "new_business",
                {"vehicle_age": 4, "vehicle_use": "personal"},
                str(uuid4()),
            )
            assert current.status_code == 200, current.text
            assert current.json()["product_version"] == "v5"
            assert current.json()["rulebook_version"] == "v5"
            current_id = current.json()["id"]
            case_ids.append(current_id)
            current_fields = client.get(
                f"/api/v1/cases/{current_id}/configuration", headers=applicant
            ).json()["fields"]

        assert after == before
        assert after["product_version"] == "v4"
        assert "prior_claims" in {field["key"] for field in after["fields"]}
        assert read_audit(UUID(pinned_id))[: len(audit_before)] == audit_before
        assert replaced.status_code == 200, replaced.text
        assert "prior_claims" not in {field["key"] for field in current_fields}
        assert len(activations) == len(imports) + 1
        assert activations[-1] == ("configuration_activated", ADMINISTRATOR[0])
        assert ("configuration_imported", ADMINISTRATOR[0]) in imports
    finally:
        for case_id in case_ids:
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
            activate_motor_version(client, admin, "v4")
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
            activate_motor_version(client, admin, "v4")
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
            activate_motor_version(client, admin, "v4")
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
