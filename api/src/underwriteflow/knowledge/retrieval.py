"""Hybrid vector and full-text retrieval for pinned guideline passages."""

import re
from typing import Any
from uuid import UUID

from sqlalchemy import Text, bindparam, case, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from underwriteflow.persistence.knowledge_models import (
    KnowledgePassage,
    KnowledgeVersion,
)
from underwriteflow.persistence.vector import Vector
from underwriteflow.providers.embedding import EmbeddingProvider


# Fuse vector and lexical ranks with reciprocal rank fusion k=60.
def fuse_ranks(
    vector_keys: list[str], lexical_keys: list[str], k: int = 60
) -> list[dict[str, Any]]:
    scores: dict[str, float] = {}
    for ranking in (vector_keys, lexical_keys):
        for rank, key in enumerate(dict.fromkeys(ranking), 1):
            scores[key] = scores.get(key, 0.0) + 1 / (k + rank)
    return [
        {"passage_key": key, "score": score}
        for key, score in sorted(
            scores.items(), key=lambda item: (-item[1], item[0])
        )
    ]


# Build inclusive filters for facts that are present on the case.
def _band_filters(facts: dict[str, Any]) -> list[Any]:
    filters: list[Any] = []
    age = facts.get("age")
    if age is not None:
        filters.append(
            or_(
                KnowledgePassage.age_min.is_(None),
                KnowledgePassage.age_min <= age,
            )
        )
        filters.append(
            or_(
                KnowledgePassage.age_max.is_(None),
                KnowledgePassage.age_max >= age,
            )
        )
    sum_assured = facts.get("sum_assured")
    if sum_assured is not None:
        filters.append(
            or_(
                KnowledgePassage.sum_assured_min.is_(None),
                KnowledgePassage.sum_assured_min <= sum_assured,
            )
        )
        filters.append(
            or_(
                KnowledgePassage.sum_assured_max.is_(None),
                KnowledgePassage.sum_assured_max >= sum_assured,
            )
        )
    return filters


# Build a bound OR full-text query so natural questions do not over-filter.
def _lexical_query(query: str) -> str:
    terms = re.findall(r"[a-z0-9]+", query.casefold())
    return " | ".join(f"{term}:*" for term in terms) or "none"


# Retrieve cited passages from one pinned version only.
async def retrieve(
    session: AsyncSession,
    embedder: EmbeddingProvider,
    version_id: UUID,
    query: str,
    facts: dict[str, Any],
    limit: int = 5,
) -> list[dict[str, Any]]:
    if not 1 <= limit <= 50:
        raise ValueError("limit must be between 1 and 50")
    version = await session.get(KnowledgeVersion, version_id)
    if version is None:
        return []
    vector = (await embedder.embed([query]))[0]
    filters = [
        KnowledgePassage.version_id == version_id,
        *_band_filters(facts),
    ]
    distance = KnowledgePassage.embedding.op("<=>")(
        bindparam("query_embedding", vector, type_=Vector(768))
    )
    vector_rows = await session.execute(
        select(KnowledgePassage.passage_key)
        .where(*filters, KnowledgePassage.embedding.is_not(None))
        .order_by(distance, KnowledgePassage.passage_key)
        .limit(limit * 10)
    )
    vector_keys = [row[0] for row in vector_rows]
    query_terms = func.to_tsquery(
        "english",
        bindparam("lexical_query", _lexical_query(query)),
    )
    exact_text = bindparam("exact_text", f"%{query.casefold()}%")
    exact = case(
        (
            or_(
                func.lower(KnowledgePassage.passage_key).like(exact_text),
                func.lower(KnowledgePassage.title).like(exact_text),
                func.lower(KnowledgePassage.body).like(exact_text),
                func.lower(cast(KnowledgePassage.thresholds, Text)).like(
                    exact_text
                ),
            ),
            1,
        ),
        else_=0,
    )
    lexical_score = func.ts_rank_cd(
        KnowledgePassage.search_vector, query_terms
    )
    lexical_rows = await session.execute(
        select(KnowledgePassage.passage_key)
        .where(
            *filters,
            or_(
                KnowledgePassage.search_vector.op("@@")(query_terms),
                exact == 1,
            ),
        )
        .order_by(
            exact.desc(), lexical_score.desc(), KnowledgePassage.passage_key
        )
        .limit(limit * 10)
    )
    lexical_keys = [row[0] for row in lexical_rows]
    fused = fuse_ranks(vector_keys, lexical_keys)[:limit]
    by_key = {
        passage.passage_key: passage
        for passage in await session.scalars(
            select(KnowledgePassage).where(
                KnowledgePassage.version_id == version_id,
                KnowledgePassage.passage_key.in_(
                    [item["passage_key"] for item in fused]
                ),
            )
        )
    }
    return [
        {
            "version": version.version,
            "version_id": str(version.id),
            "passage_key": item["passage_key"],
            "title": by_key[item["passage_key"]].title,
            "body": by_key[item["passage_key"]].body,
            "score": item["score"],
        }
        for item in fused
        if item["passage_key"] in by_key
    ]


# Retrieve the closest passages by embedding distance alone.
async def retrieve_by_meaning(
    session: AsyncSession,
    embedder: EmbeddingProvider,
    version_id: UUID,
    query: str,
    limit: int = 3,
) -> list[dict[str, Any]]:
    if not 1 <= limit <= 50:
        raise ValueError("limit must be between 1 and 50")
    version = await session.get(KnowledgeVersion, version_id)
    if version is None:
        return []
    vector = (await embedder.embed([query]))[0]
    distance = KnowledgePassage.embedding.op("<=>")(
        bindparam("query_embedding", vector, type_=Vector(768))
    )
    rows = await session.execute(
        select(KnowledgePassage)
        .where(
            KnowledgePassage.version_id == version_id,
            KnowledgePassage.embedding.is_not(None),
        )
        .order_by(distance, KnowledgePassage.passage_key)
        .limit(limit)
    )
    return [
        {
            "version": version.version,
            "version_id": str(version.id),
            "passage_key": passage.passage_key,
            "title": passage.title,
            "body": passage.body,
            "topic": passage.topic,
            "label": passage.label,
        }
        for passage in rows.scalars()
    ]
