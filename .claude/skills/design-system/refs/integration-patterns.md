# Integration Patterns Reference

> Patterns for connecting services, handling cross-boundary communication, and managing distributed workflows.

---

## Integration Decision Framework

```
┌─────────────────────────────────────────────────────────────┐
│              INTEGRATION PATTERN SELECTION                  │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
              ┌────────────────────────┐
              │  Does caller need      │
              │  immediate response?   │
              └───────────┬────────────┘
                          │
            ┌─────────────┴─────────────┐
            │                           │
           YES                         NO
            │                           │
            ▼                           ▼
    ┌───────────────┐          ┌───────────────┐
    │ SYNCHRONOUS   │          │ ASYNCHRONOUS  │
    │ REST / gRPC   │          │ Events / Queue│
    └───────┬───────┘          └───────┬───────┘
            │                           │
            ▼                           ▼
    ┌───────────────┐          ┌───────────────┐
    │ Query or      │          │ Single step   │
    │ Command?      │          │ or multi-step?│
    └───────────────┘          └───────────────┘
            │                           │
    ┌───────┴───────┐          ┌───────┴───────┐
  Query          Command     Single        Multi
    │               │           │              │
    ▼               ▼           ▼              ▼
┌───────┐     ┌───────┐   ┌───────┐     ┌───────┐
│ REST  │     │ REST  │   │ Event │     │ SAGA  │
│ GET   │     │ POST  │   │ Fire  │     │Pattern│
└───────┘     └───────┘   └───────┘     └───────┘
```

---

## 1. Synchronous Patterns

### REST API Integration

**When to Use:**







- User-blocking operations requiring immediate feedback
- Query operations (GET)
- Simple request-response workflows
- External API integration

**Pattern: API Gateway**

```
┌──────────┐     ┌─────────────┐     ┌─────────────┐
│  Client  │────▶│ API Gateway │────▶│  Service A  │
└──────────┘     │             │     └─────────────┘
                 │  • Auth     │
                 │  • Rate     │     ┌─────────────┐
                 │    Limit    │────▶│  Service B  │

                 │  • Route    │     └─────────────┘

                 │  • Transform│

                 └─────────────┘

```





**Best Practices:**



- Version APIs in URL or header

- Use proper HTTP semantics (status codes, methods)

- Implement timeout on every call

- Add circuit breaker for downstream services

- Propagate correlation IDs



**Anti-Patterns:**

- Synchronous chains longer than 2 hops

- No timeout configuration
- Blocking on non-critical dependencies



### gRPC Integration


**When to Use:**

- Internal service-to-service communication
- High-performance requirements

- Streaming data
- Strong contract requirements


**Pattern: Service Mesh with gRPC**


```

┌─────────────┐                    ┌─────────────┐
│  Service A  │   gRPC (HTTP/2)   │  Service B  │

│   ┌─────┐   │◀─────────────────▶│   ┌─────┐   │
│   │Envoy│   │   Protobuf/mTLS   │   │Envoy│   │

│   │Proxy│   │                    │   │Proxy│   │
│   └─────┘   │                    │   └─────┘   │

└─────────────┘                    └─────────────┘
```


**Best Practices:**


- Define contracts in .proto files
- Use streaming for large payloads

- Implement deadlines (not just timeouts)
- Handle backpressure in streams


---


## 2. Asynchronous Patterns


### Event-Driven Integration

**When to Use:**

- Cross-domain communication
- Fire-and-forget notifications

- Decoupling producers from consumers
- Multiple consumers need same data

**Pattern: Domain Events**

```


┌─────────────┐                              ┌─────────────┐
│   Orders    │     OrderPlaced Event       │  Inventory  │
│   Service   │────────────────────────────▶│   Service   │
└─────────────┘            │                └─────────────┘
                           │
                           │                ┌─────────────┐


                           └───────────────▶│  Shipping   │
                                           │   Service   │
                                           └─────────────┘
```

**Event Design Rules:**


1. Events are facts (past tense): `OrderPlaced`, not `PlaceOrder`
2. Include all context needed by consumers
3. Events are immutable
4. Version events for evolution

**Event Schema:**
```json

{
  "eventId": "evt_01HQXZ...",
  "eventType": "order.placed",

  "eventVersion": "1.0",
  "timestamp": "2026-01-18T10:00:00Z",
  "aggregateId": "ord_123",
  "aggregateType": "Order",

  "correlationId": "req_456",
  "causationId": "evt_prev",
  "data": {

    "orderId": "ord_123",
    "customerId": "cust_789",
    "items": [...],
    "total": 99.99

  }
}
```


### Message Queue Integration

**When to Use:**

- Work distribution
- Load leveling
- Reliable delivery required

- Single consumer per message

**Pattern: Competing Consumers**

