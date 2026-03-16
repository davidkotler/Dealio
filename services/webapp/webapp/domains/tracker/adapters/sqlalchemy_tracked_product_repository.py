from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from webapp.domains.identity.models.domain.types import UserId
from webapp.domains.tracker.models.domain.price import Price
from webapp.domains.tracker.models.domain.product_url import ProductUrl
from webapp.domains.tracker.models.domain.tracked_product import TrackedProduct
from webapp.domains.tracker.models.domain.types import TrackedProductId
from webapp.domains.tracker.models.persistence.tracked_product_record import TrackedProductRecord


@dataclass
class SQLAlchemyTrackedProductRepository:
    _session: AsyncSession

    async def get_by_id(self, product_id: TrackedProductId) -> TrackedProduct | None:
        result = await self._session.execute(
            select(TrackedProductRecord).where(TrackedProductRecord.id == product_id)
        )
        record = result.scalar_one_or_none()
        return _to_domain(record) if record is not None else None

    async def list_by_user_id(self, user_id: UserId) -> list[TrackedProduct]:
        result = await self._session.execute(
            select(TrackedProductRecord)
            .where(TrackedProductRecord.user_id == user_id)
            .order_by(TrackedProductRecord.created_at.desc())
        )
        return [_to_domain(r) for r in result.scalars().all()]

    async def count_by_user(self, user_id: UserId) -> int:
        result = await self._session.execute(
            select(func.count()).select_from(TrackedProductRecord)
            .where(TrackedProductRecord.user_id == user_id)
        )
        return result.scalar_one()

    async def exists_by_user_and_url(self, user_id: UserId, url: str) -> bool:
        result = await self._session.execute(
            select(TrackedProductRecord.id)
            .where(
                TrackedProductRecord.user_id == user_id,
                TrackedProductRecord.url == url,
            )
            .limit(1)
        )
        return result.scalar_one_or_none() is not None

    async def save(self, product: TrackedProduct) -> None:
        values = _to_record(product)
        stmt = (
            insert(TrackedProductRecord)
            .values(**values)
            .on_conflict_do_update(
                index_elements=["id"],
                set_={
                    "product_name": values["product_name"],
                    "current_price": values["current_price"],
                    "previous_price": values["previous_price"],
                    "last_checked_at": values["last_checked_at"],
                },
            )
        )
        await self._session.execute(stmt)
        await self._session.flush()

    async def delete(self, product_id: TrackedProductId) -> None:
        await self._session.execute(
            delete(TrackedProductRecord).where(TrackedProductRecord.id == product_id)
        )
        await self._session.flush()


def _to_domain(record: TrackedProductRecord) -> TrackedProduct:
    return TrackedProduct(
        id=TrackedProductId(record.id),
        user_id=UserId(record.user_id),
        url=ProductUrl(value=record.url),
        product_name=record.product_name,
        current_price=Price(value=record.current_price),
        previous_price=Price(value=record.previous_price) if record.previous_price is not None else None,
        last_checked_at=record.last_checked_at,
        created_at=record.created_at,
    )


def _to_record(product: TrackedProduct) -> dict:  # type: ignore[type-arg]
    return {
        "id": product.id,
        "user_id": product.user_id,
        "url": product.url.value,
        "product_name": product.product_name,
        "current_price": product.current_price.value,
        "previous_price": product.previous_price.value if product.previous_price is not None else None,
        "last_checked_at": product.last_checked_at,
        "created_at": product.created_at,
    }
