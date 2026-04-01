from __future__ import annotations

import asyncio
from dataclasses import dataclass

import boto3

from pipeline.domains.scraper.models.contracts.events.price_drop_sns_message import PriceDropSNSMessage
from pipeline.domains.scraper.models.domain.price_drop_message import PriceDropMessage


@dataclass
class SNSPublishAdapter:
    _topic_arn: str
    _region: str

    async def publish_price_drop(self, message: PriceDropMessage) -> None:
        client = boto3.client("sns", region_name=self._region)
        sns_message = PriceDropSNSMessage.from_domain(message)
        await asyncio.to_thread(
            client.publish,
            TopicArn=self._topic_arn,
            Message=sns_message.model_dump_json(),
        )
