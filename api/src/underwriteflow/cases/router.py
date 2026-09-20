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
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from underwriteflow.auth.dependencies import (
    AuthorizationDenied,
    authorize_case_access,
    require_permission,
)
from underwriteflow.auth.schemas import Permission
from underwriteflow.cases.schemas import (
    ApplicationUpdate,
    CaseConfigurationResponse,
    CaseCreate,
    CaseDocumentResponse,
    CaseFieldResponse,
    CaseResponse,
    DocumentResponse,
    SubmitResponse,
)
from underwriteflow.cases.service import (
    CaseService,
    CaseValidationError,
    document_is_required,
    field_is_visible,
)
from underwriteflow.cases.validation import UnsupportedFieldError
from underwriteflow.products.schemas import (
    ProductConfiguration,
    filter_configuration_for_journey,
)
from underwriteflow.storage import StorageValidationError, UploadStorage
from underwriteflow.cases.submission import SubmissionService
from underwriteflow.providers.factory import build_provider
from underwriteflow.database import get_session
from underwriteflow.persistence.models import (
    Case,
    Document,
    ProductVersion,
    RulebookVersion,
    Submission,
)

router = APIRouter(prefix="/cases", tags=["cases"])


# Build the safe case response from its pinned product version.
async def case_response(session: AsyncSession, case: Case) -> CaseResponse:
    product_version = await session.scalar(
        select(ProductVersion).where(
            ProductVersion.id == case.product_version_id
        )
    )
    rulebook = await session.scalar(
        select(RulebookVersion).where(
            RulebookVersion.id == case.rulebook_version_id
        )
    )
    if product_version is None or rulebook is None:
        raise HTTPException(
            status_code=500,
            detail="Case configuration is unavailable",
        )
    return CaseResponse(
        id=case.id,
        product_code=product_version.configuration["product_code"],
        product_version=product_version.version,
        rulebook_version=rulebook.version,
        status=case.status,
        journey=case.journey_type,
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
    except UnsupportedFieldError as error:
        raise HTTPException(status_code=422, detail=str(error)) from None
    except CaseValidationError:
        raise HTTPException(
            status_code=422,
            detail="Invalid case submission",
        ) from None


# List every case owned by the authenticated identity, newest first.
@router.get("", response_model=list[CaseResponse])
async def list_cases(
    current: dict[str, str] = Depends(require_permission(Permission.CASE_READ)),
    session: AsyncSession = Depends(get_session),
) -> list[CaseResponse]:
    cases = list(
        await session.scalars(
            select(Case)
            .where(Case.applicant_user_id == UUID(current["sub"]))
            .order_by(Case.created_at.desc())
        )
    )
    return [await case_response(session, case) for case in cases]


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
        raise AuthorizationDenied(
            403,
            "case_ownership",
            actor_user_id=UUID(current["sub"]),
            case_id=case.id,
        )
    return case


# Return one authorized case with its pinned configuration identity.
@router.get("/{case_id}", response_model=CaseResponse)
async def read_case(
    case_id: UUID,
    current: dict[str, str] = Depends(require_permission(Permission.CASE_READ)),
    session: AsyncSession = Depends(get_session),
) -> CaseResponse:
    case = await get_authorized_case(case_id, current, session)
    return await case_response(session, case)


# Return the pinned configuration and resolved requirements for one case.
@router.get(
    "/{case_id}/configuration", response_model=CaseConfigurationResponse
)
async def read_case_configuration(
    case_id: UUID,
    current: dict[str, str] = Depends(require_permission(Permission.CASE_READ)),
    session: AsyncSession = Depends(get_session),
) -> CaseConfigurationResponse:
    case = await get_authorized_case(case_id, current, session)
    product_version = await session.scalar(
        select(ProductVersion).where(
            ProductVersion.id == case.product_version_id
        )
    )
    rulebook = await session.scalar(
        select(RulebookVersion).where(
            RulebookVersion.id == case.rulebook_version_id
        )
    )
    if product_version is None or rulebook is None:
        raise HTTPException(
            status_code=409,
            detail="Case configuration is unavailable",
        )
    try:
        configuration = filter_configuration_for_journey(
            ProductConfiguration.model_validate(product_version.configuration),
            case.journey_type,
        )
    except ValidationError:
        raise HTTPException(
            status_code=409,
            detail="Case configuration cannot be read",
        ) from None
    submission = await session.scalar(
        select(Submission).where(Submission.case_id == case_id)
    )
    payload = submission.payload.get("application", {}) if submission else {}
    return CaseConfigurationResponse(
        case_id=case.id,
        product_code=configuration.product_code,
        product_version=product_version.version,
        rulebook_version=rulebook.version,
        journey=case.journey_type,
        application=payload,
        fields=[
            CaseFieldResponse(
                key=field.key,
                label=field.label,
                type=field.type,
                required=field.required,
                help_text=field.help_text,
                validation=field.validation,
                options=field.options,
                visible_when=field.visible_when,
            )
            for field in configuration.fields
            if field_is_visible(field, payload)
        ],
        documents=[
            CaseDocumentResponse(
                code=document.code,
                title=document.title,
                requirement=document.requirement,
                required=document_is_required(document, payload),
                accepted_types=document.accepted_types,
                condition=document.condition,
                stage=document.stage,
            )
            for document in configuration.documents
        ],
    )


# Replace an owned, still-mutable case's stored draft answers.
@router.put("/{case_id}/application", response_model=CaseResponse)
async def replace_application(
    case_id: UUID,
    application: ApplicationUpdate,
    request: Request,
    current: dict[str, str] = Depends(
        require_permission(Permission.CASE_WRITE)
    ),
    session: AsyncSession = Depends(get_session),
) -> CaseResponse:
    case = await session.scalar(select(Case).where(Case.id == case_id))
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")
    if case.applicant_user_id != UUID(current["sub"]):
        raise AuthorizationDenied(
            403,
            "case_ownership",
            actor_user_id=UUID(current["sub"]),
            case_id=case.id,
        )
    try:
        await CaseService(
            UploadStorage(Path(request.app.state.settings.upload_root))
        ).replace_application(
            session, case, application, UUID(current["sub"])
        )
    except UnsupportedFieldError as error:
        raise HTTPException(status_code=422, detail=str(error)) from None
    except CaseValidationError:
        raise HTTPException(
            status_code=422,
            detail="Invalid application replacement",
        ) from None
    return await case_response(session, case)


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


# Restart processing for an owned case the underwriter returned for information.
@router.post("/{case_id}/resubmit", response_model=SubmitResponse)
async def resubmit_case(
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
        ).resubmit(session, case, UUID(current["sub"]))
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
    documents = await session.scalars(
        select(Document).where(Document.case_id == case_id)
    )
    return [
        DocumentResponse.model_validate(document, from_attributes=True)
        for document in documents
    ]


# Store one supported applicant document for an owned case.
@router.post("/{case_id}/documents", response_model=DocumentResponse)
async def upload_document(
    case_id: UUID,
    request: Request,
    document: UploadFile = File(...),
    document_code: str = Form(...),
    current: dict[str, str] = Depends(
        require_permission(Permission.CASE_WRITE)
    ),
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
        raise HTTPException(
            status_code=422,
            detail="Invalid document upload",
        ) from None
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
