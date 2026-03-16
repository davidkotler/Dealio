"""Flow: request a password reset email."""
from __future__ import annotations

import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from webapp.domains.identity.models.domain.password_reset_token import PasswordResetToken
from webapp.domains.identity.models.domain.types import PasswordResetTokenId
from webapp.domains.identity.ports.email_sender import EmailSender
from webapp.domains.identity.ports.token_repository import TokenRepository
from webapp.domains.identity.ports.user_repository import UserRepository


@dataclass
class RequestPasswordReset:
    user_repo: UserRepository
    token_repo: TokenRepository
    email_sender: EmailSender
    app_base_url: str  # e.g. "https://app.dealio.com"

    async def execute(self, email: str) -> None:
        user = await self.user_repo.get_by_email(email.lower())
        if user is None:
            return  # silent — prevents email enumeration

        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        now = datetime.now(tz=timezone.utc)
        token = PasswordResetToken(
            id=PasswordResetTokenId(uuid.uuid4()),
            user_id=user.id,
            token_hash=token_hash,
            expires_at=now + timedelta(hours=1),
            used_at=None,
        )
        await self.token_repo.save(token)
        reset_link = f"{self.app_base_url}/auth/password-reset/confirm?token={raw_token}"
        await self.email_sender.send_password_reset(to_email=user.email, reset_link=reset_link)
