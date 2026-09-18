"""SQL Server repository for app.users."""

from typing import Optional
from uuid import UUID

from auth.models import AuthUser, PasswordHash
from config.settings import Settings, get_settings
from data.database import get_connection
from domain.entities import Role


ROLE_TO_ID = {
    Role.LAWYER: 1,
    Role.CLIENT: 2,
}

_USER_SELECT = """
SELECT
    u.id,
    u.email,
    u.name,
    u.password_hash,
    u.password_salt,
    r.code AS role_code
FROM app.users u
INNER JOIN app.roles r ON u.role_id = r.id
WHERE u.is_active = 1
"""


class UserRepository:
    """Reads and writes users in SQL Server."""

    def __init__(self, settings: Settings | None = None):
        self._settings = settings or get_settings()

    def get_by_email(self, email: str) -> Optional[AuthUser]:
        """Find an active user by email."""
        with get_connection(self._settings) as connection:
            cursor = connection.cursor()
            cursor.execute(f"{_USER_SELECT} AND u.email = ?", email)
            row = cursor.fetchone()
            return self._row_to_user(row) if row else None

    def get_by_id(self, user_id: str) -> Optional[AuthUser]:
        """Find an active user by ID."""
        with get_connection(self._settings) as connection:
            cursor = connection.cursor()
            cursor.execute(f"{_USER_SELECT} AND u.id = ?", user_id)
            row = cursor.fetchone()
            return self._row_to_user(row) if row else None

    def get_primary_lawyer_email(self) -> Optional[str]:
        """Return the email of the first active lawyer account, if any."""
        with get_connection(self._settings) as connection:
            cursor = connection.cursor()
            cursor.execute(
                f"""
                SELECT TOP 1 u.email
                FROM app.users u
                INNER JOIN app.roles r ON u.role_id = r.id
                WHERE u.is_active = 1 AND r.code = ?
                ORDER BY u.created_at ASC
                """,
                Role.LAWYER.value,
            )
            row = cursor.fetchone()
        return row[0] if row else None

    def email_exists(self, email: str) -> bool:
        """Return True if the email is already registered."""
        with get_connection(self._settings) as connection:
            cursor = connection.cursor()
            cursor.execute(
                "SELECT 1 FROM app.users WHERE email = ?",
                email,
            )
            return cursor.fetchone() is not None

    def create(
        self,
        email: str,
        name: str,
        role: Role,
        password_hash: PasswordHash,
    ) -> AuthUser:
        """Insert a new user and return the persisted entity."""
        role_id = ROLE_TO_ID[role]

        with get_connection(self._settings) as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                INSERT INTO app.users (
                    email, name, role_id, password_hash, password_salt
                )
                OUTPUT
                    INSERTED.id,
                    INSERTED.email,
                    INSERTED.name,
                    INSERTED.password_hash,
                    INSERTED.password_salt
                VALUES (?, ?, ?, ?, ?)
                """,
                email,
                name,
                role_id,
                password_hash.hashed_password,
                password_hash.salt,
            )
            row = cursor.fetchone()
            connection.commit()

        return AuthUser(
            id=str(row[0]),
            email=row[1],
            name=row[2],
            role=role,
            password_hash=PasswordHash(
                hashed_password=row[3],
                salt=row[4],
            ),
        )

    @staticmethod
    def _row_to_user(row) -> AuthUser:
        """Map a database row to AuthUser."""
        user_id = row[0]
        if isinstance(user_id, UUID):
            user_id = str(user_id)

        return AuthUser(
            id=user_id,
            email=row[1],
            name=row[2],
            role=Role(row[5]),
            password_hash=PasswordHash(
                hashed_password=row[3],
                salt=row[4],
            ),
        )
