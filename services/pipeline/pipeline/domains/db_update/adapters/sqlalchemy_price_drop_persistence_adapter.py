from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass
class SQLAlchemyPriceDropPersistenceAdapter:
    _session: AsyncSession

    async def conditional_update_price(
        self,
        *,
        tracked_product_id: uuid.UUID,
        old_price: Decimal,
        new_price: Decimal,
        checked_at: datetime,
    ) -> bool:
        result = await self._session.execute(
            text(
                "UPDATE tracked_products"
                " SET current_price = :new_price,"
                " previous_price = :old_price,"
                " last_checked_at = :checked_at"
                " WHERE id = :tracked_product_id"
                " AND current_price = :old_price"
            ),
            {
                "new_price": new_price,
                "old_price": old_price,
                "checked_at": checked_at,
                "tracked_product_id": str(tracked_product_id),
            },
        )
        return result.rowcount == 1

    async def create_notification(
        self,
        *,
        tracked_product_id: uuid.UUID,
        user_id: uuid.UUID,
        old_price: Decimal,
        new_price: Decimal,
    ) -> None:
        await self._session.execute(
            text(
                "INSERT INTO notifications"
                " (id, user_id, tracked_product_id, old_price, new_price, created_at)"
                " VALUES (:id, :user_id, :tracked_product_id, :old_price, :new_price, NOW())"
            ),
            {
                "id": str(uuid.uuid4()),
                "user_id": str(user_id),
                "tracked_product_id": str(tracked_product_id),
                "old_price": old_price,
                "new_price": new_price,
            },
        )

    async def write_success(
        self,
        *,
        tracked_product_id: uuid.UUID,
        checked_at: datetime,
        correlation_id: uuid.UUID,
    ) -> None:
        await self._session.execute(
            text(
                "INSERT INTO price_check_log"
                " (id, tracked_product_id, checked_at, result, retry_count, error_message)"
                " VALUES (:id, :tracked_product_id, :checked_at, 'success', 0, NULL)"
            ),
            {
                "id": str(uuid.uuid4()),
                "tracked_product_id": str(tracked_product_id),
                "checked_at": checked_at,
            },
        )
