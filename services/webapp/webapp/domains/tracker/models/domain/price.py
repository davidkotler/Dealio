from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class Price:
    value: Decimal

    def __post_init__(self) -> None:
        if self.value < Decimal("0"):
            raise ValueError(f"Price cannot be negative, got {self.value!r}.")

    def __lt__(self, other: "Price") -> bool:
        if not isinstance(other, Price):
            return NotImplemented
        return self.value < other.value

    def __le__(self, other: "Price") -> bool:
        if not isinstance(other, Price):
            return NotImplemented
        return self.value <= other.value

    def __gt__(self, other: "Price") -> bool:
        if not isinstance(other, Price):
            return NotImplemented
        return self.value > other.value

    def __ge__(self, other: "Price") -> bool:
        if not isinstance(other, Price):
            return NotImplemented
        return self.value >= other.value
