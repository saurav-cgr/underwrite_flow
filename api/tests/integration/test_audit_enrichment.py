"""Append-only audit events carry the full decision and provenance chain."""

from uuid import uuid4

from fastapi.testclient import TestClient
from fixtures.records import set_motor_status
from fixtures.support import (
    create_motor_case,
    submit_motor_case,
    upload_motor_documents,
)
from fixtures.synthetic_pdf import (
    IDENTITY_ONLY_LINES,
    MOTOR_EVIDENCE_LINES,
    text_pdf,
)

from underwriteflow.app import create_app
from underwriteflow.config import Settings

APPLICANT = ("applicant@synthetic.test", "underwriteflow-demo-applicant")
UNDERWRITER = ("underwriter@synthetic.test", "underwriteflow-demo-underwriter")
ADMIN = (
    "administrator@synthetic.test",
    "underwriteflow-demo-administrator",
)



# Log in one fictional demo role and return bearer headers.
def login(client: TestClient, credentials: tuple[str, str]) -> dict[str, str]:
    email, password = credentials
    response = client.post(
        "/api/v1/auth/session",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['token']}"}


# Read the sanitized audit trail for one case keyed by event type.
def audit_by_type(
    client: TestClient, case_id: str, headers: dict[str, str]
) -> dict:
    response = client.get(f"/api/v1/audit/cases/{case_id}", headers=headers)
    assert response.status_code == 200, response.text
    return {event["event_type"]: event["details"] for event in response.json()}


# Verify the audit trail records identity, provenance, decisions, and handoff.
def test_audit_events_record_the_full_decision_chain() -> None:
    set_motor_status("active")
    try:
        with TestClient(
            create_app(Settings(generation_provider="fake"))
        ) as client:
            applicant = login(client, APPLICANT)
            underwriter = login(client, UNDERWRITER)
            admin = login(client, ADMIN)
            created = client.post(
                "/api/v1/cases",
                json={
                    "product_code": "motor-private-car",
                    "idempotency_key": str(uuid4()),
                    "payload": {
                        "vehicle_age": 2,
                        "vehicle_use": "personal",
                        "prior_claims": 0,
                    },
                    "document_codes": ["identity_record", "vehicle_record"],
                },
                headers=applicant,
            )
            assert created.status_code == 200, created.text
            case_id = created.json()["id"]

            for code, lines in (
                ("identity_record", IDENTITY_ONLY_LINES),
                ("vehicle_record", MOTOR_EVIDENCE_LINES),
            ):
                uploaded = client.post(
                    f"/api/v1/cases/{case_id}/documents",
                    files={
                        "document": (
                            "synthetic.pdf",
                            text_pdf(lines),
                            "application/pdf",
                        )
                    },
                    data={"document_code": code},
                    headers=applicant,
                )
                assert uploaded.status_code == 200, uploaded.text

            submitted = client.post(
                f"/api/v1/cases/{case_id}/submit", headers=applicant
            )
            assert submitted.status_code == 200, submitted.text
            assert client.post(
                f"/api/v1/reviews/{case_id}/start", headers=underwriter
            ).status_code == 200
            assert client.post(
                f"/api/v1/reviews/{case_id}",
                json={
                    "action": "override",
                    "selected_route": "specialist",
                    "specialist_label": "motor inspection",
                    "reason": "Synthetic demonstration override",
                    "evidence_acknowledged": True,
                },
                headers=underwriter,
            ).status_code == 200
            completed = client.post(
                f"/api/v1/completion/{case_id}", headers=underwriter
            )
            assert completed.status_code == 200, completed.text

            audit = audit_by_type(client, case_id, admin)

    finally:
        set_motor_status("draft")

    created_details = audit["case_created"]
    assert created_details["product_version_id"]
    assert created_details["product_version"]
    assert created_details["product_content_hash"]
    assert created_details["rulebook_version_id"]
    assert created_details["rulebook_content_hash"]

    uploaded_details = audit["document_uploaded"]
    assert uploaded_details["document_id"]
    assert uploaded_details["content_hash"]
    assert uploaded_details["byte_size"] > 0

    cycle = audit["case_submitted"]
    assert cycle["recommendation"] == "expedited"
    assert cycle["review_cycle"] == 0
    assert cycle["workflow_version"] == "evidence-v1"
    assert {item["field_name"] for item in cycle["evidence_provenance"]} >= {
        "vehicle_age",
        "vehicle_use",
        "prior_claims",
    }
    assert all(
        item["source_locator"] for item in cycle["evidence_provenance"]
    )
    assert len(cycle["documents"]) == 2
    assert all(item["content_hash"] for item in cycle["documents"])
    assert cycle["rulebook_version_id"]
    assert cycle["missing_information"] == []
    assert cycle["conflicts"] == []

    review = audit["underwriter_reviewed"]
    assert review["review_id"]
    assert review["review_cycle"] == 0
    assert review["action"] == "override"
    assert review["recommended_route"] == "expedited"
    assert review["selected_route"] == "specialist"
    assert review["specialist_label"] == "motor inspection"
    assert review["reason"] == "Synthetic demonstration override"

    completion = audit["case_completed"]
    assert completion["handoff_id"]
    assert completion["destination"] == "completed_queue"
    assert completion["idempotency_key"]
    assert completion["route"] == "specialist"
    assert completion["specialist_label"] == "motor inspection"
    assert completion["review_id"] == review["review_id"]


