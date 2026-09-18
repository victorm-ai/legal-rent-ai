"""Analysis routes (RF-52, RF-13, RF-10, RF-18, RF-37)."""

from typing import List

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from api.middleware.auth import require_auth, require_lawyer
from api.schemas.analyses import (
    AnalysisApprovalRequest,
    AnalysisApprovalResponse,
    AnalysisDetailResponse,
    AnalysisStatusResponse,
    AnalysisStatusUpdateRequest,
    AnalysisSummaryResponse,
    ClauseResponse,
    ExtractedFieldResponse,
    FindingResponse,
    FindingReviewRequest,
    FindingReviewResponse,
    LegalCitationResponse,
    SourceReferenceResponse,
)
from data.analysis_dto import AnalysisDTO
from domain.analysis_status import InvalidAnalysisStatusTransitionError
from services.analysis_service import (
    AnalysisNotFoundError,
    AnalysisPipelineError,
    AnalysisReviewError,
    AnalysisService,
)
from services.contract_service import ContractAccessError, ContractNotFoundError

router = APIRouter(tags=["analyses"])


def _field_to_response(field) -> ExtractedFieldResponse:
    source = None
    if any([field.source_page, field.source_clause, field.source_section, field.source_text_snippet]):
        source = SourceReferenceResponse(
            page=field.source_page,
            clause=field.source_clause,
            section=field.source_section,
            text_snippet=field.source_text_snippet,
        )
    return ExtractedFieldResponse(
        value=field.field_value,
        confidence=field.confidence,
        requires_review=field.requires_review,
        source=source,
    )


def _summary_to_response(analysis: AnalysisDTO) -> AnalysisSummaryResponse:
    return AnalysisSummaryResponse(
        id=analysis.id,
        contract_id=analysis.contract_id,
        perspective=analysis.perspective,
        document_scope=analysis.document_scope,
        status=analysis.status,
        summary_executive=analysis.summary_executive,
        general_risk=analysis.general_risk,
        started_at=analysis.started_at,
        completed_at=analysis.completed_at,
        created_at=analysis.created_at,
    )


def _finding_to_response(finding, review=None) -> FindingResponse:
    review_response = None
    if review is not None:
        review_response = FindingReviewResponse(
            id=review.id,
            verdict=review.verdict,
            notes=review.notes,
            lawyer_id=review.lawyer_id,
            created_at=review.created_at,
        )
    return FindingResponse(
        id=finding.id,
        finding_type=finding.finding_type,
        severity=finding.severity,
        title=finding.title,
        description=finding.description,
        sort_order=finding.sort_order,
        clause_id=finding.clause_id,
        legal_basis=finding.legal_basis,
        source_law=finding.source_law,
        evidence_text=finding.evidence_text,
        evidence_page=finding.evidence_page,
        recommendation=finding.recommendation,
        suggested_rewording=finding.suggested_rewording,
        confidence=finding.confidence,
        legal_citations=[
            LegalCitationResponse(
                id=citation.id,
                law_code=citation.law_code,
                article=citation.article,
                excerpt=citation.excerpt,
                source_uri=citation.source_uri,
            )
            for citation in finding.legal_citations
        ],
        review=review_response,
    )


def _detail_to_response(analysis: AnalysisDTO) -> AnalysisDetailResponse:
    extracted_data = {
        field.field_name: _field_to_response(field)
        for field in analysis.extracted_fields
    }
    clauses = [
        ClauseResponse(
            id=clause.id,
            category=clause.category,
            text=clause.text,
            section=clause.section,
            page=clause.page,
            confidence=clause.confidence,
        )
        for clause in analysis.clauses
    ]
    findings = [
        _finding_to_response(finding, analysis.finding_reviews.get(finding.id))
        for finding in analysis.findings
    ]
    approval = None
    if analysis.approval is not None:
        approval = AnalysisApprovalResponse(
            id=analysis.approval.id,
            analysis_id=analysis.approval.analysis_id,
            lawyer_id=analysis.approval.lawyer_id,
            approved_at=analysis.approval.approved_at,
            notes=analysis.approval.notes,
        )
    return AnalysisDetailResponse(
        id=analysis.id,
        contract_id=analysis.contract_id,
        perspective=analysis.perspective,
        document_scope=analysis.document_scope,
        status=analysis.status,
        summary_executive=analysis.summary_executive,
        general_risk=analysis.general_risk,
        extracted_data=extracted_data,
        clauses=clauses,
        findings=findings,
        llm_metadata=analysis.llm_metadata,
        approval=approval,
        started_at=analysis.started_at,
        completed_at=analysis.completed_at,
        created_at=analysis.created_at,
    )


