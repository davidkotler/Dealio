"""Database infrastructure package.

Importing this package registers all ORM models with WebappBase.metadata
so that create_all / drop_all work correctly.
"""
from webapp.infrastructure.database.base import WebappBase
from webapp.domains.identity.models.persistence.user_record import UserRecord
from webapp.domains.identity.models.persistence.password_reset_token_record import PasswordResetTokenRecord
from webapp.domains.tracker.models.persistence.tracked_product_record import TrackedProductRecord
from webapp.domains.notifier.models.persistence.notification_record import NotificationRecord

__all__ = [
    "WebappBase",
    "UserRecord",
    "PasswordResetTokenRecord",
    "TrackedProductRecord",
    "NotificationRecord",
]