"""Google OIDC client adapter using Authlib and httpx."""
from __future__ import annotations

from dataclasses import dataclass

import httpx
from authlib.integrations.httpx_client import AsyncOAuth2Client
from authlib.jose import JsonWebToken

_DISCOVERY_URL = "https://accounts.google.com/.well-known/openid-configuration"


@dataclass
class AuthlibGoogleOIDCClient:
    client_id: str
    client_secret: str
    redirect_uri: str

    async def build_authorization_url(self, state: str, nonce: str) -> str:
        async with AsyncOAuth2Client(client_id=self.client_id, redirect_uri=self.redirect_uri) as client:
            metadata = await client.load_server_metadata(_DISCOVERY_URL)
            url, _ = client.create_authorization_url(
                metadata["authorization_endpoint"],
                state=state,
                nonce=nonce,
                scope="openid email profile",
            )
            return url

    async def exchange_code(self, code: str) -> dict:  # type: ignore[type-arg]
        async with AsyncOAuth2Client(
            client_id=self.client_id,
            client_secret=self.client_secret,
            redirect_uri=self.redirect_uri,
        ) as client:
            metadata = await client.load_server_metadata(_DISCOVERY_URL)
            return await client.fetch_token(metadata["token_endpoint"], code=code)

    async def verify_id_token(self, id_token: str, nonce: str) -> dict:  # type: ignore[type-arg]
        async with httpx.AsyncClient() as client:
            metadata = (await client.get(_DISCOVERY_URL)).json()
            jwks_data = (await client.get(metadata["jwks_uri"])).json()
        jwt = JsonWebToken(["RS256"])
        claims = jwt.decode(id_token, jwks_data)
        claims.validate()
        if claims.get("nonce") != nonce:
            raise ValueError("nonce mismatch")
        return dict(claims)
