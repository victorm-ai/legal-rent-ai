#!/usr/bin/env python
"""Start the backend from the repository root."""

import importlib.util
import sys
from pathlib import Path

_backend_dir = Path(__file__).resolve().parent / "backend"
sys.path.insert(0, str(_backend_dir))

_spec = importlib.util.spec_from_file_location(
    "legal_rent_backend_runner",
    _backend_dir / "run_backend.py",
)
_module = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_module)
_module.main()
