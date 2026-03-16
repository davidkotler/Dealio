"""SQLAlchemy async adapter for NotificationWriteRepository (monitor_lambda context)."""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from monitor_lambda.domains.monitor.models.domain.notification import Notification
from monitor_lambda.domains.monitor.models.persistence.notification_record import NotificationRecord


@dataclass
class SQLAlchemyNotificationWriteRepository:
    _session: AsyncSession

    async def save(self, notification: Notification) -> None:
        values = _to_record(notification)
        stmt = (
            insert(NotificationRecord)
            .values(**values)
            .on_conflict_do_update(
                index_elements=["id"],
                set_={"read_at": values["read_at"]},
            )
        )
        await self._session.execute(stmt)
        await self._session.flush()


def _to_record(notification: Notification) -> dict:  # type: ignore[type-arg]
    return {
        "id": notification.id,
        "user_id": notification.user_id,
        "tracked_product_id": notification.tracked_product_id,
        "old_price": notification.old_price,
        "new_price": notification.new_price,
        "created_at": notification.created_at,
        "read_at": notification.read_at,
    }
