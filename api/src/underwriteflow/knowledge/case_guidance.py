"""Insert-once persistence for generated route explanations."""

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert

from underwriteflow.audit.events import build_audit_event
from underwriteflow.persistence.knowledge_models import CaseGuidance
from underwriteflow.persistence.models import Case


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
