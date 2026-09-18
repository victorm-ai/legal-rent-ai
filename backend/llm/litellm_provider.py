"""Contract analysis via LiteLLM (OpenAI, Anthropic)."""

from __future__ import annotations

import json
import logging
import time

from config.settings import Settings, get_settings
from llm.base import AnalysisPipelineResult, LLMProvider
from llm.findings_utils import aggregate_general_risk, compute_sort_orders
from llm.litellm_runtime import litellm_completion, resolve_litellm_model
from llm.openai_provider import _post_process_openai_payload
from llm.prompts import CONTRACT_ANALYSIS_PROMPT_ID, build_analysis_system_prompt

logger = logging.getLogger(__name__)


class LiteLLMLLMProvider(LLMProvider):
    """Structured contract analysis using LiteLLM."""

    prompt_id = CONTRACT_ANALYSIS_PROMPT_ID

    def __init__(self, settings: Settings | None = None, provider: str | None = None):
        self._settings = settings or get_settings()
        self.provider_name = (provider or self._settings.llm_provider).strip().lower()

    @property
    def model_name(self) -> str:
        return resolve_litellm_model(self._settings, self.provider_name)

    def analyze_contract(
        self,
        contract_text: str,
        perspective: str,
        title: str | None = None,
    ) -> AnalysisPipelineResult:
        trimmed = contract_text[:120000]
        user_prompt = (
            f"Contract title: {title or 'Untitled'}\n"
            f"Analysis perspective: {perspective}\n\n"
            f"Contract text:\n{trimmed}"
        )
        messages = [
            {"role": "system", "content": build_analysis_system_prompt()},
            {"role": "user", "content": user_prompt},
        ]
        started = time.perf_counter()
        content, usage = litellm_completion(
            settings=self._settings,
            provider=self.provider_name,
            messages=messages,
            temperature=0.1,
            json_mode=True,
        )
        duration_ms = int((time.perf_counter() - started) * 1000)
        payload = _post_process_openai_payload(json.loads(content or "{}"), perspective, trimmed)
        findings = compute_sort_orders(payload.get("findings", []))
        general_risk = aggregate_general_risk(findings, payload.get("general_risk", "medium"))
        return AnalysisPipelineResult(
            extracted_fields=payload.get("extracted_fields", []),
            clauses=payload.get("clauses", []),
            findings=findings,
            summary_executive=payload.get("summary_executive", ""),
            general_risk=general_risk,
            provider=self.provider_name,
            model=self.model_name,
            tokens_input=usage.get("prompt_tokens"),
            tokens_output=usage.get("completion_tokens"),
            duration_ms=duration_ms,
            prompt_id=self.prompt_id,
            raw_response=content,
        )
