from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime

from monitor_lambda.domains.monitor.models.domain.price_check_result import PriceCheckResult
from monitor_lambda.domains.monitor.models.domain.types import TrackedProductId

_MAX_RETRY_COUNT = 10


@dataclass
class PriceCheckLog:
    id: uuid.UUID
    tracked_product_id: TrackedProductId
    result: PriceCheckResult
    checked_at: datetime
    retry_count: int = field(default=0)

    def __post_init__(self) -> None:
        if not (0 <= self.retry_count <= _MAX_RETRY_COUNT):
            raise ValueError(
                f"retry_count must be between 0 and {_MAX_RETRY_COUNT}, got {self.retry_count!r}."
            )
