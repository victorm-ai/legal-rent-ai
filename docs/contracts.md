# Contract upload — RF-03, RF-04, RF-05, RF-08, RF-53, RF-54

Documentation for the contract document upload and storage module.

## Requirements covered

| ID | Priority | Description | Status |
|----|-----------|-------------|--------|
| RF-03 | P0 | Upload contracts in PDF and DOCX format | ✅ Implemented |
| RF-04 | P0 | Reject files larger than 25 MB | ✅ Implemented |
| RF-05 | P0 | Associate multiple documents with the same contract | ✅ Implemented |
| RF-08 | P0 | Automatically identify document type | ✅ Implemented |
| RF-53 | P0 | No physical deletion from MVP UI | ✅ Implemented |
| RF-54 | P1 | Basic document retention policy | ✅ Implemented |

## Summary

| Attribute | Value |
|----------|-------|
| Allowed formats | PDF (`.pdf`), Word (`.docx`) |
| Maximum size | 25 MB per file |
| Persistence | SQL Server — column `app.contract_documents.file_content` (`VARBINARY(MAX)`) |
| Document types | `main_contract`, `annex`, `other` (RF-08); `lawyer_revision` (lawyer upload) |
| Analysis perspective | `landlord`, `tenant`, `neutral` (when creating contract) |

> **Design decision:** in the MVP files are stored as binary in the database, not in Blob Storage or the filesystem. Exported reports (RF-46+) may use external storage later.

## Module structure

```
document/
├── validation.py          # Extension, size, MIME and magic byte validation
├── text_extractor.py      # Partial text extraction (PDF/DOCX) for classification
└── classifier.py          # Automatic main_contract / annex / other classification (RF-08)

data/
├── contract_dto.py        # DTOs ContractDTO, ContractDocumentDTO
├── database.py            # pyodbc connection
└── repositories/
    ├── contract_repository.py
    └── contract_document_repository.py

services/
└── contract_service.py    # Business logic and authorization

api/
├── routes/contracts.py    # REST endpoints
└── schemas/contracts.py   # Pydantic response models
```

## Upload flow

```mermaid
sequenceDiagram
    actor User as User
    participant API as POST /contracts
    participant Svc as ContractService
    participant Val as document.validation
    participant CR as ContractRepository
    participant DR as ContractDocumentRepository
    participant DB as SQL Server

    User->>API: multipart file + perspective
    API->>API: Read bytes (25 MB limit)
    API->>Svc: validate_upload
    Svc->>Val: extension, MIME, magic bytes
    Val-->>Svc: ValidatedDocument
    Svc->>Svc: classify_document (RF-08)
    Svc->>CR: create contract
    CR->>DB: INSERT app.contracts
    Svc->>DR: create document
    DR->>DB: INSERT app.contract_documents (file_content)
    Svc-->>API: ContractDTO
    API-->>User: 201 Created
```

## REST API

Full detail in [api.md](./api.md#contracts--contracts).

| Method | Route | Description |
|--------|------|-------------|
| `POST` | `/contracts` | Create contract and upload first document |
| `GET` | `/contracts` | List contracts |
| `GET` | `/contracts/{id}` | Detail with document metadata |
| `DELETE` | `/contracts/{id}` | Soft delete contract and its documents (RF-53) |
| `POST` | `/contracts/{id}/documents` | Attach additional document (RF-05) |
| `GET` | `/contracts/{id}/documents` | List contract documents |
| `GET` | `/contracts/{id}/documents/{doc_id}/download` | Download binary |

All endpoints require **JWT Bearer token**.

### Example — Create contract with document

```http
POST /contracts HTTP/1.1
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
Content-Type: multipart/form-data

file: (binary PDF or DOCX)
perspective: tenant
title: Commercial Lease Agreement
```

The `document_type` field **is not sent in the request**; the backend infers it and returns it in the response (RF-08).

**Response 201:**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "11111111-1111-1111-1111-111111111103",
  "perspective": "tenant",
  "jurisdiction": null,
  "status": "draft",
  "title": "Commercial Lease Agreement",
  "documents": [
    {
      "id": "...",
      "file_name": "contrato.pdf",
      "document_type": "main_contract",
      "mime_type": "application/pdf",
      "file_size_bytes": 245760,
      "page_count": null,
      "uploaded_at": "2026-03-06T17:30:00.000Z"
    }
  ],
  "created_at": "2026-03-06T17:30:00.000Z",
  "updated_at": "2026-03-06T17:30:00.000Z"
}
```

### Example — Attach annex (RF-05)

```http
POST /contracts/{contract_id}/documents HTTP/1.1
Authorization: Bearer ...
Content-Type: multipart/form-data

