"""Administrator reference-document endpoints for product configuration."""

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
from sqlalchemy.ext.asyncio import AsyncSession

from underwriteflow.auth.dependencies import require_permission
from underwriteflow.auth.schemas import Permission
from underwriteflow.database import get_session
from underwriteflow.persistence.models import ReferenceDocument
from underwriteflow.products.service import (
    ProductConfigurationError,
    ProductService,
)
from underwriteflow.storage import StorageValidationError, UploadStorage

router = APIRouter(tags=["products"])


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


# Store one administrator reference document for a product version.
@router.post("/{product_code}/references")
async def upload_reference_document(
    product_code: str,
    request: Request,
    reference: UploadFile = File(...),
    version: str = Form(..., max_length=100),
    admin: dict[str, str] = Depends(
        require_permission(Permission.SCHEMAS_EDIT)
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
        require_permission(Permission.SCHEMAS_EDIT)
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
