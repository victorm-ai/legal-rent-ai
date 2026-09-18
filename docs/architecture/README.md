# Arquitectura — Legal Rent AI

Documentación **C4** (Context, Containers, Components, Code) del MVP.

**Repositorio:** monorepo con `backend/` (FastAPI) y `frontend/` (React).

## Niveles C4

| Nivel | Documento | Contenido |
|-------|-----------|-----------|
| 1 | [Contexto](./c4-level1-system-context.md) | Actores, sistemas externos, alcance |
| 2 | [Contenedores](./c4-level2-containers.md) | SPA, API, SQL Server, storage, LLM |
| 3 | [Componentes](./c4-level3-components.md) | Módulos `backend/` y `frontend/src` |
| 4 | [Código — Auth](./c4-level4-code-auth.md) | Clases en `backend/auth/` |
| — | [IA, agentes y LiteLLM](./ai-runtime-and-litellm.md) | AIRuntime, registro LLM, LangGraph, CAG |

Documentos de dominio:

- [Contratos](../contracts.md) — RF-03–RF-08, cierre y revisión editada
- [API REST](../api.md) — endpoints (incl. `/public/signing-schedule`)
- [Base de datos](../database/README.md) — esquema `app`
- [Despliegue](../deployment/docker.md) — Docker local y Azure LIDR

## Leyenda

| Símbolo | Significado |
|---------|-------------|
| ✅ | Implementado |
| 🚧 | Parcial |
| 📋 | Planificado |

## Principios

- **Monolito modular** Python en `backend/`; un proceso Uvicorn.
- **SPA desacoplada** en `frontend/` (`VITE_API_URL`).
- **Dominio** en `backend/domain/`; acceso a datos en `backend/data/repositories/`.
- **LLM** abstracto en `backend/llm/`; **guardrails** y **CAG** antes/después del proveedor.
- **Single-tenant**, despliegue objetivo **Azure**.

## Visualización Mermaid

Diagramas en sintaxis C4 (`C4Context`, `C4Container`, …). Requieren Mermaid 9.4+; revisar en VS Code con extensión Mermaid o [mermaid.live](https://mermaid.live).

## Referencias

- [Requerimientos](../requirements.md)
- [README del backend](../../backend/README.md)
