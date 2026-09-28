"""Evaluate fake or configured hybrid retrieval against one labelled set."""

import asyncio
from pathlib import Path

import yaml
from sqlalchemy import select

from underwriteflow.config import get_settings
from underwriteflow.database import Database
from underwriteflow.knowledge.retrieval import retrieve
from underwriteflow.persistence.knowledge_models import KnowledgeVersion
from underwriteflow.providers.embedding import build_embedding_provider


# Load the mounted evaluation set from either container or repository path.
def evaluation_path() -> Path:
    mounted = Path("/app/evaluation/retrieval/life-individual-term.yaml")
    return mounted if mounted.exists() else Path(
        "evaluation/retrieval/life-individual-term.yaml"
    )


# Run labelled questions against the newest active life guideline version.
async def evaluate() -> float:
    data = yaml.safe_load(evaluation_path().read_text())
    settings = get_settings()
    database = Database(settings.database_url)
    try:
        async with database.session_factory() as session:
            version = await session.scalar(
                select(KnowledgeVersion)
                .where(
                    KnowledgeVersion.scope == "guideline",
                    KnowledgeVersion.status == "active",
                )
                .order_by(KnowledgeVersion.activated_at.desc())
            )
            if version is None:
                raise RuntimeError("no active guideline version")
            provider = build_embedding_provider(settings)
            hits = 0
            for item in data["questions"]:
                results = await retrieve(
                    session,
                    provider,
                    version.id,
                    item["question"],
                    item.get("case", {}),
                )
                keys = {result["passage_key"] for result in results}
                hits += bool(keys & set(item["expected"]))
            recall = hits / len(data["questions"])
            print(f"recall={recall:.3f} hits={hits}/{len(data['questions'])}")
            return recall
    finally:
        await database.close()


# Exit non-zero when the deterministic retrieval acceptance gate fails.
def main() -> None:
    recall = asyncio.run(evaluate())
    if get_settings().generation_provider == "fake" and recall < 0.9:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
