from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Protocol, runtime_checkable

from monitor_lambda.domains.monitor.models.domain import TrackedProductId
from monitor_lambda.domains.monitor.models.domain.tracked_product_summary import TrackedProductSummary


@runtime_checkable
class TrackedProductRepository(Protocol):
    async def list_all(self) -> list[TrackedProductSummary]: ...
    async def update_price(self, product_id: TrackedProductId, new_price: Decimal, checked_at: datetime) -> None: ...
