# Reusability Reference

> *"Write it once, own it in one place, consume it everywhere."*

Reusability ensures consistent behavior across services and domains while eliminating code duplication. In this monorepo, reusable code lives at two levels: **shared libraries** (`libs/lib-<name>`) for cross-service concerns, and **shared modules** within a service for cross-domain concerns.

---

## Core Concept

Duplication is not just wasted effort — it creates behavioral drift. When the same logic exists in multiple places, each copy evolves independently: bugs get fixed in one but not others, edge cases get handled inconsistently, and consumers experience different behavior from what should be the same operation.

Reusability is about **consistency first**, efficiency second. The goal is a single source of truth for each piece of shared behavior.

---

## Placement Decision Tree

```
Is this functionality needed by 2+ services?
    │
    ├─► YES → Does a suitable `libs/lib-<name>` already exist?
    │           ├─► YES → Add to existing library
    │           └─► NO  → Create new `libs/lib-<name>`
    │
    └─► NO → Is it needed by 2+ domains within this service?
                │
                ├─► YES → Extract to shared module within the service
                │         (e.g., `services/<name>/<name>/shared/` or
                │          `services/<name>/<name>/common/`)
                │
                └─► NO → Keep it local to the domain
```

### When to Extract to `libs/`

Extract to a shared library when functionality is:
- **Cross-service** — used (or will be used) by 2+ services
- **Infrastructure-level** — HTTP clients, database pools, message brokers, observability
- **Cross-cutting concerns** — auth, validation, error handling, serialization patterns
- **Domain primitives** — shared types, enums, ID formats, audit fields
- **Behavioral contracts** — protocols/ABCs that define how services interact

### When to Extract to a Shared Module Within a Service

Extract to a service-level shared module when functionality is:
- **Cross-domain within one service** — used by 2+ domains but not relevant outside the service
- **Service-specific utilities** — formatters, validators, helpers tied to this service's context
- **Shared domain models** — value objects or types that span domains within the service

### When NOT to Extract

Keep code local when:
- Only one consumer exists today and no second is foreseeable
- The "shared" code would need per-consumer customization (use strategy pattern instead)
- Extraction would create coupling between unrelated domains
- The code is trivial (< 5 lines) and self-contained

---

## MUST

1. **Check `libs/` before implementing cross-cutting logic** — the library likely already exists
2. **Define a stable interface** (Protocol/ABC) for any shared code — consumers depend on abstractions
3. **Keep shared code generic** — no service-specific assumptions, no hardcoded domain terms from one consumer
4. **Version shared library changes** that affect public interfaces
5. **Co-locate tests with shared code** — shared libraries have their own test suites
6. **Document the public API** of shared modules — consumers need to know what's available
7. **Use dependency injection** — shared code provides implementations, consumers inject them

---

## NEVER

1. **Copy-paste code between services** — if you're copying, you should be extracting
2. **Put service-specific logic in `libs/`** — libraries serve all consumers equally
3. **Create circular dependencies** between `libs/` packages
4. **Depend on a shared library for a single utility function** — use inline if trivial
5. **Break existing consumers** when evolving shared code — additive changes, deprecation paths
6. **Create "util" or "helpers" grab-bags** — each shared module needs a clear, cohesive responsibility
7. **Duplicate types defined in `lib-schemas`** — import from the canonical source

---

## WHEN / THEN Patterns

**WHEN** implementing auth checks, token validation, or security middleware
**THEN** use `lib-security` — never roll your own per-service

**WHEN** adding structured logging, tracing, or metrics
**THEN** use `lib-observability` — consistent instrumentation across all services

**WHEN** defining API/event envelope types, pagination, error formats
**THEN** use `lib-schemas` — single source of truth for cross-boundary types

**WHEN** calling external services or unreliable dependencies
**THEN** use `lib-resilience` — consistent retry, circuit breaker, timeout behavior

**WHEN** building a new FastAPI or FastStream app
**THEN** use `lib-fastapi` / `lib-faststream` — pre-wired middleware, health probes, conventions

**WHEN** you notice 2+ services implementing the same pattern differently
**THEN** extract to `libs/`, migrate all consumers, delete the duplicates

**WHEN** two domains in the same service share a value object or utility
**THEN** extract to a `shared/` or `common/` sub-package within the service

