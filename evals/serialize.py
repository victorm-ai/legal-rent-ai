"""Normalize analysis pipeline output for regression snapshots."""

from __future__ import annotations

from typing import Any

from llm.base import AnalysisPipelineResult
from llm.findings_utils import normalize_severity


def normalize_analysis_result(result: AnalysisPipelineResult) -> dict[str, Any]:
    fields = {
        str(item.get("field_name", "")): str(item.get("field_value", "")).strip()
        for item in result.extracted_fields
        if item.get("field_name")
    }
    findings = [
        {
            "finding_type": item.get("finding_type"),
            "severity": normalize_severity(item.get("severity")),
            "title": str(item.get("title", "")).strip(),
        }
        for item in result.findings
    ]
    findings.sort(key=lambda row: (row["finding_type"] or "", row["severity"], row["title"]))
    return {
        "prompt_id": result.prompt_id,
        "provider": result.provider,
        "model": result.model,
        "general_risk": normalize_severity(result.general_risk),
        "extracted_fields": dict(sorted(fields.items())),
        "findings": findings,
        "clauses_count": len(result.clauses),
        "summary_executive": (result.summary_executive or "").strip(),
    }
