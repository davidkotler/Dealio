# FastAPI Integration Testing Reference

> Test FastAPI routes at real HTTP boundaries with TestClient, dependency overrides, and transaction isolation.

---

## Client Selection

| Scenario | Client | Rationale |
|----------|--------|-----------|
| Sync endpoints, no async DB calls | `TestClient` | Simpler, runs in sync context |
| Async DB queries in test body | `httpx.AsyncClient` | Required for `await` in tests |
| WebSocket testing | `TestClient.websocket_connect()` | Built-in WebSocket support |
| Lifespan events required | `TestClient` as context manager | Triggers startup/shutdown |

```python
# Sync: TestClient (most common)
from fastapi.testclient import TestClient
client = TestClient(app)

# Async: httpx.AsyncClient with ASGITransport
from httpx import ASGITransport, AsyncClient
async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
    response = await ac.get("/")
```

---

## Standards

### MUST

1. **Use `TestClient` as context manager** when app has lifespan events
2. **Clear `dependency_overrides` after each test** — use `yield` fixtures with cleanup
3. **Override `get_db` dependency** to inject test session with rollback
4. **Assert on response status AND body** — status alone is insufficient
5. **Test both success and error paths** — 200, 201, 400, 401, 403, 404, 422
6. **Use factories for request payloads** — never hardcode test data inline
7. **Pass Pydantic models as `.model_dump()`** — TestClient expects dicts, not models
8. **Scope DB engine to session, session to function** — tables once, rollback per test

### NEVER

9. **Set `Content-Type: multipart/form-data` manually** — httpx sets boundary automatically
10. **Use `TestClient` inside `async def` tests** — use `httpx.AsyncClient` instead
11. **Share `TestClient` instances across test modules** — create per fixture
12. **Assert only `response.status_code`** — always verify response body/state
13. **Forget `base_url` with `AsyncClient`** — required for relative URLs to work
14. **Leave `dependency_overrides` populated** — causes test pollution

---

## Conditional Rules

**WHEN** testing routes with DB dependencies  
**THEN** override `get_db` with rollback session:

```python
@pytest.fixture
def client(db_session):
    def override_get_db():
        yield db_session
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
```

**WHEN** testing authenticated routes  
**THEN** override `get_current_user` with mock user:

```python
@pytest.fixture
def authenticated_client(client, user_factory, db_session):
    user = user_factory.create()
    db_session.flush()

    def override_get_current_user():
        return user

    app.dependency_overrides[get_current_user] = override_get_current_user
    yield client
    app.dependency_overrides.clear()
```

**WHEN** testing file uploads  
**THEN** use `files=` parameter with tuple format:

```python
def test_upload_file(client):
    content = b"file content here"
    response = client.post(
        "/upload",
        files={"file": ("filename.csv", content, "text/csv")},
        data={"description": "test file"},  # Form fields alongside
    )
    assert response.status_code == 201
```

**WHEN** testing WebSocket endpoints  
**THEN** use context manager with `websocket_connect`:

```python
def test_websocket_echo(client):
    with client.websocket_connect("/ws") as ws:
        ws.send_json({"message": "hello"})
        data = ws.receive_json()
        assert data["message"] == "hello"
```

**WHEN** testing async routes with async DB  
**THEN** use `AsyncClient` with `pytest.mark.anyio`:

```python
@pytest.fixture
def anyio_backend():
    return "asyncio"

@pytest.mark.anyio
async def test_async_route(async_client):
    response = await async_client.get("/async-endpoint")
    assert response.status_code == 200
```

**WHEN** app uses lifespan events  
**THEN** use `TestClient` as context manager OR `LifespanManager`:

```python
# Option 1: TestClient context manager
with TestClient(app) as client:
    response = client.get("/")

# Option 2: LifespanManager for AsyncClient
from asgi_lifespan import LifespanManager
async with LifespanManager(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/")
```

