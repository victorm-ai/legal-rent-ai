# Documentación del Proyecto — Legal Rent AI

Documentación del sistema de análisis de contratos de arrendamiento inmobiliario en México (MVP).

## Índice

| Documento | Descripción |
|-----------|-------------|
| [cliente-abogado-flujo-contrato.png](./cliente-abogado-flujo-contrato.png) | **Diagrama** del flujo cliente–abogado (carga → cierre y firma) |
| [guide/](./guide/README.md) | **Guía de uso de la aplicación web** (PDF) |
| [requirements.md](./requirements.md) | Requerimientos cumplidos del MVP (alcance entregado al 100 %) |
| [authentication.md](./authentication.md) | Autenticación (RF-01) y roles (RF-02) — SQL Server |
| [contracts.md](./contracts.md) | Carga de contratos PDF/DOCX (RF-03–RF-08) |
| [api.md](./api.md) | Especificación REST de la API |
| [architecture/](./architecture/README.md) | Diagramas de arquitectura C4 |
| [database/](./database/README.md) | Modelo relacional, DDL y guía SSMS |
| [legal-sources/](./legal-sources/README.md) | PDFs oficiales y corpus CAG markdown |
| [deployment/](./deployment/docker.md) | Docker local y Azure (LIDR, dominio ACS) |
| [deployment/docker-architecture.md](./deployment/docker-architecture.md) | Diagrama de arquitectura Docker Compose |
| [architecture/ai-runtime-and-litellm.md](./architecture/ai-runtime-and-litellm.md) | IA, agentes y capa LiteLLM |

## Layout del repositorio (2026)

```
├── backend/          # FastAPI, servicios, LLM, guardrails, rag
├── frontend/         # React + Vite + MUI
├── docker/           # Imágenes y scripts de contenedor
├── docs/             # Esta carpeta (español)
├── evals/            # Regresión y judge offline del análisis
├── tests/            # unit / integration / smoke / load
├── scripts/          # Mantenimiento; índice en scripts/README.md
├── fixtures/         # Contratos de ejemplo (sample-contracts/)
├── .env              # Config (raíz; leída por backend/config)
├── docker-compose.yml
└── pyproject.toml
```

## Estado de implementación (septiembre 2026)

| Módulo | RF | Estado |
|--------|-----|--------|
| Autenticación y roles | RF-01, RF-02 | ✅ `lawyer`, `client` — SQL Server |
| Carga y gestión de contratos | RF-03–RF-08, RF-53, RF-56 | ✅ API + UI |
| Extracción de texto / OCR | RF-06, RF-07 | ✅ Persistido + endpoint `/text` |
| Motor de análisis IA | RF-09–RF-37, RF-52, RF-58 | ✅ Pipeline + UI |
| Corpus legal (CAG) | RF-32′, RF-34′ | ✅ Markdown + inyección en prompts |
| Guardrails LLM | RNF (dominio / inyección) | ✅ Gateway + chat scope |
| Chat contextual | RF-41–RF-45 | ✅ REST + SSE `/messages/stream` |
| Reportes PDF/JSON | RF-46–RF-49 | ✅ Generación y descarga |
| Notificaciones abogado | RF-50, RF-51 | ✅ API (+ mensajes en expediente) |
| Comparación contratos | RF-59–RF-62 | ✅ `/comparisons` |
| Revisión abogado | RF-68–RF-70 | ✅ Hallazgos, aprobación, export feedback |
| Versión editada / comparación revisiones | RF-57 | ✅ `lawyer-revision`, `revision-comparison`, `is_signed_version` |
| Cierre y coordinación de firma | RF-56 | ✅ Cierre `terminated`, agente LangGraph, ACS Email, `/schedule-signing` |
| Retención documentos | RF-54 | 🚧 Política API; purga vía `RetentionService` (sin HTTP admin) |
| Despliegue | — | ✅ Docker Compose local; Azure LIDR (`scripts/azure/deploy-lidr.ps1`) |
| Evals LLM offline | — | ✅ `python -m evals` (regresión / judge) |
| RAG vectorial (Chroma / Azure Search) | — | 📋 Planificado — hoy CAG en contexto |
| Frontend | — | ✅ Dashboard, upload, análisis, chat, reportes, cierre, agenda firma |

## Estructura de `docs/`

```
docs/
├── README.md
├── cliente-abogado-flujo-contrato.png   # Flujo cliente–abogado (también en README raíz)
├── guide/              # Guía de usuario (PDF)
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

## Convenciones

- Markdown (`.md`) para documentación técnica y funcional.
- Nombres de archivo en minúsculas con guiones cuando aplique.
- Mantener este índice al añadir documentos nuevos.

## Política de idiomas

| Ámbito | Idioma |
|--------|--------|
| Código (`backend/`, `frontend/`) | Inglés |
| Documentación (`docs/`, README raíz) | Español |
| Interfaz web | Inglés |
| API (rutas, JSON, errores) | Inglés |
| Campos legales extraídos | Español (dominio MX) |
