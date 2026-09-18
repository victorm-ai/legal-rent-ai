"""Document type classification tests (RF-08)."""

import io
import os
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from document.classifier import (
    DOCUMENT_TYPE_ANNEX,
    DOCUMENT_TYPE_MAIN,
    DOCUMENT_TYPE_OTHER,
    classify_document,
)


def _docx_with_text(text: str) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types></Types>")
        archive.writestr(
            "word/document.xml",
            f"""
            <w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
              <w:body><w:p><w:r><w:t>{text}</w:t></w:r></w:p></w:body>
            </w:document>
            """.strip(),
        )
    return buffer.getvalue()


def test_classify_main_contract_from_filename():
    result = classify_document(
        file_name="Contrato_Arrendamiento_Local.pdf",
        content=b"%PDF-1.4",
        mime_type="application/pdf",
        is_first_document=True,
    )
    assert result.document_type == DOCUMENT_TYPE_MAIN


def test_classify_annex_from_filename():
    result = classify_document(
        file_name="Anexo_A_Condiciones.docx",
        content=_docx_with_text(""),
        mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        is_first_document=False,
    )
    assert result.document_type == DOCUMENT_TYPE_ANNEX


def test_classify_annex_from_content():
    result = classify_document(
        file_name="documento.docx",
        content=_docx_with_text("ANEXO AL CONTRATO DE ARRENDAMIENTO"),
        mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        is_first_document=False,
    )
    assert result.document_type == DOCUMENT_TYPE_ANNEX


def test_classify_other_related_document():
    result = classify_document(
        file_name="Identificacion_Arrendatario.pdf",
        content=b"%PDF-1.4",
        mime_type="application/pdf",
        is_first_document=False,
    )
    assert result.document_type == DOCUMENT_TYPE_OTHER


def main():
    print("=" * 60)
    print("Legal Rent AI - Document Classification Tests")
    print("=" * 60)
    print()

    try:
        test_classify_main_contract_from_filename()
        print("Main contract from filename: PASSED")

        test_classify_annex_from_filename()
        print("Annex from filename: PASSED")

        test_classify_annex_from_content()
        print("Annex from content: PASSED")

        test_classify_other_related_document()
        print("Other related document: PASSED")

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
