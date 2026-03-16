from __future__ import annotations

from typing import Protocol, runtime_checkable

from monitor_lambda.domains.monitor.models.domain.notification import Notification


@runtime_checkable
class NotificationWriteRepository(Protocol):
    async def save(self, notification: Notification) -> None: ...
