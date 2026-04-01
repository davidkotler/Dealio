"""Email alert payload domain model."""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class EmailAlertPayload:
    to_email: str  # = user_email; NEVER logged
    user_id: uuid.UUID
    product_name: str
    product_url: str
    old_price: Decimal
    new_price: Decimal
    correlation_id: uuid.UUID
