# Domain-Driven Design Reference

> Strategic and tactical patterns for modeling complex business domains.

---

## 1. Ubiquitous Language

### MUST

- Use domain expert terminology in code, documentation, and conversation
- Define a glossary of terms per bounded context
- Name classes, methods, and variables using domain language
- Refactor code when domain understanding evolves

### NEVER

- Use technical jargon when domain terms exist (`DataProcessor` → `ClaimAdjudicator`)
- Allow synonyms for the same concept within a context
- Let developers invent terms without domain expert validation
- Mix languages from different bounded contexts

### WHEN → THEN

| When | Then |
|------|------|
| Domain expert says "we approve claims" | Name method `approve_claim()`, not `process()` or `handle()` |
| Multiple terms mean the same thing | Align on ONE term, update all code and docs |
| Term means different things in different areas | Split into separate bounded contexts |
| New concept emerges in conversation | Add to glossary, create corresponding type |

### ✅ Pattern

```python
# Domain language: "Underwriters assess risk and bind policies"
class Underwriter:
    async def assess_risk(self, application: PolicyApplication) -> RiskAssessment:
        """Evaluate application against underwriting guidelines."""
        ...

    async def bind_policy(self, application: PolicyApplication, assessment: RiskAssessment) -> BoundPolicy:
        """Convert approved application into active policy."""
        ...
```

### ❌ Anti-Pattern

```python
# Generic technical naming - loses domain meaning
class ApplicationHandler:
    async def process(self, data: dict) -> dict:
        """Handle the thing."""
        ...

    async def finalize(self, data: dict) -> dict:
        """Do the final step."""
        ...
```

---

## 2. Bounded Contexts

### MUST

- Define explicit boundaries around cohesive domain models
- Give each context its own ubiquitous language
- Separate contexts by module, package, or service boundary
- Document context relationships using context maps

### NEVER

- Share domain models directly across context boundaries
- Let one context's changes break another context
- Create a single unified model for the entire organization
- Allow implicit dependencies between contexts

### WHEN → THEN

| When | Then |
|------|------|
| Same term means different things to different teams | Create separate bounded contexts |
| Two models need different consistency guarantees | Separate into distinct contexts |
| Team ownership boundaries exist | Align context boundaries with team boundaries |
| Models change at different rates | Consider separating into contexts |

### ✅ Pattern: Context Separation

```
sales/                          # Sales Context
├── domain/
│   ├── customer.py            # Customer = prospect with budget
│   └── opportunity.py
└── application/

fulfillment/                    # Fulfillment Context  
├── domain/
│   ├── customer.py            # Customer = shipping destination
│   └── shipment.py
└── application/
```

### ✅ Pattern: Context Map

```python
# Document relationships between contexts
"""
Context Map:
┌─────────────┐         ┌──────────────┐
│   Sales     │─────────│ Fulfillment  │
│  (upstream) │ Customer│ (downstream) │
│             │  Placed │              │
└─────────────┘  Order  └──────────────┘
                  │
Relationship: Customer-Supplier
Integration: Async via OrderPlaced event
Anti-Corruption: Fulfillment translates Sales.Order → Fulfillment.ShipmentRequest
"""
```

### ❌ Anti-Pattern

```python
# Shared model across contexts - creates coupling
from shared.models import Customer  # Used everywhere - changes break everything

class SalesService:
    def create_opportunity(self, customer: Customer): ...

class FulfillmentService:
    def ship_order(self, customer: Customer): ...  # Same Customer, different needs
```

---

## 3. Aggregates

### MUST

- Design aggregates around transactional consistency boundaries
- Access aggregate internals only through the aggregate root
- Keep aggregates small - prefer smaller over larger
- Reference other aggregates by identity, not direct object reference
- Ensure one transaction modifies one aggregate

### NEVER

- Create aggregates that span multiple transactional boundaries
- Allow external code to modify aggregate internals directly
- Hold direct references to entities in other aggregates
- Update multiple aggregates in a single transaction

### WHEN → THEN

| When | Then |
|------|------|
| Group of objects must be consistent together | Model as single aggregate |
| Objects can be eventually consistent | Model as separate aggregates |
| Need to reference another aggregate | Store ID, not object reference |
| Aggregate grows beyond ~5 entities | Reconsider boundaries, likely too large |

### ✅ Pattern: Well-Bounded Aggregate

