# C4 — Level 3: Components

Logical modules within the **backend** (`backend/`) and **SPA** (`frontend/src/`).

## Backend — FastAPI components

```mermaid
C4Component
    title Backend components - Legal Rent AI

    Container(spa, "frontend/", "React", "SPA")

    Container_Boundary(apiBoundary, "backend/") {
        Component(apiApp, "api.app", "FastAPI", "CORS, health, routers")
        Component(routes, "api.routes.*", "Python", "auth, contracts, analyses, chat, reports, comparisons, signing_schedule, admin")
        Component(middleware, "api.middleware.auth", "Python", "JWT and RoleChecker")
        Component(services, "services/", "Python", "Contract, Analysis, Chat, Report, Comparison, Retention, Notification, SigningCoordination")
        Component(agents, "agents/signing_coordination", "Python", "LangGraph ReAct post-closure")
        Component(aiRuntime, "ai/", "Python", "AIRuntime LLM and agent facade")
        Component(scheduling, "scheduling/", "Python", "Mon-Fri slots America/Mexico_City")
        Component(repos, "data.repositories", "Python", "SQL Server")
        Component(document, "document/", "Python", "PDF, DOCX, OCR, classifier")
        Component(llm, "llm/", "Python", "Providers, prompts, chat, guarded wrapper")
        Component(guardrails, "guardrails/", "Python", "Lease domain, injection, gateway")
        Component(rag, "rag/", "Python", "CAG markdown corpus")
        Component(observability, "observability/", "Python", "Chat LLM tracker")
        Component(report, "report/", "Python", "PDF generator")
        Component(notification, "notification/", "Python", "Email sender")
        Component(authMod, "auth/", "Python", "Login, JWT, passwords")

        Rel(apiApp, routes, "include_router")
        Rel(routes, middleware, "Depends")
        Rel(routes, services, "Orchestrates")
        Rel(services, repos, "Persists")
        Rel(services, document, "Extracts text")
        Rel(services, llm, "Analysis and chat")
        Rel(llm, guardrails, "GuardedLLMProvider")
        Rel(llm, rag, "CAG system prompts")
        Rel(services, report, "RF-46")
        Rel(services, notification, "RF-50 and signing emails")
        Rel(services, agents, "approved to terminated")
        Rel(agents, aiRuntime, "LLM tools")
        Rel(agents, scheduling, "Lawyer availability")
        Rel(authMod, repos, "UserRepository")
    }

    Rel(spa, routes, "HTTPS JSON/SSE", "8000")
```

## Frontend — React components

```mermaid
C4Component
    title Frontend components

    Container_Boundary(web, "frontend/src") {
        Component(app, "App.tsx", "React", "Routes and MUI theme")
        Component(authCtx, "AuthContext", "React", "JWT in localStorage")
        Component(dashboard, "Dashboard", "React", "Contract list and actions")
        Component(upload, "UploadContractDialog", "React", "Multipart upload")
        Component(analysis, "AnalysisResultsDialog", "React", "Findings and risks")
        Component(chat, "Chat UI", "React", "SSE stream")
        Component(revision, "RevisionComparisonDialog", "React", "Original vs edited")
        Component(lawyerComms, "LawyerCommunicationDialog", "React", "Messages and notifications")
        Component(closure, "ContractClosureDialog", "React", "Closure approved to terminated")
        Component(signingPage, "ScheduleSigningPage", "React", "Public route schedule-signing")
        Component(apiSvc, "services/api", "TypeScript", "HTTP client")
    }

    Rel(app, authCtx, "Provider")
    Rel(dashboard, upload, "Opens dialogs")
    Rel(dashboard, analysis, "Analyze")
    Rel(analysis, apiSvc, "POST analyses")
    Rel(chat, apiSvc, "POST messages/stream")
```

## Folder → responsibility map

| Folder (`backend/`) | Status | Notes |
|----------------------|--------|--------|
| `api/` | ✅ | Routes mounted in `create_router()` |
| `auth/` | ✅ | Roles `lawyer`, `client` |
| `services/` | ✅ | Main use cases |
| `data/` | ✅ | pyodbc repositories |
| `domain/` | ✅ | Enums and entities |
| `document/` | ✅ | Extraction and classification |
| `llm/` | ✅ | Multi-provider + chat |
| `guardrails/` | ✅ | Gateway before LLM |
| `rag/` | ✅ | CAG (no vector DB) |
| `observability/` | ✅ | Chat events → DB |
| `report/` | ✅ | PDF/JSON |
| `notification/` | ✅ | ACS Email, SMTP, dev log |
| `agents/signing_coordination/` | ✅ | Post-`terminated` agent |
| `scheduling/` | ✅ | Simulated slots |
| `ai/` | ✅ | Single facade for services |
| `analysis/` | 🚧 | Reserved package; logic in `services/analysis_service.py` |
| `frontend/src/components/contracts/` | ✅ | MVP flows + closure |
| `frontend/src/components/signing/` | ✅ | Public schedule with token |
| `evals/` (repo root) | ✅ | Offline regression/judge (`python -m evals`) |

## Analysis flow (implemented)

```mermaid
C4Dynamic
    title Contract analysis

    Person(cliente, "Client", "client role")
    Container(webApp, "SPA", "React", "")
    Container_Boundary(be, "backend") {
        Component(contractSvc, "ContractService", "", "Upload and text")
        Component(analysisSvc, "AnalysisService", "", "Pipeline")
        Component(llm, "LLM + Guardrails + CAG", "", "")
    }
    ContainerDb(db, "SQL Server", "", "")

    Rel(cliente, webApp, "1. Upload and Analyze")
    Rel(webApp, contractSvc, "2. POST /contracts, /analyses")
    Rel(contractSvc, db, "3. Persists document")
    Rel(analysisSvc, llm, "4. Extract, clauses, findings")
    Rel(analysisSvc, db, "5. Saves analysis")
    Rel(webApp, cliente, "6. Shows results")
```

## Layer dependencies

```
api/routes  →  services/  →  domain/
                 ↓
    document/ | llm/ | guardrails/ | rag/ | report/ | notification/
                 ↓
              data/repositories  →  SQL Server
```

`domain/` does not import infrastructure. Configuration: `backend/config/settings.py` (`REPO_ROOT`, `BACKEND_ROOT`).
