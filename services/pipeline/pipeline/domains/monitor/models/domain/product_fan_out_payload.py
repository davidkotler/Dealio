"""ProductFanOutPayload domain model for the monitor fan-out cycle."""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class ProductFanOutPayload:
    tracked_product_id: uuid.UUID
    url: str
    current_price: Decimal
    user_id: uuid.UUID
    user_email: str  # NEVER logged
    product_name: str
    correlation_id: uuid.UUID  # One UUID per fan-out cycle
