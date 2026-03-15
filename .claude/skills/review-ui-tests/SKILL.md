---
name: review-ui-tests
version: 1.0.0

description: |
  Review Playwright UI tests for stability, maintainability, and behavioral focus.
  Evaluates locator strategies, assertion patterns, test isolation, and async handling.
  Use when reviewing UI tests, validating Playwright test quality, or assessing E2E test
  implementations after test/ui skill execution.
  Relevant for Playwright tests, browser automation, E2E testing, pytest-playwright.

chains:
  invoked-by:
    - skill: test/ui
      context: "Post-implementation quality gate"
    - skill: implement/python
      context: "When UI test files are modified"
  invokes:
    - skill: test/ui
      when: "Critical or major findings require test rewrite"
    - skill: implement/pydantic
      when: "Page Object Models need type improvements"
---

# UI Tests Review

> Validate that UI tests are stable, maintainable, and test user behavior—not implementation details.

## Quick Reference

| Aspect | Details |
|--------|---------|
| **Dimension** | UI Test Quality |
| **Scope** | `**/tests/**/test_*.py`, `**/e2e/**/*.py`, Page Objects |
| **Invoked By** | `test/ui`, `implement/python`, `/review` command |
| **Invokes** | `test/ui` (on failure) |
| **Verdict Options** | `PASS` · `PASS_WITH_SUGGESTIONS` · `NEEDS_WORK` · `FAIL` |

---

## Review Objective

Ensure UI tests validate user-facing behavior through stable locators and resilient assertions that survive refactoring without false failures.

### This Review Answers

1. Do tests use semantic locators that won't break on styling/DOM changes?
2. Are assertions web-first with auto-retry, not immediate checks?
3. Is each test isolated with independent data and state?
4. Do tests verify user behavior rather than implementation details?

### Out of Scope

- Business logic correctness (see `review/functionality`)
- API contract validation (see `review/contract-tests`)

---

## Core Workflow

```
┌─────────────────────────────────────────────────────────────┐
│                    REVIEW WORKFLOW                          │
├─────────────────────────────────────────────────────────────┤
│  1. SCOPE    →  Glob for test_*.py in tests/e2e/ui paths    │
│  2. CONTEXT  →  Load test/ui SKILL rules as baseline        │
│  3. ANALYZE  →  Check locators → assertions → isolation     │
│  4. CLASSIFY →  Assign severity per finding                 │
│  5. VERDICT  →  Determine pass/fail from severity counts    │
│  6. REPORT   →  Output structured findings                  │
│  7. CHAIN    →  Invoke test/ui if rewrite needed            │
└─────────────────────────────────────────────────────────────┘
```

### Step 1: Scope Definition

```bash
# Primary targets
**/tests/**/test_*.py
**/e2e/**/*.py
**/pages/**/*.py  # Page Object Models
```

### Step 2: Context Loading

Before analysis, internalize:







- **Implementation Skill:** `skills/test/ui/SKILL.md` → Locator hierarchy, MUST/NEVER rules
- **Principles:** `rules/principles.md` → §2.14 Test Behavior, §2.9 Testability
- **Testing Rules:** `rules/testing.md` → Pyramid, isolation requirements

### Step 3: Systematic Analysis

Evaluate each file against criteria in severity order:

| Priority | Category | Weight |
|----------|----------|--------|
| P0 | Fixed Waits & Flakiness | Blocker |
| P1 | Locator Stability | Critical |
| P2 | Assertion Patterns | Critical |
| P3 | Test Isolation | Major |
| P4 | Behavior Focus | Major |
| P5 | Naming & Structure | Minor |

### Step 4: Severity Classification

| Severity | Definition | Action |
|----------|------------|--------|
| **🔴 BLOCKER** | Test will be flaky or fail intermittently | Must fix before merge |
| **🟠 CRITICAL** | Test will break on legitimate refactors | Must fix, may defer |
| **🟡 MAJOR** | Test quality/maintainability compromised | Should fix |
| **🔵 MINOR** | Suboptimal but functional | Consider fixing |
| **⚪ SUGGESTION** | Enhancement opportunity | Optional |
| **🟢 COMMENDATION** | Exemplary pattern usage | Positive reinforcement |

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

### Flakiness Prevention (FP)

| ID | Criterion | Severity | Detection Pattern |
|----|-----------|----------|-------------------|
| FP.1 | No `time.sleep()` or `wait_for_timeout()` | 🔴 BLOCKER | `grep -E "time\.sleep\|wait_for_timeout"` |
| FP.2 | No sequential waits for async rendering | 🔴 BLOCKER | Multiple waits without condition |
| FP.3 | Route mocks set before `page.goto()` | 🟠 CRITICAL | `page.route()` after navigation |

### Locator Stability (LS)

| ID | Criterion | Severity | Detection Pattern |
|----|-----------|----------|-------------------|
| LS.1 | Semantic locators prioritized (`get_by_role`, `get_by_label`) | 🟠 CRITICAL | Direct CSS/XPath without semantic alternative |
| LS.2 | No CSS class selectors tied to styling | 🟠 CRITICAL | `.btn-primary`, `.card--active`, `.is-selected` |
| LS.3 | No XPath or structural selectors | 🟠 CRITICAL | `//div[3]/form/button`, `nth-child` |
| LS.4 | `get_by_test_id()` only when semantics unavailable | 🔵 MINOR | Overuse of test IDs |

### Assertion Quality (AQ)

