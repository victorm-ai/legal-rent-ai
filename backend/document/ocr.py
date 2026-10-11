"""OCR for scanned PDFs (RF-07) — stub; out of scope for RF-20.

RF-20 identifies relevant clauses from usable text obtained via native extraction
(PDF text layer or DOCX). The MVP does not require OCR; this module reserves the
interface for a future implementation.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

OCR_STATUS_STUB = "stub"


def is_ocr_available() -> bool:
    """Return whether an OCR engine is operational (False in MVP)."""
    return False


def extract_text_from_scanned_pdf(content: bytes, max_pages: int = 30) -> tuple[str, int | None]:
    """OCR placeholder: not implemented; MVP only processes files with native text."""
    logger.info(
        "OCR stub: %s bytes, max_pages=%s (not implemented; use PDF/DOCX with text)",
        len(content),
        max_pages,
    )
    return "", None
