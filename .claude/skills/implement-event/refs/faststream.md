# FastStream Implementation Reference

> Production patterns for event-driven microservices with FastStream 0.6+

---

## Must / Never Rules

### Application Setup

| ✅ MUST | ❌ NEVER |
|---------|----------|
| Pass broker as positional argument: `FastStream(broker)` | Use keyword: `FastStream(broker=broker)` (removed in 0.6) |
| Use `async def` for all handlers | Use synchronous `def` handlers |
| Type-annotate all handler parameters with Pydantic models | Leave parameters untyped or use `dict` |
| Install broker extras: `pip install 'faststream[kafka]'` | Install base `faststream` without broker |
| Use `ContextRepo` for global dependencies | Use module-level mutable globals |

### Event Models

| ✅ MUST | ❌ NEVER |
|---------|----------|
| Inherit from base `DomainEvent` with metadata envelope | Use raw dicts without schema |
| Use `model_config = ConfigDict(frozen=True)` for immutability | Allow mutable event instances |
| Include factory method `from_aggregate()` or `from_command()` | Construct events with scattered logic |
| Derive `idempotency_key` from business operation | Generate random UUIDs for idempotency |
| Define explicit `correlation_id` and `causation_id` | Omit tracing context from events |

### Message Handling

| ✅ MUST | ❌ NEVER |
|---------|----------|
| Check idempotency FIRST before any processing | Process before checking duplicates |
| Use `AckPolicy.NACK_ON_ERROR` for retriable operations | Use deprecated `retry=True` parameter |
| Set explicit timeouts on all external calls | Block indefinitely on I/O operations |
| Propagate `correlation_id` to all downstream calls | Drop correlation context between services |
| Classify errors as retriable vs non-retriable | Treat all exceptions identically |

### Acknowledgment Control

| ✅ MUST | ❌ NEVER |
|---------|----------|
| Use `AckPolicy` enum for acknowledgment strategy | Use boolean `retry` parameter (deprecated) |
| Raise `NackMessage` for retriable failures | Return `None` and hope for redelivery |
| Raise `RejectMessage` for poison messages | Let invalid messages retry forever |
| Use `AckPolicy.MANUAL` for complex workflows | Mix automatic and manual ack in same handler |

### Testing

| ✅ MUST | ❌ NEVER |
|---------|----------|
| Use `TestKafkaBroker`, `TestRabbitBroker` for unit tests | Require running broker for CI/CD |
| Assert with `handler.mock.assert_called_with(dict(...))` | Assert on Pydantic model instances |
| Test idempotency by publishing same event twice | Assume single delivery in tests |
| Test validation errors explicitly | Skip negative test cases |

### Observability

| ✅ MUST | ❌ NEVER |
|---------|----------|
| Use `Logger` from dependency injection | Create own logger instances |
| Log: `event_id`, `event_type`, `correlation_id`, `duration_ms` | Log full event payload (PII risk) |
| Add `TelemetryMiddleware` for distributed tracing | Skip tracing in event handlers |
| Emit metrics: `events_processed`, `events_failed`, `events_retried` | Ignore observability for async flows |

---

## When → Then Rules

### Broker Selection

| WHEN | THEN |
|------|------|
| High throughput + ordering by partition | Use `KafkaBroker` |
| Complex routing + DLQ + exchanges | Use `RabbitBroker` |
| Lightweight pub/sub + KeyValue store | Use `NatsBroker` |
| Simple streams + caching integration | Use `RedisBroker` |

### Acknowledgment Strategy

| WHEN | THEN |
|------|------|
| Handler is idempotent, failures are permanent | Use `AckPolicy.REJECT_ON_ERROR` (default) |
| Failures are transient, broker should redeliver | Use `AckPolicy.NACK_ON_ERROR` |
| Processing is fast, throughput is critical | Use `AckPolicy.ACK_FIRST` |
| Complex workflow needs explicit control | Use `AckPolicy.MANUAL` with `msg.ack()`/`nack()` |

### Error Handling

