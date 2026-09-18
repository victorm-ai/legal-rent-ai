"""Analysis DTOs (RF-52, RF-13, RF-18, RF-37)."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class SourceReferenceDTO:
    page: Optional[int] = None
    clause: Optional[str] = None
    section: Optional[str] = None
    text_snippet: Optional[str] = None


@dataclass
class ExtractedFieldDTO:
    field_name: str
    field_value: str
    confidence: float
    source_page: Optional[int] = None
    source_clause: Optional[str] = None
    source_section: Optional[str] = None
    source_text_snippet: Optional[str] = None

    @property
    def requires_review(self) -> bool:
        from config.settings import get_settings

        return self.confidence < get_settings().confidence_review_threshold


@dataclass
class LegalCitationDTO:
    id: str
    law_code: str
    article: Optional[str] = None
    excerpt: Optional[str] = None
    source_uri: Optional[str] = None


@dataclass
class FindingDTO:
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
    legal_citations: List[LegalCitationDTO] = field(default_factory=list)
    analysis_id: Optional[str] = None


@dataclass
class ClauseDTO:
    id: str
    category: str
    text: str
    confidence: float
    section: Optional[str] = None
    page: Optional[int] = None


@dataclass
class AnalysisDTO:
    id: str
    contract_id: str
    perspective: str
    document_scope: str
    status: str
    summary_executive: Optional[str]
    general_risk: Optional[str]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime
    extracted_fields: List[ExtractedFieldDTO] = field(default_factory=list)
    clauses: List[ClauseDTO] = field(default_factory=list)
    findings: List[FindingDTO] = field(default_factory=list)
    llm_metadata: Dict[str, Any] = field(default_factory=dict)
    finding_reviews: Dict[str, Any] = field(default_factory=dict)
    approval: Any = None
