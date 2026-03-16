from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class OIDCClient(Protocol):
    async def get_authorization_url(self, state: str) -> str: ...
    async def exchange_code(self, code: str, state: str) -> dict[str, str]: ...
