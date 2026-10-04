"""Stored route explanation survives reads and duplicate writes."""

import asyncio
from collections.abc import Iterator
from pathlib import Path
from uuid import uuid4

import psycopg
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text

from fixtures.records import remove_case, seed_case
from fixtures.support import ADMINISTRATOR, APPLICANT, UNDERWRITER, login
from fixtures.synthetic_pdf import blank_pdf
from underwriteflow.app import create_app
from underwriteflow.config import Settings
from underwriteflow.database import Database
from underwriteflow.evaluation.runner import evaluate_cases
from underwriteflow.knowledge.case_guidance import store_route_explanation
from underwriteflow.knowledge.explainer import RouteExplainer
from underwriteflow.persistence.models import Case, User
from underwriteflow.providers.embedding import FakeEmbeddingProvider
from underwriteflow.providers.guidance import FakeGuidanceProvider

DATABASE_URL = (
    "postgresql+asyncpg://underwriteflow:synthetic-local-password"
    "@db:5433/underwriteflow"
)
SYNC_DATABASE_URL = (
    "postgresql://underwriteflow:synthetic-local-password"
    "@db:5433/underwriteflow"
)


# Load one fictional life corpus under a unique version identity.
def life_corpus(version: str) -> str:
    path = Path("/app/knowledge-config/life-individual-term/g1.yaml")
    if not path.exists():
        path = Path("knowledge-config/life-individual-term/g1.yaml")
    return path.read_text().replace("version: g1", f"version: {version}")


# Import one synthetic guideline through the administrator API.
def import_guideline(
    client: TestClient, admin: dict[str, str], version: str
) -> str:
    imported = client.post(
        "/api/v1/knowledge/import",
        json={"scope": "guideline", "yaml": life_corpus(version)},
        headers=admin,
    )
    assert imported.status_code == 201, imported.text
    return str(imported.json()["id"])


# Activate one imported synthetic guideline for the submission test.
def activate_guideline(
    client: TestClient, admin: dict[str, str], version: str
) -> str:
    version_id = import_guideline(client, admin, version)
    activated = client.post(
        f"/api/v1/knowledge/versions/{version_id}/activate",
        headers=admin,
    )
    assert activated.status_code == 200, activated.text
    return version_id


# Read the active life guideline id, if the stack has one.
def active_guideline_id() -> str | None:
    with psycopg.connect(SYNC_DATABASE_URL) as connection:
        row = connection.execute(
            "SELECT k.id FROM knowledge_versions k JOIN products p"
            " ON p.id = k.product_id WHERE k.scope = 'guideline'"
            " AND k.status = 'active' AND p.code = 'life-individual-term'"
        ).fetchone()
    return str(row[0]) if row else None


# Activate a unique life guideline, then restore its exact prior state.
@pytest.fixture
def active_guideline() -> Iterator[None]:
    with psycopg.connect(SYNC_DATABASE_URL) as connection:
        prior = connection.execute(
            "SELECT id, status, activated_at FROM knowledge_versions "
            "WHERE product_id = (SELECT id FROM products WHERE code = %s) "
            "AND scope = %s",
            ("life-individual-term", "guideline"),
        ).fetchall()
    with TestClient(create_app(Settings(generation_provider="fake"))) as client:
        admin = login(client, ADMINISTRATOR)
        own = activate_guideline(client, admin, f"guidance-{uuid4().hex[:10]}")
        yield
        retired = client.post(
            f"/api/v1/knowledge/versions/{own}/retire",
            headers=admin,
        )
        assert retired.status_code == 200, retired.text
        with psycopg.connect(SYNC_DATABASE_URL) as connection:
            connection.execute(
                "UPDATE knowledge_versions SET status = %s "
                "WHERE product_id = (SELECT id FROM products WHERE code = %s) "
                "AND scope = %s",
                ("draft", "life-individual-term", "guideline"),
            )
            for version_id, status, activated_at in prior:
                connection.execute(
                    "UPDATE knowledge_versions SET status = %s, "
                    "activated_at = %s "
                    "WHERE id = %s",
                    (status, activated_at, version_id),
                )
            connection.commit()
            restored = connection.execute(
                "SELECT id, status, activated_at FROM knowledge_versions "
                "WHERE product_id = (SELECT id FROM products WHERE code = %s) "
                "AND scope = %s",
                ("life-individual-term", "guideline"),
            ).fetchall()
        prior_by_id = {row[0]: row[1:] for row in prior}
        restored_by_id = {
            row[0]: row[1:] for row in restored if row[0] in prior_by_id
        }
        assert restored_by_id == prior_by_id


