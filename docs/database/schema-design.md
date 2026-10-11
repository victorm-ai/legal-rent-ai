# Relational schema design — SQL Server

Data model for **Legal Rent AI** (MVP). Covers users, contracts, documents, analysis, findings, chat, reports, notifications, and basic audit.

> **Canonical schema:** [`ddl.sql`](./ddl.sql) (**23 tables** in `[app]`, includes `chat_llm_call_events`). Databases created before September 2026 must run [`migrations/run-all-incremental.sql`](./migrations/run-all-incremental.sql) and, if applicable, [`migrations/12-migrate-remove-administrator.sql`](./migrations/12-migrate-remove-administrator.sql). Verification: `python scripts/db/verify_database_schema.py` (from repo root).

## Entity-relationship diagram

```mermaid
erDiagram
    roles ||--o{ users : has
    users ||--o{ contracts : owns
    users ||--o{ download_logs : performs
    users ||--o{ chat_sessions : starts
    users ||--o{ notifications : triggers

    contracts ||--o{ contract_documents : contains
    contracts ||--o{ contract_parties : has
    contracts ||--o{ analyses : analyzed_by
    contracts ||--o{ chat_sessions : discussed_in

    analyses ||--o{ extracted_fields : yields
    analyses ||--o{ clauses : identifies
    analyses ||--o{ findings : produces
    analyses ||--o{ analysis_llm_runs : traced_by
    analyses ||--o{ reports : exported_as
    analyses ||--o{ notifications : referenced_by
    analyses ||--o| analysis_approvals : approved_by

    clauses ||--o{ findings : supports
    findings ||--o{ legal_citations : cites
    findings ||--o{ finding_reviews : reviewed_in

    chat_sessions ||--o{ chat_messages : contains

    contracts ||--o{ contract_comparisons : base_of
    contracts ||--o{ contract_comparisons : compare_of
    contract_comparisons ||--o{ comparison_changes : details

    roles {
        tinyint id PK
        nvarchar_32 code UK
        nvarchar_100 name
    }

    users {
        uniqueidentifier id PK
        nvarchar_320 email UK
        nvarchar_200 name
        tinyint role_id FK
        nvarchar_128 password_hash
        nvarchar_64 password_salt
        bit is_active
        datetime2 created_at
        datetime2 updated_at
    }

    contracts {
        uniqueidentifier id PK
        uniqueidentifier user_id FK
        nvarchar_32 perspective
        nvarchar_100 jurisdiction
        nvarchar_32 status
        nvarchar_300 title
        nvarchar_max closure_notes
        bit is_deleted
        datetime2 deleted_at
        datetime2 created_at
        datetime2 updated_at
    }

    contract_documents {
        uniqueidentifier id PK
        uniqueidentifier contract_id FK
        nvarchar_255 file_name
        varbinary_max file_content
        bigint file_size_bytes
        int page_count
        nvarchar_50 document_type
        nvarchar_100 mime_type
        bit is_signed_version
        bit is_deleted
        datetime2 uploaded_at
    }

    analyses {
        uniqueidentifier id PK
        uniqueidentifier contract_id FK
        nvarchar_32 perspective
        nvarchar_32 document_scope
        nvarchar_32 status
        nvarchar_max summary_executive
        nvarchar_16 general_risk
        datetime2 started_at
        datetime2 completed_at
        datetime2 created_at
    }

    findings {
        uniqueidentifier id PK
        uniqueidentifier analysis_id FK
        uniqueidentifier clause_id FK
        nvarchar_50 finding_type
        nvarchar_16 severity
        nvarchar_300 title
        nvarchar_max description
        nvarchar_max recommendation
    }
```

## Design conventions

### Identifiers and types