**WHEN** testing error responses (500s)  
**THEN** disable exception raising:

```python
client = TestClient(app, raise_server_exceptions=False)
response = client.get("/broken-endpoint")
assert response.status_code == 500
```

**WHEN** testing with custom headers  
**THEN** pass headers dict to request:

```python
def test_with_custom_headers(client):
    response = client.get(
        "/protected",
        headers={"X-Token": "secret-token", "X-Request-ID": "test-123"},
    )
    assert response.status_code == 200
```

---

## Fixture Patterns

### Database Session with Rollback

```python
@pytest.fixture(scope="session")
def db_engine():
    engine = create_engine(TEST_DATABASE_URL)
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def db_session(db_engine):
    connection = db_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()
```

### TestClient with Dependency Override

```python
@pytest.fixture(scope="function")
def client(db_session) -> Generator[TestClient, None, None]:
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
```

### Authenticated Client with Token

```python
@pytest.fixture
def auth_headers(user_factory, db_session) -> dict[str, str]:
    user = user_factory.create(password="testpass123")
    db_session.flush()
    token = create_access_token(data={"sub": user.email})
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def authenticated_client(client, auth_headers):
    client.headers.update(auth_headers)
    yield client
```

### AsyncClient Fixture

```python
@pytest.fixture
def anyio_backend():
    return "asyncio"

@pytest.fixture
async def async_client(db_session) -> AsyncGenerator[AsyncClient, None]:
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
```

---

## Request Patterns

### JSON Body

```python
def test_create_order(client, order_create_factory):
    payload = order_create_factory.build()
    response = client.post("/orders", json=payload.model_dump())
    assert response.status_code == 201
    assert response.json()["id"] is not None
```

### Query Parameters

```python
def test_list_orders_with_filters(client, order_factory, db_session):
    order_factory.create_batch(5, status="pending")
    db_session.flush()

    response = client.get("/orders", params={"status": "pending", "limit": 10})
    assert response.status_code == 200
    assert len(response.json()) == 5
```

### Path Parameters

```python
def test_get_order_by_id(client, order_factory, db_session):
    order = order_factory.create()
    db_session.flush()

    response = client.get(f"/orders/{order.id}")
    assert response.status_code == 200
    assert response.json()["id"] == str(order.id)
```

### Form Data

```python
def test_login(client, user_factory, db_session):
    user_factory.create(email="test@example.com", password="hashed_password")
    db_session.flush()

    response = client.post(
        "/auth/token",
        data={"username": "test@example.com", "password": "password123"},
    )
    assert response.status_code == 200
    assert "access_token" in response.json()
```

### File Upload with Form Data

```python
def test_upload_with_metadata(client):
    file_content = b"CSV,content,here"
    response = client.post(
        "/documents/upload",
        files={"file": ("data.csv", file_content, "text/csv")},
        data={"title": "My Document", "category": "reports"},
    )
    assert response.status_code == 201
    assert response.json()["filename"] == "data.csv"
```

---

## Assertion Patterns

### Status + Body + DB State

```python
def test_create_user_complete(client, db_session):
    response = client.post("/users", json={"email": "new@example.com", "name": "New User"})

    # Assert response
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "new@example.com"

    # Assert DB state
    db_session.expire_all()
    user = db_session.query(User).filter_by(email="new@example.com").first()
    assert user is not None
    assert user.name == "New User"
```

### Error Response Structure

```python
def test_validation_error_format(client):
    response = client.post("/users", json={"email": "invalid-email"})

    assert response.status_code == 422
    errors = response.json()["detail"]
    assert any(e["loc"] == ["body", "email"] for e in errors)
```

### List Response

```python
def test_list_pagination(client, order_factory, db_session):
    order_factory.create_batch(25)
    db_session.flush()

    response = client.get("/orders", params={"page": 1, "size": 10})

    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 10
    assert data["total"] == 25
    assert data["page"] == 1
```

---

## Anti-Patterns

