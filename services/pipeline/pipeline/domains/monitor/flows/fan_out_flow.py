"""Fan-out flow: reads all tracked products and publishes one EventBridge event per product."""
from __future__ import annotations

import uuid

import structlog

from pipeline.domains.monitor.ports.eventbridge_publish_port import EventBridgePublishPort
from pipeline.domains.monitor.ports.tracked_product_read_port import TrackedProductReadPort

log = structlog.get_logger()


async def fan_out_flow(
    *,
    product_read_port: TrackedProductReadPort,
    eventbridge_port: EventBridgePublishPort,
) -> None:
    """Run one fan-out cycle: generate correlation_id, read products, publish events."""
    correlation_id = uuid.uuid4()
    products = await product_read_port.list_all_for_fan_out(correlation_id=correlation_id)

    if not products:
        log.info("monitor.fan_out.no_products", correlation_id=str(correlation_id), stage="monitor")
        return

    log.info(
        "monitor.fan_out.started",
        correlation_id=str(correlation_id),
        stage="monitor",
        product_count=len(products),
    )
    await eventbridge_port.publish_batch(products)
    log.info(
        "monitor.fan_out.complete",
        correlation_id=str(correlation_id),
        stage="monitor",
        product_count=len(products),
    )
