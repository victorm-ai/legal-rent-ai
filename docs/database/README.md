# Base de datos — Legal Rent AI

Modelo relacional del MVP en **Microsoft SQL Server**. El backend (`backend/data/`) accede vía **pyodbc**.

## Índice

| Documento | Descripción |
|-----------|-------------|
| [schema-design.md](./schema-design.md) | Modelo ER, tablas y decisiones de diseño |
| [setup-ssms.md](./setup-ssms.md) | Crear la BD en SQL Server Management Studio |
| [00-create-database.sql](./00-create-database.sql) | Crea `LegalRentAI` |
| [ddl.sql](./ddl.sql) | DDL canónico: esquema `[app]` y **23 tablas** |
| [seed.sql](./seed.sql) | Usuarios demo (`lawyer`, `client`) |
| [migrations/run-all-incremental.sql](./migrations/run-all-incremental.sql) | Migraciones idempotentes |
| [12-migrate-remove-administrator.sql](./migrations/12-migrate-remove-administrator.sql) | Elimina rol legacy `administrator` |
| [migrations/](./migrations/) | Scripts incrementales (texto, chat observability, etc.) |

## Instalación rápida

Desde la **raíz del repositorio**:

```powershell
.\setup_database.bat      # BD nueva: create + ddl + seed + migraciones
.\apply_migrations.bat    # Solo actualizar BD existente
```

Manual en SSMS: [setup-ssms.md](./setup-ssms.md).

**Verificación del esquema:**

```bash
python scripts/db/verify_database_schema.py
```

(Requiere `.env` con `DB_*` y paquetes instalados; el script añade `backend/` al path.)

## Resumen

| Atributo | Valor |
|----------|-------|
| Motor | SQL Server 2019+ (Azure SQL compatible) |
| Base | `LegalRentAI` |
| Esquema | `app` |
| Identificadores | `UNIQUEIDENTIFIER` (`NEWSEQUENTIALID()`) |
| Soft delete | Contratos y documentos (RF-53) |
| Documentos | `VARBINARY(MAX)` en `contract_documents.file_content` |
| Roles activos | `lawyer` (id=1), `client` (id=2) |
| Config app | `.env` en raíz del repo → `backend/config/settings.py` |

**Fuente de verdad:** [`ddl.sql`](./ddl.sql). Bases antiguas: ejecutar [`migrations/run-all-incremental.sql`](./migrations/run-all-incremental.sql) y, si existía rol `administrator`, [`migrations/12-migrate-remove-administrator.sql`](./migrations/12-migrate-remove-administrator.sql).

## Tablas por módulo

| Módulo | Tablas |
|--------|--------|
| Auth (RF-01, RF-02) | `roles`, `users` |
| Contratos (RF-03–RF-08) | `contracts`, `contract_documents`, `contract_parties` |
| Análisis | `analyses`, `extracted_fields`, `clauses`, `findings`, `legal_citations` |
| Trazas LLM (RF-64) | `analysis_llm_runs` (+ JSON en `backend/storage/llm-runs/`) |
| Chat (RF-41–RF-45) | `chat_sessions`, `chat_messages`, `chat_llm_call_events` |
| Reportes / auditoría | `reports`, `download_logs` |
| Notificaciones | `notifications` |
| Mensajería expediente | `review_messages`, `review_message_read_cursors` |
| Comparaciones | `contract_comparisons`, `comparison_changes` |
| Revisión abogado | `finding_reviews`, `analysis_approvals` |

## Migraciones destacadas (orden en `run-all-incremental.sql`)

| Script | Tema |
|--------|------|
| `01-add-file-content.sql` | Binario en BD |
| `02-add-text-extraction.sql` | Texto extraído |
| `03-add-analysis-statuses.sql` | Estados de análisis |
| `04-add-analysis-perspective.sql` | Perspectiva |
| `05-review-messages.sql` | Mensajes revisión |
| `06-document-text-edits.sql` / `06-review-message-read-cursors.sql` | Ediciones / lectura |
| `07-lawyer-revision-document.sql` | Tipo `lawyer_revision` |
| `08-add-analysis-document-scope.sql` | `original` / `lawyer_revision` |
| `09-findings-confidence.sql` | Confianza en hallazgos |
| `10-chat-llm-observability.sql` | Eventos LLM en chat |
| `11-update-client-demo-email.sql` | Email demo client → `code.zemoreno@gmail.com` |
| `12-migrate-remove-administrator.sql` | Catálogo de roles sin `administrator` |

## Columnas alineadas con el código (2026)

| Tabla | Notas |
|-------|--------|
| `contracts` | `closure_notes`, estados de ciclo de vida, soft delete |
| `contract_documents` | `document_type` incl. `lawyer_revision`; `extraction_method` incl. `edited` |
| `analyses` | `perspective`, `document_scope`; índice único por contrato + perspectiva + scope |
| `findings` | `confidence` |
| `chat_llm_call_events` | Observabilidad de costos/latencia en chat |

## Referencias

- [Requerimientos](../requirements.md)
- [Autenticación](../authentication.md)
- [Contratos](../contracts.md)
- [API REST](../api.md)
- [Arquitectura — contenedores](../architecture/c4-level2-containers.md)
