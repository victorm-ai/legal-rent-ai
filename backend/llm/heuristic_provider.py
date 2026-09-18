"""Heuristic contract analyzer when no LLM API key is configured."""

from __future__ import annotations

import json
import re
import time
from typing import Any

from config.settings import get_settings
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
from llm.clause_taxonomy import CATEGORY_KEYWORDS
from llm.contract_rules import apply_contract_rules
from llm.field_extraction import extract_fields_from_text, supplement_fields_from_clauses
from llm.findings_utils import aggregate_general_risk, apply_evidence_guardrails, compute_sort_orders
from llm.page_tracking import resolve_page_from_offset
from llm.party_extraction import detect_missing_parties
from llm.base import AnalysisPipelineResult, LLMProvider
from llm.prompts import CONTRACT_ANALYSIS_PROMPT_ID

HEURISTIC_RULES_VERSION = "heuristic-rules-v3"

CLAUSE_HEADER = re.compile(
    r"(?=(?:CL[ÁA]USULA|Cl[áa]usula)\s+\S+[\.\:\-\s])",
    re.IGNORECASE,
)


class HeuristicLLMProvider(LLMProvider):
    """Rule-based analyzer for demos and tests without external LLM calls."""

    provider_name = "heuristic"
    model_name = HEURISTIC_RULES_VERSION
    prompt_id = CONTRACT_ANALYSIS_PROMPT_ID

    def analyze_contract(
        self,
        contract_text: str,
        perspective: str,
        title: str | None = None,
    ) -> AnalysisPipelineResult:
        started = time.perf_counter()
        normalized = contract_text.strip()
        clauses = self._extract_clauses(normalized)
        fields = supplement_fields_from_clauses(
            extract_fields_from_text(normalized),
            clauses,
        )
        fields = enrich_extracted_fields(fields, normalized)
        findings = self._generate_findings(fields, clauses, perspective, normalized)
        findings = apply_evidence_guardrails(dedupe_findings(compute_sort_orders(findings)))
        general_risk = aggregate_general_risk(findings, self._estimate_risk(fields, clauses, perspective))
        summary = self._build_summary(fields, clauses, findings, perspective, general_risk, title)
        duration_ms = int((time.perf_counter() - started) * 1000)
        return AnalysisPipelineResult(
            extracted_fields=fields,
            clauses=clauses,
            findings=findings,
            summary_executive=summary,
            general_risk=general_risk,
            provider=self.provider_name,
            model=self.model_name,
            duration_ms=duration_ms,
            prompt_id=self.prompt_id,
            raw_response=json.dumps(
                {
                    "extracted_fields": fields,
                    "clauses": clauses,
                    "findings": findings,
                    "summary_executive": summary,
                    "general_risk": general_risk,
                    "rules_version": HEURISTIC_RULES_VERSION,
                },
                ensure_ascii=False,
            ),
        )

    def _extract_fields(self, text: str) -> list[dict[str, Any]]:
        """Backward-compatible wrapper for RF-14 field extraction."""
        return extract_fields_from_text(text)

    def _extract_clauses(self, text: str) -> list[dict[str, Any]]:
        parts = CLAUSE_HEADER.split(text)
        clauses: list[dict[str, Any]] = []
        if len(parts) <= 1:
            paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if len(p.strip()) > 80]
            for index, paragraph in enumerate(paragraphs[:12], start=1):
                clauses.append(
                    {
                        "category": self._classify_clause(paragraph),
                        "text": paragraph[:2000],
                        "section": f"Section {index}",
                        "page": None,
                        "confidence": 0.65,
                    }
                )
            return clauses

        for part in parts:
            cleaned = part.strip()
            if len(cleaned) < 40:
                continue
            header_match = re.match(
                r"((?:CL[ÁA]USULA|Cl[áa]usula)\s+\S+[\.\:\-\s]*)",
                cleaned,
                re.IGNORECASE,
            )
            section = header_match.group(1).strip() if header_match else None
            offset = text.find(cleaned[:40]) if cleaned else -1
            page = resolve_page_from_offset(text, offset) if offset >= 0 else None
            clauses.append(
                {
                    "category": self._classify_clause(cleaned),
                    "text": cleaned[:2500],
                    "section": section,
                    "page": page,
                    "confidence": 0.78,
                }
            )
        return clauses[:30]

    @staticmethod
    def _classify_clause(text: str) -> str:
        lowered = text.lower()
        for category, keywords in CATEGORY_KEYWORDS.items():
            if any(keyword in lowered for keyword in keywords):
                return category
        return "other"

    @staticmethod
    def _estimate_risk(
        fields: list[dict[str, Any]],
        clauses: list[dict[str, Any]],
        perspective: str,
    ) -> str:
        values = {item["field_name"]: item["field_value"] for item in fields}
        rent = HeuristicLLMProvider._parse_amount(values.get("renta_mensual", ""))
        deposit = HeuristicLLMProvider._parse_amount(values.get("deposito", ""))
        if rent and deposit and deposit > rent * 2:
            return "high"
        penalty_clauses = [c for c in clauses if c["category"] == "penalties"]
        if len(penalty_clauses) >= 2:
            return "high"
        if not values.get("jurisdiccion"):
            return "medium"
        return "medium" if perspective != "neutral" else "low"

    def _generate_findings(
        self,
        fields: list[dict[str, Any]],
        clauses: list[dict[str, Any]],
        perspective: str,
        contract_text: str = "",
    ) -> list[dict[str, Any]]:
        findings: list[dict[str, Any]] = []
        values = {item["field_name"]: item["field_value"] for item in fields}

        lease_type = get_settings().lease_type
        findings.extend(detect_missing_clauses(clauses, lease_type=lease_type))
        findings.extend(detect_missing_parties(fields))
        findings.extend(detect_jurisdiction_issues(fields, clauses, contract_text=contract_text))
        findings.extend(detect_amount_inconsistencies(fields, clauses, self._parse_amount))
        findings.extend(detect_date_inconsistencies(fields, parse_date_value))
        findings.extend(detect_contradictions(clauses))
        findings.extend(consolidate_obligations(clauses, perspective))
        findings = apply_contract_rules(fields, clauses, perspective, findings, self._parse_amount)

        penalty_indices = [
            index for index, clause in enumerate(clauses) if clause["category"] == "penalties"
        ]
        if len(penalty_indices) >= 2 and perspective == "tenant":
            findings.append(
                {
                    "finding_type": "unfavorable_clause",
                    "severity": "high",
                    "confidence": 0.81,
                    "title": "Multiple penalty clauses detected",
                    "description": "The contract contains multiple penalty provisions that may compound tenant exposure.",
                    "recommendation": "Review cumulative penalties and negotiate caps or mutual remedies.",
                    "evidence_text": clauses[penalty_indices[0]]["text"][:500],
                    "clause_index": penalty_indices[0],
                }
            )

        return findings[:20]

    @staticmethod
    def _parse_amount(raw: str) -> float | None:
        if not raw:
            return None
        digits = re.sub(r"[^\d.]", "", raw.replace(",", ""))
        try:
            return float(digits) if digits else None
        except ValueError:
            return None

    @staticmethod
    def _build_summary(
        fields: list[dict[str, Any]],
        clauses: list[dict[str, Any]],
        findings: list[dict[str, Any]],
        perspective: str,
        general_risk: str,
        title: str | None,
    ) -> str:
        values = {item["field_name"]: item["field_value"] for item in fields}
        label = title or "Lease contract"
        perspective_label = {"landlord": "landlord", "tenant": "tenant", "neutral": "neutral"}.get(
            perspective, perspective
        )
        lines = [
            f"Executive summary — {label}",
            f"Analysis perspective: {perspective_label}. Overall risk: {general_risk.upper()}.",
        ]
        if values.get("arrendador"):
            lines.append(f"Landlord: {values['arrendador']}.")
        if values.get("arrendatario"):
            lines.append(f"Tenant: {values['arrendatario']}.")
        if values.get("inmueble_direccion"):
            lines.append(f"Property: {values['inmueble_direccion']}.")
        if values.get("renta_mensual"):
            lines.append(f"Monthly rent: {values['renta_mensual']}.")
        if values.get("deposito"):
            lines.append(f"Security deposit: {values['deposito']}.")
        if values.get("jurisdiccion"):
            lines.append(f"Jurisdiction detected: {values['jurisdiccion']}.")
        lines.append(f"{len(clauses)} clauses identified for review.")
        if findings:
            top = [item["title"] for item in findings[:3]]
            lines.append("Priority findings: " + "; ".join(top) + ".")
        lines.append(
            "This summary was generated automatically and requires professional legal review."
        )
        return " ".join(lines)
