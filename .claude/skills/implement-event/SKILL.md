---
name: implement-event
version: 1.0.0
description: |
  Implement event producers, consumers, and handlers from AsyncAPI specs and event schemas.
  Use when building event handlers, publishing domain events, consuming messages, implementing
  outbox pattern, creating idempotent consumers, or wiring up message broker integrations.
  Relevant for Kafka, RabbitMQ, SQS, EventBridge, Celery, event-driven Python applications.
---

# Event Implementation

> Transform event designs into production-ready, idempotent, observable handlers.

## Quick Reference

| Aspect | Details |
|--------|---------|
| **Invokes** | `implement/pydantic`, `test/unit`, `observe/logs`, `observe/traces` |
| **Invoked By** | `design/event`, `implement/python` |
| **Key Artifacts** | Event models, producers, consumers, outbox, DLQ handlers |

---

## Core Workflow

1. **Locate**: Find AsyncAPI spec and event schemas from design phase
2. **Model**: Generate Pydantic event classes with metadata envelope
3. **Produce**: Implement transactional outbox publisher
4. **Consume**: Build idempotent handler with deduplication
5. **Harden**: Add retry logic, DLQ routing, timeouts
6. **Observe**: Instrument with structured logging, traces, metrics
7. **Test**: Generate unit tests for happy path and failure cases

---

## Must / Never

### Event Models

**MUST:**








- Inherit from base `DomainEvent` with metadata envelope

- Use `frozen=True` for immutability

- Include factory method `from_aggregate()` or `from_command()`

- Derive `idempotency_key` from business operation, not random UUID





**NEVER:**



- Use `dict` or untyped payloads
- Allow mutable event instances


- Generate random event IDs without business correlation
- Include sensitive data (PII, secrets) in plain text




### Producers




**MUST:**




- Write to outbox table within same database transaction
- Include all metadata fields: `event_id`, `correlation_id`, `causation_id`, `timestamp`

- Log publish intent before transaction commit



- Handle serialization errors explicitly


**NEVER:**




- Publish directly to broker inside business transaction
- Fire-and-forget without delivery tracking

- Catch and swallow `SerializationError`
- Hardcode broker URLs or credentials





### Consumers


**MUST:**





- Check idempotency FIRST before any processing
- Record processed event ID atomically with business operation

- Set processing timeout < visibility timeout
- Propagate `correlation_id` to all downstream calls

- Classify errors: retriable vs non-retriable




**NEVER:**

- Assume exactly-once delivery
- Process without idempotency guard

- Block indefinitely on external calls



- Swallow exceptions without DLQ routing
- Create bidirectional event dependencies

### Error Handling


**MUST:**



- Use exponential backoff with jitter for retries
- Route to DLQ after N attempts (configurable, default 3)
- Preserve original error context in DLQ message
- Alert on DLQ threshold breach


**NEVER:**


- Retry non-retriable errors (validation, auth)
- Use fixed retry delays
- Lose stack trace or error context
- Ignore DLQ growth silently

### Observability


**MUST:**

- Log: `event.received`, `event.processing`, `event.completed`, `event.failed`
- Include: `event_id`, `event_type`, `correlation_id`, `duration_ms`
- Create trace span per consumer invocation
- Emit metrics: `events_processed`, `events_failed`, `events_retried`

**NEVER:**

- Log full event payload (may contain PII)
- Use `print()` statements
- Skip `correlation_id` in any log entry
- Forget to close trace spans on error

---

## When → Then

| When | Then |
|------|------|
| AsyncAPI spec exists | Generate Pydantic models matching schema |
| Aggregate emits event | Use transactional outbox pattern |
| Consumer processes event | Idempotency check → process → record |
| External service call needed | Wrap with timeout + circuit breaker |
| Processing fails (retriable) | Exponential backoff → DLQ after max retries |
| Processing fails (non-retriable) | Immediate DLQ with error classification |
| Event payload > 256KB | Implement claim-check: store payload, reference in event |
| Ordering required | Partition by entity ID, process sequentially per partition |
| Multiple consumers needed | Use consumer groups, each gets own idempotency namespace |

---

## Decision Tree

