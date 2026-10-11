# Architecture — Legal Rent AI

**C4** documentation (Context, Containers, Components, Code) for the MVP.

**Repository:** monorepo with `backend/` (FastAPI) and `frontend/` (React).

## C4 levels

| Level | Document | Content |
|-------|-----------|-----------|
| 1 | [Context](./c4-level1-system-context.md) | Actors, external systems, scope |
| 2 | [Containers](./c4-level2-containers.md) | SPA, API, SQL Server, storage, LLM |
| 3 | [Components](./c4-level3-components.md) | `backend/` and `frontend/src` modules |
| 4 | [Code — Auth](./c4-level4-code-auth.md) | Classes in `backend/auth/` |
| — | [AI, agents, and LiteLLM](./ai-runtime-and-litellm.md) | AIRuntime, LLM registry, LangGraph, CAG |

Domain documents:

- [Contracts](../contracts.md) — RF-03–RF-08, closure and edited revision
- [REST API](../api.md) — endpoints (incl. `/public/signing-schedule`)
- [Database](../database/README.md) — `app` schema
- [Deployment](../deployment/docker.md) — local Docker and Azure LIDR

## Legend

| Symbol | Meaning |
|---------|-------------|
| ✅ | Implemented |
| 🚧 | Partial |
| 📋 | Planned |

## Principles

- **Modular monolith** Python in `backend/`; single Uvicorn process.
- **Decoupled SPA** in `frontend/` (`VITE_API_URL`).
- **Domain** in `backend/domain/`; data access in `backend/data/repositories/`.
- **LLM** abstracted in `backend/llm/`; **guardrails** and **CAG** before/after the provider.
- **Single-tenant**, target deployment **Azure**.

## Mermaid visualization

Diagrams use C4 syntax (`C4Context`, `C4Container`, …). Require Mermaid 9.4+; preview in VS Code with Mermaid extension or [mermaid.live](https://mermaid.live).

## References

- [Requirements](../requirements.md)
- [Backend README](../../backend/README.md)
