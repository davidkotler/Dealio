---
name: review-evolvability
version: 1.0.0

description: |
  Review code for evolvability quality. Evaluates capacity to adapt to new requirements,
  technologies, and scale demands with minimal disruption to existing functionality.
  Use when reviewing modules, interfaces, schemas, or dependencies, validating architectural
  changes, refactoring, or dependency updates, or assessing extensibility, interface stability,
  and change isolation.
  Relevant for Python, TypeScript, APIs, data models, service boundaries, and any code that
  will need to evolve over time.

chains:
  invoked-by:
    - skill: implement/python
      context: "Post-implementation quality gate for evolvability"
    - skill: implement/api
      context: "API interface evolution verification"
    - skill: review/modularity
      context: "Complementary boundary analysis"
  invokes:
    - skill: implement/python
      when: "Critical or major evolvability findings detected"
    - skill: review/modularity
      when: "Boundary violations discovered"
---

# Evolvability Review

> Validate that code is designed to gracefully accommodate change over time without requiring wholesale rewrites.

## Quick Reference

| Aspect | Details |
|--------|---------|
| **Dimension** | Evolvability |
| **Scope** | Interfaces, dependencies, extension points, schemas, module boundaries |
| **Invoked By** | `implement/*`, `review/modularity`, `/review` command |
| **Invokes** | `implement/python` (on failure), `review/modularity` |
| **Verdict Options** | `PASS` · `PASS_WITH_SUGGESTIONS` · `NEEDS_WORK` · `FAIL` |

---

## Review Objective

Ensure code exhibits localized change impact, clear extension mechanisms, stable interfaces, and reversibility—the four pillars of evolvable systems.

### This Review Answers

1. Are changes localized, or will modifications cascade across modules?
2. Are public interfaces stable, versioned, and implementation-agnostic?
3. Are extension points explicit, allowing new behavior without modification?
4. Are third-party dependencies isolated behind adapters you control?

### Out of Scope

- Performance optimization (see `review/performance`)
- Test coverage adequacy (see `review/testability`)
- Code style and formatting (see `review/style`)

---

## Core Workflow

```
┌─────────────────────────────────────────────────────────────┐
│                    REVIEW WORKFLOW                          │
├─────────────────────────────────────────────────────────────┤
│  1. SCOPE    →  Identify interfaces, dependencies, schemas  │
│  2. CONTEXT  →  Load evolvability principles & patterns     │
│  3. ANALYZE  →  Apply criteria: IS, CI, EM, DE              │
│  4. CLASSIFY →  Assign severity to each finding             │
│  5. VERDICT  →  Determine pass/fail based on findings       │
│  6. REPORT   →  Output structured review results            │
│  7. CHAIN    →  Invoke downstream skills if needed          │
└─────────────────────────────────────────────────────────────┘
```

### Step 1: Scope Definition

Identify review targets using these patterns:

```bash
# Public interfaces and contracts
**/interfaces/**/*.py
**/protocols/**/*.py
**/contracts/**/*.py
**/*_protocol.py
**/*_interface.py

# API boundaries
**/api/**/*.py
**/routes/**/*.py
**/schemas/**/*.py

# External dependencies and adapters
**/adapters/**/*.py
**/clients/**/*.py
**/gateways/**/*.py

# Configuration and feature flags
**/config/**/*.py
**/settings/**/*.py
**/*_config.py
```

### Step 2: Context Loading

Before analysis, internalize:







- **Principles:** `rules/principles.md` → Loose Coupling, Dependency Inversion, API-First
- **Conventions:** `rules/architecture.md` → Bounded Contexts, Service Boundaries
- **Patterns:** `skills/design/code/refs/evolvability.md` → Strategy, Anti-Corruption Layer, Versioning

### Step 3: Systematic Analysis

For each artifact, evaluate against criteria in order of severity:

| Priority | Criterion Category | Weight |
|----------|-------------------|--------|
| P0 | Interface Stability (IS) | Blocker |
| P1 | Change Isolation (CI) | Critical |
| P2 | Extension Mechanisms (EM) | Major |
| P3 | Data Evolution (DE) | Minor to Major |

