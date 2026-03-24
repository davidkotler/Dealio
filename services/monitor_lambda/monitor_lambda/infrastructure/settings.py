"""Runtime settings loaded from environment variables."""
from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Settings:
    database_url: str = field(default="postgresql+asyncpg://dealio:dealio@localhost:5433/dealio?ssl=disable")
    ses_from_address: str = field(default="test")
    aws_region: str = field(default="us-east-1")
    llm_provider: str = field(default="gemini")
    llm_api_key: str = field(default="")
    llm_model: str = field(default="gemini-2.5-flash")
