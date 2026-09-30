"""Administrator endpoints for the informational regulatory corpus."""

from pathlib import Path
from typing import Literal
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Request,
    UploadFile,
)
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from underwriteflow.auth.dependencies import require_permission
from underwriteflow.auth.schemas import Permission
from underwriteflow.database import get_session
from underwriteflow.knowledge.errors import (
    KnowledgeConflictError,
    KnowledgeError,
    KnowledgeValidationError,
)
from underwriteflow.knowledge.regulation import ManifestError
from underwriteflow.knowledge.regulation_service import RegulationService
from underwriteflow.knowledge.router import response_summary


class RegulationTagLimit(BaseModel):
    """One accepted clause limit an administrator may declare."""

    model_config = ConfigDict(extra="forbid")

    field: str = Field(min_length=1, max_length=100)
    operator: Literal[
        "equals",
        "greater_than",
        "greater_than_or_equal",
        "less_than",
        "less_than_or_equal",
    ]
    value: int | float = Field(allow_inf_nan=False)


class RegulationTagPayload(BaseModel):
    """Accept administrator topic tags and limits for one draft clause."""

    model_config = ConfigDict(extra="forbid")

    topic_tags: list[str] = Field(default_factory=list, max_length=20)
    # Omitted limits leave any accepted limits untouched.
    limits: list[RegulationTagLimit] | None = Field(
        default=None, max_length=50
    )


class RegulationTagResponse(BaseModel):
    """Return the accepted tags and limits of one clause."""

    passage_key: str
    topic_tags: list[str]
    limits: list[RegulationTagLimit]


router = APIRouter(prefix="/knowledge", tags=["regulation"])


# Import the manifest folder, storing one approved upload first if present.
@router.post("/regulation/import", status_code=201)
async def import_regulation(
    request: Request,
    file: UploadFile | None = File(default=None),
    admin: dict[str, str] = Depends(
        require_permission(Permission.PRODUCT_CONFIG_WRITE)
    ),
    session: AsyncSession = Depends(get_session),
) -> dict:
    root = regulatory_root(request)
    try:
        version, reports = await RegulationService().import_regulation(
            session,
            root,
            actor_user_id=UUID(admin["sub"]),
            upload=file,
        )
    except ManifestError as error:
        raise HTTPException(status_code=422, detail=str(error)) from None
    except KnowledgeValidationError as error:
        raise HTTPException(status_code=422, detail=str(error)) from None
    except KnowledgeConflictError as error:
        raise HTTPException(status_code=409, detail=str(error)) from None
    except KnowledgeError as error:
        raise HTTPException(status_code=422, detail=str(error)) from None
    summary = await response_summary(session, version.id)
    summary["files"] = [
        {
            "file": item.file,
            "status": item.status,
            "reason": item.reason,
            "clause_count": item.clause_count,
        }
        for item in reports
    ]
    return summary


# Accept administrator topic tags on one regulation draft clause.
@router.put(
    "/versions/{version_id}/passages/{passage_key}/tags",
    response_model=RegulationTagResponse,
)
async def accept_regulation_tags(
    version_id: UUID,
    passage_key: str,
    payload: RegulationTagPayload,
    admin: dict[str, str] = Depends(
        require_permission(Permission.PRODUCT_CONFIG_WRITE)
    ),
    session: AsyncSession = Depends(get_session),
) -> RegulationTagResponse:
    try:
        passage = await RegulationService().accept_tags(
            session,
            version_id,
            passage_key,
            payload.topic_tags,
            (
                [item.model_dump(mode="json") for item in payload.limits]
                if payload.limits is not None
                else None
            ),
            UUID(admin["sub"]),
        )
    except KnowledgeValidationError as error:
        raise HTTPException(status_code=422, detail=str(error)) from None
    except KnowledgeConflictError as error:
        raise HTTPException(status_code=409, detail=str(error)) from None
    except KnowledgeError as error:
        raise HTTPException(status_code=404, detail=str(error)) from None
    return RegulationTagResponse(
        passage_key=passage.passage_key,
        topic_tags=list(passage.topic_tags),
        limits=list(passage.limits),
    )


# Resolve the mounted regulatory folder from the running settings.
def regulatory_root(request: Request) -> Path:
    return Path(request.app.state.settings.regulatory_root)
