"""Applicant case and document endpoints."""

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
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from underwriteflow.auth.dependencies import authorize_case_access, require_permission
from underwriteflow.auth.schemas import Permission
from underwriteflow.cases.schemas import (
    CaseCreate,
    CaseResponse,
    DocumentResponse,
    SubmitResponse,
)
from underwriteflow.cases.service import CaseService, CaseValidationError
from underwriteflow.cases.storage import StorageValidationError, UploadStorage
from underwriteflow.cases.submission import SubmissionService
from underwriteflow.providers.factory import build_provider
from underwriteflow.database import get_session
from underwriteflow.persistence.models import Case, Document, ProductVersion, RulebookVersion

router = APIRouter(prefix="/cases", tags=["cases"])


# Build the safe case response from its pinned product version.
async def case_response(session: AsyncSession, case: Case) -> CaseResponse:
    product_version = await session.scalar(
        select(ProductVersion).where(ProductVersion.id == case.product_version_id)
    )
    rulebook = await session.scalar(
        select(RulebookVersion).where(RulebookVersion.id == case.rulebook_version_id)
    )
    if product_version is None or rulebook is None:
        raise HTTPException(status_code=500, detail="Case configuration is unavailable")
    return CaseResponse(
        id=case.id,
        product_code=product_version.configuration["product_code"],
        product_version=product_version.version,
        rulebook_version=rulebook.version,
        status=case.status,
    )


# Create an applicant-owned case against the active configuration.
@router.post("", response_model=CaseResponse)
async def create_case(
    application: CaseCreate,
    request: Request,
    current: dict[str, str] = Depends(
        require_permission(Permission.CASE_WRITE)
    ),
    session: AsyncSession = Depends(get_session),
) -> CaseResponse:
    try:
        case = await CaseService(
            UploadStorage(Path(request.app.state.settings.upload_root))
        ).create_case(session, UUID(current["sub"]), application)
        return await case_response(session, case)
    except CaseValidationError:
        raise HTTPException(status_code=422, detail="Invalid case submission") from None


# Load one case only when the current role owns or may review it.
async def get_authorized_case(
    case_id: UUID,
    current: dict[str, str],
    session: AsyncSession,
) -> Case:
    case = await session.scalar(select(Case).where(Case.id == case_id))
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")
    if not authorize_case_access(current, case.applicant_user_id):
        raise HTTPException(status_code=403, detail="Forbidden")
    return case


# Return one authorized case with its pinned configuration identity.
@router.get("/{case_id}", response_model=CaseResponse)
async def read_case(
    case_id: UUID,
    current: dict[str, str] = Depends(require_permission(Permission.CASE_READ)),
    session: AsyncSession = Depends(get_session),
) -> CaseResponse:
    return await case_response(session, await get_authorized_case(case_id, current, session))


# Submit an owned case for evidence processing and human review.
@router.post("/{case_id}/submit", response_model=SubmitResponse)
async def submit_case(
    case_id: UUID,
    request: Request,
    current: dict[str, str] = Depends(
        require_permission(Permission.CASE_WRITE)
    ),
    session: AsyncSession = Depends(get_session),
) -> SubmitResponse:
    case = await get_authorized_case(case_id, current, session)
    settings = request.app.state.settings
    try:
        result = await SubmissionService(
            build_provider(settings),
            settings.upload_root,
            settings.database_url,
            retry_count=settings.provider_retry_count,
        ).submit(session, case, UUID(current["sub"]))
    except CaseValidationError as error:
        raise HTTPException(status_code=422, detail=str(error)) from None
    return SubmitResponse(
        id=case_id,
        status=str(result["status"]),
        recommendation=result["recommendation"],
    )


# Return safe metadata for all documents attached to an authorized case.
@router.get("/{case_id}/documents", response_model=list[DocumentResponse])
async def list_documents(
    case_id: UUID,
    current: dict[str, str] = Depends(require_permission(Permission.CASE_READ)),
    session: AsyncSession = Depends(get_session),
) -> list[DocumentResponse]:
    await get_authorized_case(case_id, current, session)
    documents = await session.scalars(select(Document).where(Document.case_id == case_id))
    return [DocumentResponse.model_validate(document, from_attributes=True) for document in documents]


# Store one supported applicant document for an owned case.
@router.post("/{case_id}/documents", response_model=DocumentResponse)
async def upload_document(
    case_id: UUID,
    request: Request,
    document: UploadFile = File(...),
    document_code: str = Form(...),
    current: dict[str, str] = Depends(require_permission(Permission.CASE_WRITE)),
    session: AsyncSession = Depends(get_session),
) -> DocumentResponse:
    case = await get_authorized_case(case_id, current, session)
    try:
        stored = await CaseService(
            UploadStorage(Path(request.app.state.settings.upload_root))
        ).add_document(
            session, case, document, document_code, UUID(current["sub"])
        )
    except (CaseValidationError, StorageValidationError):
        raise HTTPException(status_code=422, detail="Invalid document upload") from None
    return DocumentResponse.model_validate(stored, from_attributes=True)


# Remove one applicant document before the case enters workflow review.
@router.delete("/{case_id}/documents/{document_id}", status_code=204)
async def delete_document(
    case_id: UUID,
    document_id: UUID,
    request: Request,
    current: dict[str, str] = Depends(
        require_permission(Permission.CASE_WRITE)
    ),
    session: AsyncSession = Depends(get_session),
) -> Response:
    case = await get_authorized_case(case_id, current, session)
    try:
        await CaseService(
            UploadStorage(Path(request.app.state.settings.upload_root))
        ).remove_document(session, case, document_id, UUID(current["sub"]))
    except (CaseValidationError, StorageValidationError):
        raise HTTPException(
            status_code=422,
            detail="Document cannot be removed",
        ) from None
    return Response(status_code=204)
