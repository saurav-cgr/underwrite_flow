"""Checkpoint and audit separation across a restarted application process.

The workflow keeps its resumable state in PostgreSQL, so a review must survive
a process that goes away mid-review, and replaying that resume must never
rewrite the audit history the first decision wrote.
"""

import asyncio
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from langgraph.types import Command

from fixtures.records import (
    count_handoffs,
    read_audit,
    read_decisions,
    remove_case,
    seed_case,
)
from fixtures.support import APPLICANT, UNDERWRITER, login
from underwriteflow.app import create_app
from underwriteflow.config import Settings
from underwriteflow.workflow.checkpoint import postgres_checkpointer
from underwriteflow.workflow.state import thread_config
from underwriteflow.workflow.triage import build_triage_graph


# Create a completed legacy specialist checkpoint without a database review.
async def complete_legacy_specialist_checkpoint(
    case_id: UUID,
    database_url: str,
) -> None:
    config = thread_config(str(case_id), 0)
    async with postgres_checkpointer(database_url) as checkpointer:
        graph = build_triage_graph(checkpointer=checkpointer)
        await graph.ainvoke(
            {
                "case_id": str(case_id),
                "evidence": [],
                "conflicts": [],
                "missing_information": [],
                "risk_signals": [],
                "validations": [],
                "low_confidence": True,
            },
            config=config,
        )
        await graph.ainvoke(
            Command(
                resume={
                    "action": "confirm",
                    "evidence_acknowledged": True,
                }
            ),
            config=config,
        )


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


# Verify a retry repairs only the label on a completed legacy checkpoint.
def test_recovered_checkpoint_requires_a_valid_specialist_label() -> None:
    case_id = uuid4()
    seed_case(case_id)
    settings = Settings(generation_provider="fake")
    try:
        asyncio.run(
            complete_legacy_specialist_checkpoint(
                case_id,
                settings.database_url,
            )
        )
        with TestClient(create_app(settings)) as client:
            underwriter = login(client, UNDERWRITER)
            invalid = client.post(
                f"/api/v1/reviews/{case_id}",
                json={
                    "action": "override",
                    "selected_route": "standard",
                    "specialist_label": "unknown desk",
                    "reason": "This retry cannot replace the decision.",
                    "evidence_acknowledged": True,
                },
                headers=underwriter,
            )
            assert invalid.status_code == 422, invalid.text
            assert read_decisions(case_id) == []

            repaired = client.post(
                f"/api/v1/reviews/{case_id}",
                json={
                    "action": "override",
                    "selected_route": "standard",
                    "specialist_label": "motor inspection",
                    "reason": "This retry cannot replace the decision.",
                    "evidence_acknowledged": True,
                },
                headers=underwriter,
            )
            assert repaired.status_code == 200, repaired.text
            assert repaired.json()["action"] == "confirm"
            assert repaired.json()["selected_route"] == "specialist"

        assert read_decisions(case_id) == [(0, "confirm", "specialist")]
    finally:
        remove_case(case_id)
