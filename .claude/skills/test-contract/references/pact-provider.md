# Pact Python v3: Provider Verification Guide

> Read this when writing provider-side Pact verification tests.

## Table of Contents

1. [Verifier Class](#verifier-class)
2. [Verifying from Local Files](#verifying-from-local-files)
3. [Verifying from Pact Broker](#verifying-from-pact-broker)
4. [Consumer Version Selectors](#consumer-version-selectors)
5. [Provider State Management](#provider-state-management)
6. [FastAPI Provider Pattern](#fastapi-provider-pattern)
7. [Flask Provider Pattern](#flask-provider-pattern)
8. [Authentication Handling](#authentication-handling)
9. [Pending and WIP Pacts](#pending-and-wip-pacts)
10. [Publishing Results](#publishing-results)
11. [Provider Best Practices](#provider-best-practices)

---

## Verifier Class

Provider verification replays each pact interaction against a running provider and checks
that actual responses satisfy the consumer's minimum expectations.

```python
from pact import Verifier

verifier = Verifier("provider-name")
verifier.add_transport(url="...", protocol="...", path="...")  # Provider endpoint
verifier.add_source("./pacts/")                                # Local pact files
verifier.broker_source(url, token=..., selector=True)          # Broker source
verifier.state_handler(handlers, teardown=True)                # State management
verifier.message_handler(func)                                 # Message producer
verifier.filter(description="regex", state="regex")            # Filter interactions
verifier.filter_consumers("app1", "app2")                      # Filter by consumer
verifier.set_publish_options(version="...", branch="...")       # Publish results
verifier.include_pending()                                     # Enable pending pacts
verifier.include_wip_since("2023-01-01")                       # Enable WIP pacts
verifier.provider_branch("main")                               # Set provider branch
verifier.consumer_version(branch="main")                       # Consumer version selector
verifier.add_custom_header("key", "value")                     # Custom header
verifier.verify()                                              # Execute verification
```

---

## Verifying from Local Files

Simplest setup — point the verifier at local pact JSON files:

```python
from pact import Verifier


def test_provider_verification():
    """Verify the provider against all consumer contracts."""
    verifier = (
        Verifier("user-provider")
        .add_source("./pacts/")
        .add_transport(url="http://localhost:8080")
    )
    verifier.verify()
```

---

## Verifying from Pact Broker

In production workflows, pacts are fetched from a broker:

```python
import os
from pact import Verifier


def test_provider_from_broker():
    verifier = (
        Verifier("user-provider")
        .add_transport(url="http://localhost:8080")
        .broker_source(
            "https://my-broker.example.com",
            token=os.environ["PACT_BROKER_TOKEN"],
        )
    )

    if os.environ.get("CI"):
        verifier.set_publish_options(
            version=os.environ["GIT_SHA"],
            branch=os.environ["GIT_BRANCH"],
        )

    verifier.verify()
```

---

## Consumer Version Selectors

Target specific consumer versions when verifying from a broker:

```python
verifier = (
    Verifier("user-provider")
    .add_transport(url="http://localhost:8080")
    .broker_source("https://broker.example.com", token="...")
    # Verify against deployed/released consumers
    .consumer_version(deployed_or_released=True)
    # Verify against main branch
    .consumer_version(main_branch=True)
    # Verify against matching feature branches
    .consumer_version(matching_branch=True)
    # Verify against a specific consumer's branch
    .consumer_version(consumer="mobile-app", branch="main")
    # Verify against a specific environment
    .consumer_version(deployed=True, environment="production")
)
```

---

## Provider State Management

Provider states ensure the provider is in the correct condition before each interaction
is verified. When a consumer specifies `.given("user 123 exists")`, the provider must
set up a user with ID 123 before the request is replayed.

### Dictionary-Based Handlers (Recommended)

Map state names to specific functions:

```python
from typing import Any, Literal


def setup_user_exists(
    action: Literal["setup", "teardown"],
    parameters: dict[str, Any] | None,
) -> None:
    parameters = parameters or {}
    user_id = parameters.get("id", 123)
    if action == "setup":
        UserDb.create(User(id=user_id, name="Test User"))
    if action == "teardown":
        UserDb.delete(user_id)


def setup_no_users(
    action: Literal["setup", "teardown"],
    parameters: dict[str, Any] | None,
) -> None:
    if action == "setup":
        UserDb.clear()


state_handlers = {
    "user 123 exists": setup_user_exists,
    "no users exist": setup_no_users,
}

verifier = (
    Verifier("user-provider")
    .add_transport(url="http://localhost:8080")
    .add_source("./pacts/")
    .state_handler(state_handlers, teardown=True)
)
```

### Function-Based Handler

A single function handles all states:

```python
def state_handler(
    state: str,
    action: Literal["setup", "teardown"],
    parameters: dict[str, Any] | None,
) -> None:
    if state == "user 123 exists" and action == "setup":
        UserDb.create(User(
            id=parameters.get("id", 123),
            name=parameters.get("name", "Test User"),
        ))
    elif state == "user 123 exists" and action == "teardown":
        UserDb.delete(parameters.get("id", 123))

verifier.state_handler(state_handler)
```

### URL-Based Handler

Delegates to an external HTTP endpoint:

```python
verifier.state_handler(url="http://localhost:8080/_pact/states")
```

### State handler rules

1. **Idempotent and reproducible** — running setup twice yields the same result
2. **Always implement teardown** — clean up after each interaction
3. **Use parameterized states** — pass data via `given("user exists", id=123)`
4. **Keep states minimal** — set up only data needed for the specific interaction
5. **Same-process requirement** — function/dictionary handlers must run in the same
   process as the provider (use `threading.Thread`, not `multiprocessing.Process`)

---

## FastAPI Provider Pattern

```python
# test_provider.py
import threading
import uvicorn
import pytest
from pact import Verifier
from provider import app, users_db


@pytest.fixture(scope="session")
def provider_server():
    """Run the FastAPI provider in a background thread."""
    server = uvicorn.Server(
        uvicorn.Config(app, host="127.0.0.1", port=8080)
    )
    thread = threading.Thread(target=server.run)
    thread.daemon = True
    thread.start()
    yield "http://127.0.0.1:8080"
    server.should_exit = True


def setup_user_exists(action, parameters):
    parameters = parameters or {}
    if action == "setup":
        users_db[parameters.get("id", 123)] = {
            "id": parameters.get("id", 123),
            "name": parameters.get("name", "Test User"),
            "created_on": "2024-01-01T00:00:00Z",
        }
    elif action == "teardown":
        users_db.pop(parameters.get("id", 123), None)


def test_provider(provider_server):
    verifier = (
        Verifier("user-provider")
        .add_transport(url=provider_server)
        .add_source("./pacts/")
        .state_handler({
            "user 123 exists": setup_user_exists,
            "user 999 does not exist": lambda a, p: None,
        }, teardown=True)
    )
    verifier.verify()
```

The provider must run in the **same process** (via `threading.Thread`) so that
state handlers can directly manipulate the provider's in-memory data or dependency
injection overrides.

---

## Flask Provider Pattern

```python
import threading
from provider_flask import app


@pytest.fixture(scope="session")
def provider_server():
    thread = threading.Thread(
        target=app.run,
        kwargs={"host": "127.0.0.1", "port": 8080},
    )
    thread.daemon = True
    thread.start()
    yield "http://127.0.0.1:8080"
```

---

## Authentication Handling

Pact recommends **bypassing or stubbing authentication** during provider verification
rather than testing auth protocols through contracts.

Strategies:
1. **Provider state** — use `.given("authenticated as admin")` to configure provider
   to bypass auth checks
2. **Custom headers** — `verifier.add_custom_header("Authorization", "Bearer token123")`
3. **Relaxed validation** — accept any structurally-valid auth header during Pact tests

Consumer side:
```python
(
    pact
    .upon_receiving("an authenticated request for user data")
    .given("authenticated as admin")
    .with_request("GET", "/admin/users")
    .with_header("Authorization", match.regex(
        "Bearer valid-token",
        regex=r"Bearer .+"
    ))
    .will_respond_with(200)
    .with_body({"users": match.each_like({"id": match.int(1)})})
)
```

Auth protocols are common, stable patterns — testing them through contracts adds
complexity without proportional value.

---

## Pending and WIP Pacts

**Pending pacts** prevent new consumer expectations from breaking the provider build
before the provider implements them. A pact is "pending" until its first successful
verification. While pending, failures are reported but **do not fail the build**.

**WIP pacts** automatically pull in unverified consumer branch pacts for verification
in pending mode.

```python
verifier = (
    Verifier("my-provider")
    .include_pending()
    .include_wip_since("2023-01-01")  # Prevents pulling years of old pacts
)
```

---

## Publishing Results

Always publish verification results in CI. Without this, `can-i-deploy` has no data.

```python
import os

if os.environ.get("CI"):
    verifier.set_publish_options(
        version=os.environ["GIT_SHA"],
        branch=os.environ["GIT_BRANCH"],
    )
```

---

## Provider Best Practices

1. **Provider states should be idempotent preconditions** — inject data directly, not
   through the API being tested
2. **Each interaction verifies in isolation** — no carried state between interactions
3. **Stub downstream dependencies** — keep verification fast and deterministic
4. **Publish verification results in CI** — essential for `can-i-deploy`
5. **Use consumer version selectors** — verify pacts from main branch, matching branches,
   and all deployed/released versions
