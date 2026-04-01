from __future__ import annotations

import asyncio
import json
import uuid
from decimal import Decimal
from typing import Any

from pipeline.domains.db_update.adapters.sqlalchemy_price_drop_persistence_adapter import (
    SQLAlchemyPriceDropPersistenceAdapter,
)
from pipeline.domains.db_update.flows.persist_price_drop_flow import persist_price_drop_flow
from pipeline.domains.db_update.models.domain.price_drop_sqs_message import PriceDropSQSMessage
from pipeline.shared.infrastructure.database import make_engine, make_session
from pipeline.shared.infrastructure.settings import Settings


async def _async_handler(sqs_event: dict[str, Any]) -> None:
    settings = Settings()
    engine = make_engine(settings.database_url)

    for record in sqs_event["Records"]:
        sns_envelope = json.loads(record["body"])
        body = json.loads(sns_envelope["Message"])

        message = PriceDropSQSMessage(
            tracked_product_id=uuid.UUID(body["tracked_product_id"]),
            user_id=uuid.UUID(body["user_id"]),
            user_email=body["user_email"],
            product_name=body["product_name"],
            product_url=body["product_url"],
            old_price=Decimal(body["old_price"]),
            new_price=Decimal(body["new_price"]),
            correlation_id=uuid.UUID(body["correlation_id"]),
        )
        async with make_session(engine) as session:
            adapter = SQLAlchemyPriceDropPersistenceAdapter(session)
            await persist_price_drop_flow(
                message=message,
                product_write_port=adapter,
                notification_port=adapter,
                log_port=adapter,
            )
            await session.commit()


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    asyncio.run(_async_handler(event))
    return {"status": "ok"}
