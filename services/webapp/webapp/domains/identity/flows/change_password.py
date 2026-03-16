"""Flow: change a user's password (requires current password)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from webapp.domains.identity.exceptions import InvalidCredentialsError, PasswordChangeNotAllowedError
from webapp.domains.identity.models.domain.hashed_password import HashedPassword
from webapp.domains.identity.models.domain.types import UserId
from webapp.domains.identity.ports.user_repository import UserRepository


@dataclass
class ChangePassword:
    user_repo: UserRepository

    async def execute(self, user_id: UserId, current_password: str, new_password: str) -> None:
        user = await self.user_repo.get_by_id(user_id)
        if user is None:
            raise InvalidCredentialsError()
        if user.password_hash is None:
            raise PasswordChangeNotAllowedError()
        if not user.password_hash.verify(current_password):
            raise InvalidCredentialsError()
        now = datetime.now(tz=timezone.utc)
        user.password_hash = HashedPassword.create(new_password, cost=14)
        user.updated_at = now
        await self.user_repo.save(user)
