"""Load analysis evaluation cases from evals/datasets/analysis/*.json."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from evals.paths import DATASETS_DIR


@dataclass
class AnalysisEvalCase:
    id: str
    description: str
    contract_text: str
    perspective: str = "tenant"
    title: str | None = None
    must_extract: dict[str, str] = field(default_factory=dict)
    must_findings: list[dict[str, Any]] = field(default_factory=list)
    judge_required: bool = False
    judge_mode: str = "absolute"  # absolute | comparative


def load_case(path: Path) -> AnalysisEvalCase:
    payload = json.loads(path.read_text(encoding="utf-8"))
    case_id = payload.get("id") or path.stem
    return AnalysisEvalCase(
        id=case_id,
        description=payload.get("description", ""),
        contract_text=payload["contract_text"],
        perspective=payload.get("perspective", "tenant"),
        title=payload.get("title"),
        must_extract=dict(payload.get("must_extract") or {}),
        must_findings=list(payload.get("must_findings") or []),
        judge_required=bool(payload.get("judge_required", False)),
        judge_mode=str(payload.get("judge_mode", "absolute")),
    )


def load_all_cases() -> list[AnalysisEvalCase]:
    if not DATASETS_DIR.is_dir():
        return []
    return [load_case(path) for path in sorted(DATASETS_DIR.glob("*.json"))]


def load_case_by_id(case_id: str) -> AnalysisEvalCase:
    path = DATASETS_DIR / f"{case_id}.json"
    if not path.is_file():
        raise FileNotFoundError(f"Eval case not found: {case_id} ({path})")
    return load_case(path)
