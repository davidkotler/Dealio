---
name: test-contract
version: 2.1.0
description: |
  Validate API contracts between service consumers and providers using consumer-driven contract testing.
  Use when testing API boundaries, verifying OpenAPI/AsyncAPI compliance, checking backward compatibility,
  or implementing Pact/Schemathesis contract tests. Relevant for microservices, REST APIs, event handlers, async APIs.
---

# Contract Testing

> Validate API agreements between consumers and providers without full system integration.

## Quick Reference

| Aspect | Details |
|--------|---------|
| **Invokes** | `test/factories`, `implement/pydantic` |
| **Invoked By** | `implement/api`, `review/api` |
| **Key Tools** | Pact Python v3 (Rust FFI), Schemathesis, Hypothesis, jsonschema |
| **Pact Spec** | V4 (default), V3, V2 supported |

---

## Bundled References

Load these when you need deeper guidance on a specific area:

| Reference | When to Read | Path |
|-----------|-------------|------|
| **Pact Consumer Guide** | Writing consumer-side Pact tests, matchers, generators, fixtures | `references/pact-consumer.md` |
| **Pact Provider Guide** | Writing provider verification, state handlers, broker integration | `references/pact-provider.md` |
| **Pact Advanced Patterns** | Message pacts, plugins, GraphQL, CI/CD, breaking changes | `references/pact-advanced.md` |
| **Schemathesis Guide** | Schema-driven testing: CLI, Python API, pytest, config, checks, data generation | `references/schemathesis-guide.md` |
| **Schemathesis Advanced** | Stateful testing, hooks, auth, custom checks, serializers, CI/CD | `references/schemathesis-advanced.md` |

---

## Core Workflow

1. **Identify**: Locate API boundaries requiring contract validation
2. **Classify**: Determine contract type (consumer-driven, provider, schema, message)
3. **Locate**: Search `tests/contract/` for existing coverage
4. **Read reference**: Load the appropriate reference file for your contract type
5. **Implement**: Write contract test following patterns below
6. **Validate**: Run `pytest tests/contract/ -v`
7. **Chain**: Invoke `test/factories` for test data generation

---

## Decision Tree

```
API Boundary Detected
|
+--> Consumer needs specific response shape?
|    +--> Write CONSUMER contract (Pact v3)
|         Read: references/pact-consumer.md
|
+--> Provider exposes OpenAPI spec?
|    +--> Write SCHEMA contract (Schemathesis)
|         Read: references/schemathesis-guide.md
|
+--> Need stateful/workflow API testing?
|    +--> Write STATEFUL contract (Schemathesis state machine)
|         Read: references/schemathesis-advanced.md#stateful-testing
|
+--> Need custom hooks, auth, or CI/CD for schema tests?
|    +--> Read: references/schemathesis-advanced.md
|
+--> API versioning change?
|    +--> Write COMPATIBILITY contract
|
+--> Event/message contract (Kafka, SQS, RabbitMQ)?
|    +--> Write MESSAGE contract (Pact async)
|         Read: references/pact-advanced.md#message-pact-testing
|
+--> Provider verification needed?
|    +--> Write PROVIDER verification test
|         Read: references/pact-provider.md
|
+--> Internal service boundary?
     +--> SKIP (use integration tests)
```

---

## Standards

### MUST

1. **Test at API boundaries only** — HTTP endpoints, message queues, external SDKs
2. **Define explicit schemas** for request/response validation
3. **Version contracts** alongside API versions
4. **Use factories** for generating valid/invalid payloads
5. **Validate both success and error response shapes**
6. **Run contracts in CI** before integration tests
7. **Store Pact contracts** in a broker or `tests/contract/pacts/`
8. **Use Pact Python v3 API** — `Pact`, `Verifier`, `match`, `generate`

### NEVER

9. **Test internal implementation** — contracts are boundary-only
10. **Mock the contract itself** — mock consumer/provider, not the agreement
11. **Skip error response contracts** — 4xx/5xx shapes matter
12. **Couple to provider internals** — test observable API behavior
13. **Share state between contract tests** — each test is isolated
14. **Use contracts for business logic** — that's unit/integration territory
15. **Use exact values** when matchers exist — `match.int(42)` not `42`

