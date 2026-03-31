# Plan: Task 2 — Domain Models, Value Objects & Errors

## Context

This implements all pure domain code across five bounded contexts as the foundational layer that every subsequent task (ports, repositories, flows, APIs) depends on. The project scaffolding (Task 1) is complete: all `models/domain/` directories and `exceptions.py` stub files exist, but are empty. This task fills them with the domain types defined in LLD §1.2–§1.9.

**Complexity:** Medium
**Design Depth:** Standard

---

## Design Target

| Service | Domain | Status | Layers Affected |
|---------|--------|--------|-----------------|
| `services/webapp` | `identity` | existing | `models/domain/`, `exceptions.py` |
| `services/webapp` | `tracker` | existing | `models/domain/`, `exceptions.py` |
| `services/webapp` | `notifier` | existing | `models/domain/`, `exceptions.py` (new) |
| `services/webapp` | `scraper_client` | existing | `models/domain/` |
| `services/monitor_lambda` | `monitor` | existing | `models/domain/`, `exceptions.py` |
| `services/scraper_lambda` | `scraper` | existing | `models/domain/`, `exceptions.py` |

---

## Architecture Notes

- **No Pydantic in domain layer** — plain `@dataclass` and `@dataclass(frozen=True)` only
- **`Decimal` for all prices** — never `float`
- **`uuid.UUID` for all IDs** — typed via `NewType`
- **`passlib[bcrypt]`** already declared in `services/webapp/pyproject.toml` — use for `HashedPassword`
- **Cross-service type mirroring** — `ScraperResult`, `TrackedProductId` must be defined independently in each service (no shared lib at MVP)
- **Cross-context imports within webapp** — `UserId` lives in `identity`; Tracker and Notifier import it from there
- **`object.__setattr__`** not needed on `TrackedProduct` — it is a regular (mutable) `@dataclass`, not frozen; use direct `self.x = y` assignment instead

---

## Files to Create

### Identity Context (`services/webapp/webapp/domains/identity/models/domain/`)

| File | Contents |
|------|----------|
| `types.py` | `UserId = NewType("UserId", uuid.UUID)`, `PasswordResetTokenId = NewType(...)` |
| `user.py` | `User` entity dataclass with `__post_init__` invariant (no auth method → `ValueError`) |
| `password_reset_token.py` | `PasswordResetToken` entity with `is_valid()` method |
| `hashed_password.py` | `HashedPassword` frozen dataclass; `create(raw, cost=14)` uses `passlib.hash.bcrypt`; `verify(raw)` |

### Identity Exceptions (`services/webapp/webapp/domains/identity/exceptions.py`)

Fill stub with `IdentityError` hierarchy: `EmailAlreadyRegisteredError`, `InvalidCredentialsError`, `WeakPasswordError`, `PasswordChangeNotAllowedError`, `InvalidResetTokenError`, `InvalidOIDCStateError`, `OIDCExchangeError`, `OIDCTokenVerificationError` (9 classes total including base).

---

### Tracker Context (`services/webapp/webapp/domains/tracker/models/domain/`)

| File | Contents |
|------|----------|
| `types.py` | `TrackedProductId = NewType("TrackedProductId", uuid.UUID)` |
| `product_url.py` | `ProductUrl` frozen dataclass; `parse(raw)` validates HTTP/HTTPS, rejects RFC-1918 ranges + localhost → `InvalidProductUrlError` |
| `price.py` | `Price` frozen dataclass with `Decimal` value; `__post_init__` rejects negative; `__lt__` for comparison |
| `price_drop_occurred.py` | `PriceDropOccurred` frozen dataclass (domain event) |
| `tracked_product.py` | `TrackedProduct` mutable entity; `record_price_check(new_price, checked_at)` pure method; returns `PriceDropOccurred | None`; updates `current_price`, `previous_price`, `last_checked_at` via direct attribute assignment |

