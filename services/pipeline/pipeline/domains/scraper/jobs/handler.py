"""Scraper Lambda handler — scrape dispatch entry point."""
from __future__ import annotations

import asyncio
import uuid
from decimal import Decimal
from typing import Any

from pipeline.domains.scraper.adapters.sns_publish_adapter import SNSPublishAdapter
from pipeline.domains.scraper.adapters.sqlalchemy_failure_log_adapter import SQLAlchemyFailureLogAdapter
from pipeline.domains.scraper.flows.scrape_dispatch_flow import scrape_dispatch_flow
from pipeline.domains.scraper.models.domain.scraper_event_payload import ScraperEventPayload
from pipeline.shared.infrastructure.database import make_engine, make_session
from pipeline.shared.infrastructure.settings import Settings
from pipeline.shared.scraper_domain.adapters.gemini_llm_client import GeminiLLMClient
from pipeline.shared.scraper_domain.adapters.openai_llm_client import OpenAILLMClient


def handler(event: dict[str, Any], context: object) -> dict[str, str]:
    asyncio.run(_async_handler(event))
    return {"status": "ok"}


async def _async_handler(raw_event: dict[str, Any]) -> None:
    settings = Settings()
    detail = raw_event["detail"]
    payload = ScraperEventPayload(
        tracked_product_id=uuid.UUID(detail["tracked_product_id"]),
        url=detail["url"],
        current_price=Decimal(detail["current_price"]),
        user_id=uuid.UUID(detail["user_id"]),
        user_email=detail["user_email"],
        product_name=detail["product_name"],
        correlation_id=uuid.UUID(detail["correlation_id"]),
    )

    if settings.llm_provider == "gemini":
        llm_client = GeminiLLMClient(_api_key=settings.llm_api_key, _model=settings.llm_model)
    else:
        llm_client = OpenAILLMClient(_api_key=settings.llm_api_key, _model=settings.llm_model)

    engine = make_engine(settings.database_url)
    async with make_session(engine) as session:
        await scrape_dispatch_flow(
            event=payload,
            llm_client=llm_client,
            sns_port=SNSPublishAdapter(
                _topic_arn=settings.sns_price_drop_topic_arn,
                _region=settings.aws_region,
            ),
            log_port=SQLAlchemyFailureLogAdapter(session),
        )
