# Plan: Task 11 — Monitor Lambda Implementation

## Context

Task 11 implements the `PriceCheckCycleFlow` and supporting infrastructure for the Monitor Lambda. The Lambda is triggered by EventBridge and checks all tracked products' prices via the Scraper Lambda, creates notifications + sends SES emails on drops, and logs every outcome. The scaffold (domain models, ports, persistence records, exceptions, existing adapters) was built in T-2/T-3/T-10; this task wires it together and fills the gaps.

---

## Design Target

| Service | Domain | Status | Layers Affected |
|---------|--------|--------|-----------------|
| monitor_lambda | monitor | existing | ports, adapters (×4), flows (new), jobs/handler, infrastructure/settings |

---

## Key Discrepancies: Spec vs. Existing Code

Several adaptations are required because the task spec pseudocode was written before the domain models were finalized:

| Spec assumption | Actual state | Resolution |
|---|---|---|
| `list_all_active()` on port | Port has `list_all()` | Update port — rename |
| `update_prices()` + `update_last_checked_at()` on port | Port has single `update_price()` | Update port — replace with two methods |
| `result.retry_count` on `ScraperFailure` | `ScraperFailure` has no such field | Add `retry_count: int = 0` to `ScraperFailure`; update `ScraperLambdaClient` to populate it |
| `Price(...)` value object for comparison | No `Price` class in monitor_lambda | Compare `Decimal` directly |
| `PriceCheckLog(result="success")` (string) | Uses `PriceCheckResult` object | Use `PriceCheckResult.success()` / `.failure(msg)` factory methods |
| `email_sender.send_price_drop(to=...)` | Port defines `send_price_drop_alert(to_email=...)` | Implement adapter and call flow using port's actual method name |
| `Notification(id, user_id, tracked_product_id, old_price, new_price, ...)` | Model also has `product_name: str`, `product_url: str` | Supply from `TrackedProductSummary` |
| Verification imports from `scraper_lambda` package | No scraper_lambda dependency; local copy used | Verification scripts must import from `monitor_lambda.domains.monitor.models.domain` |

---

## Implementation Steps

### Step 1 — Update `ScraperFailure` + `ScraperLambdaClient`

**File:** `monitor_lambda/domains/monitor/models/domain/scraper_result.py`

Add `retry_count: int = 0` as the last field of `ScraperFailure`. Default `0` preserves backward compatibility with existing 3-arg construction.

**File:** `monitor_lambda/domains/monitor/adapters/scraper_lambda_client.py`

In the `scrape()` method, when returning the exhausted `last_result` after all retries, pass `retry_count=attempt`. When returning non-retryable errors immediately, leave default `retry_count=0`.

```python
# After while loop:
return ScraperFailure(
    error_type=last_result.error_type,
    message=last_result.message,
    status_code=last_result.status_code,
    retry_count=attempt,  # actual attempts made (1–3)
)
```

---

### Step 2 — Update `TrackedProductRepository` Port

**File:** `monitor_lambda/domains/monitor/ports/tracked_product_repository.py`

Replace existing two methods with three:

```python
@runtime_checkable
class TrackedProductRepository(Protocol):
    async def list_all_active(self) -> list[TrackedProductSummary]: ...
    async def update_prices(
        self,
        product_id: TrackedProductId,
        new_price: Decimal,
        previous_price: Decimal,
        last_checked_at: datetime,
    ) -> None: ...
    async def update_last_checked_at(
        self,
        product_id: TrackedProductId,
        last_checked_at: datetime,
    ) -> None: ...
```

---

### Step 3 — Create `SQLAlchemyTrackedProductRepository`

**File:** `monitor_lambda/domains/monitor/adapters/sqlalchemy_tracked_product_repository.py`

Dataclass with `_session: AsyncSession`. Uses `sqlalchemy.text()` for all queries (tracked_products is owned by webapp; no ORM model in monitor_lambda).

```python
# list_all_active — JOIN tracked_products + users
SELECT tp.id, tp.user_id, u.email, tp.url, tp.product_name, tp.current_price
FROM tracked_products tp
JOIN users u ON u.id = tp.user_id
ORDER BY tp.id

# update_prices
UPDATE tracked_products
SET current_price = :new_price,
    previous_price = :previous_price,
    last_checked_at = :last_checked_at
WHERE id = :product_id

# update_last_checked_at
UPDATE tracked_products
SET last_checked_at = :last_checked_at
WHERE id = :product_id
```