| Convention | Detail |
|------------|---------|
| Primary keys | `UNIQUEIDENTIFIER NOT NULL DEFAULT NEWSEQUENTIALID()` |
| Dates | `DATETIME2(3)` in UTC |
| Short text | `NVARCHAR(n)` |
| Long text | `NVARCHAR(MAX)` |
| Auxiliary JSON | `NVARCHAR(MAX)` with `ISJSON()` in application |
| Amounts | `DECIMAL(18,2)` where applicable in extracted fields |

### Naming

- **Tables and columns:** English, `snake_case` (e.g. `contract_documents`, `created_at`).
- **Legal domain values:** Spanish in `extracted_fields.field_name` (e.g. `arrendador`, `renta_mensual`).
- **Application enums:** stored as `NVARCHAR` with `CHECK` or catalog table.

### Soft delete (RF-53)

Contracts and documents are **not physically deleted** from the MVP UI:

- `contracts.is_deleted`, `contracts.deleted_at`
- `contract_documents.is_deleted`

Business queries must filter `is_deleted = 0`.

---

## Catalog tables

### `roles`

System roles (RF-02).

| Column | Type | Description |
|---------|------|-------------|
| `id` | `TINYINT` PK | Identifier |
| `code` | `NVARCHAR(32)` UK | `lawyer`, `client` |
| `name` | `NVARCHAR(100)` | Display name for UI |

Initial values (current MVP; after `12-migrate-remove-administrator.sql`):

| id | code | name |
|----|------|------|
| 1 | `lawyer` | Lawyer |
| 2 | `client` | Client |

---

## Authentication and users

### `users`

Authenticated users (RF-01, RF-02).

| Column | Type | Nullable | Description |
|---------|------|------|-------------|
| `id` | `UNIQUEIDENTIFIER` | NO | PK |
| `email` | `NVARCHAR(320)` | NO | UK, login |
| `name` | `NVARCHAR(200)` | NO | Display name |
| `role_id` | `TINYINT` | NO | FK → `roles.id` |
| `password_hash` | `NVARCHAR(128)` | NO | PBKDF2-HMAC-SHA256 hex |
| `password_salt` | `NVARCHAR(64)` | NO | Salt hex |
| `is_active` | `BIT` | NO | Default 1 |
| `created_at` | `DATETIME2(3)` | NO | Created |
| `updated_at` | `DATETIME2(3)` | NO | Last modified |

**Indexes:** `UX_users_email`, `IX_users_role_id`.

---

## Contracts and documents

### `contracts`

Lease contract under analysis (RF-52, RF-56).

| Column | Type | Nullable | Description |
|---------|------|------|-------------|
| `id` | `UNIQUEIDENTIFIER` | NO | PK |
| `user_id` | `UNIQUEIDENTIFIER` | NO | FK → `users.id` (owner) |
| `perspective` | `NVARCHAR(32)` | NO | `landlord`, `tenant`, `neutral` (RF-09) |
| `jurisdiction` | `NVARCHAR(100)` | YES | e.g. `Jalisco`, `Ciudad de México` (RF-10) |
| `status` | `NVARCHAR(32)` | NO | See states below |
| `title` | `NVARCHAR(300)` | YES | Optional descriptive title |
| `closure_notes` | `NVARCHAR(MAX)` | YES | Administrative closure notes (RF-56, lawyer when moving to `terminated`) |
| `is_deleted` | `BIT` | NO | Soft delete (RF-53) |
| `deleted_at` | `DATETIME2(3)` | YES | Logical deletion timestamp |
| `created_at` | `DATETIME2(3)` | NO | |
| `updated_at` | `DATETIME2(3)` | NO | |

**States (`status`):** `draft`, `in_review`, `approved`, `in_signing`, `signed`, `expired`, `terminated`.

Active UI/API flow: `draft` → `in_review` → `approved` → `terminated`. Only `terminated` blocks modifications (`LOCKED_STATUSES` in `backend/domain/contract_status.py`). The lawyer does not list contracts in `draft`.

**Indexes:** `IX_contracts_user_id`, `IX_contracts_status`, `IX_contracts_created_at`.

### `contract_documents`

