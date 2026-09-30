"""Insert-once persistence for route explanations and specialist briefs."""

import logging
from typing import Any
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert

from underwriteflow.audit.events import build_audit_event
from underwriteflow.knowledge.brief import build_brief
from underwriteflow.knowledge.retrieval import retrieve
from underwriteflow.persistence.knowledge_models import CaseGuidance
from underwriteflow.persistence.models import Case
from underwriteflow.providers.embedding import EmbeddingProvider
from underwriteflow.providers.service import ProviderError

LOGGER = logging.getLogger(__name__)


# Store one explanation per case cycle and emit one sanitized audit event.
async def store_route_explanation(
    session: AsyncSession,
    case: Case,
    triage_values: dict[str, Any],
    actor_user_id: UUID,
) -> None:
    explanation = triage_values.get("route_explanation")
    if not isinstance(explanation, dict):
        return
    citations = list(explanation.get("citations", []))
    statement = (
        insert(CaseGuidance)
        .values(
            case_id=case.id,
            review_cycle=case.review_cycle,
            kind="route_explanation",
            status=explanation.get("status", "unavailable"),
            body={
                "text": explanation.get("text", ""),
                "missing_items": list(
                    explanation.get("missing_items", [])
                ),
            },
            citations=citations,
            provider=explanation.get("provider"),
            model=explanation.get("model"),
            request_hash=explanation.get("request_hash"),
        )
        .on_conflict_do_nothing(
            index_elements=[
                CaseGuidance.case_id,
                CaseGuidance.review_cycle,
                CaseGuidance.kind,
            ]
        )
    )
    result = await session.execute(statement)
    if result.rowcount != 1:
        return
    session.add(
        build_audit_event(
            "route_explanation_stored",
            {
                "case_id": case.id,
                "review_cycle": case.review_cycle,
                "status": explanation.get("status"),
                "citation_keys": [
                    item.get("passage_key")
                    for item in citations
                    if isinstance(item, dict)
                ],
                "request_hash": explanation.get("request_hash"),
            },
            case_id=case.id,
            actor_user_id=actor_user_id,
        )
    )


# Store one deterministic brief per specialist case cycle.
async def store_specialist_brief(
    session: AsyncSession,
    case: Case,
    triage_values: dict[str, Any],
    actor_user_id: UUID,
    embedder: EmbeddingProvider | None = None,
) -> None:
    route = (triage_values.get("recommendation") or {}).get("route", "")
    if route != "specialist":
        return
    validations = list(triage_values.get("validations", []))
    context = triage_values.get("guidance_context") or {}
    passages = await _rule_passages(
        session,
        context.get("guideline_version_id"),
        [
            str(item["rule_code"])
            for item in validations
            if item.get("status") == "triggered"
        ],
        {
            "age": context.get("age"),
            "sum_assured": context.get("sum_assured"),
        },
        embedder,
    )
    brief = build_brief(
        route, list(triage_values.get("evidence", [])), validations, passages
    )
    citations = brief.pop("suggested_citations")
    result = await session.execute(
        insert(CaseGuidance)
        .values(
            case_id=case.id,
            review_cycle=case.review_cycle,
            kind="specialist_brief",
            status="template",
            body=brief,
            citations=citations,
        )
        .on_conflict_do_nothing(
            index_elements=[
                CaseGuidance.case_id,
                CaseGuidance.review_cycle,
                CaseGuidance.kind,
            ]
        )
    )
    if result.rowcount != 1:
        return
    session.add(
        build_audit_event(
            "specialist_brief_stored",
            {
                "case_id": case.id,
                "review_cycle": case.review_cycle,
                "rules": brief["rules"],
                "citation_keys": [
                    item["passage_key"] for item in citations
                ],
            },
            case_id=case.id,
            actor_user_id=actor_user_id,
        )
    )


# Retrieve the top pinned passages for the triggered rule codes.
async def _rule_passages(
    session: AsyncSession,
    version_id: object,
    rule_codes: list[str],
    facts: dict[str, Any],
    embedder: EmbeddingProvider | None,
) -> list[dict[str, Any]]:
    if not version_id or not rule_codes or embedder is None:
        return []
    try:
        # A savepoint keeps a failed query from aborting the case write.
        async with session.begin_nested():
            retrieved = await retrieve(
                session,
                embedder,
                UUID(str(version_id)),
                " ".join(rule_codes),
                facts,
            )
    except (ProviderError, SQLAlchemyError) as error:
        LOGGER.warning(
            "specialist brief retrieval failed: error=%s",
            type(error).__name__,
        )
        return []
    return [
        {
            "title": item["title"],
            "body": item["body"],
            "citation": {
                "version": item["version"],
                "passage_key": item["passage_key"],
            },
        }
        for item in retrieved
    ]