| WHEN | THEN |
|------|------|
| `ValidationError` raised | Route to DLQ immediately (non-retriable) |
| `TimeoutError` or `ConnectionError` raised | Retry with exponential backoff |
| `AuthenticationError` raised | Route to DLQ + alert (non-retriable) |
| Max retries exceeded | Route to DLQ with full error context |
| Processing succeeds but downstream fails | Raise `NackMessage` to retry entire flow |

### Event Flow

| WHEN | THEN |
|------|------|
| Handler returns a value | Use `@broker.publisher("output")` decorator |
| Publishing is conditional | Use `await broker.publish()` inside handler |
| Multiple outputs from one input | Stack multiple `@broker.publisher()` decorators |
| Need request-response | Use `await broker.request()` with timeout |
| Event payload > 256KB | Implement claim-check: publish reference, not payload |

### Testing Strategy

| WHEN | THEN |
|------|------|
| Unit testing handlers | Use `async with TestKafkaBroker(broker)` |
| Testing message flow end-to-end | Add spy subscribers for output topics |
| Verifying idempotency | Publish same message twice, assert single processing |
| Integration testing | Use `with_real=True` parameter |

---

## Patterns

### ✅ Event Model with Metadata Envelope

```python
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from uuid import UUID, uuid4

class EventMetadata(BaseModel):
    """Standard envelope for all domain events."""
    model_config = ConfigDict(frozen=True)

    event_id: UUID = Field(default_factory=uuid4)
    event_type: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    correlation_id: UUID
    causation_id: UUID
    source: str
    schema_version: str = "1.0.0"

class OrderPlaced(BaseModel):
    """Domain event with self-contained payload."""
    model_config = ConfigDict(frozen=True)

    metadata: EventMetadata
    order_id: UUID
    customer_id: UUID
    customer_email: str  # Included, not just ID
    items: list[OrderItem]
    total: Money

    @classmethod
    def from_order(
        cls,
        order: Order,
        correlation_id: UUID,
        causation_id: UUID
    ) -> "OrderPlaced":
        return cls(
            metadata=EventMetadata(
                event_type="OrderPlaced.v1",
                correlation_id=correlation_id,
                causation_id=causation_id,
                source="order-service.place_order",
            ),
            order_id=order.id,
            customer_id=order.customer_id,
            customer_email=order.customer.email,
            items=order.items,
            total=order.total,
        )
```

### ✅ Idempotent Consumer with AckPolicy

```python
from faststream import AckPolicy
from faststream.kafka import KafkaBroker
import structlog

logger = structlog.get_logger()
broker = KafkaBroker("localhost:9092")

@broker.subscriber("orders.placed", ack_policy=AckPolicy.NACK_ON_ERROR)
async def handle_order_placed(
    event: OrderPlaced,
    processed_events: ProcessedEventStore,  # Injected via Depends
) -> None:
    log = logger.bind(
        event_id=str(event.metadata.event_id),
        event_type=event.metadata.event_type,
        correlation_id=str(event.metadata.correlation_id),
    )

    # Idempotency check FIRST
    if await processed_events.exists(event.metadata.event_id):
        log.info("event.duplicate.skipped")
        return

    log.info("event.processing.started")
    start = time.monotonic()

    try:
        async with transaction():
            await reserve_inventory(event.items)
            await processed_events.record(event.metadata.event_id)

        duration_ms = (time.monotonic() - start) * 1000
        log.info("event.processing.completed", duration_ms=duration_ms)

    except Exception as e:
        log.error("event.processing.failed", error=str(e))
        raise  # AckPolicy.NACK_ON_ERROR will redeliver
```

### ✅ Manual Acknowledgment for Complex Flows

