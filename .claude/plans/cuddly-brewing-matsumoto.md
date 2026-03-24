# Plan: Task 3 — Port Protocols

## Context

Implements all `typing.Protocol` interfaces (ports) for the webapp and monitor_lambda services as part of the price-drop tracker hexagonal architecture. These contracts decouple domain flows from infrastructure adapters and are pure type definitions — no runtime logic, no state. Depends on T-2 (domain models), which is already complete.

---

## Design Decisions

### ScraperPort Location (spec discrepancy)
Sub-task 3.2 says `scraper_port.py` lives in `tracker/ports/`, but the task spec's own boundary condition note says: *"ScraperPort.scrape() signature is identical in both `webapp/domains/scraper_client/ports/` and `monitor_lambda/domains/monitor/ports/`"*. The comment in the spec also reads `# scraper_port.py (canonical in scraper_client)`.

**Decision:** Place `ScraperPort` in `scraper_client/ports/scraper_port.py`. This is the correct bounded context. The verification commands in the spec reference `tracker.ports.scraper_port` — those are wrong and should reference `scraper_client.ports`.

### New monitor domain models required
`NotificationWriteRepository` (monitor) takes a `Notification` argument, and `TrackedProductRepository` (monitor) returns `TrackedProductSummary` — neither exists in the monitor domain yet.

**Decision:** Create both as frozen/mutable dataclasses in monitor's `models/domain/` using only monitor-local types (`uuid.UUID`, `Decimal`, `str`, `TrackedProductId`). No webapp imports.

---

## Files to Create/Update (22 total)

### New monitor domain models (prerequisite)
| File | Action |
|------|--------|
| `services/monitor_lambda/monitor_lambda/domains/monitor/models/domain/tracked_product_summary.py` | New — frozen dataclass: id, user_id (uuid.UUID), user_email, url, product_name, current_price (Decimal) |
| `services/monitor_lambda/monitor_lambda/domains/monitor/models/domain/notification.py` | New — mutable dataclass: id (uuid.UUID), user_id (uuid.UUID), tracked_product_id (TrackedProductId), product_name, product_url (str), old_price (Decimal), new_price (Decimal), created_at, read_at |
| `services/monitor_lambda/monitor_lambda/domains/monitor/models/domain/__init__.py` | Update — add exports for TrackedProductSummary and Notification |

### webapp identity ports (`services/webapp/webapp/domains/identity/ports/`)
| File | Key Imports |
|------|-------------|
| `user_repository.py` | `User, UserId` from `webapp.domains.identity.models.domain` |
| `token_repository.py` | `PasswordResetToken, UserId` from `webapp.domains.identity.models.domain` |
| `token_store.py` | builtins only (str, int) |
| `email_sender.py` | builtins only (str) |
| `oidc_client.py` | builtins only (str, dict) |
| `__init__.py` | Update — export all 5 protocols |

### webapp tracker ports (`services/webapp/webapp/domains/tracker/ports/`)
| File | Key Imports |
|------|-------------|
| `tracked_product_repository.py` | `TrackedProduct, TrackedProductId` from tracker domain; `UserId` from identity domain |
| `notification_read_repository.py` | `Notification, NotificationId` from notifier domain; `UserId` from identity domain; `datetime` |
| `__init__.py` | Update — export TrackedProductRepository, NotificationReadRepository |

### webapp scraper_client port (`services/webapp/webapp/domains/scraper_client/ports/`)
| File | Key Imports |
|------|-------------|
| `scraper_port.py` | `ScraperResult` from `webapp.domains.scraper_client.models.domain` |
| `__init__.py` | Update — export ScraperPort |

### webapp notifier port (`services/webapp/webapp/domains/notifier/ports/`)
| File | Key Imports |
|------|-------------|
| `notification_write_repository.py` | `Notification` from `webapp.domains.notifier.models.domain` |
| `__init__.py` | Update — export NotificationWriteRepository |

### monitor_lambda ports (`services/monitor_lambda/monitor_lambda/domains/monitor/ports/`)
| File | Key Imports |
|------|-------------|
| `tracked_product_repository.py` | `TrackedProductId, TrackedProductSummary` from monitor domain; `Decimal`, `datetime` |
| `price_check_log_repository.py` | `PriceCheckLog` from monitor domain |
| `notification_write_repository.py` | `Notification` from monitor domain (local, not webapp) |
| `scraper_port.py` | `ScraperResult` from monitor domain |
| `email_sender.py` | `Decimal` only |
| `__init__.py` | Update — export all 5 protocols |

---

## Protocol Template

Every port file follows this pattern:

```python
from __future__ import annotations

from typing import Protocol, runtime_checkable

# domain-local imports only

@runtime_checkable
class PortName(Protocol):
    async def method(self, param: Type) -> ReturnType: ...
```

Rules:
- `@runtime_checkable` on every Protocol class
- Method bodies use `...` (not `pass`, not `raise NotImplementedError`)
- `async def` for all I/O-touching methods
- `from __future__ import annotations` on every file

---

## Verification

```bash
# webapp
cd services/webapp
uv run python -c "
from webapp.domains.identity.ports import UserRepository, TokenRepository, TokenStore, EmailSender, OIDCClient
from webapp.domains.tracker.ports import TrackedProductRepository, NotificationReadRepository
from webapp.domains.scraper_client.ports import ScraperPort
from webapp.domains.notifier.ports import NotificationWriteRepository
print('webapp ports: ok')
"

# monitor_lambda
cd services/monitor_lambda
uv run python -c "
from monitor_lambda.domains.monitor.ports import TrackedProductRepository, PriceCheckLogRepository, NotificationWriteRepository, ScraperPort, EmailSender
print('monitor ports: ok')
"

# type check
cd services/webapp && uv run ty check webapp/domains/
cd services/monitor_lambda && uv run ty check monitor_lambda/domains/
```
