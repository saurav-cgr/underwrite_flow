"""Specialist submissions persist and expose deterministic briefs."""

import asyncio
from collections.abc import Iterator
from pathlib import Path
from uuid import UUID, uuid4

import psycopg
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from fixtures.records import remove_case, seed_case
from fixtures.support import ADMINISTRATOR, APPLICANT, UNDERWRITER, login
from fixtures.synthetic_pdf import text_pdf
from underwriteflow.app import create_app
from underwriteflow.config import Settings
from underwriteflow.database import Database
from underwriteflow.knowledge.case_guidance import store_specialist_brief
from underwriteflow.knowledge.retrieval import retrieve
from underwriteflow.knowledge.service import KnowledgeService
from underwriteflow.persistence.knowledge_models import CaseGuidance
from underwriteflow.persistence.models import Case, User
from underwriteflow.providers.embedding import FakeEmbeddingProvider

DATABASE_URL = (
    "postgresql://underwriteflow:synthetic-local-password"
    "@db:5433/underwriteflow"
)
ASYNC_DATABASE_URL = (
    "postgresql+asyncpg://underwriteflow:synthetic-local-password"
    "@db:5433/underwriteflow"
)


# Read the fictional life corpus under one unique version identity.
def life_corpus(version: str) -> str:
    source = Path("/app/knowledge-config/life-individual-term/g1.yaml")
    return source.read_text().replace("version: g1", f"version: {version}")


# Restore one version table to the exact statuses found before this test.
def restore_versions(
    connection: psycopg.Connection,
    table: str,
    rows: list[tuple],
    product_code: str,
    scope: str | None = None,
) -> None:
    scope_clause = " AND scope = %s" if scope else ""
    parameters = (product_code, scope) if scope else (product_code,)
    connection.execute(
        f"UPDATE {table} SET status = 'draft' WHERE product_id = "
        f"(SELECT id FROM products WHERE code = %s){scope_clause}",
        parameters,
    )
    for version_id, status, activated_at in rows:
        connection.execute(
            f"UPDATE {table} SET status = %s, activated_at = %s "
            "WHERE id = %s",
            (status, activated_at, version_id),
        )


# Activate life v3 and one guideline, then restore shared developer state.
@pytest.fixture
def active_life_versions() -> Iterator[None]:
    with psycopg.connect(DATABASE_URL) as connection:
        product_status = connection.execute(
            "SELECT status FROM products WHERE code = %s",
            ("life-individual-term",),
        ).fetchone()[0]
        product_versions = connection.execute(
            "SELECT id, status, activated_at FROM product_versions "
            "WHERE product_id = "
            "(SELECT id FROM products WHERE code = %s)",
            ("life-individual-term",),
        ).fetchall()
        guidelines = connection.execute(
            "SELECT id, status, activated_at FROM knowledge_versions "
            "WHERE product_id = "
            "(SELECT id FROM products WHERE code = %s) AND scope = %s",
            ("life-individual-term", "guideline"),
        ).fetchall()
    with TestClient(create_app(Settings(generation_provider="fake"))) as client:
        admin = login(client, ADMINISTRATOR)
        product = client.post(
            "/api/v1/products/life-individual-term/activate",
            json={"version": "v3"},
            headers=admin,
        )
        assert product.status_code == 200, product.text
        imported = client.post(
            "/api/v1/knowledge/import",
            json={
                "scope": "guideline",
                "yaml": life_corpus(f"brief-{uuid4().hex[:10]}"),
            },
            headers=admin,
        )
        assert imported.status_code == 201, imported.text
        activated = client.post(
            f"/api/v1/knowledge/versions/{imported.json()['id']}/activate",
            headers=admin,
        )
        assert activated.status_code == 200, activated.text
        yield
    with psycopg.connect(DATABASE_URL) as connection:
        restore_versions(
            connection,
            "product_versions",
            product_versions,
            "life-individual-term",
        )
        restore_versions(
            connection,
            "knowledge_versions",
            guidelines,
            "life-individual-term",
            "guideline",
        )
        connection.execute(
            "UPDATE products SET status = %s WHERE code = %s",
            (product_status, "life-individual-term"),
        )


