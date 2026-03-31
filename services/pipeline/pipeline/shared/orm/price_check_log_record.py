from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, SmallInteger, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from pipeline.shared.orm.base import PipelineBase


class PriceCheckLogRecord(PipelineBase):
    __tablename__ = "price_check_log"
    __table_args__ = (
        CheckConstraint(
            "result IN ('success', 'failure')",
            name="chk_price_check_log_result",
        ),
        CheckConstraint(
            "retry_count >= 0 AND retry_count <= 10",
            name="chk_price_check_log_retry_count",
        ),
        CheckConstraint(
            "(result = 'success' AND error_message IS NULL) OR (result = 'failure' AND error_message IS NOT NULL)",
            name="chk_price_check_log_error_message",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tracked_product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tracked_products.id", ondelete="CASCADE"),
        nullable=False,
    )
    checked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="NOW()"
    )
    result: Mapped[str] = mapped_column(String(10), nullable=False)
    retry_count: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