```python
from pydantic import BaseModel, Field
from typing import NewType
from decimal import Decimal

OrderId = NewType("OrderId", str)
ProductId = NewType("ProductId", str)  # Reference by ID, not object

class LineItem(BaseModel):
    """Value object within Order aggregate."""
    product_id: ProductId  # Reference, not embedded Product
    quantity: int = Field(gt=0)
    unit_price: Decimal

class Order(BaseModel):
    """Aggregate root - all access through this."""
    id: OrderId
    customer_id: str  # Reference to Customer aggregate
    items: list[LineItem] = Field(default_factory=list)
    status: OrderStatus = OrderStatus.DRAFT

    def add_item(self, product_id: ProductId, quantity: int, price: Decimal) -> None:
        """Business rule: can only add items to draft orders."""
        if self.status != OrderStatus.DRAFT:
            raise DomainError("Cannot modify non-draft order")
        self.items.append(LineItem(product_id=product_id, quantity=quantity, unit_price=price))

    def submit(self) -> "OrderSubmitted":
        """Transition to submitted, return domain event."""
        if not self.items:
            raise DomainError("Cannot submit empty order")
        self.status = OrderStatus.SUBMITTED
        return OrderSubmitted(order_id=self.id, total=self.total)

    @property
    def total(self) -> Decimal:
        return sum(item.unit_price * item.quantity for item in self.items)
```

### ❌ Anti-Pattern: Bloated Aggregate

```python
class Order(BaseModel):
    id: OrderId
    customer: Customer  # ❌ Embedded aggregate - should be customer_id
    items: list[LineItem]
    shipment: Shipment  # ❌ Embedded aggregate - different consistency boundary
    payments: list[Payment]  # ❌ Embedded aggregate - separate concern
    audit_log: list[AuditEntry]  # ❌ Cross-cutting, not domain
```

---

## 4. Entities vs Value Objects

### MUST

- Give entities a unique identity that persists through state changes
- Make value objects immutable and equality-based on attributes
- Use value objects for descriptive, measurement, or quantification concepts
- Use entities when identity matters independent of attributes

### NEVER

- Use entities when value objects suffice (adds unnecessary complexity)
- Make value objects mutable
- Compare entities by attribute equality alone
- Assign identity to concepts where identity doesn't matter

### WHEN → THEN

| When | Then |
|------|------|
| "Is this the same X?" matters | Entity (identity-based) |
| "Does this X equal that X?" by attributes | Value Object |
| Concept is measured, quantified, or describes | Value Object |
| Lifecycle and state changes must be tracked | Entity |
| Concept can be freely substituted if equal | Value Object |

### ✅ Pattern: Value Objects

```python
from pydantic import BaseModel, ConfigDict, field_validator
from decimal import Decimal

class Money(BaseModel):
    """Value object - immutable, equality by attributes."""
    model_config = ConfigDict(frozen=True)

    amount: Decimal
    currency: str = "USD"

    @field_validator("currency")
    @classmethod
    def valid_currency(cls, v: str) -> str:
        if v not in {"USD", "EUR", "GBP"}:
            raise ValueError(f"Unsupported currency: {v}")
        return v

    def add(self, other: "Money") -> "Money":
        if self.currency != other.currency:
            raise ValueError("Cannot add different currencies")
        return Money(amount=self.amount + other.amount, currency=self.currency)

class Address(BaseModel):
    """Value object - no identity, just attributes."""
    model_config = ConfigDict(frozen=True)

    street: str
    city: str
    postal_code: str
    country: str

# Two addresses with same values ARE equal
addr1 = Address(street="123 Main", city="NYC", postal_code="10001", country="US")
addr2 = Address(street="123 Main", city="NYC", postal_code="10001", country="US")
assert addr1 == addr2  # True - value equality
```

### ✅ Pattern: Entities

```python
class Customer(BaseModel):
    """Entity - identity matters, attributes can change."""
    id: CustomerId  # Identity
    name: str
    email: str
    address: Address  # Value object composition

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Customer):
            return False
        return self.id == other.id  # Identity equality only

    def __hash__(self) -> int:
        return hash(self.id)

# Same ID = same customer, even if attributes differ
c1 = Customer(id=CustomerId("123"), name="Alice", email="a@x.com", address=addr1)
c2 = Customer(id=CustomerId("123"), name="Alice Smith", email="alice@x.com", address=addr2)
assert c1 == c2  # True - same identity
```

### ❌ Anti-Pattern

