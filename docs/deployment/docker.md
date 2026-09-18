# Docker — desarrollo local

**Diagrama de arquitectura:** [docker-architecture.md](./docker-architecture.md) (contenedores, red, volúmenes y flujo `/api`).

Tres contenedores de aplicación + SQL Server para paridad con despliegue en Azure (API y web en contenedores; BD gestionada en la nube).

| Servicio | Imagen | Rol |
|----------|--------|-----|
| `api` | `docker/backend/Dockerfile` | FastAPI + capa **AI** (`backend/ai/`) en el mismo proceso |
| `web` | `docker/frontend/Dockerfile` | React (build) + nginx; proxy `/api` → `api:8000` |
| `sqlserver` | Microsoft SQL Server 2022 | Solo local; en Azure usar **Azure SQL** |
| `db-init` | Imagen `mssql/server:2022` (job, `sqlcmd`) | DDL + seed + migraciones |

**Stack en la imagen `api`:** Python 3.11, FastAPI/Uvicorn, pyodbc + ODBC Driver 18, procesamiento PDF/DOCX (PyPDF2, pdfplumber, python-docx, Pillow), Tesseract (pytesseract; OCR desactivado en MVP), LLM in-process (OpenAI/Anthropic/LiteLLM/LangGraph), corpus CAG (`cag-corpus-v1.md`). No se instala el extra `[rag]` (Chroma/torch).

**Stack en `web`:** Node 20, React 19 + Vite 6 + MUI → build estático servido por nginx (proxy `/api` con soporte SSE para chat).

## Requisitos

- Docker Desktop (Windows) con Linux containers
- Archivo `.env.docker` (copiar desde `.env.docker.example`)

### Datos de Docker en `D:\Docker files` (Windows)

Imágenes, capas y el disco virtual (`.vhdx`) **no** van al repo; por defecto ocupan **C:**. Para usar **D:\Docker files**:

```powershell
.\scripts\docker\configure-docker-data-dir.ps1
```

Luego abre **Docker Desktop** y espera a que el motor esté listo. Verifica en el Explorador que aparezca `D:\Docker files\wsl\disk\docker_data.vhdx` tras el primer arranque.

Alternativa manual: Docker Desktop → **Settings** → **Resources** → **Advanced** → **Disk image location** → `D:\Docker files\wsl`.

### Proyecto en Dropbox (Windows)

Docker falla con `invalid file request backend/main.py` si los archivos son *online-only* (reparse points). Opciones:

1. **Recomendado:** carpeta del repo → *Make available offline* / *Conservar siempre en este dispositivo*.
2. **Script:** copia el repo a `%TEMP%` y construye desde ahí:

```powershell
.\scripts\docker\docker-up.ps1
```

(Equivalente a `docker compose up --build` con contexto local real.)

## Arranque

```powershell
copy .env.docker.example .env.docker
# Editar .env.docker: MSSQL_SA_PASSWORD, DB_PASSWORD (misma clave), OPENAI_API_KEY, SECRET_KEY

docker compose up --build
```

El primer build del **api** puede tardar varios minutos. La web (**http://localhost:8080**) solo responde cuando en la terminal veas contenedores `legalrent-api` y `legalrent-web` en marcha (no solo el build de `#26 pip install`).

`DB_PASSWORD` debe coincidir con `MSSQL_SA_PASSWORD` (usuario `sa`).

- UI: http://localhost:8080  
- API directa (Swagger): http://localhost:8000/docs  
- Health: http://localhost:8000/health  

Usuarios demo: ver [README raíz](../../README.md#cuentas-de-prueba-desarrollo-local).

## Capa de IA

La lógica LLM, guardrails, CAG y agentes vive bajo `backend/llm/`, `guardrails/`, `rag/`, `agents/`. Los servicios solo usan **`AIRuntime`** (`backend/ai/runtime.py`). Diagrama de alto nivel: [ai-runtime-and-litellm.md](../architecture/ai-runtime-and-litellm.md).

## Variables importantes

| Variable | En compose |
|----------|------------|
| `DB_SERVER` | `sqlserver` (override en servicio `api`) |
| `DB_TRUSTED_CONNECTION` | `false` + `sa` / `MSSQL_SA_PASSWORD` |
| `VITE_API_URL` | `/api` en build del frontend (mismo origen vía nginx) |
| `FRONTEND_BASE_URL` | `http://localhost:8080` para enlaces de firma |

**LLM / secretos:** el servicio `api` carga `.env.docker` y después **`.env`** (si existe). Pon `OPENAI_API_KEY` en `.env.docker` o en tu `.env` local; no dejes el placeholder `your-openai-api-key`. Tras cambiar la clave: `docker compose up -d --force-recreate api`.

Modo sin API externa: `LLM_PROVIDER=heuristic` en `.env.docker`.

## Volúmenes

- `sqlserver_data`: datos de SQL Server
- `api_storage`: reportes y trazas LLM (`backend/storage/`)

## Reiniciar solo la base

```powershell
docker compose down -v
docker compose up --build
```

## Azure

Despliegue automatizado en el grupo `lidr`: `scripts/azure/deploy-lidr.ps1` (ACR, Azure SQL, Container Apps). Ver [azure-resources.md](./azure-resources.md).
