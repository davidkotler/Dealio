"""Port for publishing events to EventBridge."""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from pipeline.domains.monitor.models.domain.product_fan_out_payload import ProductFanOutPayload


@runtime_checkable
class EventBridgePublishPort(Protocol):
    async def publish_batch(self, payloads: list[ProductFanOutPayload]) -> None: ...
