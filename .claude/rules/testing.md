---
paths:

- '**/tests/**/*.py'
- '**/test_*.py'
- '**/*_test.py'
---

# Python Testing Standards

Rules for writing reliable, maintainable tests that validate behavior without coupling to implementation.

## Standards

### MUST

1. **Follow AAA structure** with visual separation: Arrange → Act → Assert
2. **Name tests descriptively:** `test_<action>_<expected_outcome>` or `test_<action>_<condition>`
3. **Assert specific behavioral outcomes** (state changes, return values, raised exceptions)
4. **Use `match=` parameter** in `pytest.raises()` for exception validation
5. **Create test data via factories** — one fresh fixture per test
6. **Use transaction rollback** for database tests
7. **Test both success AND failure paths** for each behavior
8. **Mock only at external boundaries** (HTTP, databases, queues, file systems)

### NEVER

1. **Test private methods** (`_method`) — test through public interface only
2. **Share mutable state** between tests (class attributes, module globals)
3. **Write empty tests** or tests with only `assert True` / `assert result`
4. **Create test interdependencies** — every test must pass in isolation
5. **Mock your own code** — mock external services, not internal collaborators
6. **Use vague names:** `test_order()`, `test_it_works()`, `test_process_1()`
7. **Test multiple concepts** in a single test function

## Conditional Rules

**WHEN** testing exceptions **THEN** always include match string:

```python
with pytest.raises(ValueError, match="Discount cannot be negative"):
    order.apply_discount(percent=-5)
```

**WHEN** asserting timestamps **THEN** use `<=` against `datetime.now(UTC)`:

```python
assert order.completed_at <= datetime.now(UTC)
```

**WHEN** a refactor breaks your test but not your behavior **THEN** your test is wrong — rewrite it.

**WHEN** needing test data **THEN** use factory functions, not inline construction:

```python
# Use factories
order = order_factory(subtotal=Decimal("100.00"))
```

**WHEN** mocking more than 2 collaborators **THEN** refactor — the unit under test has too many dependencies.

## Patterns

### ✅ Correct: Behavior-Focused Test

```python
def test_applies_percentage_discount(self, order_factory):
    # Arrange
    order = order_factory(subtotal=Decimal("100.00"))

    # Act
    order.apply_discount(percent=10)

    # Assert
    assert order.total == Decimal("90.00")
```

### ✅ Correct: Exception with Match

```python
def test_rejects_negative_discount(order_factory):
    order = order_factory(subtotal=Decimal("100.00"))

    with pytest.raises(ValueError, match="Discount cannot be negative"):
        order.apply_discount(percent=-5)
```

### ✅ Correct: Independent Tests

```python
def test_complete_order_sets_status(order_factory):
    order = order_factory.create()

    complete_order(order.id)

    assert get_order(order.id).status == "completed"
```

## Anti-Patterns

### ❌ Testing Implementation Details

```python
# WRONG: Testing private methods
def test_calculate_internal_discount_factor():
    order = Order()
    assert order._calculate_discount_factor(10) == 0.9
```

**Why:** Breaks on refactor. Test the public interface instead.

### ❌ Test Interdependencies

```python
# WRONG: Tests depend on shared state
class TestOrderFlow:
    order_id = None

    def test_create_order(self):
        TestOrderFlow.order_id = create_order()

    def test_complete_order(self):
        complete_order(TestOrderFlow.order_id)  # Fails if run alone
```

**Why:** Violates isolation. Each test must be independently executable.

### ❌ Weak Assertions

```python
# WRONG: No meaningful assertion
def test_process_order():
    order = Order()
    order.process()  # No assertion!


# WRONG: Truthiness check
def test_order_valid():
    assert order.validate()  # What does True mean?
```

**Why:** Provides no behavioral guarantee. Assert specific state changes.

### ❌ Over-Mocking

```python
# WRONG: Mocking internal code
def test_order_total(mocker):
    mocker.patch.object(Order, 'get_items', return_value=[...])
    mocker.patch.object(Order, 'get_tax_rate', return_value=0.1)
    mocker.patch.object(Order, 'get_discount', return_value=5)
    # You're testing mocks, not code
```

**Why:** Tests become tautological. Use real objects; mock only external boundaries.

### ❌ Multiple Concepts Per Test

```python
# WRONG: Testing add, complete, AND cancel
def test_order_operations(order):
    order.add_item(item)
    assert len(order.items) == 1
    order.complete()
    assert order.status == "completed"
    order.cancel()
    assert order.status == "cancelled"
```

**Why:** Violates single responsibility. Split into focused tests.

## Pre-Commit Checklist

- [ ] No private method testing (`_method`)
- [ ] No shared mutable state between tests
- [ ] Every test has meaningful assertions
- [ ] Mocks only at external boundaries
- [ ] Error cases covered
- [ ] Descriptive test names
- [ ] One concept per test
- [ ] AAA structure with clear separation
