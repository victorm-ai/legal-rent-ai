"""Local / Ollama-compatible LLM provider (RF-67)."""

from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.request

from config.settings import Settings, get_settings
from llm.base import AnalysisPipelineResult, LLMProvider
from llm.findings_utils import aggregate_general_risk, compute_sort_orders
from llm.openai_provider import _post_process_openai_payload
from llm.prompts import CONTRACT_ANALYSIS_PROMPT_ID, build_analysis_system_prompt

logger = logging.getLogger(__name__)


class LocalLLMProvider(LLMProvider):
    """OpenAI-compatible local endpoint (Ollama, LM Studio, etc.)."""

    provider_name = "local"
    prompt_id = CONTRACT_ANALYSIS_PROMPT_ID

    def __init__(self, settings: Settings | None = None):
        self._settings = settings or get_settings()

    @property
    def model_name(self) -> str:
        return self._settings.local_llm_model

    def analyze_contract(
        self,
        contract_text: str,
        perspective: str,
        title: str | None = None,
    ) -> AnalysisPipelineResult:
        trimmed = contract_text[:80000]
        user_prompt = (
            f"Contract title: {title or 'Untitled'}\n"
            f"Analysis perspective: {perspective}\n\n"
            f"Contract text:\n{trimmed}"
        )
        payload_body = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": build_analysis_system_prompt()},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
        }
        url = f"{self._settings.local_llm_base_url.rstrip('/')}/v1/chat/completions"
        started = time.perf_counter()
        request = urllib.request.Request(
            url,
            data=json.dumps(payload_body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.URLError as exc:
            logger.exception("Local LLM request failed")
            raise RuntimeError(f"Local LLM analysis failed: {exc}") from exc

        duration_ms = int((time.perf_counter() - started) * 1000)
        envelope = json.loads(raw)
        content = envelope["choices"][0]["message"]["content"]
        parsed = _post_process_openai_payload(json.loads(content), perspective, trimmed)
        findings = compute_sort_orders(parsed.get("findings", []))
        general_risk = aggregate_general_risk(findings, parsed.get("general_risk", "medium"))
        usage = envelope.get("usage") or {}
        return AnalysisPipelineResult(
            extracted_fields=parsed.get("extracted_fields", []),
            clauses=parsed.get("clauses", []),
            findings=findings,
            summary_executive=parsed.get("summary_executive", ""),
            general_risk=general_risk,
            provider=self.provider_name,
            model=self.model_name,
            tokens_input=usage.get("prompt_tokens"),
            tokens_output=usage.get("completion_tokens"),
            duration_ms=duration_ms,
            prompt_id=self.prompt_id,
            raw_response=content,
        )
