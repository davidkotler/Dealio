# Plan: Task 9 — Tracker Domain Implementation

## Context

Task 9 implements the core user-facing tracker domain: flows for adding, removing, and dashboard-viewing of tracked products. The SQLAlchemy repository adapter and port extensions are also part of this task.

The tracker domain skeleton already exists (models, persistence record, ports, exceptions) but `flows/` and `adapters/` are empty. Two ports are also missing methods required by the new flows.

**Dependency note:** `GetDashboard` needs `NotificationReadRepository.count_unread_by_user` which does not yet exist on the port — this must be added before the flow can be implemented.

---

## Change Set (8 files)

| # | Action | File |
|---|--------|------|
| 1 | CREATE | `services/webapp/webapp/domains/tracker/models/domain/dashboard_data.py` |
| 2 | UPDATE | `services/webapp/webapp/domains/tracker/models/domain/__init__.py` |
| 3 | UPDATE | `services/webapp/webapp/domains/tracker/ports/tracked_product_repository.py` |
| 4 | UPDATE | `services/webapp/webapp/domains/tracker/ports/notification_read_repository.py` |
| 5 | CREATE | `services/webapp/webapp/domains/tracker/adapters/sqlalchemy_tracked_product_repository.py` |
| 6 | CREATE | `services/webapp/webapp/domains/tracker/flows/add_tracked_product.py` |
| 7 | CREATE | `services/webapp/webapp/domains/tracker/flows/remove_tracked_product.py` |
| 8 | CREATE | `services/webapp/webapp/domains/tracker/flows/get_dashboard.py` |

---

## File 1 — CREATE `models/domain/dashboard_data.py`

Frozen dataclass value object. Uses `tuple` (not `list`) because frozen dataclasses cannot hold mutable fields safely.

```python
from __future__ import annotations

from dataclasses import dataclass

from webapp.domains.tracker.models.domain.tracked_product import TrackedProduct


@dataclass(frozen=True)
class DashboardData:
    products: tuple[TrackedProduct, ...]
    unread_notification_count: int
```

---

## File 2 — UPDATE `models/domain/__init__.py`

Add `DashboardData` import and export. Prepend alphabetically.

**Result:**
```python
from .dashboard_data import DashboardData
from .price import Price
from .price_drop_occurred import PriceDropOccurred
from .product_url import ProductUrl
from .tracked_product import TrackedProduct
from .types import TrackedProductId

__all__ = [
    "DashboardData",
    "Price",
    "PriceDropOccurred",
    "ProductUrl",
    "TrackedProduct",
    "TrackedProductId",
]
```

---

## File 3 — UPDATE `ports/tracked_product_repository.py`

Add `count_by_user` and `exists_by_user_and_url` between `list_by_user_id` and `save`.
Note: `url` parameter is `str` (the validated string value), not `ProductUrl` — keeps port clean of value-object dependency.

**Result:**
```python
from __future__ import annotations

from typing import Protocol, runtime_checkable

from webapp.domains.identity.models.domain import UserId
from webapp.domains.tracker.models.domain import TrackedProduct, TrackedProductId


@runtime_checkable
class TrackedProductRepository(Protocol):
    async def get_by_id(self, product_id: TrackedProductId) -> TrackedProduct | None: ...
    async def list_by_user_id(self, user_id: UserId) -> list[TrackedProduct]: ...
    async def count_by_user(self, user_id: UserId) -> int: ...
    async def exists_by_user_and_url(self, user_id: UserId, url: str) -> bool: ...
    async def save(self, product: TrackedProduct) -> None: ...
    async def delete(self, product_id: TrackedProductId) -> None: ...
```

---

## File 4 — UPDATE `ports/notification_read_repository.py`

Add `count_unread_by_user` to the end of the Protocol. No import changes needed.

**Result:**
```python
from __future__ import annotations

from datetime import datetime
from typing import Protocol, runtime_checkable

from webapp.domains.identity.models.domain import UserId
from webapp.domains.notifier.models.domain import Notification, NotificationId


@runtime_checkable
class NotificationReadRepository(Protocol):
    async def list_by_user_id(self, user_id: UserId, limit: int, offset: int) -> list[Notification]: ...
    async def get_by_id(self, notification_id: NotificationId) -> Notification | None: ...
    async def mark_read(self, notification_id: NotificationId, read_at: datetime) -> None: ...
    async def count_unread_by_user(self, user_id: UserId) -> int: ...
```

---

## File 5 — CREATE `adapters/sqlalchemy_tracked_product_repository.py`

