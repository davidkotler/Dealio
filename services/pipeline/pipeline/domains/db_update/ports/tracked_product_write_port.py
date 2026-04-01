from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Protocol, runtime_checkable


@runtime_checkable
class TrackedProductWritePort(Protocol):
    async def conditional_update_price(
        self,
        *,
        tracked_product_id: uuid.UUID,
        old_price: Decimal,
        new_price: Decimal,
        checked_at: datetime,
    ) -> bool: ...  # True if rowcount==1; False if duplicate
