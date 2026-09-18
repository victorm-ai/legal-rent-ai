"""LLM provider abstraction (RF-65, RF-66)."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AnalysisPipelineResult:
    """Structured output from the analysis pipeline."""

    extracted_fields: list[dict[str, Any]]
    clauses: list[dict[str, Any]]
    summary_executive: str
    general_risk: str
    provider: str
    model: str
    findings: list[dict[str, Any]] = field(default_factory=list)
    tokens_input: int | None = None
    tokens_output: int | None = None
    duration_ms: int | None = None
    prompt_id: str | None = None
    raw_response: str | None = None


class LLMProvider(ABC):
    """Common interface for analysis LLM backends."""

    @abstractmethod
    def analyze_contract(
        self,
        contract_text: str,
        perspective: str,
        title: str | None = None,
    ) -> AnalysisPipelineResult:
        """Run structured extraction, clause ID and summary generation."""
