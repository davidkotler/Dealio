from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class PriceCheckResult:
    outcome: Literal["success", "failure"]
    message: str

    @classmethod
    def success(cls, message: str = "") -> "PriceCheckResult":
        return cls(outcome="success", message=message)

    @classmethod
    def failure(cls, message: str) -> "PriceCheckResult":
        return cls(outcome="failure", message=message)
