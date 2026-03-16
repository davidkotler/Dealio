from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import datetime

from webapp.domains.identity.models.domain.types import UserId
from webapp.domains.notifier.exceptions import InvalidCursorError
from webapp.domains.tracker.models.domain.notification_list_data import NotificationListData
from webapp.domains.tracker.ports.notification_read_repository import NotificationReadRepository


def encode_cursor(dt: datetime) -> str:
    return base64.b64encode(dt.isoformat().encode()).decode()


def decode_cursor(cursor: str) -> datetime:
    try:
        return datetime.fromisoformat(base64.b64decode(cursor.encode()).decode())
    except Exception as exc:
        raise InvalidCursorError("Malformed cursor") from exc


@dataclass
class ListNotifications:
    notification_read_repo: NotificationReadRepository

    async def execute(
        self,
        user_id: UserId,
        cursor: str | None,
        limit: int,
    ) -> NotificationListData:
        decoded_cursor: datetime | None = decode_cursor(cursor) if cursor is not None else None
        notifications = await self.notification_read_repo.list_by_user(
            user_id=user_id,
            cursor=decoded_cursor,
            limit=limit,
        )
        next_cursor: str | None = None
        if len(notifications) == limit:
            next_cursor = encode_cursor(notifications[-1].created_at)
        return NotificationListData(
            notifications=tuple(notifications),
            next_cursor=next_cursor,
        )
