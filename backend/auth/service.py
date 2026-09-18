"""
Authentication service for user and session management.
"""

from typing import Optional

from auth.models import (
    UserCredentials,
    LoginResult,
    AuthUser,
    Token,
    TokenPayload,
    PasswordHash,
)
from config.settings import Settings, get_settings
from data.repositories.user_repository import UserRepository
from domain.entities import Role


class AuthService:
    """Central authentication service backed by SQL Server."""

    def __init__(
        self,
        user_repository: UserRepository | None = None,
        settings: Settings | None = None,
    ):
        self._settings = settings or get_settings()
        self._users = user_repository or UserRepository(self._settings)

    def register(self, email: str, name: str, role: Role, password: str) -> LoginResult:
        """Register a new user."""
        if self._users.email_exists(email):
            return LoginResult(
                success=False,
                message="Email address is already registered",
                token=None,
                user=None,
            )

        password_hash = PasswordHash.generate(password)
        new_user = self._users.create(
            email=email,
            name=name,
            role=role,
            password_hash=password_hash,
        )

        return LoginResult(
            success=True,
            message="User registered successfully",
            token=self._create_token(new_user),
            user=new_user,
        )

    def login(self, credentials: UserCredentials) -> LoginResult:
        """Attempt sign-in with email and password."""
        user = self._users.get_by_email(credentials.email)

        if user is None:
            return LoginResult(
                success=False,
                message="Invalid credentials",
                token=None,
                user=None,
            )

        if not user.verify_password(credentials.password):
            return LoginResult(
                success=False,
                message="Invalid credentials",
                token=None,
                user=None,
            )

        return LoginResult(
            success=True,
            message="Sign-in successful",
            token=self._create_token(user),
            user=user,
        )

    def logout(self, token: str) -> bool:
        """Sign out (stateless MVP: token is not blacklisted)."""
        return True

    def get_user_by_id(self, user_id: str) -> Optional[AuthUser]:
        """Find a user by ID."""
        return self._users.get_by_id(user_id)

    def get_user_by_email(self, email: str) -> Optional[AuthUser]:
        """Find a user by email."""
        return self._users.get_by_email(email)

    def _create_token(self, user: AuthUser) -> Token:
        """Create an access token for the given user."""
        from auth.token import JWTTransformer

        transformer = JWTTransformer(secret_key=self._settings.secret_key)
        expires_in_minutes = self._settings.token_expiration_minutes

        payload = TokenPayload.create(
            user_id=user.id,
            email=user.email,
            role=user.role,
            expires_in_minutes=expires_in_minutes,
        )

        access_token = transformer.encode(payload)

        return Token(
            access_token=access_token,
            token_type="bearer",
            expires_in_minutes=expires_in_minutes,
        )
