from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from pipeline.shared.orm.price_check_log_record import PriceCheckLogRecord
from pipeline.shared.scraper_domain.models.domain.scraper_result import ScraperFailure


@dataclass
class SQLAlchemyFailureLogAdapter:
    _session: AsyncSession

    async def write_failure(
        self,
        *,
        tracked_product_id: uuid.UUID,
        failure: ScraperFailure,
        checked_at: datetime,
        correlation_id: uuid.UUID,
    ) -> None:
        record = PriceCheckLogRecord(
            id=uuid.uuid4(),
            tracked_product_id=tracked_product_id,
            checked_at=checked_at,
            result="failure",
            retry_count=0,
            error_message=f"{failure.error_type.value}: {failure.message}",
        )
        self._session.add(record)
        await self._session.commit()
