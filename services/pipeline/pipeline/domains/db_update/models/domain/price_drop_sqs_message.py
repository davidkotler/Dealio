from __future__ import annotations

import uuid
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class PriceDropSQSMessage:
    tracked_product_id: uuid.UUID
    user_id: uuid.UUID
    user_email: str  # NEVER logged
    product_name: str
    product_url: str
    old_price: Decimal
    new_price: Decimal
    correlation_id: uuid.UUID
