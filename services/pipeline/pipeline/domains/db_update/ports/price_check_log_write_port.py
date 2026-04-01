from __future__ import annotations

import uuid
from datetime import datetime
from typing import Protocol, runtime_checkable


@runtime_checkable
class PriceCheckLogWritePort(Protocol):
    async def write_success(
        self,
        *,
        tracked_product_id: uuid.UUID,
        checked_at: datetime,
        correlation_id: uuid.UUID,
    ) -> None: ...
