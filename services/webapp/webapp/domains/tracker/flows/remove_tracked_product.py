from __future__ import annotations

from dataclasses import dataclass

from webapp.domains.identity.models.domain.types import UserId
from webapp.domains.tracker.exceptions import ProductNotFoundError
from webapp.domains.tracker.models.domain.types import TrackedProductId
from webapp.domains.tracker.ports.tracked_product_repository import TrackedProductRepository


@dataclass
class RemoveTrackedProduct:
    product_repo: TrackedProductRepository

    async def execute(self, product_id: TrackedProductId, requesting_user_id: UserId) -> None:
        product = await self.product_repo.get_by_id(product_id)
        if product is None:
            raise ProductNotFoundError(f"Product {product_id} not found.")
        if product.user_id != requesting_user_id:
            raise ProductNotFoundError(f"Product {product_id} not found.")
        await self.product_repo.delete(product_id)