---

## Pact v3 Essentials

### Essential Imports

```python
from pact import Pact, match, generate  # Consumer
from pact import Verifier               # Provider
import pact_ffi                         # Logging/debugging
```

### Consumer Test Pattern

```python
import pytest
from pathlib import Path
from pact import Pact, match

PACT_DIR = Path(__file__).parent.parent / "pacts"


@pytest.fixture(scope="module")
def pact():
    pact = Pact("my-consumer", "my-provider")
    yield pact
    pact.write_file(PACT_DIR, overwrite=True)


def test_get_user(pact: Pact) -> None:
    """Verify consumer handles found user correctly."""
    (
        pact
        .upon_receiving("a request for user 123")
        .given("user 123 exists", id=123, name="Alice")
        .with_request("GET", "/users/123")
        .will_respond_with(200)
        .with_body({
            "id": match.int(123),
            "name": match.str("Alice"),
            "email": match.regex("alice@example.com", regex=r".+@.+\..+"),
        }, content_type="application/json")
    )

    with pact.serve() as srv:
        client = UserClient(str(srv.url))
        user = client.get_user(123)
        assert user.id == 123
        assert user.name == "Alice"
```

For the full matchers/generators reference and advanced consumer patterns,
read `references/pact-consumer.md`.

### Provider Verification Pattern

```python
from pact import Verifier


def test_provider():
    verifier = (
        Verifier("my-provider")
        .add_transport(url="http://localhost:8080")
        .add_source("./pacts/")
        .state_handler({
            "user 123 exists": setup_user_exists,
            "no users exist": setup_no_users,
        }, teardown=True)
    )
    verifier.verify()
```

For state handler patterns, broker integration, and FastAPI/Flask setup,
read `references/pact-provider.md`.

---

## Conditional Rules

**WHEN** consumer requirements change **THEN** update consumer contract first, then verify provider:
```python
# Consumer defines what it needs — use matchers for flexibility
(
    pact
    .given("user exists", id=123)
    .upon_receiving("a request for user")
    .with_request("GET", "/users/123")
    .will_respond_with(200)
    .with_body({"id": match.int(123), "email": match.str("user@example.com")})
)
```

