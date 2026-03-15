---
name: test-e2e
version: 1.0.0
description: |
  Write end-to-end tests that validate complete user journeys through the real system.
  Use when testing critical paths, user flows, API workflows, or after implementing features.
  Relevant for Python backend validation, FastAPI applications, FastStream Applications, full-stack integration.

---

# End-to-End Testing

> Validate complete user journeys through the real, running system.

## Quick Reference

| Aspect | Details |
|--------|---------|
| **Invokes** | `test/contract` (API boundaries) |
| **Invoked By** | `implement/python`, `implement/api` |
| **Location** | `tests/e2e/` |

---

## Core Workflow

1. **Identify**: Critical user journey to validate
2. **Setup**: Infrastructure via fixtures/TestContainers
3. **Seed**: Test data using factories
4. **Execute**: Flow through public interfaces (API/CLI)
5. **Assert**: Observable outcomes (responses, DB state, events)
6. **Chain**: API boundaries → invoke `test/contract`

---

## Decision Tree

```
Task Completed
├─► New user-facing feature? → E2E for happy path + critical failure
├─► Bug fix in user flow? → E2E reproducing scenario
├─► API endpoint change? → E2E test + chain → test/contract
├─► Async workflow? → E2E with polling assertions
└─► Internal refactor? → Verify existing E2E passes (no new tests)
```

---

## Standards

### MUST

1. **Test through public interfaces only** — HTTP, CLI, message queues
2. **Use real infrastructure** — Real DB, cache, queue via TestContainers
3. **One user journey per test** — Complete flow, single responsibility
4. **Seed data via factories** — No hardcoded test data
5. **Assert observable outcomes** — Responses, DB state, published events
6. **Isolate tests completely** — Independent, transaction rollback
7. **Name as user stories** — `test_user_can_<action>_when_<condition>`

### NEVER

8. **Mock internal services** — E2E exercises the real system
9. **Test implementation details** — No assertions on internal calls
10. **Share state between tests** — No class variables, no test ordering
11. **Use `time.sleep()`** — Poll with timeout for async operations
12. **Write E2E for every edge case** — Reserve for critical paths only
13. **Hardcode environment values** — Use configuration/fixtures

---

## Conditional Rules

**WHEN** testing async workflows **THEN** poll with timeout:
```python
await poll_until(lambda: order.status == "processed", timeout=10.0)
```

**WHEN** external third-party service needed **THEN** mock at HTTP boundary only:
```python
respx.post("https://api.stripe.com/v1/charges").respond(json={"id": "ch_test"})
```

**WHEN** testing auth flows **THEN** create real tokens, don't bypass:
```python
token = await auth_service.create_token(user)
response = await client.get("/protected", headers={"Authorization": f"Bearer {token}"})
```

---

## Skill Chaining

| Condition | Invoke | Handoff |
|-----------|--------|---------|
| API endpoint tested | `test/contract` | Endpoint path, schema |
| New service boundary | `test/contract` | Consumer/provider |

---

## Patterns

### ✅ Complete User Journey

```python
@pytest.mark.e2e
async def test_user_can_complete_checkout(client, db_session, user_factory, product_factory):
    # Arrange
    user = user_factory.create(verified=True)
    product = product_factory.create(price=Decimal("99.99"), stock=10)

    # Act: Multi-step flow
    await client.post("/cart/items", json={"product_id": str(product.id), "quantity": 2}, headers=auth_header(user))
    response = await client.post("/cart/checkout", json={"payment_method": "card"}, headers=auth_header(user))

    # Assert: Observable outcomes
    assert response.status_code == 200
    order = await db_session.get(Order, response.json()["order_id"])
    assert order.status == OrderStatus.CONFIRMED
    assert order.total == Decimal("199.98")
```

### ✅ Async with Polling

```python
@pytest.mark.e2e
async def test_order_processes_async(client, db_session, order_factory):
    order = order_factory.create(status=OrderStatus.PENDING)

    response = await client.post(f"/orders/{order.id}/process")
    assert response.status_code == 202

    await poll_until(lambda: db_session.get(Order, order.id).status == "processed", timeout=10.0)
```

### ✅ Error Path

```python
@pytest.mark.e2e
async def test_checkout_fails_insufficient_stock(client, user_factory, product_factory):
    user = user_factory.create()
    product = product_factory.create(stock=1)

    await client.post("/cart/items", json={"product_id": str(product.id), "quantity": 5}, headers=auth_header(user))
    response = await client.post("/cart/checkout", headers=auth_header(user))

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "INSUFFICIENT_STOCK"
```

---

## Anti-Patterns

### ❌ Mocking Internal Services
```python
# WRONG: Defeats purpose of E2E
mocker.patch("app.services.inventory.check_stock", return_value=True)
```
**Fix:** Use real services; mock only external third-party APIs at HTTP boundary.

### ❌ Sleep Instead of Poll
```python
# WRONG: Slow, flaky
await asyncio.sleep(5)
assert order.status == "processed"
```
**Fix:** `await poll_until(condition, timeout=10.0)`

### ❌ Test Interdependencies
```python
# WRONG: test_b depends on test_a
class TestOrderFlow:
    order_id = None
    def test_a_create(self): TestOrderFlow.order_id = create_order()
    def test_b_process(self): process_order(TestOrderFlow.order_id)
```
**Fix:** Each test creates its own data.

### ❌ E2E for Edge Cases
```python
# WRONG: Use unit tests for validation edge cases
@pytest.mark.e2e
async def test_email_rejects_double_dots(): ...
```
**Fix:** E2E for critical paths; unit tests for edge cases.

---

## Fixtures

```python
# tests/e2e/conftest.py
@pytest.fixture(scope="session")
def postgres():
    with PostgresContainer("postgres:15") as pg:
        yield pg

@pytest.fixture
async def db_session(db_engine):
    async with AsyncSession(db_engine) as session:
        yield session
        await session.rollback()

@pytest.fixture
async def client(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
```

---

## Directory Structure

```
tests/e2e/
├── conftest.py           # Fixtures (client, db, factories)
├── test_checkout.py      # Checkout journey
├── test_user_signup.py   # Registration journey
└── helpers/
    ├── polling.py        # poll_until utility
    └── auth.py           # auth_header helper
```

---

## Quality Gates

- [ ] Tests run independently (`pytest tests/e2e/test_file.py::test_name`)
- [ ] No `time.sleep()` — polling for async
- [ ] No internal mocks — only third-party HTTP if needed
- [ ] User journey names (`test_user_can_...`)
- [ ] Factories for all test data
- [ ] Marked `@pytest.mark.e2e`

---

## Running

```bash
pytest tests/e2e/ -v -m e2e                    # All E2E
pytest tests/e2e/test_checkout.py -v           # Specific journey
pytest tests/e2e/ --cov=app                    # With coverage
```

---
