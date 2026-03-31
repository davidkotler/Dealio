"""Scraper Lambda entry point — product price scraping job."""
from __future__ import annotations

import asyncio
from typing import Any

from pipeline.shared.scraper_domain.flows.scrape_flow import scrape_flow
from pipeline.shared.scraper_domain.models.domain.scraper_result import ScraperSuccess
from pipeline.shared.scraper_domain.ports.llm_client import LLMClient
from pipeline.shared.infrastructure.settings import Settings


def _build_llm_client(settings: Settings) -> LLMClient:
    model = settings.llm_model
    if settings.llm_provider == "openai":
        from pipeline.shared.scraper_domain.adapters.openai_llm_client import OpenAILLMClient

        return OpenAILLMClient(_api_key=settings.llm_api_key, _model=model or "gpt-4o-mini")
    if settings.llm_provider == "gemini":
        from pipeline.shared.scraper_domain.adapters.gemini_llm_client import GeminiLLMClient

        return GeminiLLMClient(_api_key=settings.llm_api_key, _model=model or "gemini-2.5-flash")
    raise ValueError(f"Unsupported LLM_PROVIDER: {settings.llm_provider!r}")


def handler(event: dict[str, Any], context: object) -> dict[str, Any]:
    """Lambda handler — accepts {url: str}, returns scrape result dict."""
    url = event.get("url", "")
    if not url:
        return {
            "status": "failure",
            "error_type": "parse_error",
            "message": "Missing url in event",
            "status_code": None,
        }
    settings = Settings()
    llm_client = _build_llm_client(settings)
    result = asyncio.run(scrape_flow(url, llm_client=llm_client))
    if isinstance(result, ScraperSuccess):
        return {
            "status": "success",
            "price": str(result.price),
            "product_name": result.product_name,
        }
    return {
        "status": "failure",
        "error_type": result.error_type.value,
        "message": result.message,
        "status_code": result.status_code,
    }
