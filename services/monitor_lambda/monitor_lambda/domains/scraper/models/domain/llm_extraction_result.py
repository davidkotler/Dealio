"""Domain model for LLM extraction output."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class LLMExtractionResult:
    price: Decimal | None
    product_name: str | None
