# Evolvability Reference

> *"The only constant in software is change. Design for the changes you cannot predict."*

This reference provides patterns and principles for designing systems that gracefully accommodate change over time without requiring wholesale rewrites.

---

## Core Concept

**Evolvability** is the capacity of a system to adapt to new requirements, technologies, and scale demands with minimal disruption to existing functionality.

A well-designed evolvable system exhibits:







- **Localized change impact** — modifications stay contained
- **Clear extension mechanisms** — new behavior adds, not modifies
- **Stable interfaces** — contracts outlive implementations
- **Reversibility** — changes can be rolled back safely

---

## MUST

1. **Define explicit extension points** for anticipated variation
2. **Version all public interfaces** (APIs, events, schemas) from day one
3. **Encapsulate implementation details** behind stable abstractions
4. **Provide migration paths** for any breaking change
5. **Isolate third-party dependencies** behind adapters
6. **Design modules for independent evolution** with clear boundaries
7. **Make configuration external** to code (environment, feature flags)
8. **Document architectural decisions** with rationale and alternatives considered
9. **Design contracts first** — interfaces before implementations
10. **Support multiple versions concurrently** during transitions

---

## NEVER

1. **Expose internal data structures** through public interfaces
2. **Create circular dependencies** between modules
3. **Hardcode behavior** that stakeholders may want to change
4. **Make breaking changes** without deprecation period
5. **Depend on implementation details** of other modules
6. **Assume current requirements are final** — they never are
7. **Leak abstraction internals** (database IDs, internal enums)
8. **Couple deployment units** to shared mutable state
9. **Design for only the current scale** without extension seams
10. **Remove functionality** without migration tooling

---

## WHEN / THEN Patterns

### Interface Evolution

**WHEN** adding new behavior to existing module  
**THEN** extend through composition or strategy pattern, not modification

**WHEN** a public interface must change  
**THEN** version the interface and maintain both versions during transition

**WHEN** deprecating functionality  
**THEN** mark deprecated, document migration path, set removal timeline

**WHEN** internal implementation changes  
**THEN** verify all public contracts remain satisfied (tests pass unchanged)

### Dependency Management

**WHEN** depending on external library or service  
**THEN** wrap in an adapter layer you control

**WHEN** a dependency becomes problematic  
**THEN** swap implementation behind existing interface, not rewrite consumers

**WHEN** two modules need to communicate  
**THEN** define a contract both can evolve against independently

### Data Evolution

**WHEN** schema changes are needed  
**THEN** use additive changes; make new fields optional with defaults

**WHEN** removing a field from schema  
**THEN** stop writing first, stop reading later, remove after migration window

**WHEN** changing field semantics  
**THEN** add new field with new semantics, deprecate old field

### Feature Evolution

**WHEN** behavior may vary by customer or context  
**THEN** externalize as configuration or feature flag

**WHEN** rolling out risky changes  
**THEN** use feature flags for gradual rollout with kill switch

**WHEN** requirements are uncertain  
**THEN** design explicit seams where variation can be injected later

---

## Patterns

### Pattern 1: Strategy Injection

Encapsulate varying behavior behind an interface; inject implementation at runtime.

```python
# ✅ Evolvable: Behavior varies without code change
from abc import ABC, abstractmethod
from typing import Protocol

class PricingStrategy(Protocol):
    def calculate(self, order: Order) -> Money: ...

class StandardPricing:
    def calculate(self, order: Order) -> Money:
        return sum(item.price * item.qty for item in order.items)

class DiscountedPricing:
    def __init__(self, discount_pct: Decimal):
        self._discount = discount_pct

    def calculate(self, order: Order) -> Money:
        base = sum(item.price * item.qty for item in order.items)
        return base * (1 - self._discount)

class OrderService:
    def __init__(self, pricing: PricingStrategy):
        self._pricing = pricing  # Injected, swappable

    def total(self, order: Order) -> Money:
        return self._pricing.calculate(order)
```

```python
# ❌ Rigid: Changing pricing requires modifying OrderService
class OrderService:
    def total(self, order: Order) -> Money:
        base = sum(item.price * item.qty for item in order.items)
        if order.customer.tier == "gold":
            return base * Decimal("0.9")  # Hardcoded logic
        return base
```

### Pattern 2: Anti-Corruption Layer

Shield your domain from external system changes with a translation boundary.

