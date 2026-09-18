"""Build CAG-ready markdown from local legal PDFs (curated articles only)."""

from __future__ import annotations

import re
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parents[2]
SOURCES = ROOT / "docs" / "legal-sources"
OUT = SOURCES / "cag-corpus-v1.md"

JALISCO_KEEP = {
    "1980",
    "1981",
    "1981-BIS",
    "1982",
    "1983",
    "1986",
    "1995",
    "1996",
    "1997",
    "2005",
    "2006",
    "2007",
    "2010",
    "2019",
    "2020",
    "2023",
    "2024",
    "2025",
    "2034",
    "2035",
    "2036",
    "2038",
    "2039",
    "2041",
    "2042",
    "2043",
    "2044",
    "2045",
    "2046",
    "2136",
    "2137",
    "2138",
    "2140",
    "2141",
    "2142",
    "2143",
    "2144",
    "2145",
    "2146",
}

CCF_KEEP = {
    "13",
    "2398",
    "2399",
    "2400",
    "2401",
    "2406",
    "2412",
    "2425",
    "2448",
    "2449",
    "2450",
    "2480",
    "2481",
    "2483",
    "2484",
    "2485",
    "2490",
    "2496",
}

CPC_KEEP = {str(n) for n in range(683, 693)} | {"692-BIS"}


def pdf_text(path: Path) -> str:
    doc = pymupdf.open(path)
    return "\n".join(page.get_text() for page in doc)


def slice_between(text: str, start: str, end: str) -> str:
    i = text.find(start)
    if i < 0:
        raise ValueError(f"Start marker not found: {start!r}")
    j = text.find(end, i + len(start))
    if j < 0:
        return text[i:]
    return text[i:j]


ARTICLE_RE = re.compile(
    r"(?:^|\n)\s*Artículo\s+(\d+)\s*(?:(Bis|BIS)\.?\s*)?[-–.]?\s*",
    re.IGNORECASE | re.MULTILINE,
)


def parse_articles(block: str) -> dict[str, str]:
    matches = list(ARTICLE_RE.finditer(block))
    out: dict[str, str] = {}
    for idx, match in enumerate(matches):
        num = match.group(1)
        bis = match.group(2)
        key = f"{num}-BIS" if bis else num
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(block)
        body = block[match.end() : end].strip()
        body = re.sub(r"^\s*-\s+", "", body)
        body = re.sub(r"[ \t]+", " ", body)
        body = re.sub(r"\n{3,}", "\n\n", body)
        if body and key not in out:
            out[key] = body
    return out


def format_article(instrument: str, key: str, body: str) -> str:
    label = key.replace("-BIS", " Bis")
    return f"### Artículo {label} ({instrument})\n\n{body.strip()}\n"


def main() -> None:
    jal_pdf = SOURCES / "codigo-civil-jalisco.pdf"
    ccf_pdf = SOURCES / "codigo-civil-federal.pdf"
    cpc_pdf = SOURCES / "codigo-procedimientos-civiles-jalisco.pdf"

    jal_text = pdf_text(jal_pdf)
    ccf_text = pdf_text(ccf_pdf)
    cpc_text = pdf_text(cpc_pdf)

    jal_block = slice_between(
        jal_text,
        "Artículo 1980.- Es arrendamiento aquél",
        "Artículo 2147.-",
    )
    ccf_block = slice_between(ccf_text, "Artículo 2398.-", "Artículo 2497.-")
    ccf_13 = slice_between(ccf_text, "Artículo 13.-", "Artículo 14.-")
    cpc_block = slice_between(cpc_text, "Artículo 683.-", "Artículo 693.-")

    jal_arts = parse_articles(jal_block)
    ccf_arts = parse_articles(ccf_block)
    ccf_13_arts = parse_articles(ccf_13)
    cpc_arts = parse_articles(cpc_block)

    sections: list[str] = [
        "# Corpus CAG v1 — Arrendamiento inmobiliario (Jalisco, México)",
        "",
        "Texto extraído de los PDF en `docs/legal-sources/` para **precarga en CAG** (contexto jurídico fijo).",
        "Incluye solo artículos **curados**; no sustituye asesoría legal ni la versión oficial vigente.",
        "",
        "| Metadato | Valor |",
        "|----------|--------|",
        "| `corpus_id` | `legal-cag-v1-jal-arrendamiento` |",
        "| `corpus_version` | `2026-09-16` |",
        "| `jurisdiction_primary` | `MX-JAL` |",
        "| `language` | `es-MX` |",
        "",
        "---",
        "",
        "## 1. Código Civil del Estado de Jalisco",
        "",
        "**Aplicación:** contratos sobre inmuebles en Jalisco (norma sustantiva principal).",
        f"**Fuente local:** `{jal_pdf.name}`",
        "",
    ]

    missing_jal: list[str] = []
    for key in sorted(JALISCO_KEEP, key=lambda k: (int(k.split("-")[0]), k)):
        body = jal_arts.get(key)
        if not body:
            missing_jal.append(key)
            continue
        sections.append(format_article("CC Jalisco", key, body))

    sections.extend(
        [
            "---",
            "",
            "## 2. Código Civil Federal",
            "",
            "**Aplicación:** conflicto de leyes (art. 13) y referencia supletoria / comparativa en arrendamiento.",
            f"**Fuente local:** `{ccf_pdf.name}`",
            "",
        ]
    )

    body_13 = ccf_13_arts.get("13")
    if body_13:
        sections.append(format_article("CCF", "13", body_13))

    missing_ccf: list[str] = []
    for key in sorted(CCF_KEEP - {"13"}, key=lambda k: int(k.split("-")[0])):
        body = ccf_arts.get(key)
        if not body:
            missing_ccf.append(key)
            continue
        sections.append(format_article("CCF", key, body))

    sections.extend(
        [
            "---",
            "",
            "## 3. Código de Procedimientos Civiles del Estado de Jalisco",
            "",
            "**Aplicación:** desocupación del inmueble arrendado (vía sumaria).",
            f"**Fuente local:** `{cpc_pdf.name}`",
            "",
        ]
    )

    missing_cpc: list[str] = []
    for key in sorted(CPC_KEEP, key=lambda k: (int(k.split("-")[0]), k)):
        body = cpc_arts.get(key)
        if not body:
            missing_cpc.append(key)
            continue
        sections.append(format_article("CPC Jalisco", key, body))

    if missing_jal or missing_ccf or missing_cpc:
        sections.extend(["---", "", "## Artículos no localizados en el PDF", ""])
        if missing_jal:
            sections.append(f"- CC Jalisco: {', '.join(missing_jal)}")
        if missing_ccf:
            sections.append(f"- CCF: {', '.join(missing_ccf)}")
        if missing_cpc:
            sections.append(f"- CPC Jalisco: {', '.join(missing_cpc)}")

    sections.extend(
        [
            "",
            "---",
            "",
            "## Uso en el pipeline CAG",
            "",
            "1. Cargar este archivo completo (o por sección) como prefijo de sistema / KV cache.",
            "2. Al citar, usar `instrument` + número de artículo y validar contra PDF oficial si hubo reforma.",
            "3. Priorizar **CC Jalisco** cuando el contrato indique Jalisco o el inmueble esté en la entidad.",
            "",
        ]
    )

    OUT.write_text("\n".join(sections), encoding="utf-8")
    print(f"Wrote {OUT} ({OUT.stat().st_size} bytes)")
    if missing_jal or missing_ccf or missing_cpc:
        print("Missing:", missing_jal, missing_ccf, missing_cpc)


if __name__ == "__main__":
    main()
