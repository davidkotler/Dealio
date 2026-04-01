from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Protocol, runtime_checkable


@runtime_checkable
class NotificationWritePort(Protocol):
    async def create_notification(
        self,
        *,
        tracked_product_id: uuid.UUID,
        user_id: uuid.UUID,
        old_price: Decimal,
        new_price: Decimal,
    ) -> None: ...
