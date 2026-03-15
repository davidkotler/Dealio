# Design Coherence

> *"A coherent system reads like it was written by a single mind with a single vision."*

Coherence ensures that a codebase maintains conceptual unity—consistent terminology, uniform patterns, predictable structure, and aligned abstractions throughout. It is the property that makes systems learnable, navigable, and evolvable.

---

## Core Dimensions of Coherence

| Dimension | Definition |
|-----------|------------|
| **Terminological** | Same concepts use same names everywhere |
| **Structural** | Similar components organized similarly |
| **Behavioral** | Similar problems solved the same way |
| **Abstraction** | Components at same layer share abstraction level |
| **Temporal** | Codebase evolves uniformly, not in "eras" |

---

## MUST

1. **Use ubiquitous language consistently** within each bounded context—same term, same meaning, everywhere
2. **Apply identical patterns** for solving structurally similar problems
3. **Maintain uniform abstraction levels** within architectural layers
4. **Follow established naming conventions** without deviation
5. **Keep module structure predictable**—if `orders/` has `service.py`, `repository.py`, so should `products/`
6. **Use consistent error handling strategies** across similar operations
7. **Apply uniform interface contracts**—if one service returns `Result[T, Error]`, all should
8. **Document deviations explicitly** when coherence must be broken for valid reasons

---

## NEVER

1. **Mix domain terminology** across bounded context boundaries without translation
2. **Solve the same problem differently** in different parts of the codebase
3. **Combine abstraction levels** within a single component (HTTP handling mixed with business rules)
4. **Introduce new conventions** without a migration plan for existing code
5. **Create "snowflake" implementations** when established patterns exist
6. **Use synonyms** for the same domain concept (`client`/`customer`/`user` interchangeably)
7. **Allow style drift**—different formatting, naming styles in different modules
8. **Accumulate multiple approaches** to the same problem over time

---

## WHEN / THEN

### Adding New Functionality

**WHEN** implementing a new feature  
**THEN** audit existing codebase for similar features and mirror their patterns exactly

```python
# Existing pattern in codebase:
class OrderService:
    def __init__(self, repo: OrderRepository, events: EventPublisher):
        self._repo = repo
        self._events = events

# ✅ New feature follows the pattern
class ShipmentService:
    def __init__(self, repo: ShipmentRepository, events: EventPublisher):
        self._repo = repo
        self._events = events

# ❌ New feature breaks the pattern
class ShipmentManager:  # Different naming
    def __init__(self, db: Database):  # Different dependency style
        self.database = db  # Different attribute naming
```

---

### Encountering Inconsistency

**WHEN** discovering two different patterns solving the same problem  
**THEN** evaluate both, select the superior one, and create a migration task—never add a third

```python
# Discovery: Two date formatting approaches exist
# Approach A (3 usages): datetime.strftime("%Y-%m-%d")
# Approach B (12 usages): date.isoformat()

# ✅ Decision: Standardize on isoformat() (more usages, cleaner)
# Action: Create tech debt ticket to migrate 3 strftime usages

# ❌ Anti-pattern: Add a third approach
formatted = f"{date.year}-{date.month:02d}-{date.day:02d}"
```

---

### Naming New Concepts

**WHEN** introducing a new domain concept  
**THEN** check the glossary first, then use consistently from first introduction

```python
# Domain glossary defines: "Fulfillment" = process of completing an order

# ✅ Consistent usage
class FulfillmentService: ...
class FulfillmentStarted(Event): ...
async def begin_fulfillment(order: Order): ...

# ❌ Incoherent usage  
class ShippingService: ...        # "Shipping" not in glossary
class OrderCompletionStarted: ... # Different term for same concept
async def process_order(order): ... # Vague, doesn't use domain language
```

---

### Cross-Context Communication

**WHEN** one bounded context needs data from another  
**THEN** translate through an anti-corruption layer using the receiving context's language

```python
# Inventory context uses "SKU", Orders context uses "ProductId"

# ✅ Anti-corruption layer translates
class InventoryAdapter:
    """Translates between Orders and Inventory bounded contexts."""

    async def check_availability(self, product_id: ProductId) -> bool:
        sku = self._to_inventory_sku(product_id)  # Explicit translation
        return await self._inventory_client.check_stock(sku)

    def _to_inventory_sku(self, product_id: ProductId) -> SKU:
        return SKU(f"SKU-{product_id.value}")

# ❌ Leaking foreign terminology
class OrderService:
    async def create_order(self, items: list[SKU]):  # SKU is Inventory's term!
        ...
```

