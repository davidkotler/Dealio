"""Shared API error response models."""
from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


class ErrorDetail(BaseModel):
    """Single error detail."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    field: Annotated[str | None, Field(default=None, description="Field that caused the error")]
    message: Annotated[str, Field(description="Human-readable error message")]


class ErrorResponse(BaseModel):
    """Standard API error response envelope."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    errors: Annotated[list[ErrorDetail], Field(description="List of error details")]
