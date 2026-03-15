---
name: review-observability
version: 1.0.0

description: |
  Review code for observability quality across logging, tracing, and metrics instrumentation.
  Evaluates structlog patterns, OpenTelemetry spans, metric cardinality, context propagation,
  and trace-log correlation. Use when reviewing instrumented code, validating telemetry
  implementations, assessing observability coverage, or after invoking observe/* skills.
  Relevant for Python backends, FastAPI, FastStream, async services, microservices.
chains:
  invoked-by:
    - skill: observe/logs
      context: "Post-implementation logging review"
    - skill: observe/traces
      context: "Post-implementation tracing review"
    - skill: observe/metrics
      context: "Post-implementation metrics review"
    - skill: implement/python
      context: "When observability code detected"
    - skill: implement/api
      context: "Endpoint instrumentation validation"
  invokes:
    - skill: observe/logs
      when: "Logging findings require remediation"
    - skill: observe/traces
      when: "Tracing findings require remediation"
    - skill: observe/metrics
      when: "Metrics findings require remediation"
---

# Observability Review

> Validate production-readiness of instrumentation through systematic analysis of logging,
> tracing, and metrics patterns against proven observability principles.

## Quick Reference

| Aspect | Details |
|--------|---------|
| **Dimension** | Observability (Logs, Traces, Metrics) |
| **Scope** | Python modules with structlog, OpenTelemetry instrumentation |
| **Invoked By** | `observe/*`, `implement/python`, `implement/api`, `/review` |
| **Invokes** | `observe/logs`, `observe/traces`, `observe/metrics` (on failure) |
| **Verdict Options** | `PASS` · `PASS_WITH_SUGGESTIONS` · `NEEDS_WORK` · `FAIL` |

---

## Review Objective

Ensure instrumentation enables effective production debugging, performance analysis, and
system health monitoring without introducing cardinality explosions, context leakage,
or security vulnerabilities.

### This Review Answers

1. Can operators correlate logs, traces, and metrics for any request?
2. Will the instrumentation scale without cardinality explosion?
3. Are sensitive data and PII protected from telemetry exposure?
4. Do naming conventions enable consistent querying across services?

### Out of Scope

- Business logic correctness (see `review/functionality`)
- Code style beyond observability patterns (see `review/style`)
- Dashboard or alert configuration (see `observe/dashboards`, `observe/alerts`)

---

## Core Workflow

```
┌─────────────────────────────────────────────────────────────┐
│                 OBSERVABILITY REVIEW WORKFLOW               │
├─────────────────────────────────────────────────────────────┤
│  1. SCOPE    →  Find instrumented modules (logs/traces/metrics)
│  2. CONTEXT  →  Load observe/* skill rules and principles   │
│  3. ANALYZE  →  Evaluate each instrumentation type          │
│  4. CLASSIFY →  Assign severity per finding                 │
│  5. VERDICT  →  Determine pass/fail from severity matrix    │
│  6. REPORT   →  Output structured findings                  │
│  7. CHAIN    →  Invoke observe/* skills for remediation     │
└─────────────────────────────────────────────────────────────┘
```

### Step 1: Scope Definition

Identify review targets:

```bash
# Logging instrumentation
**/logging.py, **/log_config.py, **/*_logger.py

# Tracing instrumentation  
**/tracing.py, **/telemetry/**/*.py, **/instrumentation.py

# Metrics instrumentation
**/metrics/**/*.py, **/instruments.py, **/telemetry/metrics.py

