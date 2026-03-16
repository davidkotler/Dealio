"""Flow: register a new user with email and password."""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from webapp.domains.identity.adapters.jwt_service import generate_jwt
from webapp.domains.identity.exceptions import EmailAlreadyRegisteredError
from webapp.domains.identity.models.domain.hashed_password import HashedPassword
from webapp.domains.identity.models.domain.types import UserId
from webapp.domains.identity.models.domain.user import User
from webapp.domains.identity.ports.user_repository import UserRepository


@dataclass
class RegisterUser:
    user_repo: UserRepository
    jwt_secret: str

    async def execute(self, email: str, raw_password: str) -> tuple[User, str]:
        normalised = email.lower()
        existing = await self.user_repo.get_by_email(normalised)
        if existing is not None:
            raise EmailAlreadyRegisteredError(normalised)
        hashed = HashedPassword.create(raw_password, cost=14)
        now = datetime.now(tz=timezone.utc)
        user = User(
            id=UserId(uuid.uuid4()),
            email=normalised,
            password_hash=hashed,
            google_sub=None,
            created_at=now,
            updated_at=now,
        )
        await self.user_repo.save(user)
        token = generate_jwt(user.id, self.jwt_secret)
        return user, token