```
                    ┌─────────────┐
                    │  Producer   │
                    └──────┬──────┘

                           │
                           ▼
                    ┌─────────────┐
                    │    Queue    │
                    └──────┬──────┘
                           │
         ┌─────────────────┼─────────────────┐
         │                 │                 │

         ▼                 ▼                 ▼
    ┌─────────┐       ┌─────────┐       ┌─────────┐
    │Consumer │       │Consumer │       │Consumer │
    │    1    │       │    2    │       │    3    │
    └─────────┘       └─────────┘       └─────────┘
```

**Best Practices:**

- Make consumers idempotent
- Use dead letter queues
- Implement visibility timeout
- Monitor queue depth

---

## 3. Saga Pattern (Distributed Transactions)

### When to Use Saga

- Multi-step business process across services
- Each step requires atomic commit
- Compensation needed on failure
- Strong consistency not required

### Choreography Saga

Each service reacts to events and publishes next event:

```
┌─────────────┐     OrderPlaced     ┌─────────────┐
│   Orders    │────────────────────▶│  Payments   │
└─────────────┘                     └──────┬──────┘
       ▲                                   │
       │                          PaymentCompleted
       │                                   │
       │ OrderShipped                      ▼
       │                           ┌─────────────┐
       └───────────────────────────│  Inventory  │
                                   └──────┬──────┘
                                          │
                                  InventoryReserved
                                          │
                                          ▼
                                   ┌─────────────┐
                                   │  Shipping   │
                                   └─────────────┘
```

**Compensation (on failure):**
```
Payment Failed
      │
      ▼
┌─────────────┐  ReleaseInventory  ┌─────────────┐
│   Orders    │◀───────────────────│  Inventory  │
│  (Cancel)   │                    │  (Rollback) │
└─────────────┘                    └─────────────┘
```

### Orchestration Saga

Central orchestrator coordinates steps:

```
                    ┌─────────────────────┐
                    │   Saga Orchestrator │
                    │    (Order Saga)     │
                    └──────────┬──────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        │                      │                      │
        ▼                      ▼                      ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│ 1. Reserve    │    │ 2. Process    │    │ 3. Ship       │
│    Inventory  │    │    Payment    │    │    Order      │
└───────────────┘    └───────────────┘    └───────────────┘
        │                      │                      │
        ▼                      ▼                      ▼
   [Success/Fail]        [Success/Fail]        [Success/Fail]
        │                      │                      │
        └──────────────────────┼──────────────────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Compensate if any   │
                    │ step failed         │
                    └─────────────────────┘
```

**Orchestrator State Machine:**
```
┌─────────┐    ┌───────────────┐    ┌───────────────┐    ┌──────────┐
│ PENDING │───▶│ RESERVING_INV │───▶│ PROCESSING_PAY│───▶│ SHIPPING │
└─────────┘    └───────────────┘    └───────────────┘    └────┬─────┘
                      │                     │                  │
                      ▼                     ▼                  ▼
               ┌─────────────┐       ┌─────────────┐    ┌──────────┐
               │ COMPENSATING│◀──────│ COMPENSATING│    │COMPLETED │
               └─────────────┘       └─────────────┘    └──────────┘
```

### Choosing Between Choreography and Orchestration

| Aspect | Choreography | Orchestration |
|--------|--------------|---------------|
| Coupling | Loose | Central coordinator |
| Visibility | Distributed | Centralized |
| Complexity | Emergent | Explicit |
| Failure handling | Each service | Orchestrator |
| Testing | Harder | Easier |
| Best for | Simple flows | Complex workflows |

---

## 4. Anti-Corruption Layer (ACL)

### When to Use

- Integrating with legacy systems
- External APIs with different domain models
- Protecting domain model from external concepts

### Pattern

```
┌─────────────────────────────────────────────────────────────┐
│                    YOUR BOUNDED CONTEXT                     │
│                                                             │
│  ┌─────────────┐                    ┌───────────────────┐  │
│  │   Domain    │                    │ Anti-Corruption   │  │
│  │   Model     │◀──── Adapts ──────│      Layer        │  │
│  │             │                    │                   │  │
│  │ • Customer  │                    │ • Translates      │  │
│  │ • Order     │                    │ • Validates       │  │
│  │ • Product   │                    │ • Isolates        │  │
│  └─────────────┘                    └─────────┬─────────┘  │
│                                               │            │
└───────────────────────────────────────────────┼────────────┘
                                                │
                              ┌─────────────────┼─────────────────┐
                              │                 │                 │
                              ▼                 ▼                 ▼
                       ┌───────────┐     ┌───────────┐     ┌───────────┐
                       │  Legacy   │     │  External │     │  Partner  │
                       │  System   │     │    API    │     │    API    │
                       └───────────┘     └───────────┘     └───────────┘
```

### Implementation

