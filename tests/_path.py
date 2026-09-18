"""Add backend package root to sys.path for tests and smoke scripts."""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_ROOT = REPO_ROOT / "backend"


def ensure_backend_path() -> Path:
    backend = str(BACKEND_ROOT)
    if backend not in sys.path:
        sys.path.insert(0, backend)
    return BACKEND_ROOT
