---
name: review-reusability
version: 1.0.0

description: |
  Review code for reusability quality. Evaluates whether cross-cutting and shared functionality
  is properly extracted to shared libraries or shared modules, whether services reuse existing
  libs instead of reimplementing, and whether shared code exposes stable interfaces.
  Use when reviewing new implementations, validating library usage, assessing code duplication
  across services or domains, or checking that cross-cutting concerns use established shared
  libraries. Relevant for Python microservices, shared libraries, monorepo code, and any code
  that might duplicate behavior already available in `libs/`.

chains:
  invoked-by:
    - skill: implement/python
      context: "Post-implementation reusability validation"
    - skill: implement/api
      context: "API pattern reuse verification"
    - skill: review/modularity
      context: "Complementary boundary and reuse analysis"
  invokes:
    - skill: implement/python
      when: "Critical or major reusability findings detected"
    - skill: review/coherence
      when: "Inconsistent usage of shared code across consumers"
---

# Reusability Review

> Validate that shared behavior lives in shared places, consumers reuse rather than reimplement, and shared code exposes stable interfaces.

## Quick Reference

| Aspect | Details |
|--------|---------|
| **Dimension** | Reusability (Consistency & Duplication Elimination) |
| **Scope** | Cross-service libraries (`libs/`), cross-domain shared modules, import patterns, duplication |
| **Invoked By** | `implement/*`, `review/modularity`, `/review` command |
| **Invokes** | `implement/python` (on failure), `review/coherence` |
| **Verdict Options** | `PASS` · `PASS_WITH_SUGGESTIONS` · `NEEDS_WORK` · `FAIL` |

---

## Review Objective

Ensure the codebase maintains a single source of truth for each piece of shared behavior — cross-service logic lives in `libs/`, cross-domain logic lives in shared service modules, and no service reimplements what a shared library already provides.

Duplication is not just wasted effort — it creates behavioral drift. When the same logic exists in multiple places, each copy evolves independently: bugs get fixed in one but not others, edge cases get handled inconsistently, and consumers experience different behavior from what should be the same operation.

### This Review Answers

1. Does this code reimplement functionality already available in a shared library (`libs/`)?
2. Is cross-service logic properly extracted to `libs/lib-<name>`?
3. Is cross-domain logic within a service extracted to a shared module?
4. Does shared code expose stable interfaces (Protocol/ABC) without service-specific assumptions?

### Out of Scope

- Module boundary correctness (see `review/modularity`)
- Interface evolution and versioning (see `review/evolvability`)
- Code style and formatting (see `review/style`)

---

## Core Workflow

```
┌─────────────────────────────────────────────────────────────┐
│                  REUSABILITY REVIEW WORKFLOW                 │
├─────────────────────────────────────────────────────────────┤
│  1. SCOPE    →  Identify changed/new files                  │
│  2. CONTEXT  →  Inventory existing libs/ and shared modules │
│  3. ANALYZE  →  Apply criteria: DU, LP, IC, CQ              │
│  4. CLASSIFY →  Assign severity to each finding             │
│  5. VERDICT  →  Determine pass/fail based on findings       │
│  6. REPORT   →  Output structured review results            │
│  7. CHAIN    →  Invoke downstream skills if needed          │
└─────────────────────────────────────────────────────────────┘
```

### Step 1: Scope Definition

Identify review targets:

```bash
# Find changed files
git diff --name-only HEAD~1
# Or for broader scope
git diff --name-only main...HEAD
```

### Step 2: Context Loading

Before analysis, build a mental inventory of what already exists:

```bash
# Inventory shared libraries
ls libs/
# Check existing shared modules within each affected service
ls services/<name>/<name>/shared/ 2>/dev/null
ls services/<name>/<name>/common/ 2>/dev/null
# Find similar implementations across services
grep -rn "class.*Service\|def .*validate\|def .*format" services/ --include="*.py" | head -30
```

**Load these references:**

- **Shared Library Table:** `CLAUDE.md` → "Shared Libraries — When to Use Each"
- **Reusability Guide:** `skills/design-code/refs/reusability.md` → Placement decision tree
- **Principles:** `rules/principles.md` → Modularity, coherence

### Step 3: Systematic Analysis

Evaluate against criteria in priority order:

| Priority | Criterion Category | Weight |
|----------|-------------------|--------|
| P0 | Duplication Detection (DU) | Blocker |
| P1 | Library Placement (LP) | Critical |
| P2 | Interface Contracts (IC) | Major |
| P3 | Consumer Quality (CQ) | Minor to Major |

### Step 4: Severity Classification

| Severity | Definition | Action Required |
|----------|------------|-----------------|
| **🔴 BLOCKER** | Reimplements core shared library functionality (auth, observability, resilience) | Must fix before merge |
| **🟠 CRITICAL** | Cross-service logic lives in one service; shared code contains service-specific assumptions | Must fix, may defer |
| **🟡 MAJOR** | Cross-domain logic duplicated within service; shared code lacks stable interface | Should fix |
| **🔵 MINOR** | Opportunity to extract common pattern; minor import inconsistencies | Consider fixing |
| **⚪ SUGGESTION** | Proactive extraction opportunity not yet causing harm | Optional improvement |
| **🟢 COMMENDATION** | Exemplary reuse of shared libraries; well-designed shared module | Positive reinforcement |

### Step 5: Verdict Determination

```
Findings Analysis
       │
       ├─► Any BLOCKER? ──────────────► FAIL
       │   (reimplements lib-security, lib-observability, etc.)
       │
       ├─► Any CRITICAL? ─────────────► NEEDS_WORK
       │   (cross-service logic not in libs/, service-specific in shared)
       │
       ├─► Multiple MAJOR? ───────────► NEEDS_WORK
       │   (>2 duplication or interface issues)
       │
       ├─► Few MAJOR or MINOR only? ──► PASS_WITH_SUGGESTIONS
       │
       └─► SUGGESTION/COMMENDATION ───► PASS
```

---

## Evaluation Criteria

### DU: Duplication Detection

| ID | Criterion | Severity | Check |
|----|-----------|----------|-------|
| DU.1 | No reimplementation of `libs/` functionality | BLOCKER | Auth, logging, tracing, metrics, resilience, HTTP client, pagination, error envelopes must come from libs |
| DU.2 | No copy-paste of logic between services | BLOCKER | Identical or near-identical implementations across service boundaries |
| DU.3 | No duplicate implementations within a service across domains | MAJOR | Same logic in 2+ domains → extract to shared module |
| DU.4 | Types defined in `lib-schemas` not redefined locally | CRITICAL | Event envelopes, pagination, domain primitives, error formats |

**Detection approach:**

```bash
# Find potential reimplementations of lib-observability
grep -rn "import logging\|logging\.getLogger\|print(" services/ --include="*.py"
# Find potential reimplementations of lib-resilience
grep -rn "for attempt in range\|retry\|@retry" services/ --include="*.py" | grep -v "lib_resilience"
# Find potential reimplementations of lib-http
grep -rn "import httpx\|httpx\.\|import requests" services/ --include="*.py" | grep -v "lib_http"
# Find duplicate type definitions
grep -rn "class.*Envelope\|class.*Page\|class.*Cursor" services/ --include="*.py"
```

### LP: Library Placement

| ID | Criterion | Severity | Check |
|----|-----------|----------|-------|
| LP.1 | Cross-service functionality lives in `libs/lib-<name>` | CRITICAL | Not embedded in one service when 2+ need it |
| LP.2 | Cross-domain functionality lives in service shared module | MAJOR | Not duplicated across domains within a service |
| LP.3 | No premature extraction to `libs/` | MAJOR | Only one consumer today and no second foreseeable → keep local |
| LP.4 | Shared code has a cohesive responsibility | MAJOR | No "utils" or "helpers" grab-bags |
| LP.5 | `libs/` packages don't contain service-specific logic | CRITICAL | Libraries serve all consumers equally |

### IC: Interface Contracts

| ID | Criterion | Severity | Check |
|----|-----------|----------|-------|
| IC.1 | Shared code exposes Protocol/ABC interfaces | MAJOR | Consumers depend on abstractions, not implementations |
| IC.2 | Shared interfaces are generic (no service-specific assumptions) | CRITICAL | No hardcoded domain terms from one consumer |
| IC.3 | Shared code is independently testable | MAJOR | Has its own test suite, not tested only through consumers |
| IC.4 | Breaking changes to shared code follow deprecation paths | CRITICAL | No surprise breakage of downstream consumers |

### CQ: Consumer Quality

