---
name: test-unit
version: 1.0.0
description: |
  Generate behavior-driven unit tests that survive refactoring and catch real bugs.
  Use when implementing Python features, validating code changes, creating test coverage,
  or when user requests tests, specs, or validation for Python code.
  Relevant for pytest, Polyfactory, test-driven development, post-implementation validation.

---

# Unit Testing

> Generate tests that validate behavior, not implementation—enabling fearless refactoring.

## Quick Reference

| Aspect | Details |
|--------|---------|
| **Invoked By** | `implement/python`, `implement/api`, `implement/pydantic` |
| **Invokes** | `review/tests` (when coverage gaps detected) |
| **Key Tools** | Write, Edit, Bash(pytest), Read |
| **Output** | `tests/unit/<module>/test_<name>.py` |

---

## Core Workflow

1. **Discover**: Identify changed/new files via context or `git diff --name-only`
2. **Analyze**: Map public interfaces—functions, methods, classes with their contracts
3. **Decide**: Classify each change → New tests | Update existing | Remove stale
4. **Generate**: Write tests following AAA pattern using factories
5. **Validate**: Run `pytest <test_file> -v` and ensure all pass
6. **Report**: Summarize coverage delta and test inventory

---

## Decision Tree

```
Code Change Detected
│
├─► New public function/method?
│   └──► Write new test file/cases
│
├─► Signature changed (params, return type)?
│   └──► Update arrangements and assertions
│
├─► Behavior changed (same signature)?
│   └──► Update expected outcomes only
│
├─► Function removed?
│   └──► Remove corresponding tests
│
└─► Internal refactor only?
    └──► Tests MUST NOT change
        └──► If tests break → tests were wrong, fix them
```

---

## Standards

### MUST

1. Follow **AAA structure** with blank line separation: Arrange → Act → Assert
2. Name tests: `test_<action>_<expected_outcome>` or `test_<action>_<condition>`
3. Use **factories** for test data—never hardcode model instantiation
4. Assert **specific behavioral outcomes**: state changes, return values, exceptions
5. Include `match=` parameter in `pytest.raises()` for exception validation
6. Test **one logical concept** per test function
7. Cover: happy path + edge cases + error cases + state changes
8. Mock only **external boundaries**: HTTP, databases, queues, time, file I/O

### NEVER

9. Test private methods (`_method`)—test through public interface
10. Share mutable state between tests (class attrs, module globals)
11. Write empty tests or use `assert result` / `assert True` as sole assertion
12. Create test interdependencies—each test must pass in isolation
13. Mock your own code—mock external services only
14. Use vague names: `test_order()`, `test_it_works()`, `test_1()`
15. Test multiple unrelated concepts in one test

---

## Conditional Rules

**WHEN** testing exceptions  
**THEN** always use match string:
```python
with pytest.raises(ValueError, match="cannot be negative"):
```

**WHEN** asserting timestamps  
**THEN** use `<=` against current time:
```python
assert order.completed_at <= datetime.now(UTC)
```

**WHEN** a refactor breaks tests but not behavior  
**THEN** the test was wrong—rewrite to test behavior, not implementation.

**WHEN** testing code with I/O dependencies  
**THEN** inject the dependency and mock at the boundary:
```python
def test_sends_notification(mocker, order_factory):
    mock_notify = mocker.patch("app.notifications.send")
    # ... test with mock
```

**WHEN** testing retry/failure behavior  
**THEN** use `side_effect` with sequences:
```python
mock_api.side_effect = [ConnectionError(), SuccessResponse()]
```

**WHEN** testing datetime-dependent logic  
**THEN** freeze time at usage site:
```python
mocker.patch("app.orders.datetime").now.return_value = frozen_time
```

**WHEN** multiple tests share setup  
**THEN** extract to pytest fixture in `conftest.py`.

**WHEN** testing pure functions with invariants  
**THEN** consider Hypothesis for property-based testing.

---

## Required Coverage Matrix

| Category | What to Test | Example Assertion |
|----------|--------------|-------------------|
| **Happy Path** | Normal input → expected output | `assert order.total == Decimal("25.00")` |
| **Edge Cases** | Boundaries, empty, limits | `assert result == Decimal("0.00")` |
| **Error Cases** | Invalid input → exception | `pytest.raises(ValueError, match=...)` |
| **State Changes** | Side effects on object | `assert order.status == COMPLETED` |

---

## Patterns

### ✅ Correct: AAA with Factory

