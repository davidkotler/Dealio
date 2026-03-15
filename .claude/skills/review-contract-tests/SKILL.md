---
name: review-contract-tests
version: 1.1.0

description: |
  Review contract tests for API boundary validation quality, pattern compliance, and behavioral focus.
  Use when reviewing Pact consumer contracts, Schemathesis schema tests, JSON schema validations,
  or any API contract test implementation. Validates that contracts test boundaries (not internals),
  use flexible matchers, cover error responses, and follow testing pyramid principles.
  Relevant for Python contract tests, API testing, microservices, REST/async API validation.

chains:
  invoked-by:
    - skill: test/contract
      context: "Post-implementation quality gate for contract tests"
    - skill: implement/api
      context: "After API implementation, validate contract coverage"
    - skill: review/api
      context: "API review triggers contract test validation"
  invokes:
    - skill: test/contract
      when: "Critical or major findings require test fixes"
    - skill: test/factories
      when: "Test data generation issues detected"
    - skill: implement/pydantic
      when: "Schema definition issues found"
---

# Contract Test Review

> Validate that contract tests properly guard API boundaries through systematic quality analysis.

## Quick Reference

| Aspect | Details |
|--------|---------|
| **Dimension** | Contract Test Quality |
| **Scope** | `tests/contract/**/*.py`, `**/test_*contract*.py`, `**/contract_test*.py`, `**/test_*schema*.py`, `schemathesis.toml` |
| **Invoked By** | `test/contract`, `implement/api`, `/review` command |
| **Invokes** | `test/contract` (on failure), `test/factories` (data issues) |
| **Verdict Options** | `PASS` · `PASS_WITH_SUGGESTIONS` · `NEEDS_WORK` · `FAIL` |

---

## Review Objective

Ensure contract tests validate API agreements between consumers and providers without coupling to implementation details, enabling confident refactoring and API evolution.

### This Review Answers

1. Are contracts testing API boundaries only, not internal implementation?
2. Do contracts use flexible matchers that survive provider evolution?
3. Are both success AND error response shapes validated?
4. Are contracts isolated, independent, and following AAA structure?
5. Do Schemathesis tests use v4.x API, appropriate loaders, and proper check configuration?

### Out of Scope

- Business logic validation (unit test territory)
- Full integration testing (integration test territory)
- Performance characteristics of contract tests

---

## Core Workflow

1. **SCOPE** → `tests/contract/**/*.py`, `**/test_*contract*.py`
2. **CONTEXT** → Load `rules/testing.md`, `rules/mocking.md`, `rules/factories.md`
3. **ANALYZE** → Apply criteria by priority: P0 (Blocker) → P1 (Critical) → P2 (Major) → P3 (Minor)
4. **CLASSIFY** → Assign severity per finding
5. **VERDICT** → Determine outcome based on severity distribution
6. **CHAIN** → Invoke `test/contract` if fixes needed

### Severity Classification

| Severity | Definition | Action |
|----------|------------|--------|
| **🔴 BLOCKER** | Tests internal implementation, not API boundary | Must fix |
| **🟠 CRITICAL** | Missing error contracts, mocking contract schema | Must fix |
| **🟡 MAJOR** | Over-specified matchers, shared state, weak assertions | Should fix |
| **🔵 MINOR** | Naming issues, missing AAA separation | Consider |
| **⚪ SUGGESTION** | Style improvements | Optional |

### Verdict Logic

```
Any BLOCKER? ────────────► FAIL
Any CRITICAL? ───────────► NEEDS_WORK
Multiple MAJOR (>2)? ────► NEEDS_WORK
Few MAJOR/MINOR? ────────► PASS_WITH_SUGGESTIONS
Suggestions only? ───────► PASS
```

---

## Evaluation Criteria

### Boundary Testing (P0/P1)

| ID | Criterion | Severity | Check |
|----|-----------|----------|-------|
| BT.1 | Tests API boundary only (HTTP, message queue, SDK) | BLOCKER | No db_session, no internal method calls |
| BT.2 | No assertions on database state or internal objects | BLOCKER | Assert on response shape, not `db.query()` |
| BT.3 | Mock consumer/provider, never the contract schema | CRITICAL | No `mocker.patch("app.schemas...")` |
| BT.4 | No private method testing (`_method`) | BLOCKER | Public API surface only |

### Contract Correctness (P1/P2)

| ID | Criterion | Severity | Check |
|----|-----------|----------|-------|
| CC.1 | Uses flexible matchers (`match.int()`, `match.str()`, `match.regex()`, `match.each_like()`) | CRITICAL | No exact value matching for dynamic fields |
| CC.2 | Error response shapes validated (4xx/5xx) | CRITICAL | `test_error_response_*` tests exist |
| CC.3 | Schema validation uses explicit JSON schema | MAJOR | `validate(instance, schema)` pattern |
| CC.4 | Contracts versioned alongside API versions | MAJOR | Version in filename or test name |
| CC.5 | Backward compatibility explicitly tested | MAJOR | `test_previous_consumer_works_with_new_*` patterns |

