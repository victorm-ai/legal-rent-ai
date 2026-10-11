# Backend — Legal Rent AI

REST API in **Python 3.11+**, **FastAPI**, and **Uvicorn**. Code lives under `backend/`; configuration (`.env`) is at the **repository root**.

## Startup

From the monorepo root:

```bash
pip install -e "."
python run_backend.py
```

Or from this folder:

```bash
uvicorn api.app:app --reload --host 0.0.0.0 --port 8000
```

- Health: `http://localhost:8000/health`
- Swagger: `http://localhost:8000/docs`

## Structure

| Folder | Responsibility |
|---------|-----------------|
| `api/` | FastAPI routes, JWT middleware, Pydantic schemas |
| `auth/` | Login, registration, JWT, download and signing schedule tokens |
| `services/` | Use cases (contracts, analysis, chat, reports, retention, signing coordination, …) |
| `agents/signing_coordination/` | LangGraph ReAct agent after `approved→terminated` closure |
| `scheduling/` | Slot generation (Mon–Fri, `America/Mexico_City`) |
| `data/` | DTOs and SQL Server repositories (pyodbc) |
| `domain/` | Domain entities and enums |
| `document/` | PDF/DOCX, OCR, annex classification |
| `ai/` | `AIRuntime` facade (analysis, chat, agents); services depend on this |
| `llm/` | LLM providers (`openai`, `anthropic`, `azure`, `local`, `heuristic`) |
| `guardrails/` | Lease domain, anti-injection, gateway |
| `rag/` | Legal CAG corpus (`docs/legal-sources/cag-corpus-v1.md`) |
| `observability/` | LLM call traces and costs in chat |
| `report/` | PDF/JSON report generation |
| `notification/` | ACS Email, SMTP fallback, dev mode (`NOTIFICATION_DEV_MODE`) |
| `storage/` | Runtime files (reports, LLM responses) |
| `config/` | `settings.py` (`REPO_ROOT` + `BACKEND_ROOT`) |

## Configuration

Variables in `.env` at the repo root (see `.env.example`). Relative paths:

- Legal corpus and docs → resolved against `REPO_ROOT`
- `storage/reports`, `storage/llm-runs` → under `backend/storage/`

Notable integration settings:

- `LLM_PROVIDER`, OpenAI/Anthropic/Azure keys
- `AZURE_COMMUNICATION_*` — signing coordination email
- `FRONTEND_BASE_URL` — `/schedule-signing?token=` links
- `ANALYSIS_ASYNC`, `LEGAL_CAG_*`, `GUARDRAILS_*`

## Offline evaluation

The `evals/` package (repo root) is not part of the API process:

```bash
python -m evals --help
```

## Tests

```bash
# from repo root
pytest tests/unit
pytest tests/integration
```

## Documentation

- [REST API](../docs/api.md)
- [AI, agents, and LiteLLM](../docs/architecture/ai-runtime-and-litellm.md)
- [Docker architecture](../docs/deployment/docker-architecture.md)
- [Database](../docs/database/README.md)
- [C4 architecture](../docs/architecture/README.md)
- [Scripts](../scripts/README.md)
