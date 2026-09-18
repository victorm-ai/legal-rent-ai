# C4 — Nivel 4: Código (módulo de autenticación)

El **nivel 4** detalla clases a nivel de código. Este documento cubre **`backend/auth/`** (JWT, login, registro). Otros módulos críticos (`services/`, `llm/`) se describen en el [nivel 3](./c4-level3-components.md).

## Diagrama de clases — `backend/auth/`

```mermaid
classDiagram
    direction TB

    class AuthService {
        -user_repository UserRepository
        +login(credentials) LoginResult
        +register(email, name, role, password) LoginResult
        -create_token(user) Token
    }

    class JWTTransformer {
        -secret_key str
        +encode(payload) str
        +decode(token) TokenPayload
    }

    class PasswordHash {
        +hashed_password str
        +salt str
        +generate(password) PasswordHash
        +verify(password) bool
    }

    class AuthUser {
        +id str
        +email str
        +name str
        +role Role
        +password_hash PasswordHash
        +create() AuthUser
        +verify_password(password) bool
        +to_user() User
    }

    class UserCredentials {
        +email str
        +password str
    }

    class LoginResult {
        +success bool
        +message str
        +token Token
        +user AuthUser
    }

    class Token {
        +access_token str
        +token_type str
        +expires_in_minutes int
    }

    class TokenPayload {
        +user_id str
        +email str
        +role Role
        +expires_at datetime
        +create() TokenPayload
        +is_expired() bool
    }

    class User {
        +id str
        +email str
        +name str
        +role Role
    }

    class Role {
        <<enumeration>>
        LAWYER
        CLIENT
    }

    AuthService --> AuthUser : gestiona
    AuthService --> JWTTransformer : genera tokens
    AuthService --> UserCredentials : recibe
    AuthService --> LoginResult : retorna
    AuthUser --> PasswordHash : contiene
    AuthUser --> User : to_user
    AuthUser --> Role : tiene
    LoginResult --> Token : opcional
    JWTTransformer --> TokenPayload : encode decode
    TokenPayload --> Role : incluye
    User --> Role : tiene
```

## Diagrama de secuencia — Login

```mermaid
sequenceDiagram
    actor User as Usuario
    participant Web as React LoginForm
    participant API as POST auth login
    participant Svc as AuthService
    participant JWT as JWTTransformer

    User->>Web: email y password
    Web->>API: JSON credentials
    API->>Svc: login UserCredentials
    Svc->>Svc: UserRepository.get_by_email
    Svc->>Svc: verify_password
    alt credenciales validas
        Svc->>JWT: encode TokenPayload
        JWT-->>Svc: access_token
        Svc-->>API: LoginResult success
        API-->>Web: 200 OK con token
        Web->>Web: guardar en localStorage
        Web-->>User: Dashboard
    else credenciales invalidas
        Svc-->>API: LoginResult failure
        API-->>Web: 401 Invalid credentials
        Web-->>User: mensaje de error
    end
```

## Diagrama de secuencia — Request autenticado

```mermaid
sequenceDiagram
    participant Web as React AuthContext
    participant API as FastAPI endpoint
    participant MW as RoleChecker
    participant JWT as JWTTransformer

    Web->>API: Authorization Bearer token
    API->>MW: Depends require_lawyer
    MW->>JWT: decode token
    alt token valido y rol permitido
        JWT-->>MW: TokenPayload
        MW-->>API: current_user
        API-->>Web: 200 response
    else token invalido o rol insuficiente
        MW-->>Web: 401 o 403
    end
```

## Archivos del módulo

| Archivo | Responsabilidad |
|---------|-----------------|
| `auth/service.py` | Lógica de login y registro vía `UserRepository` |
| `auth/models.py` | `AuthUser`, `PasswordHash`, `Token`, `TokenPayload`, `LoginResult` |
| `auth/token.py` | `JWTTransformer` — encode/decode HS256 |
| `data/repositories/user_repository.py` | Persistencia de usuarios en SQL Server |
| `api/routes/auth.py` | Endpoints REST |
| `api/middleware/auth.py` | `RoleChecker`, decoradores por rol |
| `auth/signing_schedule_token.py` | JWT de agenda de firma (query `token`, sin exp de sesión) |

Ver también módulo de contratos: [contracts.md](../contracts.md).

## Notas de implementación

- **Hashing**: PBKDF2-HMAC-SHA256, 100 000 iteraciones, salt aleatorio.
- **JWT**: HS256, expiración configurable (default 60 min).
- **Roles**: valores en inglés (`lawyer`, `client`).
- **Persistencia**: usuarios en `app.users` vía `UserRepository` (pyodbc). Contratos y documentos: ver [contracts.md](../contracts.md).

## Próximos diagramas de código (planificado)

| Módulo | Clases clave |
|--------|--------------|
| `document/` | `validate_upload` — PDF/DOCX, 25 MB ✅ |
| `analysis/` | `ClauseAnalyzer`, `RiskClassifier` |
| `llm/` | `LLMProvider`, `AzureOpenAIProvider` |
| `rag/` | `LegalCorpusRetriever`, `EmbeddingService` |
