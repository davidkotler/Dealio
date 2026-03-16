"""SQLAlchemy async adapter for PriceCheckLogRepository (monitor_lambda context)."""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from monitor_lambda.domains.monitor.models.domain.price_check_log import PriceCheckLog
from monitor_lambda.domains.monitor.models.persistence.price_check_log_record import PriceCheckLogRecord


@dataclass
class SQLAlchemyPriceCheckLogRepository:
    _session: AsyncSession

    async def save(self, log: PriceCheckLog) -> None:
        error_message = log.result.message if log.result.outcome == "failure" else None
        stmt = insert(PriceCheckLogRecord).values(
            id=log.id,
            tracked_product_id=log.tracked_product_id,
            checked_at=log.checked_at,
            result=log.result.outcome,
            retry_count=log.retry_count,
            error_message=error_message,
        )
        await self._session.execute(stmt)
        await self._session.flush()