Row-to-domain conversion: map `Row` columns to `TrackedProductSummary` fields. Cast id to `TrackedProductId`.

---

### Step 4 — Create `SQLAlchemyPriceCheckLogRepository`

**File:** `monitor_lambda/domains/monitor/adapters/sqlalchemy_price_check_log_repository.py`

Dataclass with `_session: AsyncSession`. Implements `PriceCheckLogRepository` port.

Map `PriceCheckLog` to `PriceCheckLogRecord`:
- `result` → `log.result.outcome` (the string `"success"` or `"failure"`)
- `error_message` → `log.result.message if log.result.outcome == "failure" else None`
- `retry_count` → `log.retry_count`

Use `insert(PriceCheckLogRecord).values(...)` and `await session.flush()`.

---

### Step 5 — Create `SESEmailSender`

**File:** `monitor_lambda/domains/monitor/adapters/ses_email_sender.py`

Implements `EmailSender` port (`send_price_drop_alert`).

```python
@dataclass
class SESEmailSender:
    _from_address: str
    _client: Any = field(default_factory=lambda: boto3.client("ses"))

    async def send_price_drop_alert(
        self, to_email: str, product_name: str, product_url: str,
        old_price: Decimal, new_price: Decimal,
    ) -> None:
        # Run boto3 send_email in thread (sync → async)
        # HTML body: product_name, old_price → new_price, product_url link
        # On ClientError → raise EmailDeliveryError
```

Use `asyncio.to_thread(self._client.send_email, ...)` for non-blocking invocation.

---

### Step 6 — Create `PriceCheckCycleFlow`

**File:** `monitor_lambda/domains/monitor/flows/price_check_cycle_flow.py`

Dataclass with 5 injected dependencies (all Protocols): `product_repo`, `price_check_log_repo`, `notification_repo`, `scraper`, `email_sender`.

Key behaviours:
- `run()`: load all products → create tasks → `asyncio.gather(*tasks, return_exceptions=True)` → log cycle end with success/failure counts → log error if >5% failure rate
- `_check_product(semaphore, product)`: wraps `_check_one` in semaphore + try/except; logs + raises `ProductCheckError` on exception (never propagates raw)
- `_check_one(product)`:
  1. Call `scraper.scrape(product.url)`
  2. If `ScraperFailure`: write failure log (`PriceCheckResult.failure(...)`, `retry_count=result.retry_count`), log warning with `url_hash`, return (no timestamp update)
  3. If `ScraperSuccess`: compare `result.price < product.current_price`
     - Drop: `update_prices()`, create + save `Notification`, try `send_price_drop_alert()` (catch `EmailDeliveryError` → log only)
     - No drop: `update_last_checked_at()`
  4. Write success log (`PriceCheckResult.success()`, `retry_count=0`)

Logging rules:
- `url_hash = hashlib.sha256(product.url.encode()).hexdigest()[:16]` — never log raw URL
- `user_id = str(product.user_id)` — never log raw email
- structlog: `log.info(...)`, `log.warning(...)`, `log.error(...)`

---

### Step 7 — Create `Settings`

**File:** `monitor_lambda/infrastructure/settings.py`

Simple dataclass using `os.environ`:

```python
@dataclass(frozen=True)
class Settings:
    database_url: str = field(default_factory=lambda: os.environ["DATABASE_URL"])
    scraper_lambda_name: str = field(default_factory=lambda: os.environ["SCRAPER_LAMBDA_NAME"])
    ses_from_address: str = field(default_factory=lambda: os.environ["SES_FROM_ADDRESS"])
```

---

### Step 8 — Implement Lambda Handler

**File:** `monitor_lambda/domains/monitor/jobs/handler.py`

Replace stub:

```python
def handler(event: dict[str, Any], context: object) -> dict[str, str]:
    asyncio.run(_async_handler())
    return {"status": "ok"}

async def _async_handler() -> None:
    settings = Settings()
    engine = create_async_engine(settings.database_url)
    async with AsyncSession(engine) as session:
        flow = PriceCheckCycleFlow(
            product_repo=SQLAlchemyTrackedProductRepository(session),
            price_check_log_repo=SQLAlchemyPriceCheckLogRepository(session),
            notification_repo=SQLAlchemyNotificationWriteRepository(session),
            scraper=ScraperLambdaClient(lambda_name=settings.scraper_lambda_name),
            email_sender=SESEmailSender(from_address=settings.ses_from_address),
        )
        await flow.run()
```

