---
name: review-modularity
version: 1.0.0

description: |
  Review code for modularity quality. Evaluates coupling, cohesion, boundaries, and dependency management.
  Use when reviewing modules, classes, functions, validating architectural boundaries,
  or assessing separation of concerns, SOLID principles, and Law of Demeter compliance.
  Relevant for Python, TypeScript, any object-oriented or modular codebase.

chains:
  invoked-by:
    - skill: implement/python
    - skill: implement/api
    - skill: review/design
  invokes:
    - skill: refactor/extract
      when: "Critical or major findings detected"
    - skill: review/coherence
      when: "Boundary changes need consistency check"
---

# Modularity Review

> Validate loose coupling, high cohesion, and clean boundaries through systematic structural analysis.

## Quick Reference

| Aspect | Details |
|--------|---------|
| **Scope** | Modules, classes, functions, imports, dependencies |
| **Metrics** | CBO (≤7), LCOM (≤2), Fan-out (≤5) |
| **Invokes** | `refactor/extract` (on failure) |
| **Verdict** | `PASS` · `PASS_WITH_SUGGESTIONS` · `NEEDS_WORK` · `FAIL` |

---

## Review Objective

Ensure code is decomposed into cohesive, loosely-coupled modules with explicit boundaries.

**Key Questions:**







1. Are boundaries aligned with domain concepts and single responsibilities?
2. Are dependencies injected and pointing toward abstractions?
3. Is CBO ≤ 7, LCOM ≤ 2, fan-out ≤ 5?
4. Does code respect Law of Demeter (no train wrecks)?

---

## Evaluation Criteria

### Boundary Integrity (BI)

| ID | Criterion | Severity |
|----|-----------|----------|
| BI.1 | No circular dependencies between modules | 🔴 BLOCKER |
| BI.2 | No imports of private/internal symbols (`_`-prefixed) | 🟠 CRITICAL |
| BI.3 | Boundaries align with domain concepts | 🟡 MAJOR |
| BI.4 | No shared database tables across modules | 🟠 CRITICAL |

### Coupling Assessment (CA)

| ID | Criterion | Severity |
|----|-----------|----------|
| CA.1 | Dependencies injected, not instantiated internally | 🟠 CRITICAL |
| CA.2 | Depend on abstractions (Protocol/ABC) at boundaries | 🟡 MAJOR |
| CA.3 | CBO ≤ 7 (count distinct class dependencies) | 🟠 CRITICAL |
| CA.4 | Fan-out ≤ 5 direct dependencies per module | 🟡 MAJOR |
| CA.5 | No Law of Demeter violations (max one dot) | 🟡 MAJOR |

### Cohesion Assessment (CO)