# Import one draft guideline without changing active developer data.
@pytest.fixture
def draft_guideline() -> Iterator[str]:
    with TestClient(create_app(Settings(generation_provider="fake"))) as client:
        admin = login(client, ADMINISTRATOR)
        yield import_guideline(
            client, admin, f"guidance-{uuid4().hex[:10]}"
        )


# Create one submit-ready fictional life case for the graph test.
def create_life_case(client: TestClient, applicant: dict[str, str]) -> str:
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
    case_id = str(created.json()["id"])
    uploaded = client.post(
        f"/api/v1/cases/{case_id}/documents",
        files={
            "document": ("synthetic.pdf", blank_pdf(), "application/pdf")
        },
        data={"document_code": "identity_record"},
        headers=applicant,
    )
    assert uploaded.status_code == 200, uploaded.text
    return case_id


# Store one synthetic explanation twice through the async persistence boundary.
async def store_twice(case_id: str) -> None:
    database = Database(DATABASE_URL)
    try:
        async with database.session_factory() as session:
            case = await session.scalar(select(Case).where(Case.id == case_id))
            actor = await session.scalar(select(User).limit(1))
            assert case is not None
            assert actor is not None
            values = {
                "route_explanation": {
                    "status": "generated",
                    "text": "Standard review cites synthetic guidance.",
                    "missing_items": [],
                    "citations": [
                        {
                            "version": "g1",
                            "passage_key": "synthetic-section",
                        }
                    ],
                    "provider": "fake",
                    "model": "fake-guidance-1",
                    "request_hash": "synthetic-hash",
                }
            }
            await store_route_explanation(session, case, values, actor.id)
            await store_route_explanation(session, case, values, actor.id)
            await session.commit()
    finally:
        await database.close()


# Verify route data is unchanged and stored explanation is stable after restart.
def test_route_explanation_is_insert_once_and_restart_stable() -> None:
    case_id = uuid4()
    seed_case(case_id)
    try:
        with psycopg.connect(SYNC_DATABASE_URL) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
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
        asyncio.run(store_twice(str(case_id)))
        settings = Settings(generation_provider="fake")
        with TestClient(create_app(settings)) as first:
            response = first.get(
                f"/api/v1/reviews/{case_id}/guidance",
                headers=login(first, UNDERWRITER),
            )
            assert response.status_code == 200, response.text
            first_body = response.json()
            assert first_body["route_explanation"]["text"] == (
                "Standard review cites synthetic guidance."
            )
        with TestClient(create_app(settings)) as second:
            response = second.get(
                f"/api/v1/reviews/{case_id}/guidance",
                headers=login(second, UNDERWRITER),
            )
            assert response.json() == first_body

        with psycopg.connect(SYNC_DATABASE_URL) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT route FROM recommendations WHERE case_id = %s",
                    (case_id,),
                )
                assert cursor.fetchone() == ("standard",)
                cursor.execute(
                    "SELECT count(*) FROM case_guidance WHERE case_id = %s",
                    (case_id,),
                )
                assert cursor.fetchone() == (1,)
                cursor.execute(
                    "SELECT count(*) FROM audit_events "
                    "WHERE case_id = %s AND event_type = %s",
                    (case_id, "route_explanation_stored"),
                )
                assert cursor.fetchone() == (1,)
    finally:
        remove_case(case_id)


