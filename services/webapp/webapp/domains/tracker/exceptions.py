"""Domain exceptions for the tracker bounded context."""
from __future__ import annotations


class TrackerError(Exception):
    """Base exception for all tracker domain errors."""


class InvalidProductUrlError(TrackerError):
    """Raised when a product URL is malformed or points to a disallowed host."""


class ProductLimitExceededError(TrackerError):
    """Raised when a user attempts to track more products than their limit allows."""


class DuplicateProductError(TrackerError):
    """Raised when a user attempts to track a product URL they are already tracking."""


class ScrapingFailedError(TrackerError):
    """Raised when the scraper cannot retrieve a price for a product."""


class ProductNotFoundError(TrackerError):
    """Raised when a tracked product cannot be found."""
