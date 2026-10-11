# C4 — Level 2: Containers

Deployable units: SPA, API, database, and external services.

## Diagram — MVP target view

```mermaid
C4Container
    title Containers - Legal Rent AI MVP (target)

    Person(user, "User", "Client or lawyer")

    Container_Boundary(c1, "Legal Rent AI") {
        Container(webApp, "Web application", "React, TypeScript, Vite, MUI", "Dashboard, contracts, analysis, chat")
        Container(api, "API Backend", "Python, FastAPI", "REST under backend/")
        ContainerDb(database, "Database", "SQL Server LegalRentAI", "Relational data and PDF/DOCX binaries")
        Container(fileStorage, "Local storage", "backend/storage", "PDF reports and LLM traces")
        Container(vectorDb, "Vector database", "ChromaDB or Azure AI Search", "Future RAG")
    }

    System_Ext(llm, "LLM provider", "OpenAI, Anthropic, Azure OpenAI via LiteLLM")
    System_Ext(email, "Email", "ACS Email, SMTP or dev mode")
    System_Ext(legalCorpus, "CAG corpus", "docs/legal-sources/cag-corpus-v1.md")

    Rel(user, webApp, "HTTPS", "3000")
    Rel(webApp, api, "JSON JWT", "8000")
    Rel(api, database, "pyodbc", "SQL")
    Rel(api, fileStorage, "Filesystem", "reports and llm-runs")
    Rel(api, legalCorpus, "Reads markdown", "REPO_ROOT")
    Rel(api, llm, "Completions", "HTTPS")
    Rel(api, email, "Notifications and signing coordination", "HTTPS/SMTP")
    Rel(api, vectorDb, "Embeddings", "planned")
```

## Diagram — Current state (September 2026)

```mermaid
C4Container
    title Implemented containers

    Person(user, "User", "client or lawyer")

    Container_Boundary(c1, "Monorepo") {
        Container(webApp, "frontend/", "React 19, Vite, MUI", "Upload, analysis, chat SSE, closure, signing schedule")
        Container(api, "backend/", "FastAPI", "Auth, contracts, analysis, chat, signing agent, guardrails, CAG")
        ContainerDb(database, "SQL Server", "LegalRentAI app.*", "23 tables")
        Container(localStore, "backend/storage", "Disk", "Reports and LLM JSON")
    }

    System_Ext(llm, "LLM", "LiteLLM multi-provider")

    Rel(user, webApp, "Uses", ":3000")
    Rel(webApp, api, "REST + SSE", ":8000")
    Rel(api, database, "Read/Write", "SQL")
    Rel(api, localStore, "Writes reports", "FS")
    Rel(api, llm, "Analysis and chat", "API")
```

## Container descriptions

### Web application (`frontend/`)

| Attribute | Value |
|----------|-------|
| Stack | React 19, TypeScript, Vite, Material UI |
| Dev port | 3000 (`VITE_API_URL` → backend) |
| Status | ✅ Dashboard, contracts, analysis, chat, comparisons, closure, `/schedule-signing` |

### API Backend (`backend/`)

| Attribute | Value |
|----------|-------|
| Stack | Python 3.11+, FastAPI, Uvicorn |
| Dev port | 8000 |
| Entry | `run_backend.py` (root) or `backend/run_backend.py` |
| Status | ✅ Functional MVP: see [api.md](../api.md) |

### Database

| Attribute | Value |
|----------|-------|
| Engine | SQL Server 2019+ / Azure SQL |
| Schema | `[app]`, 23 tables |
| Documents | `VARBINARY(MAX)` in row (no Blob in dev) |

### File storage

| Environment | Usage |
|---------|-----|
| Dev | Reports in `backend/storage/reports/`; contracts in SQL |
| Prod (target) | Azure Blob for high-volume artifacts |

### Legal corpus (CAG)

Curated markdown in `docs/legal-sources/cag-corpus-v1.md`, loaded by `backend/rag/cag_corpus.py` (no vector index in the current MVP).

### Vector database

📋 Planned (ChromaDB / Azure AI Search). Current legal grounding is **cache-augmented generation** with a static corpus.

## Communication

| Source | Destination | Protocol |
|--------|---------|-----------|
| SPA | API | HTTPS JSON + SSE (chat) |
| API | SQL Server | TDS / pyodbc |
| API | LLM | HTTPS (OpenAI, Anthropic, etc.) |
| API | Email | ACS Email (`AZURE_COMMUNICATION_*`) or SMTP; log if `NOTIFICATION_DEV_MODE=true` |

### Docker Compose (development)

| Container | Role |
|------------|-----|
| `api` | Image `docker/backend/Dockerfile` |
| `web` | nginx + proxy `/api` → API (SSE chat) |
| `sqlserver` + `db-init` | SQL Server 2022 + scripts in `docs/database/` |

Guide: [deployment/docker.md](../deployment/docker.md).

## Azure deployment (LIDR)

Implemented via **`scripts/azure/deploy-lidr.ps1`**: ACR, Azure SQL, Container Apps (`legalrent-lidr-api`, `legalrent-lidr-web`). Resources and ACS tests: [deployment/azure-resources.md](../deployment/azure-resources.md).

Extended target: Key Vault for secrets, dedicated Azure OpenAI, Blob for high-volume artifacts.
