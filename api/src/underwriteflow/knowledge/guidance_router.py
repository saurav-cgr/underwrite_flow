"""Underwriter-only access to stored case route guidance."""

import logging
from collections.abc import Callable
from datetime import datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from underwriteflow.auth.dependencies import require_underwriter
from underwriteflow.database import get_session
from underwriteflow.knowledge.questions import ask_question, list_questions
from underwriteflow.persistence.knowledge_models import (
    CaseGuidance,
    CaseKnowledgePin,
    KnowledgeVersion,
)
from underwriteflow.persistence.models import Case, Recommendation
from underwriteflow.providers.embedding import build_embedding_provider
from underwriteflow.providers.guidance import build_guidance_provider
from underwriteflow.providers.service import ProviderError

LOGGER = logging.getLogger(__name__)
SYNTHETIC_LABEL = "SYNTHETIC - FOR DEMONSTRATION ONLY"


class GuidanceCitationResponse(BaseModel):
    """Public citation without passage body content."""

    version: str
    passage_key: str


class MissingGuidanceResponse(BaseModel):
    """One missing item and its cited reason."""

    item: str
    reason: str
    citations: list[GuidanceCitationResponse] = Field(default_factory=list)


class RouteExplanationResponse(BaseModel):
    """Stored route explanation shown to an underwriter."""

    status: Literal["generated", "template", "unavailable"]
    text: str
    missing_items: list[MissingGuidanceResponse] = Field(
        default_factory=list
    )
    citations: list[GuidanceCitationResponse] = Field(default_factory=list)
    label: str = SYNTHETIC_LABEL


class GuidanceResponse(BaseModel):
    """Complete guidance panel response for one review cycle."""

    pinned: dict[str, str | None]
    route_explanation: RouteExplanationResponse
    specialist_brief: None = None
    suggested_citations: list[GuidanceCitationResponse] = Field(
        default_factory=list
    )


class QuestionRequest(BaseModel):
    """One free-text underwriter question about a case."""

    question: str = Field(min_length=1, max_length=1000)


class QuestionResponse(BaseModel):
    """Stored question with its cited answer or the fallback phrase."""

    id: UUID
    question: str
    answer: str
    covered: bool
    citations: list[GuidanceCitationResponse] = Field(default_factory=list)
    asked_by: str
    created_at: datetime


router = APIRouter(prefix="/reviews", tags=["review-guidance"])


# Answer one question from pinned guidance and store the exchange.
@router.post(
    "/{case_id}/questions",
    response_model=QuestionResponse,
    status_code=201,
)
async def post_question(
    case_id: UUID,
    body: QuestionRequest,
    request: Request,
    current: dict[str, object] = Depends(require_underwriter()),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    case = await _case_or_404(session, case_id)
    settings = request.app.state.settings
    result = await ask_question(
        session,
        _optional(build_guidance_provider, settings),
        _optional(build_embedding_provider, settings),
        case,
        UUID(str(current["sub"])),
        body.question,
    )
    await session.commit()
    return result


# List every underwriter's questions for one case, oldest first.
@router.get("/{case_id}/questions", response_model=list[QuestionResponse])
async def get_questions(
    case_id: UUID,
    _: dict[str, object] = Depends(require_underwriter()),
    session: AsyncSession = Depends(get_session),
) -> list[dict[str, object]]:
    await _case_or_404(session, case_id)
    return await list_questions(session, case_id)


# Build one provider, or None so unusable settings yield the fallback.
def _optional(build: Callable[[object], object], settings: object) -> object:
    try:
        return build(settings)
    except ProviderError as error:
        LOGGER.warning(
            "case answer provider unavailable: error=%s",
            type(error).__name__,
        )
        return None


# Load one case or raise the shared not-found response.
async def _case_or_404(session: AsyncSession, case_id: UUID) -> Case:
    case = await session.scalar(select(Case).where(Case.id == case_id))
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")
    return case


# Read the stored explanation and pinned version names without generating.
@router.get("/{case_id}/guidance", response_model=GuidanceResponse)
async def get_guidance(
    case_id: UUID,
    _: dict[str, object] = Depends(require_underwriter()),
    session: AsyncSession = Depends(get_session),
) -> GuidanceResponse:
    case = await _case_or_404(session, case_id)
    pin = await session.scalar(
        select(CaseKnowledgePin).where(CaseKnowledgePin.case_id == case_id)
    )
    recommendation = await session.scalar(
        select(Recommendation).where(Recommendation.case_id == case_id)
    )
    guidance = await session.scalar(
        select(CaseGuidance).where(
            CaseGuidance.case_id == case_id,
            CaseGuidance.review_cycle == case.review_cycle,
            CaseGuidance.kind == "route_explanation",
        )
    )
    guideline_version = await _version_name(
        session,
        pin.guideline_version_id if pin else None,
    )
    regulation_version = await _version_name(
        session, pin.regulation_version_id
    ) if pin else None
    explanation = _explanation_response(guidance)
    if recommendation and recommendation.route == "manual":
        explanation = _unavailable_response()
    return GuidanceResponse(
        pinned={
            "guideline_version": guideline_version,
            "regulation_version": regulation_version,
        },
        route_explanation=explanation,
    )


# Resolve one pinned knowledge version to its stable version name.
async def _version_name(
    session: AsyncSession, version_id: UUID | None
) -> str | None:
    if version_id is None:
        return None
    version = await session.get(KnowledgeVersion, version_id)
    return version.version if version else None


# Convert stored JSON into the bounded public explanation response.
def _explanation_response(
    guidance: CaseGuidance | None,
) -> RouteExplanationResponse:
    if guidance is None:
        return _unavailable_response()
    body = guidance.body or {}
    citations = [
        GuidanceCitationResponse(
            version=str(item.get("version", "")),
            passage_key=str(item.get("passage_key", "")),
        )
        for item in guidance.citations or []
        if isinstance(item, dict)
    ]
    missing = [
        MissingGuidanceResponse(
            item=str(item.get("item", "")),
            reason=str(item.get("reason", "")),
            citations=[
                GuidanceCitationResponse(
                    version=str(citation.get("version", "")),
                    passage_key=str(citation.get("passage_key", "")),
                )
                for citation in item.get("citations", [])
                if isinstance(citation, dict)
            ],
        )
        for item in body.get("missing_items", [])
        if isinstance(item, dict)
    ]
    return RouteExplanationResponse(
        status=guidance.status,
        text=str(body.get("text", "")),
        missing_items=missing,
        citations=citations,
    )


# Return the fixed safe response when no stored explanation exists.
def _unavailable_response() -> RouteExplanationResponse:
    return RouteExplanationResponse(
        status="unavailable",
        text="Explanation unavailable.",
    )
