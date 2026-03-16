"""Pydantic API contracts for tracked products."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AddProductRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    url: str


class ProductResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    url: str
    product_name: str
    current_price: str
    previous_price: str | None
    last_checked_at: datetime | None
    created_at: datetime


class DashboardResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    products: list[ProductResponse]
    unread_notification_count: int
