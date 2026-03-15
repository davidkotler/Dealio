from __future__ import annotations

from scraper_lambda.domains.scraper.models.domain.scraper_result import (
    ScraperErrorType,
    ScraperFailure,
    ScraperResult,
    ScraperSuccess,
)
from scraper_lambda.domains.scraper.flows.classify_response import (
    classify_response,
)
from scraper_lambda.domains.scraper.flows.extract_name import extract_name
from scraper_lambda.domains.scraper.flows.extract_price import extract_price
from scraper_lambda.domains.scraper.flows.fetch_page import fetch_page


async def scrape_flow(url: str) -> ScraperResult:
    """
    Orchestrate the complete scraping flow for a product URL.

    Flow:
    1. Fetch the page from the URL
    2. Classify the response (ok, blocked, http_error)
    3. Extract price from HTML
    4. Extract product name from HTML
    5. Return success or failure result

    Catches unexpected exceptions and returns ScraperFailure with PARSE_ERROR.

    Args:
        url: The product URL to scrape

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

        # Step 3: Extract price
        price = extract_price(result.text)
        if price is None:
            return ScraperFailure(
                error_type=ScraperErrorType.PARSE_ERROR,
                message="Price not found",
                status_code=None,
            )

        # Step 4: Extract product name
        name = extract_name(result.text)
        if name is None:
            return ScraperFailure(
                error_type=ScraperErrorType.PARSE_ERROR,
                message="Product name not found",
                status_code=None,
            )

        # Step 5: Return success
        return ScraperSuccess(price=price, product_name=name)

    except Exception as e:
        return ScraperFailure(
            error_type=ScraperErrorType.PARSE_ERROR,
            message=str(e),
            status_code=None,
        )
