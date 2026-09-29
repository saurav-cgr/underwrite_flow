"""Underwriter case Q&A answers from pinned guidance or the fallback."""

import asyncio
import json
from collections.abc import Iterator
from pathlib import Path
from uuid import UUID, uuid4

import psycopg
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from fixtures.injection import (
    INJECTION_TEXT,
    clean_identity_pdf,
    injected_identity_pdf,
)
from fixtures.records import remove_case, seed_case, synthetic_user
from fixtures.support import ADMINISTRATOR, APPLICANT, login
from underwriteflow.app import create_app
from underwriteflow.config import Settings
from underwriteflow.database import Database
from underwriteflow.knowledge.questions import (
    FALLBACK_ANSWER,
    ask_question,
    list_questions,
)
from underwriteflow.persistence.models import Case, User
from underwriteflow.providers.embedding import FakeEmbeddingProvider
from underwriteflow.providers.guidance import (
    FakeGuidanceProvider,
    GuidanceCitation,
    GuidanceOutput,
    GuidanceRequest,
)

DATABASE_URL = (
    "postgresql+asyncpg://underwriteflow:synthetic-local-password"
    "@db:5433/underwriteflow"
)
SYNC_DATABASE_URL = (
    "postgresql://underwriteflow:synthetic-local-password"
    "@db:5433/underwriteflow"
)
COVERED_QUESTION = "Does a hazardous occupation need specialist review?"
UNCOVERED_QUESTION = "Zebra xylophone quokka?"


class RecordingProvider(FakeGuidanceProvider):
    """Fake provider that keeps every answer request for inspection."""

    # Start with no recorded requests and optional cited keys.
    def __init__(self, citation_keys: list[str] | None = None) -> None:
        super().__init__()
        self.requests: list[GuidanceRequest] = []
        self.citation_keys = citation_keys

    # Record the request, then answer with fixed or default citations.
    async def answer(self, request: GuidanceRequest) -> GuidanceOutput:
        self.requests.append(request)
        output = await super().answer(request)
        if self.citation_keys is None:
            return output
        version = output.citations[0].version
        return output.model_copy(
            update={
                "citations": [
                    GuidanceCitation(version=version, passage_key=key)
                    for key in self.citation_keys
                ]
            }
        )


# Import one fictional life guideline draft with fake embeddings.
@pytest.fixture(scope="module")
def guideline_id() -> str:
    path = Path("/app/knowledge-config/life-individual-term/g1.yaml")
    version = f"questions-{uuid4().hex[:10]}"
    corpus = path.read_text().replace("version: g1", f"version: {version}")
    with TestClient(create_app(Settings(generation_provider="fake"))) as client:
        imported = client.post(
            "/api/v1/knowledge/import",
            json={"scope": "guideline", "yaml": corpus},
            headers=login(client, ADMINISTRATOR),
        )
    assert imported.status_code == 201, imported.text
    return str(imported.json()["id"])


# Seed one standard-route case pinned to the draft guideline.
@pytest.fixture
def pinned_case(guideline_id: str) -> Iterator[UUID]:
    case_id = uuid4()
    seed_case(case_id)
    pin_and_route(case_id, guideline_id)
    try:
        yield case_id
    finally:
        remove_case(case_id)


# Pin a case to one guideline and store a standard recommendation.
def pin_and_route(case_id: UUID, guideline_id: str) -> None:
    with psycopg.connect(SYNC_DATABASE_URL) as connection:
        connection.execute(
            "INSERT INTO case_knowledge_pins (case_id, guideline_version_id)"
            " VALUES (%s, %s)",
            (case_id, guideline_id),
        )
        connection.execute(
            "INSERT INTO recommendations "
            "(id, case_id, route, status, summary, workflow_version) "
            "VALUES (gen_random_uuid(), %s, %s, %s, %s, %s)",
            (
                case_id,
                "standard",
                "pending_human_review",
                '{"recommendation":{"route":"standard"}}',
                "triage-v1",
            ),
        )


# Ask one question through the service and commit the stored exchange.
async def ask(
    case_id: UUID,
    question: str,
    provider: FakeGuidanceProvider,
    actor_id: UUID | None = None,
) -> dict[str, object]:
    database = Database(DATABASE_URL)
    try:
        async with database.session_factory() as session:
            case = await session.scalar(select(Case).where(Case.id == case_id))
            if actor_id is None:
                actor_id = await session.scalar(
                    select(User.id).where(User.role == "Underwriter")
                )
            result = await ask_question(
                session,
                provider,
                FakeEmbeddingProvider(),
                case,
                actor_id,
                question,
            )
            await session.commit()
            return result
    finally:
        await database.close()