```python
# ✅ Evolvable: External changes don't propagate
class PaymentGateway(Protocol):
    async def charge(self, amount: Money, token: str) -> PaymentResult: ...

class StripeAdapter:
    """Translates between our domain and Stripe's API."""
    def __init__(self, client: stripe.Client):
        self._client = client

    async def charge(self, amount: Money, token: str) -> PaymentResult:
        # Stripe-specific logic contained here
        response = await self._client.charges.create(
            amount=int(amount * 100),  # Stripe uses cents
            currency="usd",
            source=token,
        )
        # Translate to our domain model
        return PaymentResult(
            id=PaymentId(response.id),
            status=self._map_status(response.status),
        )
```

```python
# ❌ Rigid: Stripe details leak throughout codebase
class OrderService:
    async def checkout(self, order: Order, token: str):
        # Stripe API called directly — any Stripe change affects this
        response = await stripe.charges.create(
            amount=int(order.total * 100),
            currency="usd",
            source=token,
        )
        order.payment_id = response.id  # Stripe's ID format leaks
```

### Pattern 3: Versioned Interfaces

Support multiple API versions simultaneously for graceful evolution.

```python
# ✅ Evolvable: Old clients keep working
from fastapi import APIRouter

router_v1 = APIRouter(prefix="/v1")
router_v2 = APIRouter(prefix="/v2")

@router_v1.get("/users/{id}")
async def get_user_v1(id: int) -> UserResponseV1:
    user = await user_service.get(id)
    return UserResponseV1.from_domain(user)  # Old shape

@router_v2.get("/users/{id}")
async def get_user_v2(id: int) -> UserResponseV2:
    user = await user_service.get(id)
    return UserResponseV2.from_domain(user)  # New shape with more fields
```

### Pattern 4: Additive Schema Evolution

Evolve data schemas without breaking existing consumers.

```python
# ✅ Evolvable: New fields are optional, old readers ignore them
class OrderEventV1(BaseModel):
    order_id: str
    customer_id: str
    total: Decimal

class OrderEventV2(BaseModel):
    order_id: str
    customer_id: str
    total: Decimal
    currency: str = "USD"  # Added with default
    loyalty_points: int | None = None  # Optional new field

# Old consumers reading V2 events still work — extra fields ignored
# New consumers can use new fields when present
```

```python
# ❌ Breaking: Renaming or removing fields breaks consumers
class OrderEventV2(BaseModel):
    id: str  # Renamed from order_id — BREAKS CONSUMERS
    customer_id: str
    amount: Decimal  # Renamed from total — BREAKS CONSUMERS
    # currency field removed — BREAKS CONSUMERS
```

### Pattern 5: Feature Flags for Behavior Evolution

Decouple deployment from release; enable gradual rollout.

```python
# ✅ Evolvable: New behavior controlled without deployment
class FeatureFlags(Protocol):
    def is_enabled(self, flag: str, context: dict) -> bool: ...

class RecommendationService:
    def __init__(self, flags: FeatureFlags, ml_engine: MLEngine, rules_engine: RulesEngine):
        self._flags = flags
        self._ml = ml_engine
        self._rules = rules_engine

    async def get_recommendations(self, user_id: str) -> list[Product]:
        if self._flags.is_enabled("use_ml_recommendations", {"user": user_id}):
            return await self._ml.recommend(user_id)
        return await self._rules.recommend(user_id)  # Fallback
```

### Pattern 6: Plugin Architecture

Allow extension without core modification.

```python
# ✅ Evolvable: New exporters added without changing core
from abc import ABC, abstractmethod
from typing import ClassVar

class Exporter(ABC):
    format_name: ClassVar[str]

    @abstractmethod
    def export(self, data: Report) -> bytes: ...

class ExporterRegistry:
    def __init__(self):
        self._exporters: dict[str, Exporter] = {}

    def register(self, exporter: Exporter) -> None:
        self._exporters[exporter.format_name] = exporter

    def export(self, format: str, data: Report) -> bytes:
        if format not in self._exporters:
            raise UnsupportedFormatError(format)
        return self._exporters[format].export(data)

# New formats added by registration, not modification
registry.register(PDFExporter())
registry.register(CSVExporter())
registry.register(ExcelExporter())  # Added later without core changes
```

---

## Anti-Patterns

### Anti-Pattern 1: Primitive Obsession Prevents Evolution

```python
# ❌ Strings for everything — can't evolve validation or behavior
def create_user(email: str, phone: str, country_code: str):
    # No place to add email validation rules
    # No place to add phone formatting logic
    # Country-specific behavior scattered everywhere
    ...
```

