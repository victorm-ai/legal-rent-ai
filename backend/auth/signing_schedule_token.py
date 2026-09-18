"""JWT tokens for public signing-schedule UI (scoped to one client + contract)."""

from __future__ import annotations

import time
from typing import Any

import jwt

from config.settings import get_settings


class SigningScheduleTokenService:
    """Issues and validates signing-schedule tokens (no expiry until reserved in UI)."""

    ALGORITHM = "HS256"
    TOKEN_TYPE = "signing_schedule"

    def __init__(self, secret_key: str | None = None):
        settings = get_settings()
        self.secret_key = secret_key or settings.secret_key

    def create(self, *, client_user_id: str, contract_id: str) -> str:
        payload = {
            "typ": self.TOKEN_TYPE,
            "client_user_id": client_user_id,
            "contract_id": contract_id,
            "iat": int(time.time()),
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.ALGORITHM)

    def verify(self, token: str) -> dict[str, Any] | None:
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.ALGORITHM],
                options={"verify_exp": False},
            )
        except jwt.InvalidTokenError:
            return None

        if payload.get("typ") != self.TOKEN_TYPE:
            return None
        client_user_id = payload.get("client_user_id")
        contract_id = payload.get("contract_id")
        if not client_user_id or not contract_id:
            return None
        return {
            "client_user_id": str(client_user_id),
            "contract_id": str(contract_id),
        }
