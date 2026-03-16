from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from webapp.domains.identity.models.domain.types import UserId
from webapp.domains.tracker.models.domain.price import Price
from webapp.domains.tracker.models.domain.price_drop_occurred import PriceDropOccurred
from webapp.domains.tracker.models.domain.product_url import ProductUrl
from webapp.domains.tracker.models.domain.types import TrackedProductId


@dataclass
class TrackedProduct:
    id: TrackedProductId
    user_id: UserId
    url: ProductUrl
    product_name: str
    current_price: Price
    previous_price: Price | None
    last_checked_at: datetime | None
    created_at: datetime

    def record_price_check(self, new_price: Price, checked_at: datetime) -> PriceDropOccurred | None:
        if new_price < self.current_price:
            event = PriceDropOccurred(
                tracked_product_id=self.id,
                user_id=self.user_id,
                product_name=self.product_name,
                product_url=self.url,
                old_price=self.current_price,
                new_price=new_price,
                occurred_at=checked_at,
            )
            self.previous_price = self.current_price
            self.current_price = new_price
            self.last_checked_at = checked_at
            return event
        self.current_price = new_price
        self.last_checked_at = checked_at
        return None
