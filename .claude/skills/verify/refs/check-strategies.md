# Check Strategies

> Detailed guidance on how to execute each type of verification check — choosing between
> inline execution, script generation, and Playwright automation.

---

## Strategy Selection

Not every check should be executed the same way. The right strategy depends on what you're
checking and what tools are available.

### Decision Matrix

| Check Type | Preferred Strategy | Fallback |
|-----------|-------------------|----------|
| Bash command (from "How to Verify") | Run directly via Bash | Script if multi-step |
| curl/httpie API call | Run directly via Bash | Script if response needs parsing |
| File existence (from DoD) | Glob check | Read to verify non-trivial content |
| Code symbol existence (from sub-tasks) | Grep or read file | Script if checking structure |
| Data model match (against LLD) | Read + compare | Script for field-by-field validation |
| API contract match (against OpenAPI) | Read route + compare to spec | Script for schema comparison |
| Database state (invariants, side effects) | SQL via Bash | Script if complex queries |
| UI walkthrough | Playwright MCP tools | Playwright script if multi-step journey |
| Event flow | Check handler + DLQ | Script for publish-then-check |
| Boundary value | Construct + execute request | Script for batch boundary testing |

---

## Executing UI Checks via Playwright

UI and visual checks are fully automated using Playwright — either through the Playwright MCP
tools (for interactive step-by-step checks) or by writing Playwright scripts (for complex
multi-step journeys that need to be re-runnable).

> **These are verification artifacts, not codebase tests.** Scripts live in `verifications/`,
> not `tests/`. They validate task completion for QA purposes and may be discarded after the
> task is verified. However, they follow the same Playwright best practices as `/test-ui` to
> ensure reliable, non-flaky execution.

### Playwright Best Practices (from `/test-ui` and `/review-ui-tests`)

These rules apply to all Playwright usage in verification — MCP tools and scripts alike:

**Locator priority hierarchy** (most to least stable):

1. `get_by_role()` — buttons, links, headings, form controls
2. `get_by_label()` — form inputs with labels
3. `get_by_placeholder()` — inputs with placeholder text
4. `get_by_text()` — visible text content
5. `get_by_test_id()` — only when semantics are unavailable
6. `locator("[attr]")` — last resort

**Assertion rules:**

- Use web-first assertions: `expect(locator).to_be_visible()` — auto-retries until timeout
- Never `assert element.is_visible()` — immediate, doesn't retry, flaky
- Use `page.expect_response()` when a click triggers an API call — wait for the response before asserting the outcome

**Flakiness prevention:**

- Never `time.sleep()` or `page.wait_for_timeout()` — use condition-based waits
- Never CSS class selectors tied to styling (`.btn-primary`, `.card--active`)
- Never XPath or complex structural selectors (`//div[3]/form/button`)
- Set up `page.route()` mocks before `page.goto()`, not after

**Script vs test differences:**

| Aspect | Verification scripts (`verifications/`) | Codebase tests (`tests/`) |
|--------|----------------------------------------|--------------------------|
| API | `playwright.sync_api` (standalone) | `pytest-playwright` (async fixtures) |
| Lifecycle | Ephemeral — may be discarded after task verified | Permanent — part of regression suite |
| Isolation | Not required — single-run, no parallel concerns | Required — each test creates/cleans own data |
| Page Objects | Not needed — inline locators are fine | Use for 3+ tests on same page |
| Output | Print PASS/FAIL to stdout | pytest assertions + markers |

### Playwright MCP Tools (preferred for simple checks)

Use the Playwright MCP tools when the check involves a few steps on a single page or a
simple navigation flow. The MCP tools use the accessibility tree via `browser_snapshot`,
which naturally aligns with semantic locator best practices:

| Tool | When to use |
|------|------------|
| `browser_navigate` | Load the page under test |
| `browser_snapshot` | Capture the accessibility tree — verify element presence by role/name/text |
| `browser_click` | Click buttons, links, menu items (use ref from snapshot) |
| `browser_fill_form` | Fill form fields with test data |
| `browser_press_key` | Submit forms (Enter), trigger keyboard shortcuts |
| `browser_take_screenshot` | Capture visual evidence for the report |
| `browser_wait_for` | Wait for async UI updates (navigation, network idle) |
| `browser_console_messages` | Check for JavaScript errors |
| `browser_network_requests` | Verify API calls were made correctly |

