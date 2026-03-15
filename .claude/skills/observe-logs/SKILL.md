---
name: observe-logs
version: 1.0.0
description: |
  Add structured logging to Python code using structlog with context propagation.
  Use when adding logging, instrumenting code, improving observability, or after implementing Python features.
  Relevant for Python services, FastAPI apps, Faststream event handlers, async code, request handling.
---

# Structured Logging (structlog)

> Logs are structured events, not strings. Every log MUST be machine-parseable and context-rich.

## Quick Reference

| Aspect | Rule |
|--------|------|
| **Library** | `structlog` only — never `print()` or raw `logging` |
| **Format** | JSON (prod) / Console (dev) via `sys.stderr.isatty()` |
| **Output** | Unbuffered stdout |
| **Context** | `contextvars` for request-scoped data |
| **Events** | Lowercase dot-notation: `user.created`, `order.failed` |
| **Invokes** | `observe/traces`, `observe/metrics` |
| **Invoked By** | `implement/python`, `implement/api`, `observe` |

---

## Core Workflow

1. **Acquire Logger**: Module-level `logger = structlog.get_logger()`
2. **Configure Once**: Call `configure_logging()` before `app.run()` at entrypoint
3. **Bind Context**: Use `bind_contextvars()` in middleware for request metadata
4. **Log Events**: Structured `log.info("domain.action", key=value)` — never f-strings
5. **Clear Context**: Call `clear_contextvars()` at request boundaries
6. **Chain**: Invoke `observe/traces` for span correlation

---

## Logger Acquisition

```python
# ✅ ALWAYS: Module-level acquisition
import structlog
logger = structlog.get_logger()

def process_order(order_id: str) -> None:
    log = logger.bind(order_id=order_id)  # ✅ Local binding for context
    log.info("order.processing_started")
```

```python
# ❌ NEVER: bind() or new() at module/class scope — evaluated at import time
logger = structlog.get_logger().bind(service="api")  # BUG: static context
```

---

## Configuration

**MUST configure once at startup, before any logging occurs.**

```python
import sys
import logging
import structlog

def configure_logging() -> None:
    processors = [
        structlog.contextvars.merge_contextvars,    # ALWAYS first
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        # Add OTEL context injection here (see observe/traces)
        # Add redaction processor here
        structlog.processors.dict_tracebacks,
        # Renderer ALWAYS last
        structlog.dev.ConsoleRenderer(colors=True)
        if sys.stderr.isatty()
        else structlog.processors.JSONRenderer(),
    ]
    structlog.configure(
        processors=processors,
        cache_logger_on_first_use=True,  # MUST in production
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
    )
```

### Processor Chain Order (MUST follow exactly)

| Order | Processor | Purpose |
|-------|-----------|---------|
| 1 | `merge_contextvars` | ALWAYS first — merges request context |
| 2 | Filtering | Custom `DropEvent` for noise reduction |
| 3 | `add_log_level` | Enrichment |
| 4 | `TimeStamper(fmt="iso", utc=True)` | ISO 8601 UTC timestamps |
| 5 | OTEL context injector | Trace/span correlation |
| 6 | Redaction processor | Sensitive data protection |
| 7 | `dict_tracebacks` | JSON-friendly exceptions |
| 8 | `JSONRenderer` / `ConsoleRenderer` | ALWAYS last |

---

## Context Management

```python
from structlog.contextvars import bind_contextvars, clear_contextvars

# Middleware: Bind request metadata
async def logging_middleware(request, call_next):
    clear_contextvars()  # MUST: Prevent leakage from previous requests
    bind_contextvars(
        request_id=request.headers.get("x-request-id"),
        user_id=request.state.user_id,
        http_method=request.method,
        http_path=request.url.path,
    )
    return await call_next(request)
```

---

## Event & Key Naming

### Event Names: `{domain}.{action}` or `{domain}.{action}_{result}`

