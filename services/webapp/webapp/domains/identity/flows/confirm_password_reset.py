"""Flow: confirm a password reset using a submitted token."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone

from webapp.domains.identity.exceptions import InvalidResetTokenError
from webapp.domains.identity.models.domain.hashed_password import HashedPassword
from webapp.domains.identity.ports.token_repository import TokenRepository
from webapp.domains.identity.ports.user_repository import UserRepository


@dataclass
class ConfirmPasswordReset:
    token_repo: TokenRepository
    user_repo: UserRepository

    async def execute(self, submitted_token: str, new_password: str) -> None:
        token_hash = hashlib.sha256(submitted_token.encode()).hexdigest()
        token = await self.token_repo.get_by_token_hash(token_hash)
        if token is None or not token.is_valid():
            raise InvalidResetTokenError()
        now = datetime.now(tz=timezone.utc)
        await self.token_repo.mark_used(token.id, now)
        user = await self.user_repo.get_by_id(token.user_id)
        if user is None:
            raise InvalidResetTokenError()
        user.password_hash = HashedPassword.create(new_password, cost=14)
        user.updated_at = now
        await self.user_repo.save(user)
