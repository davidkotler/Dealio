"""Email Lambda handler."""
from __future__ import annotations

import asyncio
import json
import uuid
from decimal import Decimal
from typing import Any

from pipeline.domains.email.adapters.ses_email_sender import SESEmailSenderAdapter
from pipeline.domains.email.flows.send_alert_flow import send_alert_flow
from pipeline.domains.email.models.domain.email_alert_payload import EmailAlertPayload
from pipeline.shared.infrastructure.settings import Settings


async def _async_handler(sqs_event: dict[str, Any]) -> None:
    settings = Settings()
    adapter = SESEmailSenderAdapter(
        _from_address=settings.ses_from_address,
        _region=settings.aws_region,
    )

    for record in sqs_event["Records"]:
        sns_envelope = json.loads(record["body"])
        body = json.loads(sns_envelope["Message"])

        payload = EmailAlertPayload(
            to_email=body["user_email"],
            user_id=uuid.UUID(body["user_id"]),
            product_name=body["product_name"],
            product_url=body["product_url"],
            old_price=Decimal(body["old_price"]),
            new_price=Decimal(body["new_price"]),
            correlation_id=uuid.UUID(body["correlation_id"]),
        )
        await send_alert_flow(payload=payload, email_sender=adapter)


def handler(event: dict[str, Any], context: Any) -> dict[str, str]:
    asyncio.run(_async_handler(event))
    return {"status": "ok"}
