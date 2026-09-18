"""
Data models and DTOs for the contract analyzer.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List


@dataclass
class SourceReference:
    """Reference to the source of an extracted field."""
    page: Optional[int] = None
    clause: Optional[str] = None
    section: Optional[str] = None
    text_snippet: Optional[str] = None


@dataclass
class ExtractedField:
    """Extracted field with confidence score and source."""
    value: Any
    confidence: float
    source: Optional[SourceReference] = None

    def requires_review(self) -> bool:
        return self.confidence < 0.8


@dataclass
class ExtractedData:
    """Structured data extracted from a contract."""
    # Parties (Spanish field names match legal domain terminology)
    arrendador: Optional[ExtractedField] = None
    arrendatario: Optional[ExtractedField] = None
    fiador: Optional[ExtractedField] = None
    obligado_solidario: Optional[ExtractedField] = None

    # Property
    inmueble_direccion: Optional[ExtractedField] = None
    inmueble_uso: Optional[ExtractedField] = None
    inmueble_superficie: Optional[ExtractedField] = None

    # Economic terms
    renta_mensual: Optional[ExtractedField] = None
    deposito: Optional[ExtractedField] = None
    garantia: Optional[ExtractedField] = None

    # Dates and duration
    fecha_inicio: Optional[ExtractedField] = None
    fecha_fin: Optional[ExtractedField] = None
    duracion_meses: Optional[ExtractedField] = None

    # Jurisdiction
    jurisdiccion: Optional[ExtractedField] = None


@dataclass
class ClauseDTO:
    """DTO for contract clauses."""
    id: str
    category: str
    text: str
    confidence: float = 0.0
    section: Optional[str] = None
    page: Optional[int] = None


@dataclass
class FindingDTO:
    """DTO for analysis findings."""
    id: str
    finding_type: str
    severity: str
    title: str
    description: str
    legal_basis: Optional[str] = None
    recommendation: Optional[str] = None


@dataclass
class AnalysisResult:
    """Analysis result DTO."""
    contract_id: str
    summary_executive: str
    general_risk: str
    extracted_data: Dict[str, Any]
    clauses_analyzed: List[ClauseDTO]
    findings: List[FindingDTO]
    llm_metadata: Dict[str, Any] = field(default_factory=dict)
