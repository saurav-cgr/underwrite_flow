"""Frozen journey-aware contracts: create, application replace, catalogue.

Split from ``test_case_contract.py`` so journey-specific behaviour has a
dedicated home as the feature grows.
"""

from uuid import uuid4

from fastapi.testclient import TestClient

from fixtures.records import motor_status, remove_case, set_motor_status
from fixtures.support import ADMINISTRATOR, APPLICANT, UNDERWRITER, login
from underwriteflow.app import create_app
from underwriteflow.config import Settings

# Activate motor v4 for the duration of one test and always restore v1.
def activate_motor_v4(client: TestClient) -> dict[str, str]:
    admin = login(client, ADMINISTRATOR)
    activated = client.post(
        "/api/v1/products/motor-private-car/activate",
        json={"version": "v4"},
        headers=admin,
    )
    assert activated.status_code == 200, activated.text
    return admin


# Verify a case defaults to the new-business journey when none is given.
def test_create_case_defaults_to_new_business_journey() -> None:
    prior = motor_status()
    set_motor_status("active", "v1")
    case_id = ""
    try:
        settings = Settings(generation_provider="fake")
        with TestClient(create_app(settings)) as client:
            applicant = login(client, APPLICANT)
            created = client.post(
                "/api/v1/cases",
                json={
                    "product_code": "motor-private-car",
                    "idempotency_key": str(uuid4()),
                    "payload": {"vehicle_age": 2},
                    "document_codes": [],
                },
                headers=applicant,
            )
            assert created.status_code == 200, created.text
            case_id = created.json()["id"]
            assert created.json()["journey"] == "new_business"
    finally:
        if case_id:
            remove_case(case_id)
        set_motor_status(prior, "v1")


# Verify a renewal case is created and pinned to the chosen journey.
def test_create_case_persists_chosen_journey() -> None:
    prior = motor_status()
    case_id = ""
    try:
        settings = Settings(generation_provider="fake")
        with TestClient(create_app(settings)) as client:
            activate_motor_v4(client)
            applicant = login(client, APPLICANT)
            created = client.post(
                "/api/v1/cases",
                json={
                    "product_code": "motor-private-car",
                    "idempotency_key": str(uuid4()),
                    "journey": "renewal",
                    "payload": {"vehicle_age": 3},
                    "document_codes": [],
                },
                headers=applicant,
            )
            assert created.status_code == 200, created.text
            case_id = created.json()["id"]
            assert created.json()["journey"] == "renewal"
    finally:
        if case_id:
            remove_case(case_id)
        set_motor_status("active", "v1")
        set_motor_status(prior, "v1")


# Verify the catalogue excludes a product that does not support a journey.
def test_catalog_journey_filter_excludes_unsupported_products() -> None:
    prior = motor_status()
    set_motor_status("active", "v1")
    try:
        settings = Settings(generation_provider="fake")
        with TestClient(create_app(settings)) as client:
            applicant = login(client, APPLICANT)
            renewal_catalog = client.get(
                "/api/v1/products/catalog?journey=renewal",
                headers=applicant,
            )
            assert renewal_catalog.status_code == 200, renewal_catalog.text
            offered = {
                entry["product_code"] for entry in renewal_catalog.json()
            }
            # The active v1 motor configuration only supports new business.
            assert "motor-private-car" not in offered
    finally:
        set_motor_status(prior, "v1")


# Verify an owner may replace a draft's answers before review starts.
def test_replace_application_updates_the_stored_draft() -> None:
    prior = motor_status()
    case_id = ""
    try:
        settings = Settings(generation_provider="fake")
        with TestClient(create_app(settings)) as client:
            applicant = login(client, APPLICANT)
            created = client.post(
                "/api/v1/cases",
                json={
                    "product_code": "motor-private-car",
                    "idempotency_key": str(uuid4()),
                    "payload": {},
                    "document_codes": [],
                },
                headers=applicant,
            )
            assert created.status_code == 200, created.text
            case_id = created.json()["id"]

            replaced = client.put(
                f"/api/v1/cases/{case_id}/application",
                json={
                    "payload": {"vehicle_age": 5},
                    "document_codes": [],
                },
                headers=applicant,
            )
            assert replaced.status_code == 200, replaced.text

            configuration = client.get(
                f"/api/v1/cases/{case_id}/configuration", headers=applicant
            )
            assert configuration.status_code == 200, configuration.text
    finally:
        if case_id:
            remove_case(case_id)
        set_motor_status(prior, "v1")


# Verify a second applicant may not replace another applicant's draft.
def test_replace_application_is_owner_only() -> None:
    prior = motor_status()
    case_id = ""
    try:
        settings = Settings(generation_provider="fake")
        with TestClient(create_app(settings)) as client:
            applicant = login(client, APPLICANT)
            underwriter = login(client, UNDERWRITER)
            created = client.post(
                "/api/v1/cases",
                json={
                    "product_code": "motor-private-car",
                    "idempotency_key": str(uuid4()),
                    "payload": {},
                    "document_codes": [],
                },
                headers=applicant,
            )
            assert created.status_code == 200, created.text
            case_id = created.json()["id"]

            denied = client.put(
                f"/api/v1/cases/{case_id}/application",
                json={"payload": {}, "document_codes": []},
                headers=underwriter,
            )
            assert denied.status_code == 403, denied.text
    finally:
        if case_id:
            remove_case(case_id)
        set_motor_status(prior, "v1")
