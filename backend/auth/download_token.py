"""Short-lived JWT tokens for document downloads (RNF-21)."""

import time
from datetime import datetime, timezone
from typing import Optional

import jwt

from config.settings import get_settings


class DownloadTokenService:
    """Issues and validates scoped download tokens."""

    ALGORITHM = "HS256"
    TOKEN_TYPE = "document_download"

    def __init__(self, secret_key: str | None = None, ttl_seconds: int | None = None):
        settings = get_settings()
        self.secret_key = secret_key or settings.secret_key
        self.ttl_seconds = ttl_seconds or settings.download_token_ttl_seconds

    def create(self, *, user_id: str, contract_id: str, document_id: str) -> tuple[str, datetime]:
        expires_at = datetime.now(timezone.utc).timestamp() + self.ttl_seconds
        payload = {
            "typ": self.TOKEN_TYPE,
            "user_id": user_id,
            "contract_id": contract_id,
            "document_id": document_id,
            "exp": int(expires_at),
            "iat": int(time.time()),
        }
        token = jwt.encode(payload, self.secret_key, algorithm=self.ALGORITHM)
        return token, datetime.fromtimestamp(expires_at, tz=timezone.utc)

    def verify(
        self,
        token: str,
        *,
        contract_id: str,
        document_id: str,
    ) -> Optional[str]:
        """Return user_id if token is valid for the requested resource."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.ALGORITHM])
        except jwt.InvalidTokenError:
            return None

        if payload.get("typ") != self.TOKEN_TYPE:
            return None
        if payload.get("contract_id") != contract_id:
            return None
        if payload.get("document_id") != document_id:
            return None

        user_id = payload.get("user_id")
        return str(user_id) if user_id else None
