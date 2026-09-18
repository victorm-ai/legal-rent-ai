"""Contract and document upload routes (RF-03, RF-04, RF-05)."""

from typing import List

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import Response

from api.middleware.auth import require_auth, require_client, require_lawyer
from auth.download_token import DownloadTokenService
from api.schemas.retention import RetentionPolicyResponse
from api.schemas.analyses import AnalysisDetailResponse, AnalysisStartRequest, AnalysisSummaryResponse
from api.routes.analyses import _detail_to_response, _summary_to_response
from api.schemas.contracts import (
    ContractDocumentResponse,
    ContractPartyResponse,
    ContractResponse,
    ContractSummaryResponse,
    ContractUpdateRequest,
    DocumentTextResponse,
    DownloadTokenResponse,
)
from config.settings import get_settings
from data.contract_dto import ContractDTO, ContractDocumentDTO, ContractPartyDTO, ContractSummaryDTO
from document.validation import DocumentValidationError
from domain.contract_status import InvalidStatusTransitionError
from services.analysis_service import (
    AnalysisPipelineError,
    AnalysisService,
)
from services.contract_service import (
    ContractAccessError,
    ContractNotFoundError,
    ContractService,
    DocumentNotFoundError,
)
from services.retention_service import RetentionService
from api.schemas.delivery import ReviewMessageResponse, SendReviewMessageRequest
from api.routes import review_communication as review_communication_routes
from services.review_communication_service import (
    ReviewCommunicationError,
    ReviewCommunicationService,
)
from services.comparison_service import ComparisonError, ComparisonService
from api.routes.comparisons import ComparisonResponse, _comparison_to_response

router = APIRouter(prefix="/contracts", tags=["contracts"])


