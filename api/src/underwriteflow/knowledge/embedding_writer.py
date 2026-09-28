"""Write bounded batches of embeddings for imported knowledge passages."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from underwriteflow.config import get_settings
from underwriteflow.persistence.knowledge_models import KnowledgePassage
from underwriteflow.providers.embedding import (
    EmbeddingProvider,
    build_embedding_provider,
)
from underwriteflow.providers.service import ProviderError

BATCH_SIZE = 100


# Render searchable passage facts into one provider input string.
def passage_text(passage: KnowledgePassage) -> str:
    return " ".join(
        (
            passage.passage_key,
            passage.topic,
            passage.title,
            str(passage.thresholds),
            passage.body,
        )
    )


# Embed every passage in batches no larger than the provider contract allows.
async def write_embeddings(
    session: AsyncSession,
    version_id,
    provider: EmbeddingProvider | None = None,
) -> None:
    provider = provider or build_embedding_provider(get_settings())
    passages = list(
        await session.scalars(
            select(KnowledgePassage)
            .where(KnowledgePassage.version_id == version_id)
            .order_by(KnowledgePassage.passage_key)
        )
    )
    for start in range(0, len(passages), BATCH_SIZE):
        batch = passages[start : start + BATCH_SIZE]
        vectors = await provider.embed([passage_text(item) for item in batch])
        if len(vectors) != len(batch):
            raise ProviderError("embedding provider returned invalid data")
        for passage, vector in zip(batch, vectors):
            passage.embedding = vector
    await session.flush()
