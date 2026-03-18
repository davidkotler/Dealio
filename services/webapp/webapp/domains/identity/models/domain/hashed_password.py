from __future__ import annotations

import hashlib
from dataclasses import dataclass

import bcrypt


def _prepare(raw: str) -> bytes:
    return hashlib.sha256(raw.encode()).hexdigest().encode()


@dataclass(frozen=True)
class HashedPassword:
    value: str

    @classmethod
    def create(cls, raw: str, cost: int = 14) -> "HashedPassword":
        hashed = bcrypt.hashpw(_prepare(raw), bcrypt.gensalt(rounds=cost))
        return cls(value=hashed.decode())

    def verify(self, raw: str) -> bool:
        return bcrypt.checkpw(_prepare(raw), self.value.encode())