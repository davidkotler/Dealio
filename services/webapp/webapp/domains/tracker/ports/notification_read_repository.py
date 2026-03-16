from __future__ import annotations

from datetime import datetime
from typing import Protocol, runtime_checkable

from webapp.domains.identity.models.domain import UserId
from webapp.domains.notifier.models.domain import Notification, NotificationId


@runtime_checkable
class NotificationReadRepository(Protocol):
    async def list_by_user_id(self, user_id: UserId, limit: int, offset: int) -> list[Notification]: ...
    async def get_by_id(self, notification_id: NotificationId) -> Notification | None: ...
    async def mark_read(self, notification_id: NotificationId, read_at: datetime) -> None: ...
