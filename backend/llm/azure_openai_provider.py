"""Azure OpenAI provider (RF-66)."""

from __future__ import annotations

import json
import logging
import time

from openai import AzureOpenAI

from config.settings import Settings, get_settings
from llm.base import AnalysisPipelineResult, LLMProvider
from llm.findings_utils import aggregate_general_risk, compute_sort_orders
from llm.openai_provider import _post_process_openai_payload
from llm.prompts import CONTRACT_ANALYSIS_PROMPT_ID, build_analysis_system_prompt

logger = logging.getLogger(__name__)


class AzureOpenAILLMProvider(LLMProvider):
    provider_name = "azure_openai"
    prompt_id = CONTRACT_ANALYSIS_PROMPT_ID

    def __init__(self, settings: Settings | None = None):
        self._settings = settings or get_settings()

    @property
    def model_name(self) -> str:
        return self._settings.azure_openai_deployment

    def analyze_contract(
        self,
        contract_text: str,
        perspective: str,
        title: str | None = None,
    ) -> AnalysisPipelineResult:
        client = AzureOpenAI(
            api_key=self._settings.azure_openai_api_key,
            api_version=self._settings.azure_openai_api_version,
            azure_endpoint=self._settings.azure_openai_endpoint,
        )
        trimmed = contract_text[:120000]
        user_prompt = (
            f"Contract title: {title or 'Untitled'}\n"
            f"Analysis perspective: {perspective}\n\n"
            f"Contract text:\n{trimmed}"
        )
        started = time.perf_counter()
        try:
            response = client.chat.completions.create(
                model=self.model_name,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": build_analysis_system_prompt()},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.1,
            )
        except Exception as exc:
            logger.exception("Azure OpenAI analysis failed")
            raise RuntimeError(f"Azure OpenAI analysis failed: {exc}") from exc

        duration_ms = int((time.perf_counter() - started) * 1000)
        content = response.choices[0].message.content or "{}"
        payload = _post_process_openai_payload(json.loads(content), perspective, trimmed)
        usage = response.usage
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
            tokens_input=usage.prompt_tokens if usage else None,
            tokens_output=usage.completion_tokens if usage else None,
            duration_ms=duration_ms,
            prompt_id=self.prompt_id,
            raw_response=content,
        )