| ID | Criterion | Severity | Detection Pattern |
|----|-----------|----------|-------------------|
| AQ.1 | Web-first assertions used (`expect().to_be_visible()`) | 🟠 CRITICAL | `assert element.is_visible()` |
| AQ.2 | No immediate assertion patterns | 🟠 CRITICAL | `assert await locator.is_visible() == True` |
| AQ.3 | `expect_response()` for async data loads | 🟡 MAJOR | Click without response wait |
| AQ.4 | Assertions verify user-visible outcomes | 🟡 MAJOR | Asserting internal state |

### Test Isolation (TI)

| ID | Criterion | Severity | Detection Pattern |
|----|-----------|----------|-------------------|
| TI.1 | Each test creates/cleans own data | 🟡 MAJOR | Shared fixtures without cleanup |
| TI.2 | No shared mutable state between tests | 🟡 MAJOR | Module-level variables modified |
| TI.3 | Browser contexts used, not new instances | 🟡 MAJOR | `browser.launch()` per test |
| TI.4 | Auth state properly isolated/shared | 🔵 MINOR | Inconsistent storage state handling |

### Behavior Focus (BF)

| ID | Criterion | Severity | Detection Pattern |
|----|-----------|----------|-------------------|
| BF.1 | Tests verify user journeys, not DOM structure | 🟡 MAJOR | Assertions on element counts/structure |
| BF.2 | No Redux/internal state assertions | 🟡 MAJOR | `page.evaluate("window.__REDUX_STATE__")` |
| BF.3 | Third-party services mocked | 🟡 MAJOR | Direct external API calls |
| BF.4 | Tests survive implementation refactors | 🔵 MINOR | Tight coupling to current DOM |

### Structure & Naming (SN)

| ID | Criterion | Severity | Detection Pattern |
|----|-----------|----------|-------------------|
| SN.1 | Descriptive names: `test_user_can_<action>` | 🔵 MINOR | `test_1`, `test_login`, `test_click` |
| SN.2 | `async def` for all test functions | 🔵 MINOR | Sync test functions |
| SN.3 | Page Objects for repeated page interactions | ⚪ SUGGESTION | Inline locators across 3+ tests |
| SN.4 | Parametrization for validation variants | ⚪ SUGGESTION | Duplicate tests for valid/invalid |

---

## Patterns & Anti-Patterns

### ✅ Indicators of Quality

```python
async def test_user_can_complete_checkout(page: Page, test_product):
    """Validates complete purchase journey."""
    await page.get_by_role("button", name="Add to Cart").click()
    await expect(page.get_by_test_id("cart-count")).to_have_text("1")

    await page.get_by_role("link", name="Checkout").click()
    await page.get_by_label("Email").fill("test@example.com")

    async with page.expect_response("**/api/orders") as response:
        await page.get_by_role("button", name="Place Order").click()

    assert response.value.ok
    await expect(page.get_by_role("heading", name="Order Confirmed")).to_be_visible()
```

**Why this works:** Semantic locators, web-first assertions, response waiting, behavior-focused, descriptive name.

### ❌ Red Flags

```python
def test_checkout(page):
    page.click("div.product-card > button.btn-primary")
    time.sleep(2)
    assert page.locator(".cart-badge").inner_text() == "1"

    page.click("a[href='/checkout']")
    page.fill("#email-input", "test@example.com")
    page.click("form > div:nth-child(3) > button")

    time.sleep(3)
    state = page.evaluate("window.__REDUX_STATE__.order.status")
    assert state == "completed"
```

**Why this fails:** CSS class selectors (LS.2), fixed sleeps (FP.1), immediate assertions (AQ.1), structural selectors (LS.3), implementation testing (BF.2), non-descriptive name (SN.1), sync function (SN.2).

---

## Output Formats

### Finding Format

Each finding includes: **Location** (file:line) → **Criterion** (ID) → **Issue** → **Evidence** (code) → **Suggestion** → **Rationale**

### Summary Format

Output includes: **Verdict** with emoji → **Metrics table** (counts per severity) → **Top 3 findings** → **Recommended actions** → **Chain decision**

---

## Skill Chaining

### Chain Triggers

| Verdict | Action | Target |
|---------|--------|--------|
| `FAIL` | Mandatory rewrite | `test/ui` |
| `NEEDS_WORK` | Targeted fixes | `test/ui` |
| `PASS_WITH_SUGGESTIONS` | Optional | None |
| `PASS` | Continue | Next review phase |

### Handoff Protocol

When chaining to `test/ui`: Provide **Chain Target** → **Priority Findings** (BLOCKER/CRITICAL IDs) → **Context** (issue count) → **Constraint** (preserve coverage)

---

## Integration Points

### Upstream

| Source | Trigger | Context |
|--------|---------|---------|
| `test/ui` | Post-implementation | New/modified test files |
| `/review` command | Explicit | User-specified scope |
| `implement/python` | Python file edit | When path matches test patterns |

### Downstream

| Target | Condition | Handoff |
|--------|-----------|---------|
| `test/ui` | Verdict ≠ PASS | Findings + priority |
| `review/e2e-tests` | Composite review | Current verdict |

---

## Quality Gates

Before finalizing review output:

- [ ] All test files in scope were analyzed
- [ ] Each finding has location + criterion + severity
- [ ] Verdict aligns with severity distribution
- [ ] Actionable suggestions provided for non-PASS verdicts
- [ ] Locator hierarchy violations explicitly flagged
- [ ] Fixed wait patterns identified with alternatives
- [ ] Chain decision is explicit and justified
