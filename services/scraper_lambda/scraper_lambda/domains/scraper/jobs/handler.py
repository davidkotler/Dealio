"""Scraper Lambda entry point — product price scraping job."""
from __future__ import annotations

import asyncio
from typing import Any

from scraper_lambda.domains.scraper.flows.scrape_flow import scrape_flow
from scraper_lambda.domains.scraper.models.domain.scraper_result import (
    ScraperSuccess,
)


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
    result = asyncio.run(scrape_flow(url))
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
