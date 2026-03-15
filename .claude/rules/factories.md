---
paths:

- '**/tests/**/*.py'
- '**/test_*.py'
- '**/*_test.py'
---

# Test Data Factories

Generate realistic, type-safe test data using Polyfactory, Faker, and Hypothesis.

## Standards

### MUST

1. Use Polyfactory for Pydantic models, dataclasses, and SQLAlchemy models
2. Use Faker for realistic primitive values (emails, names, addresses, dates)
3. Use Hypothesis for property-based testing on pure functions and validators
4. Define factories in `tests/factories/` with one file per domain aggregate
5. Export all factories from `tests/factories/__init__.py`
6. Expose factories as pytest fixtures in `tests/conftest.py`
7. Use `.build()` for in-memory objects; use `.create()` only when persistence required
8. Override only the attributes relevant to the test assertion
9. Use `@classmethod` field overrides in factories for Faker integration

### NEVER

10. Instantiate domain models directly in tests with hardcoded values
11. Use random/manual string generation when Faker provides a provider
12. Share mutable factory state across tests
13. Use Hypothesis for integration tests or tests with I/O
14. Create factories for DTOs or value objects that are trivial to construct

## When → Then

**WHEN** testing a Pydantic model or dataclass  
**THEN** create a `ModelFactory` subclass with `__model__` set to the target class

**WHEN** a field requires realistic format (email, phone, address, UUID)  
**THEN** override the field with a Faker provider via `@classmethod`

**WHEN** testing pure functions with invariants (parsers, validators, calculations)  
**THEN** use Hypothesis `@given` decorators with appropriate strategies

**WHEN** testing serialization/deserialization roundtrips  
**THEN** use Hypothesis to generate arbitrary valid inputs

**WHEN** a test needs nested objects with specific values  
**THEN** build nested factories explicitly and pass to parent factory

**WHEN** multiple tests need the same factory  
**THEN** expose the factory class as a pytest fixture in `conftest.py`

## Patterns

### Factory Definition

```python
# tests/factories/order.py
from polyfactory.factories.pydantic_factory import ModelFactory
from faker import Faker
from app.domain.order import Order, OrderItem

fake = Faker()

class OrderItemFactory(ModelFactory):
    __model__ = OrderItem

class OrderFactory(ModelFactory):
    __model__ = Order

    @classmethod
    def customer_email(cls) -> str:
        return fake.email()
```

### Factory Usage with Overrides

```python
def test_order_total_calculation(order_factory):
    order = order_factory.build(
        items=[
            OrderItemFactory.build(price=Decimal("10.00"), quantity=2),
            OrderItemFactory.build(price=Decimal("5.00"), quantity=1),
        ]
    )
    assert order.calculate_total() == Decimal("25.00")
```

### Fixture Pattern

```python
# tests/conftest.py
@pytest.fixture
def order_factory():
    return OrderFactory

@pytest.fixture
def faker_instance():
    return Faker()
```

### Hypothesis for Invariants

```python
from hypothesis import given, strategies as st

@given(
    subtotal=st.decimals(min_value=0, max_value=10000),
    discount_pct=st.decimals(min_value=0, max_value=100)
)
def test_discount_never_exceeds_subtotal(subtotal, discount_pct):
    order = Order(subtotal=subtotal)
    order.apply_discount(percent=discount_pct)
    assert order.total >= 0
```

## Anti-Patterns

### ❌ Hardcoded Test Data

```python
# BAD: Brittle, unclear which values matter
def test_order_creation():
    order = Order(
        id="ord_123",
        customer_id="cust_456",
        customer_email="test@test.com",
        items=[OrderItem(sku="ABC", price=Decimal("10"), quantity=1)]
    )
    assert order.is_valid()
```

### ✅ Factory with Minimal Overrides

```python
# GOOD: Only override what the test asserts
def test_order_is_valid_with_items(order_factory):
    order = order_factory.build(items=[OrderItemFactory.build()])
    assert order.is_valid()
```

### ❌ Manual Random Strings

```python
# BAD: Not realistic, no format validation
email = f"user{random.randint(1,1000)}@test.com"
```

### ✅ Faker Provider

```python
# GOOD: Realistic, consistent format
email = fake.email()
```

### ❌ Hypothesis for I/O

```python
# BAD: Hypothesis is for pure functions
@given(st.text())
async def test_save_user(name):
    await db.save(User(name=name))  # I/O in property test
```

## Directory Structure

```
tests/
├── conftest.py          # Factory fixtures
├── factories/
│   ├── __init__.py      # Export all factories
│   ├── order.py         # OrderFactory, OrderItemFactory
│   ├── user.py          # UserFactory
│   └── payment.py       # PaymentFactory
├── unit/
└── integration/
```

## Exceptions

- Trivial value objects (e.g., `Money(amount=100)`) may be constructed directly
- Test utilities and helpers do not require factories
- Hypothesis may use `pytest.mark.slow` for expensive property tests
