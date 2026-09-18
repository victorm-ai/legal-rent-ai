# API REST — Legal Rent AI

Especificación de la API del MVP. Texto en español; **rutas, campos JSON y mensajes de error en inglés** (convención del código).

**Código:** `backend/api/`. **Referencia viva:** Swagger en `http://localhost:8000/docs`.

## Índice

1. [Información general](#información-general)
2. [Autenticación y roles](#autenticación-y-roles)
3. [Convenciones](#convenciones)
4. [Resumen de endpoints implementados](#resumen-de-endpoints-implementados)
5. [Detalle por módulo](#detalle-por-módulo)
6. [Endpoints planificados](#endpoints-planificados)
7. [Modelos y enums](#modelos-y-enums)
8. [Matriz de roles](#matriz-de-roles)
9. [Códigos de error](#códigos-de-error)
10. [Referencia cruzada](#referencia-cruzada)

---

## Información general

| Atributo | Valor |
|----------|-------|
| Base URL (dev) | `http://localhost:8000` |
| Formato | JSON (`Content-Type: application/json`) |
| Uploads | `multipart/form-data` |
| Autenticación | JWT Bearer (excepto `/health`, `/auth/login`, `/auth/register`, `/public/signing-schedule*` con token en query) |
| Framework | FastAPI 0.104+ |
| Versión API | `0.1.0` |
| Arranque | `python run_backend.py` (raíz) o `uvicorn api.app:app` desde `backend/` |

### Cabeceras

| Cabecera | Obligatoria | Descripción |
|----------|-------------|-------------|
| `Authorization` | Rutas protegidas | `Bearer <access_token>` |
| `Content-Type` | POST/PATCH con cuerpo | `application/json` o `multipart/form-data` |

---

## Autenticación y roles

Flujo JWT. Detalle del módulo: [authentication.md](./authentication.md).

1. `POST /auth/login` → `access_token`
2. Requests: `Authorization: Bearer <token>`
3. `POST /auth/logout` → cierre en cliente

**Roles en token y BD:** `lawyer`, `client` (no hay rol `administrator` en el MVP actual).

Usuarios demo (`seed.sql` / README raíz):

| Email | Contraseña | Rol |
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

Registro con rol `client`. Mismo formato de respuesta que login.

### `POST /auth/logout`

Requiere Bearer. Response 200: `{ "message": "Signed out successfully" }`.

---

## Convenciones

### Identificadores

- UUID (`string`) en producción (`UNIQUEIDENTIFIER` en SQL Server).

### Fechas

- ISO 8601 UTC, p. ej. `"2026-09-16T22:30:00.000Z"`.

### Soft delete (RF-53)

`DELETE /contracts/{id}` marca `is_deleted`; no borra filas. Listados excluyen eliminados según rol y ownership.

### Upload

- PDF y DOCX, máximo **25 MB** (HTTP 413 si excede).
- Campo archivo: `file`.

### Descarga con token (RNF-21)

`POST .../download-token` emite URL con query `token` de corta vida; `GET .../download?token=` acepta JWT **o** token.

---

## Resumen de endpoints implementados

| Módulo | Métodos principales |
|--------|---------------------|
| Health | `GET /health` |
| Auth | `POST /auth/login`, `/register`, `/logout` |
| Contratos | `GET/POST /contracts`, `GET/PATCH/DELETE /contracts/{id}` |
| Documentos | `POST /contracts/{id}/documents`, `GET .../documents`, `GET .../download`, `GET .../text`, `POST .../download-token` |
| Partes | `GET /contracts/{id}/parties` |
| Análisis (por contrato) | `POST/GET /contracts/{id}/analyses` |
| Análisis (detalle) | `GET/PATCH /analyses/{id}`, `GET /analyses/{id}/status` |
| Revisión abogado | `POST /analyses/{id}/findings/{finding_id}/review`, `POST /analyses/{id}/approve` |
| Revisión editada | `POST /contracts/{id}/lawyer-revision`, `POST/GET .../revision-comparison` |
| Mensajes expediente | `GET/POST /contracts/{id}/review-messages`, `POST .../mark-read` |
| Mensajes por análisis | `GET/POST /analyses/{id}/review-messages` |
| Retención | `GET /contracts/retention-policy` |
| Chat | `POST/GET /contracts/{id}/chat/sessions`, `POST/GET /chat/sessions/{id}/messages`, **`POST .../messages/stream` (SSE)**, `GET .../suggestions` |
| Reportes | `POST/GET /analyses/{id}/reports`, `GET /reports/{id}/download` |
| Notificaciones | `POST/GET /analyses/{id}/notifications` |
| Comparaciones | `POST /comparisons`, `GET /comparisons/{id}` |
| Admin / feedback | `GET /admin/feedback/export` (lawyer) |
| Agenda de firma (pública) | `GET/POST /public/signing-schedule` (JWT en query `token`, sin login SPA) |

---

## Detalle por módulo

### Health

#### `GET /health`

Sin autenticación. Response: `status`, `service`, `version`.

---

### Contratos — `/contracts`

| Método | Ruta | Notas |
|--------|------|--------|
| `GET` | `/contracts` | Lista; `lawyer` ve contratos de clientes asignados / visibilidad ampliada según servicio |
| `POST` | `/contracts` | Multipart: `file`, `perspective` (`tenant` en MVP UI), `title` opcional |
| `GET` | `/contracts/{id}` | Detalle + documentos |
| `PATCH` | `/contracts/{id}` | `status`, `title`, `closure_notes` (RF-56) |
| `DELETE` | `/contracts/{id}` | Soft delete (RF-53) |
| `GET` | `/contracts/retention-policy` | Días de retención post-eliminación (RF-54) |

**`POST /contracts/{id}/documents`:** adjunto adicional; form `file`, opcional `is_signed_version` (RF-57 parcial).

**`POST /contracts/{id}/lawyer-revision`:** solo `lawyer`; sube DOCX/PDF editado (`document_type` / scope `lawyer_revision`).

**`POST /contracts/{id}/analyses`:** body JSON con `perspective` y `document_scope` (`original` \| `lawyer_revision`). Por defecto pipeline **síncrono** (`ANALYSIS_ASYNC=false`); si `true`, responde 201 con `processing` y el cliente hace polling en `/analyses/{id}/status`.

**Ciclo de vida (RF-56):** `PATCH /contracts/{id}` acepta `status`, `title`, `closure_notes`. Flujo UI habitual:

| Paso | Rol | Transición |
|------|-----|------------|
| Enviar a revisión legal | `client` | `draft` → `in_review` |
| Aprobar expediente | `client` | `in_review` → `approved` |
| Cierre administrativo | `lawyer` | `approved` → `terminated` (+ `closure_notes` recomendadas) |

Al pasar a `terminated`, el backend puede ejecutar **coordinación de firma** (agente LangGraph + correo ACS/SMTP con enlace `{FRONTEND_BASE_URL}/schedule-signing?token=...`). Si el agente falla, el servicio revierte el status del contrato. Tras `terminated`, el contrato queda **bloqueado** (`is_contract_locked`).

Estados reservados en modelo (`in_signing`, `signed`, `expired`) existen en BD pero no forman parte del flujo principal de la SPA hoy.

**Comparación original vs editado:**

- `POST /contracts/{id}/revision-comparison` — puede devolver 202 si el análisis de la revisión está en curso.
- `GET /contracts/{id}/revision-comparison/latest`

Ver [contracts.md](./contracts.md) para ejemplos multipart.

---

### Análisis — `/analyses`

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/analyses/{id}` | Resultado completo: campos extraídos, cláusulas, hallazgos, citas, metadata LLM |
| `GET` | `/analyses/{id}/status` | Polling de pipeline |
| `PATCH` | `/analyses/{id}/status` | Transiciones de workflow (RF-58) |
| `POST` | `/analyses/{id}/findings/{finding_id}/review` | Solo `lawyer` — `verdict`: `correct`, `incorrect`, `not_relevant` |
| `POST` | `/analyses/{id}/approve` | Solo `lawyer` — aprobación formal (RF-69) |

---

### Chat — SSE

| Método | Ruta | Descripción |
|--------|------|-------------|
| `POST` | `/contracts/{id}/chat/sessions` | Body: `analysis_id` opcional |
| `GET` | `/contracts/{id}/chat/sessions` | Lista sesiones |
| `POST` | `/chat/sessions/{id}/messages` | Respuesta completa en JSON |
| `POST` | `/chat/sessions/{id}/messages/stream` | **Server-Sent Events** — tokens y eventos (`type`: chunk, done, error) |
| `GET` | `/chat/sessions/{id}/messages` | Historial |
| `GET` | `/chat/sessions/{id}/suggestions` | Preguntas sugeridas (RF-44) |

El frontend usa el endpoint **stream** para respuesta en tiempo real.

---

### Reportes

| Método | Ruta | Descripción |
|--------|------|-------------|
| `POST` | `/analyses/{id}/reports` | Body: `{ "format": "pdf" \| "json" }` |
| `GET` | `/analyses/{id}/reports` | Lista metadatos |
| `GET` | `/reports/{id}/download` | Archivo desde `backend/storage/reports/` |

Registra descarga en `download_logs` cuando aplica (RF-55).

---

### Notificaciones y mensajes

| Método | Ruta | Descripción |
|--------|------|-------------|
| `POST` | `/analyses/{id}/notifications` | Cliente notifica decisión al abogado (ACS Email, SMTP o `NOTIFICATION_DEV_MODE` log) |
| `GET` | `/analyses/{id}/notifications` | Historial |
| `GET/POST` | `/analyses/{id}/review-messages` | Hilo cliente–abogado ligado al análisis |
| `GET/POST` | `/contracts/{id}/review-messages` | Mensajes a nivel expediente |
| `POST` | `/contracts/{id}/review-messages/mark-read` | Cursor de lectura |

---

### Comparaciones — `/comparisons`

| Método | Ruta | Body |
|--------|------|------|
| `POST` | `/comparisons` | `{ "base_contract_id", "compare_contract_id" }` |
| `GET` | `/comparisons/{id}` | Detalle + cambios |

> Nota: la comparación **original vs revisión editada** del mismo contrato usa `/contracts/{id}/revision-comparison`, no este prefijo.

---

### Admin

#### `GET /admin/feedback/export`

Rol `lawyer`. Export JSON de `finding_reviews` y `analysis_approvals` (RF-70). No existe rol `admin` en el MVP; el prefijo `/admin` es convención histórica.

---

### Agenda de firma pública — `/public/signing-schedule`

Sin Bearer de sesión. Autenticación mediante **JWT de un solo uso de agenda** en query (`token`), emitido por `SigningCoordinationService` / `SigningScheduleTokenService`.

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/public/signing-schedule?token=` | Contexto del contrato, comparación resumida y slots disponibles (simulados, Lun–Vie `America/Mexico_City`) |
| `POST` | `/public/signing-schedule/confirm?token=` | Body: slot elegido; confirmación **simulada** (sin persistencia de cita en BD) |

Requisitos de negocio: contrato en status `terminated` y token válido. La SPA expone la ruta **`/schedule-signing`** (`ScheduleSigningPage.tsx`) consumiendo estos endpoints.

Variables relacionadas: `FRONTEND_BASE_URL`, `SIGNING_SCHEDULE_*`, `AZURE_COMMUNICATION_*`, `SMTP_*`, `NOTIFICATION_DEV_MODE` (ver `.env.example`).

---

## Endpoints planificados

| Área | Descripción |
|------|-------------|
| Retención HTTP | `GET /contracts/retention/status`, `POST /contracts/retention/purge` — la purga existe en `RetentionService.purge_expired()` pero **no** está expuesta en REST |
| Usuarios `/users/*` | CRUD administrativo (RF-01/02 ampliado) |
| Paginación | Listados con `page` / `page_size` |
| RAG vectorial | Endpoints de ingestión/consulta embeddings |

---

## Modelos y enums

| Campo | Valores relevantes |
|-------|-------------------|
| `role` | `lawyer`, `client` |
| `perspective` | `landlord`, `tenant`, `neutral` (análisis UI: tenant) |
| `document_scope` | `original`, `lawyer_revision` |
| `contract.status` | `draft`, `in_review`, `approved`, `in_signing`, `signed`, `expired`, `terminated` |
| `analysis.status` | `processing`, `ai_generated`, `pending_review`, `reviewed`, `approved`, `failed` |
| `document_type` | `main_contract`, `annex`, `other`, `lawyer_revision` |
| `extraction_method` | `native`, `ocr`, `edited`, `none` |
| `finding_type` | `legal_risk`, `missing_clause`, `contradiction`, `inconsistency`, `recommendation` |
| `severity` / `general_risk` | `low`, `medium`, `high` |

Campos extraídos (`extracted_data`): español — `arrendador`, `arrendatario`, `renta_mensual`, etc. Ver `backend/data/models.py` y [schema-design.md](./database/schema-design.md).

---

## Matriz de roles

| Recurso | client | lawyer |
|---------|--------|--------|
| Crear contrato / subir documentos | ✅ | ❌ (salvo `POST .../lawyer-revision`) |
| Ver contratos propios | ✅ | ✅ (no ve `draft` de clientes) |
| Transiciones de status RF-56 | ✅ (`draft→in_review`, `in_review→approved`) | ✅ (`approved→terminated`) |
| Ejecutar análisis | ✅ | ✅ |
| Chat | ✅ | ✅ |
| Reportes / descargas | ✅ | ✅ |
| Revisar hallazgos / aprobar análisis | ❌ | ✅ |
| Subir revisión editada | ❌ | ✅ |
| Export feedback | ❌ | ✅ |
| Soft delete contrato propio | ✅ | según reglas de servicio |
| Agenda pública de firma | ✅ (vía enlace con token) | — |

---

## Códigos de error

Formato FastAPI: `{ "detail": "..." }` o lista de errores de validación (422).

| HTTP | Uso |
|------|-----|
| 400 | Validación de negocio |
| 401 | Token ausente o inválido |
| 403 | Rol o ownership |
| 404 | Recurso no encontrado |
| 409 | Conflicto (p. ej. análisis duplicado, transición de estado) |
| 413 | Archivo > 25 MB |
| 422 | Pydantic / reglas de dominio |

---

## Referencia cruzada

| Documento | Contenido |
|-----------|-----------|
| [authentication.md](./authentication.md) | JWT, middleware, SQL |
| [contracts.md](./contracts.md) | Upload, clasificación RF-08 |
| [requirements.md](./requirements.md) | RF-* |
| [database/schema-design.md](./database/schema-design.md) | Tablas SQL Server |
| [architecture/c4-level2-containers.md](./architecture/c4-level2-containers.md) | Contenedores |
| Swagger | Solo endpoints montados en `create_router()` |

### Mapa RF → endpoints (resumen)

| RF | Endpoints |
|----|-----------|
| RF-01, RF-02 | `/auth/*` |
| RF-03–RF-08, RF-53, RF-56 | `/contracts*` |
| RF-06–RF-07 | `.../text`, extracción en upload |
| RF-09–RF-37, RF-52, RF-58 | `/contracts/{id}/analyses`, `/analyses/{id}*` |
| RF-41–RF-45 | `/contracts/{id}/chat/*`, `/chat/sessions/*` |
| RF-46–RF-49 | `/analyses/{id}/reports`, `/reports/{id}/download` |
| RF-50, RF-51 | `/analyses/{id}/notifications`, review-messages |
| RF-54 | `GET /contracts/retention-policy` (+ purga programática) |
| RF-55 | Descargas documentos/reportes → `download_logs` |
| RF-59–RF-62 | `/comparisons` |
| RF-68–RF-70 | Revisión hallazgos, approve, `/admin/feedback/export` |
| RF-56 (cierre) | `PATCH /contracts/{id}` → `terminated`; agente + `/public/signing-schedule` |

---

## Historial de versiones

| Versión | Fecha | Cambios |
|---------|-------|---------|
| 0.7.0 | 2026-09 | Coordinación de firma, endpoints públicos, ACS Email, demo client email, scripts reorganizados |
| 0.6.0 | 2026-09 | Doc alineada a monorepo `backend/`; chat SSE; CAG; roles lawyer/client |
| 0.5.0 | 2026-09 | Retención RF-54 (política) |
| 0.4.0 | 2026-09 | Soft delete RF-53 |
| 0.3.0 | 2026-09 | Clasificación RF-08 |
| 0.2.0 | 2026-03 | Auth + contratos en SQL Server |
| 0.1.0 | 2026-03 | Health + auth inicial |
