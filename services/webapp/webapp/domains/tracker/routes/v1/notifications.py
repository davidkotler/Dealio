"""Tracker notification routes — v1."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from webapp.dependencies import get_current_user, get_db_session
from webapp.domains.notifier.models.domain.types import NotificationId
from webapp.domains.tracker.adapters.sqlalchemy_notification_read_repository import (
    SQLAlchemyNotificationReadRepository,
)
from webapp.domains.tracker.flows.dismiss_notification import DismissNotification
from webapp.domains.tracker.flows.list_notifications import ListNotifications
from webapp.domains.tracker.models.contracts.api.notifications import (
    NotificationListResponse,
    NotificationResponse,
)
from webapp.domains.notifier.models.domain.notification import Notification
from webapp.domains.identity.models.domain.user import User

router = APIRouter(tags=["notifications"])


def _to_notification_response(n: Notification) -> NotificationResponse:
    return NotificationResponse(
        id=str(n.id),
        tracked_product_id=str(n.tracked_product_id),
        old_price=str(n.old_price.value),
        new_price=str(n.new_price.value),
        created_at=n.created_at,
        read_at=n.read_at,
    )


@router.get("/notifications", status_code=200, response_model=NotificationListResponse)
async def list_notifications(
    cursor: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=50),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> NotificationListResponse:
    data = await ListNotifications(
        notification_read_repo=SQLAlchemyNotificationReadRepository(session),
    ).execute(current_user.id, cursor, limit)
    return NotificationListResponse(
        notifications=[_to_notification_response(n) for n in data.notifications],
        next_cursor=data.next_cursor,
    )


@router.patch("/notifications/{notification_id}/read", status_code=200, response_model=NotificationResponse)
async def dismiss_notification(
    notification_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> NotificationResponse:
    notification = await DismissNotification(
        notification_read_repo=SQLAlchemyNotificationReadRepository(session),
    ).execute(NotificationId(notification_id), current_user.id)
    return _to_notification_response(notification)