---

## Files Modified / Created

| Action | File |
|--------|------|
| Modify | `monitor_lambda/domains/monitor/models/domain/scraper_result.py` |
| Modify | `monitor_lambda/domains/monitor/adapters/scraper_lambda_client.py` |
| Modify | `monitor_lambda/domains/monitor/ports/tracked_product_repository.py` |
| Create | `monitor_lambda/domains/monitor/adapters/sqlalchemy_tracked_product_repository.py` |
| Create | `monitor_lambda/domains/monitor/adapters/sqlalchemy_price_check_log_repository.py` |
| Create | `monitor_lambda/domains/monitor/adapters/ses_email_sender.py` |
| Create | `monitor_lambda/domains/monitor/flows/price_check_cycle_flow.py` |
| Create | `monitor_lambda/infrastructure/settings.py` |
| Modify | `monitor_lambda/domains/monitor/jobs/handler.py` |

All paths relative to `services/monitor_lambda/`.

---

## Verification

```bash
cd services/monitor_lambda

# Test 1: price drop → notification + email + log written
uv run python -c "
import asyncio, uuid
from decimal import Decimal
from unittest.mock import AsyncMock
from monitor_lambda.domains.monitor.flows.price_check_cycle_flow import PriceCheckCycleFlow
from monitor_lambda.domains.monitor.models.domain.tracked_product_summary import TrackedProductSummary
from monitor_lambda.domains.monitor.models.domain.scraper_result import ScraperSuccess

product = TrackedProductSummary(
    id=uuid.uuid4(), user_id=uuid.uuid4(), user_email='user@example.com',
    url='https://example.com/product', product_name='Widget', current_price=Decimal('100.00')
)
mock_product_repo = AsyncMock()
mock_product_repo.list_all_active.return_value = [product]
mock_log_repo = AsyncMock()
mock_notification_repo = AsyncMock()
mock_scraper = AsyncMock()
mock_scraper.scrape.return_value = ScraperSuccess(price=Decimal('89.99'), product_name='Widget')
mock_email = AsyncMock()
flow = PriceCheckCycleFlow(
    product_repo=mock_product_repo, price_check_log_repo=mock_log_repo,
    notification_repo=mock_notification_repo, scraper=mock_scraper, email_sender=mock_email,
)
asyncio.run(flow.run())
mock_product_repo.update_prices.assert_called_once()
mock_notification_repo.save.assert_called_once()
mock_email.send_price_drop_alert.assert_called_once()
mock_log_repo.save.assert_called_once()
print('PASS: price drop detected, notification created, email sent, log written')
"

# Test 2: one product failure doesn't block others
uv run python -c "
import asyncio, uuid
from decimal import Decimal
from unittest.mock import AsyncMock
from monitor_lambda.domains.monitor.flows.price_check_cycle_flow import PriceCheckCycleFlow
from monitor_lambda.domains.monitor.models.domain.tracked_product_summary import TrackedProductSummary
from monitor_lambda.domains.monitor.models.domain.scraper_result import ScraperSuccess, ScraperFailure, ScraperErrorType

products = [
    TrackedProductSummary(id=uuid.uuid4(), user_id=uuid.uuid4(), user_email='a@x.com',
        url='https://example.com/fail', product_name='Bad', current_price=Decimal('50')),
    TrackedProductSummary(id=uuid.uuid4(), user_id=uuid.uuid4(), user_email='b@x.com',
        url='https://example.com/ok', product_name='Good', current_price=Decimal('100')),
]
mock_product_repo = AsyncMock()
mock_product_repo.list_all_active.return_value = products
async def mock_scrape(url):
    if 'fail' in url:
        return ScraperFailure(ScraperErrorType.PARSE_ERROR, 'no price', None)
    return ScraperSuccess(price=Decimal('89.99'), product_name='Good')
mock_scraper = AsyncMock()
mock_scraper.scrape.side_effect = mock_scrape
flow = PriceCheckCycleFlow(
    product_repo=mock_product_repo, price_check_log_repo=AsyncMock(),
    notification_repo=AsyncMock(), scraper=mock_scraper, email_sender=AsyncMock(),
)
asyncio.run(flow.run())
print('PASS: cycle completed despite one product failure')
print('Price drop processed:', mock_product_repo.update_prices.call_count == 1)
"
```

Note: verification scripts import from `monitor_lambda.domains.monitor.models.domain.scraper_result` (local mirror), not `scraper_lambda` package (not a dependency).