# Read the stored history through the service.
async def history(case_id: UUID) -> list[dict[str, object]]:
    database = Database(DATABASE_URL)
    try:
        async with database.session_factory() as session:
            return await list_questions(session, case_id)
    finally:
        await database.close()


# Read audit details for one case and event type, oldest first.
def audit_rows(case_id: UUID, event_type: str) -> list[tuple]:
    with psycopg.connect(SYNC_DATABASE_URL) as connection:
        return connection.execute(
            "SELECT details, actor_user_id FROM audit_events "
            "WHERE case_id = %s AND event_type = %s ORDER BY occurred_at",
            (case_id, event_type),
        ).fetchall()


# Read the stored route for one case.
def stored_route(case_id: UUID) -> str:
    with psycopg.connect(SYNC_DATABASE_URL) as connection:
        row = connection.execute(
            "SELECT route FROM recommendations WHERE case_id = %s",
            (case_id,),
        ).fetchone()
    return row[0]


# Given a covered question, when asked, then it cites a pinned passage.
def test_covered_answer_cites_pinned_passage(
    pinned_case: UUID, guideline_id: str
) -> None:
    result = asyncio.run(
        ask(pinned_case, COVERED_QUESTION, RecordingProvider())
    )

    assert result["covered"] is True
    assert result["answer"] != FALLBACK_ANSWER
    keys = [item["passage_key"] for item in result["citations"]]
    assert keys
    with psycopg.connect(SYNC_DATABASE_URL) as connection:
        found = connection.execute(
            "SELECT count(*) FROM knowledge_passages "
            "WHERE version_id = %s AND passage_key = ANY(%s)",
            (guideline_id, keys),
        ).fetchone()
    assert found == (len(keys),)


# Given no retrieval hit, when asked, then fallback without a provider call.
def test_no_hit_returns_exact_fallback_without_provider(
    pinned_case: UUID,
) -> None:
    provider = RecordingProvider()

    result = asyncio.run(ask(pinned_case, UNCOVERED_QUESTION, provider))

    assert result["answer"] == "not covered by guidelines"
    assert result["covered"] is False
    assert result["citations"] == []
    assert provider.requests == []


# Given uncited provider output, when asked, then the fallback is stored.
def test_answer_without_valid_citations_becomes_fallback(
    pinned_case: UUID,
) -> None:
    provider = RecordingProvider(citation_keys=["not-a-pinned-key"])

    result = asyncio.run(ask(pinned_case, COVERED_QUESTION, provider))

    assert result["answer"] == FALLBACK_ANSWER
    assert result["covered"] is False
    assert result["citations"] == []
    dropped = audit_rows(pinned_case, "citation_dropped")
    assert [row[0]["passage_key"] for row in dropped] == ["not-a-pinned-key"]
    assert dropped[0][0]["output_kind"] == "case_answer"


# Given cited fallback text, when asked, then it is stored as not covered.
def test_cited_fallback_text_is_not_covered(pinned_case: UUID) -> None:
    provider = RecordingProvider(citation_keys=["life-occupation-hazardous"])
    provider.text_override = FALLBACK_ANSWER

    result = asyncio.run(ask(pinned_case, COVERED_QUESTION, provider))

    assert result["answer"] == FALLBACK_ANSWER
    assert result["covered"] is False
    assert result["citations"] == []


# Given one foreign citation, when asked, then only it is dropped and logged.
def test_foreign_citation_dropped_valid_citation_kept(
    pinned_case: UUID,
) -> None:
    provider = RecordingProvider(
        citation_keys=["life-occupation-hazardous", "absent-key"]
    )

    result = asyncio.run(ask(pinned_case, COVERED_QUESTION, provider))

    assert result["covered"] is True
    assert [item["passage_key"] for item in result["citations"]] == [
        "life-occupation-hazardous"
    ]
    dropped = audit_rows(pinned_case, "citation_dropped")
    assert [row[0]["passage_key"] for row in dropped] == ["absent-key"]


