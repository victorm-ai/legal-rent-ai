"""OCR para PDF escaneados (RF-07) — cascaron, fuera de alcance RF-20.

RF-20 identifica cláusulas relevantes a partir de texto utilizable obtenido
mediante extracción nativa (PDF con capa de texto o DOCX). El MVP no requiere
OCR; este módulo reserva la interfaz para una implementación futura.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

OCR_STATUS_STUB = "stub"


def is_ocr_available() -> bool:
    """Indica si hay un motor OCR operativo (False en MVP)."""
    return False


def extract_text_from_scanned_pdf(content: bytes, max_pages: int = 30) -> tuple[str, int | None]:
    """Placeholder OCR: no implementado; el MVP solo procesa archivos con texto nativo."""
    logger.info(
        "OCR stub: %s bytes, max_pages=%s (sin implementación; usar PDF/DOCX con texto)",
        len(content),
        max_pages,
    )
    return "", None
