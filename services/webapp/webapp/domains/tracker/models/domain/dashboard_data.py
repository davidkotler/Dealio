from __future__ import annotations

from dataclasses import dataclass

from webapp.domains.tracker.models.domain.tracked_product import TrackedProduct


@dataclass(frozen=True)
class DashboardData:
    products: tuple[TrackedProduct, ...]
    unread_notification_count: int
