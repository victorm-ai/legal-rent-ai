# REST API — Legal Rent AI

MVP API specification. Prose in English; **routes, JSON fields, and error messages remain in English** (code convention).

**Code:** `backend/api/`. **Live reference:** Swagger at `http://localhost:8000/docs`.

## Table of contents

1. [General information](#general-information)
2. [Authentication and roles](#authentication-and-roles)
3. [Conventions](#conventions)
4. [Summary of implemented endpoints](#summary-of-implemented-endpoints)
5. [Detail by module](#detail-by-module)
6. [Planned endpoints](#planned-endpoints)
7. [Models and enums](#models-and-enums)
8. [Role matrix](#role-matrix)
9. [Error codes](#error-codes)
10. [Cross-reference](#cross-reference)

---

## General information

| Attribute | Value |
|----------|-------|
| Base URL (dev) | `http://localhost:8000` |
| Format | JSON (`Content-Type: application/json`) |
| Uploads | `multipart/form-data` |
| Authentication | JWT Bearer (except `/health`, `/auth/login`, `/auth/register`, `/public/signing-schedule*` with token in query) |
| Framework | FastAPI 0.104+ |
| API version | `0.1.0` |
| Startup | `python run_backend.py` (repo root) or `uvicorn api.app:app` from `backend/` |

### Headers

| Header | Required | Description |
|----------|-------------|-------------|
| `Authorization` | Protected routes | `Bearer <access_token>` |
| `Content-Type` | POST/PATCH with body | `application/json` or `multipart/form-data` |

---

## Authentication and roles

JWT flow. Module detail: [authentication.md](./authentication.md).

1. `POST /auth/login` → `access_token`
2. Requests: `Authorization: Bearer <token>`
3. `POST /auth/logout` → client-side sign-out

**Roles in token and DB:** `lawyer`, `client` (no `administrator` role in the current MVP).

Demo users (`seed.sql` / root README):

| Email | Password | Role |
|-------|------------|-----|
| `abogado@contractes.com` | `abogado123` | `lawyer` |
| `code.zemoreno@gmail.com` | `cliente123` | `client` |

### `POST /auth/login`

**Request:**

```json
{
  "email": "code.zemoreno@gmail.com",
  "password": "cliente123"
}
```

**Response 200:** `token_type`, `access_token`, `expires_in_minutes`, `user_id`, `email`, `name`, `role`.

### `POST /auth/register`

Registration with role `client`. Same response shape as login.

### `POST /auth/logout`

Requires Bearer. Response 200: `{ "message": "Signed out successfully" }`.

---

## Conventions

### Identifiers

- UUID (`string`) in production (`UNIQUEIDENTIFIER` in SQL Server).

### Dates

- ISO 8601 UTC, e.g. `"2026-09-16T22:30:00.000Z"`.

### Soft delete (RF-53)

`DELETE /contracts/{id}` sets `is_deleted`; does not remove rows. Listings exclude deleted records per role and ownership.

### Upload

- PDF and DOCX, maximum **25 MB** (HTTP 413 if exceeded).
- File field: `file`.

### Download with token (RNF-21)

`POST .../download-token` issues a URL with a short-lived query `token`; `GET .../download?token=` accepts JWT **or** token.

---

## Summary of implemented endpoints

| Module | Main methods |
|--------|---------------------|
| Health | `GET /health` |
| Auth | `POST /auth/login`, `/register`, `/logout` |
| Contracts | `GET/POST /contracts`, `GET/PATCH/DELETE /contracts/{id}` |
| Documents | `POST /contracts/{id}/documents`, `GET .../documents`, `GET .../download`, `GET .../text`, `POST .../download-token` |
| Parties | `GET /contracts/{id}/parties` |
| Analysis (per contract) | `POST/GET /contracts/{id}/analyses` |
| Analysis (detail) | `GET/PATCH /analyses/{id}`, `GET /analyses/{id}/status` |
| Lawyer review | `POST /analyses/{id}/findings/{finding_id}/review`, `POST /analyses/{id}/approve` |
| Edited revision | `POST /contracts/{id}/lawyer-revision`, `POST/GET .../revision-comparison` |
| Case messages | `GET/POST /contracts/{id}/review-messages`, `POST .../mark-read` |
| Messages per analysis | `GET/POST /analyses/{id}/review-messages` |
| Retention | `GET /contracts/retention-policy` |
| Chat | `POST/GET /contracts/{id}/chat/sessions`, `POST/GET /chat/sessions/{id}/messages`, **`POST .../messages/stream` (SSE)**, `GET .../suggestions` |
| Reports | `POST/GET /analyses/{id}/reports`, `GET /reports/{id}/download` |
| Notifications | `POST/GET /analyses/{id}/notifications` |
| Comparisons | `POST /comparisons`, `GET /comparisons/{id}` |
| Admin / feedback | `GET /admin/feedback/export` (lawyer) |
| Public signing schedule | `GET/POST /public/signing-schedule` (JWT in query `token`, no SPA login) |

---

## Detail by module

### Health

#### `GET /health`

No authentication. Response: `status`, `service`, `version`.

---

### Contracts — `/contracts`

| Method | Route | Notes |
|--------|------|--------|
| `GET` | `/contracts` | List; `lawyer` sees assigned clients’ contracts / expanded visibility per service |
| `POST` | `/contracts` | Multipart: `file`, `perspective` (`tenant` in MVP UI), optional `title` |
| `GET` | `/contracts/{id}` | Detail + documents |
| `PATCH` | `/contracts/{id}` | `status`, `title`, `closure_notes` (RF-56) |
| `DELETE` | `/contracts/{id}` | Soft delete (RF-53) |
| `GET` | `/contracts/retention-policy` | Days of retention after deletion (RF-54) |

**`POST /contracts/{id}/documents`:** additional attachment; form `file`, optional `is_signed_version` (RF-57 partial).

**`POST /contracts/{id}/lawyer-revision`:** `lawyer` only; uploads edited DOCX/PDF (`document_type` / scope `lawyer_revision`).

**`POST /contracts/{id}/analyses`:** JSON body with `perspective` and `document_scope` (`original` \| `lawyer_revision`). By default the pipeline is **synchronous** (`ANALYSIS_ASYNC=false`); if `true`, responds 201 with `processing` and the client polls `/analyses/{id}/status`.

**Lifecycle (RF-56):** `PATCH /contracts/{id}` accepts `status`, `title`, `closure_notes`. Typical UI flow:

| Step | Role | Transition |
|------|-----|------------|
| Submit for legal review | `client` | `draft` → `in_review` |
| Approve case | `client` | `in_review` → `approved` |
| Administrative closure | `lawyer` | `approved` → `terminated` (+ `closure_notes` recommended) |

When moving to `terminated`, the backend may run **signing coordination** (LangGraph agent + ACS/SMTP email with link `{FRONTEND_BASE_URL}/schedule-signing?token=...`). If the agent fails, the service reverts the contract status. After `terminated`, the contract is **locked** (`is_contract_locked`).

Reserved model states (`in_signing`, `signed`, `expired`) exist in the DB but are not part of the main SPA flow today.

**Original vs edited comparison:**

- `POST /contracts/{id}/revision-comparison` — may return 202 if revision analysis is in progress.
- `GET /contracts/{id}/revision-comparison/latest`

See [contracts.md](./contracts.md) for multipart examples.

---

### Analysis — `/analyses`

| Method | Route | Description |
|--------|------|-------------|
| `GET` | `/analyses/{id}` | Full result: extracted fields, clauses, findings, citations, LLM metadata |
| `GET` | `/analyses/{id}/status` | Pipeline polling |
| `PATCH` | `/analyses/{id}/status` | Workflow transitions (RF-58) |
| `POST` | `/analyses/{id}/findings/{finding_id}/review` | `lawyer` only — `verdict`: `correct`, `incorrect`, `not_relevant` |
| `POST` | `/analyses/{id}/approve` | `lawyer` only — formal approval (RF-69) |

---

### Chat — SSE

| Method | Route | Description |
|--------|------|-------------|
| `POST` | `/contracts/{id}/chat/sessions` | Body: optional `analysis_id` |
| `GET` | `/contracts/{id}/chat/sessions` | List sessions |
| `POST` | `/chat/sessions/{id}/messages` | Full JSON response |
| `POST` | `/chat/sessions/{id}/messages/stream` | **Server-Sent Events** — tokens and events (`type`: chunk, done, error) |
| `GET` | `/chat/sessions/{id}/messages` | History |
| `GET` | `/chat/sessions/{id}/suggestions` | Suggested questions (RF-44) |

The frontend uses the **stream** endpoint for real-time responses.

---

### Reports

| Method | Route | Description |
|--------|------|-------------|
| `POST` | `/analyses/{id}/reports` | Body: `{ "format": "pdf" \| "json" }` |
| `GET` | `/analyses/{id}/reports` | Metadata list |
| `GET` | `/reports/{id}/download` | File from `backend/storage/reports/` |

Records download in `download_logs` when applicable (RF-55).

---

### Notifications and messages

| Method | Route | Description |
|--------|------|-------------|
| `POST` | `/analyses/{id}/notifications` | Client notifies lawyer of decision (ACS Email, SMTP, or `NOTIFICATION_DEV_MODE` log) |
| `GET` | `/analyses/{id}/notifications` | History |
| `GET/POST` | `/analyses/{id}/review-messages` | Client–lawyer thread tied to analysis |
| `GET/POST` | `/contracts/{id}/review-messages` | Case-level messages |
| `POST` | `/contracts/{id}/review-messages/mark-read` | Read cursor |

---

### Comparisons — `/comparisons`

| Method | Route | Body |
|--------|------|------|
| `POST` | `/comparisons` | `{ "base_contract_id", "compare_contract_id" }` |
| `GET` | `/comparisons/{id}` | Detail + changes |

> Note: **original vs edited revision** comparison for the same contract uses `/contracts/{id}/revision-comparison`, not this prefix.

---

### Admin

#### `GET /admin/feedback/export`

Role `lawyer`. JSON export of `finding_reviews` and `analysis_approvals` (RF-70). No `admin` role in the MVP; the `/admin` prefix is a historical convention.

---

### Public signing schedule — `/public/signing-schedule`

No session Bearer. Authentication via **one-time schedule JWT** in query (`token`), issued by `SigningCoordinationService` / `SigningScheduleTokenService`.

| Method | Route | Description |
|--------|------|-------------|
| `GET` | `/public/signing-schedule?token=` | Contract context, summary comparison, and available slots (simulated, Mon–Fri `America/Mexico_City`) |
| `POST` | `/public/signing-schedule/confirm?token=` | Body: chosen slot; **simulated** confirmation (no appointment persistence in DB) |

Business rules: contract in `terminated` status and valid token. The SPA exposes route **`/schedule-signing`** (`ScheduleSigningPage.tsx`) consuming these endpoints.

Related variables: `FRONTEND_BASE_URL`, `SIGNING_SCHEDULE_*`, `AZURE_COMMUNICATION_*`, `SMTP_*`, `NOTIFICATION_DEV_MODE` (see `.env.example`).

---

## Planned endpoints

| Area | Description |
|------|-------------|
| Retention HTTP | `GET /contracts/retention/status`, `POST /contracts/retention/purge` — purge exists in `RetentionService.purge_expired()` but is **not** exposed on REST |
| Users `/users/*` | Administrative CRUD (extended RF-01/02) |
| Pagination | Listings with `page` / `page_size` |
| Vector RAG | Embedding ingest/query endpoints |

---

## Models and enums

| Field | Relevant values |
|-------|-------------------|
| `role` | `lawyer`, `client` |
| `perspective` | `landlord`, `tenant`, `neutral` (analysis UI: tenant) |
| `document_scope` | `original`, `lawyer_revision` |
| `contract.status` | `draft`, `in_review`, `approved`, `in_signing`, `signed`, `expired`, `terminated` |
| `analysis.status` | `processing`, `ai_generated`, `pending_review`, `reviewed`, `approved`, `failed` |
| `document_type` | `main_contract`, `annex`, `other`, `lawyer_revision` |
| `extraction_method` | `native`, `ocr`, `edited`, `none` |
| `finding_type` | `legal_risk`, `missing_clause`, `contradiction`, `inconsistency`, `recommendation` |
| `severity` / `general_risk` | `low`, `medium`, `high` |

Extracted fields (`extracted_data`): Spanish keys — `arrendador`, `arrendatario`, `renta_mensual`, etc. See `backend/data/models.py` and [schema-design.md](./database/schema-design.md).

---

## Role matrix

| Resource | client | lawyer |
|---------|--------|--------|
| Create contract / upload documents | ✅ | ❌ (except `POST .../lawyer-revision`) |
| View own contracts | ✅ | ✅ (does not see client `draft`) |
| RF-56 status transitions | ✅ (`draft→in_review`, `in_review→approved`) | ✅ (`approved→terminated`) |
| Run analysis | ✅ | ✅ |
| Chat | ✅ | ✅ |
| Reports / downloads | ✅ | ✅ |
| Review findings / approve analysis | ❌ | ✅ |
| Upload edited revision | ❌ | ✅ |
| Export feedback | ❌ | ✅ |
| Soft delete own contract | ✅ | per service rules |
| Public signing schedule | ✅ (via token link) | — |

---

## Error codes

FastAPI format: `{ "detail": "..." }` or validation error list (422).

| HTTP | Usage |
|------|-----|
| 400 | Business validation |
| 401 | Missing or invalid token |
| 403 | Role or ownership |
| 404 | Resource not found |
| 409 | Conflict (e.g. duplicate analysis, state transition) |
| 413 | File > 25 MB |
| 422 | Pydantic / domain rules |

---

## Cross-reference

| Document | Content |
|-----------|-----------|
| [authentication.md](./authentication.md) | JWT, middleware, SQL |
| [contracts.md](./contracts.md) | Upload, classification RF-08 |
| [requirements.md](./requirements.md) | RF-* |
| [database/schema-design.md](./database/schema-design.md) | SQL Server tables |
| [architecture/c4-level2-containers.md](./architecture/c4-level2-containers.md) | Containers |
| Swagger | Only endpoints mounted in `create_router()` |

### RF → endpoints map (summary)

| RF | Endpoints |
|----|-----------|
| RF-01, RF-02 | `/auth/*` |
| RF-03–RF-08, RF-53, RF-56 | `/contracts*` |
| RF-06–RF-07 | `.../text`, extraction on upload |
| RF-09–RF-37, RF-52, RF-58 | `/contracts/{id}/analyses`, `/analyses/{id}*` |
| RF-41–RF-45 | `/contracts/{id}/chat/*`, `/chat/sessions/*` |
| RF-46–RF-49 | `/analyses/{id}/reports`, `/reports/{id}/download` |
| RF-50, RF-51 | `/analyses/{id}/notifications`, review-messages |
| RF-54 | `GET /contracts/retention-policy` (+ programmatic purge) |
| RF-55 | Document/report downloads → `download_logs` |
| RF-59–RF-62 | `/comparisons` |
| RF-68–RF-70 | Finding review, approve, `/admin/feedback/export` |
| RF-56 (closure) | `PATCH /contracts/{id}` → `terminated`; agent + `/public/signing-schedule` |

---

## Version history

| Version | Date | Changes |
|---------|-------|---------|
| 0.7.0 | 2026-09 | Signing coordination, public endpoints, ACS Email, demo client email, reorganized scripts |
| 0.6.0 | 2026-09 | Doc aligned to `backend/` monorepo; chat SSE; CAG; lawyer/client roles |
| 0.5.0 | 2026-09 | Retention RF-54 (policy) |
| 0.4.0 | 2026-09 | Soft delete RF-53 |
| 0.3.0 | 2026-09 | Classification RF-08 |
| 0.2.0 | 2026-03 | Auth + contracts on SQL Server |
| 0.1.0 | 2026-03 | Health + initial auth |
