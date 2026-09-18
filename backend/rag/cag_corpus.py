"""Cache-augmented legal corpus loaded from markdown (RF-32–RF-34)."""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path

from config.settings import REPO_ROOT, Settings, get_settings

logger = logging.getLogger(__name__)

CORPUS_HEADER = (
    "---\n"
    "AUTHORIZED LEGAL CORPUS (CAG): Mexican lease law excerpts for Jalisco and supplemental federal/state procedural rules. "
    "Ground legal_rule findings, legal_basis, source_law, and legal_citations ONLY on this corpus and the contract text. "
    "Do not invent articles or laws not supported below.\n"
    "---\n"
)


def resolve_corpus_path(settings: Settings | None = None) -> Path:
    settings = settings or get_settings()
    path = Path(settings.legal_cag_corpus_path)
    if not path.is_absolute():
        path = REPO_ROOT / path
    return path


@lru_cache(maxsize=1)
def _load_corpus_text_cached(resolved_path: str, enabled: bool) -> str:
    if not enabled:
        return ""
    path = Path(resolved_path)
    if not path.is_file():
        logger.warning("Legal CAG corpus file not found: %s", path)
        return ""
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        logger.exception("Failed to read legal CAG corpus: %s", path)
        return ""


def get_cag_corpus_text(settings: Settings | None = None) -> str:
    """Return full markdown corpus for injection into LLM system context."""
    settings = settings or get_settings()
    path = resolve_corpus_path(settings)
    return _load_corpus_text_cached(str(path.resolve()), settings.legal_cag_enabled)


def clear_corpus_cache() -> None:
    """Clear cached corpus (tests or after file update)."""
    _load_corpus_text_cached.cache_clear()


def build_legal_context_block(settings: Settings | None = None) -> str:
    corpus = get_cag_corpus_text(settings)
    if not corpus:
        return ""
    return f"{CORPUS_HEADER}\n{corpus}"
