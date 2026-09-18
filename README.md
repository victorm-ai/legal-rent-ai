# Sistema de Análisis de Contratos de Arrendamiento en México — MVP

Sistema para analizar contratos de arrendamiento inmobiliario en México, con énfasis en Jalisco.

## Guía de uso (aplicación web)

Manual paso a paso para **cliente** y **abogado** (login, carga de contratos, análisis, chat, revisión, cierre y firma):

- **PDF:** [Legal Rent AI Guide.pdf](./docs/guide/Legal%20Rent%20AI%20Guide.pdf)

Entornos habituales: [Docker local](#docker-local) (`http://localhost:8080`) o [Azure (LIDR)](#uso-en-azure-lidr). Usa las [cuentas de prueba](#cuentas-de-prueba-desarrollo-local) de abajo.

## Flujo cliente–abogado (desde la carga del contrato)

Recorrido completo del expediente: carga y análisis IA, colaboración, estados del contrato (`draft` → `in_review` → `approved` → `terminated`) y coordinación de firma tras el cierre.

![Flujo de trabajo cliente y abogado — Legal Rent AI](./docs/cliente-abogado-flujo-contrato.png)

Archivo fuente: [`docs/cliente-abogado-flujo-contrato.png`](./docs/cliente-abogado-flujo-contrato.png). Detalle funcional en [`docs/requirements.md`](./docs/requirements.md#5-flujo-principal-completado) y [`docs/api.md`](./docs/api.md).

## Características del MVP

- Carga y extracción de texto de PDFs y DOCX
- OCR para documentos escaneados
- Extracción estructurada de información contractual
- Análisis de cláusulas y detección de riesgos
- Corpus legal autorizado (CAG) en prompts; RAG vectorial planificado
- Chat contextual con el contrato
- Generación de reportes
- Notificaciones por correo al abogado (ACS Email / SMTP / modo dev)
- Coordinación de firma tras cierre del expediente (agente + agenda pública con token)

## Requisitos

- Python 3.11+
- Azure OpenAI o proveedor LLM compatible
- SQL Server 2019+ (local o Azure SQL) — ver [docs/database](./docs/database/README.md)

## Instalación

```bash
# Crear entorno virtual
python -m venv venv

# Activar entorno virtual
venv\Scripts\activate  # En Windows

# Instalar dependencias
pip install -e "."
```

## Estructura del Proyecto

```
├── backend/             # API Python (FastAPI) y servicios
│   ├── api/             # Rutas REST
│   ├── auth/            # Autenticación (RF-01)
│   ├── services/        # Casos de uso
│   ├── llm/             # Proveedores LLM, prompts, chat
│   ├── guardrails/      # Validación de dominio e inyección
│   ├── rag/             # Corpus jurídico (CAG)
│   ├── storage/         # Reportes y trazas LLM en runtime
│   └── run_backend.py   # Arranque uvicorn (desde backend/)
├── frontend/            # React + Vite + Material UI
├── docker/              # Dockerfiles e init de BD para Compose
├── docs/                # Documentación (español); incluye guide/ (PDF de usuario)
├── evals/               # Evaluación offline del análisis LLM (`python -m evals`)
├── tests/               # Pruebas (unit, integration, smoke, load)
├── scripts/             # Utilidades; ver scripts/README.md
├── fixtures/            # Contratos de ejemplo (`sample-contracts/`)
├── docker-compose.yml   # Stack local api + web + SQL Server
├── run_backend.py       # Wrapper: inicia backend desde la raíz
└── pyproject.toml       # Dependencias (`pip install -e .`)
```

### Ejecutar pruebas

```bash
pytest                    # suite completa bajo tests/
pytest tests/unit         # pruebas sin BD (cuando aplique)
python tests/smoke/auth_quick.py
```

## Documentación

Índice central: [`docs/README.md`](./docs/README.md).

| Tema | Enlace |
|------|--------|
| **Uso de la aplicación web** | [docs/guide/README.md](./docs/guide/README.md) · [PDF](./docs/guide/Legal%20Rent%20AI%20Guide.pdf) |
| Backend (código) | [backend/README.md](./backend/README.md) |
| Frontend | [frontend/README.md](./frontend/README.md) |
| Scripts | [scripts/README.md](./scripts/README.md) |
| API REST | [docs/api.md](./docs/api.md) |
| Docker / Azure | [docs/deployment/docker.md](./docs/deployment/docker.md) |
| Arquitectura Docker | [docs/deployment/docker-architecture.md](./docs/deployment/docker-architecture.md) |
| IA, agentes y LiteLLM | [docs/architecture/ai-runtime-and-litellm.md](./docs/architecture/ai-runtime-and-litellm.md) |
| Base de datos | [docs/database/README.md](./docs/database/README.md) |
| Arquitectura C4 | [docs/architecture/README.md](./docs/architecture/README.md) |
| Requerimientos | [docs/requirements.md](./docs/requirements.md) |
| Autenticación | [docs/authentication.md](./docs/authentication.md) |
| Contratos | [docs/contracts.md](./docs/contracts.md) |

## Política de idiomas

| Ámbito | Idioma |
|--------|--------|
| Código fuente | Inglés |
| Documentación (`docs/`, este README) | Español |
| Interfaz web (`frontend/`) | Inglés |
| API (mensajes y roles) | Inglés |

Los roles de usuario en la API usan los valores `lawyer` y `client`.

## Configuración

Copia el archivo `.env.example` a `.env` y configura tus variables:

```bash
copy .env.example .env
```

**Proveedor LLM (LiteLLM):** por defecto `LLM_PROVIDER=openai` con `OPENAI_API_KEY`. Para Anthropic, define `LLM_PROVIDER=anthropic`, `ANTHROPIC_API_KEY` y opcionalmente `ANTHROPIC_MODEL` (p. ej. `claude-3-5-haiku-20241022`). Análisis y chat usan el mismo proveedor configurado. El chat en la UI consume `POST /chat/sessions/{id}/messages/stream` (SSE) para mostrar la respuesta en tiempo real.

## Docker (local)

Tres contenedores (`api`, `web`, `sqlserver`) + job de inicialización de BD.

- Guía operativa: [docs/deployment/docker.md](./docs/deployment/docker.md)
- **Diagrama de arquitectura** (ASCII + Mermaid; Mermaid requiere preview GitHub/VS Code): [docs/deployment/docker-architecture.md](./docs/deployment/docker-architecture.md)

## Capa de IA (AIRuntime + LiteLLM)

Análisis, chat SSE y agente LangGraph de coordinación de firma pasan por **`AIRuntime`** y el registro de proveedores en `backend/llm/`, con abstracción unificada en `litellm_runtime` (OpenAI / Anthropic / Azure / heurístico).

**Diagrama de alto nivel** (ASCII + Mermaid): [docs/architecture/ai-runtime-and-litellm.md](./docs/architecture/ai-runtime-and-litellm.md)

En Windows, para guardar imágenes y disco virtual en **D:\Docker files** (no en C:):

```powershell
.\scripts\docker\configure-docker-data-dir.ps1
# Abrir Docker Desktop y esperar a que esté listo
```

```powershell
copy .env.docker.example .env.docker
# Ajustar MSSQL_SA_PASSWORD y DB_PASSWORD (mismo valor), OPENAI_API_KEY, SECRET_KEY
# Si el repo está en Dropbox (Windows): .\scripts\docker\docker-up.ps1
docker compose up --build
```

UI: http://localhost:8080 — API: http://localhost:8000/docs

## Uso en Azure (LIDR)

Despliegue en el grupo de recursos **`lidr`** (Container Apps + Azure SQL). La SPA llama a la API vía **`/api`** en el mismo origen (equivalente a Docker/nginx).

| Recurso | URL |
|--------|-----|
| **Aplicación web** (login, dashboard) | https://legalrent-lidr-web.ashyhill-93ea1614.eastus2.azurecontainerapps.io |
| **API REST** | https://legalrent-lidr-api.ashyhill-93ea1614.eastus2.azurecontainerapps.io |
| **Swagger** | https://legalrent-lidr-api.ashyhill-93ea1614.eastus2.azurecontainerapps.io/docs |
| **Health** | https://legalrent-lidr-api.ashyhill-93ea1614.eastus2.azurecontainerapps.io/health |

Agenda de firma pública (enlace con token del correo post-cierre):  
`https://legalrent-lidr-web.ashyhill-93ea1614.eastus2.azurecontainerapps.io/schedule-signing?token=…`

**Cuentas de prueba** (usuarios demo de `docs/database/seed.sql`; mismas credenciales que en local si la BD Azure se inicializó con el script de deploy):

| Email | Contraseña | Rol (API) |
|-------|------------|-----------|
| `abogado@contractes.com` | `abogado123` | `lawyer` |
| `code.zemoreno@gmail.com` | `cliente123` | `client` |

Flujo recomendado: entrar como **cliente**, subir un contrato y analizar; luego **abogado** para revisión, cierre o export de feedback.

Documentación de infraestructura: [docs/deployment/azure-resources.md](./docs/deployment/azure-resources.md). Redespliegue: `scripts/azure/deploy-lidr.ps1`.

## Iniciar el Backend

```bash
# Opción 1: Usar el script helper
python run_backend.py

# Opción 2: Directamente con uvicorn (desde backend/)
cd backend
uvicorn api.app:app --reload --host 0.0.0.0 --port 8000

# Verificar que funciona:
# http://localhost:8000/health
# http://localhost:8000/docs (Swagger UI)
```

## Iniciar el Frontend

Requisitos: **Node.js 18+** y npm.

```bash
# Opción 1: Windows
start_frontend.bat

# Opción 2: Manual
cd frontend
npm install
npm run dev

# Abrir en tu navegador:
# http://localhost:3000
```

Stack del frontend: **React 19**, **TypeScript**, **Vite** y **Material UI (MUI)**.

Para apuntar a un backend distinto, crea `frontend/.env.local`:

```bash
VITE_API_URL=http://localhost:8000
```

## Cuentas de prueba (desarrollo local)

Mismas credenciales que en Azure (ver tabla anterior). Válidas tras ejecutar `setup_database.bat` o el seed en Docker/Azure.

| Email | Contraseña | Rol (API) |
|-------|------------|-----------|
| `abogado@contractes.com` | `abogado123` | `lawyer` |
| `code.zemoreno@gmail.com` | `cliente123` | `client` |

## Sistema de Colores

El proyecto utiliza un sistema de colores consistente:

- **Primary**: Indigo (#4f46e5) - Para acciones primarias
- **Success**: Emerald (#10b981) - Para estados positivos
- **Warning**: Amber (#f59e0b) - Para alertas
- **Danger**: Red (#ef4444) - Para errores y riesgos altos

## Características de la Interfaz

- Diseño responsive (móvil, tablet, desktop)
- Tema limpio y profesional con sombras suaves
- Feedback visual para estados de carga y errores
- Persistentencia de sesión con localStorage
- UI moderna con gradientes sutiles

## API

Documentación completa: [`docs/api.md`](./docs/api.md). Swagger: `http://localhost:8000/docs`.

Incluye contratos, análisis IA, chat (SSE), reportes, comparaciones, revisión abogado, notificaciones, cierre del expediente y agenda de firma pública (`/public/signing-schedule`).

### Evaluación offline del análisis LLM

```bash
python -m evals --mode regression
```

Casos y baselines en `evals/`; no expone endpoints HTTP.
