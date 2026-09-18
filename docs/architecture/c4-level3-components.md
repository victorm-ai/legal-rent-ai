# C4 — Nivel 3: Componentes

Módulos lógicos dentro del **backend** (`backend/`) y la **SPA** (`frontend/src/`).

## Backend — Componentes FastAPI

```mermaid
C4Component
    title Componentes backend - Legal Rent AI

    Container(spa, "frontend/", "React", "SPA")

    Container_Boundary(apiBoundary, "backend/") {
        Component(apiApp, "api.app", "FastAPI", "CORS, health, routers")
        Component(routes, "api.routes.*", "Python", "auth, contracts, analyses, chat, reports, comparisons, signing_schedule, admin")
        Component(middleware, "api.middleware.auth", "Python", "JWT y RoleChecker")
        Component(services, "services/", "Python", "Contract, Analysis, Chat, Report, Comparison, Retention, Notification, SigningCoordination")
        Component(agents, "agents/signing_coordination", "Python", "LangGraph ReAct post-cierre")
        Component(aiRuntime, "ai/", "Python", "AIRuntime fachada LLM y agentes")
        Component(scheduling, "scheduling/", "Python", "Slots Lun-Vie America/Mexico_City")
        Component(repos, "data.repositories", "Python", "SQL Server")
        Component(document, "document/", "Python", "PDF, DOCX, OCR, classifier")
        Component(llm, "llm/", "Python", "Providers, prompts, chat, guarded wrapper")
        Component(guardrails, "guardrails/", "Python", "Lease domain, injection, gateway")
        Component(rag, "rag/", "Python", "CAG corpus markdown")
        Component(observability, "observability/", "Python", "Chat LLM tracker")
        Component(report, "report/", "Python", "PDF generator")
        Component(notification, "notification/", "Python", "Email sender")
        Component(authMod, "auth/", "Python", "Login, JWT, passwords")

        Rel(apiApp, routes, "include_router")
        Rel(routes, middleware, "Depends")
        Rel(routes, services, "Orquesta")
        Rel(services, repos, "Persiste")
        Rel(services, document, "Extrae texto")
        Rel(services, llm, "Analisis y chat")
        Rel(llm, guardrails, "GuardedLLMProvider")
        Rel(llm, rag, "System prompts CAG")
        Rel(services, report, "RF-46")
        Rel(services, notification, "RF-50 y emails firma")
        Rel(services, agents, "approved to terminated")
        Rel(agents, aiRuntime, "LLM tools")
        Rel(agents, scheduling, "Disponibilidad abogado")
        Rel(authMod, repos, "UserRepository")
    }

    Rel(spa, routes, "HTTPS JSON/SSE", "8000")
```

## Frontend — Componentes React

```mermaid
C4Component
    title Componentes frontend

    Container_Boundary(web, "frontend/src") {
        Component(app, "App.tsx", "React", "Rutas y tema MUI")
        Component(authCtx, "AuthContext", "React", "JWT en localStorage")
        Component(dashboard, "Dashboard", "React", "Lista contratos y acciones")
        Component(upload, "UploadContractDialog", "React", "Multipart upload")
        Component(analysis, "AnalysisResultsDialog", "React", "Hallazgos y riesgos")
        Component(chat, "Chat UI", "React", "SSE stream")
        Component(revision, "RevisionComparisonDialog", "React", "Original vs editado")
        Component(lawyerComms, "LawyerCommunicationDialog", "React", "Mensajes y notificaciones")
        Component(closure, "ContractClosureDialog", "React", "Cierre approved to terminated")
        Component(signingPage, "ScheduleSigningPage", "React", "Ruta publica schedule-signing")
        Component(apiSvc, "services/api", "TypeScript", "Cliente HTTP")
    }

    Rel(app, authCtx, "Provider")
    Rel(dashboard, upload, "Abre dialogos")
    Rel(dashboard, analysis, "Analyze")
    Rel(analysis, apiSvc, "POST analyses")
    Rel(chat, apiSvc, "POST messages/stream")
```

## Mapa carpeta → responsabilidad

| Carpeta (`backend/`) | Estado | Notas |
|----------------------|--------|--------|
| `api/` | ✅ | Rutas montadas en `create_router()` |
| `auth/` | ✅ | Roles `lawyer`, `client` |
| `services/` | ✅ | Casos de uso principales |
| `data/` | ✅ | Repositorios pyodbc |
| `domain/` | ✅ | Enums y entidades |
| `document/` | ✅ | Extracción y clasificación |
| `llm/` | ✅ | Multi-proveedor + chat |
| `guardrails/` | ✅ | Gateway previo a LLM |
| `rag/` | ✅ | CAG (sin vector DB) |
| `observability/` | ✅ | Eventos chat → BD |
| `report/` | ✅ | PDF/JSON |
| `notification/` | ✅ | ACS Email, SMTP, dev log |
| `agents/signing_coordination/` | ✅ | Agente post-`terminated` |
| `scheduling/` | ✅ | Slots simulados |
| `ai/` | ✅ | Fachada única para servicios |
| `analysis/` | 🚧 | Paquete reservado; lógica en `services/analysis_service.py` |
| `frontend/src/components/contracts/` | ✅ | Flujos MVP + cierre |
| `frontend/src/components/signing/` | ✅ | Agenda pública con token |
| `evals/` (raíz repo) | ✅ | Regresión/judge offline (`python -m evals`) |

## Flujo de análisis (implementado)

```mermaid
C4Dynamic
    title Analisis contractual

    Person(cliente, "Client", "client role")
    Container(webApp, "SPA", "React", "")
    Container_Boundary(be, "backend") {
        Component(contractSvc, "ContractService", "", "Upload y texto")
        Component(analysisSvc, "AnalysisService", "", "Pipeline")
        Component(llm, "LLM + Guardrails + CAG", "", "")
    }
    ContainerDb(db, "SQL Server", "", "")

    Rel(cliente, webApp, "1. Upload y Analyze")
    Rel(webApp, contractSvc, "2. POST /contracts, /analyses")
    Rel(contractSvc, db, "3. Persiste documento")
    Rel(analysisSvc, llm, "4. Extrae, clausulas, hallazgos")
    Rel(analysisSvc, db, "5. Guarda analisis")
    Rel(webApp, cliente, "6. Muestra resultados")
```

## Dependencias entre capas

```
api/routes  →  services/  →  domain/
                 ↓
    document/ | llm/ | guardrails/ | rag/ | report/ | notification/
                 ↓
              data/repositories  →  SQL Server
```

`domain/` no importa infraestructura. Configuración: `backend/config/settings.py` (`REPO_ROOT`, `BACKEND_ROOT`).
