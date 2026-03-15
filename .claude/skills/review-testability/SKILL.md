---
name: review-testability
version: 1.0.0

description: |
  Review code for testability quality. Evaluates dependency injection, pure function separation,
  determinism, and behavior-focused design that survives refactoring.
  Use when reviewing implementations, validating code changes, or assessing test isolation.
  Relevant for Python modules, services, domain logic, and production code.

chains:
  invoked-by:
    - skill: implement/python
      context: "Post-implementation quality gate"
    - skill: implement/api
      context: "After API handler implementation"
  invokes:
    - skill: implement/python
      when: "Critical or major testability findings detected"
---

# Testability Review

> Validate code can be tested in isolation with deterministic, behavior-focused tests that survive refactoring.

## Quick Reference

| Aspect | Details |
|--------|---------|
| **Scope** | Classes, functions, modules, services |
| **Invokes** | `implement/python` (on failure) |
| **Verdicts** | `PASS` · `PASS_WITH_SUGGESTIONS` · `NEEDS_WORK` · `FAIL` |

---

## Review Objective

Ensure code enables fast, isolated, deterministic testing where tests verify observable *behavior*—not implementation details—enabling confident refactoring.

### Key Questions

1. Can units be tested in complete isolation from collaborators?
2. Are dependencies explicit and injectable?
3. Is business logic separated from I/O and side effects?
4. Will tests survive refactoring if behavior is unchanged?

---

## Workflow

```
SCOPE → CONTEXT → ANALYZE → CLASSIFY → VERDICT → REPORT → CHAIN
```

1. **Scope:** Production code (`**/src/**/*.py`, `**/app/**/*.py`) excluding tests
2. **Context:** Load `rules/principles.md` §2.7, `design/code/refs/testability.md`
3. **Analyze:** Apply criteria by severity priority (P0→P3)
4. **Classify:** Assign severity per criterion
5. **Verdict:** Derive from severity distribution
6. **Report:** Structured findings + summary
7. **Chain:** Invoke `implement/python` if FAIL/NEEDS_WORK

---

## Severity Classification

| Severity | Definition | Action |
|----------|------------|--------|
| **🔴 BLOCKER** | Untestable without production resources | Must fix |
| **🟠 CRITICAL** | Non-deterministic or hidden dependencies | Must fix |
| **🟡 MAJOR** | Tight coupling requiring extensive mocking | Should fix |
| **🔵 MINOR** | Suboptimal patterns increasing test complexity | Consider |
| **⚪ SUGGESTION** | Improvement opportunities | Optional |
| **🟢 COMMENDATION** | Exemplary testable design | Reinforce |

### Verdict Logic

- Any BLOCKER → `FAIL`
- Any CRITICAL → `NEEDS_WORK`
- Multiple MAJOR → `NEEDS_WORK`
- Few MAJOR/MINOR → `PASS_WITH_SUGGESTIONS`
- Only positive → `PASS`

---

## Evaluation Criteria

### Dependency Management (DM)

| ID | Criterion | Severity | Check |
|----|-----------|----------|-------|
| DM.1 | Collaborators injected via constructor | BLOCKER | No instantiation in methods |
| DM.2 | Dependencies typed to abstractions | MAJOR | Protocol/ABC, not concretions |
| DM.3 | Constructor performs only assignment | CRITICAL | No logic/I/O in `__init__` |
| DM.4 | No service locator pattern | BLOCKER | No global registry access |
| DM.5 | ≤5 constructor parameters | MAJOR | More signals overload |
| DM.6 | No singletons for dependencies | CRITICAL | Shared state across tests |

### Purity & Determinism (PD)

| ID | Criterion | Severity | Check |
|----|-----------|----------|-------|
| PD.1 | No direct `datetime.now()`/`time.time()` | CRITICAL | Inject clock |
| PD.2 | No direct `random()`/`uuid4()` | CRITICAL | Inject randomness |
| PD.3 | Pure functions separated from I/O | MAJOR | Core logic has no side effects |
| PD.4 | No global/module-level mutable state | BLOCKER | Tests pollute each other |
| PD.5 | Functions return values, not mutate | MAJOR | Easier assertions |
| PD.6 | Queries separated from commands | MAJOR | Verify without side effects |

