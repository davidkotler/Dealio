"""In-process scraper adapter — calls scrape_flow directly instead of via Lambda."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from monitor_lambda.domains.monitor.models.domain.scraper_result import (
    ScraperErrorType,
    ScraperFailure,
    ScraperResult,
    ScraperSuccess,
)
from monitor_lambda.domains.scraper.adapters.gemini_llm_client import GeminiLLMClient
from monitor_lambda.domains.scraper.adapters.openai_llm_client import OpenAILLMClient
from monitor_lambda.domains.scraper.flows.scrape_flow import scrape_flow
import monitor_lambda.domains.scraper.models.domain.scraper_result as _scraper_models


def _build_llm_client(provider: str, api_key: str, model: str) -> Any:
    if provider == "openai":
        return OpenAILLMClient(_api_key=api_key, _model=model)
    return GeminiLLMClient(_api_key=api_key, _model=model)


@dataclass
class LocalScraperAdapter:
    _llm_provider: str
    _llm_api_key: str
    _llm_model: str

    async def scrape(self, url: str) -> ScraperResult:
        llm_client = _build_llm_client(self._llm_provider, self._llm_api_key, self._llm_model)
        result = await scrape_flow(url, llm_client=llm_client)
        return _convert(result)


def _convert(result: _scraper_models.ScraperResult) -> ScraperResult:
    if isinstance(result, _scraper_models.ScraperSuccess):
        return ScraperSuccess(price=result.price, product_name=result.product_name)
    return ScraperFailure(
        error_type=ScraperErrorType(result.error_type.value),
        message=result.message,
        status_code=result.status_code,
    )