```python
def test_applies_percentage_discount(order_factory):
    # Arrange
    order = order_factory.build(subtotal=Decimal("100.00"))

    # Act
    order.apply_discount(percent=10)

    # Assert
    assert order.total == Decimal("90.00")
```

### ✅ Correct: Exception Validation

```python
def test_rejects_negative_quantity(order_factory):
    order = order_factory.build()

    with pytest.raises(ValueError, match="cannot be negative"):
        order.add_item(sku="ABC", quantity=-1)
```

### ✅ Correct: External Service Mock

```python
def test_completion_charges_payment(mocker, order_factory):
    mock_gateway = mocker.patch("app.orders.service.payment_gateway.charge")
    mock_gateway.return_value = PaymentResult(success=True, txn_id="123")
    order = order_factory.build(total=Decimal("99.99"))

    order.complete()

    mock_gateway.assert_called_once_with(amount=order.total, customer_id=order.customer_id)
    assert order.status == OrderStatus.COMPLETED
```

### ✅ Correct: Parametrized Tests

```python
@pytest.mark.parametrize("discount,expected", [
    (0, Decimal("100.00")),
    (10, Decimal("90.00")),
    (100, Decimal("0.00")),
])
def test_discount_calculations(order_factory, discount, expected):
    order = order_factory.build(subtotal=Decimal("100.00"))
    order.apply_discount(percent=discount)
    assert order.total == expected
```

---

## Anti-Patterns

### ❌ Testing Private Methods

```python
# WRONG
def test_internal_factor(order):
    assert order._calculate_factor(10) == 0.9

# CORRECT: Test through public interface
def test_discount_reduces_total(order_factory):
    order = order_factory.build(subtotal=Decimal("100.00"))
    order.apply_discount(percent=10)
    assert order.total == Decimal("90.00")
```

### ❌ Over-Mocking

```python
# WRONG: Testing mocks, not code
def test_total(mocker):
    mocker.patch.object(Order, "get_items", return_value=[...])
    mocker.patch.object(Order, "get_tax", return_value=0.1)

# CORRECT: Real objects, mock only boundaries
def test_total(order_factory, item_factory):
    order = order_factory.build(items=[item_factory.build(price=100)])
    assert order.calculate_total() == Decimal("100.00")
```

### ❌ Weak Assertions

```python
# WRONG
def test_order(order_factory):
    order = order_factory.build()
    assert order  # Meaningless

# CORRECT
def test_order_initializes_pending(order_factory):
    order = order_factory.build()
    assert order.status == OrderStatus.PENDING
```

### ❌ Test Interdependency

```python
# WRONG: Second test depends on first
class TestFlow:
    order_id = None
    def test_create(self): TestFlow.order_id = create()
    def test_complete(self): complete(TestFlow.order_id)

# CORRECT: Independent
def test_complete_order(order_factory):
    order = order_factory.create()
    complete_order(order.id)
    assert get_order(order.id).status == COMPLETED
```

---

## File Structure

```
tests/
├── conftest.py           # Factory fixtures
├── factories/
│   ├── __init__.py
│   └── order.py          # OrderFactory, OrderItemFactory
└── unit/
    ├── conftest.py       # Unit-specific fixtures
    └── orders/
        ├── conftest.py   # Order-specific fixtures
        └── test_service.py
```

**Naming:** `src/orders/service.py` → `tests/unit/orders/test_service.py`

---

## Validation Commands

```bash
# Run single file
pytest tests/unit/orders/test_service.py -v

# Run with coverage
pytest tests/unit/ --cov=src --cov-report=term-missing

# Run failed tests only
pytest --lf -v
```

---

## Quality Gates

Before completing:

- [ ] Every test follows AAA with visual separation
- [ ] Names follow `test_<action>_<outcome>` pattern
- [ ] Factories used—no hardcoded model construction
- [ ] Mocks only at external boundaries
- [ ] Both success AND error paths covered
- [ ] Assertions are specific (no `assert result`)
- [ ] Each test verifies ONE concept
- [ ] No private method testing
- [ ] All tests pass: `pytest <file> -v`

---

## Output Format

```markdown
## Test Summary

| Action | File | Count |
|--------|------|-------|
| Created | `tests/unit/orders/test_service.py` | 5 new |
| Modified | `tests/unit/auth/test_tokens.py` | 2 updated |

### Test Inventory
- `test_applies_discount` — Happy path
- `test_rejects_negative_discount` — Error case
- `test_completion_updates_status` — State change

### Validation
✅ All tests passed
```