### ❌ Setting Content-Type for Multipart

```python
# WRONG: Causes boundary error
response = client.post(
    "/upload",
    files={"file": ("test.csv", b"data")},
    headers={"Content-Type": "multipart/form-data"},  # ❌
)
```

**Fix:** Remove Content-Type header — httpx sets it automatically with boundary.

### ❌ Using TestClient in Async Test

```python
# WRONG: TestClient cannot be used in async context
@pytest.mark.anyio
async def test_async_route():
    client = TestClient(app)  # ❌
    response = client.get("/")
```

**Fix:** Use `httpx.AsyncClient` with `ASGITransport`.

### ❌ Forgetting to Clear Overrides

```python
# WRONG: Leaks overrides to next test
@pytest.fixture
def client():
    app.dependency_overrides[get_db] = lambda: test_db
    yield TestClient(app)
    # Missing: app.dependency_overrides.clear()  ❌
```

**Fix:** Always clear overrides in fixture teardown.

### ❌ Testing Private Route Without Auth Override

```python
# WRONG: Will always return 401
def test_protected_route(client):
    response = client.get("/protected")  # ❌ No auth
    assert response.status_code == 200
```

**Fix:** Override `get_current_user` or use `authenticated_client` fixture.

### ❌ Passing Pydantic Model Directly

```python
# WRONG: TestClient expects dict, not Pydantic model
payload = OrderCreate(item="test", quantity=1)
response = client.post("/orders", json=payload)  # ❌
```

**Fix:** Use `payload.model_dump()` or `payload.model_dump(mode="json")`.

### ❌ Missing base_url with AsyncClient

```python
# WRONG: Relative URLs fail without base_url
async with AsyncClient(transport=ASGITransport(app=app)) as ac:
    response = await ac.get("/users")  # ❌ Fails
```

**Fix:** Always provide `base_url="http://test"`.

---

## Error Testing Matrix

| Scenario | Expected Status | Test Pattern |
|----------|-----------------|--------------|
| Resource not found | 404 | `client.get(f"/items/{nonexistent_id}")` |
| Validation error | 422 | `client.post("/items", json={"invalid": "data"})` |
| Unauthenticated | 401 | Request without auth header |
| Unauthorized | 403 | Auth as user without required role |
| Duplicate resource | 409 | Create same unique resource twice |
| Server error | 500 | `TestClient(app, raise_server_exceptions=False)` |

---

## Header Patterns

```python
# Custom request headers
response = client.get("/resource", headers={"X-Request-ID": "test-123"})

# Cookie-based auth
client.cookies.set("session_id", "test-session")
response = client.get("/protected")

# Bearer token
response = client.get("/protected", headers={"Authorization": "Bearer test-token"})

# API key
response = client.get("/resource", headers={"X-API-Key": "secret-key"})
```

---

## WebSocket Testing

```python
def test_websocket_chat(client):
    with client.websocket_connect("/ws/chat/room1") as ws:
        # Send message
        ws.send_json({"type": "message", "content": "Hello"})

        # Receive response
        response = ws.receive_json()
        assert response["type"] == "message"
        assert response["content"] == "Hello"

        # Test multiple messages
        for i in range(3):
            ws.send_text(f"Message {i}")
            data = ws.receive_text()
            assert f"Message {i}" in data

def test_websocket_auth_required(client):
    with pytest.raises(WebSocketException):
        with client.websocket_connect("/ws/protected"):
            pass  # Should fail before reaching here
```

---

## Quality Gates

Before merging route integration tests:

- [ ] Every route has at least success + one error test
- [ ] All tests use `dependency_overrides` cleanup
- [ ] Response body assertions present (not just status)
- [ ] DB state verified after mutations
- [ ] Factories generate all request payloads
- [ ] Auth tests cover authenticated and unauthenticated paths
- [ ] Error response structure matches API contract
- [ ] No hardcoded IDs or magic strings
