---
name: review-unit-tests
version: 1.0.0

description: |
  Review unit tests for behavior-focus, refactor-resilience, and quality standards.
  Use when validating test implementations, reviewing test PRs, assessing test coverage,
  or checking test quality after test generation.
  Relevant for pytest, Python testing, TDD, post-implementation validation, test factories.

chains:
  invoked-by:
    - skill: test/unit
      context: "Post-implementation quality gate"
    - skill: implement/python
      context: "When tests are generated alongside implementation"
  invokes:
    - skill: test/unit
      when: "Critical or major findings detected requiring test rewrites"
---

# Unit Tests Review

> Validate that tests verify behavior—not implementation—enabling fearless refactoring.

## Quick Reference

| Aspect | Details |
|--------|---------|
| **Dimension** | Unit Test Quality |
| **Scope** | `test_*.py`, `*_test.py`, `conftest.py`, `factories/*.py` |
| **Invoked By** | `test/unit`, `implement/python`, `/review` command |
| **Invokes** | `test/unit` (on failure) |
| **Verdict Options** | `PASS` · `PASS_WITH_SUGGESTIONS` · `NEEDS_WORK` · `FAIL` |

---

## Review Objective

Ensure test suites validate observable behavior through public interfaces, survive refactoring without breaking, and catch real bugs while avoiding false positives from implementation coupling.

### This Review Answers

1. Do tests follow AAA structure with visual separation?
2. Are tests verifying behavior through public interfaces only?
3. Are mocks restricted to external boundaries (HTTP, DB, queues, filesystem)?
4. Are factories used for test data instead of hardcoded model construction?

### Out of Scope

- Integration test infrastructure and fixtures
- Test execution performance optimization
- CI/CD pipeline configuration

---

## Core Workflow

```
┌─────────────────────────────────────────────────────────────┐
│                    REVIEW WORKFLOW                          │
├─────────────────────────────────────────────────────────────┤
│  1. SCOPE    →  Identify test files to review               │
│  2. CONTEXT  →  Load testing standards & patterns           │
│  3. ANALYZE  →  Apply evaluation criteria systematically    │
│  4. CLASSIFY →  Assign severity to each finding             │
│  5. VERDICT  →  Determine pass/fail based on findings       │
│  6. REPORT   →  Output structured review results            │
│  7. CHAIN    →  Invoke test/unit skill if rewrites needed   │
└─────────────────────────────────────────────────────────────┘
```

### Step 1: Scope Definition

```bash
# Test files
**/test_*.py
**/*_test.py
# Support files
**/conftest.py
**/factories/**/*.py
```

### Step 2: Context Loading

Before analysis, internalize:







- **Principles:** `rules/principles.md` → §2.14 Test Behavior, §2.9 Testability
- **Standards:** `rules/testing.md` → AAA, naming, isolation
- **Mocking:** `rules/mocking.md` → Boundary-only mocking
- **Factories:** `rules/test-factories.md` → Polyfactory, Faker patterns

### Step 3: Systematic Analysis

| Priority | Criterion Category | Weight |
|----------|-------------------|--------|
| P0 | Implementation Coupling | Blocker |
| P1 | Mock Misuse | Critical |
| P2 | Structure Violations | Major |
| P3 | Factory & Data Issues | Minor |

### Step 4: Severity Classification

| Severity | Definition | Action Required |
|----------|------------|-----------------|
| **🔴 BLOCKER** | Tests private methods or breaks on refactor | Must fix before merge |
| **🟠 CRITICAL** | Over-mocking or mocking internal code | Must fix, may defer |
| **🟡 MAJOR** | Missing AAA structure, weak assertions | Should fix |
| **🔵 MINOR** | Hardcoded data, naming issues | Consider fixing |
| **⚪ SUGGESTION** | Style improvements, additional coverage | Optional |
| **🟢 COMMENDATION** | Excellent behavior-focused testing | Positive reinforcement |

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

### Structure & Organization (SO)

| ID | Criterion | Severity | Check |
|----|-----------|----------|-------|
| SO.1 | AAA structure with blank line separation | MAJOR | Arrange → blank → Act → blank → Assert |
| SO.2 | Test naming: `test_<action>_<outcome>` | MINOR | Name reveals behavior being tested |
| SO.3 | One logical concept per test | MAJOR | No multiple unrelated assertions |
| SO.4 | Test isolation (no shared mutable state) | BLOCKER | No class attrs or module globals |
| SO.5 | No test interdependencies | BLOCKER | Each test passes in isolation |

### Behavior Focus (BF)

| ID | Criterion | Severity | Check |
|----|-----------|----------|-------|
| BF.1 | Tests public interface only | BLOCKER | No `_method` or `__attr` testing |
| BF.2 | Asserts behavioral outcomes | MAJOR | State changes, return values, exceptions |
| BF.3 | Survives implementation refactor | BLOCKER | Would test break if internals change? |
| BF.4 | No implementation detail assertions | CRITICAL | No internal state or call count checks |

