from __future__ import annotations

import httpx

from pipeline.shared.scraper_domain.models.domain.scraper_result import (
    ScraperErrorType,
    ScraperFailure,
)


async def fetch_page(url: str) -> httpx.Response | ScraperFailure:
    """
    Fetch a page from the given URL using an async HTTP client.

    Args:
        url: The URL to fetch

    Returns:
        Either the raw httpx.Response on success (any status code), or a ScraperFailure on network error.
        Note: Status code checking is a separate concern; 4xx/5xx responses are returned as-is.

    Raises:
        ScraperFailure: On network errors (timeout, connection issues)
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)
            return response
    except httpx.TimeoutException as e:
        return ScraperFailure(
            error_type=ScraperErrorType.TIMEOUT,
            message=str(e),
            status_code=None,
        )
    except httpx.RequestError as e:
        return ScraperFailure(
            error_type=ScraperErrorType.HTTP_ERROR,
            message=str(e),
            status_code=None,
        )
