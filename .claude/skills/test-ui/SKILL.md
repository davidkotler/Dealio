---
name: test-ui
version: 1.0.0
description: |
  Generate reliable Playwright UI tests that validate user behavior through semantic locators and web-first assertions.
  Use when writing E2E tests, UI tests, browser automation, Playwright tests, or testing user journeys.
  Relevant for critical user flows, authentication, checkout, form validation, SPA testing.
---

# UI Testing (Playwright)

> Generate stable, maintainable UI tests that validate user behavior, not implementation details.

## Quick Reference

| Aspect | Details |
|--------|---------|
| **Invokes** | `implement/python`, `implement/pydantic` |
| **Invoked By** | `implement/api`, `implement/react`, `review/tests` |
| **Key Tools** | Write, Edit, Bash(pytest), Bash(playwright) |
| **Framework** | Playwright + pytest-playwright |

---

## Core Workflow

1. **Identify**: Determine if this is a critical user journey worth UI testing
2. **Structure**: Create Page Object if testing multiple scenarios on same page
3. **Locate**: Use semantic locators following the priority hierarchy
4. **Assert**: Use web-first assertions that auto-retry
5. **Isolate**: Ensure test data isolation via fixtures
6. **Validate**: Run test, check for flakiness indicators

---

## Decision Tree

```
New UI Test Request
    │
    ├─► Critical user journey? (auth, checkout, core feature)
    │       └─► YES → Write UI test
    │       └─► NO  → Consider API-based E2E or integration test
    │
    ├─► Multiple tests on same page?
    │       └─► YES → Create Page Object Model first
    │       └─► NO  → Inline locators acceptable
    │
    └─► External dependencies involved?
            └─► YES → Mock via page.route() before navigation
            └─► NO  → Test against real endpoints
```

---

## Skill Chaining

| Condition | Invoke | Handoff Context |
|-----------|--------|-----------------|
| Need test fixtures/factories | `test/unit` | Model schemas, factory patterns |
| Testing API responses | `implement/api` | Endpoint contracts for mocking |
| Page Object needs types | `implement/pydantic` | Request/response models |

---

## Locator Priority Hierarchy

Use locators in this order (most to least stable):

| Priority | Method | When to Use |
|----------|--------|-------------|
| 1 | `get_by_role()` | Buttons, links, headings, form controls |
| 2 | `get_by_label()` | Form inputs with labels |
| 3 | `get_by_placeholder()` | Inputs with placeholder text |
| 4 | `get_by_text()` | Visible text content |
| 5 | `get_by_test_id()` | Stable contract when semantics unavailable |
| 6 | `locator("[attr]")` | Last resort for complex cases |

---

## MUST Rules

1. **MUST** use web-first assertions (`expect().to_be_visible()`) that auto-retry
2. **MUST** use semantic locators (`get_by_role`, `get_by_label`) before test IDs
3. **MUST** isolate test data—each test creates and cleans its own state
4. **MUST** set up route mocks (`page.route()`) before `page.goto()`
5. **MUST** verify authentication succeeded before saving storage state
6. **MUST** use explicit condition-based waits for async operations
7. **MUST** use `async def` for all test functions and fixtures
8. **MUST** name tests descriptively: `test_user_can_<action>_with_<condition>`

---

## NEVER Rules

1. **NEVER** use `time.sleep()` or `page.wait_for_timeout()` for fixed delays
2. **NEVER** use CSS class selectors tied to styling (`.btn-primary`, `.card--active`)
3. **NEVER** use XPath or complex structural selectors (`//div[3]/form/button`)
4. **NEVER** share mutable state between tests
5. **NEVER** test third-party services directly—mock them
6. **NEVER** spawn new browser instances per test—use contexts
7. **NEVER** assert on implementation details (Redux state, internal variables)
8. **NEVER** use immediate assertions (`assert element.is_visible()`)—use `expect()`

---

## Conditional Rules (WHEN → THEN)

### WHEN elements load asynchronously