async def _read_upload_limited(upload: UploadFile) -> bytes:
    """Read upload bytes enforcing the configured size limit."""
    max_size = get_settings().max_upload_size_bytes
    chunks: list[bytes] = []
    total = 0

    while True:
        chunk = await upload.read(1024 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > max_size:
            raise HTTPException(
                status_code=413,
                detail="File exceeds the maximum allowed size of 25 MB",
            )
        chunks.append(chunk)

    return b"".join(chunks)


def _document_to_response(document: ContractDocumentDTO) -> ContractDocumentResponse:
    return ContractDocumentResponse(
        id=document.id,
        file_name=document.file_name,
        document_type=document.document_type,
        mime_type=document.mime_type,
        file_size_bytes=document.file_size_bytes,
        page_count=document.page_count,
        extraction_method=document.extraction_method,
        is_signed_version=document.is_signed_version,
        uploaded_at=document.uploaded_at,
    )


def _party_to_response(party: ContractPartyDTO) -> ContractPartyResponse:
    return ContractPartyResponse(
        party_type=party.party_type,
        name=party.name,
        legal_representative=party.legal_representative,
        confidence=party.confidence,
        source_page=party.source_page,
    )


def _contract_to_response(contract: ContractDTO) -> ContractResponse:
    return ContractResponse(
        id=contract.id,
        user_id=contract.user_id,
        perspective=contract.perspective,
        jurisdiction=contract.jurisdiction,
        status=contract.status,
        title=contract.title,
        closure_notes=contract.closure_notes,
        documents=[_document_to_response(doc) for doc in contract.documents],
        parties=[_party_to_response(party) for party in contract.parties],
        created_at=contract.created_at,
        updated_at=contract.updated_at,
    )


def _contract_summary_to_response(
    contract: ContractSummaryDTO,
    unread_review_messages: int = 0,
) -> ContractSummaryResponse:
    return ContractSummaryResponse(
        id=contract.id,
        user_id=contract.user_id,
        perspective=contract.perspective,
        jurisdiction=contract.jurisdiction,
        status=contract.status,
        title=contract.title,
        document_count=contract.document_count,
        document_types=contract.document_types,
        parties=[_party_to_response(party) for party in contract.parties],
        is_deleted=contract.is_deleted,
        deleted_at=contract.deleted_at,
        purge_eligible_at=contract.purge_eligible_at,
        unread_review_messages=unread_review_messages,
        created_at=contract.created_at,
        updated_at=contract.updated_at,
    )


@router.get("", response_model=List[ContractSummaryResponse])
async def list_contracts(current_user: dict = Depends(require_auth)):
    """List contracts visible to the authenticated user."""
    service = ContractService()
    summaries = service.list_contracts(current_user)
    unread_counts = ReviewCommunicationService().unread_counts_by_contract(
        current_user,
        [item.id for item in summaries],
    )
    return [
        _contract_summary_to_response(item, unread_counts.get(item.id, 0))
        for item in summaries
    ]


@router.post("/{contract_id}/review-messages/mark-read", status_code=204)
async def mark_review_messages_read(
    contract_id: str,
    current_user: dict = Depends(require_auth),
):
    """Mark review chat messages as read for the current user on this contract."""
    service = ReviewCommunicationService()
    try:
        service.mark_contract_read(current_user, contract_id)
    except ContractAccessError as exc:
        raise HTTPException(status_code=403, detail=exc.message) from exc
    return Response(status_code=204)


@router.get(
    "/{contract_id}/review-messages",
    response_model=List[ReviewMessageResponse],
)
async def list_contract_review_messages(
    contract_id: str,
    current_user: dict = Depends(require_auth),
):
    """List client–lawyer review messages for a contract."""
    service = ReviewCommunicationService()
    try:
        items = service.list_messages_for_contract(current_user, contract_id)
    except ContractAccessError as exc:
        raise HTTPException(status_code=403, detail=exc.message) from exc
    return [review_communication_routes._to_response(item) for item in items]


@router.post(
    "/{contract_id}/review-messages",
    response_model=ReviewMessageResponse,
    status_code=201,
)
async def send_contract_review_message(
    contract_id: str,
    body: SendReviewMessageRequest,
    current_user: dict = Depends(require_auth),
):
    """Send a client–lawyer review message for a contract."""
    service = ReviewCommunicationService()
    try:
        message = service.send_message_for_contract(current_user, contract_id, body.content)
    except ContractNotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.message) from exc
    except ContractAccessError as exc:
        raise HTTPException(status_code=403, detail=exc.message) from exc
    except ReviewCommunicationError as exc:
        raise HTTPException(status_code=422, detail=exc.message) from exc
    return review_communication_routes._to_response(message)


@router.get("/retention-policy", response_model=RetentionPolicyResponse)
async def get_retention_policy(_current_user: dict = Depends(require_auth)):
    """Return the configured document retention policy (RF-54)."""
    policy = RetentionService().get_policy()
    return RetentionPolicyResponse(
        soft_delete_retention_days=policy.soft_delete_retention_days,
        description=policy.description,
    )


@router.post("", response_model=ContractResponse, status_code=201)
async def create_contract(
    file: UploadFile = File(...),
    perspective: str = Form(...),
    title: str | None = Form(None),
    current_user: dict = Depends(require_client),
):
    """Create a contract and upload the first PDF/DOCX document (RF-03, RF-04, RF-08)."""
    service = ContractService()
    content = await _read_upload_limited(file)

    try:
        validated = service.validate_upload(
            file_name=file.filename or "",
            content=content,
            content_type=file.content_type,
        )
        contract = service.create_contract_with_document(
            current_user=current_user,
            perspective=perspective,
            validated_document=validated,
            title=title,
        )
    except DocumentValidationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    return _contract_to_response(contract)


@router.get("/{contract_id}/parties", response_model=List[ContractPartyResponse])
async def list_contract_parties(
    contract_id: str,
    current_user: dict = Depends(require_auth),
):
    """List parties identified for a contract (RF-12)."""
    service = ContractService()
    try:
        contract = service.get_contract(current_user, contract_id)
    except ContractNotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.message) from exc
    except ContractAccessError as exc:
        raise HTTPException(status_code=403, detail=exc.message) from exc

    return [_party_to_response(party) for party in contract.parties]


