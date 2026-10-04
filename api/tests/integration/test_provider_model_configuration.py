"""Integration coverage for configured model tags and re-embedding."""

import asyncio
import json
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import select

from fixtures.regulation import listed_entry, write_document, write_manifest
from underwriteflow.config import Settings
from underwriteflow.database import Database
from underwriteflow.knowledge.regulation_service import RegulationService
from underwriteflow.knowledge.service import KnowledgeService
from underwriteflow.persistence.knowledge_models import KnowledgePassage
from underwriteflow.persistence.models import User
from underwriteflow.providers import embedding
from underwriteflow.providers.embedding import OllamaEmbeddingProvider

DATABASE_URL = (
    "postgresql+asyncpg://underwriteflow:synthetic-local-password"
    "@db:5433/underwriteflow"
)


# Build an Ollama provider with deterministic intercepted embeddings.
def configured_provider(
    monkeypatch: pytest.MonkeyPatch,
    model: str,
    requests: list[str],
) -> embedding.EmbeddingProvider:
    # Return distinct vectors for each resolved model without remote calls.
    def build(base_url: str, selected_model: str, **kwargs: object) -> object:
        # Capture the selected model and return its deterministic vectors.
        def handler(request: httpx.Request) -> httpx.Response:
            requests.append(selected_model)
            value = 1.0 if selected_model == "model-b" else 0.0
            count = len(json.loads(request.content)["input"])
            return httpx.Response(
                200,
                json={"embeddings": [[value] * 768 for _ in range(count)]},
            )

        return OllamaEmbeddingProvider(
            base_url,
            selected_model,
            transport=httpx.MockTransport(handler),
            **kwargs,
        )

    monkeypatch.setattr(embedding, "OllamaEmbeddingProvider", build)
    return embedding.build_embedding_provider(
        Settings(
            _env_file=None,
            generation_provider="fake",
            embedding_provider="ollama",
            embedding_model=model,
        )
    )


# Verify configured model changes replace guideline and regulation vectors.
def test_configured_model_change_reembeds_all_imports(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Run the persistence scenario in one isolated async database session.
    async def run() -> None:
        database = Database(DATABASE_URL)
        try:
            requests: list[str] = []
            suffix = uuid4().hex[:12]
            text = Path(
                "/app/knowledge-config/life-individual-term/g1.yaml"
            ).read_text().replace("version: g1", f"version: models-{suffix}")
            write_document(
                tmp_path,
                "circular.pdf",
                [f"1. Synthetic clause {suffix}\nBody {suffix}."],
            )
            write_manifest(
                tmp_path,
                [listed_entry(tmp_path, "circular.pdf")],
            )
            async with database.session_factory() as session:
                actor = await session.scalar(select(User).limit(1))
                first = configured_provider(monkeypatch, "model-a", requests)
                guideline = await KnowledgeService(
                    embedding_provider=first
                ).import_guideline(session, text, actor.id)
                regulation, _ = await RegulationService(
                    embedding_provider=first
                ).import_regulation(session, tmp_path)
                first_count = len(requests)
                assert first_count == 2

                await KnowledgeService(
                    embedding_provider=first
                ).import_guideline(session, text, actor.id)
                await RegulationService(
                    embedding_provider=first
                ).import_regulation(session, tmp_path)
                assert len(requests) == first_count

                second = configured_provider(monkeypatch, "model-b", requests)
                await KnowledgeService(
                    embedding_provider=second
                ).import_guideline(session, text, actor.id)
                await RegulationService(
                    embedding_provider=second
                ).import_regulation(session, tmp_path)
                assert len(requests) == first_count * 2

                for version in (guideline, regulation):
                    await session.refresh(version, attribute_names=["source"])
                    assert version.source["embedding_model"] == "ollama:model-b"
                    vectors = list(
                        await session.scalars(
                            select(KnowledgePassage.embedding).where(
                                KnowledgePassage.version_id == version.id
                            )
                        )
                    )
                    assert all(vector == [1.0] * 768 for vector in vectors)
        finally:
            await database.close()

    asyncio.run(run())
