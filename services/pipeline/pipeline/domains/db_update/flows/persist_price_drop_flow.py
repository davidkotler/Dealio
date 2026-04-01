from __future__ import annotations

from datetime import datetime, timezone

import structlog

from pipeline.domains.db_update.models.domain.price_drop_sqs_message import PriceDropSQSMessage
from pipeline.domains.db_update.ports.notification_write_port import NotificationWritePort
from pipeline.domains.db_update.ports.price_check_log_write_port import PriceCheckLogWritePort
from pipeline.domains.db_update.ports.tracked_product_write_port import TrackedProductWritePort

log = structlog.get_logger()


async def persist_price_drop_flow(
    *,
    message: PriceDropSQSMessage,
    product_write_port: TrackedProductWritePort,
    notification_port: NotificationWritePort,
    log_port: PriceCheckLogWritePort,
) -> None:
    bound_log = log.bind(
        correlation_id=str(message.correlation_id),
        tracked_product_id=str(message.tracked_product_id),
        stage="db_update",
    )
    bound_log.info("db_update.persist.started")
    checked_at = datetime.now(tz=timezone.utc)

    updated = await product_write_port.conditional_update_price(
        tracked_product_id=message.tracked_product_id,
        old_price=message.old_price,
        new_price=message.new_price,
        checked_at=checked_at,
    )
    if not updated:
        bound_log.info("db_update.conditional_write.skipped")
        return

    await notification_port.create_notification(
        tracked_product_id=message.tracked_product_id,
        user_id=message.user_id,
        old_price=message.old_price,
        new_price=message.new_price,
    )
    await log_port.write_success(
        tracked_product_id=message.tracked_product_id,
        checked_at=checked_at,
        correlation_id=message.correlation_id,
    )
    bound_log.info("db_update.persist.complete")
