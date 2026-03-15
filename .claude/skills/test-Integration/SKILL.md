---
name: test-integration
version: 1.0.0
description: |
  Write integration tests that verify component interactions at real system boundaries.
  Use when testing repository persistence, HTTP client behavior, AWS service integration,
  database queries, API endpoints, or external service communication.
  Relevant for Python backend testing, SQLAlchemy repositories, FastAPI routes, httpx clients.
---

# Integration Testing

> Verify component interactions at real boundaries with isolated, reproducible tests.

## Quick Reference

| Aspect | Details |
|--------|---------|
| **Invokes** | `test/unit` (for extracted pure logic) |
| **Invoked By** | `implement/python`, `implement/api`, `implement/database` |
| **Key Tools** | Write, Edit, Bash(pytest) |

---

## Decision Tree

```
Code Change Detected
│
├─► New repository method?
│     └─► WRITE: Repository persistence test
│
├─► New external API call?
│     └─► WRITE: HTTP client test with respx
│
├─► New AWS service usage?
│     └─► WRITE: Moto-mocked service test
│
├─► Modified query logic?
│     └─► UPDATE: Assertions + edge cases
│
├─► Refactored internals (same behavior)?
│     └─► NO CHANGE: Existing tests must pass
│
└─► Changed external contract?
      └─► UPDATE: Mock responses + verify handling
```

---

## Core Workflow

1. **Identify Boundary**: DB? HTTP? AWS? Redis?
2. **Choose Isolation**: Transaction rollback (DB), respx (HTTP), moto (AWS)
3. **Generate Data**: Use factories, never hardcode
4. **Write Test**: AAA pattern with clear separation
5. **Assert State**: Query back persisted data, verify observable behavior
6. **Test Failures**: Timeout, 404, 409, 5xx scenarios
7. **Verify Independence**: `pytest path/to/test.py::test_name` passes alone

---

## Boundary Classification

### REAL Infrastructure (Use Fixtures)

| Boundary | Isolation | Fixture |
|----------|-----------|---------|
| Database | Transaction rollback | `db_session` |
| FastAPI | TestClient + DI override | `api_client` |
| Redis | Flush after test | `redis_client` |

### MOCKED Infrastructure (No Real Connection)

| Boundary | Library | Decorator |
|----------|---------|-----------|
| AWS S3/SQS/SNS | `moto` | `@mock_aws` |
| HTTP APIs | `respx` | `@respx.mock` |
| Time | `freezegun` | `@freeze_time()` |

---

## Standards

### MUST

1. **Rollback every DB test** — No pollution, no cleanup code
2. **Use factories for all test data** — Never hardcode entity construction
3. **Assert on persisted state** — Query back and verify, don't trust returns
4. **Test failure modes** — Timeouts, 5xx, constraint violations, not-found
5. **Mock at HTTP boundary** — Use `respx`, not internal service patches
6. **Scope engine to session** — Create tables once, not per test
7. **Use `@respx.mock` decorator** — Not context managers for HTTP mocking

### NEVER

8. **Mock your own repository** — Let it hit real DB with rollback
9. **Share mutable state between tests** — No class attributes, no module globals
10. **Trust return values alone** — Always query back persisted state
11. **Hardcode IDs or timestamps** — Use factories and time freezing
12. **Skip transaction rollback** — Every test leaves DB unchanged
13. **Test implementation details** — Query structure changes shouldn't break tests

---

## Conditional Rules

**WHEN** testing database persistence **THEN** use transaction rollback fixture:
```python
def test_saves_order(db_session, order_factory):
    order = order_factory.build()
    repo = OrderRepository(db_session)
    repo.save(order)
    db_session.flush()

    retrieved = db_session.get(Order, order.id)
    assert retrieved.status == order.status
```

**WHEN** testing HTTP client behavior **THEN** use `@respx.mock` with explicit routes:
```python
@respx.mock
def test_retries_on_503():
    route = respx.post("https://api.example.com/charge")
    route.side_effect = [httpx.Response(503), httpx.Response(200, json={"id": "tx_1"})]

    result = PaymentClient().charge(100)

    assert result.id == "tx_1"
    assert route.call_count == 2
```

