"""Administrator product configuration endpoints."""

import re
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from underwriteflow.auth.dependencies import require_permission
from underwriteflow.auth.schemas import Permission
from underwriteflow.database import get_session
from underwriteflow.persistence.models import Product, ProductVersion
from underwriteflow.products.reference_router import (
    router as reference_router,
)
from underwriteflow.products.schemas import (
    ProductConfiguration,
    VersionPayload,
    YamlPayload,
    filter_configuration_for_journey,
)
from underwriteflow.products.service import (
    ProductConfigurationCorruptError,
    ProductConfigurationError,
    ProductConflictError,
    ProductService,
    load_configuration,
)

router = APIRouter(prefix="/products", tags=["products"])
router.include_router(reference_router)

SAFE_FILENAME_CHARS = re.compile(r"[^A-Za-z0-9._-]")


# Build a header-safe attachment filename from untrusted path segments.
def export_filename(product_code: str, version: str) -> str:
    code = SAFE_FILENAME_CHARS.sub("_", product_code)
    safe_version = SAFE_FILENAME_CHARS.sub("_", version)
    return f"{code}-{safe_version}.yaml"


# Return every product and its active version for administrator selection.
@router.get("")
async def list_products(
    _: dict[str, str] = Depends(
        require_permission(Permission.PRODUCT_CONFIG_READ)
    ),
    session: AsyncSession = Depends(get_session),
) -> list[dict[str, str | None]]:
    rows = await session.execute(
        select(Product, ProductVersion.version)
        .outerjoin(
            ProductVersion,
            and_(
                ProductVersion.product_id == Product.id,
                ProductVersion.status == "active",
            ),
        )
        .order_by(Product.code)
    )
    return [
        {
            "product_code": product.code,
            "title": product.title,
            "family": product.family,
            "status": product.status,
            "active_version": active_version,
        }
        for product, active_version in rows
    ]


# Return active product fields without exposing routing rules to applicants.
@router.get("/catalog")
async def list_catalog(
    journey: str | None = None,
    _: dict[str, str] = Depends(
        require_permission(Permission.CASE_WRITE)
    ),
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    versions = await session.scalars(
        select(ProductVersion)
        .where(ProductVersion.status == "active")
        .order_by(ProductVersion.version.asc())
    )
    catalog = []
    for version in versions:
        configuration = ProductConfiguration.model_validate(
            version.configuration
        )
        supported = configuration.supported_journeys
        if journey is not None and journey not in supported:
            continue
        shown = (
            filter_configuration_for_journey(configuration, journey)
            if journey is not None
            else configuration
        )
        catalog.append(
            {
                "product_code": shown.product_code,
                "title": shown.title,
                "family": shown.family,
                "scope": shown.scope,
                "description": shown.description,
                "version": version.version,
                "supported_journeys": configuration.supported_journeys,
                "fields": [
                    field.model_dump(mode="json") for field in shown.fields
                ],
                "documents": [
                    document.model_dump(mode="json")
                    for document in shown.documents
                ],
            }
        )
    return catalog


# Parse one administrator-submitted configuration or return a safe client error.
def parse_configuration(payload: YamlPayload):
    try:
        return load_configuration(payload.yaml_text)
    except ProductConfigurationError as error:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid product configuration: {error}",
        ) from None


# Validate product YAML without changing the active configuration.
@router.post("/validate")
async def validate_configuration(
    payload: YamlPayload,
    _: dict[str, str] = Depends(
        require_permission(Permission.SCHEMAS_EDIT)
    ),
) -> dict[str, str]:
    configuration = parse_configuration(payload)
    return {
        "product_code": configuration.product_code,
        "version": configuration.version,
    }


# Preview the normalized impact of product YAML without persistence.
@router.post("/preview")
async def preview_configuration(
    payload: YamlPayload,
    _: dict[str, str] = Depends(
        require_permission(Permission.SCHEMAS_EDIT)
    ),
) -> dict:
    return ProductService().preview(parse_configuration(payload))


