---
name: review-e2e-tests
version: 1.0.0

description: |
  Review end-to-end tests for user journey completeness, real system integration, and behavioral validation.
  Use when reviewing E2E test implementations, validating test pyramid adherence, or assessing test resilience to refactoring.
  Relevant for Python pytest E2E tests, FastAPI integration, Faststream integration, TestContainers usage, async workflow validation.
chains:
  invoked-by:
    - skill: test/e2e
      context: "Post-implementation quality gate"
    - skill: implement/python
      context: "After E2E test creation"
  invokes:
    - skill: test/e2e
      when: "Critical or major findings require test rewrites"
---

# E2E Test Review

> Validate that E2E tests exercise complete user journeys through real systems while remaining resilient to refactoring.

## Quick Reference

| Aspect | Details |
|--------|---------|
| **Scope** | `tests/e2e/**/*.py`, `@pytest.mark.e2e` decorated tests |
| **Invoked By** | `test/e2e`, `implement/python`, `/review` command |
| **Invokes** | `test/e2e` (on failure) |
| **Verdict Options** | `PASS` · `PASS_WITH_SUGGESTIONS` · `NEEDS_WORK` · `FAIL` |

---

## Review Objective

Ensure E2E tests validate complete user journeys through the real system while remaining independent, deterministic, and resilient to internal refactoring.

### Key Questions

1. Does each test represent a complete user journey through public interfaces?
2. Are tests exercising real infrastructure without mocking internals?
3. Will these tests survive internal refactoring without breaking?
4. Are async operations handled with polling rather than sleeps?

---

## Core Workflow

```
1. SCOPE    →  Find tests/e2e/**/*.py and @pytest.mark.e2e
2. ANALYZE  →  Evaluate against criteria (JC, SI, TI, BF, AH, DF, NM)
3. CLASSIFY →  Assign severity per finding
4. VERDICT  →  FAIL|NEEDS_WORK|PASS_WITH_SUGGESTIONS|PASS
5. CHAIN    →  Invoke test/e2e if rewrites needed
```

---

## Evaluation Criteria

### 🔴 BLOCKER Criteria

| ID | Criterion | Check |
|----|-----------|-------|
| JC.1 | Complete user flow, not fragments | Multi-step flow through public API |
| JC.2 | Public interfaces only | No direct service calls bypassing HTTP |
| SI.1 | Real infrastructure (DB, cache) | TestContainers, no in-memory fakes |
| SI.2 | **No internal mocks** | Zero `mocker.patch("app.*")` |
| BF.1 | Observable outcome assertions | Responses, DB state—not mock call counts |

### 🟠 CRITICAL Criteria

| ID | Criterion | Check |
|----|-----------|-------|
| TI.1 | No shared mutable state | No class attributes storing test data |
| TI.2 | No test ordering dependencies | Each test runnable in isolation |
| SI.3 | External APIs mocked at HTTP only | `respx`/`httpx_mock` for third-party services |
| BF.2 | Survives refactoring | No coupling to private methods |
| JC.3 | Happy + failure paths | Both success and error scenarios |

### 🟡 MAJOR Criteria

| ID | Criterion | Check |
|----|-----------|-------|
| AH.1 | `poll_until` for async | No `time.sleep()` or `asyncio.sleep()` |
| TI.3 | Transaction rollback/cleanup | `db_session` fixture with rollback |
| BF.3 | One journey per test | Single flow, single responsibility |
| DF.1 | Factory for test data | No hardcoded data dictionaries |

### 🔵 MINOR Criteria

| ID | Criterion | Check |
|----|-----------|-------|
| NM.1 | User story naming | `test_user_can_<action>_when_<condition>` |
| NM.2 | Marked `@pytest.mark.e2e` | Enables selective test runs |
| AH.2 | Explicit poll timeouts | `timeout=` parameter present |
| DF.2 | Minimal factory overrides | Only test-relevant attributes |

---

## Verdict Logic