Associated PDF/DOCX files (RF-03, RF-05, RF-08, RF-57).

| Column | Type | Nullable | Description |
|---------|------|------|-------------|
| `id` | `UNIQUEIDENTIFIER` | NO | PK |
| `contract_id` | `UNIQUEIDENTIFIER` | NO | FK → `contracts.id` |
| `file_name` | `NVARCHAR(255)` | NO | Original file name |
| `file_content` | `VARBINARY(MAX)` | NO | Binary PDF/DOCX content |
| `file_size_bytes` | `BIGINT` | NO | Size in bytes (max 25 MB, RF-04) |
| `page_count` | `INT` | YES | Detected page count |
| `document_type` | `NVARCHAR(50)` | NO | `main_contract`, `annex`, `other`, `lawyer_revision` |
| `mime_type` | `NVARCHAR(100)` | YES | `application/pdf`, etc. |
| `is_signed_version` | `BIT` | NO | Signed version (RF-57) |
| `is_deleted` | `BIT` | NO | Soft delete |
| `uploaded_at` | `DATETIME2(3)` | NO | |

**Indexes:** `IX_contract_documents_contract_id`.

### `contract_parties`

Parties identified in the contract (RF-12).

| Column | Type | Nullable | Description |
|---------|------|------|-------------|
| `id` | `UNIQUEIDENTIFIER` | NO | PK |
| `contract_id` | `UNIQUEIDENTIFIER` | NO | FK → `contracts.id` |
| `party_type` | `NVARCHAR(50)` | NO | `landlord`, `tenant`, `guarantor`, etc. |
| `name` | `NVARCHAR(300)` | YES | Name or legal entity |
| `legal_representative` | `NVARCHAR(300)` | YES | Representative |
| `address` | `NVARCHAR(500)` | YES | Address |
| `confidence` | `DECIMAL(5,4)` | YES | Extraction confidence |
| `source_page` | `INT` | YES | Evidence page |

---

## Analysis

### `analyses`

Analysis run on a contract (RF-52, RF-58).

| Column | Type | Nullable | Description |
|---------|------|------|-------------|
| `id` | `UNIQUEIDENTIFIER` | NO | PK |
| `contract_id` | `UNIQUEIDENTIFIER` | NO | FK → `contracts.id` |
| `status` | `NVARCHAR(32)` | NO | See states below |
| `summary_executive` | `NVARCHAR(MAX)` | YES | Executive summary (RF-37) |
| `general_risk` | `NVARCHAR(16)` | YES | `low`, `medium`, `high` |
| `started_at` | `DATETIME2(3)` | YES | Processing start |
| `completed_at` | `DATETIME2(3)` | YES | End (target ≤ 60 s, RNF-05) |
| `created_at` | `DATETIME2(3)` | NO | |

**States (`status`):** `ai_generated`, `pending_review`, `reviewed`, `approved`.

**Indexes:** `IX_analyses_contract_id`, `IX_analyses_status`, `IX_analyses_created_at`.

### `analysis_llm_runs`

AI technical traceability (RF-64, RNF-48).

| Column | Type | Nullable | Description |
|---------|------|------|-------------|
| `id` | `UNIQUEIDENTIFIER` | NO | PK |
| `analysis_id` | `UNIQUEIDENTIFIER` | NO | FK → `analyses.id` |
| `provider` | `NVARCHAR(100)` | NO | e.g. `azure_openai` |
| `model` | `NVARCHAR(100)` | NO | e.g. `gpt-4o` |
| `model_version` | `NVARCHAR(50)` | YES | Version |
| `prompt_id` | `NVARCHAR(100)` | YES | Prompt identifier |
| `response_storage_path` | `NVARCHAR(500)` | YES | Raw response in blob |
| `tokens_input` | `INT` | YES | Input tokens |
| `tokens_output` | `INT` | YES | Output tokens |
| `duration_ms` | `INT` | YES | Duration |
| `created_at` | `DATETIME2(3)` | NO | |

