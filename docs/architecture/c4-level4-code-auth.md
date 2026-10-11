# C4 — Level 4: Code (authentication module)

**Level 4** details classes at code level. This document covers **`backend/auth/`** (JWT, login, registration). Other critical modules (`services/`, `llm/`) are described at [level 3](./c4-level3-components.md).

## Class diagram — `backend/auth/`

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

    AuthService --> AuthUser : manages
    AuthService --> JWTTransformer : generates tokens
    AuthService --> UserCredentials : receives
    AuthService --> LoginResult : returns
    AuthUser --> PasswordHash : contains
    AuthUser --> User : to_user
    AuthUser --> Role : has
    LoginResult --> Token : optional
    JWTTransformer --> TokenPayload : encode decode
    TokenPayload --> Role : includes
    User --> Role : has
```

## Sequence diagram — Login

```mermaid
sequenceDiagram
    actor User as User
    participant Web as React LoginForm
    participant API as POST auth login
    participant Svc as AuthService
    participant JWT as JWTTransformer

    User->>Web: email and password
    Web->>API: JSON credentials
    API->>Svc: login UserCredentials
    Svc->>Svc: UserRepository.get_by_email
    Svc->>Svc: verify_password
    alt valid credentials
        Svc->>JWT: encode TokenPayload
        JWT-->>Svc: access_token
        Svc-->>API: LoginResult success
        API-->>Web: 200 OK with token
        Web->>Web: save to localStorage
        Web-->>User: Dashboard
    else invalid credentials
        Svc-->>API: LoginResult failure
        API-->>Web: 401 Invalid credentials
        Web-->>User: error message
    end
```

## Sequence diagram — Authenticated request

```mermaid
sequenceDiagram
    participant Web as React AuthContext
    participant API as FastAPI endpoint
    participant MW as RoleChecker
    participant JWT as JWTTransformer

    Web->>API: Authorization Bearer token
    API->>MW: Depends require_lawyer
    MW->>JWT: decode token
    alt valid token and allowed role
        JWT-->>MW: TokenPayload
        MW-->>API: current_user
        API-->>Web: 200 response
    else invalid token or insufficient role
        MW-->>Web: 401 or 403
    end
```

## Module files

| File | Responsibility |
|---------|-----------------|
| `auth/service.py` | Login and registration logic via `UserRepository` |
| `auth/models.py` | `AuthUser`, `PasswordHash`, `Token`, `TokenPayload`, `LoginResult` |
| `auth/token.py` | `JWTTransformer` — encode/decode HS256 |
| `data/repositories/user_repository.py` | User persistence in SQL Server |
| `api/routes/auth.py` | REST endpoints |
| `api/middleware/auth.py` | `RoleChecker`, role decorators |
| `auth/signing_schedule_token.py` | Signing schedule JWT (query `token`, not session exp) |

See also contracts module: [contracts.md](../contracts.md).

## Implementation notes

- **Hashing**: PBKDF2-HMAC-SHA256, 100,000 iterations, random salt.
- **JWT**: HS256, configurable expiration (default 60 min).
- **Roles**: English values (`lawyer`, `client`).
- **Persistence**: users in `app.users` via `UserRepository` (pyodbc). Contracts and documents: see [contracts.md](../contracts.md).

## Planned code diagrams

| Module | Key classes |
|--------|--------------|
| `document/` | `validate_upload` — PDF/DOCX, 25 MB ✅ |
| `analysis/` | `ClauseAnalyzer`, `RiskClassifier` |
| `llm/` | `LLMProvider`, `AzureOpenAIProvider` |
| `rag/` | `LegalCorpusRetriever`, `EmbeddingService` |
