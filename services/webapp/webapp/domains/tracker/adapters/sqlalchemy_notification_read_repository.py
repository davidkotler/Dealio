from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from webapp.domains.identity.models.domain.types import UserId
from webapp.domains.notifier.models.domain.notification import Notification
from webapp.domains.notifier.models.domain.types import NotificationId
from webapp.domains.notifier.models.persistence.notification_record import NotificationRecord
from webapp.domains.tracker.models.domain.price import Price
from webapp.domains.tracker.models.domain.types import TrackedProductId


@dataclass
class SQLAlchemyNotificationReadRepository:
    _session: AsyncSession

    async def get(self, notification_id: NotificationId) -> Notification | None:
        result = await self._session.execute(
            select(NotificationRecord).where(NotificationRecord.id == notification_id)
        )
        record = result.scalar_one_or_none()
        return _to_domain(record) if record is not None else None

    async def list_by_user(
        self, user_id: UserId, cursor: datetime | None, limit: int
    ) -> list[Notification]:
        stmt = select(NotificationRecord).where(NotificationRecord.user_id == user_id)
        if cursor is not None:
            stmt = stmt.where(NotificationRecord.created_at < cursor)
        stmt = stmt.order_by(NotificationRecord.created_at.desc()).limit(limit)
        result = await self._session.execute(stmt)
        return [_to_domain(r) for r in result.scalars().all()]

    async def count_unread_by_user(self, user_id: UserId) -> int:
        result = await self._session.execute(
            select(func.count())
            .select_from(NotificationRecord)
            .where(
                NotificationRecord.user_id == user_id,
                NotificationRecord.read_at.is_(None),
            )
        )
        return result.scalar_one()

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


def _to_domain(record: NotificationRecord) -> Notification:
    return Notification(
        id=NotificationId(record.id),
        user_id=UserId(record.user_id),
        tracked_product_id=TrackedProductId(record.tracked_product_id),
        old_price=Price(value=record.old_price),
        new_price=Price(value=record.new_price),
        created_at=record.created_at,
        read_at=record.read_at,
    )


def _to_record(notification: Notification) -> dict:  # type: ignore[type-arg]
    return {
        "id": notification.id,
        "user_id": notification.user_id,
        "tracked_product_id": notification.tracked_product_id,
        "old_price": notification.old_price.value,
        "new_price": notification.new_price.value,
        "created_at": notification.created_at,
        "read_at": notification.read_at,
    }