| Pattern | Examples |
|---------|----------|
| Standard | `user.created`, `order.shipped`, `payment.processed` |
| Outcome | `payment.charge_failed`, `auth.token_expired` |
| Nested | `order.item_added`, `cart.item_removed` |

### Key Names: `snake_case` with units

| ✅ Correct | ❌ Wrong |
|-----------|---------|
| `duration_ms` | `duration` |
| `size_bytes` | `size` |
| `http_status_code` | `statusCode` |
| `db_query_time_ms` | `queryTime` |

```python
# ❌ NEVER: String interpolation
log.info(f"User {user_id} created order {order_id}")

# ✅ ALWAYS: Structured key=value
log.info("order.created", user_id=user_id, order_id=order_id)
```

---

## Log Levels

| Level | Usage |
|-------|-------|
| `debug` | Development diagnostics, verbose tracing |
| `info` | Business events, state transitions |
| `warning` | Recoverable issues, degraded operation |
| `error` | Failures requiring attention |
| `critical` | System-wide failures, data loss risk |

---

## Exception Handling

```python
try:
    risky_operation()
except ValidationError as e:
    log.exception(  # Auto-captures exc_info
        "order.validation_failed",
        order_id=order_id,
        error_type="ValidationError",   # MUST include
        error_code="INVALID_QUANTITY",  # MUST include
    )
    raise
```

---

## Sensitive Data Redaction

**MUST redact:** `password`, `token`, `secret`, `authorization`, `api_key`, `credit_card`

```python
# ❌ NEVER: Log sensitive data
log.info("user.auth", password=pwd, token=jwt)

# ✅ ALWAYS: Log references only
log.info("user.auth", user_id=uid, auth_method="jwt")
```

---

## Performance Rules

```python
# ❌ NEVER: Log in tight loops
for item in million_items:
    log.debug("processing", item_id=item.id)

# ✅ ALWAYS: Log aggregates or sample
log.info("batch.started", count=len(items))
log.info("batch.completed", count=len(items), duration_ms=elapsed)

# ❌ NEVER: High-cardinality values as keys
log.info("request", body=request_body)

# ✅ ALWAYS: Log metadata
log.info("request", body_size_bytes=len(request_body), content_type=ct)
```

---

## Async Code

**MUST use async-prefixed methods in asyncio code:**

```python
await log.ainfo("async.operation_completed", result_count=len(results))
await log.adebug("async.step_finished", step="validation")
await log.aexception("async.operation_failed", error_type=type(e).__name__)
```

---

## Skill Chaining

| Condition | Invoke | Handoff Context |
|-----------|--------|-----------------|
| Adding distributed tracing | `observe/traces` | Service name, span conventions |
| Adding metrics alongside logs | `observe/metrics` | Metric names, label cardinality |
| Log config in FastAPI app | `implement/api` | Middleware integration point |

---

## Hard Rules Summary

| ❌ NEVER | ✅ ALWAYS |
|----------|-----------|
| `print()` for logs | `structlog.get_logger()` |
| f-strings in log messages | Keyword arguments `key=value` |
| Log in tight loops | Log aggregates/samples |
| Log PII/tokens/secrets | Redact sensitive data |
| `bind()` at module scope | `bind()` in functions |
| Missing `error_type`/`error_code` | Include both on all errors |

---

## Quality Gates

Before completing any logging implementation:

- [ ] Logger acquired at module level with `structlog.get_logger()`
- [ ] Configuration called once at startup, before any logging
- [ ] JSON in production, console in development
- [ ] `merge_contextvars` first in processor chain
- [ ] `clear_contextvars()` at request boundaries
- [ ] Events use `domain.action` naming convention
- [ ] All context as keyword arguments (no f-strings)
- [ ] ISO 8601 UTC timestamps configured
- [ ] Sensitive data redacted (password, token, secret, api_key)
- [ ] No logging in tight loops
- [ ] `error_type` and `error_code` on all error logs
- [ ] Async methods (`ainfo`, `adebug`) used in async code
