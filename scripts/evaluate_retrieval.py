"""Evaluate fake or configured hybrid retrieval against one labelled set."""

import asyncio
import sys
from pathlib import Path

import yaml
from sqlalchemy import select

from underwriteflow.config import get_settings
from underwriteflow.database import Database
from underwriteflow.knowledge.retrieval import retrieve
from underwriteflow.persistence.knowledge_models import KnowledgeVersion
from underwriteflow.persistence.models import Product
from underwriteflow.providers.embedding import build_embedding_provider

PRODUCTS = {
    "motor-private-car": "motor-private-car.yaml",
    "life-individual-term": "life-individual-term.yaml",
    "health-individual-family-floater": (
        "health-individual-family-floater.yaml"
    ),
}


# Load one mounted evaluation set from either container or repository path.
def evaluation_path(product_code: str) -> Path:
    filename = PRODUCTS[product_code]
    mounted = Path("/app/evaluation/retrieval") / filename
    return mounted if mounted.exists() else Path(
        "evaluation/retrieval"
    ) / filename


# Run labelled questions against one product's active guideline version.
async def evaluate(product_code: str) -> float:
    data = yaml.safe_load(evaluation_path(product_code).read_text())
    settings = get_settings()
    database = Database(settings.database_url)
    try:
        async with database.session_factory() as session:
            version = await session.scalar(
                select(KnowledgeVersion)
                .join(Product, Product.id == KnowledgeVersion.product_id)
                .where(
                    KnowledgeVersion.scope == "guideline",
                    KnowledgeVersion.status == "active",
                    Product.code == product_code,
                )
                .order_by(KnowledgeVersion.activated_at.desc())
            )
            if version is None:
                raise RuntimeError(
                    f"no active guideline version for {product_code}"
                )
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
            print(
                f"product={product_code} recall={recall:.3f} "
                f"hits={hits}/{len(data['questions'])}"
            )
            return recall
    finally:
        await database.close()


# Exit non-zero when a deterministic retrieval acceptance gate fails.
def main() -> None:
    product_code = sys.argv[1] if len(sys.argv) > 1 else "life-individual-term"
    if product_code not in PRODUCTS:
        raise SystemExit(
            "usage: evaluate_retrieval.py "
            "[motor-private-car|life-individual-term|"
            "health-individual-family-floater]"
        )
    recall = asyncio.run(evaluate(product_code))
    if get_settings().generation_provider == "fake" and recall < 0.9:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
