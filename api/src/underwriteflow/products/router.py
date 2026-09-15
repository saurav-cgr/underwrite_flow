"""Administrator product configuration endpoints."""

from pathlib import Path
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    Response,
    UploadFile,
)
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from underwriteflow.auth.dependencies import require_permission
from underwriteflow.auth.schemas import Permission
from underwriteflow.database import get_session
from underwriteflow.persistence.models import (
    Product,
    ProductVersion,
    ReferenceDocument,
)
from underwriteflow.products.schemas import VersionPayload, YamlPayload
from underwriteflow.products.service import (
    ProductConfigurationError,
    ProductConflictError,
    ProductService,
    load_configuration,
)
from underwriteflow.storage import StorageValidationError, UploadStorage

router = APIRouter(prefix="/products", tags=["products"])


# Build the safe reference metadata response without storage keys.
def reference_response(document: ReferenceDocument) -> dict[str, object]:
    return {
        "id": str(document.id),
        "version": document.version,
        "filename": document.filename,
        "content_type": document.content_type,
        "byte_size": document.byte_size,
        "content_hash": document.content_hash,
        "page_count": document.page_count,
    }


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
        configuration = version.configuration
        catalog.append(
            {
                "product_code": configuration["product_code"],
                "title": configuration["title"],
                "family": configuration["family"],
                "scope": configuration["scope"],
                "description": configuration["description"],
                "version": version.version,
                "fields": configuration["fields"],
                "documents": configuration["documents"],
            }
        )
    return catalog


# Parse one administrator-submitted configuration or return a safe client error.
def parse_configuration(payload: YamlPayload):
    try:
        return load_configuration(payload.yaml_text)
    except ProductConfigurationError:
        raise HTTPException(
            status_code=422,
            detail="Invalid product configuration",
        ) from None


# Validate product YAML without changing the active configuration.
@router.post("/validate")
async def validate_configuration(
    payload: YamlPayload,
    _: dict[str, str] = Depends(
        require_permission(Permission.PRODUCT_CONFIG_WRITE)
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
        require_permission(Permission.PRODUCT_CONFIG_WRITE)
    ),
) -> dict:
    return ProductService().preview(parse_configuration(payload))


# Import validated YAML as a draft version for administrator review.
@router.post("/import")
async def import_configuration(
    payload: YamlPayload,
    admin: dict[str, str] = Depends(
        require_permission(Permission.PRODUCT_CONFIG_WRITE)
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


# Activate one version and retire the previous active version.
@router.post("/{product_code}/activate")
async def activate_configuration(
    product_code: str,
    payload: VersionPayload,
    admin: dict[str, str] = Depends(
        require_permission(Permission.PRODUCT_CONFIG_WRITE)
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
        require_permission(Permission.PRODUCT_CONFIG_WRITE)
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


# Store one administrator reference document for a product version.
@router.post("/{product_code}/references")
async def upload_reference_document(
    product_code: str,
    request: Request,
    reference: UploadFile = File(...),
    version: str = Form(..., max_length=100),
    admin: dict[str, str] = Depends(
        require_permission(Permission.PRODUCT_CONFIG_WRITE)
    ),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    try:
        document = await ProductService().add_reference_document(
            session,
            product_code,
            version,
            reference,
            UploadStorage(Path(request.app.state.settings.upload_root)),
            UUID(admin["sub"]),
        )
    except (ProductConfigurationError, StorageValidationError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from None
    return reference_response(document)


# List administrator reference documents for a product.
@router.get("/{product_code}/references")
async def list_reference_documents(
    product_code: str,
    version: str | None = None,
    _: dict[str, str] = Depends(
        require_permission(Permission.PRODUCT_CONFIG_READ)
    ),
    session: AsyncSession = Depends(get_session),
) -> list[dict[str, object]]:
    documents = await ProductService().list_reference_documents(
        session, product_code, version
    )
    return [reference_response(document) for document in documents]


# Remove one administrator reference document.
@router.delete("/{product_code}/references/{reference_id}", status_code=204)
async def delete_reference_document(
    product_code: str,
    reference_id: UUID,
    request: Request,
    admin: dict[str, str] = Depends(
        require_permission(Permission.PRODUCT_CONFIG_WRITE)
    ),
    session: AsyncSession = Depends(get_session),
) -> Response:
    try:
        await ProductService().remove_reference_document(
            session,
            product_code,
            reference_id,
            UploadStorage(Path(request.app.state.settings.upload_root)),
            UUID(admin["sub"]),
        )
    except ProductConfigurationError as error:
        raise HTTPException(status_code=404, detail=str(error)) from None
    return Response(status_code=204)
