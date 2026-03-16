from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class OIDCClient(Protocol):
    async def build_authorization_url(self, state: str, nonce: str) -> str: ...
    async def exchange_code(self, code: str) -> dict: ...  # type: ignore[type-arg]
    async def verify_id_token(self, id_token: str, nonce: str) -> dict: ...  # type: ignore[type-arg]
