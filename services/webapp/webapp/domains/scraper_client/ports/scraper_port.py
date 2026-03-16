from __future__ import annotations

from typing import Protocol, runtime_checkable

from webapp.domains.scraper_client.models.domain import ScraperResult


@runtime_checkable
class ScraperPort(Protocol):
    async def scrape(self, url: str) -> ScraperResult: ...