**RFC-1918 ranges to reject in `ProductUrl.parse`:** `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `127.0.0.0/8`, `::1`, `localhost` hostname.
**Implementation:** Use `ipaddress` stdlib to check parsed host; also reject `"localhost"` as a hostname literal.

### Tracker Exceptions (`services/webapp/webapp/domains/tracker/exceptions.py`)

Fill stub with `TrackerError` hierarchy: `InvalidProductUrlError`, `ProductLimitExceededError`, `DuplicateProductError`, `ScrapingFailedError`, `ProductNotFoundError` (6 classes total).

---

### Notifier Context (`services/webapp/webapp/domains/notifier/models/domain/`)

| File | Contents |
|------|----------|
| `types.py` | `NotificationId = NewType("NotificationId", uuid.UUID)` |
| `notification.py` | `Notification` mutable entity; fields include `UserId`, `TrackedProductId`, `Price` snapshots; `read_at: datetime | None` |

### Notifier Exceptions (`services/webapp/webapp/domains/notifier/exceptions.py`)

**New file** (does not exist yet): `NotifierError` base + `NotificationNotFoundError`.

---

### Scraper Client Context (`services/webapp/webapp/domains/scraper_client/models/domain/`)

| File | Contents |
|------|----------|
| `scraper_result.py` | `ScraperErrorType` enum, `ScraperSuccess` + `ScraperFailure` frozen dataclasses, `ScraperResult = ScraperSuccess \| ScraperFailure` type alias |

---

### Monitor Lambda (`services/monitor_lambda/monitor_lambda/domains/monitor/models/domain/`)

| File | Contents |
|------|----------|
| `types.py` | `TrackedProductId = NewType("TrackedProductId", uuid.UUID)` — local copy, no shared lib |
| `scraper_result.py` | Mirror of `ScraperErrorType`, `ScraperSuccess`, `ScraperFailure`, `ScraperResult` |
| `price_check_result.py` | `PriceCheckResult` frozen dataclass with `outcome: Literal["success", "failure"]`; `success()` and `failure()` class methods |
| `price_check_log.py` | `PriceCheckLog` regular dataclass (append-only entity); `id: uuid.UUID`, `retry_count: int` (0–10) |

### Monitor Exceptions (`services/monitor_lambda/monitor_lambda/domains/monitor/exceptions.py`)

Fill stub with `MonitorError` hierarchy: `PriceCheckCycleError`, `ProductCheckError`, `EmailDeliveryError` (4 classes total).

---

### Scraper Lambda (`services/scraper_lambda/scraper_lambda/domains/scraper/models/domain/`)

| File | Contents |
|------|----------|
| `scraper_result.py` | Canonical definition of `ScraperErrorType`, `ScraperSuccess`, `ScraperFailure`, `ScraperResult` |

### Scraper Exceptions (`services/scraper_lambda/scraper_lambda/domains/scraper/exceptions.py`)

Fill stub with `ScraperInternalError(Exception)`.

---

## Cross-Context Import Pattern (within webapp)

```
identity.models.domain.types   ──► imported by tracker (UserId in TrackedProduct, PriceDropOccurred)
                                ──► imported by notifier (UserId in Notification)
tracker.models.domain.types    ──► imported by notifier (TrackedProductId in Notification)
tracker.models.domain.price    ──► imported by tracker (TrackedProduct, PriceDropOccurred)
tracker.models.domain.product_url ──► imported by tracker (TrackedProduct, PriceDropOccurred)
```

---

## Key Implementation Details

### `HashedPassword.create` / `verify`
```python
from passlib.hash import bcrypt as _bcrypt  # passlib[bcrypt] already in deps

@classmethod
def create(cls, raw: str, cost: int = 14) -> "HashedPassword":
    return cls(value=_bcrypt.using(rounds=cost).hash(raw))

def verify(self, raw: str) -> bool:
    return _bcrypt.verify(raw, self.value)