# Application code with observability
**/api/**/*.py, **/services/**/*.py, **/handlers/**/*.py
```

### Step 2: Context Loading

Before analysis, internalize:







- **Principles:** `rules/principles.md` → Section 1.10 Observability
- **Logging Rules:** `observe/logs/SKILL.md` → structlog patterns
- **Tracing Rules:** `observe/traces/SKILL.md` → OpenTelemetry span conventions
- **Metrics Rules:** `observe/metrics/SKILL.md` → Instrument selection, cardinality

### Step 3: Systematic Analysis

Evaluate each category in priority order:

| Priority | Category | Weight | Key Checks |
|----------|----------|--------|------------|
| P0 | Security & PII | Blocker | No secrets/PII in telemetry |
| P1 | Cardinality | Critical | All attributes < 100 unique values |
| P2 | Acquisition | Critical | Module-level logger/tracer/meter |
| P3 | Naming | Major | Semantic conventions followed |
| P4 | Context | Major | Trace correlation, contextvars |
| P5 | Completeness | Minor | Coverage of I/O boundaries |

### Step 4: Severity Classification

| Severity | Definition | Action Required |
|----------|------------|-----------------|
| **🔴 BLOCKER** | PII exposure, credentials in logs, unbounded cardinality | Must fix before merge |
| **🟠 CRITICAL** | Wrong acquisition location, missing error recording | Must fix, may defer |
| **🟡 MAJOR** | Non-semantic naming, missing context propagation | Should fix |
| **🔵 MINOR** | Suboptimal patterns, missing units | Consider fixing |
| **⚪ SUGGESTION** | Enhancement opportunities | Optional |
| **🟢 COMMENDATION** | Exemplary patterns | Positive reinforcement |

### Step 5: Verdict Determination

```
Findings Analysis
       │
       ├─► Any BLOCKER (PII, secrets, unbounded)? ──► FAIL
       │
       ├─► Any CRITICAL (acquisition, error handling)? ──► NEEDS_WORK
       │
       ├─► Multiple MAJOR (naming, context)? ──► NEEDS_WORK
       │
       ├─► Few MAJOR or MINOR only? ──► PASS_WITH_SUGGESTIONS
       │
       └─► SUGGESTION/COMMENDATION only? ──► PASS
```

---

## Evaluation Criteria

### Logging Quality (LQ)

| ID | Criterion | Severity | Check |
|----|-----------|----------|-------|
| LQ.1 | Logger acquired at module level | CRITICAL | `logger = structlog.get_logger()` at top of file |
| LQ.2 | No `bind()` at module/class scope | CRITICAL | `bind()` only inside functions |
| LQ.3 | Events use `domain.action` naming | MAJOR | Lowercase, dot-separated, no variables |
| LQ.4 | Keys use `snake_case` with units | MAJOR | `duration_ms`, `size_bytes`, not `duration` |
| LQ.5 | No f-strings in log messages | MAJOR | `log.info("event", key=val)` not `log.info(f"...")` |
| LQ.6 | Sensitive data redacted | BLOCKER | No password, token, secret, api_key, PII |
| LQ.7 | Error logs include `error_type`, `error_code` | MAJOR | Both present on all error/exception logs |
| LQ.8 | No logging in tight loops | CRITICAL | Log aggregates, not iterations |
| LQ.9 | Async code uses async methods | MINOR | `await log.ainfo()` in async functions |
| LQ.10 | `clear_contextvars()` at request boundaries | MAJOR | Prevents context leakage |

### Tracing Quality (TQ)

| ID | Criterion | Severity | Check |
|----|-----------|----------|-------|
| TQ.1 | Tracer acquired at module level | CRITICAL | `tracer = trace.get_tracer(__name__)` at top |
| TQ.2 | Span names are static | BLOCKER | No f-strings, no variables in names |
| TQ.3 | Span names use `component.operation` | MAJOR | Lowercase, dot-separated |
| TQ.4 | Attributes use semantic conventions | MAJOR | `SpanAttributes.*` before custom |
| TQ.5 | Custom attributes < 100 cardinality | CRITICAL | No user_id, order_id, request_id |
| TQ.6 | No PII in attributes | BLOCKER | No email, name, token in attributes |
| TQ.7 | Both `record_exception()` and `set_status(ERROR)` | CRITICAL | Both called on failures |
| TQ.8 | No explicit `set_status(OK)` | MINOR | Success status is implicit |
| TQ.9 | Async fan-out copies context | CRITICAL | `contextvars.copy_context()` before spawn |
| TQ.10 | Spans only at I/O boundaries | MINOR | No spans for pure computation |

### Metrics Quality (MQ)

| ID | Criterion | Severity | Check |
|----|-----------|----------|-------|
| MQ.1 | Instruments created at module level | CRITICAL | Never inside functions |
| MQ.2 | Correct instrument type selected | MAJOR | Counter/UpDownCounter/Histogram/Gauge |
| MQ.3 | Semantic naming `domain.component.metric` | MAJOR | Lowercase, dot-separated |
| MQ.4 | Units specified | MAJOR | `s`, `By`, `{request}` not missing |
| MQ.5 | Attributes < 100 cardinality | CRITICAL | Bounded enums, not IDs |
| MQ.6 | No user IDs or request IDs in attributes | BLOCKER | Unbounded cardinality |
| MQ.7 | `error.type` attribute included | MAJOR | On all metrics |
| MQ.8 | No auto-instrumented metric duplication | MAJOR | Check library coverage first |
| MQ.9 | Histogram buckets align to SLOs | MINOR | Percentile boundaries match targets |
| MQ.10 | HTTP status codes bucketed to classes | MINOR | `2xx`, `3xx` not individual codes |

### Cross-Cutting Concerns (CC)

| ID | Criterion | Severity | Check |
|----|-----------|----------|-------|
| CC.1 | Trace IDs propagated to logs | MAJOR | OTEL context injector in processor chain |
| CC.2 | Consistent cardinality rules across all types | CRITICAL | Same bounded attributes everywhere |
| CC.3 | Naming conventions consistent | MAJOR | Same domain terms in logs/traces/metrics |
| CC.4 | Configuration centralized | MINOR | Single config module, not scattered |
| CC.5 | Health probes separate from business metrics | MINOR | Dedicated health endpoints |

---

## Patterns & Anti-Patterns

### ✅ Indicators of Quality

```python
# Module-level acquisition (all three)
import structlog
from opentelemetry import trace, metrics

