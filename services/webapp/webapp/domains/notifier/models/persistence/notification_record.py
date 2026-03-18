"""SQLAlchemy ORM model for the notifications table."""
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from webapp.infrastructure.database.base import WebappBase


class NotificationRecord(WebappBase):
    __tablename__ = "notifications"
    __table_args__ = (
        CheckConstraint("new_price < old_price", name="chk_notifications_price_drop"),
        CheckConstraint("old_price > 0", name="chk_notifications_old_price"),
        CheckConstraint("new_price >= 0", name="chk_notifications_new_price"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    tracked_product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tracked_products.id", ondelete="CASCADE"),
        nullable=False,
    )
    old_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    new_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default="NOW()")
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
