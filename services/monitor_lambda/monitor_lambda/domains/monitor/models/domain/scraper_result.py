# Mirror of scraper_lambda's ScraperResult — no shared lib at MVP
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum


class ScraperErrorType(Enum):
    TIMEOUT = "timeout"
    HTTP_ERROR = "http_error"
    PARSE_ERROR = "parse_error"
    BLOCKED = "blocked"


@dataclass(frozen=True)
class ScraperSuccess:
    price: Decimal
    product_name: str


@dataclass(frozen=True)
class ScraperFailure:
    error_type: ScraperErrorType
    message: str
    status_code: int | None


ScraperResult = ScraperSuccess | ScraperFailure