**WHEN** a shared module grows to serve only one consumer's needs
**THEN** move it back to the consuming domain — premature extraction creates coupling

---

## Patterns

### Pattern 1: Cross-Service Shared Library

```python
# libs/lib-security/lib_security/guards.py — Shared auth guard
from typing import Protocol

class AuthorizationGuard(Protocol):
    async def check(self, subject: str, resource: str, action: str) -> bool: ...

class RBACGuard:
    """Role-based authorization guard used by all services."""

    def __init__(self, role_resolver: RoleResolver):
        self._roles = role_resolver

    async def check(self, subject: str, resource: str, action: str) -> bool:
        roles = await self._roles.get_roles(subject)
        return any(role.permits(resource, action) for role in roles)
```

```python
# services/notification/notification/domains/channels/flows/send.py — Consumer
from lib_security.guards import AuthorizationGuard

class SendNotificationFlow:
    def __init__(self, auth: AuthorizationGuard, ...):
        self._auth = auth  # Same guard, same behavior, every service
```

### Pattern 2: Service-Level Shared Module

```python
# services/order/order/shared/formatting.py — Shared within service
from decimal import Decimal

class MoneyFormatter:
    """Formats monetary values consistently across order domains."""

    @staticmethod
    def display(amount: Decimal, currency: str = "USD") -> str:
        return f"{currency} {amount:,.2f}"
```

```python
# services/order/order/domains/checkout/flows/confirm.py
from order.shared.formatting import MoneyFormatter

# services/order/order/domains/invoicing/flows/generate.py
from order.shared.formatting import MoneyFormatter
# Same formatting logic, guaranteed consistency
```

### Pattern 3: Extracting Duplicated Logic to libs/

```python
# BEFORE: Each service has its own pagination implementation
# services/order/order/domains/listing/routes/v1/list.py
class PaginatedResponse(BaseModel):
    items: list[Any]
    next_cursor: str | None
    # ... slightly different from notification's version

# services/notification/notification/domains/history/routes/v1/list.py
class PaginatedResponse(BaseModel):
    items: list[Any]
    cursor: str | None  # Different field name!
    # ... behavioral drift
```

```python
# AFTER: Single source of truth in lib-schemas
# libs/lib-schemas/lib_schemas/pagination.py
class CursorPage(BaseModel, Generic[T]):
    """Cursor-based pagination response used by all services."""
    items: list[T]
    next_cursor: str | None = None
    has_more: bool

# Both services import from the same place — consistent behavior guaranteed
from lib_schemas.pagination import CursorPage
```

### Pattern 4: Protocol-First Shared Interface

```python
# libs/lib-events/lib_events/publisher.py — Interface in shared lib
from typing import Protocol

class EventPublisher(Protocol):
    """All services use this protocol to publish domain events."""
    async def publish(self, event: EventEnvelope) -> None: ...

# libs/lib-events/lib_events/redis_publisher.py — One implementation
class RedisEventPublisher:
    async def publish(self, event: EventEnvelope) -> None:
        # Redis-specific logic, shared across all services
        ...

# Services depend on the Protocol, not the implementation
# Swapping Redis for SQS means changing one adapter, not every service
```

---

## Anti-Patterns

### Anti-Pattern 1: Copy-Paste Reuse

```python
# services/order/order/utils/auth.py
def verify_jwt(token: str) -> Claims:
    # 47 lines of JWT verification logic

# services/notification/notification/utils/auth.py
def verify_jwt(token: str) -> Claims:
    # Same 47 lines, copy-pasted, now with a bug fix the other doesn't have
```

**Fix:** Use `lib-security` — one implementation, one place to fix bugs.

### Anti-Pattern 2: The "Utils" Junk Drawer

```python
# libs/lib-utils/lib_utils/__init__.py
from .string_helpers import *      # 3 functions
from .date_helpers import *        # 2 functions
from .validation_helpers import *  # 1 function
from .crypto_helpers import *      # 1 function
# No cohesion — this is a grab-bag, not a library
```

**Fix:** Each shared library has a clear, single responsibility. String formatting might belong in the consuming domain. Crypto belongs in `lib-security`. Date handling might belong in `lib-schemas` as domain primitives.

### Anti-Pattern 3: Premature Extraction