@router.get("/{contract_id}", response_model=ContractResponse)
async def get_contract(
    contract_id: str,
    current_user: dict = Depends(require_auth),
):
    """Get contract details with associated documents."""
    service = ContractService()
    try:
        contract = service.get_contract(current_user, contract_id)
    except ContractNotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.message) from exc
    except ContractAccessError as exc:
        raise HTTPException(status_code=403, detail=exc.message) from exc

    return _contract_to_response(contract)


@router.patch("/{contract_id}", response_model=ContractResponse)
async def update_contract(
    contract_id: str,
    payload: ContractUpdateRequest,
    current_user: dict = Depends(require_auth),
):
    """Update contract metadata or lifecycle status (RF-56)."""
    if payload.status is None and payload.title is None and payload.closure_notes is None:
        raise HTTPException(status_code=400, detail="Provide status, title, or closure_notes to update")

    service = ContractService()
    try:
        contract = service.update_contract(
            current_user=current_user,
            contract_id=contract_id,
            status=payload.status,
            title=payload.title,
            closure_notes=payload.closure_notes,
        )
    except ContractNotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.message) from exc
    except ContractAccessError as exc:
        raise HTTPException(status_code=403, detail=exc.message) from exc
    except InvalidStatusTransitionError as exc:
        raise HTTPException(status_code=400, detail=exc.message) from exc

    return _contract_to_response(contract)


@router.delete("/{contract_id}", status_code=204)
async def delete_contract(
    contract_id: str,
    current_user: dict = Depends(require_auth),
):
    """Soft-delete a contract and its documents (RF-53)."""
    service = ContractService()
    try:
        service.delete_contract(current_user, contract_id)
    except ContractNotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.message) from exc
    except ContractAccessError as exc:
        raise HTTPException(status_code=403, detail=exc.message) from exc


@router.post(
    "/{contract_id}/documents",
    response_model=ContractDocumentResponse,
    status_code=201,
)
async def add_document(
    contract_id: str,
    file: UploadFile = File(...),
    is_signed_version: bool = Form(False),
    current_user: dict = Depends(require_client),
):
    """Attach an additional document to a contract (RF-05, RF-08, RF-57)."""
    service = ContractService()
    content = await _read_upload_limited(file)

    try:
        validated = service.validate_upload(
            file_name=file.filename or "",
            content=content,
            content_type=file.content_type,
        )
        document = service.add_document(
            current_user=current_user,
            contract_id=contract_id,
            validated_document=validated,
            is_signed_version=is_signed_version,
        )
    except DocumentValidationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    except ContractNotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.message) from exc
    except ContractAccessError as exc:
        raise HTTPException(status_code=403, detail=exc.message) from exc

    return _document_to_response(document)


@router.post(
    "/{contract_id}/analyses",
    response_model=AnalysisDetailResponse,
    status_code=201,
)
async def start_contract_analysis(
    contract_id: str,
    body: AnalysisStartRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(require_auth),
):
    """Run contract analysis pipeline for a specific perspective (RF-52, RF-09)."""
    settings = get_settings()
    service = AnalysisService()
    try:
        analysis = service.start_analysis(
            current_user,
            contract_id,
            body.perspective,
            document_scope=body.document_scope,
            run_async=settings.analysis_async,
        )
        if settings.analysis_async and analysis.status == "processing":
            background_tasks.add_task(service.run_pipeline_for_analysis, analysis.id)
        return _detail_to_response(analysis)
    except ContractNotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.message) from exc
    except ContractAccessError as exc:
        raise HTTPException(status_code=403, detail=exc.message) from exc
    except AnalysisPipelineError as exc:
        message = exc.args[0] if exc.args else str(exc)
        status_code = 409 if "already exists" in message.lower() else 422
        raise HTTPException(status_code=status_code, detail=message) from exc

    return _detail_to_response(analysis)