```
Any BLOCKER?           → FAIL
Any CRITICAL?          → NEEDS_WORK
Multiple MAJOR?        → NEEDS_WORK
Few MAJOR/MINOR only?  → PASS_WITH_SUGGESTIONS
SUGGESTION only?       → PASS
```

---

## Anti-Pattern Detection

Run these checks to identify violations:

```bash
# SI.2: Internal mocks (BLOCKER)
grep -rn "mocker.patch.*app\." tests/e2e/

# AH.1: Sleep usage (MAJOR)
grep -rn "time\.sleep\|asyncio\.sleep" tests/e2e/

# TI.1: Shared state (CRITICAL)
grep -rn "class Test" tests/e2e/ | xargs grep -l "= None"
```

---

## Patterns

### ✅ Correct E2E Test

```python
@pytest.mark.e2e
async def test_user_can_complete_checkout(client, db_session, user_factory, product_factory):
    # Arrange: Factories
    user = user_factory.create(verified=True)
    product = product_factory.create(price=Decimal("99.99"), stock=10)

    # Act: Complete flow through HTTP
    await client.post("/cart/items", json={"product_id": str(product.id), "quantity": 2},
                      headers=auth_header(user))
    response = await client.post("/cart/checkout", headers=auth_header(user))

    # Assert: Observable outcomes
    assert response.status_code == 200
    order = await db_session.get(Order, response.json()["order_id"])
    assert order.status == OrderStatus.CONFIRMED
```

### ❌ Internal Mock (SI.2 BLOCKER)

```python
# WRONG: Defeats E2E purpose
mocker.patch("app.services.inventory.check_stock", return_value=True)
```

**Fix:** Use real services; mock only external third-party APIs via `respx`.

### ❌ Sleep Instead of Poll (AH.1 MAJOR)

```python
# WRONG: Slow and flaky
await asyncio.sleep(5)
```

**Fix:** `await poll_until(lambda: order.status == "processed", timeout=10.0)`

### ❌ Shared State (TI.1 CRITICAL)

```python
# WRONG: Test interdependency
class TestOrderFlow:
    order_id = None  # Shared between tests
```

**Fix:** Each test creates its own data via factories.

---

## Finding Format

```markdown
### [🔴 BLOCKER] Internal Service Mock

**Location:** `tests/e2e/test_checkout.py:45`
**Criterion:** SI.2

**Evidence:**
```python
mocker.patch("app.services.inventory.check_stock", return_value=True)
```

**Fix:** Remove mock. Use factory-created product with sufficient stock.
```

---

## Summary Format

```markdown
## Verdict: 🟠 NEEDS_WORK

| Blockers | Critical | Major | Minor |
|----------|----------|-------|-------|
| 1 | 2 | 3 | 4 |

**Key Findings:**
1. [BLOCKER] Internal mock in test_checkout.py (SI.2)
2. [CRITICAL] Shared state in test_order_flow.py (TI.1)
3. [MAJOR] sleep() instead of poll_until (AH.1)

**Chain:** `test/e2e` — Rewrite required for SI.2, TI.1 violations
```

---

## Skill Chaining

| Verdict | Action | Target |
|---------|--------|--------|
| `FAIL` | Mandatory rewrite | `test/e2e` |
| `NEEDS_WORK` | Targeted fixes | `test/e2e` |
| `PASS_WITH_SUGGESTIONS` | Optional | None |
| `PASS` | Continue | `review/functionality` |

**Handoff:** Provide criterion IDs, file locations, and preserve existing journey coverage.

---

## Quality Gates

- [ ] All `tests/e2e/**/*.py` analyzed
- [ ] All `@pytest.mark.e2e` tests found
- [ ] Zero `mocker.patch("app.*")` (SI.2)
- [ ] Zero `sleep()` calls (AH.1)
- [ ] Zero shared class state (TI.1)
- [ ] Factory usage verified (DF.1)
- [ ] Verdict matches severity distribution
- [ ] Chain decision explicit

---
