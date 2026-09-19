"""Frozen audit-history contract: authorized filtering, read-only access."""

from fastapi.testclient import TestClient
from fixtures.records import motor_status, remove_case, set_motor_status
from fixtures.support import (
    ADMINISTRATOR,
    APPLICANT,
    UNDERWRITER,
    create_motor_case,
    login,
    submit_motor_case,
    upload_motor_documents,
)

from underwriteflow.app import create_app
from underwriteflow.config import Settings

AUDIT_EVENT_KEYS = {
    "id",
    "case_id",
    "actor_user_id",
    "event_type",
    "details",
    "occurred_at",
    "supersedes_event_id",
}


# Read one case's audit history as an authorized administrator.
def read_audit(
    client: TestClient, headers: dict[str, str], case_id: str, query: str
) -> list[dict]:
    response = client.get(
        f"/api/v1/audit/cases/{case_id}{query}", headers=headers
    )
    assert response.status_code == 200, response.text
    return response.json()


# Pin the audit view shape and prove authorized filtering narrows history.
def test_audit_history_is_filterable_and_read_only() -> None:
    prior = motor_status()
    set_motor_status("active")
    case_id = ""
    try:
        settings = Settings(generation_provider="fake")
        with TestClient(create_app(settings)) as client:
            applicant = login(client, APPLICANT)
            admin = login(client, ADMINISTRATOR)
            created = create_motor_case(client, applicant)
            case_id = str(created["id"])
            upload_motor_documents(client, applicant, case_id)
            submit_motor_case(client, applicant, case_id)

            events = read_audit(client, admin, case_id, "")
            assert [event["event_type"] for event in events][-1] == (
                "case_submitted"
            )
            for event in events:
                assert set(event) == AUDIT_EVENT_KEYS, event
                assert str(event["case_id"]) == case_id
                assert event["supersedes_event_id"] is None

            filtered = read_audit(
                client, admin, case_id, "?event_type=case_submitted"
            )
            assert [event["event_type"] for event in filtered] == [
                "case_submitted"
            ]
            limited = read_audit(client, admin, case_id, "?limit=1")
            assert [event["id"] for event in limited] == [events[0]["id"]]

            # Audit history is readable only with the audit scope.
            for headers in (
                applicant,
                login(client, UNDERWRITER),
            ):
                denied = client.get(
                    f"/api/v1/audit/cases/{case_id}", headers=headers
                )
                assert denied.status_code == 403, denied.text

            # The audit boundary is read-only: no mutation route exists.
            posted = client.post(
                f"/api/v1/audit/cases/{case_id}", headers=admin
            )
            assert posted.status_code == 405, posted.text
    finally:
        if case_id:
            remove_case(case_id)
        set_motor_status(prior)
