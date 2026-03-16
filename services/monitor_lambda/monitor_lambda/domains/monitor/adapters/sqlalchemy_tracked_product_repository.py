"""SQLAlchemy async adapter for TrackedProductRepository (monitor_lambda context)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from monitor_lambda.domains.monitor.models.domain.tracked_product_summary import TrackedProductSummary
from monitor_lambda.domains.monitor.models.domain.types import TrackedProductId

_LIST_ALL_ACTIVE = text("""
    SELECT tp.id, tp.user_id, u.email, tp.url, tp.product_name, tp.current_price
    FROM tracked_products tp
    JOIN users u ON u.id = tp.user_id
    ORDER BY tp.id
""")

_UPDATE_PRICES = text("""
    UPDATE tracked_products
    SET current_price = :new_price,
        previous_price = :previous_price,
        last_checked_at = :last_checked_at
    WHERE id = :product_id
""")

_UPDATE_LAST_CHECKED_AT = text("""
    UPDATE tracked_products
    SET last_checked_at = :last_checked_at
    WHERE id = :product_id
""")


@dataclass
class SQLAlchemyTrackedProductRepository:
    _session: AsyncSession

    async def list_all_active(self) -> list[TrackedProductSummary]:
        result = await self._session.execute(_LIST_ALL_ACTIVE)
        return [_row_to_summary(row) for row in result.mappings()]

    async def update_prices(
        self,
        product_id: TrackedProductId,
        new_price: Decimal,
        previous_price: Decimal,
        last_checked_at: datetime,
    ) -> None:
        await self._session.execute(
            _UPDATE_PRICES,
            {
                "new_price": new_price,
                "previous_price": previous_price,
                "last_checked_at": last_checked_at,
                "product_id": product_id,
            },
        )

    async def update_last_checked_at(
        self,
        product_id: TrackedProductId,
        last_checked_at: datetime,
    ) -> None:
        await self._session.execute(
            _UPDATE_LAST_CHECKED_AT,
            {"last_checked_at": last_checked_at, "product_id": product_id},
        )


def _row_to_summary(row: Any) -> TrackedProductSummary:
    return TrackedProductSummary(
        id=TrackedProductId(row["id"]),
        user_id=row["user_id"],
        user_email=row["email"],
        url=row["url"],
        product_name=row["product_name"],
        current_price=row["current_price"],
    )
