"""
Authentication and authorization middleware.
"""

from typing import List
from fastapi import Request, Depends, HTTPException

from auth.token import JWTTransformer
from config.settings import get_settings


class RoleChecker:
    """Role-based authorization dependency."""

    def __init__(self, allowed_roles: List[str] | None = None):
        self.allowed_roles = allowed_roles or []

    async def __call__(self, request: Request) -> dict:
        authorization = request.headers.get("Authorization")

        if not authorization:
            raise HTTPException(
                status_code=401,
                detail="Unauthorized. Authentication token required.",
            )

        try:
            scheme, token = authorization.split()
            if scheme.lower() != "bearer":
                raise ValueError("Invalid authentication scheme")
        except ValueError:
            raise HTTPException(
                status_code=401,
                detail="Invalid token format. Use 'Bearer <token>'.",
            )

        secret_key = get_settings().secret_key
        transformer = JWTTransformer(secret_key=secret_key)
        payload = transformer.decode(token)

        if payload is None:
            raise HTTPException(
                status_code=401,
                detail="Invalid or expired token.",
            )

        role_value = payload.role.value

        if self.allowed_roles and role_value not in self.allowed_roles:
            raise HTTPException(
                status_code=403,
                detail=(
                    f"Access denied. Required role(s): "
                    f"{', '.join(self.allowed_roles)}"
                ),
            )

        return {
            "user_id": payload.user_id,
            "email": payload.email,
            "role": payload.role,
        }


def require_auth(user: dict = Depends(RoleChecker())) -> dict:
    """Require any authenticated user."""
    return user


def require_lawyer(user: dict = Depends(RoleChecker(allowed_roles=["lawyer"]))) -> dict:
    """Require lawyer role."""
    return user


def require_client(user: dict = Depends(RoleChecker(allowed_roles=["client"]))) -> dict:
    """Require client role (contract upload and ownership actions)."""
    return user
