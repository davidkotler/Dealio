# Designing for Observability

> **Scope:** Architectural decisions that enable runtime visibility  
> **Phase:** Design (before implementation)  
> **Chains to:** `observe/logs`, `observe/traces`, `observe/metrics`, `observe/alerts`

---

## Core Principle

**Design systems where failure modes are visible, not hidden.**

Observability is not instrumentation added later—it's a structural property designed upfront. A well-designed system reveals its internal state through deliberate architectural choices.

---

## 1. Observability Contracts

### MUST

- Define observability requirements before implementation begins
- Specify what events, metrics, and traces each component produces
- Document log levels and their semantic meaning for the domain
- Plan correlation ID generation and propagation strategy
- Design explicit instrumentation points at system boundaries

### NEVER

- Treat observability as a post-implementation concern
- Design components with no defined observability surface
- Assume you can retrofit meaningful observability without refactoring
- Leave failure visibility as an implementation detail

### WHEN designing a new component THEN define its observability contract

```yaml
# ✅ Pattern: Observability contract (define before implementation)
component: OrderService
observability:
  logs:
    - event: order.created
      level: INFO
      fields: [order_id, customer_id, total, item_count]
    - event: order.failed
      level: ERROR
      fields: [order_id, error_code, error_message, stack_trace]

  metrics:
    - name: orders_created_total
      type: counter
      labels: [status, payment_method]
    - name: order_processing_duration_seconds
      type: histogram
      buckets: [0.1, 0.5, 1, 2, 5]

  traces:
    - span: process_order
      children: [validate_inventory, charge_payment, send_confirmation]

  health:
    liveness: /health/live
    readiness: /health/ready
```

```python
# ❌ Anti-pattern: No observability contract
class OrderService:
    """Processes orders."""  # No defined observability surface
    pass
```

---

## 2. Structured Logging Design

### MUST

- Design log events as structured data, not arbitrary strings
- Define a consistent schema for log fields across the system
- Plan log levels with clear semantic boundaries
- Include correlation IDs in every log event schema
- Design for machine parsing and human readability

### NEVER

- Design for `print()` or unstructured string concatenation
- Mix log levels arbitrarily (ERROR for warnings, INFO for debug)
- Design logs that require regex to parse
- Include unbounded fields (full request bodies, large arrays)

### WHEN defining log events THEN use structured schemas

```python
# ✅ Pattern: Structured log event design
@dataclass
class LogEvent:
    """Base schema for all log events."""
    timestamp: datetime
    level: LogLevel
    event: str           # Dot-namespaced: "order.created", "payment.failed"
    correlation_id: str
    service: str
    version: str

@dataclass
class OrderCreatedEvent(LogEvent):
    """Structured event for order creation."""
    order_id: OrderId
    customer_id: CustomerId
    total: Money
    item_count: int
    # Bounded, typed fields - no arbitrary data
```

```python
# ❌ Anti-pattern: Unstructured logging design
def process_order(order):
    print(f"Processing order {order}")  # Unstructured, unparsable
    logger.info(f"Order: {order.to_dict()}")  # Unbounded, untyped
```

### Log Level Semantics

| Level | Design Intent | Example |
|-------|---------------|---------|
| **ERROR** | Requires human attention; impacts users | Payment gateway timeout |
| **WARN** | Degraded but functional; may need attention | Cache miss, using fallback |
| **INFO** | Business events; audit trail | Order created, user registered |
| **DEBUG** | Troubleshooting; not for production default | SQL queries, internal state |

---

## 3. Distributed Tracing Design

### MUST

- Design span hierarchy before implementation
- Plan trace context propagation across all boundaries (HTTP, queue, DB)
- Define meaningful span names that reflect operations, not code
- Design for trace sampling strategy (head-based, tail-based)
- Include business context in span attributes

### NEVER

- Design systems where traces break at async boundaries
- Create spans without parent context consideration
- Use implementation details as span names (`handle_request_v2`)
- Design for 100% trace sampling without considering cost

### WHEN designing service interactions THEN plan span hierarchy

```
# ✅ Pattern: Span hierarchy design (design before implementation)

[API Gateway] ─── POST /orders ───────────────────────────────────┐
                                                                  │
    [OrderService] ─── process_order ─────────────────────────────┤
        │                                                         │
        ├── validate_inventory ────── [InventoryService] ─────────┤
        │       └── check_stock (DB query)                        │
        │                                                         │
        ├── charge_payment ────────── [PaymentService] ───────────┤
        │       └── stripe_charge (external API)                  │
        │                                                         │
        └── send_confirmation ─────── [NotificationService] ──────┘
                └── email_send (external API)
```

