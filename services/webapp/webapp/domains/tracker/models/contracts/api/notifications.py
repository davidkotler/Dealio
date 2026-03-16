"""Pydantic API contracts for notifications."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class NotificationResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    tracked_product_id: str
    old_price: str
    new_price: str
    created_at: datetime
    read_at: datetime | None


class NotificationListResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    notifications: list[NotificationResponse]
    next_cursor: str | None