### Test Quality (P2)

| ID | Criterion | Severity | Check |
|----|-----------|----------|-------|
| TQ.1 | Follows AAA structure with visual separation | MAJOR | Comments: `# Arrange`, `# Act`, `# Assert` |
| TQ.2 | Descriptive names: `test_<action>_<outcome>` | MAJOR | Not `test_contract_1`, `test_api` |
| TQ.3 | Uses factories for test data, not hardcoded values | MAJOR | `order_factory.build()`, not inline dicts |
| TQ.4 | Specific assertions, not just `assert response` | MAJOR | Assert on schema validation result |
| TQ.5 | Exception testing uses `match=` parameter | MINOR | `pytest.raises(ValueError, match="...")` |

### Isolation & Independence (P2/P3)

| ID | Criterion | Severity | Check |
|----|-----------|----------|-------|
| II.1 | No shared mutable state between tests | MAJOR | No class attributes, module globals |
| II.2 | Each test independently executable | MAJOR | `pytest test_file.py::test_name -v` works |
| II.3 | Pact lifecycle properly managed (`pact.serve()` context manager, `write_file()` in teardown) | MAJOR | Fixture with yield and cleanup |
| II.4 | Fixtures scoped appropriately (module for Pact) | MINOR | `@pytest.fixture(scope="module")` |

### Schemathesis Usage (P1/P2)

When Schemathesis tests are present, apply these additional criteria.
For implementation guidance, see `skills/test-contract/references/schemathesis-guide.md` and `skills/test-contract/references/schemathesis-advanced.md`.

| ID | Criterion | Severity | Check |
|----|-----------|----------|-------|
| ST.1 | Uses v4.x API (`schemathesis.openapi.from_url`, `from_asgi`, `from_path`) | CRITICAL | No deprecated `schemathesis.from_uri()` or `schemathesis.from_url()` (top-level) |
| ST.2 | Uses `from_asgi()` for FastAPI services (no network overhead) | MAJOR | Not `from_url("http://localhost:...")` when app is importable |
| ST.3 | Uses `call_and_validate()` over manual `call()` + `validate_response()` | MINOR | Prefer single method unless custom response handling needed |
| ST.4 | Configures appropriate checks (`--checks all` or selective) | MAJOR | Not relying on default `not_a_server_error` alone |
| ST.5 | Uses hooks to pin path parameters to known test data when needed | MAJOR | `map_path_parameters` hook instead of relying on random IDs that produce 404s |
| ST.6 | Stateful testing enabled when API has CRUD workflows | MAJOR | `--phases` includes `stateful` or OpenAPI links defined |
| ST.7 | `schemathesis.toml` used for repeatable project config | MINOR | Not passing all options via CLI flags in CI |

---

## Patterns & Anti-Patterns

### ✅ Correct: Boundary-Focused Contract

```python
def test_get_user_returns_expected_shape(pact):
    # ── Arrange ──────────────────────────────────────
    (
        pact
        .upon_receiving("a request for user 123")
        .given("user 123 exists", id=123)
        .with_request("GET", "/users/123")
        .will_respond_with(200)
        .with_body({
            "id": match.int(123),
            "email": match.regex("user@example.com", regex=r".+@.+\..+"),
        }, content_type="application/json")
    )

    # ── Act ──────────────────────────────────────────
    with pact.serve() as srv:
        client = UserClient(str(srv.url))
        user = client.get_user(123)

    # ── Assert ───────────────────────────────────────
    assert user.id == 123
    assert "@" in user.email
```

**Why:** Pact v3 fluent API, flexible matchers, real client code, AAA structure, boundary-only assertions.

### ✅ Correct: Schemathesis Schema Contract

```python
import schemathesis

# v4.x API: direct ASGI testing for FastAPI (no network overhead)
schema = schemathesis.openapi.from_asgi("/openapi.json", app)

@schema.parametrize()
def test_api_conforms_to_openapi(case):
    """Property-based: all endpoints match OpenAPI spec."""
    case.call_and_validate()
```

**Why:** Uses v4.x `from_asgi()` loader (ST.1, ST.2), `call_and_validate()` (ST.3), auto-runs all checks.

### ❌ Anti-Patterns

**Testing Internal Implementation:**
```python
# WRONG: Asserting on database state
assert db_session.query(User).count() == 1  # Implementation detail!
```

**Mocking the Contract:**
```python
# WRONG: Defeats contract testing purpose
mocker.patch("app.schemas.UserResponse", return_value={"id": 1})
```

