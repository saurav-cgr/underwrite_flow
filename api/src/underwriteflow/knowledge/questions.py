"""Underwriter case questions answered only from pinned guidance."""

import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from underwriteflow.audit.events import build_audit_event
from underwriteflow.knowledge.case_facts import case_facts
from underwriteflow.knowledge.retrieval import retrieve
from underwriteflow.persistence.knowledge_models import (
    CaseKnowledgePin,
    CaseQuestion,
)
from underwriteflow.persistence.models import (
    Case,
    ExtractedField,
    Recommendation,
    Submission,
    User,
)
from underwriteflow.providers.embedding import EmbeddingProvider
from underwriteflow.providers.guidance import (
    GuidanceOutput,
    GuidanceProvider,
    GuidanceRequest,
)
from underwriteflow.providers.service import ProviderError

LOGGER = logging.getLogger(__name__)
FALLBACK_ANSWER = "not covered by guidelines"
# A passage ranked by only one retriever scores at most 1/61 under RRF k=60.
# ponytail: requiring vector and lexical agreement is a coarse relevance
# gate; replace with a calibrated score once live recall is measured.
MIN_FUSED_SCORE = 1 / 61


# Answer, store, and audit one question without touching the route.
async def ask_question(
    session: AsyncSession,
    provider: GuidanceProvider | None,
    embedder: EmbeddingProvider | None,
    case: Case,
    actor_user_id: UUID,
    question: str,
) -> dict[str, object]:
    answer, citations, output = FALLBACK_ANSWER, [], None
    passages = await _passages(session, embedder, case, question)
    if passages and provider is not None:
        try:
            output = await provider.answer(
                await _request(session, case, question, passages)
            )
        except ProviderError as error:
            LOGGER.warning(
                "case answer provider failed: case_id=%s error=%s",
                case.id,
                type(error).__name__,
            )
    if output is not None:
        citations = _valid_citations(session, case.id, output, passages)
        # Cited fallback text is still the fallback outcome.
        if output.text.strip() == FALLBACK_ANSWER:
            citations = []
        if citations:
            answer = output.text
    row = CaseQuestion(
        case_id=case.id,
        asked_by_user_id=actor_user_id,
        question=question,
        answer=answer,
        covered=bool(citations),
        citations=citations,
        provider=output.provider if citations else None,
        model=output.model if citations else None,
    )
    session.add(row)
    await session.flush()
    session.add(
        build_audit_event(
            "case_question_answered",
            {
                "case_id": case.id,
                "question_id": row.id,
                "covered": row.covered,
                "citation_keys": [item["passage_key"] for item in citations],
            },
            case_id=case.id,
            actor_user_id=actor_user_id,
        )
    )
    await session.refresh(row)
    name = await session.scalar(
        select(User.display_name).where(User.id == actor_user_id)
    )
    return _response(row, name)


# Return every stored question for one case, oldest first.
async def list_questions(
    session: AsyncSession, case_id: UUID
) -> list[dict[str, object]]:
    rows = await session.execute(
        select(CaseQuestion, User.display_name)
        .join(User, User.id == CaseQuestion.asked_by_user_id)
        .where(CaseQuestion.case_id == case_id)
        .order_by(CaseQuestion.created_at, CaseQuestion.id)
    )
    return [_response(row, name) for row, name in rows]


# Retrieve relevant passages from the case's pinned guideline only.
async def _passages(
    session: AsyncSession,
    embedder: EmbeddingProvider | None,
    case: Case,
    question: str,
) -> list[dict[str, object]]:
    pin = await session.get(CaseKnowledgePin, case.id)
    if embedder is None or pin is None or pin.guideline_version_id is None:
        return []
    facts = await _facts(session, case.id)
    try:
        # A savepoint keeps a failed query from aborting the question write.
        async with session.begin_nested():
            passages = await retrieve(
                session, embedder, pin.guideline_version_id, question, facts
            )
    except (ProviderError, SQLAlchemyError) as error:
        LOGGER.warning(
            "case answer retrieval failed: case_id=%s error=%s",
            case.id,
            type(error).__name__,
        )
        return []
    return [item for item in passages if item["score"] > MIN_FUSED_SCORE]


# Read age and sum-assured band facts from the latest submission.
async def _facts(
    session: AsyncSession, case_id: UUID
) -> dict[str, object]:
    submission = await session.scalar(
        select(Submission)
        .where(Submission.case_id == case_id)
        .order_by(Submission.submitted_at.desc())
        .limit(1)
    )
    if submission is None:
        return {"age": None, "sum_assured": None}
    payload = submission.payload.get("application", submission.payload)
    try:
        return case_facts(payload, submission.submitted_at)
    except (TypeError, ValueError):
        return {"age": None, "sum_assured": None}


# Build the provider request; question and evidence stay untrusted data.
async def _request(
    session: AsyncSession,
    case: Case,
    question: str,
    passages: list[dict[str, object]],
) -> GuidanceRequest:
    route = await session.scalar(
        select(Recommendation.route).where(Recommendation.case_id == case.id)
    )
    evidence = await session.execute(
        select(
            ExtractedField.field_name,
            ExtractedField.value,
            ExtractedField.source_locator,
        )
        .where(ExtractedField.case_id == case.id)
        .order_by(ExtractedField.field_name, ExtractedField.id)
    )
    return GuidanceRequest(
        route=route or "",
        context={"case_id": str(case.id)},
        passages=passages,
        untrusted={
            "question": question,
            "evidence": [
                {"field": name, "value": value, "source": source}
                for name, value, source in evidence
            ],
        },
    )


# Keep provider citations found in the pinned retrieval set; log the rest.
def _valid_citations(
    session: AsyncSession,
    case_id: UUID,
    output: GuidanceOutput,
    passages: list[dict[str, object]],
) -> list[dict[str, str]]:
    allowed = {
        (str(item["version"]), str(item["passage_key"])) for item in passages
    }
    valid = []
    for citation in output.citations:
        key = (citation.version, citation.passage_key)
        if key in allowed:
            valid.append({"version": key[0], "passage_key": key[1]})
            continue
        session.add(
            build_audit_event(
                "citation_dropped",
                {
                    "case_id": case_id,
                    "output_kind": "case_answer",
                    "passage_key": citation.passage_key,
                },
                case_id=case_id,
            )
        )
    return list({item["passage_key"]: item for item in valid}.values())


# Convert one stored row into the public question response shape.
def _response(row: CaseQuestion, asked_by: str | None) -> dict[str, object]:
    return {
        "id": row.id,
        "question": row.question,
        "answer": row.answer,
        "covered": row.covered,
        "citations": list(row.citations),
        "asked_by": asked_by or "Unknown underwriter",
        "created_at": row.created_at,
    }
