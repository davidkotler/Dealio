"""Domain exceptions for the monitor bounded context."""
from __future__ import annotations


class MonitorError(Exception):
    """Base exception for all monitor domain errors."""


class PriceCheckCycleError(MonitorError):
    """Raised when an error occurs during a full price-check cycle."""


class ProductCheckError(MonitorError):
    """Raised when checking the price for a single product fails."""


class EmailDeliveryError(MonitorError):
    """Raised when a price-drop notification email cannot be delivered."""
