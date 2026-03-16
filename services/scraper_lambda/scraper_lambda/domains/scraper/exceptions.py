"""Domain exceptions for the scraper bounded context."""
from __future__ import annotations


class ScraperInternalError(Exception):
    """Raised when an unexpected internal error occurs during scraping."""