```python
# ACL Adapter Example
class LegacyCustomerAdapter:
    """Translates legacy CRM data to our Customer model."""

    def __init__(self, legacy_client: LegacyCRMClient):
        self._client = legacy_client

    def get_customer(self, customer_id: CustomerId) -> Customer:
        # Fetch from legacy system (their model)
        legacy_data = self._client.fetch_account(str(customer_id))

        # Translate to our domain model
        return Customer(
            id=customer_id,
            name=CustomerName(
                first=legacy_data['FNAME'],
                last=legacy_data['LNAME']
            ),
            email=Email(legacy_data['EMAIL_ADDR']),
            status=self._map_status(legacy_data['ACCT_STATUS'])
        )

    def _map_status(self, legacy_status: str) -> CustomerStatus:
        mapping = {
            'A': CustomerStatus.ACTIVE,
            'I': CustomerStatus.INACTIVE,
            'S': CustomerStatus.SUSPENDED
        }
        return mapping.get(legacy_status, CustomerStatus.UNKNOWN)
```

---

## 5. Outbox Pattern

### Problem

Dual write problem: updating database AND publishing event must be atomic.

```
# WRONG: Non-atomic dual write
def place_order(order: Order):
    db.save(order)      # Step 1: Database commit
    events.publish(     # Step 2: Message publish
        OrderPlaced(order)
    )
    # What if publish fails after commit?
```

### Solution: Transactional Outbox

```
┌─────────────────────────────────────────────────────────────┐
│                      SERVICE                                │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              SINGLE TRANSACTION                      │   │
│  │                                                      │   │
│  │  ┌─────────────┐         ┌─────────────────────┐    │   │
│  │  │   Orders    │         │    Outbox Table     │    │   │
│  │  │   Table     │         │                     │    │   │
│  │  │             │         │ id | event | status │    │   │
│  │  │ INSERT INTO │         │ INSERT INTO         │    │   │
│  │  │ orders...   │         │ outbox...           │    │   │
│  │  └─────────────┘         └─────────────────────┘    │   │
│  │                                                      │   │
│  └──────────────────────────────────────────────────────┘   │
│                                    │                        │
│                                    │                        │
│  ┌─────────────────────────────────┼────────────────────┐   │
│  │         OUTBOX PROCESSOR        │                    │   │
│  │                                 ▼                    │   │
│  │  Poll outbox ──▶ Publish ──▶ Mark processed        │   │
│  └──────────────────────────────────────────────────────┘   │
│                                    │                        │
└────────────────────────────────────┼────────────────────────┘
                                     │
                                     ▼
                            ┌─────────────────┐
                            │  Message Broker │
                            └─────────────────┘
```

### Implementation

```sql
-- Outbox table
CREATE TABLE outbox (
    id UUID PRIMARY KEY,
    aggregate_type VARCHAR(255) NOT NULL,
    aggregate_id VARCHAR(255) NOT NULL,
    event_type VARCHAR(255) NOT NULL,
    payload JSONB NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    processed_at TIMESTAMP NULL
);

-- Single transaction
BEGIN;
    INSERT INTO orders (...) VALUES (...);
    INSERT INTO outbox (id, aggregate_type, aggregate_id, event_type, payload)
    VALUES (gen_random_uuid(), 'Order', 'ord_123', 'OrderPlaced', '{"..."}');
COMMIT;
```

---

## 6. Idempotency Patterns

### Problem

Messages may be delivered more than once. Handlers must be idempotent.

### Solutions

**1. Idempotency Key:**
```python
class PaymentHandler:
    def handle(self, event: PaymentRequested):
        # Check if already processed
        if self.processed_events.exists(event.event_id):
            return  # Skip duplicate

        # Process
        self.payment_service.process(event.payment)

        # Mark as processed
        self.processed_events.add(event.event_id)
```

**2. Natural Idempotency:**
```python
# Setting state is naturally idempotent
def handle_payment_completed(self, event: PaymentCompleted):
    order = self.orders.get(event.order_id)
    order.mark_paid()  # Idempotent: multiple calls = same result
    self.orders.save(order)
```

**3. Deduplication Table:**
```sql
CREATE TABLE processed_events (
    event_id UUID PRIMARY KEY,
    processed_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- In transaction
INSERT INTO processed_events (event_id) VALUES ($1)
ON CONFLICT (event_id) DO NOTHING;
-- If inserted, process. If conflict, skip.
```

---

## Integration Checklist

Before finalizing integration design:

- [ ] Communication pattern (sync/async) justified for each interaction
- [ ] All synchronous calls have timeouts and circuit breakers
- [ ] Events are versioned and include correlation IDs
- [ ] Sagas have compensation logic for all steps
- [ ] Anti-corruption layers protect domain boundaries
- [ ] Outbox pattern used where atomic publish required
- [ ] All handlers are idempotent
- [ ] Dead letter queues configured for failed messages
- [ ] Retry policies with backoff defined