```python
# libs/lib-order-helpers/  ← Only used by order service!
# Created "just in case" another service needs it
# Now order service has an external dependency on its own logic
```

**Fix:** Keep code in the consuming service until a second consumer actually appears. Extraction is cheap when you need it; premature extraction creates unnecessary coupling.

### Anti-Pattern 4: Leaking Service Context into Shared Code

```python
# libs/lib-notifications/lib_notifications/sender.py
class NotificationSender:
    async def send(self, user_id: str, message: str):
        # Hard-coded to notification service's database schema
        await self._db.execute(
            "INSERT INTO notifications (user_id, body) VALUES ($1, $2)",
            user_id, message,
        )
```

**Fix:** Shared libraries are infrastructure-agnostic. They define interfaces (Protocols) and provide generic implementations. Service-specific persistence stays in the service's adapter layer.

### Anti-Pattern 5: Inconsistent Shared Behavior

```python
# Service A: Uses lib-resilience with custom timeout
policy = http_call_policy(timeout=30)

# Service B: Skips lib-resilience entirely, uses raw httpx
response = await httpx.get(url)  # No retry, no circuit breaker, no timeout

# Service C: Rolls its own retry logic
for attempt in range(3):
    try:
        response = await httpx.get(url)
        break
    except:
        await asyncio.sleep(attempt * 2)
```

**Fix:** All services use `lib-resilience` with its preset policies. Consistent behavior, consistent observability, consistent failure handling.

---

## Reusability Checklist

Before finalizing a design, verify:

### Discovery
- [ ] Searched `libs/` for existing implementations of needed functionality
- [ ] Checked if other services solve a similar problem
- [ ] Reviewed `lib-schemas` for any types being redefined

### Extraction Decision
- [ ] Cross-service need confirmed → `libs/lib-<name>`
- [ ] Cross-domain need confirmed → service shared module
- [ ] Single-consumer → kept local (no premature extraction)

### Shared Code Quality
- [ ] Interface defined as Protocol/ABC (consumers depend on abstraction)
- [ ] No service-specific assumptions in shared code
- [ ] Tests co-located with shared code
- [ ] Public API documented (what, not how)
- [ ] Breaking changes follow deprecation path

### Consumer Integration
- [ ] All consumers import from the canonical source
- [ ] No duplicate implementations remain after extraction
- [ ] Dependency injection used (shared code doesn't instantiate its own deps)

---

## Existing Shared Libraries Quick Reference

Before writing new shared code, check if it belongs in an existing library:

| Library | Owns | Don't Reinvent |
|---------|------|----------------|
| `lib-schemas` | Cross-boundary types, envelopes, pagination, domain primitives | Pydantic base models, ID types, enums |
| `lib-security` | Auth, authz, secrets, input sanitization, tenant context | JWT validation, RBAC guards, permission checks |
| `lib-observability` | Logging, tracing, metrics, health checks | `get_logger`, `get_tracer`, `get_meter` |
| `lib-resilience` | Retry, circuit breaker, timeout, bulkhead, rate limiter | External call wrappers |
| `lib-fastapi` | App factory, middleware, error handling, response builders | `create_app`, `ApiError`, `ok`/`ok_list` |
| `lib-faststream` | Event app factory, envelope enforcement, correlation | `create_app`, event middleware |
| `lib-http` | Outbound HTTP with resilience and tracing | httpx wrappers |
| `lib-events` | Event context, registry, publisher protocol | `EventPublisher`, `EventRegistry` |
| `lib-database` | Connection pools, health checks, instrumentation | DB pool setup, query tracing |
| `lib-aws` | S3, SQS, SNS, EventBridge, Secrets Manager wrappers | AWS service clients |
| `lib-settings` | Configuration composition via `BaseServiceSettings` | Env var parsing |
| `lib-testing` | Factories, fixtures, contract validators, assertions | Test infrastructure |

---

## Related References

- **[modularity.md](modularity.md)** — Boundary definition and cohesion (where reusability decisions intersect with module structure)
- **[coherence.md](coherence.md)** — Ensuring shared code follows consistent patterns
- **[evoleability.md](evoleability.md)** — Versioning shared interfaces for safe evolution
- **[data-model.md](data-model.md)** — Layered model reuse across domain/contracts/persistence

---

*The cheapest code to maintain is the code you only wrote once.*
