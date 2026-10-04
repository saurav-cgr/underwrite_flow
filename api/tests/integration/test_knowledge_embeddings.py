"""Embedding persistence coverage for imported synthetic corpora."""

from pathlib import Path
from uuid import uuid4

from sqlalchemy import select

from fixtures.regulation import listed_entry, write_document, write_manifest
from underwriteflow.database import Database
from underwriteflow.knowledge.regulation_service import RegulationService
from underwriteflow.knowledge.service import KnowledgeService
from underwriteflow.persistence.knowledge_models import KnowledgePassage
from underwriteflow.persistence.models import User
from underwriteflow.providers.embedding import FakeEmbeddingProvider

DATABASE_URL = (
    "postgresql+asyncpg://underwriteflow:synthetic-local-password"
    "@db:5433/underwriteflow"
)


class TrackingEmbedder(FakeEmbeddingProvider):
    """Track deterministic fake embedding calls."""

    # Record bounded batches and return deterministic fake vectors.
    async def embed(self, texts: list[str]) -> list[list[float]]:
        self.calls.append(len(texts))
        if self.model == "fake-b":
            return [[0.0] * 767 + [1.0] for _ in texts]
        return await super().embed(texts)

    # Store calls separately so the test can inspect provider batching.
    def __init__(self) -> None:
        self.calls: list[int] = []


class AlternateTrackingEmbedder(TrackingEmbedder):
    """Track fake embeddings under a distinct model identity."""

    model = "fake-b"


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


# Verify guideline imports reuse matching models and replace stale vectors.
def test_guideline_import_reembeds_when_model_changes() -> None:
    import asyncio

    # Run provider-switch checks inside one async database session.
    async def run() -> None:
        database = Database(DATABASE_URL)
        try:
            first_provider = TrackingEmbedder()
            second_provider = AlternateTrackingEmbedder()
            async with database.session_factory() as session:
                actor = await session.scalar(select(User).limit(1))
                text = Path(
                    "/app/knowledge-config/life-individual-term/g1.yaml"
                ).read_text()
                text = text.replace(
                    "version: g1", f"version: switch-{uuid4().hex[:12]}"
                )
                first_service = KnowledgeService(
                    embedding_provider=first_provider
                )
                version = await first_service.import_guideline(
                    session, text, actor.id
                )
                assert first_provider.calls == [12]
                assert version.source["embedding_model"] == (
                    "fake:fake-embedding-768"
                )

                await first_service.import_guideline(session, text, actor.id)
                assert first_provider.calls == [12]
                original = list(
                    await session.scalars(
                        select(KnowledgePassage.embedding).where(
                            KnowledgePassage.version_id == version.id
                        )
                    )
                )

                version.source = {
                    key: value
                    for key, value in version.source.items()
                    if key != "embedding_model"
                }
                await session.commit()
                await first_service.import_guideline(session, text, actor.id)
                assert first_provider.calls == [12, 12]
                await session.refresh(version, attribute_names=["source"])
                assert version.source["embedding_model"] == (
                    "fake:fake-embedding-768"
                )

                await KnowledgeService(
                    embedding_provider=second_provider
                ).import_guideline(session, text, actor.id)
                assert second_provider.calls == [12]
                await session.refresh(version, attribute_names=["source"])
                assert version.source["embedding_model"] == "fake:fake-b"
                replaced = list(
                    await session.scalars(
                        select(KnowledgePassage.embedding).where(
                            KnowledgePassage.version_id == version.id
                        )
                    )
                )
                expected = [0.0] * 767 + [1.0]
                assert replaced == [expected] * 12
                assert all(old != new for old, new in zip(original, replaced))
        finally:
            await database.close()

    asyncio.run(run())


# Verify regulation imports replace vectors when provider model changes.
def test_regulation_import_reembeds_when_model_changes(tmp_path: Path) -> None:
    import asyncio

    # Run provider-switch checks inside one async database session.
    async def run() -> None:
        database = Database(DATABASE_URL)
        try:
            suffix = uuid4().hex[:12]
            write_document(
                tmp_path,
                "circular.pdf",
                [f"1. Synthetic clause {suffix}\nBody {suffix}."],
            )
            write_manifest(
                tmp_path,
                [listed_entry(tmp_path, "circular.pdf")],
            )
            first_provider = TrackingEmbedder()
            second_provider = AlternateTrackingEmbedder()
            async with database.session_factory() as session:
                first_service = RegulationService(
                    embedding_provider=first_provider
                )
                version, _ = await first_service.import_regulation(
                    session, tmp_path
                )
                passages = list(
                    await session.scalars(
                        select(KnowledgePassage).where(
                            KnowledgePassage.version_id == version.id
                        )
                    )
                )
                assert len(passages) == 1
                assert first_provider.calls == [1]
                original = passages[0].embedding

                await RegulationService(
                    embedding_provider=second_provider
                ).import_regulation(session, tmp_path)
                assert second_provider.calls == [1]
                await session.refresh(version, attribute_names=["source"])
                assert version.source["embedding_model"] == "fake:fake-b"
                passages = list(
                    await session.scalars(
                        select(KnowledgePassage).where(
                            KnowledgePassage.version_id == version.id
                        )
                    )
                )
                assert passages[0].embedding == [0.0] * 767 + [1.0]
                assert passages[0].embedding != original
        finally:
            await database.close()

    asyncio.run(run())
