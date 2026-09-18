"""Schema and domain invariants for analysis JSON (post-pipeline)."""

from __future__ import annotations

from typing import Any

from llm.findings_utils import SEVERITY_RANK, VALID_FINDING_TYPES, normalize_severity


def score_structural_invariants(snapshot: dict[str, Any]) -> list[str]:
    """Return a list of violation messages; empty means pass."""
    errors: list[str] = []

    risk = snapshot.get("general_risk")
    if risk not in SEVERITY_RANK:
        errors.append(f"general_risk invalid: {risk!r}")

    fields = snapshot.get("extracted_fields")
    if not isinstance(fields, dict):
        errors.append("extracted_fields must be a dict")
    else:
        for name, value in fields.items():
            if not str(name).strip():
                errors.append("extracted_fields contains empty field_name key")
            if value is None:
                errors.append(f"field {name!r} has null value")

    findings = snapshot.get("findings")
    if not isinstance(findings, list):
        errors.append("findings must be a list")
    else:
        for index, item in enumerate(findings):
            if not isinstance(item, dict):
                errors.append(f"findings[{index}] is not an object")
                continue
            ftype = item.get("finding_type")
            if ftype not in VALID_FINDING_TYPES:
                errors.append(f"findings[{index}] invalid finding_type: {ftype!r}")
            severity = normalize_severity(item.get("severity"))
            if severity not in SEVERITY_RANK:
                errors.append(f"findings[{index}] invalid severity: {item.get('severity')!r}")

    summary = snapshot.get("summary_executive")
    if not isinstance(summary, str) or not summary.strip():
        errors.append("summary_executive must be a non-empty string")

    clauses_count = snapshot.get("clauses_count")
    if not isinstance(clauses_count, int) or clauses_count < 0:
        errors.append(f"clauses_count invalid: {clauses_count!r}")

    return errors
