from __future__ import annotations

import uuid
from dataclasses import dataclass
from decimal import Decimal

from monitor_lambda.domains.monitor.models.domain.types import TrackedProductId


@dataclass(frozen=True)
class TrackedProductSummary:
    id: TrackedProductId
    user_id: uuid.UUID
    user_email: str
    url: str
    product_name: str
    current_price: Decimal
