"""Thirty-question fake-provider retrieval recall gates."""

import asyncio
from pathlib import Path

import pytest
import yaml
from sqlalchemy import select

from underwriteflow.database import Database
from underwriteflow.knowledge.retrieval import retrieve
from underwriteflow.knowledge.service import KnowledgeService
from underwriteflow.persistence.knowledge_models import KnowledgeVersion
from underwriteflow.persistence.models import User
from underwriteflow.providers.embedding import FakeEmbeddingProvider

DATABASE_URL = (
    "postgresql+asyncpg://underwriteflow:synthetic-local-password"
    "@db:5433/underwriteflow"
)

PRODUCTS = (
    (
        "motor-private-car",
        "/app/evaluation/retrieval/motor-private-car.yaml",
        "/app/knowledge-config/motor-private-car/g1.yaml",
    ),
    (
        "life-individual-term",
        "/app/evaluation/retrieval/life-individual-term.yaml",
        "/app/knowledge-config/life-individual-term/g1.yaml",
    ),
    (
        "health-individual-family-floater",
        "/app/evaluation/retrieval/health-individual-family-floater.yaml",
        "/app/knowledge-config/health-individual-family-floater/g1.yaml",
    ),
)


# Resolve a mounted path in Docker or the repository path during local runs.
def mounted_path(path: str) -> Path:
    mounted = Path(path)
    if mounted.exists():
        return mounted
    return Path(__file__).parents[3] / path.removeprefix("/app/")


# Import one labelled corpus and validate its stored identity.
async def guideline_version(
    session, corpus_path: Path
) -> KnowledgeVersion:
    actor = await session.scalar(select(User).limit(1))
    corpus = yaml.safe_load(corpus_path.read_text())
    corpus["version"] = f"recall-{corpus['version']}"
    return await KnowledgeService(
        embedding_provider=FakeEmbeddingProvider()
    ).import_guideline(
        session,
        yaml.safe_dump(corpus),
        actor.id if actor else None,
    )


# Verify each labelled product set reaches at least ninety percent recall.
@pytest.mark.parametrize("product_code,evaluation_file,corpus_file", PRODUCTS)
def test_product_retrieval_recall(
    product_code: str, evaluation_file: str, corpus_file: str
) -> None:
    # Run the labelled recall set inside one async database session.
    async def run() -> None:
        data = yaml.safe_load(mounted_path(evaluation_file).read_text())
        database = Database(DATABASE_URL)
        try:
            async with database.session_factory() as session:
                version = await guideline_version(
                    session, mounted_path(corpus_file)
                )
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