```python
# Money as entity - unnecessary identity
class Money(BaseModel):
    id: str  # ❌ Money doesn't need identity
    amount: Decimal
    currency: str

# Address as mutable - breaks value object semantics
class Address(BaseModel):
    street: str
    city: str

    def update_street(self, new_street: str) -> None:  # ❌ Mutation
        self.street = new_street
```

---

## 5. Domain Events

### MUST

- Name events in past tense (something that happened)
- Make events immutable and self-contained
- Include all data consumers need (no callbacks required)
- Use events for cross-aggregate and cross-context communication
- Record when the event occurred

### NEVER

- Name events as commands or intentions (`CreateOrder` → `OrderCreated`)
- Include mutable references in events
- Require event consumers to call back for more data
- Use events for intra-aggregate state changes

### WHEN → THEN

| When | Then |
|------|------|
| State change in one aggregate affects another | Publish domain event |
| Other bounded contexts need to react | Publish domain event |
| Audit trail of business-significant changes needed | Publish domain event |
| Change is internal to aggregate only | No event needed |

### ✅ Pattern: Self-Contained Events

```python
from pydantic import BaseModel, Field
from datetime import datetime

class OrderPlaced(BaseModel):
    """Domain event - immutable record of what happened."""
    model_config = ConfigDict(frozen=True)

    # Identity
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    occurred_at: datetime = Field(default_factory=datetime.utcnow)

    # Aggregate reference
    order_id: OrderId

    # Self-contained data - consumer has everything needed
    customer_id: CustomerId
    items: list[OrderItemSnapshot]  # Snapshot, not references
    total: Money
    shipping_address: Address

class OrderItemSnapshot(BaseModel):
    """Immutable snapshot of item at event time."""
    model_config = ConfigDict(frozen=True)

    product_id: ProductId
    product_name: str  # Denormalized - no callback needed
    quantity: int
    unit_price: Money
```

### ✅ Pattern: Event Publishing

```python
class Order(BaseModel):
    _pending_events: list[DomainEvent] = []

    def place(self) -> None:
        # State change
        self.status = OrderStatus.PLACED
        self.placed_at = datetime.utcnow()

        # Record event
        self._pending_events.append(OrderPlaced(
            order_id=self.id,
            customer_id=self.customer_id,
            items=[self._snapshot_item(i) for i in self.items],
            total=self.total,
            shipping_address=self.shipping_address,
        ))

    def collect_events(self) -> list[DomainEvent]:
        events = self._pending_events.copy()
        self._pending_events.clear()
        return events
```

### ❌ Anti-Pattern

```python
# Event requiring callback
class OrderPlaced(BaseModel):
    order_id: OrderId  # ❌ Consumer must call back to get items, total, etc.

# Command-style naming
class PlaceOrder(BaseModel):  # ❌ This is a command, not an event
    order_id: OrderId

# Mutable event
class OrderPlaced(BaseModel):
    order_id: OrderId
    items: list[LineItem]  # ❌ Mutable reference to live objects
```

---

## 6. Repositories

### MUST

- Define repository interfaces in the domain layer
- Implement repositories in the infrastructure layer
- Return aggregate roots only, never internal entities
- Provide semantically meaningful query methods
- Handle persistence concerns in implementation, not interface

### NEVER

- Expose query language (SQL, Cypher) in repository interface
- Return partial aggregates or internal entities
- Put business logic in repositories
- Create repositories for non-aggregate-root entities

### WHEN → THEN

| When | Then |
|------|------|
| Need to retrieve aggregate by ID | `get(id) -> Aggregate | None` |
| Need existence check | `exists(id) -> bool` |
| Need domain-specific lookup | Named method: `find_pending_orders()` |
| Need complex queries for read models | Use separate Query Service (CQRS) |

### ✅ Pattern: Repository Interface

```python
from abc import ABC, abstractmethod

class OrderRepository(ABC):
    """Domain layer interface - implementation-agnostic."""

    @abstractmethod
    async def get(self, order_id: OrderId) -> Order | None:
        """Retrieve complete aggregate by identity."""
        ...

    @abstractmethod
    async def save(self, order: Order) -> None:
        """Persist aggregate (insert or update)."""
        ...

    @abstractmethod
    async def find_pending_by_customer(self, customer_id: CustomerId) -> list[Order]:
        """Domain-meaningful query method."""
        ...

# Infrastructure implementation
class SqlOrderRepository(OrderRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get(self, order_id: OrderId) -> Order | None:
        # SQL is hidden in implementation
        result = await self._session.execute(
            select(OrderModel).where(OrderModel.id == order_id)
        )
        row = result.scalar_one_or_none()
        return self._to_domain(row) if row else None

    async def save(self, order: Order) -> None:
        model = self._to_persistence(order)
        await self._session.merge(model)
```

