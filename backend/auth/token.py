"""
JWT token encoding and validation.
"""

import jwt
import time
from datetime import datetime, timezone
from typing import Optional

from domain.entities import Role


class JWTTransformer:
    """Encodes and decodes JWT access tokens."""

    ALGORITHM = "HS256"

    def __init__(self, secret_key: str):
        self.secret_key = secret_key

    def encode(self, payload) -> str:
        """Encode a TokenPayload into a JWT string."""
        payload_dict = {
            "user_id": payload.user_id,
            "email": payload.email,
            "role": payload.role.value,
            "exp": int(payload.expires_at.timestamp()),
            "iat": int(time.time()),
        }

        return jwt.encode(payload_dict, self.secret_key, algorithm=self.ALGORITHM)

    def decode(self, token: str) -> Optional:
        """Decode and validate a JWT. Returns TokenPayload or None."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.ALGORITHM])

            from auth.models import TokenPayload

            return TokenPayload(
                user_id=payload["user_id"],
                email=payload["email"],
                role=Role(payload["role"]),
                expires_at=datetime.fromtimestamp(payload["exp"], tz=timezone.utc),
            )
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