file: (binary)
```

The type (`main_contract`, `annex`, `other`) is detected automatically on upload.

## Validations (RF-03, RF-04)

| Validation | HTTP error | Message |
|------------|------------|---------|
| Disallowed extension | 400 | `Only PDF and DOCX files are allowed` |
| Empty file | 400 | `Uploaded file is empty` |
| Size > 25 MB | 413 | `File exceeds the maximum allowed size of 25 MB` |
| Content does not match format | 400 | `File content does not match the declared format` |
| Invalid perspective | 400 | `Perspective must be landlord, tenant, or neutral` |

Checks applied:

1. Extension `.pdf` or `.docx`
2. Size in bytes (stream limit in API and validation in service)
3. MIME type (`application/pdf` or DOCX OpenXML)
4. Magic bytes: `%PDF` for PDF; `PK\x03\x04` for DOCX (ZIP)

## Automatic classification (RF-08)

When creating a contract or attaching a document, `ContractService` invokes `document.classifier.classify_document` with:

| Signal | Examples |
|-------|----------|
| File name | `Anexo_*`, `Contrato_*`, `Identificacion_*` |
| Content (preview) | «contrato de arrendamiento», «anexo al contrato» |
| Context | First document → bias to `main_contract`; additional → bias to `annex` / `other` |

Possible values in `document_type`:

| Value | Description |
|-------|-------------|
| `main_contract` | Main lease contract |
| `annex` | Annex, addendum, or appendix |
| `other` | ID, receipts, policies, or other related documents |

The frontend shows the detected label after upload and in the document viewer.

## Soft delete (RF-53)

From the dashboard, the owning **client** (or per service rules for the lawyer) can delete a contract. The operation:

1. Sets `app.contracts.is_deleted = 1` and records `deleted_at`.
2. Sets `app.contract_documents.is_deleted = 1` for all contract documents.
3. Does **not** delete rows or binary data from the database.

The confirmation dialog clarifies that the contract is archived, not destroyed. After soft delete it no longer appears in the client’s usual listings; metadata includes `purge_eligible_at` per policy.

## Document retention (RF-54)

Configurable basic policy:

| Rule | Default value |
|-------|-------------------|
| Active contracts | Retained while in use |
| Archived contracts (soft delete) | **365 days** before eligible for permanent purge |

Environment variable:

```bash
SOFT_DELETE_RETENTION_DAYS=365
```

**Implemented HTTP endpoint:**

| Method | Route | Description |
|--------|------|-------------|
| `GET` | `/contracts/retention-policy` | Current policy (any authenticated user) |

**Physical purge** is in `backend/services/retention_service.py` (`purge_expired()`), callable from scripts or scheduled tasks; there is **no** `GET/POST /contracts/retention/*` on the API yet.

Purge does **not** remove archived contracts with blocking dependencies (analyses/comparisons), per repository rules.

The frontend shows the policy in the delete dialog.

## Authorization

| Action | client | lawyer |
|--------|--------|--------|
| Create contract / attach documents | ✅ | ❌ (except `POST .../lawyer-revision`) |
| View / list | ✅ (own) | ✅ (expanded visibility) |
| Download | ✅ (own) | ✅ |
| Delete (soft delete) | ✅ (own) | per service rules |
| Upload edited revision | ❌ | ✅ |

## Database

Tables involved:

| Table | Usage |
|-------|-------|
| `app.contracts` | Contract metadata (perspective, status, title) |
| `app.contract_documents` | Name, type, MIME, size, and **binary content** |

Verification query in SSMS:

```sql
USE LegalRentAI;

SELECT
    c.title,
    d.file_name,
    d.document_type,
    d.file_size_bytes,
    d.uploaded_at
FROM app.contract_documents d
JOIN app.contracts c ON c.id = d.contract_id
WHERE d.is_deleted = 0
ORDER BY d.uploaded_at DESC;
```

Migration for DBs created before binary storage: `docs/database/migrations/01-add-file-content.sql`.

## Lawyer revision and closure (RF-56, RF-57)

| Capability | API / UI |
|-----------|----------|
| Upload edited version | `POST /contracts/{id}/lawyer-revision` (`document_type` / scope `lawyer_revision`) |
| Compare original vs edited | `POST/GET /contracts/{id}/revision-comparison*` |
| Signed version (flag) | `POST /contracts/{id}/documents` with `is_signed_version=true` (RF-57) |
| Administrative closure | Lawyer: `PATCH /contracts/{id}` → `status=terminated` + `closure_notes` (`ContractClosureDialog`) |
| Post-closure coordination | Agent + email with link to `/schedule-signing?token=`; public API `/public/signing-schedule` |

Active UI status flow: `draft` → `in_review` → `approved` → `terminated`. Only `terminated` locks edits (`LOCKED_STATUSES`).

## Configuration

Optional variable in `.env`:

```bash
# Maximum upload size (default: 26214400 = 25 MB)
MAX_UPLOAD_SIZE_BYTES=26214400
```

Requires the same SQL Server connection as authentication (`DB_SERVER`, `DB_NAME`, etc.). See [authentication.md](./authentication.md#configuration).

## Tests

```bash
pytest tests/integration/test_contracts.py
pytest tests/unit/test_document_classifier.py
pytest tests/integration/test_retention.py
pytest tests/unit/test_text_extraction.py
pytest tests/integration/test_phase1.py
```

Covers PDF validation, 25 MB limit, extension rejection, full flow (create contract + annex + download), automatic classification, persisted text extraction, OCR, download logs, and status transitions.

## References

- [api.md](./api.md) — REST specification
- [database/schema-design.md](./database/schema-design.md) — `contract_documents` model
- [requirements.md](./requirements.md) — RF-03 through RF-08
