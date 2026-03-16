"""SQLAlchemy declarative base for webapp ORM models."""
from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class WebappBase(DeclarativeBase):
    """Base class for all webapp ORM models."""