Mirrors `domains/identity/adapters/sqlalchemy_user_repository.py` exactly in structure:
- `@dataclass` holding `_session: AsyncSession`
- Module-level `_to_domain()` / `_to_record()` translation functions
- `insert().on_conflict_do_update()` for upsert (PostgreSQL dialect)
- `flush()` after every mutation (no `commit` — outer layer manages transactions)

**Key subtlety — `_to_domain` constructs `ProductUrl` directly:**
```python
url=ProductUrl(value=record.url)  # NOT ProductUrl.parse() — SSRF check is ingress-only
```
SSRF validation is an ingress concern. Bypassing `parse()` on reads prevents a policy change from breaking reads of stored records.

**Upsert excludes `url`, `user_id`, `created_at` from `set_`** — these are immutable once a product is created.

```python
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
```

---

## File 6 — CREATE `flows/add_tracked_product.py`

Algorithm: SSRF validate → limit check → duplicate check → scrape → construct → save → return.

`_PRODUCT_LIMIT = 5` as a module-level constant (not constructor-injected — spec says 5 is fixed).

`ScrapingFailedError` raised `from None` — `ScraperFailure` is a data object, not an exception, so there is no exception chain to preserve.

```python
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from webapp.domains.identity.models.domain.types import UserId
from webapp.domains.scraper_client.models.domain.scraper_result import ScraperFailure
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

        result = await self.scraper.scrape(url.value)
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
```

---

## File 7 — CREATE `flows/remove_tracked_product.py`

Both "not found" and "wrong owner" branches raise the **same** `ProductNotFoundError` with the same message — intentional no-enumeration design.

```python
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
```

---

## File 8 — CREATE `flows/get_dashboard.py`

`asyncio.gather` parallelises the two independent queries. `tuple(products)` converts the list returned by the repository to satisfy `DashboardData.products: tuple[TrackedProduct, ...]`.

```python
from __future__ import annotations

import asyncio
from dataclasses import dataclass

from webapp.domains.identity.models.domain.types import UserId
from webapp.domains.tracker.models.domain.dashboard_data import DashboardData
from webapp.domains.tracker.ports.notification_read_repository import NotificationReadRepository
from webapp.domains.tracker.ports.tracked_product_repository import TrackedProductRepository


@dataclass
class GetDashboard:
    product_repo: TrackedProductRepository
    notification_read_repo: NotificationReadRepository

    async def execute(self, user_id: UserId) -> DashboardData:
        products, unread_count = await asyncio.gather(
            self.product_repo.list_by_user_id(user_id),
            self.notification_read_repo.count_unread_by_user(user_id),
        )
        return DashboardData(
            products=tuple(products),
            unread_notification_count=unread_count,
        )
```

---

## Verification

```bash
cd services/webapp

# SSRF blocked
uv run python -c "
import asyncio
from unittest.mock import AsyncMock
from webapp.domains.tracker.flows.add_tracked_product import AddTrackedProduct
from webapp.domains.tracker.exceptions import InvalidProductUrlError

flow = AddTrackedProduct(product_repo=AsyncMock(), scraper=AsyncMock())
try:
    asyncio.run(flow.execute(user_id='00000000-0000-0000-0000-000000000001', raw_url='http://192.168.1.1'))
    print('FAIL')
except InvalidProductUrlError:
    print('PASS: SSRF blocked')
"

# 5-product limit enforced
uv run python -c "
import asyncio, uuid
from unittest.mock import AsyncMock
from webapp.domains.tracker.flows.add_tracked_product import AddTrackedProduct
from webapp.domains.tracker.exceptions import ProductLimitExceededError

mock_repo = AsyncMock()
mock_repo.count_by_user.return_value = 5
flow = AddTrackedProduct(product_repo=mock_repo, scraper=AsyncMock())
try:
    asyncio.run(flow.execute(user_id=uuid.uuid4(), raw_url='https://example.com/product'))
    print('FAIL')
except ProductLimitExceededError:
    print('PASS: limit enforced')
"

# GetDashboard empty state
uv run python -c "
import asyncio, uuid
from unittest.mock import AsyncMock
from webapp.domains.tracker.flows.get_dashboard import GetDashboard

mock_product_repo = AsyncMock()
mock_product_repo.list_by_user_id.return_value = []
mock_notif_repo = AsyncMock()
mock_notif_repo.count_unread_by_user.return_value = 0
flow = GetDashboard(product_repo=mock_product_repo, notification_read_repo=mock_notif_repo)
result = asyncio.run(flow.execute(user_id=uuid.uuid4()))
assert result.products == ()
assert result.unread_notification_count == 0
print('PASS: empty dashboard')
"
```
