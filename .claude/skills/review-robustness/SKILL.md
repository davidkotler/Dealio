---
name: review-robustness
version: 1.0.0

description: |
  Review code for robustness and resilience quality. Evaluates failure handling, input validation,
  error propagation, and defensive patterns. Use when reviewing error handling code, validating
  external service integrations, or assessing fault tolerance. Relevant for Python backends,
  API handlers, async operations, database transactions, and any code crossing trust boundaries.

chains:
  invoked-by:
    - skill: implement/python
      context: "Post-implementation robustness validation"
    - skill: implement/api
      context: "API boundary validation"
  invokes:
    - skill: implement/python
      when: "Critical or major robustness findings detected"
---

# Robustness Review

> Validate that systems withstand failure, reject invalid input, and maintain integrity under stress.

## Quick Reference

| Aspect | Details |
|--------|---------|
| **Scope** | Error handling, input validation, external calls, state mutations |
| **Invoked By** | `implement/*`, `/review` command |
| **Invokes** | `implement/python` (on failure) |
| **Verdicts** | `PASS` · `PASS_WITH_SUGGESTIONS` · `NEEDS_WORK` · `FAIL` |

---

## Review Objective

Ensure code assumes everything can fail—validating aggressively at boundaries, failing fast with clear signals, and never silently corrupting state.

### Key Questions

1. Are all external inputs validated at system boundaries?
2. Do expected failure modes have explicit, typed representations?
3. Are external dependencies protected with timeouts, retries, circuit breakers?
4. Is error context preserved through call chains?
5. Are mutations idempotent and safe to retry?

### Out of Scope

- Business logic correctness → `review/functionality`
- Code style → `review/style`
- Performance → `review/performance`

---

## Core Workflow

```
1. SCOPE    →  Identify boundary code, external calls, mutations
2. CONTEXT  →  Load robustness patterns & principles
3. ANALYZE  →  Check validation, errors, resilience patterns
4. CLASSIFY →  Assign severity per criterion
5. VERDICT  →  Pass/fail based on severity distribution
6. REPORT   →  Output structured findings
7. CHAIN    →  Invoke implement/* if fixes needed
```

### Scope Patterns

```bash
**/api/**/*.py, **/routes/**/*.py    # API boundaries
**/services/**/*.py, **/clients/**/*.py  # External calls
**/repositories/**/*.py              # State mutations
```

---

## Severity Classification

| Severity | Definition | Action |
|----------|------------|--------|
| 🔴 BLOCKER | Silent corruption, swallowed exceptions, unvalidated input | Must fix |
| 🟠 CRITICAL | Missing timeouts, lost error context, non-idempotent mutations | Must fix |
| 🟡 MAJOR | None/null for errors, unbounded collections, catch-all handlers | Should fix |
| 🔵 MINOR | Missing circuit breakers, no graceful degradation | Consider |
| ⚪ SUGGESTION | Could use Result types | Optional |

### Verdict Logic

```
BLOCKER found         → FAIL
CRITICAL found        → NEEDS_WORK
Multiple MAJOR found  → NEEDS_WORK
Few MAJOR/MINOR only  → PASS_WITH_SUGGESTIONS
SUGGESTION only       → PASS
```

---

## Evaluation Criteria

### Input Validation (IV)

| ID | Criterion | Severity |
|----|-----------|----------|
| IV.1 | External input validated at boundary (Pydantic at API entry) | 🔴 BLOCKER |
| IV.2 | Schema/types/constraints checked before processing | 🟠 CRITICAL |
| IV.3 | Validation separated from business logic | 🟡 MAJOR |
| IV.4 | Collections have explicit size bounds (`max_length`) | 🟡 MAJOR |

### Error Handling (EH)

| ID | Criterion | Severity |
|----|-----------|----------|
| EH.1 | No silently swallowed exceptions (`except: pass`) | 🔴 BLOCKER |
| EH.2 | Error context preserved (`raise ... from e`) | 🟠 CRITICAL |
| EH.3 | Expected failures use Result/Union types, not exceptions | 🟡 MAJOR |
| EH.4 | No None/null returned for errors | 🟡 MAJOR |
| EH.5 | No catch-all without re-raising or logging | 🟡 MAJOR |