### Mock Usage (MU)

| ID | Criterion | Severity | Check |
|----|-----------|----------|-------|
| MU.1 | Mocks only external boundaries | CRITICAL | HTTP, DB, queues, filesystem, time |
| MU.2 | No mocking of code under test | BLOCKER | Never mock same module/package |
| MU.3 | Mock path is usage site, not definition | MAJOR | `mocker.patch("app.module.dep")` |
| MU.4 | Realistic return values matching contracts | MAJOR | Return types match actual API |
| MU.5 | Max 2 mocks per test | CRITICAL | >2 indicates too many dependencies |

### Test Data (TD)

| ID | Criterion | Severity | Check |
|----|-----------|----------|-------|
| TD.1 | Factories for model instantiation | MAJOR | No hardcoded `Model(field="value")` |
| TD.2 | Faker for realistic primitives | MINOR | Emails, names, addresses use Faker |
| TD.3 | Override only relevant attributes | MINOR | Don't set fields unrelated to assertion |
| TD.4 | `.build()` for memory, `.create()` for persistence | MINOR | Correct factory method usage |

### Assertions (AS)

| ID | Criterion | Severity | Check |
|----|-----------|----------|-------|
| AS.1 | Specific assertions, no `assert result` | MAJOR | Assert exact expected values |
| AS.2 | Exception tests use `match=` parameter | MAJOR | `pytest.raises(Error, match="...")` |
| AS.3 | Coverage: happy + edge + error + state | MAJOR | All four categories present |
| AS.4 | Timestamps use `<=` against current time | MINOR | `assert ts <= datetime.now(UTC)` |

---

## Patterns & Anti-Patterns

### ✅ Correct: Behavior-Focused Test

```python
def test_applies_percentage_discount(order_factory):
    # Arrange
    order = order_factory.build(subtotal=Decimal("100.00"))

    # Act
    order.apply_discount(percent=10)

    # Assert
    assert order.total == Decimal("90.00")
```

**Why this works:** Tests observable behavior (total changes), uses factory, AAA structure, survives internal refactor.

### ❌ Red Flag: Testing Private Methods

```python
def test_internal_calculation(order):
    assert order._calculate_factor(10) == 0.9
```

**Why this fails:** Couples to implementation. Breaks when `_calculate_factor` is renamed/removed even if behavior unchanged.

### ❌ Red Flag: Over-Mocking

```python
def test_total(mocker):
    mocker.patch.object(Order, "get_items", return_value=[...])
    mocker.patch.object(Order, "get_tax", return_value=0.1)
    mocker.patch.object(Order, "get_discount", return_value=5)
```

**Why this fails:** Tests mocks, not code. No real logic executes.

### ❌ Red Flag: Test Interdependency

```python
class TestFlow:
    order_id = None
    def test_create(self): TestFlow.order_id = create()
    def test_complete(self): complete(TestFlow.order_id)
```

**Why this fails:** `test_complete` fails when run in isolation.



---



## Output Formats




### Finding Format


```markdown

### [🔴 BLOCKER] {{TITLE}}
**Location:** `path/file.py:42` | **Criterion:** BF.1 - Tests public interface only

**Issue:** {{description}}
**Evidence:** \`\`\`python ... \`\`\`

**Suggestion:** {{fix}} | **Rationale:** {{why}}
```


### Summary Format

```markdown
# Unit Tests Review Summary
## Verdict: {{EMOJI}} {{VERDICT}}
| Metric | Blockers | Critical | Major | Minor |
|--------|----------|----------|-------|-------|
| Count  | {{N}}    | {{N}}    | {{N}} | {{N}} |

## Key Findings: {{TOP_3}}
## Actions: {{REQUIRED_FIXES}}
## Chain Decision: {{EXPLANATION}}
```

---

## Skill Chaining

| Verdict | Chain Action | Target Skill |
|---------|--------------|--------------|
| `FAIL` | Mandatory rewrite | `test/unit` |
| `NEEDS_WORK` | Targeted fixes | `test/unit` |
| `PASS_WITH_SUGGESTIONS` | Optional | None |
| `PASS` | Continue pipeline | `review/integration-tests` or complete |

### Handoff Protocol

```markdown
**Chain Target:** `test/unit`
**Priority Findings:** {{BLOCKER_AND_CRITICAL_IDS}}
**Constraint:** Preserve test coverage while fixing structure
```

---

## Quality Gates

Before finalizing review:

- [ ] All test files in scope analyzed
- [ ] Each finding has location + criterion + severity
- [ ] Verdict aligns with severity distribution
- [ ] Actionable suggestions for non-PASS verdicts
- [ ] Chain decision explicit and justified