### Design Structure (DS)

| ID | Criterion | Severity | Check |
|----|-----------|----------|-------|
| DS.1 | Single responsibility per unit | MAJOR | Fewer paths = fewer tests |
| DS.2 | No static methods with side effects | CRITICAL | Cannot substitute |
| DS.3 | Inheritance depth ≤2 levels | MAJOR | Full hierarchy understanding |
| DS.4 | No Law of Demeter violations | MINOR | `a.b.c.d` couples to structure |
| DS.5 | Behavior via public interface | MAJOR | Tests survive refactoring |
| DS.6 | Explicit seams for external resources | BLOCKER | DB/HTTP/FS behind abstractions |

---

## Patterns

### ✅ Testable Design

```python
class OrderPricingService:
    def __init__(self, discount_repo: DiscountRepository, clock: Clock):
        self._discounts = discount_repo  # Injected abstraction
        self._clock = clock              # Time injectable

    def calculate_total(self, order: Order) -> Money:
        discounts = self._discounts.get_applicable(order)
        return self._apply_discounts(order.subtotal, discounts)

    def _apply_discounts(self, subtotal: Money, discounts: list) -> Money:
        return Money(subtotal - sum(d.amount for d in discounts))  # Pure
```

**Why:** Dependencies explicit. Logic pure. Time abstracted. Each piece testable with simple fakes.

### ❌ Untestable Design

```python
class OrderProcessor:
    def process(self, order_id: str) -> None:
        order = db.query(f"SELECT * FROM orders WHERE id = {order_id}")  # Hidden
        if datetime.now() > order.expires_at:  # Non-deterministic
            return
        discount = DiscountService().calculate(order)  # Instantiated internally
        db.execute("UPDATE orders SET total = ?", order.total)  # Mixed I/O
```

**Why:** No seams. Time not injectable. Can't substitute DiscountService. Requires real DB.

---

## Finding Format

```markdown
### [🟠 CRITICAL] Direct datetime.now() prevents deterministic testing

**Location:** `src/services/auction.py:45`
**Criterion:** PD.1 - No direct datetime.now()

**Issue:**
`is_expired()` calls `datetime.now()` directly—impossible to test time edge cases.

**Evidence:**
```python
def is_expired(self, auction: Auction) -> bool:
    return datetime.now() > auction.end_time
```

**Suggestion:**
```python
def __init__(self, clock: Clock):
    self._clock = clock

def is_expired(self, auction: Auction) -> bool:
    return self._clock.now() > auction.end_time
```

**Rationale:**
Injected clock enables precise time control in tests without flakiness.
```

---

## Summary Format

```markdown
# Testability Review Summary

## Verdict: {{EMOJI}} {{VERDICT}}

| Metric | Count |
|--------|-------|
| Files Reviewed | X |
| Blockers | X |
| Critical | X |
| Major | X |

## Key Findings
1. {{TOP_FINDING}}
2. {{SECOND_FINDING}}
3. {{THIRD_FINDING}}

## Actions
1. {{ACTION}}

## Chain Decision
{{CHAIN_JUSTIFICATION}}
```

---

## Skill Chaining

| Verdict | Action | Target |
|---------|--------|--------|
| `FAIL` | Mandatory | `implement/python` |
| `NEEDS_WORK` | Targeted fixes | `implement/python` |
| `PASS_*` | Continue | Next review phase |

### Handoff

```markdown
**Chain Target:** `implement/python`
**Priority Findings:** {{IDS}}
**Constraint:** Preserve public API contracts
```

Re-review loop: Max 3 iterations on modified files.

---

## Deep References

| Reference | When | Path |
|-----------|------|------|
| Testability Patterns | Complex patterns | `design/code/refs/testability.md` |
| Principles | Justification | `rules/principles.md` §2.7, §2.9 |

---

## Quality Gates

- [ ] All production code analyzed
- [ ] Each finding has location + criterion + severity
- [ ] Verdict aligns with severity distribution
- [ ] Suggestions enable behavior-focused tests
- [ ] Chain decision explicit
