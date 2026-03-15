---
paths:

- '**/tests/**/*.py'
- '**/test_*.py'
- '**/*_test.py'
---

# Mocking Rules

Mocks isolate code from external dependencies. Mock at system boundaries, never internal implementation.

## Standards

### MUST

1. Mock only external boundaries: HTTP services, databases, message queues, file system, third-party SDKs
2. Mock time-dependent operations (`datetime.now()`, `time.time()`) for deterministic tests
3. Verify mock interactions: arguments passed, call count, and resulting system state
4. Use `mocker.patch()` with the full import path where the dependency is *used*, not where it's defined
5. Provide realistic return values that match actual API contracts

### NEVER

6. Mock code in the same module or package under test
7. Mock pure functions or simple data transformations
8. Mock private methods or internal state (`_method`, `__attr`)
9. Mock return values you control—use factories instead
10. Create mocks more complex than the code they replace

## Conditional Rules

**WHEN** testing retry/failure behavior **THEN** use `side_effect` with sequences:

```python
mock_api.side_effect = [ConnectionError(), ConnectionError(), SuccessResponse(data="ok")]
```

**WHEN** mocking datetime **THEN** patch at the usage site and freeze to a known value:

```python
mocker.patch("app.services.order.datetime").now.return_value = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
```

**WHEN** testing code with injected dependencies **THEN** prefer fakes over mocks:

```python
# Prefer: Fake implementation
service = OrderService(payment=FakePaymentGateway())

# Avoid: Mock with manual setup
mock_payment = mocker.patch("app.payments.PaymentGateway")
```

**WHEN** the same mock setup repeats across tests **THEN** extract to a pytest fixture.

## Patterns

### External Service Mock

```python
def test_order_completion_charges_payment(mocker, order):
    mock_gateway = mocker.patch("app.orders.service.payment_gateway.charge")
    mock_gateway.return_value = PaymentResult(success=True, transaction_id="txn_123")

    order.complete()

    # Verify interaction
    mock_gateway.assert_called_once_with(amount=order.total, customer_id=order.customer_id)
    # Verify system state
    assert order.status == OrderStatus.COMPLETED
```

### Database Mock (Unit Tests Only)

```python
def test_user_lookup_returns_none_when_not_found(mocker):
    mock_repo = mocker.patch("app.users.service.user_repository")
    mock_repo.get_by_id.return_value = None

    result = user_service.find_user("missing-id")

    assert result is None
    mock_repo.get_by_id.assert_called_once_with("missing-id")
```

## Anti-Patterns

### ❌ Mocking Internal Implementation

```python
# WRONG: Breaks on refactor, tests implementation not behavior
def test_order_total(mocker, order):
    mocker.patch.object(order, "_calculate_subtotal", return_value=100)
    mocker.patch.object(order, "_apply_discounts", return_value=10)
```

**Fix:** Test the public `order.total` property with real data via factories.

### ❌ Over-Mocking (Testing Mocks)

```python
# WRONG: No real code executed—only verifying mock wiring
def test_order_total(mocker):
    mocker.patch.object(Order, "get_items", return_value=[mock_item])
    mocker.patch.object(Order, "get_tax_rate", return_value=Decimal("0.1"))
    mocker.patch.object(Order, "get_discount", return_value=Decimal("5"))
```

**Fix:** Mock only external calls; let internal logic execute.

### ❌ Mocking What You Control

```python
# WRONG: Use factory to create user with desired state
def test_user_greeting(mocker):
    mocker.patch.object(user, "get_full_name", return_value="John Doe")
```

**Fix:**

```python
def test_user_greeting(user_factory):
    user = user_factory.build(first_name="John", last_name="Doe")
    assert user.get_full_name() == "John Doe"
```

## Mock Assertion Checklist

Every mock interaction should verify:

1. **Arguments** — `assert_called_once_with(...)` or inspect `call_args`
2. **Call count** — `assert mock.call_count == N` for retry/batch scenarios
3. **System state** — Assert on object state changes, not just mock calls

```python
def test_notification_sent_on_order_completion(mocker, order):
    mock_notify = mocker.patch("app.orders.service.notifications.send")

    order.complete()

    mock_notify.assert_called_once_with(
        user_id=order.customer_id,
        message=f"Order {order.id} completed"
    )
    assert order.notification_sent_at is not None  # System state verification
```

## Exceptions

- **Integration tests**: Use real dependencies (databases, caches) with test containers
- **Contract tests**: Mock the consumer/provider, not the contract itself
- **E2E tests**: No mocks—test the full system