```python
from faststream import AckPolicy
from faststream.kafka import KafkaMessage
from faststream.exceptions import AckMessage, NackMessage, RejectMessage

@broker.subscriber("payments.process", ack_policy=AckPolicy.MANUAL)
async def process_payment(
    event: PaymentRequested,
    msg: KafkaMessage,  # Raw message for manual control
) -> None:
    try:
        result = await payment_gateway.charge(event.amount, event.token)

        if result.success:
            await msg.ack()
        elif result.retriable:
            await msg.nack()  # Redeliver
        else:
            await msg.reject()  # Send to DLQ

    except ValidationError:
        raise RejectMessage()  # Poison message, never retry
    except TimeoutError:
        raise NackMessage()  # Transient, retry


```

### ✅ Error Classification and DLQ Routing

```python
from enum import Enum
from pydantic import ValidationError

class ErrorClass(str, Enum):
    RETRIABLE = "retriable"
    NON_RETRIABLE = "non_retriable"

NON_RETRIABLE_ERRORS = (
    ValidationError,
    PermissionError,
    AuthenticationError,
    ValueError,
)

def classify_error(error: Exception) -> ErrorClass:
    if isinstance(error, NON_RETRIABLE_ERRORS):
        return ErrorClass.NON_RETRIABLE
    return ErrorClass.RETRIABLE

@broker.subscriber("events", ack_policy=AckPolicy.MANUAL)
async def with_dlq_routing(
    event: DomainEvent,
    msg: KafkaMessage,
    dlq_publisher: DLQPublisher,
) -> None:
    try:
        await process(event)
        await msg.ack()
    except Exception as e:
        if classify_error(e) == ErrorClass.NON_RETRIABLE:
            await dlq_publisher.send(event, error=e)
            await msg.ack()  # Don't redeliver poison messages
        else:
            await msg.nack()  # Retry via broker
```

### ✅ Structured Logging with Context

```python
import structlog
from faststream import Depends, Logger
from typing import Annotated

def bind_event_context(event: DomainEvent) -> structlog.BoundLogger:
    return structlog.get_logger().bind(
        event_id=str(event.metadata.event_id),
        event_type=event.metadata.event_type,
        correlation_id=str(event.metadata.correlation_id),
        causation_id=str(event.metadata.causation_id),
    )

@broker.subscriber("orders.placed")
async def handle_with_logging(
    event: OrderPlaced,
    logger: Logger,  # FastStream's injected logger
) -> None:
    log = bind_event_context(event)

    log.info("event.received")

    try:
        result = await process(event)
        log.info("event.processed", result_id=result.id)
    except Exception as e:
        log.error("event.failed", error=str(e), error_type=type(e).__name__)
        raise
```

### ✅ Testing with TestBroker

```python
import pytest
from faststream.kafka import TestKafkaBroker
from app.events import broker, handle_order_placed, OrderPlaced

@pytest.fixture
def sample_event() -> OrderPlaced:
    return OrderPlaced(
        metadata=EventMetadata(
            event_type="OrderPlaced.v1",
            correlation_id=uuid4(),
            causation_id=uuid4(),
            source="test",
        ),
        order_id=uuid4(),
        customer_id=uuid4(),
        customer_email="test@example.com",
        items=[],
        total=Money(100),
    )

@pytest.mark.asyncio
async def test_order_placed_handler(sample_event):
    async with TestKafkaBroker(broker) as tb:
        await tb.publish(sample_event, "orders.placed")

        # Assert handler was called with dict representation
        handle_order_placed.mock.assert_called_once_with(
            dict(sample_event)
        )

@pytest.mark.asyncio
async def test_idempotency(sample_event):
    """Same event published twice should only process once."""
    async with TestKafkaBroker(broker) as tb:
        await tb.publish(sample_event, "orders.placed")
        await tb.publish(sample_event, "orders.placed")  # Duplicate

        # Handler called twice, but processing should detect duplicate
        assert handle_order_placed.mock.call_count == 2

@pytest.mark.asyncio
async def test_validation_error():
    async with TestKafkaBroker(broker) as tb:
        with pytest.raises(ValidationError):
            await tb.publish({"invalid": "data"}, "orders.placed")
```

### ✅ Middleware for Observability