| ID | Criterion | Severity |
|----|-----------|----------|
| CO.1 | Single Responsibility: one reason to change | 🟡 MAJOR |
| CO.2 | Methods use class state (LCOM ≤ 2) | 🟡 MAJOR |
| CO.3 | No feature envy (method uses another class's data more) | 🟡 MAJOR |
| CO.4 | Module ≤ 500 lines, ≤ 10 public symbols | 🔵 MINOR |

### SOLID Principles (SP)

| ID | Criterion | Severity |
|----|-----------|----------|
| SP.1 | Open/Closed: extensible without modification | 🟡 MAJOR |
| SP.2 | Liskov Substitution: subtypes are substitutable | 🟠 CRITICAL |
| SP.3 | Interface Segregation: no fat interfaces | 🟡 MAJOR |
| SP.4 | Dependency Inversion: abstractions at boundaries | 🟠 CRITICAL |

---

## Verdict Logic

```
Any BLOCKER?           → FAIL
Any CRITICAL?          → NEEDS_WORK
Multiple (≥3) MAJOR?   → NEEDS_WORK
Few MAJOR/MINOR?       → PASS_WITH_SUGGESTIONS
SUGGESTION only?       → PASS
```



---



## Metrics




### CBO (Coupling Between Objects)


Count distinct classes a class depends on. **Threshold: ≤7**


```python
# CBO = 4 (PaymentGateway, Logger, Customer, Order)

class OrderService:
    def __init__(self, gateway: PaymentGateway, logger: Logger): ...

    def process(self, customer: Customer, order: Order): ...
```


### LCOM (Lack of Cohesion in Methods)

Measures method relatedness via shared instance variables. **Threshold: ≤2**

```python
# LCOM = 0 (all methods use self._items) ✅
class Cart:
    def add(self, item): self._items.append(item)
    def total(self): return sum(i.price for i in self._items)

# LCOM = 3 (methods share nothing) ❌
class Utils:
    def parse_date(self, s): ...
    def format_currency(self, n): ...
    def validate_email(self, e): ...
```

---

## Patterns

### ✅ Good: Clean Boundary with DI

```python
class PaymentGateway(ABC):
    @abstractmethod
    async def charge(self, amount: Money) -> PaymentResult: ...

class OrderService:
    def __init__(self, payments: PaymentGateway, repo: OrderRepository):
        self._payments = payments  # Injected abstraction
        self._repo = repo
```

### ❌ Bad: Multiple Violations

```python
from inventory._internal.stock import StockLevel  # BI.2: Private import

class OrderService:
    def __init__(self):
        self._stripe = StripeClient("sk_live_xxx")  # CA.1: Hardcoded

    def process(self, order, invoice):
        rate = order.customer.address.region.tax_rate  # CA.5: Train wreck
        invoice._line_items.append(...)  # CO.3: Feature envy
```

---

## Finding Format

```markdown
### [🟠 CRITICAL] Hardcoded Dependency

**Location:** `src/orders/service.py:15`
**Criterion:** CA.1

**Issue:** OrderService instantiates StripeClient directly.

**Evidence:**
\`\`\`python
self._stripe = StripeClient("sk_live_xxx")
\`\`\`

**Suggestion:** Inject PaymentGateway abstraction via constructor.

**Rationale:** Hardcoded dependencies prevent testing and violate DI.
```

---

## Summary Format

```markdown
# Modularity Review Summary

## Verdict: 🟠 NEEDS_WORK

| Metric | Count |
|--------|-------|
| Files | 12 |
| Blockers | 0 |
| Critical | 2 |
| Major | 4 |
| Minor | 3 |

| Module | CBO | LCOM | Status |
|--------|-----|------|--------|
| orders/service.py | 8 | 1 | ⚠️ High CBO |
| shared/utils.py | 2 | 4 | ⚠️ Low cohesion |

## Chain Decision
→ `refactor/extract` for CA.1, CA.3
```

---

## Skill Chaining

| Verdict | Action | Target |
|---------|--------|--------|
| FAIL | Mandatory | `refactor/extract` |
| NEEDS_WORK | Targeted fixes | `refactor/extract` |
| PASS | Continue | `review/coherence` |

**Handoff:** Include priority findings, constraint to preserve public APIs.

**Re-review:** Max 3 iterations on modified files before escalation.

---

## Example: High CBO

**Input:** `src/orders/service.py` with 8 dependencies

**Finding:**
```markdown
### [🟠 CRITICAL] CBO=8 Exceeds Threshold

**Location:** `src/orders/service.py:10`
**Criterion:** CA.3

**Issue:** OrderService depends on 8 classes (repo, payments, inventory,
notifications, pricing, tax, shipping, audit).

**Suggestion:** Split into OrderCreator (repo, pricing, tax) and
OrderFulfillment (inventory, shipping).
```

**Verdict:** NEEDS_WORK → Chain to `refactor/extract`

---

## Deep References

| Reference | When | Path |
|-----------|------|------|
| Modularity patterns | Complex boundaries | `refs/modularity.md` |
| DDD contexts | Domain alignment | `refs/ddd.md` |
| Principles | Design violations | `rules/principles.md` |

---

## Quality Gates

- [ ] CBO/LCOM calculated for each class
- [ ] Each finding has location + criterion + severity
- [ ] Metrics summary table included
- [ ] Verdict matches severity distribution
- [ ] Chain decision explicit
