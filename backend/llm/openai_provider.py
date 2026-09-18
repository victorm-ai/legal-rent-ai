"""OpenAI-backed contract analyzer (OpenAI Python SDK v3+)."""

from __future__ import annotations

import json
import logging
import time
from typing import Any

from openai import OpenAI

from config.settings import Settings, get_settings
from llm.analysis_enrichment import (
    consolidate_obligations,
    dedupe_findings,
    detect_amount_inconsistencies,
    detect_contradictions,
    detect_date_inconsistencies,
    detect_jurisdiction_issues,
    detect_missing_clauses,
    enrich_extracted_fields,
    parse_date_value,
)
from llm.field_extraction import supplement_fields_from_clauses
from llm.findings_utils import apply_evidence_guardrails
from llm.party_extraction import detect_missing_parties
from llm.base import AnalysisPipelineResult, LLMProvider
from llm.contract_rules import apply_contract_rules
from llm.findings_utils import aggregate_general_risk, compute_sort_orders
from llm.heuristic_provider import HeuristicLLMProvider
from llm.prompts import CONTRACT_ANALYSIS_PROMPT_ID, build_analysis_system_prompt

logger = logging.getLogger(__name__)


def _parse_amount(raw: str) -> float | None:
    return HeuristicLLMProvider._parse_amount(raw)


def _post_process_openai_payload(
    payload: dict[str, Any],
    perspective: str,
    contract_text: str = "",
) -> dict[str, Any]:
    """Apply enrichment and rules to OpenAI JSON output (RF-11–26, RF-63)."""
    clauses = payload.get("clauses", [])
    fields = supplement_fields_from_clauses(payload.get("extracted_fields", []), clauses)
    fields = enrich_extracted_fields(fields, contract_text)
    findings = list(payload.get("findings", []))
    for item in findings:
        if "confidence" not in item:
            item["confidence"] = 0.78

    findings.extend(detect_missing_clauses(clauses, lease_type=get_settings().lease_type))
    findings.extend(detect_missing_parties(fields))
    findings.extend(detect_jurisdiction_issues(fields, clauses, contract_text=contract_text))
    findings.extend(detect_amount_inconsistencies(fields, clauses, _parse_amount))
    findings.extend(detect_date_inconsistencies(fields, parse_date_value))
    findings.extend(detect_contradictions(clauses))
    findings.extend(consolidate_obligations(clauses, perspective))
    findings = apply_contract_rules(fields, clauses, perspective, findings, _parse_amount)
    findings = apply_evidence_guardrails(dedupe_findings(findings))

    payload["extracted_fields"] = fields
    payload["findings"] = findings[:25]
    return payload


class OpenAILLMProvider(LLMProvider):
    """OpenAI chat completion provider with JSON output."""

    provider_name = "openai"
    prompt_id = CONTRACT_ANALYSIS_PROMPT_ID

    def __init__(self, settings: Settings | None = None):
        self._settings = settings or get_settings()

    @property
    def model_name(self) -> str:
        return self._settings.openai_model

    def analyze_contract(
        self,
        contract_text: str,
        perspective: str,
        title: str | None = None,
    ) -> AnalysisPipelineResult:
        client = OpenAI(api_key=self._settings.openai_api_key)
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
            logger.exception("OpenAI analysis failed")
            raise RuntimeError(f"OpenAI analysis failed: {exc}") from exc

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


def _is_usable_openai_key(api_key: str) -> bool:
    from llm.litellm_runtime import is_usable_openai_key

    return is_usable_openai_key(api_key)


def get_llm_provider(settings: Settings | None = None) -> LLMProvider:
    """Return the configured LLM provider (RF-65–RF-67)."""
    from llm.registry import get_llm_provider as _registry_get

    return _registry_get(settings)
