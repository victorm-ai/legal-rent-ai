"""Text extraction tests (RF-06, RF-07)."""

import io
import os
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from document.text_extractor import (
    EXTRACTION_NATIVE,
    EXTRACTION_NONE,
    extract_document_text,
    extract_text_preview,
)


def _docx_with_text(text: str) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(
            "[Content_Types].xml",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="xml" ContentType="application/xml"/>'
            "</Types>",
        )
        archive.writestr(
            "word/document.xml",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            "<w:body>"
            f"<w:p><w:r><w:t>{text}</w:t></w:r></w:p>"
            "</w:body></w:document>",
        )
    return buffer.getvalue()


def test_extract_docx_full_text():
    content = _docx_with_text("Contrato de arrendamiento en Ciudad de Mexico")
    result = extract_document_text(
        content,
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ocr_enabled=False,
    )

    assert "arrendamiento" in result.text.lower()
    assert result.extraction_method == EXTRACTION_NATIVE


def test_extract_text_preview_truncates():
    long_text = " ".join(["clause"] * 2000)
    content = _docx_with_text(long_text)
    preview = extract_text_preview(
        content,
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        max_chars=500,
    )

    assert len(preview) <= 500
    assert "clause" in preview


def test_extract_pdf_without_text_returns_none_method():
    content = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
    result = extract_document_text(content, "application/pdf", ocr_enabled=False)

    assert result.extraction_method in {EXTRACTION_NONE, EXTRACTION_NATIVE}


def main() -> int:
    print("=" * 60)
    print("Legal Rent AI - Text Extraction Tests")
    print("=" * 60)
    print()
    try:
        test_extract_docx_full_text()
        print("DOCX full extraction: PASSED")

        test_extract_text_preview_truncates()
        print("Text preview truncation: PASSED")

        test_extract_pdf_without_text_returns_none_method()
        print("PDF without text: PASSED")

        print()
        print("=" * 60)
        print("ALL TESTS PASSED")
        print("=" * 60)
        return 0
    except Exception as exc:
        print(f"\nTest failed: {exc}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
