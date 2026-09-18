"""Golden expectations from eval case definitions."""

from __future__ import annotations

import re
from typing import Any

from llm.findings_utils import SEVERITY_RANK, normalize_severity


def _normalize_amount(raw: str) -> str:
    cleaned = (raw or "").replace(",", "")
    match = re.search(r"(\d+(?:\.\d+)?)", cleaned)
    if not match:
        return ""
    value = float(match.group(1))
    if abs(value - round(value)) < 0.01:
        return str(int(round(value)))
    return str(value)


def _field_matches(expected: str, actual: str) -> bool:
    expected = expected.strip()
    actual = (actual or "").strip()
    if not expected:
        return bool(actual)
    if expected.startswith("/") and expected.endswith("/") and len(expected) > 2:
        pattern = expected[1:-1]
        return re.search(pattern, actual, re.IGNORECASE) is not None
    if re.fullmatch(r"\d+", _normalize_amount(expected)):
        return _normalize_amount(expected) == _normalize_amount(actual)
    return expected.lower() in actual.lower()


def score_golden_expectations(
    snapshot: dict[str, Any],
    must_extract: dict[str, str],
    must_findings: list[dict[str, Any]],
) -> list[str]:
    errors: list[str] = []
    fields: dict[str, str] = snapshot.get("extracted_fields") or {}

    for field_name, expected in must_extract.items():
        actual = fields.get(field_name, "")
        if not _field_matches(str(expected), str(actual)):
            errors.append(
                f"must_extract[{field_name}]: expected {expected!r}, got {actual!r}"
            )

    findings: list[dict[str, Any]] = snapshot.get("findings") or []
    for rule_index, rule in enumerate(must_findings):
        ftype = rule.get("finding_type")
        severity_min = normalize_severity(rule.get("severity_min"))
        min_rank = SEVERITY_RANK[severity_min]
        text_contains = rule.get("text_contains")

        matched = [
            item
            for item in findings
            if (ftype is None or item.get("finding_type") == ftype)
            and SEVERITY_RANK.get(normalize_severity(item.get("severity")), 1) <= min_rank
        ]
        if not matched:
            errors.append(
                f"must_findings[{rule_index}]: no finding matching type={ftype!r} "
                f"severity>={severity_min!r}"
            )
            continue
        if text_contains:
            needle = str(text_contains).lower()
            if not any(needle in str(item.get("title", "")).lower() for item in matched) and not any(
                needle in str(item.get("description", "")).lower() for item in matched
            ):
                errors.append(
                    f"must_findings[{rule_index}]: no finding text containing {text_contains!r}"
                )

    return errors
