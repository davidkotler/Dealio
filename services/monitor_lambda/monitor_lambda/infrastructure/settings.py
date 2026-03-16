"""Runtime settings loaded from environment variables."""
from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Settings:
    database_url: str = field(default_factory=lambda: os.environ["DATABASE_URL"])
    scraper_lambda_name: str = field(default_factory=lambda: os.environ["SCRAPER_LAMBDA_NAME"])
    ses_from_address: str = field(default_factory=lambda: os.environ["SES_FROM_ADDRESS"])
