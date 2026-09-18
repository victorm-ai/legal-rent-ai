"""LLM provider wrapper that enforces guardrails before analysis."""

from __future__ import annotations

from guardrails.gateway import GuardrailsGateway, get_guardrails_gateway
from llm.base import AnalysisPipelineResult, LLMProvider


class GuardedLLMProvider(LLMProvider):
    """Decorates an LLM provider: services → guardrails → inner LLM."""

    def __init__(
        self,
        inner: LLMProvider,
        gateway: GuardrailsGateway | None = None,
    ):
        self._inner = inner
        self._gateway = gateway or get_guardrails_gateway()

    @property
    def provider_name(self) -> str:
        return getattr(self._inner, "provider_name", "unknown")

    @property
    def model_name(self) -> str:
        return getattr(self._inner, "model_name", "unknown")

    @property
    def prompt_id(self) -> str | None:
        return getattr(self._inner, "prompt_id", None)

    def analyze_contract(
        self,
        contract_text: str,
        perspective: str,
        title: str | None = None,
    ) -> AnalysisPipelineResult:
        self._gateway.validate_analysis_input(contract_text, title)
        return self._inner.analyze_contract(
            contract_text=contract_text,
            perspective=perspective,
            title=title,
        )
