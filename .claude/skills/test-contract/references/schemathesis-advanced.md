# Schemathesis Advanced — Stateful Testing, Hooks, Auth, Extensions, CI/CD

> Advanced patterns: stateful workflows, hooks system, authentication, custom checks,
> serializers/formats, GraphQL scalars, CI/CD integration, troubleshooting.

## Table of Contents

1. [Stateful Testing](#stateful-testing)
2. [Hooks and Extension System](#hooks-and-extension-system)
3. [Authentication Patterns](#authentication-patterns)
4. [Custom Checks](#custom-checks)
5. [Custom Formats, Serializers, and Deserializers](#custom-formats-serializers-and-deserializers)
6. [GraphQL Patterns](#graphql-patterns)
7. [Targeted Testing with Metrics](#targeted-testing-with-metrics)
8. [CI/CD Integration](#cicd-integration)
9. [Best Practices](#best-practices)
10. [Troubleshooting](#troubleshooting)

---

## Stateful Testing

Chains API operations into realistic workflows where response data feeds subsequent requests. Without stateful testing, `GET /users/123` uses a random ID and gets a 404. With it, `POST /users` creates a user, extracts the returned ID, and feeds it to `GET /users/{id}` and `DELETE /users/{id}`.

### How Links Are Discovered

1. **Automatic dependency analysis** — infers links from response schemas and path parameters
2. **Location header analysis** — captures `Location` headers from earlier test phases
3. **Explicit OpenAPI links** — defined in your schema

Control via config:
```toml
[phases.stateful.inference]
algorithms = ["location-headers", "dependency-analysis"]
```

### Defining OpenAPI Links

```yaml
paths:
  /users:
    post:
      operationId: createUser
      responses:
        '201':
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/User'
          links:
            GetUser:
              operationId: getUser
              parameters:
                userId: '$response.body#/id'
            DeleteUser:
              operationId: deleteUser
              parameters:
                userId: '$response.body#/id'
```

### Regex-Based Link Extraction

Schemathesis extends standard OpenAPI links with regex:

```yaml
links:
  GetUserByLocation:
    operationId: getUser
    parameters:
      userId: '$response.header.Location#regex:/users/(.+)'
  SetManagerId:
    operationId: setUserManager
    requestBody: "$response.body#/id"
```

### Python State Machine API

```python
schema = schemathesis.openapi.from_url("http://localhost:8000/openapi.json")


class APIWorkflow(schema.as_state_machine()):
    def setup(self):
        """Runs once at the start of each test scenario."""
        # Seed database, create test users

    def teardown(self):
        """Runs once at the end of each test scenario."""

    def before_call(self, case):
        """Modify every request in the sequence."""
        case.headers = case.headers or {}
        case.headers["X-Request-ID"] = str(uuid.uuid4())

    def after_call(self, response, case):
        """Process every response in the sequence."""
        assert response.elapsed.total_seconds() < 5.0


TestAPI = APIWorkflow.TestCase  # Creates pytest-compatible test class
```

### Using Fixtures with State Machines

```python
import pytest


@pytest.fixture(scope="session")
def database():
    yield db


@pytest.mark.usefixtures("database")
class TestAPI(APIWorkflow.TestCase):
    pass
```

### CLI Stateful Testing

Enabled by default when links are discoverable. Force stateful-only:
```bash
schemathesis run --phases=stateful https://api.example.com/openapi.json
```

---

## Hooks and Extension System

Hooks customize every stage of the pipeline. Register globally via `@schemathesis.hook` or per-schema via `@schema.hook`.

### Data Transformation Pipeline

Hooks execute in order: **filter → map → flatmap → final test case**.

Parts: `query`, `headers`, `body`, `path_parameters`, `cookies`, `case`.

#### `map_*` — Transform generated values

```python
@schemathesis.hook
def map_query(ctx, query):
    """Replace random user_id with known test user."""
    if query and "user_id" in query:
        query["user_id"] = "test-user-123"
    return query


@schemathesis.hook
def map_path_parameters(ctx, path_parameters):
    """Pin path parameters to known test data."""
    if path_parameters and "product_id" in path_parameters:
        path_parameters["product_id"] = "product_1"
    return path_parameters
```

#### `filter_*` — Skip irrelevant test cases

```python
@schemathesis.hook
def filter_query(ctx, query):
    """Skip cases where query lacks required fields."""
    return query and "user_id" in query
```

#### `flatmap_*` — Generate dependent/correlated data

```python
from hypothesis import strategies as st


@schemathesis.hook
def flatmap_body(ctx, body):
    """Generate emails matching the organization domain."""
    if body and "email" in body and "organization" in body:
        org = body["organization"]
        return st.just({**body, "email": f"user@{org.lower()}.com"})
    return st.just(body)
```

### Lifecycle Hooks

```python
@schemathesis.hook
def before_call(ctx, case, **kwargs):
    """Modify request right before sending."""
    case.headers = case.headers or {}
    case.headers["X-Test-Mode"] = "true"


@schemathesis.hook
def after_call(ctx, case, response):
    """Process every response (logging, metrics)."""
    print(f"{case.method} {case.path} -> {response.status_code}")
```

Additional lifecycle hooks: `before_load_schema`, `after_load_schema`, `before_process_path`, `before_generate_case`.

### Hook Filters (Selective Application)

Since v4.1:

```python
@schemathesis.hook.apply_to(method="POST", path_regex="^/admin")
def map_body(ctx, body):
    body["admin_override"] = True
    return body


@schemathesis.hook.skip_for(method="GET", path="/health")
def filter_query(ctx, query):
    return query is not None
```

### Loading Hooks in CLI

```bash
# Via environment variable
export SCHEMATHESIS_HOOKS=mymodule.hooks
schemathesis run https://api.example.com/openapi.json

# Via config
# schemathesis.toml: hooks = "myproject.tests.hooks"
```

---

## Authentication Patterns

### Static Headers (CLI)

```bash
schemathesis run -H "Authorization: Bearer $TOKEN" http://localhost:8000/openapi.json
schemathesis run --auth user:password http://localhost:8000/openapi.json
```

### OpenAPI-Aware Security Schemes (Config)

```toml
[auth.openapi.ApiKeyAuth]
api_key = "${API_KEY}"

[auth.openapi.BearerAuth]
bearer = "${TOKEN}"

[auth.openapi.BasicAuth]
username = "${USERNAME}"
password = "${PASSWORD}"
```

### Dynamic Token Refresh (Python)

For APIs with expiring tokens:

```python
import requests
import schemathesis


@schemathesis.auth(refresh_interval=600)
class TokenAuth:
    def __init__(self):
        self.refresh_token = None

    def get(self, case, ctx):
        if self.refresh_token:
            response = requests.post(
                "http://api/auth/refresh",
                headers={"Authorization": f"Bearer {self.refresh_token}"},
            )
        else:
            response = requests.post(
                "http://api/auth/login",
                json={"username": "demo", "password": "test"},
            )
        data = response.json()
        self.refresh_token = data.get("refresh_token", self.refresh_token)
        return data["access_token"]

    def set(self, case, data, ctx):
        case.headers = case.headers or {}
        case.headers["Authorization"] = f"Bearer {data}"
```

Tokens cached for **300 seconds** by default. `refresh_interval` customizes this.

### Context-Aware Auth

```python
@schemathesis.auth()
class ContextAwareAuth:
    def get(self, case, context):
        if "/admin/" in context.operation.path:
            return self.get_admin_token()
        return self.get_user_token()

    def set(self, case, data, context):
        case.headers = {"Authorization": f"Bearer {data}"}
```

### Selective Auth Application

```python
@schemathesis.auth().apply_to(path=["/users/", "/orders/"])
@schemathesis.auth().apply_to(path_regex="^/admin")
@schemathesis.auth().apply_to(method=["POST", "PUT", "DELETE"])
@schemathesis.auth().skip_for(path="/health", method="GET")
```

For ASGI apps, `ctx.app` gives direct access to the application instance for in-process token acquisition.

---

## Custom Checks

Register domain-specific validation beyond the 13 built-ins:

```python
@schemathesis.check
def check_cors_headers(ctx, response, case):
    """Verify CORS headers are present on all responses."""
    if "Access-Control-Allow-Origin" not in response.headers:
        raise AssertionError("Missing CORS headers")


@schemathesis.check
def check_audit_trail(ctx, response, case):
    """Ensure all mutations produce audit trail headers."""
    if case.method in ("POST", "PUT", "DELETE") and response.status_code < 400:
        if "X-Audit-ID" not in response.headers:
            raise AssertionError("Missing audit trail header")


@schemathesis.check
def check_pagination_consistency(ctx, response, case):
    """Validate pagination metadata is consistent."""
    if response.status_code == 200 and case.method == "GET":
        data = response.json()
        if isinstance(data, dict) and "total" in data and "items" in data:
            if data["total"] < len(data["items"]):
                raise AssertionError(
                    f"Total ({data['total']}) < items ({len(data['items'])})"
                )
```

Custom checks registered with `@schemathesis.check` are automatically available in both CLI and Python modes.

---

## Custom Formats, Serializers, and Deserializers

### Custom String Formats

When your schema uses custom `format` values:

```python
from hypothesis import strategies as st
import schemathesis

schemathesis.openapi.format(
    "credit-card",
    st.from_regex(r"4[0-9]{15}", fullmatch=True),
)
schemathesis.openapi.format(
    "phone-number",
    st.from_regex(r"\+1[0-9]{10}", fullmatch=True),
)
```

### Serializer Aliases

Reuse built-in serializers for vendor-specific media types:

```python
schemathesis.serializer.alias("application/vnd.api+json", "application/json")
schemathesis.serializer.alias(
    ["application/x-json", "text/json"], "application/json"
)
```

### Custom Serializers

```python
@schemathesis.serializer("text/csv")
def csv_serializer(ctx, value):
    return csv_bytes
```

### Custom Deserializers

Enable response validation for non-standard content types:

```python
import msgpack


@schemathesis.deserializer("application/msgpack", "application/x-msgpack")
def deserialize_msgpack(ctx, response):
    return msgpack.unpackb(response.content, raw=False)
```

### Custom Media Type Strategies

Generate domain-specific binary content:

```python
schemathesis.openapi.media_type(
    "application/pdf", st.sampled_from([pdf_bytes_v1, pdf_bytes_v2])
)
```

---

## GraphQL Patterns

Custom scalars map Hypothesis strategies to GraphQL AST nodes:

```python
from schemathesis.graphql import nodes
from hypothesis import strategies as st

schemathesis.graphql.scalar("Email", st.emails().map(nodes.String))
schemathesis.graphql.scalar(
    "PositiveInt", st.integers(min_value=1).map(nodes.Int)
)
schemathesis.graphql.scalar(
    "Price",
    st.decimals(min_value=0, max_value=1000, places=2).map(nodes.Float),
)
```

Node factories: `nodes.String`, `nodes.Int`, `nodes.Float`, `nodes.Boolean`, `nodes.Null`.

---

## Targeted Testing with Metrics

Guide generation toward inputs that maximize a custom metric:

```python
@schemathesis.metric
def response_size(ctx: schemathesis.MetricContext) -> float:
    """Bias generation toward larger responses."""
    return float(len(ctx.response.content))
```

---

## CI/CD Integration

### GitHub Actions (Official Action)

```yaml
name: API Tests
on: [push, pull_request]
jobs:
  api-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: docker compose up -d
      - uses: schemathesis/action@v2
        with:
          schema: 'http://localhost:8080/openapi.json'
          args: >-
            --header "Authorization: Bearer ${{ secrets.API_TOKEN }}"
            --report junit
            --continue-on-failure
      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: schemathesis-results
          path: schemathesis-report/
```

### GitLab CI with Docker

```yaml
api-tests:
  stage: test
  image:
    name: schemathesis/schemathesis:stable
    entrypoint: [""]
  script:
    - schemathesis run http://api:8080/openapi.json
      --header "Authorization: Bearer $API_TOKEN"
      --wait-for-schema 60
      --report junit
  artifacts:
    when: always
    reports:
      junit: schemathesis-report/junit.xml
```

### Build Gating with Warnings

Turn warnings into hard failures (exit code 1):

```toml
[fail-on]
missing_test_data = true      # API returns mostly 404s
validation_mismatch = true     # API rejects most generated data
missing_deserializer = true    # Can't validate responses
unused_openapi_auth = true     # Configured auth not in schema
```

Use `--wait-for-schema` for startup timing in containerized environments.

---

## Best Practices

### Schema Quality is Foundational

Schemathesis is only as effective as your schema:

- Define `required` fields accurately — missing declarations mean Schemathesis won't test their absence
- Use precise constraints: `type`, `format`, `minimum`, `maximum`, `minLength`, `maxLength`, `pattern`, `enum`
- Document all response codes including 4xx errors — undocumented responses trigger conformance failures
- Include `example`/`examples` values — Schemathesis tests these first

### Handle Test Data Thoughtfully

Random IDs cause 404 errors. Solutions:

- **Hooks**: Replace random values with known test data using `map_*` hooks
- **Stateful testing**: Let POST operations provide IDs for GET/DELETE
- **OpenAPI links**: Explicitly declare how operations connect

Watch for the `missing_test_data` warning — it indicates most responses are 404s.

### Recommended Workflow

1. **Development**: `schemathesis run --mode=positive --max-examples 50` — fast feedback
2. **PR checks**: `schemathesis run --checks all --max-examples 100` — standard coverage
3. **Release candidates**: `schemathesis run -w 8 --max-examples 500 --continue-on-failure` — thorough
4. **Direct ASGI/WSGI for Python services** — eliminate network overhead

### Per-Operation Configuration

Different endpoints have different needs:

```toml
[generation]
max-examples = 100

# Deep testing for critical endpoints
[[operations]]
include-path-regex = "/(payments|transactions)/"
generation.max-examples = 500

# Generous timeouts for slow endpoints
[[operations]]
include-tag = "reports"
request-timeout = 30.0
```

---

## Troubleshooting

### Too Many 404 Responses

Generated path parameters don't match real resources. Use `map_*` hooks to inject known IDs, add stateful testing with OpenAPI links, or fix path parameter constraints in your schema.

### `FailedHealthCheck: filtering out too much data`

Schema constraints are too complex or contradictory. Check for conflicting `oneOf`/`anyOf`, overly restrictive patterns. Suppress:
```bash
schemathesis run --hypothesis-suppress-health-check=filter_too_much \
  https://api.example.com/openapi.json
```

### `Unsatisfiable` Errors in Stateful Testing

All operations have inbound links but none can be initial entry points. Ensure at least one operation (e.g., a POST endpoint) can be called without data from other operations.

### Slow Test Runs

Reduce `max-examples`, limit to specific operations with `--include-*`, use `--workers` for parallelism, disable shrinking with `--no-shrink`, test positive mode only during development.

### Schema Validation Errors

If schema doesn't fully conform to OpenAPI spec:
```bash
schemathesis run --validate-schema=false https://api.example.com/openapi.json
```
