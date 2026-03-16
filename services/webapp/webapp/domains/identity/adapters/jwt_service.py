"""JWT generation and decoding for identity authentication."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt  # noqa: F401 — JWTError re-exported for callers

from webapp.domains.identity.models.domain.types import UserId

__all__ = ["JWTError", "generate_jwt", "decode_jwt"]

_ALGORITHM = "HS256"
_TOKEN_TTL_SECONDS = 86400  # 24 hours


def generate_jwt(user_id: UserId, secret: str) -> str:
    """Return a signed JWT encoding user_id with a 24-hour expiry."""
    now = datetime.now(tz=timezone.utc)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(seconds=_TOKEN_TTL_SECONDS),
    }
    return jwt.encode(payload, secret, algorithm=_ALGORITHM)


def decode_jwt(token: str, secret: str) -> UserId:
    """Decode and verify a JWT, returning the UserId.

    Raises:
        JWTError: if the token is invalid, expired, or tampered with.
    """
    payload = jwt.decode(token, secret, algorithms=[_ALGORITHM])
    return UserId(uuid.UUID(payload["sub"]))