@router.get(
    "/{contract_id}/analyses",
    response_model=List[AnalysisSummaryResponse],
)
async def list_contract_analyses(
    contract_id: str,
    current_user: dict = Depends(require_auth),
):
    """List analyses for a contract (RF-52)."""
    service = AnalysisService()
    try:
        analyses = service.list_analyses(current_user, contract_id)
    except ContractNotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.message) from exc
    except ContractAccessError as exc:
        raise HTTPException(status_code=403, detail=exc.message) from exc

    return [_summary_to_response(item) for item in analyses]


@router.post(
    "/{contract_id}/revision-comparison",
    response_model=ComparisonResponse,
    status_code=201,
)
async def create_revision_comparison(
    contract_id: str,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(require_auth),
):
    """Analyze edited revision if needed and compare it against the original contract."""
    settings = get_settings()
    contract_service = ContractService()
    analysis_service = AnalysisService()
    comparison_service = ComparisonService()

    try:
        contract = contract_service.get_contract(current_user, contract_id)
    except ContractNotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.message) from exc
    except ContractAccessError as exc:
        raise HTTPException(status_code=403, detail=exc.message) from exc

    try:
        comparison, changes, rows = comparison_service.compare_edited_revision(
            current_user,
            contract_id,
        )
        return _comparison_to_response(comparison, changes, rows)
    except ComparisonError as exc:
        message = exc.message.lower()
        if "versión editada" not in message and "edited" not in message:
            raise HTTPException(status_code=422, detail=exc.message) from exc

    try:
        analysis = analysis_service.start_analysis(
            current_user,
            contract_id,
            contract.perspective,
            document_scope="lawyer_revision",
            run_async=settings.analysis_async,
        )
        if settings.analysis_async and analysis.status == "processing":
            background_tasks.add_task(analysis_service.run_pipeline_for_analysis, analysis.id)
            raise HTTPException(
                status_code=202,
                detail="El análisis de la versión editada está en proceso. Intente la comparación de nuevo en unos momentos.",
            )
    except AnalysisPipelineError as exc:
        detail = exc.args[0] if exc.args else str(exc)
        if "already exists" in detail.lower():
            pass
        else:
            raise HTTPException(status_code=422, detail=detail) from exc
    except ContractAccessError as exc:
        raise HTTPException(status_code=403, detail=exc.message) from exc

    try:
        comparison, changes, rows = comparison_service.compare_edited_revision(
            current_user,
            contract_id,
        )
    except ComparisonError as exc:
        raise HTTPException(status_code=422, detail=exc.message) from exc

    return _comparison_to_response(comparison, changes, rows)


@router.get(
    "/{contract_id}/revision-comparison/latest",
    response_model=ComparisonResponse,
)
async def get_latest_revision_comparison(
    contract_id: str,
    current_user: dict = Depends(require_auth),
):
    """Return the latest original-vs-edited comparison for a contract."""
    comparison_service = ComparisonService()
    try:
        result = comparison_service.get_latest_revision_comparison(current_user, contract_id)
    except ContractNotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.message) from exc
    except ContractAccessError as exc:
        raise HTTPException(status_code=403, detail=exc.message) from exc

    if result is None:
        raise HTTPException(status_code=404, detail="No revision comparison found for this contract.")
    comparison, changes, rows = result
    return _comparison_to_response(comparison, changes, rows)


@router.get(
    "/{contract_id}/documents",
    response_model=List[ContractDocumentResponse],
)
async def list_documents(
    contract_id: str,
    current_user: dict = Depends(require_auth),
):
    """List documents associated with a contract."""
    service = ContractService()
    try:
        documents = service.list_documents(current_user, contract_id)
    except ContractNotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.message) from exc
    except ContractAccessError as exc:
        raise HTTPException(status_code=403, detail=exc.message) from exc

    return [_document_to_response(doc) for doc in documents]


