"""Journey exposure across queue, review, audit, and completion views."""

from fastapi.testclient import TestClient

from fixtures.records import remove_case
from fixtures.support import (
    ADMINISTRATOR,
    APPLICANT,
    UNDERWRITER,
    create_motor_case,
    login,
    start_review,
    submit_motor_case,
    upload_motor_documents,
)
from underwriteflow.app import create_app
from underwriteflow.config import Settings


# Verify journey flows through queue, review, audit, and completion views.
def test_journey_appears_in_queue_review_audit_and_completion() -> None:
    case_id = ""
    try:
        settings = Settings(generation_provider="fake")
        with TestClient(create_app(settings)) as client:
            applicant = login(client, APPLICANT)
            underwriter = login(client, UNDERWRITER)
            created = create_motor_case(client, applicant)
            assert created["journey"] == "new_business"
            case_id = created["id"]
            upload_motor_documents(client, applicant, case_id)
            submit_motor_case(client, applicant, case_id)

            matching = client.get(
                "/api/v1/queues",
                params={"journey": "new_business"},
                headers=underwriter,
            )
            assert matching.status_code == 200, matching.text
            queued = next(
                item
                for item in matching.json()
                if item["case_id"] == case_id
            )
            assert queued["journey"] == "new_business"

            excluded = client.get(
                "/api/v1/queues",
                params={"journey": "renewal"},
                headers=underwriter,
            )
            assert excluded.status_code == 200, excluded.text
            assert all(
                item["case_id"] != case_id for item in excluded.json()
            )

            started = start_review(client, underwriter, case_id)
            assert started["journey"] == "new_business"

            decided = client.post(
                f"/api/v1/reviews/{case_id}",
                json={"action": "confirm", "evidence_acknowledged": True},
                headers=underwriter,
            )
            assert decided.status_code == 200, decided.text
            assert decided.json()["journey"] == "new_business"

            completed = client.post(
                f"/api/v1/completion/{case_id}", headers=underwriter
            )
            assert completed.status_code == 200, completed.text
            assert completed.json()["journey"] == "new_business"

            repeated = client.post(
                f"/api/v1/completion/{case_id}", headers=underwriter
            )
            assert repeated.status_code == 200, repeated.text
            assert repeated.json() == completed.json()

            administrator = login(client, ADMINISTRATOR)
            audit = client.get(
                f"/api/v1/audit/cases/{case_id}", headers=administrator
            )
            assert audit.status_code == 200, audit.text
            events = {
                event["event_type"]: event["details"]
                for event in audit.json()
            }
            assert events["case_created"]["journey"] == "new_business"
            assert events["document_uploaded"]["journey"] == "new_business"
            assert events["case_submitted"]["journey"] == "new_business"
            assert events["underwriter_reviewed"]["journey"] == (
                "new_business"
            )
            assert events["case_completed"]["journey"] == "new_business"
    finally:
        if case_id:
            remove_case(case_id)