### Step 4: Severity Classification

| Severity | Definition | Action Required |
|----------|------------|-----------------|
| **🔴 BLOCKER** | Breaking change without migration path; exposed internals in public API | Must fix before merge |
| **🟠 CRITICAL** | Concrete coupling preventing substitution; circular dependencies | Must fix, may defer |
| **🟡 MAJOR** | Missing extension points; hardcoded behavior; leaky abstractions | Should fix |
| **🔵 MINOR** | Missing versioning; undocumented architectural decisions | Consider fixing |
| **⚪ SUGGESTION** | Opportunity for improved extensibility; optional abstraction | Optional improvement |
| **🟢 COMMENDATION** | Exemplary evolvability patterns; excellent interface design | Positive reinforcement |

### Step 5: Verdict Determination

```
Findings Analysis
       │
       ├─► Any BLOCKER? ──────────────► FAIL
       │
       ├─► Any CRITICAL? ─────────────► NEEDS_WORK
       │
       ├─► Multiple MAJOR? ───────────► NEEDS_WORK
       │
       ├─► Few MAJOR or MINOR only? ──► PASS_WITH_SUGGESTIONS
       │
       └─► SUGGESTION/COMMENDATION ───► PASS
```

---

## Evaluation Criteria

### Interface Stability (IS)

| ID | Criterion | Severity | Check |
|----|-----------|----------|-------|
| IS.1 | Public interfaces depend on abstractions (Protocol/ABC) | CRITICAL | No concrete types in public signatures |
| IS.2 | All public APIs are versioned or version-ready | MAJOR | Version in URL, header, or module path |
| IS.3 | No internal types exposed in public signatures | BLOCKER | No internal IDs, enums, or data structures leaked |
| IS.4 | Contracts defined before implementations | MAJOR | Protocol/interface exists separate from implementation |
| IS.5 | Breaking changes have deprecation period | BLOCKER | No sudden removal; migration path documented |

### Change Isolation (CI)

| ID | Criterion | Severity | Check |
|----|-----------|----------|-------|
| CI.1 | Third-party dependencies wrapped in adapters | CRITICAL | External libs behind interfaces you control |
| CI.2 | No circular dependencies between modules | CRITICAL | Dependency graph is acyclic |
| CI.3 | Configuration external to code | MAJOR | Env vars, config files, or feature flags |
| CI.4 | Modules designed for independent evolution | MAJOR | Clear boundaries, no shared mutable state |
| CI.5 | Single requirement change affects only one module | MAJOR | Changes don't cascade across boundaries |

### Extension Mechanisms (EM)

| ID | Criterion | Severity | Check |
|----|-----------|----------|-------|
| EM.1 | Explicit extension points for anticipated variation | MAJOR | Strategy pattern, plugins, or hooks defined |
| EM.2 | New behavior adds, not modifies (Open/Closed) | MAJOR | Extension through composition, not modification |
| EM.3 | Dependencies injected, not instantiated internally | CRITICAL | Constructor/parameter injection, not `new` |
| EM.4 | Feature flags available for behavior variation | MINOR | Gradual rollout capability exists |
| EM.5 | Plugin/registry pattern for variable output formats | MINOR | Dynamic registration over hardcoded switch |

### Data Evolution (DE)

| ID | Criterion | Severity | Check |
|----|-----------|----------|-------|
| DE.1 | Schema changes are additive (new fields optional) | MAJOR | No required field additions without defaults |
| DE.2 | Field removal follows deprecation process | CRITICAL | Stop writing → stop reading → remove |
| DE.3 | Field semantics changes use new field names | MAJOR | Old field deprecated, new field added |
| DE.4 | Event/message formats support schema evolution | MAJOR | Backward-compatible serialization |
| DE.5 | Migration tooling exists for breaking changes | BLOCKER | Scripts/tools for data migration provided |

---

