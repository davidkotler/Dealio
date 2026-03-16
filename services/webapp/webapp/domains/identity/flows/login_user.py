"""Flow: authenticate a user with email and password."""
from __future__ import annotations

from dataclasses import dataclass

from webapp.domains.identity.adapters.jwt_service import generate_jwt
from webapp.domains.identity.exceptions import InvalidCredentialsError
from webapp.domains.identity.models.domain.user import User
from webapp.domains.identity.ports.user_repository import UserRepository


@dataclass
class LoginUser:
    user_repo: UserRepository
    jwt_secret: str

    async def execute(self, email: str, raw_password: str) -> tuple[User, str]:
        user = await self.user_repo.get_by_email(email.lower())
        if user is None or user.password_hash is None:
            raise InvalidCredentialsError()
        if not user.password_hash.verify(raw_password):
            raise InvalidCredentialsError()
        token = generate_jwt(user.id, self.jwt_secret)
        return user, token