# Upload one identity PDF, submit through normal extraction, repin to draft.
def submit_life_case(document: bytes, guideline_id: str) -> UUID:
    with TestClient(create_app(Settings(generation_provider="fake"))) as client:
        applicant = login(client, APPLICANT)
        activated = client.post(
            "/api/v1/products/life-individual-term/activate",
            json={"version": "v3"},
            headers=login(client, ADMINISTRATOR),
        )
        assert activated.status_code == 200, activated.text
        created = client.post(
            "/api/v1/cases",
            json={
                "product_code": "life-individual-term",
                "idempotency_key": str(uuid4()),
                "payload": {
                    "requested_cover": 1_000_000,
                    "date_of_birth": "1990-01-01",
                    "occupation_type": "office",
                    "health_declaration": True,
                },
                "document_codes": ["identity_record"],
            },
            headers=applicant,
        )
        assert created.status_code == 200, created.text
        case_id = UUID(created.json()["id"])
        uploaded = client.post(
            f"/api/v1/cases/{case_id}/documents",
            files={"document": ("identity.pdf", document, "application/pdf")},
            data={"document_code": "identity_record"},
            headers=applicant,
        )
        assert uploaded.status_code == 200, uploaded.text
        submitted = client.post(
            f"/api/v1/cases/{case_id}/submit", headers=applicant
        )
        assert submitted.status_code == 200, submitted.text
    with psycopg.connect(SYNC_DATABASE_URL) as connection:
        connection.execute(
            "UPDATE case_knowledge_pins SET guideline_version_id = %s "
            "WHERE case_id = %s",
            (guideline_id, case_id),
        )
    return case_id


# Read one extracted field value stored by normal document extraction.
def extracted_value(case_id: UUID, field_name: str) -> object:
    with psycopg.connect(SYNC_DATABASE_URL) as connection:
        row = connection.execute(
            "SELECT value FROM extracted_fields "
            "WHERE case_id = %s AND field_name = %s",
            (case_id, field_name),
        ).fetchone()
    return row[0] if row else None


# Given an injected uploaded document, when asked, then it matches its twin.
def test_injection_is_untrusted_and_matches_clean_twin(
    guideline_id: str,
) -> None:
    injected_case = submit_life_case(injected_identity_pdf(), guideline_id)
    twin = submit_life_case(clean_identity_pdf(), guideline_id)
    try:
        injected_provider = RecordingProvider()
        injected = asyncio.run(
            ask(injected_case, COVERED_QUESTION, injected_provider)
        )
        clean = asyncio.run(ask(twin, COVERED_QUESTION, RecordingProvider()))
        assert extracted_value(injected_case, "holder_name") == INJECTION_TEXT
        assert extracted_value(twin, "holder_name") == "Synthetic Holder"
        assert stored_route(injected_case) == stored_route(twin)
        assert injected["covered"] is True
        assert injected["answer"] == clean["answer"]
        assert injected["citations"] == clean["citations"]
        request = injected_provider.requests[0]
        assert INJECTION_TEXT in json.dumps(request.untrusted)
        trusted = request.model_dump(exclude={"untrusted"})
        assert INJECTION_TEXT not in json.dumps(trusted, default=str)
        assert request.route == stored_route(twin)
    finally:
        remove_case(injected_case)
        remove_case(twin)


# Given an answer, when audited, then details hold ids and no question text.
def test_answer_audit_has_ids_without_question_text(
    pinned_case: UUID,
) -> None:
    result = asyncio.run(
        ask(pinned_case, COVERED_QUESTION, RecordingProvider())
    )

    rows = audit_rows(pinned_case, "case_question_answered")
    assert len(rows) == 1
    details, actor = rows[0]
    assert actor is not None
    assert details["case_id"] == str(pinned_case)
    assert details["question_id"] == str(result["id"])
    assert details["covered"] is True
    assert details["citation_keys"] == [
        item["passage_key"] for item in result["citations"]
    ]
    assert COVERED_QUESTION not in json.dumps(details)


# Given two underwriters, when history is read, then all rows oldest first.
def test_history_lists_every_underwriter_oldest_first(
    pinned_case: UUID,
) -> None:
    with synthetic_user(
        role="Underwriter", display_name="Second Synthetic Underwriter"
    ) as second:
        first = asyncio.run(
            ask(pinned_case, COVERED_QUESTION, RecordingProvider())
        )
        later = asyncio.run(
            ask(pinned_case, UNCOVERED_QUESTION, RecordingProvider(), second)
        )
        rows = asyncio.run(history(pinned_case))
        remove_case_questions(pinned_case)

    assert [row["id"] for row in rows] == [first["id"], later["id"]]
    assert rows[1]["asked_by"] == "Second Synthetic Underwriter"
    assert rows[0]["asked_by"] != rows[1]["asked_by"]


# Delete stored questions so the synthetic user can be removed first.
def remove_case_questions(case_id: UUID) -> None:
    with psycopg.connect(SYNC_DATABASE_URL) as connection:
        connection.execute(
            "DELETE FROM case_questions WHERE case_id = %s", (case_id,)
        )
