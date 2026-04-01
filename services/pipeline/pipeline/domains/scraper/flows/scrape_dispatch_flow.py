from __future__ import annotations

from datetime import datetime, timezone

import structlog

from pipeline.domains.scraper.models.domain.price_drop_message import PriceDropMessage
from pipeline.domains.scraper.models.domain.scraper_event_payload import ScraperEventPayload
from pipeline.domains.scraper.ports.price_check_log_write_port import PriceCheckLogWritePort
from pipeline.domains.scraper.ports.sns_publish_port import SNSPublishPort
from pipeline.shared.scraper_domain.flows.scrape_flow import scrape_flow
from pipeline.shared.scraper_domain.models.domain.scraper_result import ScraperFailure, ScraperSuccess
from pipeline.shared.scraper_domain.ports.llm_client import LLMClient

log = structlog.get_logger()


async def scrape_dispatch_flow(
    *,
    event: ScraperEventPayload,
    llm_client: LLMClient,
    sns_port: SNSPublishPort,
    log_port: PriceCheckLogWritePort,
) -> None:
    bound_log = log.bind(
        correlation_id=str(event.correlation_id),
        tracked_product_id=str(event.tracked_product_id),
        stage="scraper",
    )
    bound_log.info("scraper.scrape.started")
    result = await scrape_flow(event.url, llm_client=llm_client)
    checked_at = datetime.now(tz=timezone.utc)

    match result:
        case ScraperFailure() as failure:
            bound_log.warning("scraper.scrape.failure", error_type=failure.error_type.value)
            await log_port.write_failure(
                tracked_product_id=event.tracked_product_id,
                failure=failure,
                checked_at=checked_at,
                correlation_id=event.correlation_id,
            )
        case ScraperSuccess() as success if success.price < event.current_price:
            bound_log.info("scraper.price_drop.detected", user_id=str(event.user_id))
            await sns_port.publish_price_drop(
                PriceDropMessage(
                    tracked_product_id=event.tracked_product_id,
                    user_id=event.user_id,
                    user_email=event.user_email,
                    product_name=event.product_name,
                    product_url=event.url,
                    old_price=event.current_price,
                    new_price=success.price,
                    correlation_id=event.correlation_id,
                )
            )
        case ScraperSuccess():
            bound_log.info("scraper.scrape.no_price_drop")
