"""Embedding persistence coverage for imported synthetic corpora."""

from pathlib import Path
from uuid import uuid4

from sqlalchemy import select

from underwriteflow.database import Database
from underwriteflow.knowledge.service import KnowledgeService
from underwriteflow.persistence.knowledge_models import KnowledgePassage
from underwriteflow.persistence.models import User

DATABASE_URL = (
    "postgresql+asyncpg://underwriteflow:synthetic-local-password"
    "@db:5433/underwriteflow"
)


class TrackingEmbedder:
    """Record batch sizes while returning valid deterministic vectors."""

    name = "fake"
    model = "test"

    # Record one bounded provider call and return unit-width test vectors.
    async def embed(self, texts: list[str]) -> list[list[float]]:
        self.calls.append(len(texts))
        return [[1.0] + [0.0] * 767 for _ in texts]

    # Store calls separately so the test can inspect provider batching.
    def __init__(self) -> None:
        self.calls: list[int] = []


# Verify every imported passage receives an embedding in bounded batches.
def test_import_writes_embeddings_in_batches() -> None:
    import asyncio

    # Run persistence checks inside one async database session.
    async def run() -> None:
        database = Database(DATABASE_URL)
        try:
            provider = TrackingEmbedder()
            async with database.session_factory() as session:
                actor = await session.scalar(select(User).limit(1))
                text = Path(
                    "/app/knowledge-config/life-individual-term/g1.yaml"
                ).read_text()
                text = text.replace(
                    "version: g1", f"version: embed-{uuid4().hex[:12]}"
                )
                version = await KnowledgeService(
                    embedding_provider=provider
                ).import_guideline(session, text, actor.id)
                passages = list(
                    await session.scalars(
                        select(KnowledgePassage).where(
                            KnowledgePassage.version_id == version.id
                        )
                    )
                )
                assert provider.calls
                assert max(provider.calls) <= 100
                assert len(passages) == 12
                assert all(passage.embedding for passage in passages)
        finally:
            await database.close()

    asyncio.run(run())
