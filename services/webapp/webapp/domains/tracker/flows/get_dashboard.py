from __future__ import annotations

import asyncio
from dataclasses import dataclass

from webapp.domains.identity.models.domain.types import UserId
from webapp.domains.tracker.models.domain.dashboard_data import DashboardData
from webapp.domains.tracker.ports.notification_read_repository import NotificationReadRepository
from webapp.domains.tracker.ports.tracked_product_repository import TrackedProductRepository


@dataclass
class GetDashboard:
    product_repo: TrackedProductRepository
    notification_read_repo: NotificationReadRepository

    async def execute(self, user_id: UserId) -> DashboardData:
        products, unread_count = await asyncio.gather(
            self.product_repo.list_by_user_id(user_id),
            self.notification_read_repo.count_unread_by_user(user_id),
        )
        return DashboardData(
            products=tuple(products),
            unread_notification_count=unread_count,
        )
