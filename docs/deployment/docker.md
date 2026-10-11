# Docker — local development

**Architecture diagram:** [docker-architecture.md](./docker-architecture.md) (containers, network, volumes, and `/api` flow).

Three application containers + SQL Server for parity with Azure deployment (API and web in containers; managed DB in the cloud).

| Service | Image | Role |
|----------|--------|-----|
| `api` | `docker/backend/Dockerfile` | FastAPI + **AI** layer (`backend/ai/`) in the same process |
| `web` | `docker/frontend/Dockerfile` | React (build) + nginx; proxy `/api` → `api:8000` |
| `sqlserver` | Microsoft SQL Server 2022 | Local only; use **Azure SQL** in Azure |
| `db-init` | Image `mssql/server:2022` (job, `sqlcmd`) | DDL + seed + migrations |

**Stack in the `api` image:** Python 3.11, FastAPI/Uvicorn, pyodbc + ODBC Driver 18, PDF/DOCX processing (PyPDF2, pdfplumber, python-docx, Pillow), Tesseract (pytesseract; OCR disabled in MVP), in-process LLM (OpenAI/Anthropic/LiteLLM/LangGraph), CAG corpus (`cag-corpus-v1.md`). The `[rag]` extra (Chroma/torch) is not installed.

**Stack in `web`:** Node 20, React 19 + Vite 6 + MUI → static build served by nginx (proxy `/api` with SSE support for chat).

## Requirements

- Docker Desktop (Windows) with Linux containers
- `.env.docker` file (copy from `.env.docker.example`)

### Docker data on `D:\Docker files` (Windows)

Images, layers, and the virtual disk (`.vhdx`) **do not** live in the repo; by default they use **C:**. To use **D:\Docker files**:

```powershell
.\scripts\docker\configure-docker-data-dir.ps1
```

Then open **Docker Desktop** and wait until the engine is ready. Verify in Explorer that `D:\Docker files\wsl\disk\docker_data.vhdx` appears after the first start.

Manual alternative: Docker Desktop → **Settings** → **Resources** → **Advanced** → **Disk image location** → `D:\Docker files\wsl`.

### Project on Dropbox (Windows)

Docker fails with `invalid file request backend/main.py` if files are *online-only* (reparse points). Options:

1. **Recommended:** repo folder → *Make available offline* / *Always keep on this device*.
2. **Script:** copies the repo to `%TEMP%` and builds from there:

```powershell
.\scripts\docker\docker-up.ps1
```

(Equivalent to `docker compose up --build` with a real local context.)

## Startup

```powershell
copy .env.docker.example .env.docker
# Edit .env.docker: MSSQL_SA_PASSWORD, DB_PASSWORD (same value), OPENAI_API_KEY, SECRET_KEY

docker compose up --build
```

The first **api** build may take several minutes. The web UI (**http://localhost:8080**) only responds when you see `legalrent-api` and `legalrent-web` containers running in the terminal (not only the `#26 pip install` build step).

`DB_PASSWORD` must match `MSSQL_SA_PASSWORD` (`sa` user).

- UI: http://localhost:8080  
- API direct (Swagger): http://localhost:8000/docs  
- Health: http://localhost:8000/health  

Demo users: see [root README](../../README.md#cuentas-de-prueba-desarrollo-local).

## AI layer

LLM logic, guardrails, CAG, and agents live under `backend/llm/`, `guardrails/`, `rag/`, `agents/`. Services only use **`AIRuntime`** (`backend/ai/runtime.py`). High-level diagram: [ai-runtime-and-litellm.md](../architecture/ai-runtime-and-litellm.md).

## Important variables

| Variable | In compose |
|----------|------------|
| `DB_SERVER` | `sqlserver` (override on `api` service) |
| `DB_TRUSTED_CONNECTION` | `false` + `sa` / `MSSQL_SA_PASSWORD` |
| `VITE_API_URL` | `/api` in frontend build (same origin via nginx) |
| `FRONTEND_BASE_URL` | `http://localhost:8080` for signing links |

**LLM / secrets:** the `api` service loads `.env.docker` then **`.env`** (if present). Put `OPENAI_API_KEY` in `.env.docker` or your local `.env`; do not leave the `your-openai-api-key` placeholder. After changing the key: `docker compose up -d --force-recreate api`.

Mode without external API: `LLM_PROVIDER=heuristic` in `.env.docker`.

## Volumes

- `sqlserver_data`: SQL Server data
- `api_storage`: reports and LLM traces (`backend/storage/`)

## Reset database only

```powershell
docker compose down -v
docker compose up --build
```

## Azure

Automated deployment in group `lidr`: `scripts/azure/deploy-lidr.ps1` (ACR, Azure SQL, Container Apps). See [azure-resources.md](./azure-resources.md).