@router.get("/analyses/{analysis_id}", response_model=AnalysisDetailResponse)
async def get_analysis(
    analysis_id: str,
    current_user: dict = Depends(require_auth),
):
    """Return full analysis results (RF-37)."""
    service = AnalysisService()
    try:
        analysis = service.get_analysis(current_user, analysis_id)
    except AnalysisNotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.message) from exc
    except ContractNotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.message) from exc
    except ContractAccessError as exc:
        raise HTTPException(status_code=403, detail=exc.message) from exc

    return _detail_to_response(analysis)


@router.get("/analyses/{analysis_id}/status", response_model=AnalysisStatusResponse)
async def get_analysis_status(
    analysis_id: str,
    current_user: dict = Depends(require_auth),
):
    """Return analysis pipeline status for polling."""
    service = AnalysisService()
    try:
        analysis = service.get_analysis_status(current_user, analysis_id)
    except AnalysisNotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.message) from exc
    except ContractNotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.message) from exc
    except ContractAccessError as exc:
        raise HTTPException(status_code=403, detail=exc.message) from exc

    return AnalysisStatusResponse(
        id=analysis.id,
        contract_id=analysis.contract_id,
        perspective=analysis.perspective,
        document_scope=analysis.document_scope,
        status=analysis.status,
        started_at=analysis.started_at,
        completed_at=analysis.completed_at,
    )


@router.patch("/analyses/{analysis_id}/status", response_model=AnalysisSummaryResponse)
async def update_analysis_status(
    analysis_id: str,
    body: AnalysisStatusUpdateRequest,
    current_user: dict = Depends(require_auth),
):
    """Change analysis review workflow status (RF-58)."""
    service = AnalysisService()
    try:
        analysis = service.update_analysis_status(current_user, analysis_id, body.status)
    except AnalysisNotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.message) from exc
    except ContractNotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.message) from exc
    except ContractAccessError as exc:
        raise HTTPException(status_code=403, detail=exc.message) from exc
    except InvalidAnalysisStatusTransitionError as exc:
        raise HTTPException(status_code=409, detail=exc.message) from exc

    return _summary_to_response(analysis)


@router.post(
    "/analyses/{analysis_id}/findings/{finding_id}/review",
    response_model=FindingReviewResponse,
)
async def review_finding(
    analysis_id: str,
    finding_id: str,
    body: FindingReviewRequest,
    current_user: dict = Depends(require_lawyer),
):
    """Mark a finding as correct, incorrect, or not relevant (RF-68)."""
    service = AnalysisService()
    try:
        review = service.review_finding(
            current_user,
            analysis_id,
            finding_id,
            body.verdict,
            body.notes,
        )
    except AnalysisNotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.message) from exc
    except ContractNotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.message) from exc
    except ContractAccessError as exc:
        raise HTTPException(status_code=403, detail=exc.message) from exc
    except AnalysisReviewError as exc:
        raise HTTPException(status_code=409, detail=exc.message) from exc

    return FindingReviewResponse(
        id=review.id,
        verdict=review.verdict,
        notes=review.notes,
        lawyer_id=review.lawyer_id,
        created_at=review.created_at,
    )


@router.post("/analyses/{analysis_id}/approve", response_model=AnalysisApprovalResponse)
async def approve_analysis(
    analysis_id: str,
    body: AnalysisApprovalRequest,
    current_user: dict = Depends(require_lawyer),
):
    """Formally approve an analysis after lawyer review (RF-69)."""
    service = AnalysisService()
    try:
        approval = service.approve_analysis(current_user, analysis_id, body.notes)
    except AnalysisNotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.message) from exc
    except ContractNotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.message) from exc
    except ContractAccessError as exc:
        raise HTTPException(status_code=403, detail=exc.message) from exc
    except AnalysisReviewError as exc:
        raise HTTPException(status_code=409, detail=exc.message) from exc

    return AnalysisApprovalResponse(
        id=approval.id,
        analysis_id=approval.analysis_id,
        lawyer_id=approval.lawyer_id,
        approved_at=approval.approved_at,
        notes=approval.notes,
    )