async def _resolve_download_user(request: Request, contract_id: str, document_id: str, token: str | None) -> dict:
    if token:
        user_id = DownloadTokenService().verify(
            token,
            contract_id=contract_id,
            document_id=document_id,
        )
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid or expired download token.")
        return {"user_id": user_id, "email": "", "role": None}

    from api.middleware.auth import RoleChecker

    checker = RoleChecker()
    return await checker(request)


@router.post(
    "/{contract_id}/documents/{document_id}/download-token",
    response_model=DownloadTokenResponse,
)
async def create_download_token(
    contract_id: str,
    document_id: str,
    current_user: dict = Depends(require_auth),
):
    """Issue a short-lived token for document download (RNF-21)."""
    service = ContractService()
    try:
        service.get_document_content(current_user, contract_id, document_id)
    except ContractNotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.message) from exc
    except DocumentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.message) from exc
    except ContractAccessError as exc:
        raise HTTPException(status_code=403, detail=exc.message) from exc

    token_service = DownloadTokenService()
    token, expires_at = token_service.create(
        user_id=current_user["user_id"],
        contract_id=contract_id,
        document_id=document_id,
    )
    download_path = f"/contracts/{contract_id}/documents/{document_id}/download?token={token}"
    return DownloadTokenResponse(token=token, expires_at=expires_at, download_path=download_path)


@router.get("/{contract_id}/documents/{document_id}/download")
async def download_document(
    request: Request,
    contract_id: str,
    document_id: str,
    token: str | None = Query(default=None),
):
    """Download a stored document from the database."""
    current_user = await _resolve_download_user(request, contract_id, document_id, token)
    service = ContractService()
    try:
        file_name, mime_type, content = service.get_document_content(
            current_user,
            contract_id,
            document_id,
        )
    except ContractNotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.message) from exc
    except DocumentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.message) from exc
    except ContractAccessError as exc:
        raise HTTPException(status_code=403, detail=exc.message) from exc

    return Response(
        content=content,
        media_type=mime_type,
        headers={"Content-Disposition": f'attachment; filename="{file_name}"'},
    )


@router.get(
    "/{contract_id}/documents/{document_id}/text",
    response_model=DocumentTextResponse,
)
async def get_document_text(
    contract_id: str,
    document_id: str,
    current_user: dict = Depends(require_auth),
):
    """Return persisted extracted text for a document (RF-06)."""
    service = ContractService()
    try:
        text, extraction_method, page_count = service.get_document_text(
            current_user,
            contract_id,
            document_id,
        )
    except ContractNotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.message) from exc
    except DocumentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.message) from exc
    except ContractAccessError as exc:
        raise HTTPException(status_code=403, detail=exc.message) from exc

    return DocumentTextResponse(
        document_id=document_id,
        text=text,
        extraction_method=extraction_method,
        page_count=page_count,
        character_count=len(text),
    )


@router.post(
    "/{contract_id}/lawyer-revision",
    response_model=ContractDocumentResponse,
    status_code=201,
)
async def upload_lawyer_revision(
    contract_id: str,
    file: UploadFile = File(...),
    current_user: dict = Depends(require_lawyer),
):
    """Upload a lawyer-edited contract file, replacing any previous revision."""
    service = ContractService()
    content = await _read_upload_limited(file)

    try:
        validated = service.validate_upload(
            file_name=file.filename or "",
            content=content,
            content_type=file.content_type,
        )
        document = service.upload_lawyer_revision(
            current_user=current_user,
            contract_id=contract_id,
            validated_document=validated,
        )
    except DocumentValidationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    except ContractNotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.message) from exc
    except ContractAccessError as exc:
        raise HTTPException(status_code=403, detail=exc.message) from exc

    return _document_to_response(document)