## Patterns & Anti-Patterns

### ✅ Indicators of Quality

```python
# Strategy pattern: behavior varies without code change
class PricingStrategy(Protocol):
    def calculate(self, order: Order) -> Money: ...

class OrderService:
    def __init__(self, pricing: PricingStrategy):  # Injected, swappable
        self._pricing = pricing

    def total(self, order: Order) -> Money:
        return self._pricing.calculate(order)
```

**Why this works:** Pricing logic can evolve (new discount rules, A/B testing) without modifying `OrderService`. The interface is stable; implementations are swappable.

### ❌ Red Flags

```python
# Concrete coupling: can't substitute implementations
class OrderProcessor:
    def __init__(self):
        self._notifier = EmailNotifier()      # Hardcoded concrete class
        self._payment = StripePayment()       # Locked to specific vendor

    async def process(self, order: Order):
        # Changing notification method requires modifying this class
        await self._payment.charge(order)
        await self._notifier.send(order.customer, "Order confirmed")
```

**Why this fails:** Adding SMS notifications or switching payment providers requires modifying `OrderProcessor`. Changes cascade; nothing is swappable.

---

## Finding Output Format

Structure each finding as:

```markdown
### [🟠 CRITICAL] Concrete Coupling Prevents Evolution

**Location:** `src/orders/processor.py:15-22`
**Criterion:** CI.1 - Third-party dependencies wrapped in adapters

**Issue:**
Direct instantiation of `StripePayment` couples order processing to a specific
payment vendor. Switching providers requires modifying this class.

**Evidence:**
```python
class OrderProcessor:
    def __init__(self):
        self._payment = StripePayment()  # Concrete dependency
```

**Suggestion:**
Inject a `PaymentGateway` protocol and wrap Stripe in an adapter:
```python
class OrderProcessor:
    def __init__(self, payment: PaymentGateway):
        self._payment = payment
```

**Rationale:**
Evolvability requires dependencies on abstractions. When payment requirements
change (new provider, multi-provider support), only the adapter changes.
```

---

## Review Summary Format

```markdown
# Evolvability Review Summary

## Verdict: 🟠 NEEDS_WORK

| Metric | Count |
|--------|-------|
| Files Reviewed | 12 |
| Blockers | 0 |
| Critical | 2 |
| Major | 4 |
| Minor | 2 |
| Suggestions | 3 |
| Commendations | 1 |

## Key Findings

1. **CI.1 CRITICAL** - PaymentService directly instantiates Stripe client
2. **CI.2 CRITICAL** - Circular import between orders and inventory modules
3. **IS.3 MAJOR** - Internal OrderStatus enum exposed in public API response

## Recommended Actions

1. Wrap Stripe client in PaymentGateway adapter
2. Extract shared types to break circular dependency
3. Create public OrderStatusDTO separate from internal enum

## Skill Chain Decision

Invoking `implement/python` to address critical findings CI.1 and CI.2 before re-review.
```

---

## Skill Chaining

### Chain Triggers

| Verdict | Chain Action | Target Skill |
|---------|--------------|--------------|
| `FAIL` | Mandatory implementation fixes | `implement/python` |
| `NEEDS_WORK` | Targeted fixes for critical/major | `implement/python` |
| `PASS_WITH_SUGGESTIONS` | Optional improvements | None (suggestions only) |
| `PASS` | Continue pipeline | `review/robustness` or next phase |

### Handoff Protocol

When chaining to implement:

```markdown
**Chain Target:** `implement/python`
**Priority Findings:** IS.3, CI.1, CI.2
**Context:** Review identified 2 critical evolvability violations requiring remediation

**Constraint:** Preserve existing public interface contracts; add adapters without breaking consumers

```



### Re-Review Loop



After implement completes, re-invoke this review with:

- Scope limited to modified files
- Focus on previously-failed criteria
- Maximum 3 iterations before escalation

---

## Integration Points

### Upstream Integration

This skill is invoked by:

| Source | Trigger | Context Provided |
|--------|---------|------------------|
| `implement/python` | Post-implementation | Changed files list |
| `implement/api` | After API changes | Modified endpoints |
| `/review` command | Explicit invocation | User-specified scope |

### Downstream Integration

This skill invokes:

| Target | Condition | Handoff |
|--------|-----------|---------|
| `implement/python` | Verdict ≠ PASS | Findings + priority |
| `review/modularity` | Boundary violations | Related findings |
| `review/robustness` | After evolvability passes | Continue pipeline |

---

## Examples

### Example 1: Anti-Corruption Layer Missing

**Input:** Review `src/orders/checkout.py`

**Analysis:**
```python
class CheckoutService:
    async def process(self, order: Order, token: str):
        # Direct Stripe API call - no adapter layer
        response = await stripe.charges.create(
            amount=int(order.total * 100),  # Stripe-specific: cents
            currency="usd",
            source=token,
        )
        order.payment_id = response.id  # Stripe ID format leaks into domain
```

**Output:**
```markdown
### [🟠 CRITICAL] External API Leaks Through Domain

**Location:** `src/orders/checkout.py:12-19`
**Criterion:** CI.1 - Third-party dependencies wrapped in adapters

**Issue:**
Stripe API called directly in domain service. Stripe-specific details (cents conversion,
response ID format) leak throughout codebase. Any Stripe API change affects this file.

**Suggestion:**
Create `PaymentGateway` protocol and `StripeAdapter`:
```python
class PaymentGateway(Protocol):
    async def charge(self, amount: Money, token: str) -> PaymentResult: ...

class StripeAdapter:
    async def charge(self, amount: Money, token: str) -> PaymentResult:
        response = await self._client.charges.create(...)
        return PaymentResult(id=PaymentId(response.id), ...)
```

**Rationale:**
Anti-corruption layers protect your domain from external API changes. When Stripe
updates their API or you switch providers, only the adapter changes.
```

**Verdict:** `NEEDS_WORK` → Chain to `implement/python`

### Example 2: Excellent Strategy Pattern Usage

**Input:** Review `src/pricing/service.py`

**Analysis:**
```python
class PricingStrategy(Protocol):
    def calculate(self, order: Order) -> Money: ...

class TieredPricing:
    def calculate(self, order: Order) -> Money:
        # Volume-based pricing logic
        ...

class PricingService:
    def __init__(self, strategy: PricingStrategy):
        self._strategy = strategy

    def get_price(self, order: Order) -> Money:
        return self._strategy.calculate(order)
```

**Output:**
```markdown
### [🟢 COMMENDATION] Exemplary Strategy Pattern Implementation

**Location:** `src/pricing/service.py:1-20`
**Criterion:** EM.1 - Explicit extension points for anticipated variation

**Observation:**
Pricing strategy is properly abstracted behind a Protocol. New pricing models
(promotional, subscription, dynamic) can be added without modifying PricingService.
Dependency injection enables testing and runtime configuration.

**Impact:**
This design allows pricing to evolve independently of order processing. A/B testing
different pricing strategies requires only configuration changes.
```

**Verdict:** `PASS`

---

## Deep References

Load on-demand for complex reviews:

| Reference | When to Load | Path |
|-----------|--------------|------|
| Evolvability Patterns | Complex refactoring needed | `refs/evolvability.md` |
| Engineering Principles | Principle violations detected | `rules/principles.md` |
| DDD Concepts | Bounded context issues | `skills/design/code/refs/ddd.md` |
| Modularity Guide | Boundary violations | `skills/design/code/refs/modularity.md` |

---

## Quality Gates

Before finalizing review output:

- [ ] All interfaces, adapters, and schemas in scope were analyzed
- [ ] Each finding has location + criterion ID + severity
- [ ] Verdict aligns with severity distribution
- [ ] Actionable suggestions provided for non-PASS verdicts
- [ ] Chain decision is explicit and justified
- [ ] Output follows structured format
- [ ] No false positives from intentional design decisions (documented exceptions)
