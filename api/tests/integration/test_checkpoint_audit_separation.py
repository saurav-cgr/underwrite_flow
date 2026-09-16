"""Checkpoint and audit separation across a restarted application process.

The workflow keeps its resumable state in PostgreSQL, so a review must survive
a process that goes away mid-review, and replaying that resume must never
rewrite the audit history the first decision wrote.
"""

from uuid import uuid4

from fastapi.testclient import TestClient

from review_support import (
    APPLICANT,
    UNDERWRITER,
    count_handoffs,
    login,
    read_audit,
    read_decisions,
    remove_case,
    seed_case,
)
from underwriteflow.app import create_app
from underwriteflow.config import Settings


# Verify a review decision resumes from a checkpoint another process wrote.
def test_review_resumes_after_the_application_restarts() -> None:
    case_id = uuid4()
    seed_case(case_id)
    settings = Settings(generation_provider="fake")
    try:
        # First process: the applicant submits, so the case stops at the human
        # interrupt and its checkpoint lands in PostgreSQL.
        with TestClient(create_app(settings)) as first:
            submitted = first.post(
                f"/api/v1/cases/{case_id}/submit",
                headers=login(first, APPLICANT),
            )
            assert submitted.status_code == 200, submitted.text
            assert submitted.json()["status"] == "underwriter_review"

        # The first process is gone; nothing about this case is in memory.
        with TestClient(create_app(settings)) as second:
            underwriter = login(second, UNDERWRITER)
            opened = second.post(
                f"/api/v1/reviews/{case_id}/start", headers=underwriter
            )
            assert opened.status_code == 200, opened.text
            assert opened.json()["recommendation"]["route"] == "expedited"

            decided = second.post(
                f"/api/v1/reviews/{case_id}",
                json={"action": "confirm", "evidence_acknowledged": True},
                headers=underwriter,
            )
            assert decided.status_code == 200, decided.text
            assert decided.json()["status"] == "confirmed"
            assert decided.json()["selected_route"] == "expedited"

            completed = second.post(
                f"/api/v1/completion/{case_id}", headers=underwriter
            )
            assert completed.status_code == 200, completed.text

        assert read_decisions(case_id) == [(0, "confirm", "expedited")]
        assert count_handoffs(case_id) == 1
    finally:
        remove_case(case_id)


# Verify replaying a resume returns the first decision without rewriting audit.
def test_repeated_resume_cannot_rewrite_audit_history() -> None:
    case_id = uuid4()
    seed_case(case_id)
    try:
        settings = Settings(generation_provider="fake")
        with TestClient(create_app(settings)) as client:
            underwriter = login(client, UNDERWRITER)
            submitted = client.post(
                f"/api/v1/cases/{case_id}/submit",
                headers=login(client, APPLICANT),
            )
            assert submitted.status_code == 200, submitted.text

            first = client.post(
                f"/api/v1/reviews/{case_id}",
                json={
                    "action": "override",
                    "selected_route": "standard",
                    "reason": "Synthetic demonstration override.",
                    "evidence_acknowledged": True,
                },
                headers=underwriter,
            )
            assert first.status_code == 200, first.text
            assert first.json()["selected_route"] == "standard"

            history = read_audit(case_id)

            # A second resume for the same cycle cannot change the recorded
            # decision, nor the rows the first decision appended.
            second = client.post(
                f"/api/v1/reviews/{case_id}",
                json={"action": "confirm", "evidence_acknowledged": True},
                headers=underwriter,
            )
            assert second.status_code == 200, second.text
            assert second.json()["action"] == "override"
            assert second.json()["selected_route"] == "standard"

        assert read_audit(case_id) == history
        assert read_decisions(case_id) == [(0, "override", "standard")]
    finally:
        remove_case(case_id)
