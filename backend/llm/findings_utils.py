"""Shared helpers for findings severity ordering and risk aggregation."""

from __future__ import annotations

from typing import Any

SEVERITY_RANK = {"high": 0, "medium": 1, "low": 2}

VALID_FINDING_TYPES = frozenset(
    {
        "legal_rule",
        "best_practice",
        "missing_clause",
        "contradiction",
        "inconsistency",
        "unfavorable_clause",
        "obligation",
    }
)


def normalize_severity(value: str | None) -> str:
    normalized = (value or "medium").lower().strip()
    return normalized if normalized in SEVERITY_RANK else "medium"


def compute_sort_orders(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Assign sort_order and return findings sorted high → medium → low."""
    ranked = sorted(
        enumerate(findings),
        key=lambda item: (
            SEVERITY_RANK.get(normalize_severity(item[1].get("severity")), 1),
            item[0],
        ),
    )
    ordered: list[dict[str, Any]] = []
    for order, (_, finding) in enumerate(ranked):
        finding["sort_order"] = order
        ordered.append(finding)
    return ordered


def aggregate_general_risk(findings: list[dict[str, Any]], fallback: str = "medium") -> str:
    if not findings:
        return fallback
    severities = {normalize_severity(item.get("severity")) for item in findings}
    if "high" in severities:
        return "high"
    if "medium" in severities:
        return "medium"
    return "low"


def resolve_clause_id(
    finding: dict[str, Any],
    saved_clauses: list[Any],
) -> str | None:
    """Map clause_index or section hint to a persisted clause ID."""
    clause_index = finding.get("clause_index")
    if clause_index is not None:
        try:
            index = int(clause_index)
            if 0 <= index < len(saved_clauses):
                return saved_clauses[index].id
        except (TypeError, ValueError):
            pass

    section_hint = finding.get("clause_section") or finding.get("section")
    if section_hint:
        lowered = str(section_hint).lower()
        for clause in saved_clauses:
            if clause.section and lowered in clause.section.lower():
                return clause.id
    return None


def ensure_finding_confidence(finding: dict[str, Any]) -> dict[str, Any]:
    """Ensure every finding has a confidence score (RNF-13)."""
    if "confidence" not in finding or finding["confidence"] is None:
        severity = normalize_severity(finding.get("severity"))
        finding["confidence"] = {"high": 0.86, "medium": 0.78, "low": 0.72}[severity]
    return finding


def apply_evidence_guardrails(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Mark findings without evidence as requiring review (RNF-10)."""
    guarded: list[dict[str, Any]] = []
    for item in findings:
        finding = ensure_finding_confidence(dict(item))
        evidence = (finding.get("evidence_text") or "").strip()
        if finding.get("severity") == "high" and not evidence:
            suffix = " [Requires human review — limited evidence.]"
            description = finding.get("description") or ""
            if suffix.strip() not in description:
                finding["description"] = description + suffix
            finding["confidence"] = min(float(finding.get("confidence", 0.78)), 0.75)
        guarded.append(finding)
    return guarded
