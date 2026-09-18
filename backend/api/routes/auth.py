"""
Authentication API routes.
"""

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional

from auth.models import UserCredentials
from auth.service import AuthService


router = APIRouter(prefix="/auth", tags=["authentication"])


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    token_type: str
    access_token: str
    expires_in_minutes: int
    user_id: str
    email: str
    name: str
    role: str


class ErrorResponse(BaseModel):
    detail: str


@router.post(
    "/login",
    response_model=LoginResponse,
    responses={401: {"model": ErrorResponse, "description": "Invalid credentials"}},
)
async def login(request: LoginRequest):
    """Sign in with email and password."""
    auth_service = AuthService()
    result = auth_service.login(
        UserCredentials(email=request.email, password=request.password)
    )

    if not result.success:
        raise HTTPException(status_code=401, detail=result.message)

    return LoginResponse(
        token_type=result.token.token_type,
        access_token=result.token.access_token,
        expires_in_minutes=result.token.expires_in_minutes,
        user_id=result.user.id,
        email=result.user.email,
        name=result.user.name,
        role=result.user.role.value,
    )


@router.post(
    "/logout",
    responses={
        200: {"description": "Signed out successfully"},
        401: {"model": ErrorResponse, "description": "Invalid token"},
    },
)
async def logout(authorization: Optional[str] = Header(None)):
    """Sign out the current session."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Token not provided")

    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(status_code=401, detail="Invalid authentication scheme")
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid token format")

    auth_service = AuthService()
    auth_service.logout(token)

    return {"message": "Signed out successfully"}


@router.post(
    "/register",
    response_model=LoginResponse,
    responses={
        400: {"model": ErrorResponse, "description": "User already exists"},
        422: {"model": ErrorResponse, "description": "Invalid data"},
    },
)
async def register(request: LoginRequest):
    """Register a new user (defaults to client role)."""
    from domain.entities import Role

    auth_service = AuthService()
    result = auth_service.register(
        email=request.email,
        name=request.email.split("@")[0],
        role=Role.CLIENT,
        password=request.password,
    )

    if not result.success:
        raise HTTPException(status_code=400, detail=result.message)

    return LoginResponse(
        token_type=result.token.token_type,
        access_token=result.token.access_token,
        expires_in_minutes=result.token.expires_in_minutes,
        user_id=result.user.id,
        email=result.user.email,
        name=result.user.name,
        role=result.user.role.value,
    )


def get_current_user(authorization: str = Header(None)) -> dict:
    """Dependency that returns the current user from the JWT."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Token not provided")

    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(status_code=401, detail="Invalid authentication scheme")
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid token format")

    from auth.token import JWTTransformer
    from config.settings import get_settings

    transformer = JWTTransformer(secret_key=get_settings().secret_key)
    payload = transformer.decode(token)

    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    return {
        "user_id": payload.user_id,
        "email": payload.email,
        "role": payload.role,
    }