logger = structlog.get_logger()
tracer = trace.get_tracer(__name__)
meter = metrics.get_meter(__name__)

# Bounded attributes, semantic naming
request_counter.add(1, {
    "http.request.method": "POST",      # ~10 values
    "http.route": "/api/users/{id}",    # Template, bounded
    "myapp.order.type": order.type,     # Enum, bounded
})

# Proper error handling with both methods
except OrderError as exc:
    span.record_exception(exc)
    span.set_status(Status(StatusCode.ERROR, str(exc)))
    logger.exception("order.creation_failed",
        error_type=type(exc).__name__,
        error_code=exc.code)
    raise
```

**Why this works:** Module-level acquisition prevents per-call overhead, bounded attributes prevent cardinality explosion, dual error recording ensures both span status and exception details are captured.

### ❌ Red Flags

```python
# WRONG: Acquisition inside function
async def handle_request(request):
    logger = structlog.get_logger()  # Per-call overhead
    tracer = trace.get_tracer(__name__)  # Duplicate tracer

# WRONG: Unbounded cardinality
span.set_attribute("user.email", user.email)  # PII + unbounded
span.set_attribute("request.id", request_id)  # Infinite cardinality
log.info(f"Processing order {order_id}")      # f-string, not structured

# WRONG: Variable in span name
with tracer.start_as_current_span(f"order.get_{order_id}"):  # Cardinality explosion
```

**Why this fails:** Per-call acquisition creates overhead and potential duplicate registrations, unbounded attributes cause storage explosion and query timeouts, f-strings prevent structured querying.

---

## Finding Output Format

```markdown
### [{{SEVERITY_EMOJI}} {{SEVERITY}}] {{FINDING_TITLE}}

**Location:** `{{FILE_PATH}}:{{LINE_NUMBER}}`
**Criterion:** {{CRITERION_ID}} - {{CRITERION_NAME}}

**Issue:**
{{ISSUE_DESCRIPTION}}

**Evidence:**
```python
{{CODE_SNIPPET}}
```

**Suggestion:**
{{REMEDIATION_GUIDANCE}}

**Rationale:**
{{WHY_THIS_MATTERS}}
```

---

## Review Summary Format

```markdown
# Observability Review Summary

## Verdict: {{VERDICT_EMOJI}} {{VERDICT}}

| Metric | Count |
|--------|-------|
| Files Reviewed | {{COUNT}} |
| Blockers | {{COUNT}} |
| Critical | {{COUNT}} |
| Major | {{COUNT}} |
| Minor | {{COUNT}} |
| Suggestions | {{COUNT}} |
| Commendations | {{COUNT}} |

## Coverage Assessment

| Type | Status | Files |
|------|--------|-------|
| Logging | ✅/⚠️/❌ | {{FILES}} |
| Tracing | ✅/⚠️/❌ | {{FILES}} |
| Metrics | ✅/⚠️/❌ | {{FILES}} |

## Key Findings

{{TOP_3_FINDINGS_SUMMARY}}

## Recommended Actions

1. {{ACTION_1}}
2. {{ACTION_2}}
3. {{ACTION_3}}

## Skill Chain Decision

