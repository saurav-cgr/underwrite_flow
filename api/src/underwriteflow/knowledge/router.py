"""Administrator endpoints for fictional guideline versions."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from underwriteflow.auth.dependencies import require_permission
from underwriteflow.auth.schemas import Permission
from underwriteflow.database import get_session
from underwriteflow.knowledge.errors import (
    KnowledgeConflictError,
    KnowledgeError,
    KnowledgeValidationError,
)
from underwriteflow.knowledge.repository import KnowledgeRepository
from underwriteflow.knowledge.regulation_service import RegulationService
from underwriteflow.knowledge.schemas import (
    KnowledgePreviewResponse,
    KnowledgeYamlPayload,
)
from underwriteflow.knowledge.service import KnowledgeService


router = APIRouter(prefix="/knowledge", tags=["knowledge"])
SHARED_SCOPES = {"regulation"}


# Require guideline scope for the first versioned knowledge API.
def validate_scope(scope: str) -> None:
    if scope != "guideline":
        raise HTTPException(status_code=422, detail="unsupported scope")


# Accept a shared scope for reading, which loads no product corpus.
def validate_list_scope(scope: str) -> None:
    if scope != "guideline" and scope not in SHARED_SCOPES:
        raise HTTPException(status_code=422, detail="unsupported scope")


# Return a safe summary with its resolved product code.
async def response_summary(
    session: AsyncSession, version_id: UUID
) -> dict:
    repository = KnowledgeRepository()
    version = await repository.find(session, version_id)
    if version is None:
        raise HTTPException(
            status_code=404, detail="Knowledge version not found"
        )
    product = (
        await repository.find_product_by_id(session, version.product_id)
        if version.product_id is not None
        else None
    )
    return await KnowledgeService().summary(
        session, version, product.code if product else None
    )


# Validate guideline YAML without persisting a version.
@router.post("/validate")
async def validate_knowledge(
    payload: KnowledgeYamlPayload,
    _: dict[str, str] = Depends(
        require_permission(Permission.PRODUCT_CONFIG_WRITE)
    ),
    session: AsyncSession = Depends(get_session),
) -> dict:
    validate_scope(payload.scope)
    try:
        _, report = await KnowledgeService().validate(session, payload.yaml)
    except KnowledgeError as error:
        raise HTTPException(status_code=422, detail=str(error)) from None
    return report


# Import one guideline YAML as an immutable draft version.
@router.post("/import", status_code=201)
async def import_knowledge(
    payload: KnowledgeYamlPayload,
    admin: dict[str, str] = Depends(
        require_permission(Permission.PRODUCT_CONFIG_WRITE)
    ),
    session: AsyncSession = Depends(get_session),
) -> dict:
    validate_scope(payload.scope)
    try:
        version = await KnowledgeService().import_guideline(
            session, payload.yaml, UUID(admin["sub"])
        )
    except KnowledgeConflictError as error:
        raise HTTPException(status_code=409, detail=str(error)) from None
    except KnowledgeError as error:
        raise HTTPException(status_code=422, detail=str(error)) from None
    return await response_summary(session, version.id)


# List knowledge versions newest first for administrator review.
@router.get("/versions")
async def list_knowledge_versions(
    scope: str | None = None,
    product_code: str | None = None,
    _: dict[str, str] = Depends(
        require_permission(Permission.PRODUCT_CONFIG_READ)
    ),
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    if scope is not None:
        validate_list_scope(scope)
    rows = await KnowledgeRepository().list_versions(
        session, scope, product_code
    )
    return [
        {
            "id": version.id,
            "scope": version.scope,
            "product_code": code,
            "version": version.version,
            "status": version.status,
            "content_type": version.content_type,
            "passage_count": count,
            "activated_at": version.activated_at,
        }
        for version, code, count in rows
    ]


# Return bounded passage text for one selected version.
@router.get("/versions/{version_id}/preview")
async def preview_knowledge(
    version_id: UUID,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
    _: dict[str, str] = Depends(
        require_permission(Permission.PRODUCT_CONFIG_READ)
    ),
    session: AsyncSession = Depends(get_session),
) -> KnowledgePreviewResponse:
    repository = KnowledgeRepository()
    version = await repository.find(session, version_id)
    if version is None:
        raise HTTPException(
            status_code=404, detail="Knowledge version not found"
        )
    summary = await response_summary(session, version_id)
    passages = await repository.list_passages(
        session, version_id, offset=offset, limit=limit
    )
    items = []
    for passage in passages:
        items.append(
            {
                "passage_key": passage.passage_key,
                "title": passage.title,
                "topic": passage.topic,
                "bands": {
                    "age_min": passage.age_min,
                    "age_max": passage.age_max,
                    "sum_assured_min": passage.sum_assured_min,
                    "sum_assured_max": passage.sum_assured_max,
                },
                "label": passage.label,
                "body": passage.body,
                "thresholds": passage.thresholds,
                "topic_tags": passage.topic_tags,
                "suggested_tags": passage.suggested_tags,
                "limits": passage.limits,
            }
        )
    return KnowledgePreviewResponse(
        version=summary,
        validation=version.validation,
        passages=items,
    )


# Activate one validated draft and retire its active sibling.
@router.post("/versions/{version_id}/activate")
async def activate_knowledge(
    version_id: UUID,
    admin: dict[str, str] = Depends(
        require_permission(Permission.PRODUCT_CONFIG_WRITE)
    ),
    session: AsyncSession = Depends(get_session),
) -> dict:
    actor = UUID(admin["sub"])
    existing = await KnowledgeRepository().find(session, version_id)
    service = (
        RegulationService()
        if existing is not None and existing.scope in SHARED_SCOPES
        else KnowledgeService()
    )
    try:
        version = await service.activate(session, version_id, actor)
    except KnowledgeValidationError as error:
        raise HTTPException(status_code=422, detail=str(error)) from None
    except KnowledgeConflictError as error:
        raise HTTPException(status_code=409, detail=str(error)) from None
    except KnowledgeError as error:
        raise HTTPException(status_code=404, detail=str(error)) from None
    return await response_summary(session, version.id)


# Retire one knowledge version without creating a replacement.
@router.post("/versions/{version_id}/retire")
async def retire_knowledge(
    version_id: UUID,
    admin: dict[str, str] = Depends(
        require_permission(Permission.PRODUCT_CONFIG_WRITE)
    ),
    session: AsyncSession = Depends(get_session),
) -> dict:
    try:
        version = await KnowledgeService().retire(
            session, version_id, UUID(admin["sub"])
        )
    except KnowledgeError as error:
        raise HTTPException(status_code=404, detail=str(error)) from None
    return await response_summary(session, version.id)
