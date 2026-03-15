---
name: observe-metrics
version: 1.0.0

description: |
  Instrument Python applications with production-grade OpenTelemetry metrics
  (Counters, Histograms, UpDownCounters, ObservableGauges). Use when adding
  application metrics, implementing telemetry, measuring request latency,
  tracking error rates, monitoring queue depths, or instrumenting business KPIs.
  Relevant for Python observability, OpenTelemetry SDK, SLO monitoring,
  Prometheus-style metrics.
---

# OpenTelemetry Metrics Instrumentation

> Instrument Python applications with production-grade metrics that answer: "How many?", "How long?", "How much?"

## Quick Reference

| Aspect | Details |
|--------|---------|
| **Invokes** | `test/unit`, `review/observability` |
| **Invoked By** | `implement/python`, `implement/api`, `optimize/performance` |
| **Key Tools** | Write, Edit, Grep |
| **Primary File** | `metrics/instruments.py` or `telemetry/metrics.py` |

---

## Core Workflow

1. **Audit**: Search for existing metrics with `Grep` for `create_counter`, `create_histogram`, `meter.create`
2. **Select**: Choose correct instrument type using Decision Tree below
3. **Register**: Create instruments at module level in central registry
4. **Attribute**: Define bounded attributes (<100 cardinality)
5. **Record**: Implement recording with error handling
6. **Validate**: Verify no auto-instrumentation conflicts
7. **Chain**: Invoke `test/unit` for metrics tests, `review/observability` for review

---

## Instrument Selection Decision Tree

```
What are you measuring?
│
├─► Value only increases? (requests, errors, bytes sent)
│   └──► Counter
│        └──► Method: add(value)
│
├─► Value increases AND decreases? (connections, queue depth)
│   └──► UpDownCounter
│        └──► Method: add(±value)
│
├─► Need percentiles/distribution? (latency, payload size)
│   └──► Histogram
│        └──► Method: record(value)
│
└─► Point-in-time snapshot from external source? (CPU, memory)
    └──► ObservableGauge
         └──► Method: callback function
```

---

## Hard Rules

### MUST

- Create instruments at **module level**, never inside functions
- Use semantic naming: `<domain>.<component>.<metric>`
- Keep attribute cardinality **under 100 unique values**
- Include `error.type` attribute on all metrics
- Specify units: seconds (`s`), bytes (`By`), count (`{request}`)
- Align histogram buckets to SLO thresholds
- Use `UpDownCounter` for values that can decrease
- Check for auto-instrumentation before adding metrics

### NEVER

- Create instruments inside function bodies (causes duplicates)
- Use user IDs, request IDs, or full URLs as attributes
- Use Counters for bidirectional values
- Use milliseconds (always use seconds with `s` unit)
- Duplicate metrics already covered by auto-instrumentation
- Forget units on instrument definitions
- Use custom naming schemes (follow OTel semantic conventions)

---

## Conditional Rules

**WHEN** measuring monotonically increasing totals (requests, errors, bytes)  
**THEN** use `Counter` with `add(value)` method

**WHEN** measuring values that go up AND down (connections, queue size)  
**THEN** use `UpDownCounter` with `add(±value)` method

**WHEN** measuring distributions needing percentiles (latency, payload size)  
**THEN** use `Histogram` with `record(value)` method

**WHEN** measuring point-in-time snapshots via callback (CPU, memory)  
**THEN** use `ObservableGauge` with non-blocking callback

**WHEN** HTTP status codes would exceed cardinality limits  
**THEN** bucket into classes: `2xx`, `3xx`, `4xx`, `5xx`

**WHEN** auto-instrumentation library exists for the framework  
**THEN** check which metrics are already instrumented before adding

**WHEN** recording durations  
**THEN** use `time.perf_counter()` and context managers for accuracy

---

## Skill Chaining

### Invoke Downstream Skills When

| Condition | Invoke | Handoff Context |
|-----------|--------|-----------------|
| Metrics implementation complete | `test/unit` | Instrument names, expected attributes |
| Ready for observability review | `review/observability` | Metrics file paths |

### Chaining Syntax

```markdown
**Invoking Sub-Skill:** `test/unit`
**Reason:** Metrics instrumentation complete, need coverage tests
**Handoff Context:** Instruments in `metrics/instruments.py`, test attribute cardinality
```

---

## Patterns

### ✅ Do: Instrument Registry Pattern

```python
# metrics/instruments.py
from opentelemetry import metrics

meter = metrics.get_meter("myapp")

# Counters (monotonically increasing)
http_requests = meter.create_counter(
    "http.server.requests",
    unit="{request}",
    description="Total HTTP requests",
)

# UpDownCounters (bidirectional)
active_connections = meter.create_up_down_counter(
    "http.server.connections.active",
    unit="{connection}",
    description="Active HTTP connections",
)

# Histograms (distributions)
request_duration = meter.create_histogram(
    "http.server.request.duration",
    unit="s",
    description="HTTP request duration",
)
```

