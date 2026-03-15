---
name: review-integration-tests
version: 1.0.0

description: |
  Review integration tests for boundary isolation, behavior focus, and test independence.
  Use when reviewing test files in tests/integration/, validating repository tests,
  HTTP client tests, API endpoint tests, or AWS service integration tests.
  Relevant for Python pytest suites, FastAPI TestClient, SQLAlchemy, respx, moto.

chains:
  invoked-by:
    - skill: test/integration
      context: "Post-implementation quality gate"
    - skill: implement/api
      context: "After API route test generation"
    - skill: implement/python
      context: "After repository/service test implementation"
  invokes:
    - skill: test/integration
      when: "Critical or major findings require test rewrite"
    - skill: implement/python
      when: "Test reveals missing production code patterns"
---

# Integration Tests Review

> Validate that integration tests verify component interactions at real boundaries with isolated, reproducible, behavior-focused assertions.

## Quick Reference

| Aspect | Details |
|--------|---------|
| **Dimension** | Integration Test Quality |
| **Scope** | `tests/integration/**/*.py`, `**/test_*_integration.py` |
| **Invoked By** | `test/integration`, `implement/api`, `implement/python` |
| **Invokes** | `test/integration` (on failure), `implement/python` (missing patterns) |
| **Verdict Options** | `PASS` · `PASS_WITH_SUGGESTIONS` · `NEEDS_WORK` · `FAIL` |

---

## Review Objective

Ensure integration tests validate real component interactions at system boundaries while remaining isolated, independent, and focused on observable behavior rather than implementation details.

### This Review Answers

1. Are tests hitting real boundaries (DB, HTTP, AWS) with proper isolation?
2. Do tests verify persisted/observable state, not just return values?
3. Are tests independent with no shared mutable state?
4. Do factories generate all test data with minimal overrides?

### Out of Scope

- Unit test review (see `review/unit-tests`)
- Production code quality (see `review/python`, `review/api`)

---

## Core Workflow

```
┌─────────────────────────────────────────────────────────────┐
│                    REVIEW WORKFLOW                          │
├─────────────────────────────────────────────────────────────┤
│  1. SCOPE    →  Identify integration test files             │
│  2. CONTEXT  →  Load testing rules & integration SKILL      │
│  3. ANALYZE  →  Apply criteria: boundaries, isolation, data │
│  4. CLASSIFY →  Assign severity to each finding             │
│  5. VERDICT  →  Determine pass/fail based on findings       │
│  6. REPORT   →  Output structured review results            │
│  7. CHAIN    →  Invoke test/integration if rewrite needed   │
└─────────────────────────────────────────────────────────────┘
```

### Step 1: Scope Definition

Identify review targets:

```bash
tests/integration/**/*.py
tests/**/test_*_repository.py
tests/**/test_*_client.py
tests/**/test_*_service.py
```

### Step 2: Context Loading

Before analysis, internalize:







- **Rules:** `rules/testing.md` → AAA structure, behavior focus
- **Rules:** `rules/mocking.md` → External boundary mocking only
- **Rules:** `rules/test-factories.md` → Factory patterns
- **Skills:** `skills/test/integration/SKILL.md` → Boundary classification

### Step 3: Systematic Analysis

Evaluate each test file against criteria in severity order:

| Priority | Criterion Category | Weight |
|----------|-------------------|--------|
| P0 | Boundary Violations | Blocker |
| P1 | Isolation Failures | Critical |
| P2 | Assertion Deficiencies | Major |
| P3 | Data & Structure Issues | Minor |

### Step 4: Severity Classification

| Severity | Definition | Action Required |
|----------|------------|-----------------|
| **🔴 BLOCKER** | Mocking own code, test interdependencies, no rollback | Must fix before merge |
| **🟠 CRITICAL** | Missing state verification, shared mutable state | Must fix, may defer |
| **🟡 MAJOR** | Hardcoded data, weak assertions, missing error cases | Should fix |
| **🔵 MINOR** | Naming issues, AAA separation, missing edge cases | Consider fixing |
| **⚪ SUGGESTION** | Optimization, better patterns available | Optional improvement |
| **🟢 COMMENDATION** | Exemplary patterns worth replicating | Positive reinforcement |

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

### Boundary & Isolation (BI)

