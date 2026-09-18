"""Basic concurrent smoke test for API health (RNF-01)."""

from __future__ import annotations

import concurrent.futures
import os
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

API_URL = os.getenv("API_URL", "http://localhost:8000")
CONCURRENT_USERS = int(os.getenv("LOAD_CONCURRENT_USERS", "10"))


def hit_health(_index: int) -> int:
    response = httpx.get(f"{API_URL}/health", timeout=30.0)
    return response.status_code


def main() -> int:
    with concurrent.futures.ThreadPoolExecutor(max_workers=CONCURRENT_USERS) as pool:
        codes = list(pool.map(hit_health, range(CONCURRENT_USERS)))
    ok = sum(1 for code in codes if code == 200)
    print(f"Concurrent health checks: {ok}/{CONCURRENT_USERS} succeeded")
    return 0 if ok == CONCURRENT_USERS else 1


if __name__ == "__main__":
    raise SystemExit(main())
