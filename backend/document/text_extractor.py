"""Extract and persist plain text from PDF and DOCX files (RF-06).

RF-20 consumes native text extracted here; scanned OCR lives in document/ocr.py (stub).
"""

from dataclasses import dataclass
import io
import logging
import zipfile
import xml.etree.ElementTree as ET

from document.ocr import extract_text_from_scanned_pdf

MAX_PREVIEW_PAGES = 5
MAX_PREVIEW_PARAGRAPHS = 120
MIN_USABLE_TEXT_CHARS = 40
DEFAULT_MAX_PDF_PAGES = 100
DEFAULT_OCR_MAX_PAGES = 30

EXTRACTION_NATIVE = "native"
EXTRACTION_OCR = "ocr"
EXTRACTION_NONE = "none"

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TextExtractionResult:
    """Full text extraction outcome for a document."""

    text: str
    page_count: int | None
    extraction_method: str


def extract_text_preview(content: bytes, mime_type: str, max_chars: int = 8000) -> str:
    """Return a text preview used for document classification."""
    result = extract_document_text(
        content,
        mime_type,
        ocr_enabled=False,
        max_pdf_pages=MAX_PREVIEW_PAGES,
    )
    normalized = " ".join(result.text.split())
    return normalized[:max_chars]


def extract_document_text(
    content: bytes,
    mime_type: str,
    ocr_enabled: bool = True,
    max_pdf_pages: int = DEFAULT_MAX_PDF_PAGES,
    ocr_max_pages: int = DEFAULT_OCR_MAX_PAGES,
) -> TextExtractionResult:
    """Extract full document text from PDF/DOCX with native text layers (RF-06)."""
    if mime_type == "application/pdf":
        return _extract_pdf_full(content, ocr_enabled, max_pdf_pages, ocr_max_pages)

    text = _extract_docx_full(content)
    page_count = None
    if text.strip():
        return TextExtractionResult(
            text=text,
            page_count=page_count,
            extraction_method=EXTRACTION_NATIVE,
        )
    return TextExtractionResult(text="", page_count=page_count, extraction_method=EXTRACTION_NONE)


def _extract_pdf_full(
    content: bytes,
    ocr_enabled: bool,
    max_pdf_pages: int,
    ocr_max_pages: int,
) -> TextExtractionResult:
    text, page_count = _extract_pdf_native(content, max_pdf_pages)
    if _is_usable_text(text):
        return TextExtractionResult(
            text=text,
            page_count=page_count,
            extraction_method=EXTRACTION_NATIVE,
        )

    if ocr_enabled:
        ocr_text, ocr_pages = extract_text_from_scanned_pdf(content, ocr_max_pages)
        if _is_usable_text(ocr_text):
            return TextExtractionResult(
                text=ocr_text,
                page_count=ocr_pages,
                extraction_method=EXTRACTION_OCR,
            )

    return TextExtractionResult(
        text=text.strip(),
        page_count=page_count,
        extraction_method=EXTRACTION_NONE if not text.strip() else EXTRACTION_NATIVE,
    )


def _is_usable_text(text: str) -> bool:
    return len(text.strip()) >= MIN_USABLE_TEXT_CHARS


def _extract_pdf_native(content: bytes, max_pages: int) -> tuple[str, int | None]:
    text = _extract_pdf_with_pdfplumber(content, max_pages)
    page_count = _pdf_page_count(content)
    if _is_usable_text(text):
        return text, page_count

    fallback = _extract_pdf_with_pypdf2(content, max_pages)
    if _is_usable_text(fallback):
        return fallback, page_count
    return fallback or text, page_count


def _extract_pdf_with_pdfplumber(content: bytes, max_pages: int) -> str:
    try:
        import pdfplumber

        parts: list[str] = []
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            for index, page in enumerate(pdf.pages):
                if index >= max_pages:
                    break
                page_text = page.extract_text() or ""
                if page_text.strip():
                    parts.append(f"\n<!-- PAGE:{index + 1} -->\n{page_text}")
        return "\n".join(parts)
    except Exception:
        logger.warning("pdfplumber extraction failed", exc_info=True)
        return ""


def _extract_pdf_with_pypdf2(content: bytes, max_pages: int) -> str:
    try:
        from PyPDF2 import PdfReader

        reader = PdfReader(io.BytesIO(content))
        parts: list[str] = []
        for index, page in enumerate(reader.pages):
            if index >= max_pages:
                break
            page_text = page.extract_text() or ""
            if page_text.strip():
                parts.append(f"\n<!-- PAGE:{index + 1} -->\n{page_text}")
        return "\n".join(parts)
    except Exception:
        logger.warning("PyPDF2 extraction failed", exc_info=True)
        return ""


def _pdf_page_count(content: bytes) -> int | None:
    try:
        from PyPDF2 import PdfReader

        return len(PdfReader(io.BytesIO(content)).pages)
    except Exception:
        return None


def _extract_docx_full(content: bytes) -> str:
    try:
        from docx import Document

        document = Document(io.BytesIO(content))
        paragraphs = [
            paragraph.text.strip()
            for paragraph in document.paragraphs
            if paragraph.text.strip()
        ]
        if paragraphs:
            return "\n".join(paragraphs)
    except Exception:
        pass

    return _extract_docx_text_fallback(content)


def _extract_docx_text_fallback(content: bytes) -> str:
    """Fallback for minimal DOCX files without full python-docx support."""
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            if "word/document.xml" not in archive.namelist():
                return ""

            xml_content = archive.read("word/document.xml")
            root = ET.fromstring(xml_content)
            namespace = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
            texts = [
                node.text.strip()
                for node in root.iter(f"{namespace}t")
                if node.text and node.text.strip()
            ]
            return "\n".join(texts)
    except Exception:
        logger.warning("DOCX fallback extraction failed", exc_info=True)
        return ""