# Verify the audit trail reports real conflicts and gaps, not placeholders.
def test_audit_records_detected_conflicts_and_missing_fields() -> None:
    set_motor_status("active")
    try:
        with TestClient(
            create_app(Settings(generation_provider="fake"))
        ) as client:
            applicant = login(client, APPLICANT)
            admin = login(client, ADMIN)
            created = client.post(
                "/api/v1/cases",
                json={
                    "product_code": "motor-private-car",
                    "idempotency_key": str(uuid4()),
                    "payload": {
                        "vehicle_age": 2,
                        "vehicle_use": "personal",
                        "prior_claims": 0,
                    },
                    "document_codes": ["identity_record", "vehicle_record"],
                },
                headers=applicant,
            )
            assert created.status_code == 200, created.text
            case_id = created.json()["id"]

            uploads = (
                ("identity_record", IDENTITY_ONLY_LINES),
                ("vehicle_record", ["vehicle_age: 2", "vehicle_use: personal"]),
                ("vehicle_record", ["vehicle_age: 9", "vehicle_use: personal"]),
            )
            for code, lines in uploads:
                uploaded = client.post(
                    f"/api/v1/cases/{case_id}/documents",
                    files={
                        "document": (
                            "synthetic.pdf",
                            text_pdf(lines),
                            "application/pdf",
                        )
                    },
                    data={"document_code": code},
                    headers=applicant,
                )
                assert uploaded.status_code == 200, uploaded.text

            submitted = client.post(
                f"/api/v1/cases/{case_id}/submit", headers=applicant
            )
            assert submitted.status_code == 200, submitted.text
            audit = audit_by_type(client, case_id, admin)
    finally:
        set_motor_status("draft")

    cycle = audit["case_submitted"]
    assert "vehicle_age" in cycle["conflicts"]
    assert "prior_claims" in cycle["missing_information"]
    assert cycle["recommendation"] == "needs_information"
    assert len(cycle["documents"]) == 3
    assert cycle["evidence_provenance"]


