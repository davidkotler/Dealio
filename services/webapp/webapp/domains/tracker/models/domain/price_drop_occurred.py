from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from webapp.domains.identity.models.domain.types import UserId
from webapp.domains.tracker.models.domain.price import Price
from webapp.domains.tracker.models.domain.product_url import ProductUrl
from webapp.domains.tracker.models.domain.types import TrackedProductId


@dataclass(frozen=True)
class PriceDropOccurred:
    tracked_product_id: TrackedProductId
    user_id: UserId
    product_name: str
    product_url: ProductUrl
    old_price: Price
    new_price: Price
    occurred_at: datetime