# Import validated YAML as a draft version for administrator review.
@router.post("/import")
async def import_configuration(
    payload: YamlPayload,
    admin: dict[str, str] = Depends(
        require_permission(Permission.SCHEMAS_EDIT)
    ),
    session: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    configuration = parse_configuration(payload)
    try:
        version = await ProductService().import_configuration(
            session,
            configuration,
            UUID(admin["sub"]),
        )
    except ProductConfigurationError as error:
        raise HTTPException(status_code=409, detail=str(error)) from None
    return {
        "product_code": configuration.product_code,
        "version": version.version,
        "status": version.status,
    }


# Return immutable configuration version history to an administrator.
@router.get("/{product_code}/history")
async def list_history(
    product_code: str,
    _: dict[str, str] = Depends(
        require_permission(Permission.PRODUCT_CONFIG_READ)
    ),
    session: AsyncSession = Depends(get_session),
) -> list[dict[str, str | None]]:
    versions = await ProductService().repository.list_versions(
        session,
        product_code,
    )
    return [
        {
            "version": version.version,
            "status": version.status,
            "content_hash": version.content_hash,
            "activated_at": (
                version.activated_at.isoformat()
                if version.activated_at
                else None
            ),
        }
        for version in versions
    ]


# Return one persisted version's validated, normalized configuration.
@router.get("/{product_code}/versions/{version}")
async def read_version_configuration(
    product_code: str,
    version: str,
    _: dict[str, str] = Depends(
        require_permission(Permission.PRODUCT_CONFIG_READ)
    ),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    try:
        configuration = await ProductService().read_version(
            session, product_code, version
        )
    except ProductConfigurationCorruptError as error:
        raise HTTPException(status_code=422, detail=str(error)) from None
    except ProductConfigurationError as error:
        raise HTTPException(status_code=404, detail=str(error)) from None
    return configuration.model_dump(mode="json")


# Export one persisted version as a canonical YAML attachment.
@router.get("/{product_code}/versions/{version}/export")
async def export_version_configuration(
    product_code: str,
    version: str,
    _: dict[str, str] = Depends(
        require_permission(Permission.PRODUCT_CONFIG_READ)
    ),
    session: AsyncSession = Depends(get_session),
) -> Response:
    try:
        yaml_text = await ProductService().export_version(
            session, product_code, version
        )
    except ProductConfigurationCorruptError as error:
        raise HTTPException(status_code=422, detail=str(error)) from None
    except ProductConfigurationError as error:
        raise HTTPException(status_code=404, detail=str(error)) from None
    filename = export_filename(product_code, version)
    return Response(
        content=yaml_text,
        media_type="application/yaml",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        },
    )


# Activate one version and retire the previous active version.
@router.post("/{product_code}/activate")
async def activate_configuration(
    product_code: str,
    payload: VersionPayload,
    admin: dict[str, str] = Depends(
        require_permission(Permission.SCHEMAS_EDIT)
    ),
    session: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    try:
        version = await ProductService().activate(
            session,
            product_code,
            payload.version,
            UUID(admin["sub"]),
        )
    except ProductConflictError as error:
        raise HTTPException(status_code=409, detail=str(error)) from None
    except ProductConfigurationError as error:
        raise HTTPException(status_code=404, detail=str(error)) from None
    return {
        "product_code": product_code,
        "version": version.version,
        "status": version.status,
    }


# Retire one configuration version and record the administrator action.
@router.post("/{product_code}/retire")
async def retire_configuration(
    product_code: str,
    payload: VersionPayload,
    admin: dict[str, str] = Depends(
        require_permission(Permission.SCHEMAS_EDIT)
    ),
    session: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    try:
        version = await ProductService().retire(
            session,
            product_code,
            payload.version,
            UUID(admin["sub"]),
        )
    except ProductConfigurationError as error:
        raise HTTPException(status_code=404, detail=str(error)) from None
    return {
        "product_code": product_code,
        "version": version.version,
        "status": version.status,
    }
