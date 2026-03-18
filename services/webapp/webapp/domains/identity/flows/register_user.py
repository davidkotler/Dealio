"""Flow: register a new user with email and password."""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

import structlog

from webapp.domains.identity.adapters.jwt_service import generate_jwt
from webapp.domains.identity.exceptions import EmailAlreadyRegisteredError
from webapp.domains.identity.models.domain.hashed_password import HashedPassword
from webapp.domains.identity.models.domain.types import UserId
from webapp.domains.identity.models.domain.user import User
from webapp.domains.identity.ports.user_repository import UserRepository

logger = structlog.get_logger()


@dataclass
class RegisterUser:
    user_repo: UserRepository
    jwt_secret: str

    async def execute(self, email: str, raw_password: str) -> tuple[User, str]:
        normalised = email.lower()
        log = logger.bind(email=normalised)
        await log.adebug("user.register_started")

        try:
            existing = await self.user_repo.get_by_email(normalised)
        except Exception:
            await log.aexception(
                "user.register_failed",
                error_type="RepositoryError",
                error_code="DB_LOOKUP_FAILED",
            )
            raise

        if existing is not None:
            await log.awarning("user.register_email_conflict", error_code="EMAIL_ALREADY_REGISTERED")
            raise EmailAlreadyRegisteredError(normalised)

        try:
            hashed = HashedPassword.create(raw_password, cost=14)
        except Exception:
            await log.aexception(
                "user.register_failed",
                error_type="PasswordHashError",
                error_code="PASSWORD_HASH_FAILED",
            )
            raise

        now = datetime.now(tz=timezone.utc)
        user = User(
            id=UserId(uuid.uuid4()),
            email=normalised,
            password_hash=hashed,
            google_sub=None,
            created_at=now,
            updated_at=now,
        )

        try:
            await self.user_repo.save(user)
        except Exception:
            await log.aexception(
                "user.register_failed",
                user_id=str(user.id),
                error_type="RepositoryError",
                error_code="DB_SAVE_FAILED",
            )
            raise

        try:
            token = generate_jwt(user.id, self.jwt_secret)
        except Exception:
            await log.aexception(
                "user.register_failed",
                user_id=str(user.id),
                error_type="JWTError",
                error_code="JWT_GENERATION_FAILED",
            )
            raise

        await log.ainfo("user.registered", user_id=str(user.id))
        return user, token
