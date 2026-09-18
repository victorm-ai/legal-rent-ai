# Configuración en SQL Server Management Studio

Guía para crear la base de datos **LegalRentAI** y el esquema `[app]` en SQL Server local.

## Requisitos

| Requisito | Detalle |
|-----------|---------|
| SQL Server | 2019+ (Express, Developer o Standard) |
| SSMS | Cualquier versión reciente |
| Autenticación | Windows (`localhost`) o SQL Server con usuario/contraseña |

## Opción A — Script automático (recomendado)

Desde la raíz del proyecto, ejecuta:

```powershell
.\setup_database.bat
```

Esto crea la base de datos, el esquema `[app]`, las **23 tablas**, aplica migraciones incrementales y los usuarios demo (`lawyer`, `client`).

Si ya tienes `LegalRentAI` de una versión anterior del proyecto:

```powershell
.\apply_migrations.bat
```

## Opción B — Manual en SSMS

### 1. Conectar al servidor

1. Abre **SQL Server Management Studio**
2. **Connect** → Server name: **`localhost`** (instancia por defecto)
3. Authentication: **Windows Authentication** (o SQL Server si lo configuraste)

> **Error 26 en SSMS:** suele indicar un nombre de instancia incorrecto. En muchas instalaciones **no** existe `SQLEXPRESS`. Usa `localhost` sin sufijo `\instancia` salvo que sepas que tienes una instancia con nombre en ejecución.

> **Error de certificado SSL** (*"La cadena de certificación fue emitida por una entidad en la que no se confía"*): en SSMS 19+ el cifrado viene activado por defecto. En el cuadro **Connect to Server**, abre **Options >>** → pestaña **Connection Properties** → marca **Trust server certificate** (*Confiar en el certificado de servidor*). Es normal en SQL Server local con certificado autofirmado.

Nombres alternativos válidos para la instancia por defecto: `.`, `(local)`, nombre del equipo.

Si tienes varias instancias, comprueba cuál está activa en `services.msc` → **SQL Server (MSSQLSERVER)** = instancia por defecto.

### 2. Ejecutar scripts en orden

Abre cada archivo con **File → Open → File** y pulsa **Execute** (F5):

| Orden | Archivo | Qué hace |
|-------|---------|----------|
| 1 | `00-create-database.sql` | Crea la BD `LegalRentAI` |
| 2 | `ddl.sql` | Crea esquema `[app]` y tablas |
| 3 | `seed.sql` | Inserta usuarios demo (opcional) |
| 4 | `migrations/run-all-incremental.sql` | Alinea BDs antiguas con el DDL actual (idempotente) |
| 5 | `migrations/12-migrate-remove-administrator.sql` | Solo si aún existe el rol `administrator` |

> Los scripts son idempotentes: si la BD o las tablas ya existen, no fallan.

### 3. Verificar en SSMS

En **Object Explorer**:

```
Databases
└── LegalRentAI
    └── Tables
        └── app.roles
        └── app.users
        └── app.contracts
        └── ... (23 tablas en total)
```

Consulta rápida:

```sql
USE LegalRentAI;
SELECT s.name AS schema_name, t.name AS table_name
FROM sys.tables t
JOIN sys.schemas s ON t.schema_id = s.schema_id
WHERE s.name = N'app'
ORDER BY t.name;
```

Deberías ver **23 tablas** (incluye `chat_llm_call_events`).

## Usuarios demo (seed)

| Email | Contraseña | Rol |
|-------|------------|-----|
| abogado@contractes.com | abogado123 | lawyer |
| code.zemoreno@gmail.com | cliente123 | client |

> El backend autentica y persiste contratos contra SQL Server (`LegalRentAI`). Usuarios demo en `seed.sql`; documentos en `app.contract_documents.file_content`.

## Conexión desde la aplicación

Cadena de conexión de ejemplo (Windows Auth); la app lee `DB_*` desde `.env` en la raíz del repo:

```
Server=localhost;Database=LegalRentAI;Trusted_Connection=True;TrustServerCertificate=True;
```

SQL Server Authentication:

```
Server=localhost;Database=LegalRentAI;User Id=sa;Password=<tu_password>;TrustServerCertificate=True;
```

## Referencias

- [schema-design.md](./schema-design.md) — modelo ER y decisiones de diseño
- [ddl.sql](./ddl.sql) — DDL completo
- [README.md](./README.md) — índice de documentación de BD