### ✅ Do: Duration Context Manager

```python
import time
from contextlib import contextmanager

@contextmanager
def record_duration(histogram, attributes: dict):
    start = time.perf_counter()
    error_type = None
    try:
        yield
    except Exception as e:
        error_type = type(e).__name__
        raise
    finally:
        duration = time.perf_counter() - start
        attrs = {**attributes}
        if error_type:
            attrs["error.type"] = error_type
        histogram.record(duration, attrs)
```

### ✅ Do: Bounded Attributes Only

```python
request_counter.add(1, {
    "http.request.method": "POST",        # ~10 values
    "http.response.status_code": 201,     # ~50 values
    "http.route": "/api/users/{id}",      # Template, not actual URL
})
```

### ❌ Don't: Per-Call Instrument Creation

```python
def handle_request():
    counter = meter.create_counter("requests")  # WRONG: Creates duplicate!
    counter.add(1)
```

### ❌ Don't: Unbounded Attributes

```python
request_counter.add(1, {
    "user_id": user.id,        # Millions of unique values
    "request_id": request.id,  # Infinite cardinality
    "url.full": request.url,   # Query params make this unbounded
})
```

### ❌ Don't: Duplicate Auto-Instrumented Metrics

```python
# FastAPI auto-instrumentation already records http.server.request.duration
@app.middleware("http")
async def metrics_middleware(request, call_next):
    start = time.time()
    response = await call_next(request)
    request_duration.record(time.time() - start)  # DUPLICATE!
    return response
```

---

## Auto-Instrumentation Reference

These metrics are already instrumented by OTel libraries:

| Library | Auto-Instrumented Metrics |
|---------|---------------------------|
| `opentelemetry-instrumentation-fastapi` | `http.server.request.duration` |
| `opentelemetry-instrumentation-httpx` | `http.client.request.duration` |
| `opentelemetry-instrumentation-sqlalchemy` | `db.client.query.duration` |
| `opentelemetry-instrumentation-redis` | Redis operation metrics |

**Add only business metrics not covered by auto-instrumentation.**

---

## Required Attributes by Metric Type

| Metric Type | Required Attributes |
|-------------|---------------------|
| HTTP Server | `http.request.method`, `http.response.status_code`, `http.route` |
| HTTP Client | `http.request.method`, `http.response.status_code`, `server.address` |
| Database | `db.system`, `db.operation.name`, `db.collection.name` |
| Messaging | `messaging.system`, `messaging.operation.name`, `messaging.destination.name` |

---

## Quality Gates

Before completing metrics instrumentation:

- [ ] All instruments created at module level (not per-call)
- [ ] All attributes bounded (< 100 unique values)
- [ ] No user IDs, request IDs, or full URLs in attributes
- [ ] Semantic naming follows `<domain>.<component>.<metric>`
- [ ] Units specified: seconds (`s`), bytes (`By`), count (`{request}`)
- [ ] `error.type` attribute included on all metrics
- [ ] No duplicated auto-instrumented metrics
- [ ] Histogram buckets aligned to SLO thresholds
- [ ] Correct instrument type for each measurement

---

## Example: Complete Metrics Setup

**Input:** "Add metrics for an order processing service"

**Output:**

```python
# src/metrics/instruments.py
from opentelemetry import metrics

meter = metrics.get_meter("order-service")

orders_created = meter.create_counter(
    "orders.created",
    unit="{order}",
    description="Total orders created",
)

orders_value = meter.create_counter(
    "orders.value",
    unit="{dollar}",
    description="Total order value in dollars",
)

order_processing_duration = meter.create_histogram(
    "orders.processing.duration",
    unit="s",
    description="Order processing duration",
)

active_checkouts = meter.create_up_down_counter(
    "checkouts.active",
    unit="{checkout}",
    description="Active checkout sessions",
)
```

```python
# src/api/routes/orders.py
from src.metrics.instruments import (
    orders_created, orders_value,
    order_processing_duration, active_checkouts,
)
from src.metrics.helpers import record_duration

@router.post("/orders", response_model=OrderResponse)
async def create_order(order: OrderCreate):
    active_checkouts.add(1)
    try:
        with record_duration(order_processing_duration, {"order.type": order.type}):
            result = await service.create(order)

        orders_created.add(1, {
            "order.type": order.type,
            "payment.method": order.payment_method,
        })
        orders_value.add(result.total_cents / 100, {"order.type": order.type})
        return result
    finally:
        active_checkouts.add(-1)
```

---
