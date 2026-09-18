"""PDF report generation (RF-48, RF-40, RF-31, RF-36)."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def generate_pdf_report(payload: dict[str, Any], output_path: Path) -> None:
    from fpdf import FPDF

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", size=14)
    width = pdf.epw
    pdf.cell(width, 10, "Legal Rent AI - Contract Analysis Report", ln=True)
    pdf.set_font("Helvetica", size=10)
    pdf.ln(4)

    meta = payload.get("meta", {})
    pdf.multi_cell(width, 6, f"Contract: {_safe_text(str(meta.get('contract_title', 'N/A')))}")
    pdf.multi_cell(width, 6, f"Analysis ID: {_safe_text(str(meta.get('analysis_id', 'N/A')))}")
    pdf.multi_cell(width, 6, f"General risk: {_safe_text(str(meta.get('general_risk', 'N/A')))}")
    pdf.ln(4)

    summary = payload.get("summary_executive") or ""
    if summary:
        pdf.set_font("Helvetica", style="B", size=11)
        pdf.cell(0, 8, "Executive summary", ln=True)
        pdf.set_font("Helvetica", size=10)
        pdf.multi_cell(width, 6, _safe_text(summary))
        pdf.ln(2)

    extracted = payload.get("extracted_data") or {}
    if extracted:
        pdf.set_font("Helvetica", style="B", size=11)
        pdf.cell(0, 8, "Extracted data", ln=True)
        pdf.set_font("Helvetica", size=10)
        for key, value in extracted.items():
            if isinstance(value, dict):
                line = f"- {key}: {value.get('value', '')}"
                if value.get("requires_review"):
                    line += " [Requires review]"
                source = value.get("source") or {}
                if source.get("text_snippet"):
                    line += f" (source: {source['text_snippet'][:80]}…)"
            else:
                line = f"- {key}: {value}"
            pdf.multi_cell(width, 6, _safe_text(str(line)))
        pdf.ln(2)

    findings = payload.get("findings") or []
    if findings:
        pdf.set_font("Helvetica", style="B", size=11)
        pdf.cell(0, 8, f"Findings ({len(findings)})", ln=True)
        pdf.set_font("Helvetica", size=10)
        for item in findings:
            pdf.multi_cell(
                width,
                6,
                f"[{item.get('severity', '').upper()}] {_safe_text(str(item.get('title', '')))}",
            )
            pdf.multi_cell(width, 6, _safe_text(str(item.get("description", ""))))
            if item.get("recommendation"):
                pdf.multi_cell(width, 6, f"Recommendation: {_safe_text(str(item['recommendation']))}")
            if item.get("legal_basis"):
                pdf.multi_cell(width, 6, f"Legal basis: {_safe_text(str(item['legal_basis']))}")
            if item.get("source_law"):
                pdf.multi_cell(width, 6, f"Source law: {_safe_text(str(item['source_law']))}")
            if item.get("evidence_text"):
                pdf.multi_cell(width, 6, f"Evidence: {_safe_text(str(item['evidence_text'])[:400])}")
            if item.get("suggested_rewording"):
                pdf.multi_cell(
                    width,
                    6,
                    f"Suggested rewording: {_safe_text(str(item['suggested_rewording'])[:400])}",
                )
            pdf.ln(2)

    pdf.output(str(output_path))


def _safe_text(value: str) -> str:
    replacements = {
        "\u2014": "-",
        "\u2013": "-",
        "\u201c": '"',
        "\u201d": '"',
        "\u2018": "'",
        "\u2019": "'",
        "\u00a0": " ",
    }
    for src, dst in replacements.items():
        value = value.replace(src, dst)
    return value.encode("latin-1", errors="replace").decode("latin-1")
