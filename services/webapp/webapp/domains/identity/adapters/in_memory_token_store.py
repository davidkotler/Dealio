"""In-memory TokenStore adapter with TTL enforcement."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone


@dataclass
class InMemoryTokenStore:
    """Volatile key-value store with per-entry TTL.

    Intended for testing and local development. Not safe for multi-process deployments.
    """

    _store: dict[str, tuple[str, datetime]] = field(default_factory=dict)

    async def store(self, key: str, value: str, ttl_seconds: int) -> None:
        expires_at = datetime.now(tz=timezone.utc) + timedelta(seconds=ttl_seconds)
        self._store[key] = (value, expires_at)

    async def get(self, key: str) -> str | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        value, expires_at = entry
        if datetime.now(tz=timezone.utc) >= expires_at:
            del self._store[key]
            return None
        return value

    async def delete(self, key: str) -> None:
        self._store.pop(key, None)
