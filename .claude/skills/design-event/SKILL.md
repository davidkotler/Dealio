---
name: design-event
version: 2.0.0
description: |
  Design event schemas, producers, and consumers before implementation.
  Use when creating event handlers, publishing domain events, designing async messaging,
  planning event-driven integrations, or implementing saga patterns.
  Relevant for Kafka, RabbitMQ, SQS, EventBridge, domain events, CQRS.
---

# Event Design

> Design event contracts, participants, behavior, and Pydantic models before writing implementation code.
> AsyncAPI specs are generated from code — this skill produces the design thinking that precedes code.

## Quick Reference

| Aspect | Details |
|--------|---------|
| **Invokes** | `implement/event`, `implement/pydantic`, `design/api` |
| **Invoked By** | `design/code`, `implement/python`, `design/api` |
| **Key Artifacts** | Participants registry, event Pydantic models, behavior spec, expected outcomes |

---

## Core Workflow

1. **Classify**: Determine event type (domain, integration, notification)
2. **Name**: Apply past-tense domain language naming
3. **Participants**: Define producers and consumers with clear responsibilities
4. **Model**: Design Pydantic payload with metadata envelope
5. **Behavior**: Specify happy path, edge cases, failure modes, and expected outcomes
6. **Validate**: Check against quality gates before implementation

---

## Design Artifacts

### Artifact 1: Participants Registry

For each event, define WHO produces it, WHO consumes it, and WHAT each party is responsible for.

```markdown
## Event: OrderPlaced.v1

### Producer: OrderService
- **Trigger**: Customer completes checkout successfully
- **Responsibility**: Validate order, persist to DB, emit event in same transaction (outbox)
- **Idempotency key**: Derived from `order_id`
- **Partition key**: `customer_id` (ensures ordering per customer)

### Consumer: InventoryService
- **Responsibility**: Reserve stock for ordered items
- **Idempotency**: Deduplicate by `event_id` in processed_events table
- **Failure strategy**: Retry 3x with exponential backoff, then DLQ
- **SLA**: Process within 5s of receipt

### Consumer: NotificationService
- **Responsibility**: Send order confirmation email to customer
- **Idempotency**: Deduplicate by `order_id` + `notification_type`
- **Failure strategy**: Retry 3x, then DLQ (non-critical, no compensation needed)
- **SLA**: Process within 30s of receipt
```

### Artifact 2: Event Pydantic Models

Design self-contained payload models. Consumer needs no callbacks to the producer.

```python
from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID

class EventMetadata(BaseModel):
    """Standard envelope for all events."""
    event_id: UUID = Field(description="Unique identifier for this event instance")
    event_type: str = Field(description="Versioned event type: 'OrderPlaced.v1'")
    timestamp: datetime = Field(description="When the event occurred (ISO 8601)")
    correlation_id: UUID = Field(description="Traces request across services")
    causation_id: UUID = Field(description="ID of event/command that caused this")
    source: str = Field(description="Producing service and handler")
    schema_version: str = Field(description="Semantic version of payload schema")

class OrderPlaced(BaseModel):
    """All data consumers need -- no callbacks required."""
    metadata: EventMetadata
    order_id: UUID
    customer_id: UUID
    customer_email: str          # Included so NotificationService doesn't call back
    items: list[OrderItem]       # Full item details for InventoryService
    total: Money
    shipping_address: Address    # Complete address for ShippingService
    placed_at: datetime
```

### Artifact 3: Behavior Specification

For each event, document the happy path, edge cases, and expected outcomes.

```markdown
## Behavior: OrderPlaced.v1

### Happy Path
1. Customer completes checkout
2. OrderService validates order, persists to DB
3. OrderService writes event to outbox (same transaction)
4. Outbox relay publishes event to broker
5. InventoryService reserves stock -> emits `InventoryReserved.v1`
6. NotificationService sends confirmation email

### Edge Cases
| Scenario | Behavior | Outcome |
|----------|----------|---------|
| Duplicate event delivered | Consumer checks `event_id` in processed_events | Skipped, logged as duplicate |
| Insufficient stock | InventoryService cannot reserve | Emits `InventoryReservationFailed.v1`, saga compensates |
| Customer email invalid | NotificationService fails to send | Routes to DLQ, no saga compensation (non-critical) |
| Producer DB write succeeds, outbox write fails | Impossible -- same transaction | N/A (transactional outbox guarantees atomicity) |
| Consumer crashes mid-processing | Message not acknowledged | Broker redelivers, consumer retries idempotently |

### Expected Outcomes
| Consumer | Success State | Observable Effect |
|----------|---------------|-------------------|
| InventoryService | Stock reserved for all items | `InventoryReserved.v1` emitted, stock decremented |
| NotificationService | Email sent | Confirmation email in customer inbox |
```

---

## Must / Never

### Event Naming

**MUST:**
- Use past tense verbs: `OrderPlaced`, `PaymentReceived`, `UserRegistered`
- Use domain ubiquitous language, not technical terms
- Include bounded context prefix for integration events: `Payments.PaymentCompleted`
- Version event types from day one: `OrderPlaced.v1`

**NEVER:**
- Use imperative names: ~~`CreateOrder`~~, ~~`ProcessPayment`~~
- Use generic names: ~~`DataChanged`~~, ~~`EntityUpdated`~~
- Use CRUD terminology: ~~`OrderCreated`~~, ~~`OrderDeleted`~~ (prefer domain terms)
- Include implementation details in names: ~~`KafkaOrderMessage`~~

### Event Schema

**MUST:**
- Include metadata envelope: `event_id`, `event_type`, `timestamp`, `correlation_id`, `causation_id`, `source`, `schema_version`
- Make payload self-contained -- consumer needs no callbacks
- Use semantic versioning for schema changes
- Document all fields with descriptions and examples

