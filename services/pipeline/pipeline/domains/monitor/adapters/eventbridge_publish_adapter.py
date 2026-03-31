"""EventBridge adapter for publishing ProductPriceCheckRequested events."""
from __future__ import annotations

import asyncio
from typing import Any

import boto3
import structlog

from pipeline.domains.monitor.models.contracts.events.product_price_check_requested import (
    ProductPriceCheckRequestedDetail,
)
from pipeline.domains.monitor.models.domain.product_fan_out_payload import ProductFanOutPayload

log = structlog.get_logger()

_BATCH_SIZE = 10
_SOURCE = "dealio.pipeline.monitor"
_DETAIL_TYPE = "ProductPriceCheckRequested"


class EventBridgePublishAdapter:
    def __init__(self, *, _bus_name: str, _region: str) -> None:
        self._bus_name = _bus_name
        self._region = _region
        self._client = boto3.client("events", region_name=_region)

    async def publish_batch(self, payloads: list[ProductFanOutPayload]) -> None:
        chunks = [
            payloads[i : i + _BATCH_SIZE]
            for i in range(0, len(payloads), _BATCH_SIZE)
        ]
        await asyncio.gather(*[self._put_chunk(chunk) for chunk in chunks])

    async def _put_chunk(self, chunk: list[ProductFanOutPayload]) -> None:
        entries = [self._to_entry(p) for p in chunk]
        await asyncio.to_thread(self._client.put_events, Entries=entries)

    def _to_entry(self, payload: ProductFanOutPayload) -> dict[str, Any]:
        return {
            "Source": _SOURCE,
            "DetailType": _DETAIL_TYPE,
            "Detail": ProductPriceCheckRequestedDetail.from_payload(payload).model_dump_json(),
            "EventBusName": self._bus_name,
        }
