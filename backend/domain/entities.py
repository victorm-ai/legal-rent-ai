"""
Domain entities for the contract analyzer.
"""

from enum import Enum
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass


class RiskLevel(str, Enum):
    """Contractual risk levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class AnalysisStatus(str, Enum):
    """Contract analysis lifecycle states."""
    GENERATED_BY_AI = "ai_generated"
    PENDING_REVIEW = "pending_review"
    REVIEWED = "reviewed"
    APPROVED = "approved"


class ContractStatus(str, Enum):
    """Contract lifecycle states."""
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    IN_SIGNING = "in_signing"
    SIGNED = "signed"
    EXPIRED = "expired"
    TERMINATED = "terminated"


class Role(str, Enum):
    """User roles."""
    LAWYER = "lawyer"
    CLIENT = "client"


@dataclass
class User:
    """System user."""
    id: str
    email: str
    name: str
    role: Role


@dataclass
class Party:
    """Party in a contract (landlord, tenant, etc.)."""
    id: Optional[str] = None
    type: Optional[str] = None
    name: Optional[str] = None
    legal_representative: Optional[str] = None
    address: Optional[str] = None


@dataclass
class Contract:
    """Primary entity: lease contract."""
    id: str
    user_id: str
    perspective: str
    jurisdiccion: Optional[str] = None

    status: ContractStatus = ContractStatus.DRAFT

    file_name: Optional[str] = None
    file_size_bytes: Optional[int] = None
    page_count: Optional[int] = None
    document_type: Optional[str] = None

    parts: List[Party] = None  # type: ignore

    created_at: datetime = None  # type: ignore
    updated_at: datetime = None  # type: ignore

    def __post_init__(self):
        if self.parts is None:
            self.parts = []


@dataclass
class Clause:
    """Clause identified in the contract."""
    id: str
    contract_id: str
    category: str
    text: str
    section: Optional[str] = None
    page: Optional[int] = None
    confidence: float = 0.0


@dataclass
class Finding:
    """Finding from contract analysis."""
    id: str
    contract_id: str
    finding_type: str
    severity: RiskLevel
    title: str
    description: str

    clause_id: Optional[str] = None
    legal_basis: Optional[str] = None
    source_law: Optional[str] = None
    evidence_text: Optional[str] = None
    evidence_page: Optional[int] = None
    recommendation: Optional[str] = None
    suggested_rewording: Optional[str] = None


@dataclass
class AnalysisResult:
    """Complete result of a contract analysis."""
    id: str
    contract_id: str

    summary_executive: str
    general_risk: RiskLevel

    extracted_data: Dict[str, Any]
    clauses_analyzed: List[Clause]
    findings: List[Finding]

    analysis_status: AnalysisStatus = AnalysisStatus.GENERATED_BY_AI
    llm_model: Optional[str] = None
    llm_provider: Optional[str] = None

    created_at: datetime = None  # type: ignore