### ❌ Anti-Pattern

```python
# Leaky abstraction - exposes SQL
class OrderRepository(ABC):
    @abstractmethod
    async def query(self, sql: str, params: dict) -> list[Order]:  # ❌ SQL in interface
        ...

# Returns internal entities
class OrderRepository(ABC):
    @abstractmethod
    async def get_line_items(self, order_id: OrderId) -> list[LineItem]:  # ❌ Internal entity
        ...

# Business logic in repository
class OrderRepository:
    async def place_order(self, order: Order) -> None:  # ❌ Business logic belongs in domain
        order.status = OrderStatus.PLACED
        order.placed_at = datetime.utcnow()
        await self.save(order)
```

---

## 7. Domain Services

### MUST

- Use domain services for operations that don't belong to a single entity
- Keep domain services stateless
- Name services using domain language verbs
- Place domain services in the domain layer

### NEVER

- Create domain services for operations that fit naturally on entities
- Put infrastructure concerns in domain services
- Make domain services stateful
- Use domain services as a dumping ground for logic

### WHEN → THEN

| When | Then |
|------|------|
| Operation involves multiple aggregates | Domain service |
| Operation is a domain concept but not entity behavior | Domain service |
| Operation requires external service | Application service (not domain) |
| Operation fits on single entity | Put it on the entity |

### ✅ Pattern: Domain Service

```python
class TransferService:
    """Domain service - stateless operation across aggregates."""

    def transfer(
        self,
        source: Account,
        destination: Account,
        amount: Money,
    ) -> tuple[Withdrawal, Deposit]:
        """
        Transfer money between accounts.
        Neither Account owns this operation - it spans both.
        """
        if source.balance < amount:
            raise InsufficientFundsError(source.id, amount)

        withdrawal = source.withdraw(amount)
        deposit = destination.deposit(amount)

        return withdrawal, deposit

class PricingService:
    """Domain service - complex calculation not owned by single entity."""

    def calculate_quote(
        self,
        product: Product,
        customer: Customer,
        quantity: int,
    ) -> Quote:
        """Pricing depends on product, customer tier, and quantity."""
        base_price = product.base_price * quantity
        tier_discount = self._tier_discount(customer.tier, base_price)
        volume_discount = self._volume_discount(quantity, base_price)

        return Quote(
            product_id=product.id,
            quantity=quantity,
            base_price=base_price,
            discounts=[tier_discount, volume_discount],
            final_price=base_price - tier_discount.amount - volume_discount.amount,
        )
```

### ❌ Anti-Pattern

```python
# Should be on entity
class OrderService:
    def add_item(self, order: Order, item: LineItem) -> None:  # ❌ Belongs on Order
        order.items.append(item)

# Infrastructure in domain service
class NotificationService:  # ❌ This is application/infrastructure, not domain
    def __init__(self, smtp_client: SmtpClient):
        self._smtp = smtp_client

    def notify_order_placed(self, order: Order) -> None:
        self._smtp.send(...)

# Stateful service
class PricingService:
    def __init__(self):
        self._cache: dict[str, Price] = {}  # ❌ Stateful - use external cache
```

---

## 8. Anti-Corruption Layer (ACL)

### MUST

- Create ACL when integrating with external or legacy systems
- Translate external models into domain models
- Isolate the translation logic in a dedicated layer
- Keep domain model pure and unaffected by external models

### NEVER

- Let external data structures leak into domain code
- Modify domain model to match external system's model
- Skip ACL for "simple" integrations (they grow complex)
- Scatter translation logic throughout the codebase

### WHEN → THEN

| When | Then |
|------|------|
| Integrating with legacy system | Build ACL to translate |
| Consuming third-party API | Build ACL adapter |
| External model doesn't fit domain | ACL translates to domain concepts |
| Multiple external systems provide same concept | ACL normalizes to single domain model |

### ✅ Pattern: Anti-Corruption Layer

