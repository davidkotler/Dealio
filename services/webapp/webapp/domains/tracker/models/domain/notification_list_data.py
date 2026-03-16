from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from webapp.domains.notifier.models.domain.notification import Notification


@dataclass(frozen=True)
class NotificationListData:
    notifications: tuple[Notification, ...]
    next_cursor: str | None
