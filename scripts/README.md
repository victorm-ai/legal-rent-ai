# Scripts — Legal Rent AI

Utilidades ejecutadas desde la **raíz del repositorio** (`python scripts/...` o `.bat` en la raíz).

## Layout

| Carpeta | Contenido |
|---------|-----------|
| [`windows/`](./windows/) | `.bat` para SSMS local (`setup_database`, `apply_migrations`, `start_frontend`) |
| [`docker/`](./docker/) | Compose local (`docker-up`, `docker-clean`, directorio de datos Docker) |
| [`azure/`](./azure/) | Despliegue LIDR (`deploy-lidr.ps1`) y prueba ACS Email (`probe_acs_email_sender.py`) |
| [`db/`](./db/) | Verificación de esquema SQL (`verify_database_schema.py`) |
| [`maintenance/`](./maintenance/) | Limpieza de datos demo (`purge_all_contracts`, `cleanup_lawyer_test_data`, …) |
| [`corpus/`](./corpus/) | Regenerar `docs/legal-sources/cag-corpus-v1.md` desde PDFs |
| [`docs/`](./docs/) | Mantenimiento de documentación (`update_requirements_status.py`) |

## Atajos en la raíz

Los archivos `setup_database.bat`, `apply_migrations.bat` y `start_frontend.bat` delegan en `scripts/windows/`.
