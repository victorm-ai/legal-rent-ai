"""Pytest configuration: backend on import path."""

import sys
from pathlib import Path

_backend = Path(__file__).resolve().parent.parent / "backend"
_backend_str = str(_backend)
if _backend_str not in sys.path:
    sys.path.insert(0, _backend_str)