---

### Choosing Abstraction Level

**WHEN** designing a component  
**THEN** ensure all operations within it exist at the same abstraction level

```python
# ✅ Uniform abstraction level (all orchestration)
class OrderWorkflow:
    async def process(self, order: Order) -> ProcessedOrder:
        validated = await self._validator.validate(order)
        priced = await self._pricer.calculate(validated)
        persisted = await self._repository.save(priced)
        await self._notifier.notify_created(persisted)
        return persisted

# ❌ Mixed abstraction levels
class OrderWorkflow:
    async def process(self, order: Order) -> ProcessedOrder:
        # High-level orchestration
        validated = await self._validator.validate(order)

        # Suddenly low-level implementation detail
        total = Decimal("0")
        for item in order.items:
            price = item.unit_price * item.quantity
            if item.discount:
                price = price * (1 - item.discount.percentage)
            total += price
        order.total = total

        # Back to high-level
        persisted = await self._repository.save(order)
        return persisted
```

---

### Structuring Modules

**WHEN** creating a new module/package  
**THEN** mirror the structure of existing peer modules

```
# Existing structure in src/domains/orders/
orders/
├── __init__.py
├── models.py
├── service.py
├── repository.py
├── events.py
└── exceptions.py

# ✅ New module mirrors structure
shipments/
├── __init__.py
├── models.py
├── service.py
├── repository.py
├── events.py
└── exceptions.py

# ❌ Inconsistent structure
shipments/
├── __init__.py
├── shipment.py          # Different naming
├── db.py                # Different naming
├── handlers/            # Unexpected subdirectory
│   └── ship_handler.py
└── utils.py             # No peer module has this
```

---

### Handling Errors

**WHEN** implementing error handling  
**THEN** follow the established error strategy consistently

```python
# Established pattern: Domain errors are specific exceptions

# ✅ Consistent error handling
class InsufficientInventoryError(DomainError):
    def __init__(self, sku: str, requested: int, available: int):
        self.sku = sku
        self.requested = requested
        self.available = available
        super().__init__(f"Insufficient inventory for {sku}")

async def reserve_inventory(sku: str, quantity: int) -> Reservation:
    available = await repo.get_available(sku)
    if available < quantity:
        raise InsufficientInventoryError(sku, quantity, available)
    return await repo.create_reservation(sku, quantity)

# ❌ Inconsistent error handling
async def reserve_inventory(sku: str, quantity: int) -> Reservation | None:
    available = await repo.get_available(sku)
    if available < quantity:
        return None  # Breaks pattern: returns None instead of raising
    return await repo.create_reservation(sku, quantity)
```

---

### Evolving the Codebase

**WHEN** improving patterns or introducing better approaches  
**THEN** migrate all usages—partial adoption creates incoherence

```python
# Decision: Migrate from dataclass to Pydantic for validation

# ✅ Complete migration (atomic change)
# PR: "Migrate all DTOs to Pydantic"
# - Converts ALL 47 dataclass DTOs to Pydantic
# - Updates all instantiation sites
# - Single coherent state after merge

# ❌ Partial migration (creates incoherence)
# PR: "Use Pydantic for new OrderDTO"
# - Converts only OrderDTO
# - Now 1 Pydantic model, 46 dataclasses
# - Team confused about which to use
# - Both patterns coexist indefinitely
```

---

## Patterns

### Pattern: Glossary-Driven Development

Maintain a domain glossary and enforce its usage:

```markdown
# docs/glossary.md

| Term | Definition | Context | Anti-terms |
|------|------------|---------|------------|
| Order | A customer's intent to purchase | Orders | Purchase, Transaction |
| Fulfillment | Process of completing an order | Fulfillment | Shipping, Delivery |
| Customer | Entity placing orders | Orders | Client, User, Buyer |
| SKU | Stock Keeping Unit identifier | Inventory | ProductId, ItemCode |
```