```python
from faststream import BaseMiddleware
from faststream.types import StreamMessage
from opentelemetry import trace
import time

class ObservabilityMiddleware(BaseMiddleware):
    def __init__(self, tracer_provider=None):
        self.tracer = trace.get_tracer(__name__, tracer_provider=tracer_provider)

    async def consume_scope(self, call_next, msg: StreamMessage):
        event_type = msg.headers.get("event_type", "unknown")
        correlation_id = msg.headers.get("correlation_id", "none")

        with self.tracer.start_as_current_span(f"consume:{event_type}") as span:
            span.set_attribute("messaging.correlation_id", correlation_id)
            start = time.monotonic()

            try:
                result = await call_next(msg)
                span.set_attribute("messaging.outcome", "success")
                return result
            except Exception as e:
                span.set_attribute("messaging.outcome", "failure")
                span.record_exception(e)
                raise
            finally:
                duration_ms = (time.monotonic() - start) * 1000
                span.set_attribute("messaging.duration_ms", duration_ms)

broker = KafkaBroker(middlewares=[ObservabilityMiddleware()])
```

### ✅ Publisher with Outbox Pattern Integration

```python
from faststream.kafka import KafkaBroker

broker = KafkaBroker("localhost:9092")
order_placed_publisher = broker.publisher("orders.placed")

class OutboxRelayer:
    """Polls outbox table and publishes to broker."""

    def __init__(self, session: AsyncSession, broker: KafkaBroker):
        self._session = session
        self._broker = broker

    async def relay_pending(self, batch_size: int = 100) -> int:
        entries = await self._session.execute(
            select(OutboxEntry)
            .where(OutboxEntry.published_at.is_(None))
            .limit(batch_size)
            .with_for_update(skip_locked=True)
        )

        count = 0
        for entry in entries.scalars():
            event = self._deserialize(entry)
            await self._broker.publish(
                event,
                entry.topic,
                headers={
                    "event_id": str(event.metadata.event_id),
                    "event_type": event.metadata.event_type,
                    "correlation_id": str(event.metadata.correlation_id),
                },
            )
            entry.published_at = datetime.utcnow()
            count += 1

        await self._session.commit()
        return count
```

---

## Anti-Patterns

### ❌ Keyword Broker Argument (Removed in 0.6)

```python
# WRONG: Raises error in FastStream 0.6+
app = FastStream(broker=broker)

# CORRECT: Positional only
app = FastStream(broker)
```

### ❌ Deprecated retry Parameter

```python
# WRONG: Deprecated, will be removed
@broker.subscriber("topic", retry=True)
async def handler(msg): ...

# CORRECT: Use AckPolicy
@broker.subscriber("topic", ack_policy=AckPolicy.NACK_ON_ERROR)
async def handler(msg): ...
```

### ❌ Processing Before Idempotency Check

```python
# WRONG: Side effects before deduplication
@broker.subscriber("payments")
async def bad_handler(event: PaymentReceived):
    await ledger.credit(event.amount)  # Runs on every delivery!

    if await processed.exists(event.metadata.event_id):
        return  # Too late, already credited

# CORRECT: Check first, then process
@broker.subscriber("payments")
async def good_handler(event: PaymentReceived):
    if await processed.exists(event.metadata.event_id):
        return  # Exit before any side effects

    async with transaction():
        await ledger.credit(event.amount)
        await processed.record(event.metadata.event_id)
```

### ❌ Blocking I/O in Async Handler

```python
# WRONG: Blocks event loop
import requests

@broker.subscriber("api-calls")
async def bad_handler(msg):
    response = requests.get(msg.url)  # Sync HTTP!
    return response.json()

# CORRECT: Use async client
import httpx

@broker.subscriber("api-calls")
async def good_handler(msg):
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(msg.url)
        return response.json()
```

### ❌ Missing Timeout on External Calls

```python
# WRONG: Can hang forever
@broker.subscriber("orders")
async def bad_handler(order: Order):
    await external_service.process(order)  # No timeout!

# CORRECT: Explicit timeout
@broker.subscriber("orders")
async def good_handler(order: Order):
    async with asyncio.timeout(30.0):
        await external_service.process(order)
```

