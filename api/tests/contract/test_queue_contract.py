"""Frozen JSON shape for the underwriter queue summary."""

from fastapi.testclient import TestClient

from fixtures.records import motor_status, remove_case, set_motor_status
from fixtures.support import (
    APPLICANT,
    UNDERWRITER,
    create_motor_case,
    login,
    submit_motor_case,
    upload_motor_documents,
)
from underwriteflow.app import create_app
from underwriteflow.config import Settings

QUEUE_ITEM_KEYS = {
    "case_id",
    "product_code",
    "journey",
    "status",
    "route",
    "selected_route",
    "specialist_label",
    "specialist",
    "awaiting_handoff",
    "reconciliation_status",
    "discrepancy_count",
    "missing_evidence_count",
}


# Pin the queue summary keys and the configured reconciliation counts.
def test_queue_item_reports_reconciliation_counts() -> None:
    prior = motor_status()
    set_motor_status("active")
    case_id = ""
    try:
        settings = Settings(generation_provider="fake")
        with TestClient(create_app(settings)) as client:
            applicant = login(client, APPLICANT)
            underwriter = login(client, UNDERWRITER)
            created = create_motor_case(client, applicant)
            case_id = str(created["id"])
            upload_motor_documents(client, applicant, case_id)
            submit_motor_case(client, applicant, case_id)

            listing = client.get("/api/v1/queues", headers=underwriter)
            assert listing.status_code == 200, listing.text
            item = next(
                entry
                for entry in listing.json()
                if entry["case_id"] == case_id
            )
            assert set(item) == QUEUE_ITEM_KEYS, item
            assert item["reconciliation_status"] == "CLEARED"
            assert item["discrepancy_count"] == 0
            assert item["missing_evidence_count"] == 0

            cleared = client.get(
                "/api/v1/queues",
                params={"reconciliation_status": "CLEARED"},
                headers=underwriter,
            )
            assert cleared.status_code == 200, cleared.text
            assert case_id in [
                entry["case_id"] for entry in cleared.json()
            ]

            flagged = client.get(
                "/api/v1/queues",
                params={"reconciliation_status": "FLAGGED_DISCREPANCY"},
                headers=underwriter,
            )
            assert flagged.status_code == 200, flagged.text
            assert case_id not in [
                entry["case_id"] for entry in flagged.json()
            ]
    finally:
        if case_id:
            remove_case(case_id)
        set_motor_status(prior)