```python
# External system's model (we don't control this)
@dataclass
class LegacyCrmCustomer:
    cust_no: str
    cust_name: str
    cust_addr_1: str
    cust_addr_2: str
    cust_type_cd: int  # 1=retail, 2=wholesale, 3=partner

# Our domain model (clean, domain-driven)
class Customer(BaseModel):
    id: CustomerId
    name: str
    address: Address
    tier: CustomerTier

# Anti-corruption layer - isolates translation
class CrmCustomerTranslator:
    """Translates legacy CRM model to domain model."""

    _TIER_MAP = {
        1: CustomerTier.RETAIL,
        2: CustomerTier.WHOLESALE,
        3: CustomerTier.PARTNER,
    }

    def to_domain(self, legacy: LegacyCrmCustomer) -> Customer:
        return Customer(
            id=CustomerId(legacy.cust_no),
            name=legacy.cust_name,
            address=Address(
                street=legacy.cust_addr_1,
                unit=legacy.cust_addr_2 or None,
                # ... parse remaining address fields
            ),
            tier=self._TIER_MAP.get(legacy.cust_type_cd, CustomerTier.RETAIL),
        )

    def to_legacy(self, customer: Customer) -> LegacyCrmCustomer:
        """Reverse translation when writing back."""
        ...

class CrmCustomerAdapter:
    """Adapter using ACL to provide domain-friendly interface."""

    def __init__(self, crm_client: LegacyCrmClient, translator: CrmCustomerTranslator):
        self._crm = crm_client
        self._translator = translator

    async def get_customer(self, customer_id: CustomerId) -> Customer | None:
        legacy = await self._crm.fetch_customer(str(customer_id))
        return self._translator.to_domain(legacy) if legacy else None
```

### ❌ Anti-Pattern

```python
# Domain model polluted by external concerns
class Customer(BaseModel):
    id: CustomerId
    name: str
    cust_type_cd: int  # ❌ Legacy field leaked into domain

    @property
    def tier(self) -> CustomerTier:
        # ❌ Translation logic scattered in domain
        return {1: CustomerTier.RETAIL, 2: CustomerTier.WHOLESALE}[self.cust_type_cd]

# Direct use of external model in domain
class OrderService:
    async def create_order(self, crm_customer: LegacyCrmCustomer) -> Order:  # ❌ External type in domain
        ...
```

---

## 9. Strategic Design Decision Framework

### Context Boundary Decisions

```
Need to split contexts?
│
├─► Same term, different meanings? ──► YES, split
├─► Different teams/ownership? ──► YES, split
├─► Different rates of change? ──► Consider splitting
├─► Different consistency needs? ──► YES, split
└─► Strong transactional coupling? ──► NO, keep together
```

### Aggregate Boundary Decisions

```
Should X be in Aggregate A?
│
├─► Must be consistent with A in same transaction? ──► YES, include
├─► Can be eventually consistent? ──► NO, separate aggregate
├─► Referenced but not modified together? ──► NO, reference by ID
└─► Aggregate growing beyond ~5 entities? ──► Reconsider boundaries
```

### Entity vs Value Object Decision

```
How to model concept X?
│
├─► Need to track X's identity over time? ──► Entity
├─► X described by attributes only? ──► Value Object
├─► "Same X" means "same attributes"? ──► Value Object
├─► "Same X" means "same identity"? ──► Entity
└─► X is measurement/description/quantity? ──► Value Object
```

---

## 10. Quick Reference Checklist

### Designing a New Domain Model

- [ ] Identify bounded contexts and their relationships
- [ ] Define ubiquitous language glossary for each context
- [ ] Map aggregates to consistency boundaries
- [ ] Classify concepts as Entity or Value Object
- [ ] Design aggregates to be small and reference others by ID
- [ ] Define domain events for cross-aggregate communication
- [ ] Create repository interfaces in domain layer
- [ ] Plan anti-corruption layers for external integrations

### Code Review Checklist

- [ ] Names use ubiquitous language?
- [ ] Aggregates are accessed only through roots?
- [ ] Value objects are immutable?
- [ ] Events are past-tense and self-contained?
- [ ] No cross-aggregate object references?
- [ ] Repository interfaces are implementation-agnostic?
- [ ] Domain layer has no infrastructure dependencies?

---

## References

For deeper coverage, see:

- **modularity.md**: Module boundaries and cohesion
- **evolvability.md**: Designing for change over time
- **coherence.md**: Ensuring model consistency
- **testability.md**: Testing domain models effectively
