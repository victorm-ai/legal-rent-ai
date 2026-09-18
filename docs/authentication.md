# Sistema de Autenticación - RF-01

## Descripción

Este módulo implementa la funcionalidad de autenticación de usuarios para el sistema de análisis de contratos, conforme al requerimiento **RF-01** del documento de especificaciones.

### Características Implementadas

- ✅ Gestión de usuarios con roles **Abogado** y **Cliente** (`lawyer`, `client`)
- ✅ Hash seguro de contraseñas con PBKDF2-HMAC-SHA256
- ✅ Generación y validación de tokens JWT con expiración
- ✅ API REST para login/logout/registro
- ✅ Middleware de autorización por roles
- ✅ Persistencia en SQL Server (`LegalRentAI`, tablas `app.users` / `app.roles`)

## Estructura del módulo

Código en **`backend/auth/`**. Middleware JWT en **`backend/api/middleware/auth.py`**.

```
backend/auth/
├── models.py        # UserCredentials, Token, PasswordHash
├── token.py         # JWT encode/decode
├── service.py       # Login y registro
└── ...
```

## Uso Básico

### 1. Login de Usuario

```python
from auth.models import UserCredentials
from auth.service import AuthService

# Crear servicio
auth_service = AuthService()

# Intentar login
credentials = UserCredentials(email="code.zemoreno@gmail.com", password="cliente123")
result = auth_service.login(credentials)

if result.success:
    print(f"Token: {result.token.access_token}")
else:
    print(f"Error: {result.message}")
```

### 2. Registro de Nuevo Usuario

```python
from domain.entities import Role

result = auth_service.register(
    email="nuevo@contractes.com",
    name="Nuevo Usuario",
    role=Role.CLIENT,
    password="contraseña123"
)

if result.success:
    print(f"Usuario registrado con token: {result.token.access_token}")
```

### 3. Validación de Token JWT

```python
from auth.token import JWTTransformer
from datetime import datetime

# Crear transformer
transformer = JWTTransformer(secret_key="tu-secret-key")

# Decodificar token
payload = transformer.decode(token_string)

if payload is None:
    # Token inválido o expirado
    pass
else:
    # Token válido, usar payload.user_id, payload.email, payload.role
    print(f"Usuario: {payload.email}")
```

### 4. Hash de Contraseñas

```python
from auth.models import PasswordHash

# Generar hash
password = "mi-contraseña-segura"
hash_result = PasswordHash.generate(password)
print(f"Salt: {hash_result.salt}")
print(f"Hash: {hash_result.hashed_password}")

# Verificar contraseña
is_valid = hash_result.verify(password)  # True
```

## API Endpoints

