# Backend — Legal Rent AI

API REST en **Python 3.11+**, **FastAPI** y **Uvicorn**. Código bajo `backend/`; la configuración (`.env`) vive en la **raíz del repositorio**.

## Arranque

Desde la raíz del monorepo:

```bash
pip install -e "."
python run_backend.py
```

O desde esta carpeta:

```bash
uvicorn api.app:app --reload --host 0.0.0.0 --port 8000
```

- Health: `http://localhost:8000/health`
- Swagger: `http://localhost:8000/docs`

## Estructura

| Carpeta | Responsabilidad |
|---------|-----------------|
| `api/` | Rutas FastAPI, middleware JWT, schemas Pydantic |
| `auth/` | Login, registro, JWT, tokens de descarga y agenda de firma |
| `services/` | Casos de uso (contratos, análisis, chat, reportes, retención, coordinación de firma, …) |
| `agents/signing_coordination/` | Agente LangGraph ReAct tras cierre `approved→terminated` |
| `scheduling/` | Generación de slots (Lun–Vie, `America/Mexico_City`) |
| `data/` | DTOs y repositorios SQL Server (pyodbc) |
| `domain/` | Entidades y enums de dominio |
| `document/` | PDF/DOCX, OCR, clasificación de anexos |
| `ai/` | Fachada `AIRuntime` (análisis, chat, agentes); servicios dependen de aquí |
| `llm/` | Proveedores LLM (`openai`, `anthropic`, `azure`, `local`, `heuristic`) |
| `guardrails/` | Dominio arrendamiento, anti-inyección, gateway |
| `rag/` | Corpus jurídico CAG (`docs/legal-sources/cag-corpus-v1.md`) |
| `observability/` | Trazas y costos de llamadas LLM en chat |
| `report/` | Generación de reportes PDF/JSON |
| `notification/` | ACS Email, SMTP fallback, modo dev (`NOTIFICATION_DEV_MODE`) |
| `storage/` | Archivos en runtime (reportes, respuestas LLM) |
| `config/` | `settings.py` (`REPO_ROOT` + `BACKEND_ROOT`) |

## Configuración

Variables en `.env` en la raíz del repo (ver `.env.example`). Rutas relativas:

- Corpus legal y docs → resueltas contra `REPO_ROOT`
- `storage/reports`, `storage/llm-runs` → bajo `backend/storage/`

Destacadas para integraciones:

- `LLM_PROVIDER`, claves OpenAI/Anthropic/Azure
- `AZURE_COMMUNICATION_*` — correo de coordinación de firma
- `FRONTEND_BASE_URL` — enlaces `/schedule-signing?token=`
- `ANALYSIS_ASYNC`, `LEGAL_CAG_*`, `GUARDRAILS_*`

## Evaluación offline

El paquete `evals/` (raíz del repo) no forma parte del proceso API:

```bash
python -m evals --help
```

## Pruebas

```bash
# desde la raíz del repo
pytest tests/unit
pytest tests/integration
```

## Documentación

- [API REST](../docs/api.md)
- [IA, agentes y LiteLLM](../docs/architecture/ai-runtime-and-litellm.md)
- [Arquitectura Docker](../docs/deployment/docker-architecture.md)
- [Base de datos](../docs/database/README.md)
- [Arquitectura C4](../docs/architecture/README.md)
- [Scripts](../scripts/README.md)
