# Carga de contratos — RF-03, RF-04, RF-05, RF-08, RF-53, RF-54

Documentación del módulo de carga y almacenamiento de documentos contractuales.

## Requerimientos cubiertos

| ID | Prioridad | Descripción | Estado |
|----|-----------|-------------|--------|
| RF-03 | P0 | Cargar contratos en formato PDF y DOCX | ✅ Implementado |
| RF-04 | P0 | Rechazar archivos superiores a 25 MB | ✅ Implementado |
| RF-05 | P0 | Asociar múltiples documentos al mismo contrato | ✅ Implementado |
| RF-08 | P0 | Identificar automáticamente el tipo de documento | ✅ Implementado |
| RF-53 | P0 | No eliminación física desde la UI del MVP | ✅ Implementado |
| RF-54 | P1 | Política básica de retención de documentos | ✅ Implementado |

## Resumen

| Atributo | Valor |
|----------|-------|
| Formatos permitidos | PDF (`.pdf`), Word (`.docx`) |
| Tamaño máximo | 25 MB por archivo |
| Persistencia | SQL Server — columna `app.contract_documents.file_content` (`VARBINARY(MAX)`) |
| Tipos de documento | `main_contract`, `annex`, `other` (RF-08); `lawyer_revision` (subida del abogado) |
| Perspectiva de análisis | `landlord`, `tenant`, `neutral` (al crear contrato) |

> **Decisión de diseño:** en el MVP los archivos se almacenan como binario en la base de datos, no en Blob Storage ni filesystem. Los reportes exportados (RF-46+) podrán usar almacenamiento externo más adelante.

## Estructura del módulo

```
document/
├── validation.py          # Validación de extensión, tamaño, MIME y magic bytes
├── text_extractor.py      # Extracción de texto parcial (PDF/DOCX) para clasificación
└── classifier.py          # Clasificación automática main_contract / annex / other (RF-08)

data/
├── contract_dto.py        # DTOs ContractDTO, ContractDocumentDTO
├── database.py            # Conexión pyodbc
└── repositories/
    ├── contract_repository.py
    └── contract_document_repository.py

services/
└── contract_service.py    # Lógica de negocio y autorización

api/
├── routes/contracts.py    # Endpoints REST
└── schemas/contracts.py   # Modelos Pydantic de respuesta
```

## Flujo de carga

```mermaid
sequenceDiagram
    actor User as Usuario
    participant API as POST /contracts
    participant Svc as ContractService
    participant Val as document.validation
    participant CR as ContractRepository
    participant DR as ContractDocumentRepository
    participant DB as SQL Server

    User->>API: multipart file + perspective
    API->>API: Leer bytes (límite 25 MB)
    API->>Svc: validate_upload
    Svc->>Val: extensión, MIME, magic bytes
    Val-->>Svc: ValidatedDocument
    Svc->>Svc: classify_document (RF-08)
    Svc->>CR: create contract
    CR->>DB: INSERT app.contracts
    Svc->>DR: create document
    DR->>DB: INSERT app.contract_documents (file_content)
    Svc-->>API: ContractDTO
    API-->>User: 201 Created
```

## API REST