```

### `ProductUrl.parse` — SSRF prevention
```python
import ipaddress, urllib.parse

def parse(cls, raw: str) -> "ProductUrl":
    parsed = urllib.parse.urlparse(raw)
    if parsed.scheme not in ("http", "https"):
        raise InvalidProductUrlError(...)
    host = parsed.hostname or ""
    if host in ("localhost", ""):
        raise InvalidProductUrlError(...)
    try:
        addr = ipaddress.ip_address(host)
        if addr.is_private or addr.is_loopback or addr.is_link_local:
            raise InvalidProductUrlError(...)
    except ValueError:
        pass  # hostname, not IP — only "localhost" rejected above
    return cls(value=raw)
```

### `TrackedProduct.record_price_check` — mutable entity, direct assignment
```python
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
```

---

## `__init__.py` Exports

Update each `models/domain/__init__.py` to re-export all public types so consumers can import from the package rather than individual modules:

```python
# e.g. identity/models/domain/__init__.py
from .types import UserId, PasswordResetTokenId
from .user import User
from .password_reset_token import PasswordResetToken
from .hashed_password import HashedPassword

__all__ = ["UserId", "PasswordResetTokenId", "User", "PasswordResetToken", "HashedPassword"]
```

---

## Verification

Run after implementation from each service root using `uv run python`:

```bash
# From services/webapp/
uv run python -c "
from webapp.domains.identity.models.domain.user import User
import uuid; from datetime import datetime, timezone
now = datetime.now(tz=timezone.utc)
try:
    User(id=uuid.uuid4(), email='a@b.com', password_hash=None, google_sub=None, created_at=now, updated_at=now)
    print('FAIL')
except ValueError:
    print('PASS: User invariant enforced')
"

uv run python -c "
from webapp.domains.tracker.models.domain.tracked_product import TrackedProduct
from webapp.domains.tracker.models.domain.product_url import ProductUrl
from webapp.domains.tracker.models.domain.price import Price
import uuid; from decimal import Decimal; from datetime import datetime, timezone
p = TrackedProduct(id=uuid.uuid4(), user_id=uuid.uuid4(), url=ProductUrl('https://example.com/p'), product_name='Widget', current_price=Price(Decimal('100.00')), previous_price=None, last_checked_at=None, created_at=datetime.now(tz=timezone.utc))
e = p.record_price_check(Price(Decimal('89.99')), datetime.now(tz=timezone.utc))
print(type(e).__name__)  # PriceDropOccurred
print(p.record_price_check(Price(Decimal('89.99')), datetime.now(tz=timezone.utc)))  # None
"

uv run python -c "
from webapp.domains.tracker.models.domain.product_url import ProductUrl
from webapp.domains.tracker.exceptions import InvalidProductUrlError
for url in ('http://192.168.1.1/p', 'http://localhost/p', 'ftp://example.com'):
    try:
        ProductUrl.parse(url)
        print(f'FAIL: {url}')
    except InvalidProductUrlError:
        print(f'PASS: rejected {url}')
"
```

---

## Sub-Task Order

Execute sequentially (each builds on the previous):

1. **2.1** Identity ID types (`types.py`)
2. **2.3** Identity exceptions (needed by `HashedPassword`)
3. **2.2** Identity entities + `HashedPassword`
4. **2.4** Tracker ID types + value objects (`types.py`, `price.py`, `product_url.py`)
5. **2.6** Tracker exceptions + `PriceDropOccurred` event
6. **2.5** Tracker `TrackedProduct` aggregate (needs Price, ProductUrl, PriceDropOccurred)
7. **2.7** Notifier entity + exceptions (needs UserId, TrackedProductId, Price)
8. **2.9** Scraper domain in `scraper_lambda` + mirrors in `scraper_client` and `monitor_lambda`
9. **2.8** Monitor `PriceCheckResult` + `PriceCheckLog` (needs TrackedProductId mirror)
10. **2.10** Monitor + Scraper exceptions
