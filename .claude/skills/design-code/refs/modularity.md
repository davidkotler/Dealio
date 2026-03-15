# Modularity Reference

> Decompose systems into cohesive, loosely-coupled modules with explicit boundaries.

---

## Core Metrics

| Metric | Target | Smell |
|--------|--------|-------|
| **Cohesion** | High (single concept) | Methods don't use each other |
| **Coupling** | Low (abstractions only) | Many cross-module imports |
| **Fan-out** | ≤5 dependencies | Module depends on >7 others |
| **Depth** | ≤3 levels | Deep nested module hierarchies |

---

## MUST

- always have full import path
- Depend on abstractions (protocols/ABCs) at module boundaries
- Inject all external dependencies through constructors or function parameters
- Align module boundaries with domain concepts, not technical layers
- Keep implementation details private and unexposed
- Design each module to be testable in isolation
- Use anti-corruption layers when integrating external systems

## NEVER

- Import internal/private symbols from other modules
- Share database tables, schemas, or ORM models across modules
- Create circular dependencies between modules
- Let domain logic leak outside its owning module
- Instantiate collaborators inside classes (hardcoded coupling)
- Expose mutable internal state structures
- Build "god modules" spanning multiple unrelated concepts

---

## WHEN / THEN

**WHEN** code changes together for the same business reason  
**THEN** keep it in the same module

**WHEN** code has different reasons to change  
**THEN** separate into distinct modules

**WHEN** modules need to communicate  
**THEN** define explicit contracts (protocols, DTOs, events)

**WHEN** crossing domain boundaries  
**THEN** translate using anti-corruption layer

**WHEN** a module exceeds ~500 lines or ~10 public symbols  
**THEN** evaluate splitting along natural domain seams

**WHEN** testing requires mocking >3 collaborators  
**THEN** re-evaluate module boundaries and responsibilities

**WHEN** two modules share identical data structures  
**THEN** extract shared types to a separate contracts module

---

## Decision Tree

```
Need to add new code?
    │
    ├─► Does it change for same reason as existing module?
    │       ├─► YES → Add to existing module
    │       └─► NO  → Create new module
    │
    ├─► Need to use another module's functionality?
    │       ├─► Public API exists? → Use it
    │       └─► No public API?     → Request API, don't reach in
    │
    ├─► Two modules need same type?
    │       └─► Extract to shared contracts module
    │
    └─► Module getting too large?
            └─► Split along domain seams, not technical layers
```

---

## Patterns

### ✅ Clean Module Boundary

```python

from orders.service import OrderService
from orders.models import Order, CreateOrderRequest
```

```python
# orders/service.py — Implementation depends on abstractions
from abc import ABC, abstractmethod

class PaymentGateway(ABC):
    @abstractmethod
    async def charge(self, amount: Money) -> PaymentResult: ...

class OrderService:
    def __init__(self, payments: PaymentGateway, repo: OrderRepository):
        self._payments = payments  # Injected abstraction
        self._repo = repo

    async def place_order(self, request: CreateOrderRequest) -> Order:
        order = Order.create(request)
        await self._payments.charge(order.total)
        await self._repo.save(order)
        return order
```

### ✅ Anti-Corruption Layer

```python
# orders/adapters/inventory_client.py
class InventoryClient:
    """Translates between Order domain and Inventory domain."""

    def __init__(self, http_client: HttpClient):
        self._http = http_client

    async def reserve(self, items: list[OrderItem]) -> Reservation:
        # Translate TO external domain
        payload = [{"sku": i.sku, "qty": i.quantity} for i in items]
        response = await self._http.post("/reserve", json=payload)
        # Translate FROM external domain
        return Reservation(
            id=response["reservation_id"],
            expires_at=parse_datetime(response["expires"]),
        )
```

### ✅ Module-Level Factory

```python
# orders/__init__.py
def create_order_service(config: Config) -> OrderService:
    """Factory assembles module with its dependencies."""
    repo = PostgresOrderRepository(config.database_url)
    payments = StripePaymentGateway(config.stripe_key)
    return OrderService(payments=payments, repo=repo)
```

### ✅ Facade for Complex Subsystem

