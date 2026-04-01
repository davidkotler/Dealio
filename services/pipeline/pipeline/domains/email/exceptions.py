"""Email domain exceptions."""
from __future__ import annotations


class EmailDeliveryError(Exception):
    """Raised when SES fails to deliver an email."""