**WHEN** provider adds optional fields **THEN** existing contracts still pass (Pact's loose response matching ignores extra fields)

**WHEN** provider removes/renames fields **THEN** this is a BREAKING change — use expand-and-contract pattern (see `references/pact-advanced.md#breaking-changes`)

**WHEN** testing OpenAPI compliance **THEN** use Schemathesis for property-based schema testing (read `references/schemathesis-guide.md`):
```bash
# All checks, continue after failures to find all issues
schemathesis run http://localhost:8000/openapi.json --checks all --continue-on-failure
```

**WHEN** testing OpenAPI compliance for a FastAPI app **THEN** use direct ASGI testing (read `references/schemathesis-guide.md#pytest-integration`):
```python
import schemathesis

schema = schemathesis.openapi.from_asgi("/openapi.json", app)

@schema.parametrize()
def test_api(case):
    case.call_and_validate()
```

**WHEN** testing stateful API workflows (create→read→delete) **THEN** use Schemathesis stateful phase (read `references/schemathesis-advanced.md#stateful-testing`)

**WHEN** Schemathesis needs custom auth, hooks, or CI/CD integration **THEN** read `references/schemathesis-advanced.md`

**WHEN** testing async/event contracts **THEN** use Pact message pacts (see `references/pact-advanced.md#message-pact-testing`):
```python
(
    pact
    .upon_receiving("an order created event", "Async")
    .with_body(event_body, "application/json")
    .with_metadata({"kafka_topic": "orders"})
)
pact.verify(handler, "Async")
```

**WHEN** testing GraphQL **THEN** use standard HTTP POST to `/graphql` (see `references/pact-advanced.md#graphql-contract-testing`)

**WHEN** integrating with CI/CD **THEN** read `references/pact-advanced.md#cicd-integration` for pipeline patterns

---

## Skill Chaining

| Condition | Invoke | Handoff Context |
|-----------|--------|-----------------|
| Need test payloads | `test/factories` | Schema shape, edge cases needed |
| Complex response models | `implement/pydantic` | Field types, validation rules |
| After contracts pass | `test/integration` | Verified contract paths |

---

## Schema Validation Patterns

### Pattern: JSON Schema Validation

```python
import pytest
from jsonschema import validate

ORDER_RESPONSE_SCHEMA = {
    "type": "object",
    "required": ["id", "status", "items", "total"],
    "properties": {
        "id": {"type": "string", "format": "uuid"},
        "status": {"type": "string", "enum": ["pending", "paid", "shipped"]},
        "items": {"type": "array", "minItems": 1},
        "total": {"type": "string", "pattern": r"^\d+\.\d{2}$"},
    },
    "additionalProperties": False,
}

def test_order_response_matches_schema(api_client, order_factory):
    order = order_factory.create()
    response = api_client.get(f"/orders/{order.id}")
    validate(instance=response.json(), schema=ORDER_RESPONSE_SCHEMA)
```

### Pattern: Schemathesis Property-Based (v4.x API)

For full loader options, generation modes, and configuration, read `references/schemathesis-guide.md`.

```python
import schemathesis

# v4.x API: use schemathesis.openapi.from_url (not schemathesis.from_uri)
schema = schemathesis.openapi.from_url("http://localhost:8000/openapi.json")

@schema.parametrize()
def test_api_conforms_to_openapi(case):
    """Property-based: all endpoints match OpenAPI spec."""
    case.call_and_validate()


# For FastAPI apps — direct ASGI testing (no network overhead)
schema = schemathesis.openapi.from_asgi("/openapi.json", app)

@schema.parametrize()
def test_api_direct(case):
    case.call_and_validate()
```

For stateful testing, hooks, auth patterns, and CI/CD, read `references/schemathesis-advanced.md`.

### Pattern: Backward Compatibility

```python
def test_previous_consumer_works_with_new_provider(api_client):
    """Ensure new API still serves previous contract requirements."""
    previous_required_fields = {"id", "name", "email"}
    response = api_client.get("/users/123")
    response_fields = set(response.json().keys())
    assert previous_required_fields.issubset(response_fields)
```

---

## Anti-Patterns

### Using raw HTTP client in tests

```python
# WRONG: Tests requests library, not your client
with pact.serve() as srv:
    response = requests.get(f"{srv.url}/users/123")

# CORRECT: Tests your actual client
with pact.serve() as srv:
    client = UserClient(str(srv.url))
    user = client.get_user(123)
```

### Over-specifying contracts

```python
# WRONG: Exact values — brittle
body = {"id": 42, "name": "Alice", "created_at": "2024-01-15T10:30:00Z"}

# CORRECT: Type matchers — resilient
body = {
    "id": match.int(42),
    "name": match.str("Alice"),
    "created_at": match.datetime(),
}
```

### Testing provider business logic

```python
# WRONG: Asserting on calculation results
assert response.json()["discount"] == 15.0  # Business logic!

# CORRECT: Asserting on response shape
.with_body({"amount": match.number(29.99), "currency": match.str("USD")})
```

---

## Directory Structure

```
tests/contract/
+-- conftest.py                    # Shared fixtures (pact logging, paths)
+-- consumer/
|   +-- conftest.py                # Pact fixture for consumer
|   +-- test_user_service.py       # Consumer contracts
|   +-- test_order_service.py
+-- provider/
|   +-- conftest.py                # State handler fixtures
|   +-- test_verification.py       # Provider verification
+-- pacts/                         # Generated Pact JSON files
|   +-- my-consumer-my-provider.json
+-- schemas/                       # JSON schemas for validation
    +-- order_response.json
    +-- error_response.json
```

---

## Fixture Patterns

```python
# tests/contract/conftest.py
import pytest
import pact_ffi


@pytest.fixture(autouse=True, scope="session")
def pact_logging():
    pact_ffi.log_to_stderr("INFO")
```

```python
# tests/contract/consumer/conftest.py
from pathlib import Path
from pact import Pact
import pytest

PACT_DIR = Path(__file__).parent.parent / "pacts"


@pytest.fixture(scope="module")
def pact():
    pact = Pact("my-consumer", "my-provider").with_specification("V4")
    yield pact
    pact.write_file(PACT_DIR, overwrite=True)
```

---

## Quality Gates

Before completing contract test work:

- [ ] Contracts test API boundaries only (not internals)
- [ ] Uses Pact v3 API (`Pact`, `match`, `generate`)
- [ ] Uses matchers for flexible response validation
- [ ] Error response shapes are validated (4xx/5xx)
- [ ] Contracts versioned with API versions
- [ ] Pact files generated in `tests/contract/pacts/`
- [ ] Tests run independently: `pytest tests/contract/ -v`
- [ ] No shared mutable state between tests
- [ ] Provider states are parameterized and idempotent
- [ ] Schemathesis uses v4.x API (`schemathesis.openapi.from_url`, not `schemathesis.from_uri`)
- [ ] Schemathesis uses `from_asgi()` for FastAPI apps (no network overhead)
- [ ] Schemathesis config in `schemathesis.toml` if project uses it regularly

---

## Deep References

### Pact
- **[references/pact-consumer.md](references/pact-consumer.md)**: Full matchers/generators table, pytest fixtures, multi-provider, composition patterns
- **[references/pact-provider.md](references/pact-provider.md)**: Verifier API, state handlers, FastAPI/Flask patterns, broker integration, auth handling
- **[references/pact-advanced.md](references/pact-advanced.md)**: Message pacts, GraphQL, plugins, CI/CD, can-i-deploy, breaking changes, debugging

### Schemathesis
- **[references/schemathesis-guide.md](references/schemathesis-guide.md)**: CLI reference, Python API (v4.x loaders), pytest integration, `schemathesis.toml` config, data generation modes, test phases, 13 built-in checks, operation filtering
- **[references/schemathesis-advanced.md](references/schemathesis-advanced.md)**: Stateful testing (state machines, OpenAPI links), hooks system (map/filter/flatmap), dynamic auth, custom checks, serializers/formats, GraphQL scalars, CI/CD (GitHub Actions, GitLab), troubleshooting

### Rules
- **[../../rules/testing.md](../../rules/testing.md)**: Core AAA structure, naming conventions
- **[../../rules/mocking.md](../../rules/mocking.md)**: When mocking is appropriate in contracts
- **[../../rules/factories.md](../../rules/factories.md)**: Generating test payloads

---

## Validation Commands

```bash
# Run all contract tests
pytest tests/contract/ -v

# Run consumer tests only
pytest tests/contract/consumer/ -v -m consumer

# Run provider verification only
pytest tests/contract/provider/ -v -m provider

# Run Schemathesis against live API (all checks, continue on failure)
schemathesis run http://localhost:8000/openapi.json --checks all --continue-on-failure

# Schemathesis with parallel workers and thorough coverage
schemathesis run -w 4 --max-examples 500 http://localhost:8000/openapi.json

# Schemathesis negative testing only (verify invalid input rejection)
schemathesis run --mode=negative http://localhost:8000/openapi.json

# Schemathesis stateful testing only
schemathesis run --phases=stateful http://localhost:8000/openapi.json

# Schemathesis with JUnit report for CI
schemathesis run --report junit --checks all http://localhost:8000/openapi.json

# Publish contracts to broker
pact-broker publish tests/contract/pacts/ \
    --broker-base-url=$PACT_BROKER_URL \
    --consumer-app-version=$(git rev-parse HEAD) \
    --branch=$(git branch --show-current)

# Check deployment safety
pact-broker can-i-deploy \
    --pacticipant my-service \
    --version $(git rev-parse HEAD) \
    --to-environment production
```