| ID | Criterion | Severity | Check |
|----|-----------|----------|-------|
| CQ.1 | Consumers import from canonical shared sources | MAJOR | `from lib_security import ...`, not local reimplementation |
| CQ.2 | Consumers use dependency injection for shared code | MAJOR | Shared implementations injected, not instantiated inline |
| CQ.3 | All consumers of a shared lib use it consistently | MINOR | Same configuration patterns, same usage patterns |
| CQ.4 | No consumer bypasses shared code for "special" cases | MAJOR | Special cases handled via strategy/config, not bypass |

---

## Shared Library Quick Reference

Before flagging duplication, verify against existing libraries:

| Library | What It Owns | Reimplementation Red Flags |
|---------|-------------|---------------------------|
| `lib-security` | Auth, authz, secrets, sanitization, tenant context | `jwt.decode(`, manual RBAC checks, custom auth middleware |
| `lib-observability` | Logging, tracing, metrics, health checks | `import logging`, `print(`, custom span creation |
| `lib-resilience` | Retry, circuit breaker, timeout, bulkhead, rate limiter | `for attempt in range`, `@retry`, manual backoff loops |
| `lib-http` | Outbound HTTP with resilience and tracing | Raw `httpx.get(`, `import requests`, manual retry around HTTP |
| `lib-schemas` | Envelopes, pagination, domain primitives, error formats | Local `CursorPage`, duplicate `EventEnvelope`, redefined enums |
| `lib-fastapi` | App factory, middleware, error handling, response builders | Bare `FastAPI()`, custom error handlers, manual CORS setup |
| `lib-faststream` | Event app factory, envelope enforcement, correlation | Bare `FastStream()`, manual event correlation |
| `lib-events` | Event context, registry, publisher protocol | Custom `EventPublisher`, manual correlation IDs |
| `lib-database` | Connection pools, health checks, instrumentation | Manual pool creation, custom DB health checks |
| `lib-aws` | S3, SQS, SNS, EventBridge, Secrets Manager wrappers | Direct `boto3.client(` calls without wrappers |
| `lib-settings` | Configuration composition via `BaseServiceSettings` | Manual `os.environ.get(` parsing |
| `lib-testing` | Factories, fixtures, contract validators, assertions | Custom test factories, hand-rolled DB fixtures |

---

## Patterns & Anti-Patterns

### Indicators of Quality

```python
# ✅ Consumer properly uses shared library
from lib_security.guards import AuthorizationGuard
from lib_observability import get_logger, get_tracer
from lib_resilience.presets import http_call_policy

class OrderService:
    def __init__(self, auth: AuthorizationGuard, ...):
        self._auth = auth  # Same guard, same behavior, every service
        self._logger = get_logger(__name__)
        self._tracer = get_tracer(__name__)
```

**Why this works:** Every service gets the same auth behavior, the same log format, the same trace context propagation. Bug fixes and improvements propagate to all consumers automatically.

### Red Flags

```python
# ❌ BLOCKER: Reimplements lib-observability
import logging
logger = logging.getLogger(__name__)  # Should use lib_observability.get_logger

# ❌ BLOCKER: Reimplements lib-resilience
async def call_with_retry(url: str, max_retries: int = 3):
    for attempt in range(max_retries):
        try:
            return await httpx.get(url)  # Also bypasses lib-http!
        except Exception:
            await asyncio.sleep(2 ** attempt)

# ❌ CRITICAL: Type redefined locally instead of using lib-schemas
class PaginatedResponse(BaseModel):  # Should use lib_schemas.pagination.CursorPage
    items: list[Any]
    next_cursor: str | None = None
```

**Why this fails:** Each service now has its own logging format, its own retry behavior, its own pagination contract. When a bug is found, it gets fixed in one place but not others. Consumers experience inconsistent behavior.

### The Behavioral Drift Anti-Pattern

```python
# Service A: Uses lib-resilience with circuit breaker
policy = http_call_policy(timeout=30)
result = await policy.execute(lambda: http_client.get(url))

# Service B: Rolls its own retry (no circuit breaker, no tracing)
for i in range(3):
    try:
        result = await httpx.get(url, timeout=10)
        break
    except httpx.TimeoutException:
        if i == 2: raise

# Service C: No resilience at all
result = await httpx.get(url)  # No timeout, no retry, no circuit breaker
```

