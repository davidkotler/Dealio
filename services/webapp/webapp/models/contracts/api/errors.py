"""Shared API error response models."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ErrorResponse(BaseModel):
    """Standard API error response envelope."""

    model_config = ConfigDict(frozen=True)

    detail: str
    code: str
