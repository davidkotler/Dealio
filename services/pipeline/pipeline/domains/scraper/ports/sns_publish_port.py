from __future__ import annotations

from typing import Protocol, runtime_checkable

from pipeline.domains.scraper.models.domain.price_drop_message import PriceDropMessage


@runtime_checkable
class SNSPublishPort(Protocol):
    async def publish_price_drop(self, message: PriceDropMessage) -> None: ...