```
Implementation Request
│
├─► Producer or Consumer?
│   ├─► Producer ──► Transactional Outbox
│   │                 ├─► Same DB as aggregate? ──► Outbox table
│   │                 └─► Different DB? ──► Saga with compensation
│   │
│   └─► Consumer ──► Idempotent Handler
│                     ├─► Simple processing? ──► Inline handler
│                     └─► Complex/long-running? ──► Saga coordinator
│
├─► Error Classification
│   ├─► ValidationError ──► Non-retriable → DLQ immediately
│   ├─► TimeoutError ──► Retriable → Backoff + retry
│   ├─► ConnectionError ──► Retriable → Backoff + retry
│   └─► AuthError ──► Non-retriable → DLQ + alert
│
└─► Observability Level
    ├─► Critical path ──► Full tracing + metrics + alerts
    ├─► Standard ──► Logging + basic metrics
    └─► High-volume ──► Sampled tracing + aggregated metrics
```

---

## Skill Chaining

| Condition | Invoke | Handoff Context |
|-----------|--------|-----------------|
| Complex event payload | `implement/pydantic` | Field definitions, validators |
| Handler needs DB access | `implement/database` | Query patterns, transaction scope |
| After implementation | `test/unit` | Event fixtures, mock broker |
| Adding structured logs | `observe/logs` | Log schema, correlation fields |
| Distributed tracing | `observe/traces` | Span naming, context propagation |

**Chaining Syntax:**
```markdown
**Invoking:** `implement/pydantic`
**Reason:** Event payload requires nested models with custom validators
**Context:** Fields: user_id (UUID), items (list[OrderItem]), metadata (dict)
```

---

## Patterns

### ✅ Event Model with Metadata

```python
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from uuid import UUID, uuid4

class EventMetadata(BaseModel):
    model_config = ConfigDict(frozen=True)

    event_id: UUID = Field(default_factory=uuid4)
    event_type: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    correlation_id: UUID
    causation_id: UUID
    source: str
    schema_version: str = "1.0.0"

class OrderPlaced(BaseModel):
    model_config = ConfigDict(frozen=True)

    metadata: EventMetadata
    order_id: UUID
    customer_id: UUID
    items: list[OrderItem]
    total: Money

    @classmethod
    def from_order(cls, order: Order, correlation_id: UUID, causation_id: UUID) -> "OrderPlaced":
        return cls(
            metadata=EventMetadata(
                event_type="OrderPlaced.v1",
                correlation_id=correlation_id,
                causation_id=causation_id,
                source="order-service.place_order",
            ),
            order_id=order.id,
            customer_id=order.customer_id,
            items=order.items,
            total=order.total,
        )
```

### ✅ Transactional Outbox Producer

```python
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger()

class OutboxPublisher:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def publish(self, event: DomainEvent) -> None:
        logger.info(
            "event.outbox.queued",
            event_id=str(event.metadata.event_id),
            event_type=event.metadata.event_type,
            correlation_id=str(event.metadata.correlation_id),
        )
        outbox_entry = OutboxEntry(
            id=event.metadata.event_id,
            event_type=event.metadata.event_type,
            payload=event.model_dump_json(),
            created_at=event.metadata.timestamp,
        )
        self._session.add(outbox_entry)
        # Committed with business transaction
```

### ✅ Idempotent Consumer

```python
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential_jitter

logger = structlog.get_logger()

class OrderPlacedHandler:
    def __init__(self, processed_events: ProcessedEventStore, inventory: InventoryService):
        self._processed = processed_events
        self._inventory = inventory

    async def handle(self, event: OrderPlaced) -> None:
        log = logger.bind(
            event_id=str(event.metadata.event_id),
            event_type=event.metadata.event_type,
            correlation_id=str(event.metadata.correlation_id),
        )

        # Idempotency check FIRST
        if await self._processed.exists(event.metadata.event_id):
            log.info("event.duplicate.skipped")
            return

        log.info("event.processing.started")
        try:
            async with transaction():
                await self._reserve_inventory(event)
                await self._processed.record(event.metadata.event_id)
            log.info("event.processing.completed")
        except Exception as e:
            log.error("event.processing.failed", error=str(e), error_type=type(e).__name__)
            raise

    @retry(stop=stop_after_attempt(3), wait=wait_exponential_jitter(max=10))
    async def _reserve_inventory(self, event: OrderPlaced) -> None:
        await self._inventory.reserve(event.items, timeout=5.0)
```

### ✅ DLQ Router

