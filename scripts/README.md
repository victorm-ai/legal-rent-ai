# Scripts — Legal Rent AI

Utilities run from the **repository root** (`python scripts/...` or root `.bat` files).

## Layout

| Folder | Contents |
|---------|-----------|
| [`windows/`](./windows/) | `.bat` for local SSMS (`setup_database`, `apply_migrations`, `start_frontend`) |
| [`docker/`](./docker/) | Local Compose (`docker-up`, `docker-clean`, Docker data directory) |
| [`azure/`](./azure/) | LIDR deploy (`deploy-lidr.ps1`) and ACS Email probe (`probe_acs_email_sender.py`) |
| [`db/`](./db/) | SQL schema verification (`verify_database_schema.py`) |
| [`maintenance/`](./maintenance/) | Demo data cleanup (`purge_all_contracts`, `cleanup_lawyer_test_data`, …) |
| [`corpus/`](./corpus/) | Regenerate `docs/legal-sources/cag-corpus-v1.md` from PDFs |
| [`docs/`](./docs/) | Documentation maintenance (`update_requirements_status.py`) |

## Root shortcuts

Files `setup_database.bat`, `apply_migrations.bat`, and `start_frontend.bat` delegate to `scripts/windows/`.
