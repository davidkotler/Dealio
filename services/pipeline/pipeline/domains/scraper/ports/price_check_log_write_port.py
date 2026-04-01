from __future__ import annotations

import uuid
from datetime import datetime
from typing import Protocol, runtime_checkable

from pipeline.shared.scraper_domain.models.domain.scraper_result import ScraperFailure


@runtime_checkable
class PriceCheckLogWritePort(Protocol):
    async def write_failure(
        self,
        *,
        tracked_product_id: uuid.UUID,
        failure: ScraperFailure,
        checked_at: datetime,
        correlation_id: uuid.UUID,
    ) -> None: ...
