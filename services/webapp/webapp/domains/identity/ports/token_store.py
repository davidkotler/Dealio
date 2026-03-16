from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class TokenStore(Protocol):
    async def store(self, key: str, value: str, ttl_seconds: int) -> None: ...
    async def get(self, key: str) -> str | None: ...
    async def delete(self, key: str) -> None: ...