```python
# ✅ Pattern: Span attributes design
span_attributes = {
    "order.id": order_id,           # Business context
    "order.total": total,
    "customer.tier": customer_tier,
    "payment.method": payment_method,
    # NOT: internal_retry_count, cache_key, db_connection_id
}
```

---

## 4. Metrics Design

### MUST

- Design metrics with bounded cardinality (labels have finite values)
- Use the RED method for services: Rate, Errors, Duration
- Use the USE method for resources: Utilization, Saturation, Errors
- Plan histogram buckets based on expected latency distribution
- Design counters for events, gauges for current state, histograms for distributions

### NEVER

- Design high-cardinality labels (user IDs, request IDs, timestamps)
- Create metrics without considering aggregation queries
- Design unbounded label values (error messages, URLs with parameters)
- Mix metric types inappropriately (gauge for cumulative counts)

### WHEN designing metrics THEN plan for cardinality

```python
# ✅ Pattern: Bounded cardinality metrics design
metrics_design = {
    "http_requests_total": {
        "type": "counter",
        "labels": ["method", "endpoint", "status_code"],  # Bounded
        # method: ~5 values, endpoint: ~50 values, status: ~10 values
        # Cardinality: 5 × 50 × 10 = 2,500 series (manageable)
    },
    "request_duration_seconds": {
        "type": "histogram",
        "labels": ["method", "endpoint"],
        "buckets": [0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
    },
}
```

```python
# ❌ Anti-pattern: High cardinality design
metrics_design = {
    "http_requests_total": {
        "labels": ["user_id", "request_id", "full_url"],  # UNBOUNDED
        # Cardinality: millions × millions × millions = explosion
    },
}
```

### Metric Type Selection

| Metric Type | Design For | Example |
|-------------|------------|---------|
| **Counter** | Cumulative events | `requests_total`, `errors_total` |
| **Gauge** | Current state | `connections_active`, `queue_depth` |
| **Histogram** | Distributions | `request_duration`, `response_size` |
| **Summary** | Pre-calculated percentiles | `request_latency_p99` |

---

## 5. Error Taxonomy Design

### MUST

- Categorize errors by severity, recoverability, and ownership
- Design error codes that are actionable and queryable
- Plan error context that aids debugging without exposing internals
- Design for alert routing (which team owns which error class)

### NEVER

- Design generic errors that provide no diagnostic value
- Mix transient and permanent failures in the same error type
- Design errors that expose internal implementation details to users
- Create error codes that change with implementation refactoring

### WHEN designing error handling THEN create an error taxonomy

```python
# ✅ Pattern: Error taxonomy design
class ErrorTaxonomy:
    """Design error classification before implementation."""

    categories = {
        "validation": {
            "severity": "low",
            "recoverable": True,
            "owner": "caller",
            "alert": False,
            "codes": ["INVALID_INPUT", "MISSING_FIELD", "FORMAT_ERROR"],
        },
        "downstream": {
            "severity": "medium",
            "recoverable": True,  # With retry
            "owner": "platform",
            "alert": True,
            "codes": ["PAYMENT_TIMEOUT", "INVENTORY_UNAVAILABLE"],
        },
        "internal": {
            "severity": "high",
            "recoverable": False,
            "owner": "service_team",
            "alert": True,
            "codes": ["DATABASE_ERROR", "CONFIG_MISSING"],
        },
    }
```

```python
# ❌ Anti-pattern: Flat, uninformative errors
class OrderError(Exception):
    pass  # No taxonomy, no context, no routing
```

---

## 6. Health Check Design

### MUST

- Design separate probes: liveness, readiness, startup
- Define what "healthy" means for each dependency
- Plan graceful degradation signals (partial health)
- Design health checks that are fast and non-destructive

### NEVER

- Conflate liveness with readiness (causes cascading restarts)
- Design health checks that perform heavy operations
- Make liveness depend on downstream services
- Design binary health when partial functionality is possible

### WHEN designing service health THEN separate probe types

