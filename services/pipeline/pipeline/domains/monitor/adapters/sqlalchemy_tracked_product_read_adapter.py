"""SQLAlchemy adapter for reading tracked products for the fan-out cycle."""
from __future__ import annotations

import uuid
from decimal import Decimal

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from pipeline.domains.monitor.models.domain.product_fan_out_payload import ProductFanOutPayload

log = structlog.get_logger()

_FAN_OUT_SQL = text(
    """
    SELECT tp.id, tp.user_id, u.email AS user_email, tp.url, tp.product_name, tp.current_price
    FROM tracked_products tp
    JOIN users u ON u.id = tp.user_id
    ORDER BY tp.id
    """
)


class SQLAlchemyTrackedProductReadAdapter:
    def __init__(self, _session: AsyncSession) -> None:
        self._session = _session

    async def list_all_for_fan_out(self, *, correlation_id: uuid.UUID) -> list[ProductFanOutPayload]:
        result = await self._session.execute(_FAN_OUT_SQL)
        rows = result.mappings().all()
        return [
            ProductFanOutPayload(
                tracked_product_id=uuid.UUID(str(row["id"])),
                url=row["url"],
                current_price=Decimal(str(row["current_price"])),
                user_id=uuid.UUID(str(row["user_id"])),
                user_email=row["user_email"],
                product_name=row["product_name"],
                correlation_id=correlation_id,
            )
            for row in rows
        ]
