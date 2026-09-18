"""
Base interfaces for authentication repositories and services.
"""

from abc import ABC, abstractmethod
from typing import Optional, List

from auth.models import AuthUser, UserCredentials, LoginResult
from domain.entities import Role


class IUserRepository(ABC):
    """User repository interface."""

    @abstractmethod
    async def get_by_id(self, user_id: str) -> Optional[AuthUser]:
        pass

    @abstractmethod
    async def get_by_email(self, email: str) -> Optional[AuthUser]:
        pass

    @abstractmethod
    async def create(self, user: AuthUser) -> bool:
        pass

    @abstractmethod
    async def list_all(self) -> List[AuthUser]:
        pass


class IAuthService(ABC):
    """Authentication service interface."""

    @abstractmethod
    async def login(self, credentials: UserCredentials) -> LoginResult:
        pass

    @abstractmethod
    async def logout(self, token: str) -> bool:
        pass

    @abstractmethod
    async def get_current_user(self, token: str) -> Optional[AuthUser]:
        pass