```python
from enum import Enum

class ErrorClassification(str, Enum):
    RETRIABLE = "retriable"
    NON_RETRIABLE = "non_retriable"

def classify_error(error: Exception) -> ErrorClassification:
    non_retriable = (ValidationError, AuthenticationError, PermissionError)
    return ErrorClassification.NON_RETRIABLE if isinstance(error, non_retriable) else ErrorClassification.RETRIABLE

async def handle_with_dlq(event: DomainEvent, handler: Callable, dlq: DLQPublisher, max_retries: int = 3) -> None:
    attempt = 0
    last_error = None

    while attempt < max_retries:
        try:
            await handler(event)
            return
        except Exception as e:
            last_error = e
            if classify_error(e) == ErrorClassification.NON_RETRIABLE:
                break
            attempt += 1
            await asyncio.sleep(min(2 ** attempt + random.uniform(0, 1), 30))

    await dlq.send(event, error=last_error, attempts=attempt)
    logger.warning("event.routed_to_dlq", event_id=str(event.metadata.event_id), error=str(last_error))
```

---

## Anti-Patterns

### ❌ Publishing Outside Transaction

```python
# WRONG: Event may publish but business op fails (or vice versa)
async def place_order(cmd: PlaceOrderCommand) -> Order:
    order = await order_repo.save(Order.create(cmd))
    await broker.publish(OrderPlaced.from_order(order))  # Not transactional!
    return order
```

### ❌ Missing Idempotency

```python
# WRONG: Processes duplicate events, corrupting state
async def handle_payment(event: PaymentReceived) -> None:
    await ledger.credit(event.amount)  # Runs multiple times on retry!
```

### ❌ Blocking Consumer

```python
# WRONG: No timeout, blocks indefinitely
async def handle_order(event: OrderPlaced) -> None:
    response = await external_service.call(event)  # May hang forever
```

### ❌ Swallowing Errors

```python
# WRONG: Failures disappear silently
async def handle_event(event: DomainEvent) -> None:
    try:
        await process(event)
    except Exception:
        pass  # Lost forever, no DLQ, no alert
```

### ❌ Anemic Event (ID Only)

```python
# WRONG: Forces consumer to call back for details
class OrderPlaced(BaseModel):
    order_id: UUID  # Consumer must fetch order - defeats event-driven purpose
```

---

## Quality Gates

Before completing event implementation:

- [ ] Event model inherits metadata envelope with all required fields
- [ ] Producer uses transactional outbox (same transaction as business op)
- [ ] Consumer checks idempotency before ANY processing
- [ ] All external calls have explicit timeouts
- [ ] Errors classified as retriable vs non-retriable
- [ ] DLQ routing implemented for max retry exceeded
- [ ] Structured logging with `event_id`, `correlation_id`, `event_type`
- [ ] Unit tests cover: happy path, duplicate event, retriable error, non-retriable error

---

## Examples

### Example 1: Implement Consumer from Design

**Input:** "Implement the UserRegistered event handler from the AsyncAPI spec"

**Output:**
```python
# src/events/handlers/user_registered.py
import structlog
from src.events.models import UserRegistered
from src.services.email import EmailService
from src.infrastructure.idempotency import ProcessedEventStore

logger = structlog.get_logger()

class UserRegisteredHandler:
    def __init__(self, email_service: EmailService, processed: ProcessedEventStore):
        self._email = email_service
        self._processed = processed

    async def handle(self, event: UserRegistered) -> None:
        log = logger.bind(
            event_id=str(event.metadata.event_id),
            correlation_id=str(event.metadata.correlation_id),
            user_id=str(event.user_id),
        )

        if await self._processed.exists(event.metadata.event_id):
            log.info("event.duplicate.skipped")
            return

        log.info("event.processing.started")
        async with transaction():
            await self._email.send_welcome(event.email, event.display_name)
            await self._processed.record(event.metadata.event_id)
        log.info("event.processing.completed")
```

### Example 2: Implement Producer with Outbox

**Input:** "Add event publishing to the order placement use case"

**Output:**
```python
# src/usecases/place_order.py
class PlaceOrderUseCase:
    def __init__(self, order_repo: OrderRepository, outbox: OutboxPublisher):
        self._orders = order_repo
        self._outbox = outbox

    async def execute(self, cmd: PlaceOrderCommand, correlation_id: UUID) -> Order:
        async with transaction():
            order = Order.create(cmd)
            await self._orders.save(order)

            event = OrderPlaced.from_order(
                order=order,
                correlation_id=correlation_id,
                causation_id=cmd.command_id,
            )
            await self._outbox.publish(event)

        return order
```

---

## Deep References

- **[refs/faststream.md](refs/faststream.md)**:
