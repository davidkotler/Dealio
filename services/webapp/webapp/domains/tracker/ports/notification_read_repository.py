from __future__ import annotations

from datetime import datetime
from typing import Protocol, runtime_checkable

from webapp.domains.identity.models.domain import UserId
from webapp.domains.notifier.models.domain import Notification, NotificationId


@runtime_checkable
class NotificationReadRepository(Protocol):
    async def get(self, notification_id: NotificationId) -> Notification | None: ...
    async def list_by_user(
        self, user_id: UserId, cursor: datetime | None, limit: int
    ) -> list[Notification]: ...
    async def count_unread_by_user(self, user_id: UserId) -> int: ...
    async def save(self, notification: Notification) -> None: ...
