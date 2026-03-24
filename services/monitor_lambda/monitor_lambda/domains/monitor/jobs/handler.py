"""Monitor Lambda entry point — price alert evaluation job."""
from __future__ import annotations

import asyncio
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from monitor_lambda.domains.monitor.adapters.local_scraper_adapter import LocalScraperAdapter
from monitor_lambda.domains.monitor.adapters.ses_email_sender import SESEmailSender
from monitor_lambda.domains.monitor.adapters.sqlalchemy_notification_write_repository import (
    SQLAlchemyNotificationWriteRepository,
)
from monitor_lambda.domains.monitor.adapters.sqlalchemy_price_check_log_repository import (
    SQLAlchemyPriceCheckLogRepository,
)
from monitor_lambda.domains.monitor.adapters.sqlalchemy_tracked_product_repository import (
    SQLAlchemyTrackedProductRepository,
)
from monitor_lambda.domains.monitor.flows.price_check_cycle_flow import PriceCheckCycleFlow
from monitor_lambda.infrastructure.settings import Settings


def handler(event: dict[str, Any], context: object) -> dict[str, str]:
    """Lambda handler for the price-check monitoring cycle."""
    asyncio.run(_async_handler())
    return {"status": "ok"}


async def _async_handler() -> None:
    settings = Settings()
    engine = create_async_engine(settings.database_url)
    async with AsyncSession(engine) as session:
        flow = PriceCheckCycleFlow(
            product_repo=SQLAlchemyTrackedProductRepository(session),
            price_check_log_repo=SQLAlchemyPriceCheckLogRepository(session),
            notification_repo=SQLAlchemyNotificationWriteRepository(session),
            scraper=LocalScraperAdapter(
                _llm_provider=settings.llm_provider,
                _llm_api_key=settings.llm_api_key,
                _llm_model=settings.llm_model,
            ),
            email_sender=SESEmailSender(
                _from_address=settings.ses_from_address,
                _region=settings.aws_region,
            ),
        )
        await flow.run()