| ID | Criterion | Severity | Check |
|----|-----------|----------|-------|
| BI.1 | Tests hit real boundaries (DB, HTTP, AWS) with isolation | BLOCKER | No `mocker.patch` on own repositories/services |
| BI.2 | External HTTP calls use `@respx.mock` decorator | CRITICAL | `respx.mock` present for HTTP client tests |
| BI.3 | AWS calls use `@mock_aws` with resource creation | CRITICAL | `moto` decorator + bucket/queue creation in Arrange |
| BI.4 | Database tests use transaction rollback fixture | BLOCKER | `db_session` fixture with `transaction.rollback()` |
| BI.5 | FastAPI tests override `get_db` dependency | CRITICAL | `app.dependency_overrides[get_db]` in fixture |
| BI.6 | Dependency overrides cleared after test | CRITICAL | `app.dependency_overrides.clear()` in teardown |

### Test Independence (TI)

| ID | Criterion | Severity | Check |
|----|-----------|----------|-------|
| TI.1 | No shared mutable state (class attrs, module globals) | BLOCKER | No `cls.order_id`, no module-level mutation |
| TI.2 | Each test creates own data via factories | CRITICAL | Factory calls in each test function |
| TI.3 | Tests pass in isolation | CRITICAL | `pytest path::test_name` works standalone |
| TI.4 | No test ordering dependencies | BLOCKER | No `test_1` creating data for `test_2` |
| TI.5 | Engine scoped to session, session to function | MAJOR | `scope="session"` for engine, `scope="function"` for session |

### Assertion Quality (AQ)

| ID | Criterion | Severity | Check |
|----|-----------|----------|-------|
| AQ.1 | Asserts on persisted state, not just return values | CRITICAL | `db_session.get()` or query after mutation |
| AQ.2 | Both response status AND body verified | MAJOR | `assert response.status_code` + `response.json()` |
| AQ.3 | Error response structure validated | MAJOR | `response.json()["detail"]` checked for 4xx |
| AQ.4 | Mock interactions verified (args, call count) | MAJOR | `assert_called_once_with()` or `call_args` check |
| AQ.5 | Exception assertions use `match=` parameter | MAJOR | `pytest.raises(Error, match="pattern")` |
| AQ.6 | System state verified after mock interactions | CRITICAL | Object state checked, not just mock call |

### Data Management (DM)

| ID | Criterion | Severity | Check |
|----|-----------|----------|-------|
| DM.1 | Factories generate all test entities | MAJOR | No inline `Order(id="123", ...)` construction |
| DM.2 | Minimal overrides (only test-relevant fields) | MINOR | Factory calls override ≤3 fields |
| DM.3 | Pydantic models passed as `.model_dump()` | MAJOR | No raw Pydantic objects to TestClient |
| DM.4 | No hardcoded IDs, emails, or timestamps | MAJOR | Faker providers or factory defaults |
| DM.5 | Realistic values from Faker providers | MINOR | `fake.email()`, `fake.uuid4()`, not `"test@test.com"` |

### Error Handling (EH)

| ID | Criterion | Severity | Check |
|----|-----------|----------|-------|
| EH.1 | Timeout scenarios tested | MAJOR | `httpx.TimeoutException` or connection timeout |
| EH.2 | Not-found cases return proper status | MAJOR | 404 response tested for missing resources |
| EH.3 | Conflict/constraint violations tested | MAJOR | 409 or `IntegrityError` scenarios |
| EH.4 | 5xx handling with `raise_server_exceptions=False` | MINOR | Server error paths tested |
| EH.5 | Retry behavior verified with `side_effect` sequences | MINOR | `[Error(), Error(), Success()]` pattern |

### Structure & Naming (SN)

| ID | Criterion | Severity | Check |
|----|-----------|----------|-------|
| SN.1 | AAA structure with visual separation | MINOR | Blank lines or comments between phases |
| SN.2 | Names follow `test_<action>_<outcome>` | MINOR | Descriptive, reveals intent |
| SN.3 | One concept per test function | MAJOR | No testing create+update+delete together |
| SN.4 | Fixtures properly typed with Generator | MINOR | `-> Generator[TestClient, None, None]` |

---

## Patterns & Anti-Patterns

### ✅ Indicators of Quality

```python
def test_saves_order_to_database(db_session, order_factory):
    # Arrange
    order = order_factory.build(status="pending")
    repo = OrderRepository(db_session)

    # Act
    repo.save(order)
    db_session.flush()

    # Assert - Query back persisted state
    retrieved = db_session.get(Order, order.id)
    assert retrieved is not None
    assert retrieved.status == "pending"
```

**Why this works:** Hits real DB with rollback isolation, uses factory, verifies persisted state not return value, clear AAA structure.

### ❌ Red Flags

```python
def test_order_service(mocker, db_session):
    # Mocking own repository - this is a unit test in disguise
    mocker.patch.object(OrderRepository, 'save')
    service = OrderService(db_session)
    result = service.create_order(...)
    assert result.id is not None  # Only checking return value
```

