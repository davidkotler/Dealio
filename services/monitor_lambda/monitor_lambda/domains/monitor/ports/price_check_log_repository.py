from __future__ import annotations

from typing import Protocol, runtime_checkable

from monitor_lambda.domains.monitor.models.domain import PriceCheckLog


@runtime_checkable
class PriceCheckLogRepository(Protocol):
    async def save(self, log: PriceCheckLog) -> None: ...
