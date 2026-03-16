from __future__ import annotations

from dataclasses import dataclass

from passlib.hash import bcrypt as _bcrypt


@dataclass(frozen=True)
class HashedPassword:
    value: str

    @classmethod
    def create(cls, raw: str, cost: int = 14) -> "HashedPassword":
        return cls(value=_bcrypt.using(rounds=cost).hash(raw))

    def verify(self, raw: str) -> bool:
        return _bcrypt.verify(raw, self.value)
