# Local legal sources (legal corpus — Top 3)

**Official PDF copies** downloaded from the Internet for the MVP analysis of real estate lease contracts in **Jalisco, Mexico**. They serve as offline documentary backup and as input for the **CAG corpus** (`cag-corpus-v1.md`) injected into analysis and chat; **do not load them whole into LLM context** — see [Recommended use](#recommended-use-cag--rag).

| Field | Value |
|-------|--------|
| Downloaded to repository | September 16, 2026 |
| Folder | `docs/legal-sources/` |
| Related requirements | RF-32′, RF-34′ in [requirements.md](../requirements.md) |

---

## 1. Civil Code of the State of Jalisco

| | |
|--|--|
| **File** | [`codigo-civil-jalisco.pdf`](./codigo-civil-jalisco.pdf) (~2.2 MB) |
| **Source** | [Congress of the State of Jalisco — Virtual Library](https://congresoweb.congresojal.gob.mx/BibliotecaVirtual/busquedasleyes/ListadoCr3.cfm) |
| **Direct URL** | `https://congresoweb.congresojal.gob.mx/BibliotecaVirtual/legislacion/Códigos/Documentos_PDF-Códigos/Código Civil del Estado de Jalisco-240626.pdf` |
| **Last amendment (legislative catalog)** | 06/18/2026 (per Congress index) |

### What it is

**State** code regulating, among other matters, the **lease contract** of property in Jalisco. For properties located in the state, it is the **main substantive norm** that should support findings and chat when detected jurisdiction is Jalisco.

### Lease-relevant content (CAG excerpt)

**Title VI — Lease (articles 1980–2146)**, in particular:

| Block | Articles | Topics |
|--------|-----------|--------|
| General provisions | 1980–1994 | Definition, rent, formalities |
| Landlord obligations | 1995–2004 | Delivery, maintenance, repairs |
| Tenant obligations | 2005–2022 | Payment, use, vacating, utilities |
| Real property (general) | 2023–2037 | **Minimum contract content**, indefinite term (2034–2035) |
| Residential | 2038–2044 | Rent caps and public order (2041–2043), renewal |
| Commercial / industrial | 2045–2053+ | Terms and rent for commercial premises |
| Sublease | 2136–2139 | Subleasing |
| Termination | 2140–2146 | Rescission and end of contract |

The PDF includes the **full civil code** (persons, family, obligations, sale, etc.). Only the title above matters for the lease corpus.

---

## 2. Federal Civil Code

| | |
|--|--|
| **File** | [`codigo-civil-federal.pdf`](./codigo-civil-federal.pdf) (~3.3 MB) |
| **Source** | [Chamber of Deputies — LeyesBiblio](https://www.diputados.gob.mx/LeyesBiblio/ref/ccf.htm) |
| **Direct URL** | `https://www.diputados.gob.mx/LeyesBiblio/pdf/CCF.pdf` |
| **Current text (PDF header)** | Last reform DOF **11-14-2025** |

### What it is

**Federal** code of supplementary application and, in some cases, direct application. For **real property lease**, article **13, section III** establishes that the **law of the place where the property is located** applies (in MVP practice: Jalisco CC). The FCC remains useful as a **conflict-of-laws framework** and reference for **movables**, terms, and structure of the federal lease title.

### Lease-relevant content (CAG excerpt)

| Block | Articles | Topics |
|--------|-----------|--------|
| Preliminary provisions | **13** (sec. III), 12–14 | Which law applies to real property lease |
| Title VI — Lease | **2398–2496** | Contract, obligations, residential (2448–2452), sublease, termination |

Do not use the full PDF in CAG: extract only the articles listed above.

---

## 3. Code of Civil Procedure of the State of Jalisco

| | |
|--|--|
| **File** | [`codigo-procedimientos-civiles-jalisco.pdf`](./codigo-procedimientos-civiles-jalisco.pdf) (~1.3 MB) |
| **Source** | [Congress of the State of Jalisco — Virtual Library](https://congresoweb.congresojal.gob.mx/BibliotecaVirtual/busquedasleyes/ListadoCr3.cfm) |
| **Direct URL** | `https://congresoweb.congresojal.gob.mx/BibliotecaVirtual/legislacion/Códigos/Documentos_PDF-Códigos/Código de Procedimientos Civiles del Estado de Jalisco-250424.pdf` |
| **Legislative reference (catalog)** | A.I. 9/2022; catalog update 09/05/2023 |

### What it is

**State procedural** code: rules for civil disputes before Jalisco courts. Complements substantive analysis when the contract or chat covers **vacating, default, term expiration, or recovery of the property**.

### Lease-relevant content (CAG excerpt)

| Block | Articles (approx.) | Topics |
|--------|-------------------|--------|
| Summary proceeding for **vacating** | **683–692** (verify **692 BIS** in current PDF) | Grounds (expiration, legal term, non-payment), procedure and **vacating period** (e.g. art. 688: 15 calendar days) |

The rest of the code (commercial enforcement, family, preparatory measures, etc.) is outside lease corpus v1.

---

## Recommended use (CAG / RAG)

1. **Repo storage:** these PDFs are the **authorized offline source**; re-download periodically from the same URLs and update this note.
2. **AI pipeline:** generate chunks only from the **article ranges** listed above (JSON/JSONL with `instrument`, `article`, `jurisdiction`, `source_url`).
3. **CAG:** preload **excerpts**, not all three full PDFs (hundreds of pages).
4. **Product citations:** point to specific article + official URL; the local path is for development, not end users.

## CAG corpus (markdown)

| File | Description |
|---------|-------------|
| [`cag-corpus-v1.md`](./cag-corpus-v1.md) | **Curated** articles extracted from the three PDFs for CAG preload (~35 KB). |
| [`../../scripts/corpus/build_cag_corpus_markdown.py`](../../scripts/corpus/build_cag_corpus_markdown.py) | Regenerates the markdown after updating PDFs. |

```bash
python scripts/corpus/build_cag_corpus_markdown.py
```

## Backend integration (implemented)

File [`cag-corpus-v1.md`](./cag-corpus-v1.md) is loaded from `backend/rag/cag_corpus.py` (configurable path `LEGAL_CAG_CORPUS_PATH`, default `docs/legal-sources/cag-corpus-v1.md` relative to repo root). It is injected into **analysis** and **chat** prompts via `llm/prompts.py` and `llm/chat_provider.py`.

Regenerate markdown after updating PDFs:

```bash
python scripts/corpus/build_cag_corpus_markdown.py
```

**Next product step:** vector RAG index in addition to static CAG; citation validation against official PDF in production.
