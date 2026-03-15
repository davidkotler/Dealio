---
name: observe-traces
version: 1.0.0
description: |
  Add OpenTelemetry distributed tracing to Python code. Use when instrumenting
  services, adding spans to I/O operations, tracing async workflows, or debugging
  distributed systems. Relevant for Python backends, FastAPI, async code, microservices.
---

# OpenTelemetry Tracing

> Instrument Python code with distributed traces for production observability.

## Quick Reference

| Aspect | Details |
|--------|---------|
| **Invokes** | `test/unit` |
| **Invoked By** | `implement/python`, `implement/api`, `optimize/performance` |
| **Key Tools** | Read, Edit, Write |
| **Tracer** | Module-level only: `tracer = trace.get_tracer(__name__)` |

---

## Core Workflow

1. **Locate**: Find modules with I/O boundaries (HTTP, DB, cache, queues)
2. **Acquire**: Add module-level tracer (never in functions or `__init__`)
3. **Span**: Create spans at I/O boundaries, not pure computation
4. **Attribute**: Add low-cardinality attributes using semantic conventions
5. **Error**: Record exceptions with `record_exception()` + `set_status(ERROR)`
6. **Propagate**: Use `contextvars.copy_context()` for async task fan-out
7. **Validate**: Chain to `test/unit` to verify span creation

---

## Critical Rules

### MUST

- Acquire tracer at **module level**: `tracer = trace.get_tracer(__name__)`
- Use **static span names**: `<component>.<operation>` format, lowercase, dot-separated
- Keep attribute cardinality **< 100 unique values**
- Use **semantic conventions** first: `SpanAttributes.HTTP_REQUEST_METHOD`
- Call **both** `record_exception()` and `set_status(ERROR)` on failures
- Copy context for async: `ctx = contextvars.copy_context()`
- Create spans for **I/O boundaries** and **significant business operations**

### NEVER