```python
# reporting/facade.py
class ReportingFacade:
    """Simplified interface to complex reporting subsystem."""

    def __init__(self, metrics: MetricsCollector, formatter: ReportFormatter):
        self._metrics = metrics
        self._formatter = formatter

    async def generate_summary(self, date_range: DateRange) -> Report:
        # Hides complexity of metric aggregation, formatting, etc.
        raw = await self._metrics.aggregate(date_range)
        return self._formatter.to_summary(raw)
```

### ✅ Protocol-Based Contract

```python
# contracts/repositories.py — Shared abstraction
from typing import Protocol

class OrderRepository(Protocol):
    async def get(self, id: OrderId) -> Order | None: ...
    async def save(self, order: Order) -> None: ...

# orders/service.py — Uses protocol
class OrderService:
    def __init__(self, repo: OrderRepository):  # Accepts any impl
        self._repo = repo

# infrastructure/postgres.py — Implements protocol
class PostgresOrderRepository:
    async def get(self, id: OrderId) -> Order | None: ...
    async def save(self, order: Order) -> None: ...
```

---

## Anti-Patterns

### ❌ Reaching Across Boundaries

```python
# BAD: Order module reaching into Inventory internals
from inventory._internal.stock import StockLevel  # Private import!

class OrderService:
    async def check_availability(self, sku: str) -> bool:
        return StockLevel.query(sku).available > 0  # Coupled to internals
```

### ❌ Circular Dependencies

```python
# orders/service.py
from shipping.calculator import ShippingCalculator  # orders → shipping

# shipping/calculator.py  
from orders.models import Order  # shipping → orders  ← CYCLE!
```

**Fix:** Extract shared types to `contracts/` module or use dependency inversion.

### ❌ Hardcoded Dependencies

```python
# BAD: Instantiates its own dependencies
class OrderService:
    def __init__(self):
        self._repo = PostgresOrderRepository()  # Hardcoded!
        self._payments = StripeClient("sk_live_xxx")  # Secrets in code!
```

### ❌ Leaky Abstraction

```python
# BAD: Exposing internal data structure
class OrderRepository:
    def get_order(self, id: str) -> dict:  # Returns raw dict, not domain model
        return self._db.query("SELECT * FROM orders WHERE id = %s", id)
```

### ❌ Feature Envy

```python
# BAD: Order module manipulating Invoice internals
class OrderService:
    def finalize(self, order: Order, invoice: Invoice):
        invoice._line_items.append(...)  # Reaching into Invoice internals
        invoice._total = sum(...)         # Order shouldn't know Invoice structure
        invoice._status = "finalized"
```

---

## Boundary Definition Checklist

Before finalizing a module boundary, verify:

- [ ] Module has a single, clear responsibility (one reason to change)
- [ ] Public interface is minimal and well-documented
- [ ] No imports of private/internal symbols from other modules
- [ ] Dependencies are injected, not instantiated internally
- [ ] Module can be tested with fakes/mocks for external deps
- [ ] No circular dependency chains exist
- [ ] Domain language is consistent within the module
- [ ] Changes are contained—modifying internals doesn't break consumers

---

## Module Size Heuristics

| Indicator | Action |
|-----------|--------|
| >500 lines in main module file | Consider splitting |
| >10 public exports | Likely multiple responsibilities |
| >5 direct dependencies | Risk of coupling; introduce facades |
| Tests require >3 mocks | Boundaries may be misaligned |
| Changes ripple to 3+ modules | Coupling too tight |

---

## Dependency Direction Rules

```
                    STABLE (abstract)
                          ↑
    Domain Core ←── Application ←── Infrastructure
         ↑              ↑                 ↑
     Entities      Use Cases         Adapters
                          ↑
                    VOLATILE (concrete)
```

- **Depend inward** toward stability and abstraction
- **Never depend outward** from core to infrastructure
- **Adapters implement interfaces** defined in core

---

## Related References

| Topic | Reference | When to Use |
|-------|-----------|-------------|
| Domain boundaries | `refs/ddd.md` | Defining bounded contexts |
| Testability | `refs/testability.md` | Ensuring modules are testable |
| Resilience | `refs/resilience.md` | Module failure isolation |
| Coherence | `refs/coherence.md` | Internal consistency |