**Verification flow pattern:**

1. Navigate to the target URL
2. Snapshot to verify initial state — check elements by role and name in the accessibility tree
3. Interact (click using refs from snapshot, fill forms by label)
4. Wait for response if async (use `browser_wait_for` for navigation or network idle)
5. Snapshot again to verify final state
6. Compare against the expected behavior from the task breakdown
7. Record PASS/FAIL with the snapshot as evidence

### Playwright Scripts (for complex or re-runnable checks)

Write a Playwright script when:
- The check involves 5+ steps
- Multiple pages or navigation flows are tested
- The check needs to be re-run after fixes
- Conditional logic is needed (if element X exists, do Y)

Save scripts to `{feature-dir}/verifications/{task-name}/verify_ui_{check_name}.py`.

Use `playwright.sync_api` (not async — these are standalone scripts, not pytest tests).
Follow the locator hierarchy and assertion rules above.

**Script template:**

```python
# {feature-dir}/verifications/{task-name}/verify_ui_{check_name}.py
"""Playwright UI verification: {check description}. Auto-generated by /verify."""
from playwright.sync_api import sync_playwright, expect

def verify():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()

        page.goto("http://localhost:3000/products")

        # Semantic locators (get_by_role, get_by_label — never CSS classes)
        expect(page.get_by_role("button", name="Create")).to_be_visible()
        page.get_by_role("button", name="Create").click()
        page.get_by_label("Name").fill("Widget")
        page.get_by_label("Price").fill("9.99")

        # Wait for API response before asserting (no time.sleep!)
        with page.expect_response("**/api/v1/products") as resp:
            page.get_by_role("button", name="Submit").click()
        assert resp.value.ok

        # Web-first assertions (auto-retry, not immediate)
        expect(page.get_by_text("Widget")).to_be_visible()
        expect(page.get_by_role("heading", name="Products")).to_be_visible()

        browser.close()
        print("[PASS] Product creation UI flow")

if __name__ == "__main__":
    verify()
```

### What to Verify in UI Checks

Map each "How to Verify" step that mentions UI interaction to a Playwright check:

| Task breakdown says | Playwright does |
|---------------------|----------------|
| "Open /products → confirm list shows" | Navigate + snapshot, assert table/list visible by role |
| "Click Create → fill form → submit" | Click by role + fill by label + expect_response + click submit |
| "Confirm success toast shown" | `expect(get_by_text("...")).to_be_visible()` (auto-retries) |
| "Confirm redirect to product list" | `browser_wait_for` navigation + snapshot list page |
| "Submit with empty name → see error" | Fill empty + submit + `expect(get_by_text("error")).to_be_visible()` |
| "Confirm new product appears in list" | Snapshot list, assert new item text by `get_by_text` |

---

## Executing API Checks

When the task breakdown specifies API behaviors, test them systematically:

### Happy Path

```bash
# Construct the request exactly as specified in Expected Behaviors
curl -s -w "\n%{http_code}" -X POST http://localhost:8000/v1/products \
  -H "Content-Type: application/json" \
  -d '{"name": "Widget", "price": 9.99}'
```

Capture both the response body and status code. Compare against the expected output
from the breakdown. Key checks:
- Status code matches (201, 200, etc.)
- Response body contains expected fields
- Response field types are correct (string, number, UUID format, ISO8601 date)
- No unexpected fields present

### Error Path

```bash
# Send the invalid input specified in Expected Behaviors
curl -s -w "\n%{http_code}" -X POST http://localhost:8000/v1/products \
  -H "Content-Type: application/json" \
  -d '{"name": ""}'
```

Check:
- Status code is the expected error code (422, 400, 404, etc.)
- Error response body names the correct field or constraint
- Error format matches the project's error envelope (from lib-fastapi's ApiError)

### State Side Effects

After a mutation, verify the side effect:

```bash
# Check database directly
psql -c "SELECT id, name, price FROM products ORDER BY created_at DESC LIMIT 1;"

# Or check via a GET endpoint
curl -s http://localhost:8000/v1/products/{id}
```

---

## Executing Boundary Checks

Boundary conditions often come in pairs — the value just inside the boundary (should accept)
and just outside (should reject). Test both:

### Script Pattern for Batch Boundary Testing

When multiple boundary conditions exist, a script is more efficient than individual commands:

```python
"""Verify boundary conditions for {task name}."""
import httpx
import sys

BASE = "http://localhost:8000/v1"
results = []

def check(name: str, method: str, url: str, payload: dict, expected_status: int):
    resp = getattr(httpx, method)(url, json=payload)
    passed = resp.status_code == expected_status
    results.append({
        "name": name,
        "passed": passed,
        "expected": expected_status,
        "actual": resp.status_code,
        "body": resp.text[:200],
    })
    mark = "PASS" if passed else "FAIL"
    print(f"[{mark}] {name}: expected {expected_status}, got {resp.status_code}")

# Boundary: name at max length (255 chars)
check("name_max_length", "post", f"{BASE}/products",
      {"name": "A" * 255, "price": 9.99}, 201)

# Boundary: name exceeds max length
check("name_over_max", "post", f"{BASE}/products",
      {"name": "A" * 256, "price": 9.99}, 422)

# Boundary: price minimum (0.01)
check("price_minimum", "post", f"{BASE}/products",
      {"name": "Widget", "price": 0.01}, 201)

# Boundary: price zero (rejected)
check("price_zero", "post", f"{BASE}/products",
      {"name": "Widget", "price": 0}, 422)

# Summary
passed = sum(1 for r in results if r["passed"])
total = len(results)
print(f"\n{passed}/{total} boundary checks passed")
sys.exit(0 if passed == total else 1)
```

---

## Verifying Invariants

Invariants are postconditions that must hold after all the verification steps have run.
Check them last, since the verification steps themselves may have created state.

### Database Invariants

```bash
# "Every product has non-null id, name, price, created_at"
psql -c "SELECT COUNT(*) FROM products WHERE id IS NULL OR name IS NULL OR price IS NULL OR created_at IS NULL;"
# Expected: 0

# "Products table row count never decreases (soft-delete only)"
psql -c "SELECT COUNT(*) FROM products;"
# Compare against count before verification started
```

### Code Invariants

Some invariants are about code structure rather than runtime state:

```bash
# "Every successful mutation publishes exactly one domain event"
# Check by reading the flow code and confirming publish call exists
grep -l "publish" services/products/products/domains/product/flows/*.py
```

### Contract Invariants

```bash
# "Response id always matches persisted entity id"
# This was already verified during the happy-path API check — reference that evidence
```

---

## Verifying Definition of Done

### Files Check

Use Glob to verify each file listed in the DoD exists:

```
Expected: services/products/products/domains/product/flows/create_product.py
Check:    Glob("services/products/products/domains/product/flows/create_product.py")
Verdict:  PASS if file found, FAIL if not
```

For important files, also Read the first few lines to confirm they're not empty stubs.

### Contract Compliance Check

Compare implemented endpoints/models against the specifications in lld.md:

1. Read the OpenAPI spec section from lld.md for the relevant endpoint
2. Read the actual route handler code
3. Compare: path, method, request body schema, response schema, status codes
4. Note any differences as PASS (matches) or FAIL (diverges)

### Acceptance Criteria Check

Map each acceptance criterion from the DoD back to a verification check that was already
executed. If an acceptance criterion maps to a check that passed, it's met. If no check
covers it, note it as a gap.

---

## When Services Aren't Running

If the service needs to be running for API checks but isn't, try to start it:

```bash
# Check if the service is running
curl -s http://localhost:8000/health 2>/dev/null

# If not, try starting it (common patterns)
cd services/{service-name} && uv run uvicorn {service}.main:app --port 8000 &
sleep 3  # Wait for startup
```

If the service can't be started (missing dependencies, database not available, etc.):
1. Mark all API checks as SKIPPED with reason "Service not running"
2. Fall back to code-level verification (check that the route handler exists, models are correct, etc.)
3. Note in the report that runtime verification was not possible

---

## Re-running Verification

After fixes, the user may want to re-run verification. The skill supports this naturally:
- Previous verification reports are preserved (appended with a timestamp or versioned)
- Verification scripts in the `verifications/` directory can be re-run directly
- The same task can be selected again from the task list

When re-running, mention the previous verification result:

```markdown
## Previous Verification

Last verified: {date} — Verdict: FAIL ({N} checks failed)
Failed checks: V-3 (empty name → 500), BC-2 (price 0 → accepted)

Re-running all checks...
```