- Put tracer in function body or `__init__`
- Include variables in span names (causes cardinality explosion)
- Call `set_status(StatusCode.OK)` explicitly (it's implicit)
- Trace pure CPU computation, simple getters, or loop iterations
- Store PII in attributes (emails, names, tokens, credentials)
- Use `asyncio.create_task()` without copying context first

---

## Decision Tree: When to Create Spans

```
Operation Type
│
├─► I/O Boundary? ──────────────────► ✅ CREATE SPAN
│   (HTTP, DB, cache, queue, external API)
│
├─► Significant Business Operation? ─► ✅ CREATE SPAN
│   (order creation, payment, auth)
│
├─► Pure CPU Computation? ──────────► ❌ SKIP
│
├─► Simple Getter/Setter? ──────────► ❌ SKIP
│
└─► Loop Iteration? ────────────────► ❌ SKIP
```

---

## Patterns

### ✅ Correct: Module-Level Tracer + Static Name

```python
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

tracer = trace.get_tracer(__name__)  # Module level

class OrderService:
    async def create_order(self, data: OrderCreate) -> Order:
        with tracer.start_as_current_span("order_service.create_order") as span:
            span.set_attribute("myapp.order.type", data.type.value)
            try:
                return await self._persist(data)
            except OrderError as exc:
                span.record_exception(exc)
                span.set_status(Status(StatusCode.ERROR, str(exc)))
                raise
```

### ✅ Correct: Async Context Propagation

```python
import contextvars
import asyncio

async def fan_out(self, items: list[Item]) -> list[Result]:
    with tracer.start_as_current_span("processor.fan_out") as span:
        ctx = contextvars.copy_context()  # Capture before spawning

        async def process(item: Item) -> Result:
            with tracer.start_as_current_span("processor.process_item"):
                return await compute(item)

        tasks = [asyncio.create_task(ctx.run(process, item)) for item in items]
        return await asyncio.gather(*tasks)
```

### ✅ Correct: Semantic Conventions First

```python
from opentelemetry.semconv.trace import SpanAttributes

with tracer.start_as_current_span("http_client.request") as span:
    span.set_attribute(SpanAttributes.HTTP_REQUEST_METHOD, "POST")
    span.set_attribute(SpanAttributes.HTTP_RESPONSE_STATUS_CODE, 201)
    span.set_attribute(SpanAttributes.URL_FULL, url)
```

### ❌ Wrong: Variable in Span Name

```python
# CARDINALITY EXPLOSION - unbounded span names
with tracer.start_as_current_span(f"order.get_{order_id}") as span:
    ...
```

### ❌ Wrong: Tracer in Function Body

```python
async def process(self, data):
    tracer = trace.get_tracer(__name__)  # WRONG: acquired per-call
    with tracer.start_as_current_span("process"):
        ...
```

### ❌ Wrong: High-Cardinality Attributes

```python
span.set_attribute("user.email", email)     # PII + unbounded
span.set_attribute("order.id", order_id)    # Unbounded identifier
span.set_attribute("request.body", body)    # Large + possibly PII
```

---

## Attribute Cardinality Guide

| Cardinality | Status | Examples |
|-------------|--------|----------|
| < 100 | ✅ Safe | `order.type`, `user.tier`, `http.method` |
| 100–1000 | ⚠️ Caution | `region`, `product_category` |
| > 1000 | ❌ Avoid | `user_id`, `order_id`, `email` |

**Custom attribute format:** `<domain>.<entity>.<property>`

```python
span.set_attribute("myapp.order.type", "subscription")  # ✅ Enum
span.set_attribute("myapp.order.item_count", 5)         # ✅ Bounded int
span.set_attribute("myapp.user.tier", "premium")        # ✅ Enum
```

---

## Error Recording

| Scenario | `record_exception()` | `set_status(ERROR)` |
|----------|:--------------------:|:-------------------:|
| Business exception | ✅ | ✅ |
| Unexpected exception | ✅ | ✅ |
| "Not found" (returns None) | ❌ | ❌ |
| Transient retry (non-final) | ✅ | ❌ |

```python
try:
    result = await self._execute(data)
except KnownError as exc:
    span.record_exception(exc)
    span.set_status(Status(StatusCode.ERROR, str(exc)))
    raise
# Success: status is implicitly OK - don't set explicitly
```

---

## Cross-Service Propagation

```python
from opentelemetry.propagate import inject, extract

# Client: inject context into outgoing headers
headers: dict[str, str] = {}
inject(headers)
response = await client.post(url, headers=headers)

# Server: extract context from incoming headers
ctx = extract(request.headers)
with tracer.start_as_current_span("http.server.handle", context=ctx):
    ...
```

---

## Skill Chaining

| Condition | Invoke | Rationale |
|-----------|--------|-----------|
| After adding instrumentation | `test/unit` | Verify spans are created correctly |
| Performance concerns from tracing | `optimize/performance` | Reduce overhead |
| Need structured logs with trace correlation | `observe/logs` | Add trace_id to logs |
| Need metrics from spans | `observe/metrics` | Define span-based metrics |

---

## Quality Gates

Before completing tracing instrumentation:

- [ ] Tracer acquired at module level (not in function/class body)
- [ ] All span names are static (`<component>.<operation>`, no f-strings)
- [ ] Attributes use semantic conventions where available
- [ ] Custom attributes have < 100 cardinality
- [ ] No PII in any attribute values
- [ ] All caught exceptions call both `record_exception()` and `set_status(ERROR)`
- [ ] Async fan-out uses `contextvars.copy_context()`
- [ ] No spans around pure computation or simple getters

---

## Deep References

- **[patterns.md](refs/patterns.md)**: Advanced patterns, middleware instrumentation
- **[troubleshooting.md](refs/troubleshooting.md)**: Missing spans, broken context
- **[semantic-conventions.md](refs/semantic-conventions.md)**: Full attribute reference
