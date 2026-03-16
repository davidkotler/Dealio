"""Domain exceptions for the notifier bounded context."""


class NotifierError(Exception):
    """Base exception for all notifier domain errors."""


class NotificationNotFoundError(NotifierError):
    """Raised when a notification cannot be found."""


class InvalidCursorError(NotifierError):
    """Raised when a pagination cursor cannot be decoded."""
