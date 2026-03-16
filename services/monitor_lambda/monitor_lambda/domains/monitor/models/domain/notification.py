from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from monitor_lambda.domains.monitor.models.domain.types import TrackedProductId


@dataclass
class Notification:
    id: uuid.UUID
    user_id: uuid.UUID
    tracked_product_id: TrackedProductId
    product_name: str
    product_url: str
    old_price: Decimal
    new_price: Decimal
    created_at: datetime
    read_at: datetime | None
