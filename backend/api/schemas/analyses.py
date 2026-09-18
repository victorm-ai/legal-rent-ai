"""Analysis API schemas."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AnalysisStartRequest(BaseModel):
    perspective: str = Field(..., description="Analysis perspective: tenant (Arrendatario)")
    document_scope: str = Field(
        default="original",
        description="Document bundle to analyze: original or lawyer_revision",
    )


class SourceReferenceResponse(BaseModel):
    page: Optional[int] = None
    clause: Optional[str] = None
    section: Optional[str] = None
    text_snippet: Optional[str] = None


class ExtractedFieldResponse(BaseModel):
    value: str
    confidence: float
    requires_review: bool = False
    source: Optional[SourceReferenceResponse] = None


class LegalCitationResponse(BaseModel):
    id: str
    law_code: str
    article: Optional[str] = None
    excerpt: Optional[str] = None
    source_uri: Optional[str] = None


class FindingResponse(BaseModel):
    id: str
    finding_type: str
    severity: str
    title: str
    description: str
    sort_order: int = 0
    clause_id: Optional[str] = None
    legal_basis: Optional[str] = None
    source_law: Optional[str] = None
    evidence_text: Optional[str] = None
    evidence_page: Optional[int] = None
    recommendation: Optional[str] = None
    suggested_rewording: Optional[str] = None
    confidence: Optional[float] = None
    legal_citations: List[LegalCitationResponse] = Field(default_factory=list)
    review: Optional["FindingReviewResponse"] = None


class FindingReviewResponse(BaseModel):
    id: str
    verdict: str
    notes: Optional[str] = None
    lawyer_id: str
    created_at: datetime


class AnalysisStatusUpdateRequest(BaseModel):
    status: str = Field(..., description="Target analysis status")


class FindingReviewRequest(BaseModel):
    verdict: str = Field(..., description="correct, incorrect, or not_relevant")
    notes: Optional[str] = None


class AnalysisApprovalRequest(BaseModel):
    notes: Optional[str] = None


class AnalysisApprovalResponse(BaseModel):
    id: str
    analysis_id: str
    lawyer_id: str
    approved_at: datetime
    notes: Optional[str] = None


class ClauseResponse(BaseModel):
    id: str
    category: str
    text: str
    section: Optional[str] = None
    page: Optional[int] = None
    confidence: float


class AnalysisSummaryResponse(BaseModel):
    id: str
    contract_id: str
    perspective: str
    document_scope: str = "original"
    status: str
    summary_executive: Optional[str] = None
    general_risk: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime


class AnalysisStatusResponse(BaseModel):
    id: str
    contract_id: str
    perspective: str
    document_scope: str = "original"
    status: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class AnalysisDetailResponse(BaseModel):
    id: str
    contract_id: str
    perspective: str
    document_scope: str = "original"
    status: str
    summary_executive: Optional[str] = None
    general_risk: Optional[str] = None
    extracted_data: Dict[str, ExtractedFieldResponse] = Field(default_factory=dict)
    clauses: List[ClauseResponse] = Field(default_factory=list)
    findings: List[FindingResponse] = Field(default_factory=list)
    llm_metadata: Dict[str, Any] = Field(default_factory=dict)
    approval: Optional[AnalysisApprovalResponse] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
