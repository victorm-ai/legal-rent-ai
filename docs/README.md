# Project documentation — Legal Rent AI

Documentation for the residential lease contract analysis system in Mexico (MVP).

## Index

| Document | Description |
|-----------|-------------|
| [cliente-abogado-flujo-contrato.png](./cliente-abogado-flujo-contrato.png) | **Diagram** of the client–lawyer flow (upload → closure and signing) |
| [guide/](./guide/README.md) | **Web application user guide** (PDF) |
| [requirements.md](./requirements.md) | MVP requirements delivered (100% scope) |
| [authentication.md](./authentication.md) | Authentication (RF-01) and roles (RF-02) — SQL Server |
| [contracts.md](./contracts.md) | PDF/DOCX contract upload (RF-03–RF-08) |
| [api.md](./api.md) | REST API specification |
| [architecture/](./architecture/README.md) | C4 architecture diagrams |
| [database/](./database/README.md) | Relational model, DDL, and SSMS guide |
| [legal-sources/](./legal-sources/README.md) | Official PDFs and CAG markdown corpus |
| [deployment/](./deployment/docker.md) | Local Docker and Azure (LIDR, ACS domain) |
| [deployment/docker-architecture.md](./deployment/docker-architecture.md) | Docker Compose architecture diagram |
| [architecture/ai-runtime-and-litellm.md](./architecture/ai-runtime-and-litellm.md) | AI, agents, and LiteLLM layer |

## Repository layout (2026)

```
├── backend/          # FastAPI, services, LLM, guardrails, rag
├── frontend/         # React + Vite + MUI
├── docker/           # Container images and scripts
├── docs/             # This folder (English)
├── evals/            # Offline analysis regression and judge
├── tests/            # unit / integration / smoke / load
├── scripts/          # Maintenance; index in scripts/README.md
├── fixtures/         # Sample contracts (sample-contracts/)
├── .env              # Config (root; read by backend/config)
├── docker-compose.yml
└── pyproject.toml
```

## Implementation status (September 2026)

| Module | RF | Status |
|--------|-----|--------|
| Authentication and roles | RF-01, RF-02 | ✅ `lawyer`, `client` — SQL Server |
| Contract upload and management | RF-03–RF-08, RF-53, RF-56 | ✅ API + UI |
| Text extraction / OCR | RF-06, RF-07 | ✅ Persisted + `/text` endpoint |
| AI analysis engine | RF-09–RF-37, RF-52, RF-58 | ✅ Pipeline + UI |
| Legal corpus (CAG) | RF-32′, RF-34′ | ✅ Markdown + prompt injection |
| LLM guardrails | NFR (domain / injection) | ✅ Gateway + chat scope |
| Contextual chat | RF-41–RF-45 | ✅ REST + SSE `/messages/stream` |
| PDF/JSON reports | RF-46–RF-49 | ✅ Generation and download |
| Lawyer notifications | RF-50, RF-51 | ✅ API (+ case messages) |
| Contract comparison | RF-59–RF-62 | ✅ `/comparisons` |
| Lawyer review | RF-68–RF-70 | ✅ Findings, approval, feedback export |
| Edited version / revision comparison | RF-57 | ✅ `lawyer-revision`, `revision-comparison`, `is_signed_version` |
| Closure and signing coordination | RF-56 | ✅ `terminated` closure, LangGraph agent, ACS Email, `/schedule-signing` |
| Document retention | RF-54 | 🚧 API policy; purge via `RetentionService` (no HTTP admin) |
| Deployment | — | ✅ Local Docker Compose; Azure LIDR (`scripts/azure/deploy-lidr.ps1`) |
| Offline LLM evals | — | ✅ `python -m evals` (regression / judge) |
| Vector RAG (Chroma / Azure Search) | — | 📋 Planned — CAG in context today |
| Frontend | — | ✅ Dashboard, upload, analysis, chat, reports, closure, signing schedule |

## `docs/` structure

```
docs/
├── README.md
├── cliente-abogado-flujo-contrato.png   # Client–lawyer flow (also in root README)
├── guide/              # User guide (PDF)
├── requirements.md
├── authentication.md
├── contracts.md
├── api.md
├── legal-sources/
├── architecture/
│   ├── README.md
│   ├── c4-level1-system-context.md
│   ├── c4-level2-containers.md
│   ├── c4-level3-components.md
│   └── c4-level4-code-auth.md
├── deployment/
│   ├── docker.md
│   ├── azure-resources.md
│   └── …
└── database/
    ├── README.md
    ├── schema-design.md
    ├── setup-ssms.md
    ├── ddl.sql
    ├── seed.sql
    └── migrations/
```

## Conventions

- Markdown (`.md`) for technical and functional documentation.
- Lowercase file names with hyphens where applicable.
- Keep this index updated when adding new documents.

## Language policy

| Scope | Language |
|--------|--------|
| Code (`backend/`, `frontend/`) | English |
| Documentation (`docs/`, root README) | English |
| Web UI | English |
| API (routes, JSON, errors) | English |
| Extracted legal fields | Spanish (MX domain) |
