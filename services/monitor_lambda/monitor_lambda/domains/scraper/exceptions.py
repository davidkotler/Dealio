"""Domain exceptions for the scraper bounded context."""
from __future__ import annotations


class ScraperInternalError(Exception):
    """Raised when an unexpected internal error occurs during scraping."""


class LLMExtractionError(Exception):
    """Raised when the LLM provider fails (auth, quota, network, or invalid response)."""