### `extracted_fields`

Structured extracted fields (RF-11–RF-17, RNF-46).

| Column | Type | Nullable | Description |
|---------|------|------|-------------|
| `id` | `UNIQUEIDENTIFIER` | NO | PK |
| `analysis_id` | `UNIQUEIDENTIFIER` | NO | FK → `analyses.id` |
| `field_name` | `NVARCHAR(100)` | NO | Legal field name in Spanish |
| `field_value` | `NVARCHAR(MAX)` | YES | Serialized value |
| `confidence` | `DECIMAL(5,4)` | NO | 0.0000–1.0000 |
| `source_page` | `INT` | YES | Page |
| `source_clause` | `NVARCHAR(200)` | YES | Clause |
| `source_section` | `NVARCHAR(200)` | YES | Section |
| `source_text_snippet` | `NVARCHAR(MAX)` | YES | Evidence snippet |

**Expected fields (`field_name`):** `arrendador`, `arrendatario`, `fiador`, `obligado_solidario`, `inmueble_direccion`, `inmueble_uso`, `inmueble_superficie`, `renta_mensual`, `deposito`, `garantia`, `fecha_inicio`, `fecha_fin`, `duracion_meses`, `jurisdiccion`.

**Indexes:** `IX_extracted_fields_analysis_id`, `IX_extracted_fields_field_name`.

### `clauses`

Identified clauses (RF-18–RF-21).

| Column | Type | Nullable | Description |
|---------|------|------|-------------|
| `id` | `UNIQUEIDENTIFIER` | NO | PK |
| `analysis_id` | `UNIQUEIDENTIFIER` | NO | FK → `analyses.id` |
| `category` | `NVARCHAR(100)` | NO | Clause category |
| `text` | `NVARCHAR(MAX)` | NO | Clause text |
| `section` | `NVARCHAR(200)` | YES | Document section |
| `page` | `INT` | YES | Page |
| `confidence` | `DECIMAL(5,4)` | NO | Confidence |

### `findings`

Findings and risks (RF-22–RF-28).

| Column | Type | Nullable | Description |
|---------|------|------|-------------|
| `id` | `UNIQUEIDENTIFIER` | NO | PK |
| `analysis_id` | `UNIQUEIDENTIFIER` | NO | FK → `analyses.id` |
| `clause_id` | `UNIQUEIDENTIFIER` | YES | FK → `clauses.id` |
| `finding_type` | `NVARCHAR(50)` | NO | Finding type |
| `severity` | `NVARCHAR(16)` | NO | `low`, `medium`, `high` |
| `title` | `NVARCHAR(300)` | NO | Title |
| `description` | `NVARCHAR(MAX)` | NO | Description |
| `legal_basis` | `NVARCHAR(MAX)` | YES | Legal basis |
| `source_law` | `NVARCHAR(500)` | YES | Law or code |
| `evidence_text` | `NVARCHAR(MAX)` | YES | Evidence text |
| `evidence_page` | `INT` | YES | Page |
| `recommendation` | `NVARCHAR(MAX)` | YES | Recommendation |
| `suggested_rewording` | `NVARCHAR(MAX)` | YES | Suggested wording |
| `sort_order` | `INT` | NO | Order by criticality (RNF-41) |

**Indexes:** `IX_findings_analysis_id`, `IX_findings_severity`.

### `legal_citations`

Legal references per finding (RNF-47).

| Column | Type | Nullable | Description |
|---------|------|------|-------------|
| `id` | `UNIQUEIDENTIFIER` | NO | PK |
| `finding_id` | `UNIQUEIDENTIFIER` | NO | FK → `findings.id` |
| `law_code` | `NVARCHAR(100)` | NO | e.g. Código Civil Jalisco |
| `article` | `NVARCHAR(100)` | YES | Article |
| `excerpt` | `NVARCHAR(MAX)` | YES | Quoted excerpt |
| `source_uri` | `NVARCHAR(500)` | YES | RAG corpus URI |

