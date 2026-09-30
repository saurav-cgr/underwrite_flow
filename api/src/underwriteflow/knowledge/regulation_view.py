"""Read-only related clauses beside one pinned guideline passage."""

import logging
from typing import Any
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from underwriteflow.knowledge.retrieval import retrieve_by_meaning
from underwriteflow.providers.embedding import EmbeddingProvider
from underwriteflow.providers.service import ProviderError

LOGGER = logging.getLogger(__name__)
RELATED_LIMIT = 3


# Retrieve at most three clauses related by meaning to one query passage.
async def related_clauses(
    session: AsyncSession,
    embedder: EmbeddingProvider | None,
    regulation_version_id: UUID | None,
    query: str,
    limit: int = RELATED_LIMIT,
) -> list[dict[str, Any]]:
    if embedder is None or regulation_version_id is None or not query:
        return []
    try:
        # A savepoint keeps a failed read from aborting the request session.
        async with session.begin_nested():
            return await retrieve_by_meaning(
                session, embedder, regulation_version_id, query, limit
            )
    except (ProviderError, SQLAlchemyError) as error:
        LOGGER.warning(
            "related regulation unavailable: error=%s",
            type(error).__name__,
        )
        return []