**Impact:** Three services calling external APIs with three different failure modes. Service B and C will cascade failures that Service A would have isolated.

---

## Finding Output Format

```markdown
### [{{SEVERITY_EMOJI}} {{SEVERITY}}] {{FINDING_TITLE}}

**Location:** `{{FILE_PATH}}:{{LINE_NUMBER}}`
**Criterion:** {{CRITERION_ID}} - {{CRITERION_NAME}}
**Shared Alternative:** `{{LIB_OR_MODULE_PATH}}` (existing implementation)

**Issue:**
{{DESCRIPTION_OF_DUPLICATION_OR_MISPLACEMENT}}

**Evidence:**
\`\`\`python
# Your code:
{{DUPLICATED_OR_MISPLACED_CODE}}

# Available shared implementation (from {{SHARED_SOURCE}}):
{{EXISTING_SHARED_CODE}}
\`\`\`

**Suggestion:**
{{SPECIFIC_REMEDIATION}}

**Rationale:**
{{WHY_REUSE_MATTERS_HERE}}
```

---

## Review Summary Format

```markdown
# Reusability Review Summary

## Verdict: {{VERDICT_EMOJI}} {{VERDICT}}

| Metric | Count |
|--------|-------|
| Files Reviewed | {{COUNT}} |
| Shared Libraries Checked | {{COUNT}} |
| Blockers | {{COUNT}} |
| Critical | {{COUNT}} |
| Major | {{COUNT}} |
| Minor | {{COUNT}} |
| Commendations | {{COUNT}} |

## Reusability Dimensions

| Dimension | Status | Issues |
|-----------|--------|--------|
| Duplication Detection | {{✅/❌}} | {{COUNT}} |
| Library Placement | {{✅/❌}} | {{COUNT}} |
| Interface Contracts | {{✅/❌}} | {{COUNT}} |
| Consumer Quality | {{✅/❌}} | {{COUNT}} |

## Key Findings

{{TOP_3_FINDINGS_SUMMARY}}

## Recommended Actions

{{PRIORITIZED_REMEDIATION_STEPS}}

## Skill Chain Decision

{{CHAIN_DECISION_EXPLANATION}}
```

---

## Skill Chaining

### Chain Triggers

| Verdict | Chain Action | Target Skill |
|---------|--------------|--------------|
| `FAIL` | Mandatory: migrate to shared library | `implement/python` |
| `NEEDS_WORK` | Targeted extraction or migration | `implement/python` |
| `PASS_WITH_SUGGESTIONS` | Optional improvements | None (suggestions only) |
| `PASS` | Continue pipeline | Next review or task complete |

### Handoff Protocol

When chaining to implement:

```markdown
**Chain Target:** `implement/python`
**Priority Findings:** DU.1, LP.1, IC.2
**Context:** Review identified {{COUNT}} reusability violations requiring remediation

**Constraint:** Extract to appropriate shared boundary; preserve existing consumer interfaces

**Reference Files:** {{LIST_OF_SHARED_LIBS_TO_USE_OR_EXTEND}}
```

### Re-Review Loop

After implement completes:

- Scope limited to modified files
- Focus on previously-failed criteria
- Maximum 2 iterations before escalation

---

## Integration Points

### Upstream Integration

| Source | Trigger | Context Provided |
|--------|---------|------------------|
| `implement/python` | Post-implementation | Changed files, module context |
| `implement/api` | New endpoint created | Route patterns, shared middleware |
| `/review` command | Explicit invocation | User-specified scope |

### Downstream Integration

| Target | Condition | Handoff |
|--------|-----------|---------|
| `implement/python` | Verdict ≠ PASS | Findings + shared lib references |
| `review/coherence` | Inconsistent shared code usage | Consumer patterns for alignment |
| `review/modularity` | Boundary issues discovered | Module structure analysis |

---

## Examples

### Example 1: Reimplemented Shared Library

**Input:** Review `services/billing/billing/domains/invoicing/flows/send_invoice.py`

**Analysis:**
```python
import logging
logger = logging.getLogger(__name__)

class SendInvoiceFlow:
    async def execute(self, invoice: Invoice) -> None:
        logger.info(f"Sending invoice {invoice.id}")
        # ... business logic ...
```