{{CHAIN_DECISION_EXPLANATION}}
```

---

## Skill Chaining

### Chain Triggers

| Verdict | Chain Action | Target Skill |
|---------|--------------|--------------|
| `FAIL` | Mandatory remediation | `observe/logs`, `observe/traces`, or `observe/metrics` |
| `NEEDS_WORK` | Targeted fixes | Specific observe skill based on findings |
| `PASS_WITH_SUGGESTIONS` | Optional | None (suggestions only) |
| `PASS` | Continue pipeline | `test/unit` or `review/performance` |

### Handoff Protocol

When chaining to observe skills:

```markdown
**Chain Target:** `observe/{logs|traces|metrics}`
**Priority Findings:** {{BLOCKER_AND_CRITICAL_IDS}}
**Context:** Review identified {{COUNT}} issues in {{CATEGORY}}

**Constraint:** Preserve existing instrumentation patterns

```



### Re-Review Loop



After observe skill completes:

- Scope limited to modified files
- Focus on previously-failed criteria
- Maximum 3 iterations before escalation

---

## Integration Points

### Upstream Integration

| Source | Trigger | Context Provided |
|--------|---------|------------------|
| `observe/logs` | Post-implementation | Logging module paths |
| `observe/traces` | Post-implementation | Tracing module paths |
| `observe/metrics` | Post-implementation | Metrics module paths |
| `implement/api` | Route instrumentation | Endpoint file paths |
| `/review` command | Explicit invocation | User-specified scope |

### Downstream Integration

| Target | Condition | Handoff |
|--------|-----------|---------|
| `observe/logs` | LQ findings ≥ CRITICAL | Logging findings + priority |
| `observe/traces` | TQ findings ≥ CRITICAL | Tracing findings + priority |
| `observe/metrics` | MQ findings ≥ CRITICAL | Metrics findings + priority |

---

## Examples

### Example 1: Cardinality Violation

**Input:** Review `src/api/routes/orders.py`

**Analysis:** Found span attribute using order_id directly

**Output:**
```markdown
### [🔴 BLOCKER] Unbounded Span Attribute Cardinality

**Location:** `src/api/routes/orders.py:45`
**Criterion:** TQ.5 - Custom attributes < 100 cardinality

**Issue:**
Span attribute `order.id` uses the raw order identifier, creating unbounded cardinality
that will cause storage explosion and query timeouts in production.

**Evidence:**
```python
span.set_attribute("order.id", order_id)  # Millions of unique values
```

**Suggestion:**
Remove the identifier or use a bounded classification:
```python
span.set_attribute("myapp.order.type", order.type.value)  # Enum: ~5 values
span.set_attribute("myapp.order.priority", order.priority)  # Enum: ~3 values
```

**Rationale:**
Each unique attribute value creates a new time series. Unbounded IDs cause
O(n) storage growth, slow queries, and potential service degradation.
```

**Verdict:** `FAIL` → Chain to `observe/traces`

### Example 2: Missing Error Context

**Input:** Review `src/services/payment.py`

**Output:**
```markdown
### [🟠 CRITICAL] Incomplete Error Recording in Span

**Location:** `src/services/payment.py:78`
**Criterion:** TQ.7 - Both record_exception() and set_status(ERROR)

**Issue:**
Exception handling records the exception but does not set span status to ERROR.

**Evidence:**
```python
except PaymentError as exc:
    span.record_exception(exc)  # ✅ Exception recorded
    # Missing: span.set_status(Status(StatusCode.ERROR, str(exc)))
    raise
```

**Suggestion:**
```python
except PaymentError as exc:
    span.record_exception(exc)
    span.set_status(Status(StatusCode.ERROR, str(exc)))
    raise
```

**Rationale:**
`record_exception()` adds exception details to the span, but the span status
remains UNSET. Error rate dashboards rely on span status for accuracy.
```

**Verdict:** `NEEDS_WORK` → Chain to `observe/traces`

---

## Quality Gates

Before finalizing review output:

- [ ] All instrumented files in scope were analyzed
- [ ] Logging, tracing, and metrics each evaluated separately
- [ ] Each finding has location + criterion + severity
- [ ] Cardinality assessed for ALL attributes across all types
- [ ] PII/secrets checked in logs, spans, and metrics
- [ ] Verdict aligns with severity distribution
- [ ] Actionable suggestions provided for non-PASS verdicts
- [ ] Chain decision explicit and justified
- [ ] Output follows structured format

---

## Deep References

Load on-demand for complex reviews:

| Reference | When to Load | Path |
|-----------|--------------|------|
| Logging Patterns | Complex structlog issues | `observe/logs/SKILL.md` |
| Tracing Patterns | Span propagation issues | `observe/traces/SKILL.md` |
| Metrics Patterns | Instrument selection issues | `observe/metrics/SKILL.md` |
| Observability Principles | Contract completeness | `rules/principles.md` § 1.10 |