### ❌ Swallowing Exceptions

```python
# WRONG: Message acked, error hidden
@broker.subscriber("critical")
async def bad_handler(event):
    try:
        await risky_operation(event)
    except Exception:
        pass  # Lost forever

# CORRECT: Log and re-raise for DLQ
@broker.subscriber("critical", ack_policy=AckPolicy.NACK_ON_ERROR)
async def good_handler(event, logger: Logger):
    try:
        await risky_operation(event)
    except Exception as e:
        logger.error("processing.failed", error=str(e))
        raise  # Will be redelivered or go to DLQ
```

### ❌ Anemic Event (ID Only)

```python
# WRONG: Forces callback query
class OrderPlaced(BaseModel):
    order_id: UUID  # Consumer must fetch details

# CORRECT: Self-contained payload
class OrderPlaced(BaseModel):
    order_id: UUID
    customer_id: UUID
    customer_email: str
    items: list[OrderItem]
    total: Money
```

### ❌ Missing Correlation Context

```python
# WRONG: No traceability across services
@broker.subscriber("orders")
@broker.publisher("inventory.reserve")
async def bad_handler(event: OrderPlaced) -> InventoryCommand:
    return InventoryCommand(items=event.items)  # Lost correlation!

# CORRECT: Propagate correlation context
@broker.subscriber("orders")
@broker.publisher("inventory.reserve")
async def good_handler(event: OrderPlaced) -> InventoryCommand:
    return InventoryCommand(
        metadata=EventMetadata(
            event_type="InventoryReserve.v1",
            correlation_id=event.metadata.correlation_id,  # Preserved
            causation_id=event.metadata.event_id,  # This event caused it
            source="order-service.handle_order",
        ),
        items=event.items,
    )
```

### ❌ Testing with Real Brokers

```python
# WRONG: Requires infrastructure, slow, flaky
@pytest.mark.asyncio
async def bad_test():
    broker = KafkaBroker("real-kafka:9092")
    await broker.start()
    # Slow, requires running Kafka

# CORRECT: In-memory testing
@pytest.mark.asyncio
async def good_test():
    async with TestKafkaBroker(broker) as tb:
        await tb.publish(event, "topic")
        handler.mock.assert_called_once()
```

### ❌ Global Mutable State

```python
# WRONG: Race conditions in concurrent processing
processed_count = 0

@broker.subscriber("events")
async def bad_handler(event):
    global processed_count
    processed_count += 1  # Not thread-safe!

# CORRECT: Use proper metrics or injected state
from prometheus_client import Counter

events_processed = Counter('events_processed_total', 'Total events')

@broker.subscriber("events")
async def good_handler(event):
    events_processed.inc()  # Thread-safe
```

---

## Version 0.6+ Migration Checklist

- [ ] Change `FastStream(broker=b)` → `FastStream(b)`
- [ ] Replace `retry=True` → `ack_policy=AckPolicy.NACK_ON_ERROR`
- [ ] Remove `from faststream import context` (use `ContextRepo`)
- [ ] Update middleware to `consume_scope`/`publish_scope` pattern
- [ ] Move AsyncAPI config to `specification=AsyncAPI(...)`
- [ ] Verify Python 3.10+ (3.8/3.9 dropped)

---

## Quick Reference

| Task | Pattern |
|------|---------|
| Create app | `app = FastStream(broker)` |
| Subscribe | `@broker.subscriber("topic")` |
| Publish (return) | `@broker.publisher("topic")` on handler |
| Publish (manual) | `await broker.publish(msg, "topic")` |
| Retry on error | `ack_policy=AckPolicy.NACK_ON_ERROR` |
| Manual ack | `ack_policy=AckPolicy.MANUAL` + `msg.ack()` |
| Reject poison | `raise RejectMessage()` |
| Retry explicitly | `raise NackMessage()` |
| Get logger | `logger: Logger` parameter |
| Test handler | `async with TestKafkaBroker(broker)` |
| Add tracing | `middlewares=[TelemetryMiddleware()]` |