**NEVER:**
- Put large binary payloads in events (use claim-check pattern)
- Include sensitive data (PII, secrets) without encryption
- Reference entities by ID only without context (anemic events)
- Nest deeper than 3 levels in payload structure
- Use `Any` or untyped fields in schemas

### Event Producers

**MUST:**
- Use transactional outbox pattern for reliable publishing
- Ensure exactly-one-publish per business operation
- Include idempotency key derived from business operation
- Set appropriate partition/routing key for ordering requirements

**NEVER:**
- Publish events outside database transaction boundary
- Fire-and-forget without delivery confirmation
- Publish multiple events that must be processed atomically

### Event Consumers

**MUST:**
- Design for at-least-once delivery (assume duplicates)
- Implement idempotency using event ID or business key
- Define explicit dead-letter queue (DLQ) strategy
- Set processing timeout shorter than visibility timeout
- Preserve and propagate correlation context

**NEVER:**
- Assume exactly-once delivery
- Rely on event ordering across partitions
- Block indefinitely on external calls
- Swallow exceptions without DLQ routing
- Create bidirectional event dependencies between services

---

## When -> Then

| When | Then |
|------|------|
| State change in aggregate | Emit domain event from aggregate root |
| Cross-domain communication needed | Use integration event with ACL translation |
| Consumer needs all data | Event-Carried State Transfer (fat event) |
| Payload would exceed 256KB | Claim-check pattern: store payload, reference in event |
| Ordering required for entity | Partition by entity ID |
| Long-running process spans services | Design saga with compensating events |
| Consumer repeatedly fails | Route to DLQ after N retries with backoff |
| Multiple consumers need same event | Pub/sub with consumer groups |
| Request-response semantics needed | Use synchronous API, not events |
| Read/write patterns diverge | CQRS: events update read projections |
| Schema must change | Add fields (backward compatible) or new version |

---

## Decision Tree

```
Event Design Request
|
+--> What triggers it?
|   +--> State change in domain --> Domain Event
|   +--> Cross-service integration --> Integration Event
|   +--> Notification/signal only --> Notification Event
|
+--> Who consumes it?
|   +--> Same bounded context --> Internal event (simple schema)
|   +--> Different context/team --> Public event (full contract)
|
+--> How much data?
|   +--> < 256KB --> Include in payload
|   +--> > 256KB --> Claim-check pattern
|
+--> Ordering required?
|   +--> Yes, per entity --> Partition by entity ID
|   +--> Yes, global --> Single partition (bottleneck!)
|   +--> No --> Default partitioning
|
+--> Failure handling?
    +--> Retriable --> Exponential backoff -> DLQ
    +--> Non-retriable --> Immediate DLQ
    +--> Critical --> Alert + manual intervention
```

---

## Anti-Patterns

### Anemic Event (ID Only)

```python
# Wrong -- forces consumer to call back
class OrderPlaced(BaseModel):
    order_id: UUID  # Consumer must fetch order details

# Correct -- self-contained
class OrderPlaced(BaseModel):
    order_id: UUID
    customer_id: UUID
    items: list[OrderItem]
    total: Money
```

### Command Disguised as Event

```python
# Wrong -- imperative, expects action
class ProcessPayment(BaseModel):  # This is a command, not an event
    order_id: UUID
    amount: Decimal

# Correct -- fact that occurred
class PaymentRequested(BaseModel):
    order_id: UUID
    amount: Decimal
    requested_at: datetime
```

### Missing Idempotency

```python
# Wrong -- creates duplicate on retry
async def handle_payment_received(event: PaymentReceived):
    await credit_account(event.amount)  # Runs twice on retry!

# Correct -- idempotent with deduplication
async def handle_payment_received(event: PaymentReceived):
    if await ledger.has_entry(event.metadata.event_id):
        return
    await credit_account(event.amount, idempotency_key=event.metadata.event_id)
```

---

## Saga Design Template

For multi-step processes across services:

```markdown
## Saga: OrderFulfillment

### Steps
| Step | Action | Success Event | Failure Event |
|------|--------|---------------|---------------|
| 1 | Reserve inventory | InventoryReserved.v1 | InventoryReservationFailed.v1 |
| 2 | Process payment | PaymentCompleted.v1 | PaymentFailed.v1 |
| 3 | Ship order | ShipmentDispatched.v1 | ShipmentFailed.v1 |

### Compensations
| On Failure At | Compensate |
|---------------|------------|
| Step 2 (payment) | Release inventory (InventoryReleased.v1) |
| Step 3 (shipping) | Refund payment (PaymentRefunded.v1), Release inventory |
```

---

## Skill Chaining

| Condition | Invoke | Handoff Context |
|-----------|--------|-----------------|
| Ready to implement handlers | `implement/event` | Participants registry, Pydantic models |
| Complex payload models | `implement/pydantic` | Field definitions, validations |
| Event triggers API response | `design/api` | Webhook/callback contract |
| Database projections needed | `design/data` | Read model schema |
| Saga coordination required | `design/event` (recursive) | Saga state machine |

---

## Quality Gates

Before proceeding to implementation:

- [ ] Event named in past tense using domain language
- [ ] Metadata envelope includes all required fields
- [ ] Payload is self-contained (no callback queries needed)
- [ ] Schema version defined
- [ ] Producers listed with trigger, idempotency key, and partition key
- [ ] Each consumer has: responsibility, idempotency strategy, failure strategy, SLA
- [ ] Happy path documented step-by-step
- [ ] Edge cases enumerated with behavior and outcome
- [ ] Expected outcomes defined per consumer (success state + observable effect)
- [ ] Backward compatibility approach documented
