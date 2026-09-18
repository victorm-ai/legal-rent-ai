"""Repository paths for offline evaluation (separate from backend/storage)."""

from __future__ import annotations

from pathlib import Path

EVALS_ROOT = Path(__file__).resolve().parent
REPO_ROOT = EVALS_ROOT.parent
DATASETS_DIR = EVALS_ROOT / "datasets" / "analysis"
BASELINES_DIR = EVALS_ROOT / "baselines"


def baseline_dir(prompt_id: str) -> Path:
    return BASELINES_DIR / prompt_id


def dataset_cases() -> list[Path]:
    if not DATASETS_DIR.is_dir():
        return []
    return sorted(DATASETS_DIR.glob("*.json"))