**Why this fails:** Mocks internal code (should let repository hit real DB), trusts return value without querying persisted state, provides no real integration coverage.

---

## Finding Output Format

```markdown
### [🔴 BLOCKER] Mocking Own Repository

**Location:** `tests/integration/services/test_order_service.py:15`
**Criterion:** BI.1 - Tests hit real boundaries with isolation

**Issue:**
Test mocks `OrderRepository.save()` instead of letting it interact with the real database. This converts the integration test into a unit test and provides no confidence in actual persistence behavior.

**Evidence:**
```python
mocker.patch.object(OrderRepository, 'save')
```

**Suggestion:**
Remove the mock and use the `db_session` fixture with transaction rollback. Let the repository execute real queries against the test database.

**Rationale:**
Integration tests must verify component interactions at real boundaries. Mocking your own code defeats the purpose and creates false confidence.
```

---

## Review Summary Format

```markdown
# Integration Tests Review Summary

## Verdict: 🟠 NEEDS_WORK

| Metric | Count |
|--------|-------|
| Files Reviewed | 5 |
| Blockers | 0 |
| Critical | 2 |
| Major | 4 |
| Minor | 3 |
| Suggestions | 1 |
| Commendations | 1 |

## Key Findings

1. **[CRITICAL]** 2 tests mock internal repositories instead of using real DB
2. **[CRITICAL]** Missing state verification in `test_create_order`
3. **[MAJOR]** Hardcoded test data in 4 tests - use factories

## Recommended Actions

1. Remove internal mocks, use `db_session` fixture with rollback
2. Add `db_session.get()` assertions after mutations
3. Replace inline entity construction with factory calls

## Skill Chain Decision

Chain to `test/integration` - 2 critical findings require test rewrites to establish proper boundary testing.
```

---

## Skill Chaining

### Chain Triggers

| Verdict | Chain Action | Target Skill |
|---------|--------------|--------------|
| `FAIL` | Mandatory rewrite | `test/integration` |
| `NEEDS_WORK` | Targeted fixes | `test/integration` |
| `PASS_WITH_SUGGESTIONS` | Optional | None (suggestions only) |
| `PASS` | Continue pipeline | `review/unit-tests` (if applicable) |

### Handoff Protocol

When chaining to `test/integration`:

```markdown
**Chain Target:** `test/integration`
**Priority Findings:** BI.1, AQ.1 (IDs of blocker/critical findings)
**Context:** Review identified 2 tests mocking internal code, 1 test missing state verification

**Constraint:** Preserve existing test coverage, fix isolation patterns

```



### Re-Review Loop



After `test/integration` completes fixes:

- Scope limited to modified test files
- Focus on previously-failed criteria
- Maximum 3 iterations before escalation to human review

---

## Integration Points

### Upstream Integration

| Source | Trigger | Context Provided |
|--------|---------|------------------|
| `test/integration` | Post-implementation | List of new/modified test files |
| `implement/api` | After route test generation | Route paths, expected responses |
| `implement/python` | After service/repo tests | Class names, method signatures |
| `/review` command | Explicit invocation | User-specified test scope |

### Downstream Integration

| Target | Condition | Handoff |
|--------|-----------|---------|
| `test/integration` | Verdict ≠ PASS | Findings + file paths + priority |
| `implement/python` | Missing patterns detected | Production code gaps |

---

## FastAPI-Specific Checks

When reviewing FastAPI route tests, additionally verify:

| Check | Pattern | Anti-Pattern |
|-------|---------|--------------|
| Client fixture | `TestClient` as context manager | Global `TestClient` instance |
| Auth override | `app.dependency_overrides[get_current_user]` | Skipping auth entirely |
| DB override | `app.dependency_overrides[get_db]` | Direct DB injection |
| Cleanup | `app.dependency_overrides.clear()` | Missing cleanup |
| File uploads | `files={"file": (name, content, type)}` | Manual `Content-Type` header |
| Async routes | `httpx.AsyncClient` with `ASGITransport` | `TestClient` in async tests |

---

## Quality Gates

Before finalizing review output:

- [ ] All test files in scope were analyzed
- [ ] Each finding has location + criterion ID + severity
- [ ] Verdict aligns with severity distribution
- [ ] Actionable suggestions provided for non-PASS verdicts
- [ ] Chain decision is explicit and justified
- [ ] Output follows structured format
- [ ] FastAPI-specific checks applied where relevant
- [ ] No false positives from pattern matching