---

## Contextual chat

### `chat_sessions` (RF-41)

| Column | Type | Description |
|---------|------|-------------|
| `id` | `UNIQUEIDENTIFIER` | PK |
| `contract_id` | `UNIQUEIDENTIFIER` | FK → `contracts.id` |
| `user_id` | `UNIQUEIDENTIFIER` | FK → `users.id` |
| `analysis_id` | `UNIQUEIDENTIFIER` | FK → `analyses.id` (context) |
| `created_at` | `DATETIME2(3)` | Session start |

### `chat_messages` (RF-42, RF-43)

| Column | Type | Description |
|---------|------|-------------|
| `id` | `UNIQUEIDENTIFIER` | PK |
| `session_id` | `UNIQUEIDENTIFIER` | FK → `chat_sessions.id` |
| `role` | `NVARCHAR(20)` | `user`, `assistant`, `system` |
| `content` | `NVARCHAR(MAX)` | Message |
| `references_json` | `NVARCHAR(MAX)` | Cited sources (JSON) |
| `created_at` | `DATETIME2(3)` | |

---

## Reports and downloads

### `reports` (RF-46–RF-49)

| Column | Type | Description |
|---------|------|-------------|
| `id` | `UNIQUEIDENTIFIER` | PK |
| `analysis_id` | `UNIQUEIDENTIFIER` | FK → `analyses.id` |
| `format` | `NVARCHAR(20)` | `pdf`, `json` |
| `storage_path` | `NVARCHAR(500)` | Generated file path |
| `generated_by` | `UNIQUEIDENTIFIER` | FK → `users.id` |
| `generated_at` | `DATETIME2(3)` | |

### `download_logs` (RF-55, RNF-49)

| Column | Type | Description |
|---------|------|-------------|
| `id` | `UNIQUEIDENTIFIER` | PK |
| `user_id` | `UNIQUEIDENTIFIER` | FK → `users.id` |
| `resource_type` | `NVARCHAR(50)` | `contract`, `report`, `document` |
| `resource_id` | `UNIQUEIDENTIFIER` | Resource ID |
| `downloaded_at` | `DATETIME2(3)` | |

---

## Notifications

### `notifications` (RF-50, RF-51)

| Column | Type | Description |
|---------|------|-------------|
| `id` | `UNIQUEIDENTIFIER` | PK |
| `analysis_id` | `UNIQUEIDENTIFIER` | FK → `analyses.id` |
| `user_id` | `UNIQUEIDENTIFIER` | FK → `users.id` (client) |
| `lawyer_email` | `NVARCHAR(320)` | Recipient |
| `decision` | `NVARCHAR(MAX)` | User decision |
| `status` | `NVARCHAR(32)` | `pending`, `sent`, `failed` |
| `sent_at` | `DATETIME2(3)` | Actual send time |
| `created_at` | `DATETIME2(3)` | |

---

## Contract comparison (P1)

### `contract_comparisons` (RF-59)

| Column | Type | Description |
|---------|------|-------------|
| `id` | `UNIQUEIDENTIFIER` | PK |
| `base_contract_id` | `UNIQUEIDENTIFIER` | FK → `contracts.id` |
| `compare_contract_id` | `UNIQUEIDENTIFIER` | FK → `contracts.id` |
| `created_by` | `UNIQUEIDENTIFIER` | FK → `users.id` |
| `summary` | `NVARCHAR(MAX)` | Difference summary |
| `risk_delta` | `NVARCHAR(16)` | Risk change (RF-62) |
| `created_at` | `DATETIME2(3)` | |

### `comparison_changes` (RF-60, RF-61)