# Submit one hazardous case through extraction and return its identifier.
def submit_hazardous_case(client: TestClient) -> UUID:
    applicant = login(client, APPLICANT)
    created = client.post(
        "/api/v1/cases",
        json={
            "product_code": "life-individual-term",
            "idempotency_key": str(uuid4()),
            "payload": {
                "requested_cover": 1_000_000,
                "date_of_birth": "1990-01-01",
                "occupation_type": "hazardous",
                "health_declaration": True,
                "cover_start_date": "2026-10-01",
            },
            "document_codes": [
                "identity_record",
                "income_record",
                "previous_policy",
            ],
        },
        headers=applicant,
    )
    assert created.status_code == 200, created.text
    case_id = UUID(created.json()["id"])
    document = text_pdf(
        [
            "holder_name: Synthetic Specialist",
            "requested_cover: 1000000",
            "date_of_birth: 1990-01-01",
            "occupation_type: hazardous",
            "health_declaration: true",
            "cover_start_date: 2026-10-01",
            "policy_expiry_date: 2026-09-15",
        ]
    )
    for code in ("identity_record", "income_record", "previous_policy"):
        uploaded = client.post(
            f"/api/v1/cases/{case_id}/documents",
            files={"document": (f"{code}.pdf", document, "application/pdf")},
            data={"document_code": code},
            headers=applicant,
        )
        assert uploaded.status_code == 200, uploaded.text
    submitted = client.post(
        f"/api/v1/cases/{case_id}/submit", headers=applicant
    )
    assert submitted.status_code == 200, submitted.text
    route = submitted.json()["recommendation"]["route"]
    assert route == "specialist", submitted.text
    return case_id


# Given hazardous occupation, persist and serve its sourced specialist brief.
def test_hazardous_case_stores_and_returns_specialist_brief(
    active_life_versions: None,
) -> None:
    del active_life_versions
    settings = Settings(generation_provider="fake")
    with TestClient(create_app(settings)) as client:
        case_id = submit_hazardous_case(client)
        try:
            response = client.get(
                f"/api/v1/reviews/{case_id}/guidance",
                headers=login(client, UNDERWRITER),
            )
            assert response.status_code == 200, response.text
            brief = response.json()["specialist_brief"]
            assert brief["rules"] == ["hazardous_occupation_specialist"]
            assert all(
                item["document"].endswith(".pdf")
                and item["source_locator"] == "page:1"
                for item in brief["evidence"]
            )
            assert brief["passages"][0]["citation"]["passage_key"] == (
                "life-occupation-hazardous"
            )
            assert len(response.json()["suggested_citations"]) <= 3
            with psycopg.connect(DATABASE_URL) as connection:
                stored = connection.execute(
                    "SELECT count(*) FROM case_guidance "
                    "WHERE case_id = %s AND kind = %s",
                    (case_id, "specialist_brief"),
                ).fetchone()
            assert stored == (1,)
        finally:
            remove_case(case_id)


# Store one brief and read the retrieval keys and citations it reproduces.
async def brief_passage_keys(
    case_id: UUID,
) -> tuple[list[str], list[str], list[str], list[dict[str, str]]]:
    facts = {"age": 36, "sum_assured": 1_000_000}
    corpus = life_corpus(f"brief-retrieval-{uuid4().hex[:10]}")
    database = Database(ASYNC_DATABASE_URL)
    try:
        async with database.session_factory() as session:
            actor = await session.scalar(select(User).limit(1))
            assert actor is not None
            imported = await KnowledgeService(
                embedding_provider=FakeEmbeddingProvider()
            ).import_guideline(session, corpus, actor.id)
            case = await session.get(Case, case_id)
            assert case is not None
            await store_specialist_brief(
                session,
                case,
                {
                    "recommendation": {"route": "specialist"},
                    "validations": [
                        {
                            "rule_code": "hazardous_occupation_specialist",
                            "status": "triggered",
                        }
                    ],
                    "guidance_context": {
                        "guideline_version_id": str(imported.id),
                        "age": facts["age"],
                        "sum_assured": facts["sum_assured"],
                    },
                    "evidence": [],
                },
                actor.id,
                FakeEmbeddingProvider(),
            )
            await session.commit()
            row = await session.scalar(
                select(CaseGuidance).where(
                    CaseGuidance.case_id == case.id,
                    CaseGuidance.kind == "specialist_brief",
                )
            )
            assert row is not None
            expected = await retrieve(
                session,
                FakeEmbeddingProvider(),
                imported.id,
                "hazardous_occupation_specialist",
                facts,
            )
            return (
                [
                    item["citation"]["passage_key"]
                    for item in row.body["passages"]
                ],
                [item["passage_key"] for item in row.citations],
                [item["passage_key"] for item in expected],
                [item["citation"] for item in row.body["passages"]],
            )
    finally:
        await database.close()


# Given triggered rules, cite the banded hybrid retrieval ranking.
def test_brief_passages_follow_banded_hybrid_retrieval() -> None:
    case_id = uuid4()
    seed_case(case_id)
    try:
        passages, suggestions, expected, citations = asyncio.run(
            brief_passage_keys(case_id)
        )
    finally:
        remove_case(case_id)

    assert expected
    assert passages == expected
    assert passages[0] == "life-occupation-hazardous"
    assert len(passages) > 1
    assert suggestions == expected[:3]
    assert citations
    # Stored citations stay minimal: no internal version identifier.
    assert all(
        set(item) == {"version", "passage_key"} for item in citations
    )
