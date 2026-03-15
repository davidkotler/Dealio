# Pact Python v3: Advanced Patterns

> Read this for message pacts, plugins, CI/CD integration, GraphQL,
> and breaking changes.

## Table of Contents

1. [Message Pact Testing](#message-pact-testing)
2. [GraphQL Contract Testing](#graphql-contract-testing)
3. [Plugin System (V4)](#plugin-system-v4)
4. [CI/CD Integration](#cicd-integration)
5. [Can-I-Deploy](#can-i-deploy)
6. [Webhooks](#webhooks)
7. [Breaking Changes (Expand and Contract)](#breaking-changes)
8. [Naming Conventions](#naming-conventions)
9. [Debugging Failed Verifications](#debugging-failed-verifications)
10. [What to Test and What Not To](#what-to-test)

---

## Message Pact Testing

Pact supports testing asynchronous message interactions (Kafka, RabbitMQ, SQS) from V3
onward. The key principle: **Pact abstracts away the transport layer**. No mock Kafka or
RabbitMQ needed.

### Consumer side (message handler)

```python
import json
from pact import Pact

PACT_DIR = Path(__file__).parent / "pacts"


@pytest.fixture(scope="module")
def pact():
    pact = Pact("order-processor", "order-service").with_specification("V4")
    yield pact
    pact.write_file(PACT_DIR, overwrite=True)


def test_order_created_event(pact):
    event = {
        "order_id": match.like("order-uuid-1234"),
        "product": match.like("Widget"),
        "quantity": match.like(5),
        "event_type": match.regex("CREATED", regex=r"^(CREATED|UPDATED|CANCELLED)$"),
    }

    (
        pact
        .upon_receiving("an order created event", "Async")
        .with_body(event, "application/json")
        .with_metadata({"kafka_topic": "orders"})
    )

    # Verify handler can process the expected message shape
    def handler(body, metadata):
        message = json.loads(body)
        process_order_event(message)

    pact.verify(handler, "Async")
```

### Provider side (message producer)

Register a message producer function that the verifier calls to generate messages,
then verify against the contract.

V4 adds **synchronous messages** (request-response patterns like gRPC) alongside
asynchronous ones.

---

## GraphQL Contract Testing

GraphQL uses standard HTTP interactions — queries are `POST /graphql` with JSON body:

```python
(
    pact.upon_receiving("a GraphQL query for user details")
    .with_request("POST", "/graphql")
    .with_header("Content-Type", "application/json")
    .with_body({
        "query": "query GetUser($id: ID!) { user(id: $id) { name email } }",
        "variables": {"id": "123"}
    })
    .will_respond_with(200)
    .with_body({
        "data": {
            "user": {
                "name": match.str("Jane Doe"),
                "email": match.regex("jane@example.com", regex=r".+@.+\..+"),
            }
        }
    })
)
```

Only assert on fields the consumer actually reads.

---

## Plugin System (V4)

V4 introduced a plugin framework for custom content types and transports.

```python
# Protobuf/gRPC consumer test
(
    pact
    .upon_receiving("a gRPC request for person")
    .with_plugin("protobuf", "0.4.0")
    .with_interaction_contents(
        "application/grpc",
        {
            "pact:proto": str(proto_path),
            "pact:proto-service": "PersonService/GetPerson",
            "request": {"id": "matching(type, '1')"},
            "response": {
                "name": "matching(type, 'Alice')",
                "age": "matching(type, 30)",
            },
        },
    )
)
```

Plugins are gRPC servers installed in `~/.pact/plugins/<name>-<version>/`.

---

## CI/CD Integration

### Consumer pipeline

```
1. Run unit tests
2. Run Pact consumer tests -> generates pact file
3. Publish pact to broker
4. can-i-deploy check
5. Deploy
6. Record deployment
```

### Provider pipeline

```
1. Run unit tests
2. Start provider service
3. Run Pact verification (fetch from broker)
4. Publish verification results
5. can-i-deploy check
6. Deploy
7. Record deployment
```

### Publishing pacts

```bash
pact-broker publish ./pacts/ \
    --consumer-app-version "$GIT_SHA" \
    --branch "$GIT_BRANCH" \
    --broker-base-url "$PACT_BROKER_BASE_URL" \
    --broker-token "$PACT_BROKER_TOKEN"
```

### Provider verification in CI

```python
import os
from pact import Verifier


def test_provider_ci():
    verifier = (
        Verifier("my-provider")
        .add_transport(url="http://localhost:8080")
        .broker_source(
            os.environ["PACT_BROKER_BASE_URL"],
            token=os.environ["PACT_BROKER_TOKEN"],
        )
        .consumer_version(deployed_or_released=True)
        .consumer_version(main_branch=True)
    )

    if os.environ.get("CI"):
        verifier.set_publish_options(
            version=os.environ["GIT_SHA"],
            branch=os.environ["GIT_BRANCH"],
        )

    verifier.verify()
```

---

## Can-I-Deploy

Deployment gate that queries the Pact Broker's compatibility matrix:

```bash
# Check before deploying
pact-broker can-i-deploy \
    --pacticipant my-service \
    --version $GIT_SHA \
    --to-environment production \
    --retry-while-unknown 12 \
    --retry-interval 10

# Record after deployment
pact-broker record-deployment \
    --pacticipant my-service \
    --version $GIT_SHA \
    --environment production
```

The `--retry-while-unknown` flag enables polling, essential when provider verification
is triggered asynchronously via webhooks.

---

## Webhooks

The recommended webhook event is **`contract_requiring_verification_published`**, which
fires once per provider version needing verification when a new pact is published.

Template variables: `${pactbroker.pactUrl}`, `${pactbroker.providerVersionBranch}`,
`${pactbroker.consumerName}`. Auto-retry up to 7 times with exponential backoff.

---

## Breaking Changes

The **expand and contract pattern** is the recommended approach:

1. **Expand**: Add new fields/endpoints to the provider and deploy
2. **Migrate**: Update consumers to use new fields and deploy
3. **Contract**: Remove old fields from the provider and deploy

At each step, all contracts remain green. Pending pacts provide a safety net,
and `can-i-deploy` prevents premature deployment.

---

## Naming Conventions

| Entity | Convention | Example |
|--------|-----------|---------|
| Consumer name | lowercase kebab-case | `"order-web-app"` |
| Provider name | lowercase kebab-case | `"user-service-api"` |
| Interaction description | Lowercase, specific, business language | `"a request for an existing user"` |
| Provider state | Present tense, descriptive, parameterized | `"user 123 exists"` with `id=123` |
| Pact files | Auto-named `<consumer>-<provider>.json` | `order-web-app-user-service-api.json` |

---

## Debugging Failed Verifications

| Symptom | Likely Cause | Solution |
|---------|-------------|---------|
| Missing request field | Consumer requires field provider doesn't send | Add field or update consumer |
| Type mismatch | Provider sends string but consumer expects int | Fix type on correct side |
| Missing provider state | No handler for required state | Implement the state handler |
| Extra unexpected request | Consumer makes undeclared request | Add interaction or remove request |
| Status code mismatch | Provider returns 500 instead of 200 | Fix provider bug or state setup |

Enable verbose logging for debugging:
```python
pact_ffi.log_to_stderr("DEBUG")
```

---

## What to Test

**Do test:**
- Every API endpoint your consumer actually calls
- All response scenarios your consumer handles (success, not found, server error)
- Different data shapes (empty lists, single items, pagination)
- Error responses and how your consumer reacts

**Do not test:**
- Provider internal logic (that's the provider's unit test)
- Fields your consumer doesn't use
- Every possible permutation of query parameters
- Performance or load characteristics
- Business logic calculations

**Contract granularity:**
- One interaction per logical API scenario
- Each variation must add value — ask whether it catches a real integration bug
- Over-specification is the #1 anti-pattern
