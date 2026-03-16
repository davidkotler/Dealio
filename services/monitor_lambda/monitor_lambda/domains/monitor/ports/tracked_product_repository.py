from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Protocol, runtime_checkable

from monitor_lambda.domains.monitor.models.domain import TrackedProductId
from monitor_lambda.domains.monitor.models.domain.tracked_product_summary import TrackedProductSummary


@runtime_checkable
class TrackedProductRepository(Protocol):
    async def list_all_active(self) -> list[TrackedProductSummary]: ...
    async def update_prices(
        self,
        product_id: TrackedProductId,
        new_price: Decimal,
        previous_price: Decimal,
        last_checked_at: datetime,
    ) -> None: ...
    async def update_last_checked_at(
        self,
        product_id: TrackedProductId,
        last_checked_at: datetime,
    ) -> None: ...
