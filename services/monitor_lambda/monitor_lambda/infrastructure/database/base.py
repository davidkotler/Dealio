"""SQLAlchemy declarative base for monitor_lambda ORM models."""
from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class MonitorBase(DeclarativeBase):
    """Base class for all monitor_lambda ORM models."""