**THEN** use web-first assertions or `expect_response()`:
```python
with page.expect_response("**/api/data") as response:
    page.get_by_role("button", name="Load").click()
expect(page.get_by_text("Loaded")).to_be_visible()
```

### WHEN testing authentication flows

**THEN** save `storageState` in setup, reuse across tests:
```python
@pytest.fixture(scope="session")
def auth_state(browser):
    context = browser.new_context()
    page = context.new_page()

    context.storage_state(path="auth.json")

    context.close()
```

### WHEN testing forms with validation

**THEN** test both valid and invalid states via parametrization:
```python
@pytest.mark.parametrize("email,expected", [
    ("valid@test.com", "Success"),

    ("invalid", "Invalid email"),
])
def test_email_validation(page, email, expected):

    page.get_by_label("Email").fill(email)
    page.get_by_role("button", name="Submit").click()
    expect(page.get_by_text(expected)).to_be_visible()

```

### WHEN multiple tests share page structure


**THEN** extract Page Object Model:
```python
class LoginPage:

    def __init__(self, page: Page):

        self.page = page
        self.email = page.get_by_label("Email")
        self.password = page.get_by_label("Password")

        self.submit = page.get_by_role("button", name="Sign in")

```

### WHEN testing file uploads


**THEN** use `set_input_files()` on the input element:

page.get_by_label("Upload").set_input_files("fixtures/test.pdf")
```


### WHEN testing new tabs or popups

**THEN** use `expect_page()` context manager:
```python
with page.expect_page() as popup_info:


    page.get_by_role("link", name="Open").click()
popup = popup_info.value
```

### WHEN external APIs are involved


**THEN** mock before navigation:
```python
page.route("**/api/users/*", lambda route: route.fulfill(
    json={"id": 1, "name": "Test User"}
))
page.goto("/profile")


```


## Patterns

### ✅ User-Behavior Focused Test


```python
async def test_user_can_complete_checkout(page: Page):
    """Tests complete checkout journey."""
    await page.get_by_role("button", name="Add to Cart").click()

    await expect(page.get_by_test_id("cart-count")).to_have_text("1")
    await page.get_by_role("link", name="Checkout").click()
    await page.get_by_label("Email").fill("test@example.com")


    async with page.expect_response("**/api/orders") as response:
        await page.get_by_role("button", name="Place Order").click()

    assert response.value.ok

    await expect(page.get_by_role("heading", name="Order Confirmed")).to_be_visible()
```

### ✅ Page Object Model

```python
class CheckoutPage:
    def __init__(self, page: Page):
        self.page = page

        self.email_field = page.get_by_label("Email")
        self.submit_btn = page.get_by_role("button", name="Place Order")

    async def fill_and_submit(self, email: str):
        await self.email_field.fill(email)
        await self.submit_btn.click()
```

### ✅ Isolated Test Data Fixture

```python
@pytest.fixture
async def test_user(api_client):
    user = await api_client.post("/api/test/users", json={"email": f"test-{uuid4()}@example.com"})
    yield user
    await api_client.delete(f"/api/test/users/{user['id']}")
```

---

## Anti-Patterns

```python
# ❌ Fixed Sleep — flaky and slow
await page.wait_for_timeout(3000)

# ❌ Implementation Testing — tests internal state, not user behavior
state = await page.evaluate("window.__REDUX_STATE__.cart.items")


# ❌ Structural Selectors — breaks when DOM changes
await page.click("div.container > form > div:nth-child(3) > button")

# ❌ Immediate Assertion — doesn't wait, fails on async rendering
assert await page.locator(".success").is_visible() == True
```

---

## Quality Gates

Before completing UI test generation:


- [ ] Semantic locators used (role/label/text) where possible
- [ ] No `time.sleep()` or `wait_for_timeout()`
- [ ] Each test is independent and isolated
- [ ] Tests named descriptively (`test_user_can_...`)
- [ ] Web-first assertions used (`expect().to_be_...`)
- [ ] External dependencies mocked via `page.route()`
- [ ] Test covers user behavior, not implementation

—
