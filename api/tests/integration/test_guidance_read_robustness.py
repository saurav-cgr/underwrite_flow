"""Stored guidance rows that no longer validate must degrade safely."""

import asyncio
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from fixtures.case_fixtures import remove_case, seed_case
from fixtures.support import UNDERWRITER, login
from underwriteflow.app import create_app
from underwriteflow.config import Settings
from underwriteflow.database import Database
from underwriteflow.persistence.knowledge_models import CaseGuidance

ASYNC_DATABASE_URL = (
    "postgresql+asyncpg://underwriteflow:synthetic-local-password"
    "@db:5433/underwriteflow"
)


# Insert one selected stored guidance row so the read path must degrade.
async def store_guidance_row(
    case_id: UUID,
    kind: str,
    body: object,
    citations: object,
) -> None:
    database = Database(ASYNC_DATABASE_URL)
    try:
        async with database.session_factory() as session:
            session.add(
                CaseGuidance(
                    case_id=case_id,
                    review_cycle=0,
                    kind=kind,
                    status="template",
                    body=body,
                    citations=citations,
                )
            )
            await session.commit()
    finally:
        await database.close()


# Read the stored guidance for one case as an authorized underwriter.
def read_guidance(case_id: UUID) -> tuple[int, dict]:
    settings = Settings(generation_provider="fake")
    with TestClient(create_app(settings)) as client:
        response = client.get(
            f"/api/v1/reviews/{case_id}/guidance",
            headers=login(client, UNDERWRITER),
        )
        return response.status_code, response.json()


# Given a corrupt stored brief, serve no brief instead of a server error.
def test_corrupt_stored_brief_is_ignored() -> None:
    case_id = uuid4()
    seed_case(case_id)
    try:
        asyncio.run(
            store_guidance_row(
                case_id,
                "specialist_brief",
                {"rules": "not-a-list"},
                [],
            )
        )
        status_code, payload = read_guidance(case_id)
        assert status_code == 200
        assert payload["specialist_brief"] is None
        assert payload["suggested_citations"] == []
    finally:
        remove_case(case_id)


# Given a stored brief with non-object citations, keep the usable ones.
def test_corrupt_stored_brief_citations_are_ignored() -> None:
    case_id = uuid4()
    seed_case(case_id)
    try:
        asyncio.run(
            store_guidance_row(
                case_id,
                "specialist_brief",
                {"rules": []},
                ["bad", {"version": "g1", "passage_key": "life-age"}],
            )
        )
        status_code, payload = read_guidance(case_id)
        assert status_code == 200
        assert payload["specialist_brief"] is not None
        assert payload["suggested_citations"] == [
            {"version": "g1", "passage_key": "life-age"}
        ]
    finally:
        remove_case(case_id)


# Given a stored explanation whose body is not an object, degrade safely.
def test_corrupt_stored_explanation_body_is_ignored() -> None:
    case_id = uuid4()
    seed_case(case_id)
    try:
        asyncio.run(
            store_guidance_row(case_id, "route_explanation", ["bad"], [])
        )
        status_code, payload = read_guidance(case_id)
        assert status_code == 200
        explanation = payload["route_explanation"]
        assert explanation["status"] == "template"
        assert explanation["text"] == ""
        assert explanation["missing_items"] == []
        assert explanation["citations"] == []
    finally:
        remove_case(case_id)
