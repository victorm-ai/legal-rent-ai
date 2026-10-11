# SQL Server Management Studio setup

Guide to create the **LegalRentAI** database and the `[app]` schema on local SQL Server.

## Requirements

| Requirement | Detail |
|-----------|---------|
| SQL Server | 2019+ (Express, Developer, or Standard) |
| SSMS | Any recent version |
| Authentication | Windows (`localhost`) or SQL Server with username/password |

## Option A — Automated script (recommended)

From the project root, run:

```powershell
.\setup_database.bat
```

This creates the database, the `[app]` schema, all **23 tables**, applies incremental migrations, and demo users (`lawyer`, `client`).

If you already have `LegalRentAI` from an earlier project version:

```powershell
.\apply_migrations.bat
```

## Option B — Manual in SSMS

### 1. Connect to the server

1. Open **SQL Server Management Studio**
2. **Connect** → Server name: **`localhost`** (default instance)
3. Authentication: **Windows Authentication** (or SQL Server if configured)

> **Error 26 in SSMS:** usually means an incorrect instance name. On many installs **`SQLEXPRESS` does not exist**. Use `localhost` with no `\instance` suffix unless you know a named instance is running.

> **SSL certificate error** (*"The certificate chain was issued by an authority that is not trusted"*): in SSMS 19+ encryption is on by default. In **Connect to Server**, open **Options >>** → **Connection Properties** tab → check **Trust server certificate**. This is normal for local SQL Server with a self-signed certificate.

Other valid names for the default instance: `.`, `(local)`, computer name.

If you have multiple instances, check which is active in `services.msc` → **SQL Server (MSSQLSERVER)** = default instance.

### 2. Run scripts in order

Open each file with **File → Open → File** and press **Execute** (F5):

| Order | File | What it does |
|-------|---------|----------|
| 1 | `00-create-database.sql` | Creates `LegalRentAI` database |
| 2 | `ddl.sql` | Creates `[app]` schema and tables |
| 3 | `seed.sql` | Inserts demo users (optional) |
| 4 | `migrations/run-all-incremental.sql` | Aligns older DBs with current DDL (idempotent) |
| 5 | `migrations/12-migrate-remove-administrator.sql` | Only if the `administrator` role still exists |

> Scripts are idempotent: if the database or tables already exist, they do not fail.

### 3. Verify in SSMS

In **Object Explorer**:

```
Databases
└── LegalRentAI
    └── Tables
        └── app.roles
        └── app.users
        └── app.contracts
        └── ... (23 tables total)
```

Quick query:

```sql
USE LegalRentAI;
SELECT s.name AS schema_name, t.name AS table_name
FROM sys.tables t
JOIN sys.schemas s ON t.schema_id = s.schema_id
WHERE s.name = N'app'
ORDER BY t.name;
```

You should see **23 tables** (includes `chat_llm_call_events`).

## Demo users (seed)

| Email | Password | Role |
|-------|------------|-----|
| abogado@contractes.com | abogado123 | lawyer |
| code.zemoreno@gmail.com | cliente123 | client |

> The backend authenticates and persists contracts against SQL Server (`LegalRentAI`). Demo users in `seed.sql`; documents in `app.contract_documents.file_content`.

## Application connection

Example connection string (Windows Auth); the app reads `DB_*` from `.env` at repo root:

```
Server=localhost;Database=LegalRentAI;Trusted_Connection=True;TrustServerCertificate=True;
```

SQL Server Authentication:

```
Server=localhost;Database=LegalRentAI;User Id=sa;Password=<your_password>;TrustServerCertificate=True;
```

## References

- [schema-design.md](./schema-design.md) — ER model and design decisions
- [ddl.sql](./ddl.sql) — full DDL
- [README.md](./README.md) — database documentation index
