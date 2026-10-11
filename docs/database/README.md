# Database — Legal Rent AI

Relational model for the MVP on **Microsoft SQL Server**. The backend (`backend/data/`) connects via **pyodbc**.

## Index

| Document | Description |
|-----------|-------------|
| [schema-design.md](./schema-design.md) | ER model, tables, and design decisions |
| [setup-ssms.md](./setup-ssms.md) | Create the database in SQL Server Management Studio |
| [00-create-database.sql](./00-create-database.sql) | Creates `LegalRentAI` |
| [ddl.sql](./ddl.sql) | Canonical DDL: `[app]` schema and **23 tables** |
| [seed.sql](./seed.sql) | Demo users (`lawyer`, `client`) |
| [migrations/run-all-incremental.sql](./migrations/run-all-incremental.sql) | Idempotent migrations |
| [12-migrate-remove-administrator.sql](./migrations/12-migrate-remove-administrator.sql) | Removes legacy `administrator` role |
| [migrations/](./migrations/) | Incremental scripts (text, chat observability, etc.) |

## Quick setup

From the **repository root**:

```powershell
.\setup_database.bat      # New DB: create + ddl + seed + migrations
.\apply_migrations.bat    # Update existing DB only
```

Manual in SSMS: [setup-ssms.md](./setup-ssms.md).

**Schema verification:**

```bash
python scripts/db/verify_database_schema.py
```

(Requires `.env` with `DB_*` and installed packages; the script adds `backend/` to the path.)

## Summary

| Attribute | Value |
|----------|-------|
| Engine | SQL Server 2019+ (Azure SQL compatible) |
| Database | `LegalRentAI` |
| Schema | `app` |
| Identifiers | `UNIQUEIDENTIFIER` (`NEWSEQUENTIALID()`) |
| Soft delete | Contracts and documents (RF-53) |
| Documents | `VARBINARY(MAX)` in `contract_documents.file_content` |
| Active roles | `lawyer` (id=1), `client` (id=2) |
| App config | `.env` at repo root → `backend/config/settings.py` |

**Source of truth:** [`ddl.sql`](./ddl.sql). Older databases: run [`migrations/run-all-incremental.sql`](./migrations/run-all-incremental.sql) and, if the `administrator` role existed, [`migrations/12-migrate-remove-administrator.sql`](./migrations/12-migrate-remove-administrator.sql).

## Tables by module

| Module | Tables |
|--------|--------|
| Auth (RF-01, RF-02) | `roles`, `users` |
| Contracts (RF-03–RF-08) | `contracts`, `contract_documents`, `contract_parties` |
| Analysis | `analyses`, `extracted_fields`, `clauses`, `findings`, `legal_citations` |
| LLM traces (RF-64) | `analysis_llm_runs` (+ JSON in `backend/storage/llm-runs/`) |
| Chat (RF-41–RF-45) | `chat_sessions`, `chat_messages`, `chat_llm_call_events` |
| Reports / audit | `reports`, `download_logs` |
| Notifications | `notifications` |
| Case messaging | `review_messages`, `review_message_read_cursors` |
| Comparisons | `contract_comparisons`, `comparison_changes` |
| Lawyer review | `finding_reviews`, `analysis_approvals` |

## Notable migrations (order in `run-all-incremental.sql`)

| Script | Topic |
|--------|------|
| `01-add-file-content.sql` | Binary in DB |
| `02-add-text-extraction.sql` | Extracted text |
| `03-add-analysis-statuses.sql` | Analysis states |
| `04-add-analysis-perspective.sql` | Perspective |
| `05-review-messages.sql` | Review messages |
| `06-document-text-edits.sql` / `06-review-message-read-cursors.sql` | Edits / read cursors |
| `07-lawyer-revision-document.sql` | `lawyer_revision` type |
| `08-add-analysis-document-scope.sql` | `original` / `lawyer_revision` |
| `09-findings-confidence.sql` | Finding confidence |
| `10-chat-llm-observability.sql` | LLM events in chat |
| `11-update-client-demo-email.sql` | Demo client email → `code.zemoreno@gmail.com` |
| `12-migrate-remove-administrator.sql` | Role catalog without `administrator` |

## Columns aligned with code (2026)

| Table | Notes |
|-------|--------|
| `contracts` | `closure_notes`, lifecycle states, soft delete |
| `contract_documents` | `document_type` incl. `lawyer_revision`; `extraction_method` incl. `edited` |
| `analyses` | `perspective`, `document_scope`; unique index per contract + perspective + scope |
| `findings` | `confidence` |
| `chat_llm_call_events` | Chat cost/latency observability |

## References

- [Requirements](../requirements.md)
- [Authentication](../authentication.md)
- [Contracts](../contracts.md)
- [REST API](../api.md)
- [Architecture — containers](../architecture/c4-level2-containers.md)