# Verify each document branch records provider, usage, attempts, and hashes.
def test_audit_records_provider_metadata_and_hashes() -> None:
    set_motor_status("active")
    try:
        with TestClient(
            create_app(Settings(generation_provider="fake"))
        ) as client:
            applicant = login(client, APPLICANT)
            admin = login(client, ADMIN)
            created = create_motor_case(client, applicant)
            case_id = str(created["id"])
            upload_motor_documents(client, applicant, case_id)
            submit_motor_case(client, applicant, case_id)
            audit = audit_by_type(client, case_id, admin)
    finally:
        set_motor_status("draft")

    calls = audit["case_submitted"]["provider_calls"]
    assert len(calls) == 2
    assert {call["document_code"] for call in calls} == {
        "identity_record",
        "vehicle_record",
    }
    assert {call["provider"] for call in calls} == {"fake"}
    assert {call["attempts"] for call in calls} == {1}
    assert {call["usage_unavailable"] for call in calls} == {True}
    assert {call["model"] for call in calls} == {None}
    assert {call["error_code"] for call in calls} == {None}
    assert all(call["request_hash"] for call in calls)
    assert all(call["result_hash"] for call in calls)
    # Ordering is deterministic, and every call links to a consumed document.
    assert [call["document_id"] for call in calls] == sorted(
        call["document_id"] for call in calls
    )
    assert {call["document_id"] for call in calls} == {
        document["document_id"]
        for document in audit["case_submitted"]["documents"]
    }


# Verify a later cycle and a later human decision supersede earlier events.
def test_audit_links_each_superseded_event() -> None:
    set_motor_status("active")
    try:
        with TestClient(
            create_app(Settings(generation_provider="fake"))
        ) as client:
            applicant = login(client, APPLICANT)
            underwriter = login(client, UNDERWRITER)
            admin = login(client, ADMIN)
            created = create_motor_case(client, applicant)
            case_id = str(created["id"])
            for code, lines in (
                ("identity_record", IDENTITY_ONLY_LINES),
                ("vehicle_record", ["vehicle_age: 2", "vehicle_use: personal"]),
            ):
                uploaded = client.post(
                    f"/api/v1/cases/{case_id}/documents",
                    files={
                        "document": (
                            "synthetic.pdf",
                            text_pdf(lines),
                            "application/pdf",
                        )
                    },
                    data={"document_code": code},
                    headers=applicant,
                )
                assert uploaded.status_code == 200, uploaded.text
            assert client.post(
                f"/api/v1/cases/{case_id}/submit", headers=applicant
            ).status_code == 200
            assert client.post(
                f"/api/v1/reviews/{case_id}/start", headers=underwriter
            ).status_code == 200
            assert client.post(
                f"/api/v1/reviews/{case_id}",
                json={
                    "action": "request_information",
                    "reason": "Synthetic gap in the vehicle record",
                    "evidence_acknowledged": True,
                },
                headers=underwriter,
            ).status_code == 200
            resubmitted = client.post(
                f"/api/v1/cases/{case_id}/resubmit", headers=applicant
            )
            assert resubmitted.status_code == 200, resubmitted.text
            assert client.post(
                f"/api/v1/reviews/{case_id}/start", headers=underwriter
            ).status_code == 200
            assert client.post(
                f"/api/v1/reviews/{case_id}",
                json={
                    "action": "override",
                    "selected_route": "specialist",
                    "specialist_label": "motor inspection",
                    "reason": "Synthetic demonstration override",
                    "evidence_acknowledged": True,
                },
                headers=underwriter,
            ).status_code == 200
            response = client.get(
                f"/api/v1/audit/cases/{case_id}", headers=admin
            )
            assert response.status_code == 200, response.text
            events = response.json()
    finally:
        set_motor_status("draft")

    submissions = [
        event
        for event in events
        if event["event_type"] in {"case_submitted", "case_resubmitted"}
    ]
    reviews = [
        event
        for event in events
        if event["event_type"] == "underwriter_reviewed"
    ]
    assert [event["event_type"] for event in submissions] == [
        "case_submitted",
        "case_resubmitted",
    ]
    assert submissions[0]["details"]["review_cycle"] == 0
    assert submissions[1]["details"]["review_cycle"] == 1
    assert "supersedes_event_id" not in submissions[0]["details"]
    assert (
        submissions[1]["details"]["supersedes_event_id"]
        == submissions[0]["id"]
    )
    assert [event["details"]["action"] for event in reviews] == [
        "request_information",
        "override",
    ]
    assert "supersedes_event_id" not in reviews[0]["details"]
    assert reviews[1]["details"]["supersedes_event_id"] == reviews[0]["id"]
