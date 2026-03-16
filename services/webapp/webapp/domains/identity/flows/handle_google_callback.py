"""Flow: handle Google OIDC callback — find, link, or create user, then issue JWT."""
from __future__ import annotations

import dataclasses
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from webapp.domains.identity.adapters.jwt_service import generate_jwt
from webapp.domains.identity.exceptions import (
    InvalidOIDCStateError,
    OIDCExchangeError,
    OIDCTokenVerificationError,
)
from webapp.domains.identity.models.domain.types import UserId
from webapp.domains.identity.models.domain.user import User
from webapp.domains.identity.ports.oidc_client import OIDCClient
from webapp.domains.identity.ports.token_store import TokenStore
from webapp.domains.identity.ports.user_repository import UserRepository


@dataclass
class HandleGoogleCallback:
    oidc_client: OIDCClient
    user_repo: UserRepository
    token_store: TokenStore
    jwt_secret: str

    async def execute(self, code: str, state: str) -> tuple[User, str]:
        nonce = await self.token_store.get(f"oidc:{state}")
        if nonce is None:
            raise InvalidOIDCStateError("Unknown or expired OIDC state")
        await self.token_store.delete(f"oidc:{state}")

        try:
            token_data = await self.oidc_client.exchange_code(code)
        except Exception as exc:
            raise OIDCExchangeError("Token exchange failed") from exc

        try:
            claims = await self.oidc_client.verify_id_token(token_data["id_token"], nonce)
        except Exception as exc:
            raise OIDCTokenVerificationError("ID token verification failed") from exc

        sub: str = claims["sub"]
        email: str = claims["email"]
        now = datetime.now(UTC)

        user = await self.user_repo.get_by_google_sub(sub)

        if user is None:
            existing = await self.user_repo.get_by_email(email)
            if existing is not None:
                user = dataclasses.replace(existing, google_sub=sub, updated_at=now)
                await self.user_repo.save(user)
            else:
                user = User(
                    id=UserId(uuid.uuid4()),
                    email=email,
                    password_hash=None,
                    google_sub=sub,
                    created_at=now,
                    updated_at=now,
                )
                await self.user_repo.save(user)

        jwt_token = generate_jwt(user.id, self.jwt_secret)
        return user, jwt_token