```python
# ✅ Pattern: Health probe design
health_probes = {
    "liveness": {
        # "Is the process alive and not deadlocked?"
        "checks": ["process_responsive", "no_deadlock"],
        "dependencies": [],  # NO external deps
        "timeout": "1s",
        "failure_action": "restart_container",
    },
    "readiness": {
        # "Can I accept traffic?"
        "checks": ["database_connected", "cache_warm", "config_loaded"],
        "dependencies": ["postgres", "redis"],
        "timeout": "5s",
        "failure_action": "remove_from_loadbalancer",
    },
    "startup": {
        # "Has initial setup completed?"
        "checks": ["migrations_complete", "warmup_done"],
        "timeout": "60s",
        "failure_action": "delay_liveness_checks",
    },
}
```

---

## 7. SLI/SLO Design

### MUST

- Define Service Level Indicators before implementation
- Design metrics that directly measure user experience
- Plan error budgets as design constraints
- Align SLOs with business requirements, not technical capabilities

### NEVER

- Design SLOs based on what's easy to measure
- Set SLOs without understanding user expectations
- Design indicators that don't reflect actual user experience
- Create SLOs that are impossible to achieve architecturally

### WHEN designing a service THEN define SLIs first

```yaml
# ✅ Pattern: SLI/SLO design (before implementation)
service: OrderService
slis:
  availability:
    description: "Proportion of successful requests"
    good_event: "status_code < 500"
    valid_event: "all requests excluding health checks"
    slo_target: 99.9%

  latency:
    description: "Proportion of requests served within threshold"
    good_event: "response_time < 500ms"
    valid_event: "all non-batch requests"
    slo_target: 95%

  correctness:
    description: "Proportion of orders processed without data errors"
    good_event: "order_state == expected_state"
    valid_event: "all completed orders"
    slo_target: 99.99%

error_budget:
  monthly_minutes_allowed: 43  # (100% - 99.9%) × 30 × 24 × 60
```

---

## 8. Sensitive Data Handling

### MUST

- Design data classification schema (PII, secrets, business-sensitive)
- Plan redaction strategies before logging implementation
- Design allow-lists for loggable fields, not block-lists
- Consider compliance requirements (GDPR, HIPAA) in design

### NEVER

- Design systems that log credentials, tokens, or passwords
- Assume PII won't end up in logs without explicit prevention
- Design log pipelines without considering data residency
- Use block-lists for sensitive data (too easy to miss fields)

### WHEN designing log schemas THEN use allow-lists

```python
# ✅ Pattern: Allow-list design for loggable fields
@dataclass
class UserEvent(LogEvent):
    """Only explicitly allowed fields are logged."""
    user_id: str          # ✓ Allowed: non-PII identifier
    action: str           # ✓ Allowed: business event
    # email: str          # ✗ NOT INCLUDED: PII
    # password: str       # ✗ NOT INCLUDED: credential
    # credit_card: str    # ✗ NOT INCLUDED: payment data

class LoggableFields:
    """Explicit allow-list for what can be logged."""
    USER = {"user_id", "action", "timestamp", "status"}
    ORDER = {"order_id", "status", "item_count", "total"}
    # Any field not in allow-list requires explicit approval
```

---

## Design Checklist

Before completing system design, verify:

- [ ] Observability contract defined for each component
- [ ] Log event schemas designed with bounded, typed fields
- [ ] Span hierarchy planned for distributed traces
- [ ] Metrics designed with bounded cardinality (<10k series)
- [ ] Error taxonomy created with severity and ownership
- [ ] Health probes designed (liveness ≠ readiness)
- [ ] SLIs defined based on user experience
- [ ] Sensitive data handling designed with allow-lists
- [ ] Correlation ID propagation strategy documented

---

## Skill Chaining

After design phase, invoke implementation skills:

| Design Artifact | Implementation Skill | Handoff Context |
|-----------------|---------------------|-----------------|
| Log schemas | `observe/logs` | Event types, field schemas |
| Span hierarchy | `observe/traces` | Span names, parent relationships |
| Metric definitions | `observe/metrics` | Names, types, labels, buckets |
| SLOs | `observe/dashboards` | SLI queries, thresholds |
| Error taxonomy | `observe/alerts` | Alert conditions, routing |

---

## Quick Reference

| Aspect | Design Question |
|--------|-----------------|
| **Logs** | What events matter? What fields are needed? |
| **Traces** | What's the span hierarchy? Where does context propagate? |
| **Metrics** | What indicates health? What labels are bounded? |
| **Errors** | What categories exist? Who owns each? |
| **Health** | What's liveness vs readiness? |
| **SLOs** | What does the user experience? What's the budget? |
| **Privacy** | What's allowed to log? What must be redacted? |