```python
# ✅ Rich types create evolution points
class Email(BaseModel):
    value: str

    @field_validator("value")
    @classmethod
    def validate(cls, v: str) -> str:
        # Validation rules evolve in one place
        if "@" not in v:
            raise ValueError("Invalid email")
        return v.lower()

class PhoneNumber(BaseModel):
    country_code: str
    number: str

    def format(self, style: str = "international") -> str:
        # Formatting logic evolves here
        ...
```

### Anti-Pattern 2: Concrete Coupling

```python
# ❌ Direct instantiation — can't substitute implementations
class OrderProcessor:
    def __init__(self):
        self._notifier = EmailNotifier()  # Concrete class
        self._payment = StripePayment()   # Concrete class

    async def process(self, order: Order):
        await self._payment.charge(order)
        await self._notifier.send(order.customer, "Order confirmed")
```

```python
# ✅ Interface coupling — implementations swappable
class OrderProcessor:
    def __init__(self, notifier: Notifier, payment: PaymentGateway):
        self._notifier = notifier
        self._payment = payment

    async def process(self, order: Order):
        await self._payment.charge(order)
        await self._notifier.send(order.customer, "Order confirmed")
```

### Anti-Pattern 3: Shotgun Surgery

When one change requires modifications across many files.

```python
# ❌ Customer discount logic scattered everywhere
# orders/service.py
if customer.tier == "gold": discount = 0.1

# billing/calculator.py  
if customer.tier == "gold": discount = 0.1

# shipping/service.py
if customer.tier == "gold": free_shipping = True

# Adding "platinum" tier requires changing all files
```

```python
# ✅ Centralized discount policy
class CustomerBenefits:
    """Single source of truth for customer tier benefits."""

    @staticmethod
    def for_tier(tier: CustomerTier) -> Benefits:
        return {
            CustomerTier.STANDARD: Benefits(discount=Decimal(0), free_shipping=False),
            CustomerTier.GOLD: Benefits(discount=Decimal("0.1"), free_shipping=True),
            CustomerTier.PLATINUM: Benefits(discount=Decimal("0.15"), free_shipping=True),
        }[tier]

# All consumers use CustomerBenefits — new tiers added in one place
```

### Anti-Pattern 4: Leaky Abstractions

```python
# ❌ Database implementation leaks through interface
class UserRepository:
    async def find_by_sql(self, sql: str) -> list[User]:  # Leaks SQL
        ...

    async def get_connection(self) -> Connection:  # Leaks connection pooling
        ...
```

```python
# ✅ Clean abstraction hides implementation
class UserRepository(Protocol):
    async def find_by_email(self, email: Email) -> User | None: ...
    async def find_active_since(self, since: datetime) -> list[User]: ...
    async def save(self, user: User) -> None: ...
```

---



## Evolution Checklist




Before finalizing any design, verify:






### Interface Stability



- [ ] Public interfaces depend on abstractions, not implementations
- [ ] All public contracts are versioned or version-ready



- [ ] No internal types exposed in public signatures
- [ ] Extension points exist for anticipated variation




### Change Isolation



- [ ] A single requirement change affects only one module
- [ ] Third-party dependencies wrapped in adapters

- [ ] Configuration external to code

- [ ] Feature flags available for behavior variation


### Data Evolution

- [ ] Schema changes are additive where possible
- [ ] Field removal follows deprecation process

- [ ] Event/message formats support schema evolution
- [ ] Migration tooling exists for breaking changes

### Reversibility

- [ ] Deployments can be rolled back
- [ ] Feature flags allow instant disable
- [ ] Data migrations are reversible
- [ ] Multiple versions can coexist

---

## Decision Matrix

| Situation | Evolution Strategy |
|-----------|-------------------|
| Behavior may vary by customer | Strategy pattern + configuration |
| External API dependency | Anti-corruption layer |
| Schema must change | Additive fields, versioned events |
| Risky new feature | Feature flag with gradual rollout |
| Multiple output formats | Plugin/registry pattern |
| Cross-cutting concerns | Decorator/middleware chain |
| Implementation likely to change | Interface + dependency injection |
| Requirements uncertain | Explicit seams, defer decisions |

---

## Related References

- **[modularity.md](modularity.md)** — Boundary definition and cohesion
- **[robustness.md](robustness.md)** — Handling failure gracefully
- **[testability.md](testability.md)** — Design for verification
- **[coherence.md](coherence.md)** — Maintaining conceptual integrity

---

*Evolvability is not about predicting the future — it's about designing systems that remain malleable when the future arrives.*
