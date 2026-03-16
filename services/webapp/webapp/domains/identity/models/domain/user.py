from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from webapp.domains.identity.models.domain.hashed_password import HashedPassword
from webapp.domains.identity.models.domain.types import UserId


@dataclass
class User:
    id: UserId
    email: str
    password_hash: HashedPassword | None
    google_sub: str | None
    created_at: datetime
    updated_at: datetime

    def __post_init__(self) -> None:
        if self.password_hash is None and self.google_sub is None:
            raise ValueError("User must have at least one authentication method (password or Google).")