# Verify real submission, checkpoint restart, and human resume preserve
# guidance.
def test_submission_graph_persists_guidance_before_restart(
    active_guideline: None,
) -> None:
    del active_guideline
    case_id: str | None = None
    settings = Settings(generation_provider="fake")
    with TestClient(create_app(settings)) as client:
        admin = login(client, ADMINISTRATOR)
        applicant = login(client, APPLICANT)
        product = client.post(
            "/api/v1/products/life-individual-term/activate",
            json={"version": "v3"},
            headers=admin,
        )
        assert product.status_code == 200, product.text
        case_id = create_life_case(client, applicant)
        submitted = client.post(
            f"/api/v1/cases/{case_id}/submit", headers=applicant
        )
        assert submitted.status_code == 200, submitted.text
        expected_route = submitted.json()["recommendation"]["route"]
        first = client.get(
            f"/api/v1/reviews/{case_id}/guidance",
            headers=login(client, UNDERWRITER),
        )
        assert first.status_code == 200, first.text
        first_body = first.json()
        assert first_body["route_explanation"]["status"] in {
            "generated",
            "template",
        }
        assert first_body["route_explanation"]["citations"]

    assert case_id is not None
    with TestClient(create_app(settings)) as restarted:
        underwriter = login(restarted, UNDERWRITER)
        after_restart = restarted.get(
            f"/api/v1/reviews/{case_id}/guidance",
            headers=underwriter,
        )
        assert after_restart.status_code == 200, after_restart.text
        assert after_restart.json() == first_body
        resumed = restarted.post(
            f"/api/v1/reviews/{case_id}",
            headers=underwriter,
            json={
                "action": "request_information",
                "reason": "Synthetic restart resume",
                "evidence_acknowledged": True,
            },
        )
        assert resumed.status_code == 200, resumed.text
        assert resumed.json()["status"] == "needs_information"
    with psycopg.connect(SYNC_DATABASE_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT route FROM recommendations WHERE case_id = %s",
                (case_id,),
            )
            assert cursor.fetchone() == (expected_route,)
    remove_case(case_id)


# Verify stored guidance leaves every synthetic reference route unchanged.
def test_guidance_keeps_all_reference_routes_unchanged(
    draft_guideline: str,
) -> None:
    prior = active_guideline_id()
    without_guidance = asyncio.run(evaluate_cases(guidance_enabled=False))
    with_guidance = asyncio.run(
        evaluate_cases(
            guidance_enabled=True,
            guideline_ids={"life-individual-term": draft_guideline},
        )
    )

    assert len(without_guidance) == 90
    # Guard against a vacuous pass when no guideline is active.
    assert any(
        record["explanation_status"] in {"generated", "template"}
        for record in with_guidance
    )
    assert [
        record["prediction"]["route"] for record in with_guidance
    ] == [
        record["prediction"]["route"] for record in without_guidance
    ]
    assert active_guideline_id() == prior


# Verify a failed retrieval query leaves the shared session writable.
def test_retrieval_database_error_keeps_session_usable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Fail inside the database, aborting any unprotected transaction.
    async def broken_retrieve(session: object, *args: object) -> list:
        del args
        await session.execute(text("SELECT 1/0"))  # type: ignore[attr-defined]
        return []

    monkeypatch.setattr(
        "underwriteflow.knowledge.explainer.retrieve", broken_retrieve
    )

    # Explain one route, then run a follow-up statement on the session.
    async def run() -> tuple[object, object]:
        database = Database(DATABASE_URL)
        try:
            async with database.session_factory() as session:
                explainer = RouteExplainer(
                    session, FakeGuidanceProvider(), FakeEmbeddingProvider()
                )
                result = await explainer.explain(
                    {
                        "recommendation": {"route": "standard", "factors": []},
                        "guidance_context": {
                            "guideline_version_id": str(uuid4())
                        },
                    }
                )
                return result, await session.scalar(text("SELECT 1"))
        finally:
            await database.close()

    result, follow_up = asyncio.run(run())

    assert result["status"] == "unavailable"  # type: ignore[index]
    assert follow_up == 1