| Column | Type | Description |
|---------|------|-------------|
| `id` | `UNIQUEIDENTIFIER` | PK |
| `comparison_id` | `UNIQUEIDENTIFIER` | FK → `contract_comparisons.id` |
| `change_type` | `NVARCHAR(50)` | `added`, `removed`, `modified` |
| `category` | `NVARCHAR(100)` | Affected clause or field |
| `description` | `NVARCHAR(MAX)` | Change detail |
| `old_value` | `NVARCHAR(MAX)` | Previous value |
| `new_value` | `NVARCHAR(MAX)` | New value |

---

## Human-in-the-loop (P2)

### `finding_reviews` (RF-68)

| Column | Type | Description |
|---------|------|-------------|
| `id` | `UNIQUEIDENTIFIER` | PK |
| `finding_id` | `UNIQUEIDENTIFIER` | FK → `findings.id` |
| `lawyer_id` | `UNIQUEIDENTIFIER` | FK → `users.id` |
| `verdict` | `NVARCHAR(32)` | `correct`, `incorrect`, `not_relevant` |
| `notes` | `NVARCHAR(MAX)` | Comments |
| `created_at` | `DATETIME2(3)` | |

### `analysis_approvals` (RF-69)

| Column | Type | Description |
|---------|------|-------------|
| `id` | `UNIQUEIDENTIFIER` | PK |
| `analysis_id` | `UNIQUEIDENTIFIER` | FK → `analyses.id` UK |
| `lawyer_id` | `UNIQUEIDENTIFIER` | FK → `users.id` |
| `approved_at` | `DATETIME2(3)` | |
| `notes` | `NVARCHAR(MAX)` | |

---

## Main relationships

```
users 1──* contracts
contracts 1──* contract_documents
contracts 1──* contract_parties
contracts 1──* analyses
analyses 1──* extracted_fields
analyses 1──* clauses
analyses 1──* findings
analyses 1──* analysis_llm_runs
findings 1──* legal_citations
findings 0..1──* finding_reviews
```

---

## Security and access

| Requirement | Implementation |
|---------------|----------------|
| RNF-19 | Documents stored in DB as `VARBINARY(MAX)` (`file_content`) |
| RNF-21 | Temporary download URLs via API, not in DB |
| RF-53 | Soft delete on `contracts` and `contract_documents` |
| RF-54 | Retention policy + `SOFT_DELETE_RETENTION_DAYS` |
| RF-02 | `users.role_id` + API logic |

---

## Requirements covered

| ID | DB coverage |
|----|----------------|
| RF-01, RF-02 | `users`, `roles` |
| RF-03–RF-08 | `contract_documents` |
| RF-09–RF-10 | `contracts.perspective`, `contracts.jurisdiction` |
| RF-11–RF-17 | `extracted_fields`, `contract_parties` |
| RF-18–RF-28 | `clauses`, `findings` |
| RF-37 | `analyses.summary_executive` |
| RF-41–RF-43 | `chat_sessions`, `chat_messages` |
| RF-46–RF-49 | `reports` |
| RF-50–RF-51 | `notifications` |
| RF-52–RF-57 | `contracts`, `contract_documents` |
| RF-55, RNF-49 | `download_logs` |
| RF-56, RF-58 | States on `contracts`, `analyses` |
| RF-59–RF-62 | `contract_comparisons`, `comparison_changes` |
| RF-64, RNF-48 | `analysis_llm_runs` |
| RF-68–RF-69 | `finding_reviews`, `analysis_approvals` |

---

## Implementation next steps

1. Run `setup_database.bat` or scripts in order (`00-create-database.sql` → `ddl.sql` → `seed.sql` → migrations).
2. ~~Integrate Python data access layer~~ ✅ pyodbc + repositories (`data/repositories/`).
3. ~~Migrate in-memory users to `users` table~~ ✅ `UserRepository`.
4. ~~Store documents in DB~~ ✅ `file_content VARBINARY(MAX)` (migration `01-add-file-content.sql`).
5. Implement text extraction (RF-06), OCR (RF-07), and analysis pipeline.
6. Add additional versioned migrations as the schema evolves.
