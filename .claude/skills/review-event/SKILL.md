---
name: review-event
version: 1.0.0

description: |
  Review event handlers, producers, and consumers for correctness and production-readiness.
  Use when reviewing event implementations, validating message handlers, assessing Kafka/RabbitMQ code,
  or checking event-driven patterns after implementation.
  Relevant for FastStream, Celery, asyncio event handlers, domain events, outbox pattern, DLQ routing.

chains:
  invoked-by:
    - skill: implement/event
      context: "Post-implementation quality gate"
    - skill: implement/python
      context: "When event handlers detected in changes"
  invokes:
    - skill: implement/event
      when: "Critical or major findings detected"
    - skill: review/observability
      when: "Observability gaps identified"
---

# Event Handler Review

> Validate event implementations for idempotency, reliability, and production-readiness.

## Quick Reference

| Aspect | Details |
|--------|---------|
| **Scope** | Event models, producers, consumers, handlers, DLQ routing |
| **Invoked By** | `implement/event`, `implement/python`, `/review` command |
| **Invokes** | `implement/event` (on failure), `review/observability` |
| **Verdicts** | `PASS` · `PASS_WITH_SUGGESTIONS` · `NEEDS_WORK` · `FAIL` |

---

## Review Objective

Ensure event handlers are idempotent, observable, resilient, and follow event-driven best practices.

**Key Questions:**







1. Are consumers protected against duplicate delivery?
2. Do producers use transactional outbox?
3. Is error handling classified with DLQ routing?
4. Are handlers observable with correlation context?

**Out of Scope:** Business logic (`review/functionality`), Python style (`review/style`)

---

## Workflow

1. **SCOPE** → Find `**/events/**/*.py`, `**/handlers/**/*.py`, `**/consumers/**/*.py`, `**/producers/**/*.py`
2. **CONTEXT** → Load `rules/principles.md`, `skills/implement/event/refs/faststream.md`
3. **ANALYZE** → Apply criteria by priority: P0 Idempotency → P1 Errors → P2 Observability → P3 Schema
4. **CLASSIFY** → 🔴 BLOCKER | 🟠 CRITICAL | 🟡 MAJOR | 🔵 MINOR | ⚪ SUGGESTION | 🟢 COMMENDATION
5. **VERDICT** → BLOCKER=FAIL, CRITICAL=NEEDS_WORK, multiple MAJOR=NEEDS_WORK, else PASS variants
6. **CHAIN** → FAIL/NEEDS_WORK → `implement/event`

---

## Evaluation Criteria

### Idempotency & Data Integrity (ID)

| ID | Criterion | Severity | Check |
|----|-----------|----------|-------|
| ID.1 | Idempotency check before ANY processing | BLOCKER | First op is dedup check |
| ID.2 | Event ID recorded atomically with business op | BLOCKER | Same transaction |
| ID.3 | Producer uses transactional outbox | BLOCKER | Outbox in same DB txn |
| ID.4 | Idempotency key from business operation | CRITICAL | Not random UUID |
| ID.5 | No side effects before idempotency guard | BLOCKER | Nothing modifies state first |

### Error Handling & Resilience (EH)

| ID | Criterion | Severity | Check |
|----|-----------|----------|-------|
| EH.1 | Errors classified retriable vs non-retriable | CRITICAL | Explicit classification |
| EH.2 | DLQ routing after max retries | CRITICAL | DLQ on exhaustion |
| EH.3 | Exponential backoff with jitter | MAJOR | Not fixed delays |
| EH.4 | Explicit timeout on external calls | BLOCKER | `asyncio.timeout()` |
| EH.5 | Exceptions not swallowed silently | CRITICAL | No empty `except` |
| EH.6 | Error context preserved for DLQ | MAJOR | Stack trace included |

### Observability & Tracing (OB)

| ID | Criterion | Severity | Check |
|----|-----------|----------|-------|
| OB.1 | Structured logging with event context | MAJOR | `event_id`, `correlation_id` logged |
| OB.2 | Correlation ID propagated downstream | CRITICAL | Not dropped |
| OB.3 | Appropriate log levels | MINOR | INFO success, ERROR failure |
| OB.4 | Duration metrics captured | MAJOR | Processing time logged |
| OB.5 | No PII in payload logs | CRITICAL | Full payload not logged |

### Schema & Model Design (SM)

| ID | Criterion | Severity | Check |
|----|-----------|----------|-------|
| SM.1 | Metadata envelope present | CRITICAL | event_id, correlation_id, causation_id |
| SM.2 | Event model immutable | MAJOR | `frozen=True` |
| SM.3 | Past tense naming | MINOR | `OrderPlaced` not `PlaceOrder` |
| SM.4 | Payload self-contained | MAJOR | No callback queries needed |

### FastStream Specific (FS)

| ID | Criterion | Severity | Check |
|----|-----------|----------|-------|
| FS.1 | `AckPolicy` not deprecated `retry` | MAJOR | No `retry=True` |
| FS.2 | Broker as positional arg | BLOCKER | `FastStream(broker)` |
| FS.3 | Async handlers only | CRITICAL | `async def` |
| FS.4 | Pydantic-typed parameters | MAJOR | No `dict` or untyped |

---

## Patterns

### ✅ Good Pattern

```python
@broker.subscriber("orders.placed", ack_policy=AckPolicy.NACK_ON_ERROR)
async def handle_order_placed(event: OrderPlaced, processed: ProcessedEventStore) -> None:
    log = logger.bind(event_id=str(event.metadata.event_id), correlation_id=str(event.metadata.correlation_id))
    if await processed.exists(event.metadata.event_id):  # Idempotency FIRST
        log.info("event.duplicate.skipped")
        return
    log.info("event.processing.started")
    async with asyncio.timeout(30.0):
        async with transaction():
            await process_order(event)
            await processed.record(event.metadata.event_id)  # Atomic with business op
    log.info("event.processing.completed")
```

### ❌ Bad Pattern

```python
@broker.subscriber("payments", retry=True)  # Deprecated!
async def bad_handler(event: PaymentReceived):
    await ledger.credit(event.amount)  # Side effect BEFORE dedup!
    if await processed.exists(event.metadata.event_id):
        return  # Too late - already credited
```

---

## Finding Format

```markdown
### [🔴 BLOCKER] {{Title}}
**Location:** `{{file}}:{{line}}`
**Criterion:** {{ID}} - {{Name}}
**Issue:** {{Description}}
**Evidence:** ```python ... ```
**Suggestion:** {{Fix}}
**Rationale:** {{Why it matters}}
```

---

## Skill Chaining

| Verdict | Action | Target |
|---------|--------|--------|
| `FAIL` | Mandatory fix | `implement/event` |
| `NEEDS_WORK` | Targeted fix | `implement/event` |
| `PASS_WITH_SUGGESTIONS` | Optional | None |
| `PASS` | Continue | `test/unit` |

**Handoff:** `**Chain Target:** implement/event` `**Priority Findings:** [IDs]` `**Constraint:** Preserve business logic`

---

## Quality Gates

- [ ] All event handlers analyzed
- [ ] Idempotency checked for every consumer
- [ ] Producer transactional guarantees verified
- [ ] Each finding has location + criterion + severity
- [ ] Verdict aligns with findings
- [ ] Chain decision explicit
