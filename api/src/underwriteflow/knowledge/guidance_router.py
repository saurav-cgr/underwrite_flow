"""Underwriter-only access to stored case route guidance."""

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from underwriteflow.auth.dependencies import require_underwriter
from underwriteflow.database import get_session
from underwriteflow.persistence.knowledge_models import (
    CaseGuidance,
    CaseKnowledgePin,
    KnowledgeVersion,
)
from underwriteflow.persistence.models import Case, Recommendation

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


router = APIRouter(prefix="/reviews", tags=["review-guidance"])


# Read the stored explanation and pinned version names without generating.
@router.get("/{case_id}/guidance", response_model=GuidanceResponse)
async def get_guidance(
    case_id: UUID,
    _: dict[str, object] = Depends(require_underwriter()),
    session: AsyncSession = Depends(get_session),
) -> GuidanceResponse:
    case = await session.scalar(select(Case).where(Case.id == case_id))
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")
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