**WHEN** testing AWS services **THEN** use `@mock_aws` and create resources in Arrange:
```python
@mock_aws
def test_uploads_to_s3():
    s3 = boto3.client("s3", region_name="us-east-1")
    s3.create_bucket(Bucket="test-bucket")

    FileUploader(bucket="test-bucket").upload(b"data", "file.txt")

    obj = s3.get_object(Bucket="test-bucket", Key="file.txt")
    assert obj["Body"].read() == b"data"
```

**WHEN** testing error handling **THEN** verify graceful degradation:
```python
@respx.mock
def test_handles_timeout():
    respx.post("https://api.example.com/resource").mock(
        side_effect=httpx.TimeoutException("timeout")
    )

    result = ExternalService().create_resource({"key": "value"})

    assert result.status == OperationStatus.FAILED
    assert "timeout" in result.error.lower()
```

**WHEN** testing API endpoints **THEN** use TestClient with DI override:
```python
def test_get_order_returns_200(api_client, order_factory, db_session):
    order = order_factory.build()
    db_session.add(order)
    db_session.flush()

    response = api_client.get(f"/orders/{order.id}")

    assert response.status_code == 200
    assert response.json()["id"] == str(order.id)
```

---

## Fixture Patterns

### Database Session (Transaction Rollback)

```python
@pytest.fixture(scope="session")
def db_engine():
    engine = create_engine(TEST_DATABASE_URL)
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)

@pytest.fixture
def db_session(db_engine):
    connection = db_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)
    yield session
    session.close()
    transaction.rollback()
    connection.close()
```

### API Client (FastAPI TestClient)

```python
@pytest.fixture
def api_client(db_session):
    app.dependency_overrides[get_session] = lambda: db_session
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()
```

---

## Anti-Patterns

### ❌ Mocking Own Repository

```python
# WRONG: This is a unit test in disguise
def test_order_service(mocker, db_session):
    mocker.patch.object(OrderRepository, 'save')  # ❌
    service = OrderService(db_session)
    service.create_order(...)
```

**Fix:** Let the repository hit real DB with transaction rollback.

### ❌ No Persistence Verification

```python
# WRONG: Only checks return value
def test_order_saved(db_session, order):
    result = OrderRepository(db_session).save(order)
    assert result.id is not None  # ❌ Trusting return
```

**Fix:** Query back and verify state:
```python
def test_order_saved(db_session, order_factory):
    order = order_factory.build()
    OrderRepository(db_session).save(order)
    db_session.flush()

    retrieved = db_session.get(Order, order.id)
    assert retrieved.status == order.status  # ✅
```

### ❌ Shared Test State

```python
# WRONG: Tests depend on each other
class TestOrderFlow:
    order_id = None  # ❌

    def test_create(self, db_session):
        TestOrderFlow.order_id = create_order(db_session)
```

**Fix:** Each test creates own data via factories.

---

## Error Case Checklist

| Scenario | HTTP | Database | AWS |
|----------|------|----------|-----|
| Timeout | `httpx.TimeoutException` | Connection timeout | `ClientError` |
| Not Found | 404 response | `None` from query | `NoSuchKey` |
| Conflict | 409 response | `IntegrityError` | `ConditionalCheckFailed` |
| Rate Limit | 429 response | N/A | `ThrottlingException` |
| Server Error | 5xx response | Connection error | `ServiceException` |

---

## Skill Chaining

| Condition | Invoke | Handoff Context |
|-----------|--------|-----------------|
| Complex query logic extracted | `test/unit` | Pure function, inputs/outputs |
| Schema mismatch found | `implement/database` | Table, column issue |
| Repository pattern needed | `implement/python` | Entity, required operations |

---

## Quality Gates

- [ ] All tests pass in isolation (`pytest <file>::<test_name>`)
- [ ] All DB tests use transaction rollback
- [ ] Factories generate all test data
- [ ] External boundaries use appropriate mocks (respx, moto)
- [ ] Error cases tested (timeout, not-found, conflict)
- [ ] Assertions verify persisted/observable state
- [ ] Test names follow `test_<action>_<outcome>` pattern
- [ ] No shared mutable state between tests

---

## Directory Structure

```
tests/
├── conftest.py              # db_engine, db_session, factories
└── integration/
    ├── conftest.py          # api_client, integration fixtures
    ├── repositories/
    │   └── test_order_repository.py
    ├── clients/
    │   └── test_payment_client.py
    └── services/
        └── test_order_service.py
```

---

## Deep References

- **[../unit/SKILL.md](../unit/SKILL.md)**: Unit testing for pure functions