Detalle completo en [api.md](./api.md). Ver [Resumen de endpoints implementados](./api.md#resumen-de-endpoints-implementados).

### POST /auth/login

```http
POST /auth/login HTTP/1.1
Content-Type: application/json

{
    "email": "code.zemoreno@gmail.com",
    "password": "cliente123"
}

Response (200 OK):
{
    "token_type": "bearer",
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "expires_in_minutes": 60,
    "user_id": "11111111-1111-1111-1111-111111111103",
    "email": "code.zemoreno@gmail.com",
    "name": "Sample Client",
    "role": "client"
}

Response (401 Unauthorized):
{
    "detail": "Invalid credentials"
}
```

### POST /auth/register

```http
POST /auth/register HTTP/1.1
Content-Type: application/json

{
    "email": "nuevo@contractes.com",
    "password": "nuevacontraseña123"
}

Response (200 OK):
{ ... mismo formato que login ... }

Response (400 Bad Request):
{
    "detail": "Email address is already registered"
}
```

### POST /auth/logout

```http
POST /auth/logout HTTP/1.1
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...

Response (200 OK):
{
    "message": "Signed out successfully"
}

Response (401 Unauthorized):
{
    "detail": "Token not provided"
}
```

### Uso de Middleware de Autorización

```python
from fastapi import Depends
from api.middleware.auth import require_lawyer

@app.get("/lawyer-only")
def lawyer_area(current_user = Depends(require_lawyer)):
    return {"message": f"Hola {current_user['email']}"}
```

## Roles de Usuario

| Rol (valor API) | Descripción | Accesos principales |
|-----------------|-------------|---------------------|
| `client` | Cliente / arrendatario | Subir contratos, analizar, chat, reportes, notificar abogado |
| `lawyer` | Abogado | Revisar hallazgos, aprobar análisis, revisión editada, cierre (`approved→terminated`), export feedback |

El catálogo SQL ya no incluye `administrator` (ver [`docs/database/migrations/12-migrate-remove-administrator.sql`](./database/migrations/12-migrate-remove-administrator.sql)).

### Otros tokens firmados (mismo `SECRET_KEY`)

Además del JWT de sesión, el módulo `backend/auth/` incluye servicios de tokens acotados:

| Servicio | Uso |
|----------|-----|
| `signing_schedule_token.py` | Enlace público `/schedule-signing?token=` (agenda de firma post-cierre) |
| Tokens de descarga documentos | `POST .../download-token` + `GET .../download?token=` (TTL `DOWNLOAD_TOKEN_TTL_SECONDS`) |

No comparten el flujo login/logout; se validan en rutas específicas.

## Configuración

### Variables de Entorno

Copia `.env.example` a `.env` y ajusta según tu entorno:

```bash
# JWT
SECRET_KEY=your-secret-key-here
TOKEN_EXPIRATION_MINUTES=60

# SQL Server (Windows Authentication)
DB_SERVER=localhost
DB_NAME=LegalRentAI
DB_DRIVER=ODBC Driver 17 for SQL Server
DB_TRUSTED_CONNECTION=true
```

La base de datos debe existir y tener el esquema aplicado (`setup_database.bat` o scripts en `docs/database/`).

Usuarios demo en BD: ver [database/setup-ssms.md](./database/setup-ssms.md).

### Generar Clave Secreta

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

## Pruebas

Ejecutar el script de pruebas:

```bash
pytest tests/integration/test_auth.py
# o smoke rápido:
python tests/smoke/auth_quick.py
```

Salida esperada:
```
============================================================
Legal Rent AI - Authentication Tests
============================================================

=== Password hashing ===
Correct password verification: PASSED
Wrong password rejection: PASSED

=== Auth service ===
Login successful: code.zemoreno@gmail.com (client)
Invalid password rejected: PASSED
Unknown user rejected: PASSED
Registration successful: new@contractes.com
Duplicate registration rejected: PASSED

=== JWT tokens ===
Token encode/decode: PASSED
Invalid token rejected: PASSED

============================================================
ALL TESTS PASSED
============================================================
```

## Seguridad

### Implementation Details

1. **Hashing de Contraseñas**: Se usa `PBKDF2-HMAC-SHA256` con:
   - Salt aleatorio (16 bytes hex)
   - 100,000 iteraciones
   - Comparación constante para prevenir timing attacks

2. **Tokens JWT**:
   - Expiración configurable
   - Firma HMAC-SHA256
   - Validación de expiración y integridad

3. **Middleware deRoles**: Verificación de roles en cada request protegido

### Recomendaciones para Producción

- ✅ Usar variables de entorno para `SECRET_KEY`
- ✅ Implementar rate limiting en endpoints de autenticación
- ✅ Agregar logging de intentos de login fallidos
- ✅ Implementar "account lockout" después de N intentos fallidos
- ✅ Considerar 2FA/MFA para producción
- ✅ Usar HTTPS obligatoriamente

## Requerimientos Cumplidos

| ID | Requerimiento | Estado |
|----|---------------|--------|
| RF-01 | El sistema deberá permitir autenticación de usuarios | ✅ Implementado |
| RF-02 | Roles Abogado y Cliente en MVP (`lawyer`, `client`; sin administrador en catálogo SQL) | ✅ Implementado |

Ver [contracts.md](./contracts.md) para RF-03, RF-04 y RF-05.

## Notas Técnicas

### Referencias Circulares Resolver

El módulo `auth/models.py` importa `Role` desde `domain.entities`, pero `AuthUser.to_user()` debe importar `User`. Esto se resuelve importando localmente dentro del método.

### Librerías Utilizadas

- **PyJWT**: Generación y validación de tokens JWT
- **pyodbc**: Acceso a SQL Server
- **pydantic-settings**: Configuración desde variables de entorno
- **Python Standard Library** (`hashlib`, `secrets`): Hashing seguro de contraseñas

### Capa de datos

| Módulo | Responsabilidad |
|--------|-----------------|
| `config/settings.py` | Conexión y secretos |
| `data/database.py` | Context manager pyodbc |
| `data/repositories/user_repository.py` | CRUD de `app.users` |
| `auth/service.py` | Login/register usando el repositorio |

## Próximos Pasos

1. [ ] Refresh tokens
2. [ ] Endpoints de gestión de usuarios (admin)
3. [ ] Recuperación de contraseña
4. [ ] Rate limiting y account lockout
