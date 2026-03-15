# Schemathesis Guide — Schema-Driven Property-Based API Testing

> Core usage: CLI, Python API, pytest integration, configuration, data generation, built-in checks.

## Table of Contents

1. [Schema Loading](#schema-loading)
2. [CLI Reference](#cli-reference)
3. [Pytest Integration](#pytest-integration)
4. [Configuration (schemathesis.toml)](#configuration)
5. [Data Generation Modes](#data-generation-modes)
6. [Test Execution Phases](#test-execution-phases)
7. [Built-in Checks](#built-in-checks)
8. [Operation Filtering](#operation-filtering)
9. [Adding Schema Validation to Existing Tests](#augmenting-existing-tests)

---

## Schema Loading

The API namespace changed in v4.x: use `schemathesis.openapi.from_url()` (not `schemathesis.from_uri()`).

### OpenAPI Loaders

```python
import schemathesis

# From a live URL (most common for contract testing)
schema = schemathesis.openapi.from_url(
    "https://api.example.com/openapi.json",
    headers={"Authorization": "Bearer token"},
    timeout=30,
    wait_for_schema=10.0,  # Wait up to 10s for schema availability
)

# From a local file path — useful for spec-first workflows
schema = schemathesis.openapi.from_path("./specs/openapi/v1.yaml")

# From a Python dictionary
schema = schemathesis.openapi.from_dict(schema_dict)

# Direct ASGI testing (FastAPI) — no network overhead, recommended for Python services
schema = schemathesis.openapi.from_asgi("/openapi.json", fastapi_app)

# Direct WSGI testing (Flask)
schema = schemathesis.openapi.from_wsgi("/openapi.json", flask_app)
```

### GraphQL Loaders

```python
schema = schemathesis.graphql.from_url("https://api.example.com/graphql")
schema = schemathesis.graphql.from_path("./schema.graphql")
schema = schemathesis.graphql.from_asgi("/graphql", app)
```

### Pytest Fixture Loading (Dynamic Configuration)

When schema requires runtime setup (database, dynamic tokens):

```python
import pytest
import schemathesis


@pytest.fixture
def api_schema(configured_app):
    return schemathesis.openapi.from_asgi("/openapi.json", configured_app)


schema = schemathesis.pytest.from_fixture("api_schema")


@schema.parametrize()
def test_operations(case):
    case.call_and_validate()
```

---

## CLI Reference

Both `schemathesis` and the short alias `st` work. Python 3.10+ required.

### Installation

```bash
pip install schemathesis
# or zero-install runs via uvx
uvx schemathesis run https://example.schemathesis.io/openapi.json
```

### Core Execution Options

| Option | Default | Description |
|---|---|---|
| `--generation-mode` / `--mode` | `all` | `positive`, `negative`, or `all` |
| `--max-examples` | 100 | Max test cases per operation (fuzzing phase) |
| `--workers` / `-w` | 1 | Concurrent workers (integer or `"auto"`) |
| `--max-failures` | None | Stop after N total failures |
| `--continue-on-failure` | false | Don't stop at first failure per operation |
| `--generation-seed` | None | Random seed for reproducibility |
| `--no-shrink` | false | Disable test case shrinking |
| `--phases` | all | Comma-separated: `examples`, `coverage`, `fuzzing`, `stateful` |

### Network Options

| Option | Default | Description |
|---|---|---|
| `--auth` / `-a` | None | Basic auth as `username:password` |
| `--header` / `-H` | None | Custom header `Name:Value` (repeatable) |
| `--request-timeout` | 10.0s | Per-request timeout |
| `--rate-limit` | None | Rate limit as `<limit>/<duration>` |

### Practical CLI Examples

```bash
# Quick smoke test
schemathesis run https://api.example.com/openapi.json

# Thorough pre-release with parallel workers and all checks
schemathesis run -w 8 --max-examples 500 --continue-on-failure \
  --checks all https://api.example.com/openapi.json

# Negative testing only — verify rejection of invalid inputs
schemathesis run --mode=negative https://api.example.com/openapi.json

# Test a local schema file with explicit base URL
schemathesis run ./openapi.yaml --url http://localhost:8000

# Test only POST endpoints tagged "payments"
schemathesis run --include-method POST --include-tag payments \
  https://api.example.com/openapi.json

# Only stateful phase with JUnit reporting
schemathesis run --phases=stateful --report junit \
  https://api.example.com/openapi.json

# ASGI direct testing (no network)
schemathesis run --app=myapp.main:app /openapi.json

# Reproducible run with seed
schemathesis run --generation-seed 12345 https://api.example.com/openapi.json
```

### Reporting and Output

```bash
# JUnit XML (Jenkins, GitLab, GitHub)
schemathesis run --report junit http://api.example.com/openapi.json

# VCR cassettes + HAR files
schemathesis run --report vcr,har http://api.example.com/openapi.json

# Custom output directory
schemathesis run --report junit --report-dir /tmp/results \
  http://api.example.com/openapi.json
```

Exit codes: **0** = passed, **1** = failures, **2** = interrupted, **3** = CLI usage error.

---

## Pytest Integration

### Core Pattern — `@schema.parametrize()`

Generates a separate parametrized test for every operation/method in the schema:

```python
import schemathesis
from hypothesis import settings

schema = schemathesis.openapi.from_url("http://127.0.0.1:8080/openapi.json")


@schema.parametrize()
def test_api(case):
    case.call_and_validate()


# With custom Hypothesis settings
@schema.parametrize()
@settings(max_examples=500)
def test_api_thorough(case):
    case.call_and_validate(headers={"Authorization": "Bearer token"})


# Filter to specific operations
@schema.include(operation_id="create_booking").parametrize()
def test_booking(case):
    case.call_and_validate()
```

### Case Object

The `case` object exposes:
- `case.method`, `case.path`, `case.headers`, `case.query`, `case.body`, `case.path_parameters`
- `case.call_and_validate()` — send request + run all checks
- `case.call()` — send request, return raw response (no validation)

### Direct ASGI Testing (Recommended for FastAPI)

Eliminates HTTP overhead, no port conflicts, zero network flakiness:

```python
from fastapi import FastAPI
from starlette.testclient import TestClient
import schemathesis

app = FastAPI()
schema = schemathesis.openapi.from_asgi("/openapi.json", app)


@schema.parametrize()
def test_api(case):
    with TestClient(app) as client:
        case.call_and_validate(session=client)
```

---

## Configuration

Schemathesis uses `schemathesis.toml` (auto-loaded from CWD or project root). Supports `${VAR_NAME}` env var interpolation.

**Precedence**: CLI options > per-operation config > project-wide config > defaults.

### Full Configuration Example

```toml
# schemathesis.toml
headers = { Authorization = "Bearer ${API_TOKEN}" }
continue-on-failure = true
request-timeout = 10.0

[generation]
max-examples = 500
mode = "all"

[auth]
basic = { username = "${USERNAME}", password = "${PASSWORD}" }

[checks]
enabled = false
not_a_server_error.enabled = true
response_schema_conformance.enabled = true

[phases]
stateful.enabled = true

[phases.stateful.inference]
algorithms = ["location-headers", "dependency-analysis"]

[reports.junit]
enabled = true

[output.sanitization]
enabled = false

# Per-operation overrides
[[operations]]
include-tag = "admin"
headers = { Authorization = "Bearer ${ADMIN_TOKEN}" }

[[operations]]
include-path-regex = "/(payments|users)/"
generation.max-examples = 500

# Multi-project
[[project]]
title = "Payment API"
base-url = "https://payments.example.com"
generation.max-examples = 200
```

### Loading Config Programmatically

```python
config = schemathesis.Config.from_path("path-to-my/config.toml")
schema = schemathesis.openapi.from_url(
    "http://127.0.0.1:8080/openapi.json", config=config
)
```

---

## Data Generation Modes

Controlled by `--generation-mode` / `--mode`:

| Mode | What it generates | When to use |
|---|---|---|
| `positive` | Schema-compliant data only | Verify API accepts valid inputs |
| `negative` | Deliberately invalid data (wrong types, missing required, out-of-range) | Verify API rejects bad inputs |
| `all` (default) | Both positive and negative | Broadest coverage |

### Test Case Shrinking

When a failure is found, Hypothesis automatically **shrinks** to the minimal reproducing case. A 20-field JSON body might reduce to just the single problematic field. Disable with `--no-shrink` for faster runs.

---

## Test Execution Phases

Tests execute in four sequential phases:

1. **Examples** — Uses `example`/`examples` values from your schema. Verifies documented examples actually work.
2. **Coverage** — Generates boundary values for every constraint (minLength, maxLength, min, max, enums). Deterministic count.
3. **Fuzzing** — Random diverse inputs via Hypothesis (controlled by `--max-examples`). Core edge-case discovery.
4. **Stateful** — Chains operations using response data (POST creates → GET reads → DELETE removes). Discovers workflow bugs.

Select specific phases:
```bash
schemathesis run --phases=examples,coverage,fuzzing https://api.example.com/openapi.json
```

---

## Built-in Checks

Schemathesis ships with **13 built-in checks** across four categories:

### Response Validation
- `not_a_server_error` — 5xx detection
- `status_code_conformance` — undocumented status codes
- `content_type_conformance` — unexpected content types
- `response_headers_conformance` — missing required headers
- `response_schema_conformance` — body doesn't match JSON Schema

### Input Handling
- `negative_data_rejection` — API accepts invalid data it should reject
- `positive_data_acceptance` — API rejects valid data it should accept
- `missing_required_header` — API doesn't enforce required headers
- `unsupported_method` — API doesn't return 405 for undocumented methods

### Stateful Behavior
- `use_after_free` — deleted resources still accessible
- `ensure_resource_availability` — created resources immediately available

### Security
- `ignored_auth` — authentication requirements not enforced

### Performance
- `max_response_time` — response time threshold (disabled by default)

### Selective Configuration

```bash
# Run only specific checks
schemathesis run --checks status_code_conformance,response_schema_conformance \
  https://api.example.com/openapi.json

# Enable response time check
schemathesis run --max-response-time 1.5 https://api.example.com/openapi.json
```

```toml
# In schemathesis.toml
[checks]
enabled = false
not_a_server_error.enabled = true
response_schema_conformance.enabled = true

[checks.positive_data_acceptance]
expected-statuses = [200, 201, 202]
```

---

## Operation Filtering

| Filter | Description |
|---|---|
| `--include-path` / `-E` | Include by exact path |
| `--include-path-regex` | Include by path regex |
| `--include-method` / `-M` | Include by HTTP method (repeatable) |
| `--include-tag` / `-T` | Include by OpenAPI tag |
| `--include-operation-id` / `-O` | Include by operationId |
| `--include-name` | Include by full name (`GET /users`) |
| `--exclude-deprecated` | Skip deprecated operations |

Each `--include-*` has a corresponding `--exclude-*`. Combine for precise targeting:

```bash
schemathesis run --include-method POST --include-tag payments \
  --exclude-deprecated https://api.example.com/openapi.json
```

---

## Augmenting Existing Tests

Add schema validation on top of existing test suites without replacing them:

```python
import requests
import schemathesis

schema = schemathesis.openapi.from_url("http://api.example.com/openapi.json")


def test_user_workflow():
    # Your existing test logic
    create_response = requests.post(
        "http://api.example.com/users", json={"name": "Test"}
    )
    user_id = create_response.json()["id"]

    # Add schema validation on top
    schema["/users"]["POST"].validate_response(create_response)

    get_response = requests.get(f"http://api.example.com/users/{user_id}")
    schema["/users/{id}"]["GET"].validate_response(get_response)
```

For non-throwing boolean check:
```python
assert schema["/users"]["POST"].is_valid_response(response)
```