**Output:**
```markdown
### [🔴 BLOCKER] Reimplements lib-observability Logging

**Location:** `services/billing/billing/domains/invoicing/flows/send_invoice.py:1-2`
**Criterion:** DU.1 - No reimplementation of `libs/` functionality
**Shared Alternative:** `libs/lib-observability` → `get_logger`

**Issue:**
Uses stdlib `logging` directly instead of `lib_observability.get_logger`. This bypasses
structured logging, trace correlation, and consistent log format across all services.

**Evidence:**
\`\`\`python
# Your code:
import logging
logger = logging.getLogger(__name__)

# Available shared implementation (from lib-observability):
from lib_observability import get_logger
logger = get_logger(__name__)
\`\`\`

**Suggestion:**
Replace `import logging` with `from lib_observability import get_logger`.
This provides structured logging with automatic trace ID correlation.

**Rationale:**
Every service must use lib-observability for consistent log format, trace correlation,
and centralized log management. Stdlib logging produces unstructured output that
breaks Loki queries and loses trace context.
```

**Verdict:** `FAIL` → Chain to `implement/python`

### Example 2: Proper Shared Library Usage

**Input:** Review `services/order/order/domains/checkout/flows/process_payment.py`

**Analysis:**
```python
from lib_resilience.presets import http_call_policy
from lib_http import HttpClient
from lib_observability import get_logger, get_tracer

class ProcessPaymentFlow:
    def __init__(self, http: HttpClient, policy: http_call_policy):
        self._http = http
        self._policy = policy
        self._logger = get_logger(__name__)
        self._tracer = get_tracer(__name__)
```

**Output:**
```markdown
### [🟢 COMMENDATION] Exemplary Shared Library Usage

**Location:** `services/order/order/domains/checkout/flows/process_payment.py:1-10`
**Criterion:** CQ.1 - Consumers import from canonical shared sources

**Observation:**
All cross-cutting concerns properly imported from shared libraries:
- `lib_resilience` for fault tolerance
- `lib_http` for outbound HTTP with tracing
- `lib_observability` for structured logging and tracing

**Impact:**
This service automatically gets consistent retry behavior, circuit breaking, trace
propagation, and structured logging. Bug fixes in shared libraries propagate here
without any code changes.
```

**Verdict:** `PASS`

### Example 3: Cross-Domain Duplication Within Service

**Input:** Review `services/order/order/domains/`

**Analysis:**
```bash
# Found identical date formatting in two domains
grep -rn "def format_date" services/order/ --include="*.py"
# services/order/order/domains/checkout/utils.py:5:def format_date(dt: datetime) -> str:
# services/order/order/domains/invoicing/utils.py:8:def format_date(dt: datetime) -> str:
```

**Output:**
```markdown
### [🟡 MAJOR] Duplicate Date Formatting Across Domains

**Location:** `services/order/order/domains/checkout/utils.py:5`,
`services/order/order/domains/invoicing/utils.py:8`
**Criterion:** DU.3 - No duplicate implementations within a service across domains

**Issue:**
`format_date` is implemented identically in both checkout and invoicing domains.

**Suggestion:**
Extract to `services/order/order/shared/formatting.py` and import from both domains.

**Rationale:**
When formatting requirements change (e.g., locale support), both implementations
must be updated independently — a recipe for behavioral drift.
```

**Verdict:** `NEEDS_WORK` → Chain to `implement/python`

---

## Deep References

Load on-demand for complex reviews:

| Reference | When to Load | Path |
|-----------|--------------|------|
| Reusability Patterns | Complex extraction decisions | `skills/design-code/refs/reusability.md` |
| Shared Library Table | Identifying reimplementations | `CLAUDE.md` → "Shared Libraries" section |
| Engineering Principles | Principle violations detected | `rules/principles.md` |
| Modularity Guide | Boundary overlap with reuse | `skills/design-code/refs/modularity.md` |

---

## Quality Gates

Before finalizing review output:

- [ ] All shared libraries in `libs/` checked for reimplementation in reviewed code
- [ ] Cross-service duplication patterns searched (not just single-file review)
- [ ] Each finding has location + criterion ID + severity + shared alternative
- [ ] Shared Library Quick Reference table consulted for every import pattern
- [ ] Verdict aligns with severity distribution
- [ ] Actionable suggestions point to specific shared code to use
- [ ] Chain decision is explicit with target skill
- [ ] No false positives from intentional local overrides (documented exceptions)