### External Dependencies (ED)

| ID | Criterion | Severity |
|----|-----------|----------|
| ED.1 | Timeouts on all blocking operations | 🟠 CRITICAL |
| ED.2 | Retry with exponential backoff (no infinite retries) | 🟡 MAJOR |
| ED.3 | Circuit breakers for external calls | 🔵 MINOR |
| ED.4 | Graceful degradation for non-critical dependencies | 🔵 MINOR |

### Idempotency & State (IS)

| ID | Criterion | Severity |
|----|-----------|----------|
| IS.1 | Mutations are idempotent (idempotency keys) | 🟠 CRITICAL |
| IS.2 | Check-before-write for retryable operations | 🟡 MAJOR |
| IS.3 | Atomic transactions for multi-step mutations | 🟡 MAJOR |
| IS.4 | No silent defaults masking missing required data | 🔴 BLOCKER |

### Resource Management (RM)

| ID | Criterion | Severity |
|----|-----------|----------|
| RM.1 | Queues and collections bounded | 🟡 MAJOR |
| RM.2 | Context managers for resource cleanup | 🔵 MINOR |

---

## Patterns & Anti-Patterns

### ✅ Quality Indicators

```python
# Explicit failure modes
PaymentResult = Union[PaymentSuccess, InsufficientFunds, AccountLocked]

# Full resilience stack
@circuit(failure_threshold=5, recovery_timeout=30)
@retry(stop=stop_after_attempt(3), wait=wait_exponential(max=10))
async def fetch_inventory(sku: str) -> InventoryStatus:
    async with httpx.AsyncClient(timeout=5.0) as client:
        response = await client.get(f"{URL}/items/{sku}")
        return InventoryStatus.model_validate(response.json())
```

### ❌ Red Flags

```python
# BLOCKER: Silent swallowing
except Exception:
    pass

# CRITICAL: Lost context  
raise Exception("Failed")  # No `from e`

# BLOCKER: Silent defaults
value = data.get("key", "default")  # Required data masked

# CRITICAL: Non-idempotent
await gateway.charge(amount)  # No idempotency key
```

---

## Finding Format

```markdown
### [🔴 BLOCKER] Silent Exception in Handler

**Location:** `src/services/notification.py:45`
**Criterion:** EH.1 - No silently swallowed exceptions

**Issue:** Empty except block hides failures.

**Evidence:**
```python
except Exception:
    pass
```

**Fix:** Log and re-raise, or handle explicitly with degraded response.
```

---

## Review Summary Format

```markdown
# Robustness Review Summary

## Verdict: 🟠 NEEDS_WORK

| Blockers | Critical | Major | Minor |
|----------|----------|-------|-------|
| 1 | 3 | 5 | 2 |

## Key Findings
1. [BLOCKER] Silent exception in notification service (EH.1)
2. [CRITICAL] Missing timeouts on payment gateway (ED.1)
3. [CRITICAL] Error context lost in order processor (EH.2)

## Chain Decision
→ `implement/python` with priority: EH.1, ED.1, EH.2
```

---

## Skill Chaining

| Verdict | Action | Target |
|---------|--------|--------|
| FAIL | Mandatory fix | `implement/python` |
| NEEDS_WORK | Targeted fixes | `implement/python` |
| PASS_WITH_SUGGESTIONS | None | Continue pipeline |
| PASS | Continue | Next review phase |

### Handoff

```markdown
**Target:** `implement/python`
**Findings:** EH.1, ED.1, EH.2
**Constraint:** Preserve business logic; add defensive patterns
```

---

## Quality Gates

Before completing review:

- [ ] All `except` blocks checked for silent swallowing
- [ ] All external calls checked for timeout configuration
- [ ] All mutations checked for idempotency
- [ ] All collections checked for bounds
- [ ] Error context preservation verified
- [ ] Each finding has location + criterion + severity
- [ ] Verdict aligns with severity distribution
