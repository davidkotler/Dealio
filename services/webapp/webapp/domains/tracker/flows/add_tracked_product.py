from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from webapp.domains.identity.models.domain.types import UserId
from webapp.domains.scraper_client.models.domain.scraper_result import ScraperFailure, ScraperSuccess
from webapp.domains.scraper_client.ports.scraper_port import ScraperPort
from webapp.domains.tracker.exceptions import (
    DuplicateProductError,
    ProductLimitExceededError,
    ScrapingFailedError,
)
from webapp.domains.tracker.models.domain.price import Price
from webapp.domains.tracker.models.domain.product_url import ProductUrl
from webapp.domains.tracker.models.domain.tracked_product import TrackedProduct
from webapp.domains.tracker.models.domain.types import TrackedProductId
from webapp.domains.tracker.ports.tracked_product_repository import TrackedProductRepository

_PRODUCT_LIMIT = 5


@dataclass
class AddTrackedProduct:
    product_repo: TrackedProductRepository
    scraper: ScraperPort

    async def execute(self, user_id: UserId, raw_url: str) -> TrackedProduct:
        url = ProductUrl.parse(raw_url)

        count = await self.product_repo.count_by_user(user_id)
        if count >= _PRODUCT_LIMIT:
            raise ProductLimitExceededError(
                f"User {user_id} has reached the product tracking limit of {_PRODUCT_LIMIT}."
            )

        already_exists = await self.product_repo.exists_by_user_and_url(user_id, url.value)
        if already_exists:
            raise DuplicateProductError(
                f"User {user_id} is already tracking {url.value!r}."
            )

        # result = await self.scraper.scrape(url.value)
        result = ScraperSuccess(price=70.0, product_name="name test")
        if isinstance(result, ScraperFailure):
            raise ScrapingFailedError(
                f"Scraping {url.value!r} failed: {result.message}"
            ) from None

        product = TrackedProduct(
            id=TrackedProductId(uuid.uuid4()),
            user_id=user_id,
            url=url,
            product_name=result.product_name,
            current_price=Price(value=result.price),
            previous_price=None,
            last_checked_at=None,
            created_at=datetime.now(UTC),
        )
        await self.product_repo.save(product)
        return product