**Over-Specified Matchers:**
```python
# WRONG: Exact values break on valid variations
.with_body({"email": "exact@email.com"})  # Use match.str() or match.regex()
```

**Missing Error Contracts:**
```python
# WRONG: Only happy path - no 4xx/5xx shape validation
assert response.status_code == 201  # Where are error tests?
```

**Deprecated Schemathesis API (ST.1):**
```python
# WRONG: Pre-v4.x top-level API — deprecated
schema = schemathesis.from_uri("http://localhost:8000/openapi.json")

# CORRECT: v4.x namespace
schema = schemathesis.openapi.from_url("http://localhost:8000/openapi.json")
```

**Network Testing When ASGI Available (ST.2):**
```python
# WRONG: Network overhead when FastAPI app is importable
schema = schemathesis.openapi.from_url("http://localhost:8000/openapi.json")

# CORRECT: Direct ASGI — no network, no port conflicts
schema = schemathesis.openapi.from_asgi("/openapi.json", app)
```

**Default Checks Only (ST.4):**
```python
# WRONG: Only checks for 5xx errors, misses schema conformance
schemathesis run http://localhost:8000/openapi.json  # default: not_a_server_error

# CORRECT: All checks enabled
schemathesis run --checks all http://localhost:8000/openapi.json
```

---

## Output Formats

### Finding Format

```markdown
### [🔴 BLOCKER] {{Title}}
**Location:** `path/file.py:42` | **Criterion:** BT.1
**Issue:** {{Description}}
**Evidence:** `{{code_snippet}}`
**Fix:** {{Remediation}}
```

### Review Summary

```markdown
# Contract Test Review: {{VERDICT}}
| Blockers | Critical | Major | Minor | Files |
|----------|----------|-------|-------|-------|
| {{N}}    | {{N}}    | {{N}} | {{N}} | {{N}} |

**Key Findings:** {{Top 3}}
**Actions:** {{Required fixes}}
**Chain:** {{Next skill or PASS}}
```

---

## Skill Chaining

| Verdict | Action | Target |
|---------|--------|--------|
| `FAIL` | Mandatory rewrite | `test/contract` |
| `NEEDS_WORK` | Targeted fixes | `test/contract` |
| `PASS_WITH_SUGGESTIONS` | Optional | None |
| `PASS` | Continue | `review/integration-tests` |

**Handoff:** `Chain Target: test/contract | Findings: {{IDs}} | Constraint: Preserve coverage, fix anti-patterns`

**Re-Review:** Scope to modified files, max 3 iterations.

---

## Validation Commands

```bash
pytest tests/contract/ -v                                    # Run tests
grep -r "db_session\|\.query(" tests/contract/               # Find boundary violations
grep -r "@.*\.com" tests/contract/ | grep -v "match\."       # Find over-specification
ruff check tests/contract/                                   # Style check

# Schemathesis-specific checks
grep -r "schemathesis\.from_uri\|schemathesis\.from_url(" tests/contract/  # Find deprecated v3.x API (ST.1)
grep -r "from_url.*localhost" tests/contract/ | grep -v from_asgi          # Find network tests when ASGI possible (ST.2)
grep -r "\.call()" tests/contract/ | grep -v "call_and_validate"           # Find manual call+validate (ST.3)
grep -rL "checks" tests/contract/*schema* 2>/dev/null                      # Find missing check config (ST.4)
```

---

## Quality Gates

- [ ] All contract test files analyzed
- [ ] No internal implementation assertions (BT.1, BT.2, BT.4)
- [ ] Flexible matchers used (CC.1)
- [ ] Error responses covered (CC.2)
- [ ] AAA structure and naming (TQ.1, TQ.2)
- [ ] Test independence verified (II.1, II.2)
- [ ] Schemathesis uses v4.x API, not deprecated loaders (ST.1)
- [ ] Schemathesis uses `from_asgi()` for FastAPI services (ST.2)
- [ ] Schemathesis configures checks beyond default (ST.4)
- [ ] Verdict matches severity distribution
- [ ] Chain decision justified

---

## Deep References

| Reference | Path |
|-----------|------|
| Contract Patterns | `skills/test-contract/SKILL.md` |
| Schemathesis Guide | `skills/test-contract/references/schemathesis-guide.md` |
| Schemathesis Advanced | `skills/test-contract/references/schemathesis-advanced.md` |
| Pact Consumer Guide | `skills/test-contract/references/pact-consumer.md` |
| Pact Provider Guide | `skills/test-contract/references/pact-provider.md` |
| Pact Advanced Patterns | `skills/test-contract/references/pact-advanced.md` |
| Testing Standards | `rules/testing.md` |
| Mocking Rules | `rules/mocking.md` |
| Factory Patterns | `rules/factories.md` |
| API Principles | `rules/principles.md` §1.1 |