Detalle completo en [api.md](./api.md#contratos--contracts).

| Método | Ruta | Descripción |
|--------|------|-------------|
| `POST` | `/contracts` | Crear contrato y subir el primer documento |
| `GET` | `/contracts` | Listar contratos |
| `GET` | `/contracts/{id}` | Detalle con metadatos de documentos |
| `DELETE` | `/contracts/{id}` | Soft delete del contrato y sus documentos (RF-53) |
| `POST` | `/contracts/{id}/documents` | Adjuntar documento adicional (RF-05) |
| `GET` | `/contracts/{id}/documents` | Listar documentos del contrato |
| `GET` | `/contracts/{id}/documents/{doc_id}/download` | Descargar binario |

Todos los endpoints requieren **JWT Bearer token**.

### Ejemplo — Crear contrato con documento

```http
POST /contracts HTTP/1.1
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
Content-Type: multipart/form-data

file: (binary PDF o DOCX)
perspective: tenant
title: Commercial Lease Agreement
```

El campo `document_type` **no se envía en la petición**; el backend lo infiere y lo devuelve en la respuesta (RF-08).

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

### Ejemplo — Adjuntar anexo (RF-05)

```http
POST /contracts/{contract_id}/documents HTTP/1.1
Authorization: Bearer ...
Content-Type: multipart/form-data

file: (binary)
```

El tipo (`main_contract`, `annex`, `other`) se detecta automáticamente al subir el archivo.

## Validaciones (RF-03, RF-04)

| Validación | Error HTTP | Mensaje |
|------------|------------|---------|
| Extensión no permitida | 400 | `Only PDF and DOCX files are allowed` |
| Archivo vacío | 400 | `Uploaded file is empty` |
| Tamaño > 25 MB | 413 | `File exceeds the maximum allowed size of 25 MB` |
| Contenido no coincide con formato | 400 | `File content does not match the declared format` |
| Perspectiva inválida | 400 | `Perspective must be landlord, tenant, or neutral` |

Comprobaciones aplicadas:

1. Extensión `.pdf` o `.docx`
2. Tamaño en bytes (stream con límite en API y validación en servicio)
3. MIME type (`application/pdf` o DOCX OpenXML)
4. Magic bytes: `%PDF` para PDF; `PK\x03\x04` para DOCX (ZIP)

## Clasificación automática (RF-08)

Al crear un contrato o adjuntar un documento, `ContractService` invoca `document.classifier.classify_document` con:

| Señal | Ejemplos |
|-------|----------|
| Nombre de archivo | `Anexo_*`, `Contrato_*`, `Identificacion_*` |
| Contenido (vista previa) | «contrato de arrendamiento», «anexo al contrato» |
| Contexto | Primer documento → sesgo a `main_contract`; adicionales → sesgo a `annex` / `other` |

Valores posibles en `document_type`:

| Valor | Descripción |
|-------|-------------|
| `main_contract` | Contrato principal de arrendamiento |
| `annex` | Anexo, addendum o apéndice |
| `other` | Identificación, recibos, pólizas u otros relacionados |

El frontend muestra la etiqueta detectada tras la carga y en el visor de documentos.

## Soft delete (RF-53)

Desde el dashboard, el **cliente** propietario (o según reglas del servicio para el abogado) puede eliminar un contrato. La operación:

1. Marca `app.contracts.is_deleted = 1` y registra `deleted_at`.
2. Marca `app.contract_documents.is_deleted = 1` para todos los documentos del contrato.
3. **No** borra filas ni binarios de la base de datos.

El diálogo de confirmación aclara que el contrato se archiva, no se destruye. Tras el soft delete deja de aparecer en listados habituales del cliente; metadatos incluyen `purge_eligible_at` según la política.

## Retención de documentos (RF-54)

Política básica configurable:

| Regla | Valor por defecto |
|-------|-------------------|
| Contratos activos | Se conservan mientras estén en uso |
| Contratos archivados (soft delete) | **365 días** antes de ser elegibles para purga permanente |

Variable de entorno:

```bash
SOFT_DELETE_RETENTION_DAYS=365
```

**Endpoint HTTP implementado:**

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/contracts/retention-policy` | Política vigente (cualquier usuario autenticado) |

La **purga física** está en `backend/services/retention_service.py` (`purge_expired()`), invocable desde scripts o tareas programadas; **no** hay aún `GET/POST /contracts/retention/*` en la API.

La purga **no** elimina contratos archivados con dependencias bloqueantes (análisis/comparaciones), según reglas del repositorio.

El frontend muestra la política en el diálogo de eliminación.

## Autorización

| Acción | client | lawyer |
|--------|--------|--------|
| Crear contrato / adjuntar documentos | ✅ | ❌ (excepto `POST .../lawyer-revision`) |
| Ver / listar | ✅ (propios) | ✅ (visibilidad ampliada) |
| Descargar | ✅ (propios) | ✅ |
| Eliminar (soft delete) | ✅ (propios) | según reglas del servicio |
| Subir revisión editada | ❌ | ✅ |

## Base de datos

Tablas involucradas:

| Tabla | Uso |
|-------|-----|
| `app.contracts` | Metadatos del contrato (perspectiva, estado, título) |
| `app.contract_documents` | Nombre, tipo, MIME, tamaño y **contenido binario** |

Consulta de verificación en SSMS:

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

Migración para BDs creadas antes del almacenamiento binario: `docs/database/migrations/01-add-file-content.sql`.

## Revisión del abogado y cierre (RF-56, RF-57)

| Capacidad | API / UI |
|-----------|----------|
| Subir versión editada | `POST /contracts/{id}/lawyer-revision` (`document_type` / scope `lawyer_revision`) |
| Comparar original vs editado | `POST/GET /contracts/{id}/revision-comparison*` |
| Versión firmada (flag) | `POST /contracts/{id}/documents` con `is_signed_version=true` (RF-57) |
| Cierre administrativo | Abogado: `PATCH /contracts/{id}` → `status=terminated` + `closure_notes` (`ContractClosureDialog`) |
| Coordinación post-cierre | Agente + correo con enlace a `/schedule-signing?token=`; API pública `/public/signing-schedule` |

Flujo de estados activo en UI: `draft` → `in_review` → `approved` → `terminated`. Solo `terminated` bloquea ediciones (`LOCKED_STATUSES`).

## Configuración

Variable opcional en `.env`:

```bash
# Tamaño máximo de upload (default: 26214400 = 25 MB)
MAX_UPLOAD_SIZE_BYTES=26214400
```

Requiere la misma conexión SQL Server que autenticación (`DB_SERVER`, `DB_NAME`, etc.). Ver [authentication.md](./authentication.md#configuración).

## Pruebas

```bash
pytest tests/integration/test_contracts.py
pytest tests/unit/test_document_classifier.py
pytest tests/integration/test_retention.py
pytest tests/unit/test_text_extraction.py
pytest tests/integration/test_phase1.py
```

Cubre validación PDF, límite 25 MB, rechazo de extensiones, flujo completo (crear contrato + anexo + descarga), clasificación automática, extracción de texto persistida, OCR, log de descargas y transiciones de estado.

## Referencias

- [api.md](./api.md) — especificación REST
- [database/schema-design.md](./database/schema-design.md) — modelo `contract_documents`
- [requirements.md](./requirements.md) — RF-03 a RF-08
