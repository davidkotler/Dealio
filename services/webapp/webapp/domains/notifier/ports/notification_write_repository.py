from __future__ import annotations

from typing import Protocol, runtime_checkable

from webapp.domains.notifier.models.domain import Notification


@runtime_checkable
class NotificationWriteRepository(Protocol):
    async def save(self, notification: Notification) -> None: ...
