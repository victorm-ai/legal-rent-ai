# Authentication System — RF-01

## Description

This module implements user authentication for the contract analysis system, in accordance with requirement **RF-01** in the specifications document.

### Implemented Features

- ✅ User management with **Lawyer** and **Client** roles (`lawyer`, `client`)
- ✅ Secure password hashing with PBKDF2-HMAC-SHA256
- ✅ JWT token generation and validation with expiration
- ✅ REST API for login/logout/registration
- ✅ Role-based authorization middleware
- ✅ Persistence in SQL Server (`LegalRentAI`, tables `app.users` / `app.roles`)

## Module structure

Code in **`backend/auth/`**. JWT middleware in **`backend/api/middleware/auth.py`**.

```
backend/auth/
├── models.py        # UserCredentials, Token, PasswordHash
├── token.py         # JWT encode/decode
├── service.py       # Login and registration
└── ...
```

## Basic usage

### 1. User login

```python
from auth.models import UserCredentials
from auth.service import AuthService

# Create service
auth_service = AuthService()

# Attempt login
credentials = UserCredentials(email="code.zemoreno@gmail.com", password="cliente123")
result = auth_service.login(credentials)

if result.success:
    print(f"Token: {result.token.access_token}")
else:
    print(f"Error: {result.message}")
```

### 2. Register new user

```python
from domain.entities import Role

result = auth_service.register(
    email="nuevo@contractes.com",
    name="Nuevo Usuario",
    role=Role.CLIENT,
    password="contraseña123"
)

if result.success:
    print(f"User registered with token: {result.token.access_token}")
```

### 3. JWT token validation

```python
from auth.token import JWTTransformer
from datetime import datetime

# Create transformer
transformer = JWTTransformer(secret_key="tu-secret-key")

# Decode token
payload = transformer.decode(token_string)

if payload is None:
    # Invalid or expired token
    pass
else:
    # Valid token; use payload.user_id, payload.email, payload.role
    print(f"User: {payload.email}")
```

### 4. Password hashing

```python
from auth.models import PasswordHash

# Generate hash
password = "mi-contraseña-segura"
hash_result = PasswordHash.generate(password)
print(f"Salt: {hash_result.salt}")
print(f"Hash: {hash_result.hashed_password}")

# Verify password
is_valid = hash_result.verify(password)  # True
```

## API endpoints

Full detail in [api.md](./api.md). See [Summary of implemented endpoints](./api.md#summary-of-implemented-endpoints).

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
{ ... same format as login ... }

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

### Using authorization middleware

```python
from fastapi import Depends
from api.middleware.auth import require_lawyer

@app.get("/lawyer-only")
def lawyer_area(current_user = Depends(require_lawyer)):
    return {"message": f"Hello {current_user['email']}"}
```

## User roles

| Role (API value) | Description | Main access |
|-----------------|-------------|---------------------|
| `client` | Client / tenant | Upload contracts, analyze, chat, reports, notify lawyer |
| `lawyer` | Lawyer | Review findings, approve analyses, edited revision, closure (`approved→terminated`), export feedback |

The SQL catalog no longer includes `administrator` (see [`docs/database/migrations/12-migrate-remove-administrator.sql`](./database/migrations/12-migrate-remove-administrator.sql)).

### Other signed tokens (same `SECRET_KEY`)

Besides the session JWT, the `backend/auth/` module includes scoped token services:

| Service | Usage |
|----------|-----|
| `signing_schedule_token.py` | Public link `/schedule-signing?token=` (signing schedule after closure) |
| Document download tokens | `POST .../download-token` + `GET .../download?token=` (TTL `DOWNLOAD_TOKEN_TTL_SECONDS`) |

They do not share the login/logout flow; they are validated on specific routes.

## Configuration

### Environment variables

Copy `.env.example` to `.env` and adjust for your environment:

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

The database must exist with schema applied (`setup_database.bat` or scripts in `docs/database/`).

Demo users in DB: see [database/setup-ssms.md](./database/setup-ssms.md).

### Generate secret key

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

## Tests

Run the test script:

```bash
pytest tests/integration/test_auth.py
# or quick smoke:
python tests/smoke/auth_quick.py
```

Expected output:
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

## Security

### Implementation details

1. **Password hashing**: Uses `PBKDF2-HMAC-SHA256` with:
   - Random salt (16 bytes hex)
   - 100,000 iterations
   - Constant-time comparison to prevent timing attacks

2. **JWT tokens**:
   - Configurable expiration
   - HMAC-SHA256 signature
   - Expiration and integrity validation

3. **Role middleware**: Role verification on each protected request

### Production recommendations

- ✅ Use environment variables for `SECRET_KEY`
- ✅ Implement rate limiting on authentication endpoints
- ✅ Add logging of failed login attempts
- ✅ Implement account lockout after N failed attempts
- ✅ Consider 2FA/MFA for production
- ✅ Require HTTPS

## Requirements fulfilled

| ID | Requirement | Status |
|----|---------------|--------|
| RF-01 | The system shall allow user authentication | ✅ Implemented |
| RF-02 | Lawyer and Client roles in MVP (`lawyer`, `client`; no administrator in SQL catalog) | ✅ Implemented |

See [contracts.md](./contracts.md) for RF-03, RF-04, and RF-05.

## Technical notes

### Resolving circular references

The `auth/models.py` module imports `Role` from `domain.entities`, but `AuthUser.to_user()` must import `User`. This is resolved by importing locally inside the method.

### Libraries used

- **PyJWT**: JWT token generation and validation
- **pyodbc**: SQL Server access
- **pydantic-settings**: Configuration from environment variables
- **Python Standard Library** (`hashlib`, `secrets`): Secure password hashing

### Data layer

| Module | Responsibility |
|--------|-----------------|
| `config/settings.py` | Connection and secrets |
| `data/database.py` | pyodbc context manager |
| `data/repositories/user_repository.py` | CRUD for `app.users` |
| `auth/service.py` | Login/register using the repository |

## Next steps

1. [ ] Refresh tokens
2. [ ] User management endpoints (admin)
3. [ ] Password recovery
4. [ ] Rate limiting and account lockout
