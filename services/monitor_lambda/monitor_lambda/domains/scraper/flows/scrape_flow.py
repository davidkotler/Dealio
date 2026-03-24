from __future__ import annotations

from monitor_lambda.domains.scraper.exceptions import LLMExtractionError
from monitor_lambda.domains.scraper.models.domain.scraper_result import (
    ScraperErrorType,
    ScraperFailure,
    ScraperResult,
    ScraperSuccess,
)
from monitor_lambda.domains.scraper.flows.classify_response import classify_response
from monitor_lambda.domains.scraper.flows.extract_name import extract_name
from monitor_lambda.domains.scraper.flows.extract_price import extract_price
from monitor_lambda.domains.scraper.flows.fetch_page import fetch_page
from monitor_lambda.domains.scraper.flows.preprocess_html import preprocess_html
from monitor_lambda.domains.scraper.ports.llm_client import LLMClient


async def scrape_flow(url: str, *, llm_client: LLMClient) -> ScraperResult:
    """
    Orchestrate the complete scraping flow for a product URL.

    Flow:
    1. Fetch the page from the URL
    2. Classify the response (ok, blocked, http_error)
    3. Preprocess HTML and attempt LLM extraction (price + name)
    4. On LLM failure or missing fields, cascade to regex/CSS fallback
    5. Return success or failure result

    Args:
        url: The product URL to scrape
        llm_client: LLM client for structured product data extraction

    Returns:
        ScraperResult: Either ScraperSuccess with price and name, or ScraperFailure with error details
    """
    try:
        # Step 1: Fetch the page
        result = await fetch_page(url)
        if isinstance(result, ScraperFailure):
            return result

        # Step 2: Classify the response
        classification = classify_response(result)
        if classification == "blocked":
            return ScraperFailure(
                error_type=ScraperErrorType.BLOCKED,
                message="Request was blocked",
                status_code=result.status_code,
            )
        if classification == "http_error":
            return ScraperFailure(
                error_type=ScraperErrorType.HTTP_ERROR,
                message=f"HTTP {result.status_code}",
                status_code=result.status_code,
            )

        # Step 3: LLM extraction
        cleaned = preprocess_html(result.text)
        llm_result = None
        try:
            llm_result = await llm_client.extract_product_data(cleaned)
        except LLMExtractionError:
            pass

        if llm_result is not None and llm_result.price is not None and llm_result.product_name is not None:
            return ScraperSuccess(price=llm_result.price, product_name=llm_result.product_name)

        # Step 4: Cascade fallback to regex/CSS extraction
        price = extract_price(result.text)
        if price is None:
            return ScraperFailure(
                error_type=ScraperErrorType.PARSE_ERROR,
                message="Price not found",
                status_code=None,
            )

        name = extract_name(result.text)
        if name is None:
            return ScraperFailure(
                error_type=ScraperErrorType.PARSE_ERROR,
                message="Product name not found",
                status_code=None,
            )

        return ScraperSuccess(price=price, product_name=name)

    except Exception as e:
        return ScraperFailure(
            error_type=ScraperErrorType.PARSE_ERROR,
            message=str(e),
            status_code=None,
        )
