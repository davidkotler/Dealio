from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from webapp.domains.identity.models.domain.types import UserId
from webapp.domains.notifier.exceptions import NotificationNotFoundError
from webapp.domains.notifier.models.domain.notification import Notification
from webapp.domains.notifier.models.domain.types import NotificationId
from webapp.domains.tracker.ports.notification_read_repository import NotificationReadRepository


@dataclass
class DismissNotification:
    notification_read_repo: NotificationReadRepository

    async def execute(
        self,
        notification_id: NotificationId,
        requesting_user_id: UserId,
    ) -> Notification:
        notification = await self.notification_read_repo.get(notification_id)
        if notification is None:
            raise NotificationNotFoundError(f"Notification {notification_id} not found.")
        if notification.user_id != requesting_user_id:
            raise NotificationNotFoundError(f"Notification {notification_id} not found.")
        if notification.read_at is not None:
            return notification
        notification.read_at = datetime.now(UTC)
        await self.notification_read_repo.save(notification)
        return notification
