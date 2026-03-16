from __future__ import annotations

from typing import Protocol, runtime_checkable

from monitor_lambda.domains.monitor.models.domain import ScraperResult


@runtime_checkable
class ScraperPort(Protocol):
    async def scrape(self, url: str) -> ScraperResult: ...
