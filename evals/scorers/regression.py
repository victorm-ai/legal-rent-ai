"""Compare candidate snapshot against a stored baseline."""

from __future__ import annotations

from typing import Any


def compare_regression_snapshots(
    baseline: dict[str, Any],
    candidate: dict[str, Any],
    *,
    soft_fields: frozenset[str] = frozenset({"summary_executive"}),
) -> tuple[list[str], list[str]]:
    """
    Return (hard_errors, soft_warnings).
    Hard failures block regression; soft diffs are informational (e.g. summary wording).
    """
    hard: list[str] = []
    soft: list[str] = []

    if baseline.get("general_risk") != candidate.get("general_risk"):
        hard.append(
            f"general_risk changed: {baseline.get('general_risk')!r} -> {candidate.get('general_risk')!r}"
        )

    base_fields = baseline.get("extracted_fields") or {}
    cand_fields = candidate.get("extracted_fields") or {}
    for key in sorted(set(base_fields) | set(cand_fields)):
        if base_fields.get(key) != cand_fields.get(key):
            hard.append(
                f"extracted_fields[{key!r}] changed: {base_fields.get(key)!r} -> {cand_fields.get(key)!r}"
            )

    if baseline.get("findings") != candidate.get("findings"):
        hard.append("findings list changed (type/severity/title signature)")

    if baseline.get("clauses_count") != candidate.get("clauses_count"):
        soft.append(
            f"clauses_count changed: {baseline.get('clauses_count')!r} -> {candidate.get('clauses_count')!r}"
        )

    for field in soft_fields:
        if baseline.get(field) != candidate.get(field):
            soft.append(f"{field} wording changed")

    return hard, soft
