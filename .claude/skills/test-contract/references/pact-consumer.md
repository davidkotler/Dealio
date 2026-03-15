# Pact Python v3: Consumer Testing Guide

> Read this when writing consumer-side Pact contract tests.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Consumer Test Structure](#consumer-test-structure)
3. [Pytest Fixtures](#pytest-fixtures)
4. [Matchers Reference](#matchers-reference)
5. [Generators Reference](#generators-reference)
6. [Composing Matchers and Generators](#composing-matchers-and-generators)
7. [Multi-Interaction Testing](#multi-interaction-testing)
8. [Multiple Providers](#multiple-providers)
9. [Error Response Contracts](#error-response-contracts)
10. [Consumer Best Practices](#consumer-best-practices)
11. [Anti-Patterns](#anti-patterns)

---

## Architecture Overview

Pact Python v3 (current: 3.2.1) uses direct Rust FFI bindings for fast execution
and full V3/V4 specification support. The `pact` namespace provides `Pact`, `Verifier`,
`match`, and `generate` modules. Pre-built wheels are available for Linux, macOS, and
Windows. Default specification is **V4**.

---

## Consumer Test Structure

The consumer test exercises your **real API client code** against a Pact mock server.
The mock validates requests match declared interactions and returns canned responses.

```python
from pathlib import Path
from pact import Pact, match

PACT_DIR = Path(__file__).parent.parent / "pacts"


@pytest.fixture(scope="module")
def pact():
    pact = Pact("my-consumer", "my-provider")
    yield pact
    pact.write_file(PACT_DIR, overwrite=True)


def test_get_existing_user(pact: Pact) -> None:
    """Verify the consumer correctly handles a found user."""
    expected_response = {
        "id": match.int(123),
        "name": match.str("Alice"),
        "created_on": match.datetime(),
    }

    (
        pact
        .upon_receiving("a request for user 123")
        .given("user 123 exists", id=123, name="Alice")
        .with_request("GET", "/users/123")
        .will_respond_with(200)
        .with_body(expected_response, content_type="application/json")
    )

    with pact.serve() as srv:
        client = UserClient(str(srv.url))
        user = client.get_user(123)
        assert user.id == 123
        assert user.name == "Alice"
```

Critical rules:
- **Always test your actual client code** (e.g., `UserClient`), never raw `requests.get()`
- **Use `pact.serve()` as context manager** — mock validates all interactions were exercised on exit
- **Write pact file in fixture teardown** via `pact.write_file()`, not inside individual tests
- **One `upon_receiving` per logical interaction** — descriptions must be unique within a pact

---

## Pytest Fixtures

### Shared conftest.py

```python
# tests/conftest.py
import pact_ffi
import pytest


@pytest.fixture(autouse=True, scope="session")
def pact_logging():
    """Configure Pact FFI logging for debugging."""
    pact_ffi.log_to_stderr("INFO")
    # Options: "TRACE", "DEBUG", "INFO", "WARN", "ERROR", "NONE"
```

### Consumer pact fixture

```python
# tests/contract/consumer/conftest.py
from pathlib import Path
from pact import Pact
import pytest

PACT_DIR = Path(__file__).parent.parent.parent / "pacts"


@pytest.fixture(scope="module")
def pact():
    """Shared Pact instance for consumer tests.

    Scope is 'module' so all tests in the module share
    one pact and one output file.
    """
    pact = Pact("my-consumer", "my-provider").with_specification("V4")
    yield pact
    pact.write_file(PACT_DIR, overwrite=True)
```

### Pytest markers

```toml
# pyproject.toml
[tool.pytest.ini_options]
markers = [
    "consumer: Consumer contract tests",
    "provider: Provider verification tests",
]
```

Run selectively: `pytest -m consumer` or `pytest -m provider`.

---

## Matchers Reference

Matchers validate data **structure and type** rather than exact values, making contracts
resilient to legitimate provider changes.

| Matcher | Purpose | Example |
|---------|---------|---------|
| `match.int(value)` | Integer type | `match.int(123)` |
| `match.str(value)` | String type | `match.str("Alice")` |
| `match.bool(value)` | Boolean type | `match.bool(True)` |
| `match.float(value)` | Float/decimal type | `match.float(3.14)` |
| `match.number(value)` | Any number (int or float) | `match.number(98.5)` |
| `match.like(value)` | Type-based (any structure) | `match.like({"key": "val"})` |
| `match.regex(value, regex=...)` | Regex pattern | `match.regex("2024-01-15", regex=r"\d{4}-\d{2}-\d{2}")` |
| `match.each_like(value, min=...)` | Array elements match | `match.each_like({"id": 1}, min=1)` |
| `match.array_containing(variants)` | Array contains items | `match.array_containing([match.str("a")])` |
| `match.uuid(value)` | UUID format | `match.uuid("abc-123...")` |
| `match.date(value)` | Date string | `match.date("1990-05-20")` |
| `match.time(value)` | Time string | `match.time("14:30:00")` |
| `match.datetime(value)` | Datetime string | `match.datetime("2024-01-15T10:30:00Z")` |
| `match.include(value)` | String contains | `match.include("substring")` |
| `match.each_key(...)` / `match.each_value(...)` | Map key/value matching | For validating map structures |
| `match.int(25, min=0, max=150)` | Constrained integer | Integer within range |

### Matcher best practices

- **Default to type matchers** for most fields
- **Use regex for constrained strings** (email, phone, status enums)
- **Prefer `each_like` over exact arrays** — define shape of one element
- **Avoid overly loose matchers** — a matcher accepting anything provides no contract value

---

## Generators Reference

Generators produce **dynamic values** during provider verification, so tests don't break
on timestamps, UUIDs, or other non-deterministic data.

| Generator | Purpose |
|-----------|---------|
| `generate.int(min=..., max=...)` | Random integer in range |
| `generate.uuid(format=...)` | Random UUID |
| `generate.datetime(format)` | Current datetime |
| `generate.regex(pattern)` | String from regex pattern |
| `generate.provider_state(expression)` | Value injected from provider state |
| `generate.mock_server_url(...)` | URL pointing to mock server |
| `generate.bool()` | Random boolean |

---

## Composing Matchers and Generators

Matchers and generators compose naturally for complex response structures:

```python
from pact import match, generate

response_body = {
    "users": match.each_like({
        "id": generate.int(min=100000, max=999999),
        "name": match.str("Alice"),
        "email": match.regex("a@b.com", regex=r".+@.+\..+"),
        "verification_token": generate.uuid(),
        "created_at": generate.datetime("%Y-%m-%dT%H:%M:%S%z"),
    }, min=1)
}
```

### Provider state injection

Provider states can inject dynamic values back into interactions:

```python
from pact import generate, match

(
    pact
    .upon_receiving("a request for the latest order")
    .given("an order exists", order_id="abc-123")
    .with_request("GET", match.regex(
        "/orders/abc-123",
        regex=r"/orders/.+"
    ))
    .will_respond_with(200)
    .with_body({
        "id": generate.provider_state("${order_id}"),
        "total": match.number(99.99),
    })
)
```

---

## Multi-Interaction Testing

Test complex workflows involving sequential requests within a single test.
All defined interactions **must** be exercised for the test to pass.

```python
def test_async_task_workflow(pact: Pact) -> None:
    """Test a complete create -> poll -> retrieve workflow."""

    (
        pact.upon_receiving("a request to create a task")
        .with_request("POST", "/tasks", body={"type": "report"})
        .will_respond_with(202)
        .with_header("Location", "/tasks/1/status")
    )

    (
        pact.upon_receiving("a request to check task status")
        .with_request("GET", "/tasks/1/status")
        .will_respond_with(200)
        .with_body({"status": "completed", "result_url": "/tasks/1/result"})
    )

    (
        pact.upon_receiving("a request to get task result")
        .with_request("GET", "/tasks/1/result")
        .will_respond_with(200)
        .with_body({"result": match.str("Report data")})
    )

    with pact.serve() as srv:
        client = TaskClient(str(srv.url))
        result = client.run_task_and_wait("report")
        assert result is not None
```

---

## Multiple Providers

When a consumer talks to multiple providers, create separate pact fixtures:

```python
@pytest.fixture(scope="module")
def user_pact():
    pact = Pact("my-service", "user-provider")
    yield pact
    pact.write_file(PACT_DIR)


@pytest.fixture(scope="module")
def billing_pact():
    pact = Pact("my-service", "billing-provider")
    yield pact
    pact.write_file(PACT_DIR)


def test_user_and_billing(user_pact, billing_pact):
    (
        user_pact
        .upon_receiving("get user for billing")
        .given("user 1 exists")
        .with_request("GET", "/users/1")
        .will_respond_with(200)
        .with_body({"id": match.int(1), "name": match.str("Alice")})
    )

    (
        billing_pact
        .upon_receiving("get invoice for user")
        .given("user 1 has invoices")
        .with_request("GET", "/invoices?user_id=1")
        .will_respond_with(200)
        .with_body({"invoices": match.each_like({"amount": match.number(100)})})
    )

    with user_pact.serve() as user_srv, billing_pact.serve() as billing_srv:
        client = MyClient(
            user_url=str(user_srv.url),
            billing_url=str(billing_srv.url),
        )
        result = client.get_user_with_billing(1)
        assert result.invoices is not None
```

---

## Error Response Contracts

Always test error scenarios your consumer handles:

```python
def test_get_nonexistent_user(pact: Pact) -> None:
    """Verify the consumer correctly handles a 404."""
    (
        pact
        .upon_receiving("a request for a non-existent user")
        .given("user 999 does not exist")
        .with_request("GET", "/users/999")
        .will_respond_with(404)
    )

    with pact.serve() as srv:
        client = UserClient(str(srv.url))
        with pytest.raises(requests.HTTPError):
            client.get_user(999)
```

---

## Consumer Best Practices

1. **Exercise real consumer code** — the single most important practice
2. **Use matchers everywhere** — hardcoded values create brittle contracts
3. **Test only what the consumer uses** — omit unused fields
4. **Test error scenarios** — include 4xx and 5xx the consumer must handle
5. **Avoid random data** — Pact Broker uses content hashing for duplicate detection
6. **Keep contracts minimal** — only specify fields/headers the consumer depends on

---

## Anti-Patterns

### Using raw HTTP client in tests

```python
# WRONG: Tests requests library, not your client code
with pact.serve() as srv:
    response = requests.get(f"{srv.url}/users/123")  # BAD

# CORRECT: Tests your actual client
with pact.serve() as srv:
    client = UserClient(str(srv.url))  # GOOD
    user = client.get_user(123)
```

### Over-specifying contracts

```python
# WRONG: Exact values — brittle
response = {"id": 42, "name": "Alice Smith", "created_at": "2024-01-15T10:30:00Z"}

# CORRECT: Type matchers — resilient
response = {
    "id": match.int(42),
    "name": match.str("Alice Smith"),
    "created_at": match.datetime(),
}
```

### Testing provider business logic

Pact tests verify **interface shape** (request/response formats, status codes, headers),
not provider business logic. The guiding question: "If I omit this scenario, what bug in
the consumer or what misunderstanding about the API might be missed?"
