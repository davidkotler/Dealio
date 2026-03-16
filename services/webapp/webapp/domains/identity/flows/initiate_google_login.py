"""Flow: initiate Google OIDC login by generating state/nonce and building the authorization URL."""
from __future__ import annotations

import secrets
from dataclasses import dataclass

from webapp.domains.identity.ports.oidc_client import OIDCClient
from webapp.domains.identity.ports.token_store import TokenStore


@dataclass
class InitiateGoogleLogin:
    oidc_client: OIDCClient
    token_store: TokenStore

    async def execute(self) -> str:
        state = secrets.token_urlsafe(32)
        nonce = secrets.token_urlsafe(32)
        await self.token_store.store(f"oidc:{state}", nonce, ttl_seconds=300)
        return await self.oidc_client.build_authorization_url(state, nonce)
