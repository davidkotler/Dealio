from __future__ import annotations

from datetime import datetime
from typing import Protocol, runtime_checkable

from webapp.domains.identity.models.domain import PasswordResetToken, PasswordResetTokenId, UserId


@runtime_checkable
class TokenRepository(Protocol):
    async def get_by_token_hash(self, token_hash: str) -> PasswordResetToken | None: ...
    async def save(self, token: PasswordResetToken) -> None: ...
    async def mark_used(self, token_id: PasswordResetTokenId, used_at: datetime) -> None: ...
    async def delete_by_user_id(self, user_id: UserId) -> None: ...