```python
# Linting rule enforces glossary
# .claude/hooks/pre-commit.sh
grep -r "client" src/orders/ && echo "ERROR: Use 'customer' in Orders context"
```

---

### Pattern: Structural Templates

Define templates for common structures:

```python
# Template: Domain Module Structure
# .claude/assets/templates/domain-module/

"""
{domain}/
├── __init__.py          # Public exports only
├── models.py            # Domain entities and value objects
├── service.py           # Application services
├── repository.py        # Data access abstraction
├── events.py            # Domain events
├── exceptions.py        # Domain-specific errors
└── _internal/           # Private implementation details
    └── queries.py
"""
```

---

### Pattern: Interface Consistency Checklist

Before adding a new service method:

```markdown
## Interface Coherence Checklist

- [ ] Method name follows `verb_noun` convention (`create_order`, not `order_creation`)
- [ ] Parameters use domain types, not primitives (`CustomerId`, not `str`)
- [ ] Return type matches peer methods (`Result[T, E]` if others do)
- [ ] Error handling matches established pattern (raises vs returns)
- [ ] Async/sync matches peer methods in same layer
```

---

## Anti-Patterns

### Anti-Pattern: The Synonym Trap

```python
# ❌ Same concept, multiple names
order.client_id      # Here it's "client"
order.customer_name  # Here it's "customer"
order.buyer_email    # Here it's "buyer"

# ✅ One concept, one name
order.customer_id
order.customer_name
order.customer_email
```

---

### Anti-Pattern: The Historical Layers

```python
# ❌ Codebase shows geological strata of different eras

# 2019 layer: raw SQL, no types
def get_user(user_id):
    return db.execute(f"SELECT * FROM users WHERE id = {user_id}")

# 2021 layer: SQLAlchemy, some types
def get_user(user_id: int) -> User:
    return session.query(User).filter_by(id=user_id).first()

# 2024 layer: async, repository pattern
async def get_user(user_id: UserId) -> User | None:
    return await user_repository.find_by_id(user_id)

# Result: Three different patterns coexist, team confused
```

---

### Anti-Pattern: The Abstraction Mixer

```python
# ❌ Mixing high-level workflow with low-level details
class OrderProcessor:
    async def process(self, order_data: dict) -> dict:
        # High-level: validation
        if not self._validator.validate(order_data):
            raise ValidationError()

        # Suddenly low-level: manual JSON parsing
        items = []
        for item in order_data.get("items", []):
            items.append({
                "sku": item["sku"],
                "qty": int(item.get("quantity", 1)),
                "price": float(item["price"]) * 100  # cents
            })

        # Back to high-level
        return await self._fulfillment.fulfill(items)
```

---

### Anti-Pattern: Convention Fragmentation

```python
# ❌ Multiple conventions without clear winner

# Convention A: snake_case methods
order_service.create_order()
order_service.update_order()

# Convention B: verb-only methods
payment_service.charge()
payment_service.refund()

# Convention C: handle_ prefix
notification_service.handle_send()
notification_service.handle_retry()

# Result: No predictability, every service is a surprise
```

---

## Coherence Metrics

Track coherence through automated checks:

| Metric | Target | Tool |
|--------|--------|------|
| Naming convention compliance | 100% | Custom linter |
| Pattern adoption rate | >95% | Architecture tests |
| Glossary term violations | 0 | Grep hooks |
| Module structure deviation | 0 | Directory validator |
| Mixed abstraction warnings | 0 | Code review checklist |

---

## Quick Reference Card

```
┌─────────────────────────────────────────────────────────┐
│                  COHERENCE CHECKLIST                    │
├─────────────────────────────────────────────────────────┤
│ □ Using glossary terms consistently?                    │
│ □ Pattern matches existing similar code?                │
│ □ Module structure mirrors peer modules?                │
│ □ Abstraction level uniform within component?           │
│ □ Error handling follows established strategy?          │
│ □ Naming convention followed exactly?                   │
│ □ No new convention without migration plan?             │
│ □ Cross-context communication uses ACL?                 │
└─────────────────────────────────────────────────────────┘
```

---

*Coherence is not achieved by accident—it requires discipline, vigilance, and the willingness to refactor today's code to match tomorrow's patterns.*
