"""Pinned-version and band-filter retrieval coverage."""

import asyncio
from pathlib import Path
from uuid import uuid4

from sqlalchemy import select

from underwriteflow.database import Database
from underwriteflow.knowledge.case_facts import case_facts
from underwriteflow.knowledge.retrieval import retrieve
from underwriteflow.knowledge.service import KnowledgeService
from underwriteflow.persistence.knowledge_models import KnowledgeVersion
from underwriteflow.persistence.models import User
from underwriteflow.providers.embedding import FakeEmbeddingProvider

DATABASE_URL = (
    "postgresql+asyncpg://underwriteflow:synthetic-local-password"
    "@db:5433/underwriteflow"
)


# Read one synthetic corpus under a unique immutable version identity.
def corpus(version: str) -> str:
    text = Path(
        "/app/knowledge-config/life-individual-term/g1.yaml"
    ).read_text()
    return text.replace("version: g1", f"version: {version}")


# Verify retrieval stays pinned and honors age and sum-assured bands.
def test_retrieval_filters_pinned_version_and_bands() -> None:
    # Run retrieval checks inside one async database session.
    async def run() -> None:
        database = Database(DATABASE_URL)
        try:
            async with database.session_factory() as session:
                actor = await session.scalar(select(User).limit(1))
                first = await KnowledgeService(
                    embedding_provider=FakeEmbeddingProvider()
                ).import_guideline(
                    session, corpus(f"retrieve-{uuid4().hex[:12]}"), actor.id
                )
                second = await KnowledgeService(
                    embedding_provider=FakeEmbeddingProvider()
                ).import_guideline(
                    session, corpus(f"retrieve-{uuid4().hex[:12]}"), actor.id
                )
                assert second.status == "draft"
                results = await retrieve(
                    session,
                    FakeEmbeddingProvider(),
                    first.id,
                    "high_cover_standard",
                    {"age": 42, "sum_assured": 15000000},
                )
                assert results
                assert all(item["version"] == first.version for item in results)
                assert results[0]["passage_key"] == (
                    "life-cover-high-sum-assured"
                )
                assert "life-age-eighteen-to-forty" not in {
                    item["passage_key"] for item in results
                }
                without_age = await retrieve(
                    session,
                    FakeEmbeddingProvider(),
                    first.id,
                    "life-age-eighteen-to-forty",
                    {"sum_assured": 15000000},
                )
                assert "life-age-eighteen-to-forty" in {
                    item["passage_key"] for item in without_age
                }
                assert all(
                    "version" in item and "passage_key" in item
                    for item in results
                )
        finally:
            await database.close()

    asyncio.run(run())
