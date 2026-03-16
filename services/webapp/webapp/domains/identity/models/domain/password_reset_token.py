from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from webapp.domains.identity.models.domain.types import PasswordResetTokenId, UserId


@dataclass
class PasswordResetToken:
    id: PasswordResetTokenId
    user_id: UserId
    token_hash: str
    expires_at: datetime
    used_at: datetime | None

    def is_valid(self, now: datetime | None = None) -> bool:
        if self.used_at is not None:
            return False
        reference = now if now is not None else datetime.now(tz=timezone.utc)
        return reference < self.expires_at
