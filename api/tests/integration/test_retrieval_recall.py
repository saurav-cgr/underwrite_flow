"""Thirty-question fake-provider retrieval recall gate."""

import asyncio
from pathlib import Path

import yaml
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


# Verify the labelled life set reaches at least ninety percent top-five recall.
def test_life_retrieval_recall() -> None:
    # Run the labelled recall set inside one async database session.
    async def run() -> None:
        data = yaml.safe_load(
            Path("/app/evaluation/retrieval/life-individual-term.yaml")
            .read_text()
        )
        database = Database(DATABASE_URL)
        try:
            async with database.session_factory() as session:
                version = await session.scalar(
                    select(KnowledgeVersion)
                    .where(
                        KnowledgeVersion.scope == "guideline",
                        KnowledgeVersion.version == "g1",
                    )
                )
                if version is None:
                    actor = await session.scalar(select(User).limit(1))
                    await KnowledgeService(
                        embedding_provider=FakeEmbeddingProvider()
                    ).import_guideline(
                        session,
                        Path(
                            "/app/knowledge-config/life-individual-term/g1.yaml"
                        ).read_text(),
                        actor.id if actor else None,
                    )
                    version = await session.scalar(
                        select(KnowledgeVersion).where(
                            KnowledgeVersion.scope == "guideline",
                            KnowledgeVersion.version == "g1",
                        )
                    )
                assert version is not None
                embedder = FakeEmbeddingProvider()
                hits = 0
                for item in data["questions"]:
                    results = await retrieve(
                        session,
                        embedder,
                        version.id,
                        item["question"],
                        item.get("case", {}),
                    )
                    keys = {result["passage_key"] for result in results}
                    hits += bool(keys & set(item["expected"]))
                assert len(data["questions"]) == 30
                assert hits / len(data["questions"]) >= 0.9
        finally:
            await database.close()

    asyncio.run(run())
