"""Monitor Lambda handler — fan-out entry point."""
from __future__ import annotations

import asyncio
from typing import Any

from pipeline.domains.monitor.adapters.eventbridge_publish_adapter import EventBridgePublishAdapter
from pipeline.domains.monitor.adapters.sqlalchemy_tracked_product_read_adapter import (
    SQLAlchemyTrackedProductReadAdapter,
)
from pipeline.domains.monitor.flows.fan_out_flow import fan_out_flow
from pipeline.shared.infrastructure.database import make_engine, make_session
from pipeline.shared.infrastructure.settings import Settings


def handler(event: dict[str, Any], context: object) -> dict[str, str]:
    asyncio.run(_async_handler())
    return {"status": "ok"}


async def _async_handler() -> None:
    settings = Settings()
    engine = make_engine(settings.database_url)
    async with make_session(engine) as session:
        await fan_out_flow(
            product_read_port=SQLAlchemyTrackedProductReadAdapter(session),
            eventbridge_port=EventBridgePublishAdapter(
                _bus_name=settings.eventbridge_bus_name,
                _region=settings.aws_region,
            ),
        )
