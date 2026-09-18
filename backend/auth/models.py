"""
Authentication and authorization domain models.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional
from dataclasses import dataclass
import hashlib
import secrets

from domain.entities import Role


@dataclass
class TokenPayload:
    """JWT token payload."""
    user_id: str
    email: str
    role: Role
    expires_at: datetime

    @classmethod
    def create(
        cls,
        user_id: str,
        email: str,
        role: Role,
        expires_in_minutes: int = 60,
    ) -> "TokenPayload":
        """Create a payload with expiration."""
        return cls(
            user_id=user_id,
            email=email,
            role=role,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=expires_in_minutes),
        )

    def is_expired(self) -> bool:
        """Return True if the token has expired."""
        return datetime.now(timezone.utc) > self.expires_at


@dataclass
class Token:
    """Access token."""
    access_token: str
    token_type: str = "bearer"
    expires_in_minutes: int = 60


@dataclass
class PasswordHash:
    """Password hash with salt."""
    hashed_password: str
    salt: str

    @staticmethod
    def generate(password: str, salt: Optional[str] = None) -> "PasswordHash":
        """Generate a password hash."""
        if salt is None:
            salt = secrets.token_hex(16)

        hashed = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            100_000,
        ).hex()

        return PasswordHash(hashed_password=hashed, salt=salt)

    def verify(self, password: str) -> bool:
        """Verify a plain-text password against the hash."""
        rehashed = PasswordHash.generate(password, self.salt)
        return secrets.compare_digest(rehashed.hashed_password, self.hashed_password)


@dataclass
class UserCredentials:
    """User credentials for sign-in."""
    email: str
    password: str


@dataclass
class LoginResult:
    """Result of a sign-in attempt."""
    success: bool
    message: str
    token: Optional[Token] = None
    user: Optional["AuthUser"] = None


@dataclass
class AuthUser:
    """Authenticated user with password hash."""
    id: str
    email: str
    name: str
    role: Role
    password_hash: PasswordHash

    @classmethod
    def create(
        cls,
        user_id: str,
        email: str,
        name: str,
        role: Role,
        password: Optional[str] = None,
    ) -> "AuthUser":
        """Create a user, optionally with a password."""
        password_hash = PasswordHash.generate(password) if password else None
        return cls(
            id=user_id,
            email=email,
            name=name,
            role=role,
            password_hash=password_hash,
        )

    def verify_password(self, password: str) -> bool:
        """Verify the user's password."""
        if self.password_hash is None:
            return False
        return self.password_hash.verify(password)

    def to_user(self) -> "domain.entities.User":
        """Convert to a domain User entity (without password)."""
        from domain.entities import User

        return User(
            id=self.id,
            email=self.email,
            name=self.name,
            role=self.role,
        )
