---
name: test
description: |
  Use when entering the testing phase, running `/test`, or when the user says "test",
  "write tests", "add tests", "generate tests", "test this", "create tests", "testing phase",
  "run tests", "add test coverage", "write unit tests", "write integration tests",
  "test the implementation", "add test infrastructure", "test pyramid", "test this task",
  "let's test", "validate tests", "check my tests", "are my tests good", "review tests",
  "verify tests", "test quality", "refactor tests", "fix tests", "improve tests",
  "test compliance", "do tests follow standards", "misplaced tests", "wrong pyramid level",
  "unit test should be integration", "test placement", "reorganize tests", or "test at wrong level".
  Also use when tests already exist and need validation against testing standards, when tests
  may be at the wrong pyramid level (e.g., a unit test that uses real DB should be integration),
  or when the user wants to ensure existing tests follow best practices and are correctly
  placed across the testing pyramid.
---

# /test — Testing Phase Orchestrator

> Detect existing tests, analyze pyramid placement correctness, relocate misplaced tests to the right level, validate against pyramid-specific review skills, refactor non-compliant tests via writing skills, then write missing tests — ensuring every relevant pyramid level is both correctly placed, covered, and standards-compliant.

## Quick Reference

| Aspect | Details |
|--------|---------|
| **Phase** | Testing (per-task, within implementation loop) |
| **Gate** | Implementation code must exist for the selected task (run `/implement` first if missing) |
| **Modes** | **Writing** (no tests exist), **Validation** (all tests exist), **Mixed** (some exist, some missing) |
| **Produces** | Shared test infrastructure (Step 1) + test code at relevant pyramid levels (Step 2), OR validation verdicts + refactored tests |
| **Mandatory** | Every agent proposal MUST specify which **Skill to Invoke** — agents without a skill assignment are never dispatched |
| **Shared Refs** | `sdlc-shared/refs/feature-resolution.md`, `sdlc-shared/refs/phase-gating.md`, `sdlc-shared/refs/agent-discovery.md`, `sdlc-shared/refs/propose-approve-execute.md`, `sdlc-shared/refs/sdlc-log-format.md` |
| **Next Phase** | `/review` (after tests are written for the task) |

---

## Core Workflow

### Step 1: Resolve Feature Directory

Follow the algorithm in [sdlc-shared/refs/feature-resolution.md](../sdlc-shared/refs/feature-resolution.md):

1. If the user passed an argument (e.g., `/test 001-sdlc-claude-commands`) — resolve to the matching feature directory under `docs/designs/*/`
2. If no argument — scan `docs/designs/` across all years, present a selection list of existing features
3. If argument doesn't match — report the error and present the selection list
4. If "create new" — assign next sequence number, create `docs/designs/YYYY/NNN-{kebab-case-name}/`

The resolved path becomes `{feature-dir}` for all subsequent steps.

### Step 2: Phase Gate — Require Implementation Code

Follow [sdlc-shared/refs/phase-gating.md](../sdlc-shared/refs/phase-gating.md):

```
Check: Implementation code exists for the selected task?
  |-- Yes -> Proceed to Step 3
  +-- No  -> Block:
            "No implementation code found for this task."
            "Run `/implement` first to produce code."
            -> END
```

#### How to Check "Implementation Code Exists"

Use the algorithm from the phase-gating shared ref:

1. **Check `{feature-dir}/tasks-breakdown.md`** — does it exist? If not, there is no task context at all. Block with: "No task breakdown found. Run `/tasks-breakdown` first, then `/implement`."

2. **Check `{feature-dir}/sdlc-log.md`** — look for entries recording `/implement` execution for the feature. If an entry exists with a successful outcome, code exists.

3. **Check git status** — look for code changes associated with the feature:
   ```bash
   git log --oneline --grep="{feature-name}" -- '*.py' '*.ts' '*.tsx'
   ```

4. **Check task status in `tasks-breakdown.md`** — if any task's implementation sub-tasks are marked as started or complete, code exists.

5. **Fallback: Ask the user** — if the above checks are inconclusive, ask: "Has implementation code been written for this feature? The SDLC log doesn't show a `/implement` run."

The intent is pragmatic: don't block a user who has already written code outside the orchestrator flow. If there's evidence code exists, proceed.

### Step 3: Task Context — Identify What to Test

Read the feature's context to understand what code needs testing:

1. Read `{feature-dir}/tasks-breakdown.md` — identify which tasks have been implemented (marked `✅ Complete` or `🔄 In Progress`)
2. Read `{feature-dir}/sdlc-log.md` — find `/implement` entries to identify which code files were produced and which agents participated
3. Read `{feature-dir}/lld.md` — understand API contracts, data models, event schemas, and service boundaries that define what to test
4. Read `{feature-dir}/prd.md` — check acceptance criteria that tests should validate

If multiple tasks have been implemented, present them and ask the user which task(s) to test:

```markdown
## Implemented Tasks

| # | Task | Status | Files Produced |
|---|------|--------|---------------|
| T-1 | {Task 1 title} | ✅ Complete | {files from sdlc-log} |
| T-3 | {Task 3 title} | ✅ Complete | {files from sdlc-log} |

**Select which task(s) to write tests for.** You can select one task, multiple tasks (e.g., "T-1 and T-3"), or "all" for all implemented tasks.
```

If only one task has been implemented, proceed directly with that task's context.

### Step 3.5: Detect Existing Tests & Determine Mode

Before analyzing infrastructure or proposing new test agents, check if tests already exist for the selected task's implementation files.

#### How to Detect Existing Tests

1. **Scan test directories** for files corresponding to the implementation files identified in Step 3:
   - `tests/unit/` → unit tests
   - `tests/integration/` → integration tests
   - `tests/contract/` → contract tests
   - `tests/e2e/` → e2e tests
   - `tests/ui/` or `web/tests/` → UI tests

2. **Match by naming convention**: Implementation file `services/<svc>/<svc>/domains/<dom>/flows/v1/create_payment.py` → test file `tests/unit/services/<svc>/domains/<dom>/flows/v1/test_create_payment.py` (and similar for other pyramid levels).

3. **Check pytest markers**: Scan existing test files for `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.contract`, `@pytest.mark.e2e` to classify which pyramid levels are covered.

4. **Build a coverage matrix**:

```markdown
## Existing Test Coverage — Task T-{N}

| Pyramid Level | Test Files Found | Tests Count | Status |
|---------------|-----------------|-------------|--------|
| Unit | `tests/unit/.../test_create_payment.py` | 8 tests | Exists |
| Integration | — | 0 | Missing |
| Contract | `tests/contract/.../test_payments_api.py` | 3 tests | Exists |
| E2E | — | 0 | Missing |
| UI | — | 0 | N/A (no frontend) |
```

#### Determine Mode

Based on the coverage matrix and the context-based filtering from Step 6 (which pyramid levels are relevant for this task), determine the operating mode:

| Condition | Mode | Action |
|-----------|------|--------|
| **ALL relevant pyramid levels have tests** | **Validation Only** | Skip writing, go to Step 3.6 (validate existing tests) |
| **SOME relevant levels have tests, others don't** | **Mixed** | Validate existing (Step 3.6) + write missing (Steps 4–7) |
| **NO tests exist for any relevant level** | **Writing Only** | Skip validation, proceed to Steps 4–7 (current write flow) |

Present the coverage matrix and mode to the user:

```markdown
## Test Detection Results

{coverage matrix from above}

### Mode: {Validation Only | Mixed | Writing Only}

**Validation Only:** All relevant pyramid levels already have tests. I'll validate them against the testing standards and refactor any that don't comply.

**Mixed:** Some pyramid levels have existing tests that I'll validate. For missing levels, I'll propose new test agents.

**Writing Only:** No existing tests found. Proceeding to create test infrastructure and write tests.

**Proceed with this plan?**
```

### Step 3.55: Pyramid Placement Analysis (Validation & Mixed Modes)

Before validating tests against their current level's standards, check whether each test is actually at the **correct pyramid level**. A test file sitting in `tests/unit/` might exhibit patterns that belong to integration testing — or vice versa. Catching misplacement early prevents wasting review/refactor effort on tests that need to move, not just improve.

Skip this step in **Writing Only** mode (no existing tests to analyze).

#### Misplacement Signal Matrix

Each pyramid level has defining characteristics. When a test exhibits signals from a *different* level, it's misplaced:

| Signal Found in Test Code | If Currently | Should Be | Reasoning |
|---------------------------|-------------|-----------|-----------|
| Real DB session/connection (`db_session`, `async_session` fixtures), actual SQL execution | Unit | **Integration** | Unit tests isolate logic from I/O — real database interaction crosses a boundary |
| Real HTTP calls (`httpx.AsyncClient` without mock, `TestClient` with real deps) | Unit | **Integration** | Network calls are integration boundaries by definition |
| Real message broker connections (Kafka, RabbitMQ, SQS consumers/producers) | Unit | **Integration** | Broker interaction is an external boundary |
| FastAPI `TestClient` with real dependency injection (no `dependency_overrides`) | Unit | **Integration** | Testing through the real HTTP stack with real deps = integration |
| `@mock_aws` with real AWS resource creation and interaction | Unit | **Integration** | AWS service interaction (even mocked via moto) tests boundary behavior |
| ALL dependencies mocked (`mocker.patch` on repos, services, adapters), zero real I/O | Integration | **Unit** | If nothing real is integrated, it's a unit test wearing an integration label |
| Only tests pure logic/transformations, no fixtures for DB/HTTP/queues | Integration | **Unit** | Pure function testing belongs at unit level regardless of file location |
| Validates API response schema against OpenAPI spec (`jsonschema.validate`, schema matchers) | Unit | **Contract** | Schema validation against specs is contract testing, not unit testing |
| Tests event payload structure against AsyncAPI spec | Unit or Integration | **Contract** | Event contract validation belongs in contract tests |
| Uses consumer-driven contract patterns (Pact matchers: `Like()`, `Term()`, `EachLike()`) | Unit or Integration | **Contract** | Consumer-driven patterns are contract testing by definition |
| Spans multiple services or bounded contexts in a single test | Integration | **E2E** | Cross-service testing is end-to-end |
| Tests complete multi-step user journeys (login → action → verify → outcome) | Integration | **E2E** | Full user flows belong at the E2E level |
| Uses browser automation (Playwright, Selenium) | Any non-UI | **UI** | Browser-based testing belongs in the UI level |
| Tests single component with ALL externals mocked, no real infrastructure | E2E | **Unit or Integration** | E2E tests must exercise real systems — full mocking defeats their purpose |
| `mocker.patch("app.services.*")` or `mocker.patch("app.adapters.*")` mocking own code | Integration | **Unit** | Integration tests should use real internal services; mocking own code = unit test pattern |
| More than 3 mocks in a single test | Unit | **Refactor needed** | Exceeding mock limits signals the unit under test has too many responsibilities (`.claude/rules/mocking.md` says max 2) |

#### How to Detect Misplacement

For each test file found in Step 3.5's coverage matrix, perform four analyses:

**1. Import Analysis** — What does the test import?
- Database session factories, connection pools, ORM models → integration signal
- `httpx.AsyncClient` without mock wrapper → integration signal
- `TestClient` from FastAPI → integration signal (unless all deps overridden via `dependency_overrides`)
- Playwright, Selenium → UI signal
- Only domain models, pure functions, value objects → unit signal
- `jsonschema`, Pact matchers (`Like`, `Term`) → contract signal

**2. Fixture Analysis** — What fixtures does the test use?
- `db_session`, `async_session`, database fixtures → integration signal
- `httpx_mock`, `respx`, `@respx.mock` → unit signal (mocked = not integration)
- `@mock_aws` with resource setup → integration signal
- No fixtures or only factory fixtures → unit signal
- `TestClient` fixture → check if deps are overridden (unit if mocked, integration if real)

**3. Assertion Analysis** — What does the test assert?
- Schema compliance (`jsonschema.validate`, OpenAPI validation) → contract signal
- HTTP status codes + response body shape matching → contract signal
- Persisted state via `db_session.get()` or re-query after mutation → integration signal
- Domain logic outcomes (return values, raised exceptions, state changes on objects) → unit signal
- Cross-service data flow or multi-step journey outcomes → E2E signal
- Mock call verification (`mock.assert_called_with(...)`) as the *only* assertion → unit signal

**4. Marker vs. Signal Consistency** — Does the pytest marker match the detected signals?
- `@pytest.mark.unit` but integration signals present → **misplaced**
- `@pytest.mark.integration` but only unit signals → **misplaced**
- `@pytest.mark.contract` but tests internal DB state → **misplaced**
- `@pytest.mark.e2e` but mocks internal services → **misplaced**
- No marker at all → **flag for classification** based on detected signals

#### Build Misplacement Report

```markdown
## Pyramid Placement Analysis — Task T-{N}

### Misplaced Tests Found: {count}

| # | Test File | Current Level | Correct Level | Key Signals | Confidence |
|---|-----------|--------------|---------------|-------------|------------|
| 1 | `tests/unit/.../test_create_payment.py` | Unit | Integration | Uses `db_session` fixture, asserts via `db_session.get()` after mutation | High |
| 2 | `tests/integration/.../test_payment_validator.py` | Integration | Unit | All deps mocked via `mocker.patch`, no real I/O, tests pure validation logic | High |
| 3 | `tests/unit/.../test_payments_api_schema.py` | Unit | Contract | Uses `jsonschema.validate` against OpenAPI spec, asserts response shape | Medium |

### Correctly Placed Tests: {count}

| # | Test File | Level | Confidence |
|---|-----------|-------|------------|
| 1 | `tests/unit/.../test_money_value_object.py` | Unit | High — pure logic, no I/O, factory data |
| 2 | `tests/integration/.../test_payment_repository.py` | Integration | High — real DB fixture, actual persistence, state verification |
```

If **no misplaced tests** are found, report it briefly and proceed:

```markdown
## Pyramid Placement Analysis — Task T-{N}

All {count} existing test files are correctly placed on the testing pyramid. No relocations needed.

**Proceeding to Step 3.6: Validate existing tests.**
```

#### Present and Await Approval

When misplaced tests are found, present the relocation proposal:

```markdown
## Pyramid Placement Analysis Results

{misplacement report from above}

### Proposed Relocations

For each misplaced test, the target level's tester agent will rewrite the test following the correct level's standards:

| # | Test File | From → To | Agent | Skill to Invoke |
|---|-----------|-----------|-------|-----------------|
| 1 | `test_create_payment.py` | Unit → Integration | `integration-tester` | `/test-Integration` |
| 2 | `test_payment_validator.py` | Integration → Unit | `unit-tester` | `/test-unit` |
| 3 | `test_payments_api_schema.py` | Unit → Contract | `contract-tester` | `/test-contract` |

Each relocation agent will:
1. Read the misplaced test to understand what behavior it validates
2. Rewrite it following the **target level's** standards and conventions
3. Place it in the correct test directory (`tests/{target-level}/...`)
4. Delete the original misplaced test file
5. Update the pytest marker to `@pytest.mark.{target-level}`

**Approve relocations?** You can:
- Approve all relocations
- Skip specific relocations (by number)
- Override a detected level (e.g., "keep #2 as integration")
- Skip all (accept current placement)
```

Never dispatch relocation agents without explicit approval.

#### Dispatch Relocation Agents

After approval, dispatch all approved relocation agents in parallel via the Agent tool in a **single message**. Each agent receives:

```markdown
## Context

**Feature:** {feature-name}
**Feature Directory:** {feature-dir-path}
**Phase:** Testing — Pyramid Placement Relocation
**Task:** T-{N} — {task title}

## Skill to Invoke

You MUST invoke the `/{target-writing-skill}` skill before starting your work. This skill defines the testing standards and patterns for the target pyramid level. Do not proceed without loading the skill first.

## Your Assignment

Relocate a misplaced test from {current-level} to {target-level}. The test is currently at the wrong pyramid level and needs to be rewritten following {target-level} testing standards.

## Misplaced Test

- **File:** {test file path}
- **Current Level:** {current-level} (where it is now)
- **Target Level:** {target-level} (where it should be)
- **Misplacement Signals:** {signals that indicate wrong level — e.g., "Uses db_session fixture, asserts persisted state via db_session.get()"}

## What to Do

1. **Read the misplaced test** to understand the behavior being validated — preserve all behavioral coverage
2. **Rewrite the test** following the `/{target-writing-skill}` standards:
   - For unit (`test-unit`): behavior-driven, refactor-resilient, AAA, public interface only, all deps mocked, max 2 mocks per test
   - For integration (`test-Integration`): real boundaries (DB, HTTP, events), proper isolation, factory-based data, state verification via DB query
   - For contract (`test-contract`): consumer-driven, schema compliance, flexible matchers, backward compatibility validation, no DB assertions
   - For e2e (`test-e2e`): complete user journeys, real system integration, behavioral validation, `poll_until` for async
   - For ui (`test-ui`): semantic locators, web-first assertions, proper isolation, async handling
3. **Place the rewritten test** in `tests/{target-level}/` mirroring the source directory structure
4. **Delete the original misplaced test** from `tests/{current-level}/`
5. **Update the pytest marker** to `@pytest.mark.{target-level}`
6. **Run the rewritten test** to verify it passes: `uv run pytest {new-test-file-path} -v`

## Implementation Files Under Test

{List of implementation files the test covers}

## Shared Test Infrastructure

{Available factories, fixtures, conftest from existing infrastructure or Step 1}

USE the shared infrastructure. Do NOT recreate factories, fixtures, or conftest configurations that already exist.

## Codebase Conventions

- `.claude/rules/testing.md` — AAA structure, naming, one concept per test
- `.claude/rules/mocking.md` — mock only external boundaries, max 2 mocks per test, patch at usage site
- `.claude/rules/factories.md` — Polyfactory for models, `.build()` for in-memory, `.create()` for persistence
- Test markers: `@pytest.mark.{target-level}`

## Definition of Done

- Test rewritten at correct pyramid level following target level's standards
- Test placed in correct directory (`tests/{target-level}/...`) mirroring source structure
- Original misplaced test deleted from `tests/{current-level}/`
- Pytest marker updated to `@pytest.mark.{target-level}`
- **No behavioral coverage lost** — all assertions from original test preserved or translated to the target level's assertion style
- Rewritten test passes: `uv run pytest {new-test-file-path} -v`
```

#### Update Coverage Matrix After Relocation

After all relocation agents complete, update the coverage matrix from Step 3.5 to reflect the new state. Pyramid levels may have gained or lost tests:

```markdown
## Relocation Complete

| # | Test | From → To | Status |
|---|------|-----------|--------|
| 1 | `test_create_payment.py` | Unit → Integration | ✅ Relocated |
| 2 | `test_payment_validator.py` | Integration → Unit | ✅ Relocated |
| 3 | `test_payments_api_schema.py` | Unit → Contract | ✅ Relocated |

### Updated Coverage Matrix

| Pyramid Level | Test Files | Tests Count | Status | Changes |
|---------------|-----------|-------------|--------|---------|
| Unit | `test_money_value_object.py`, `test_payment_validator.py` | 10 | Exists | +1 relocated from Integration |
| Integration | `test_payment_repository.py`, `test_create_payment.py` | 8 | Exists | +1 relocated from Unit |
| Contract | `test_payments_api_schema.py` | 3 | Exists (new) | +1 relocated from Unit |
| E2E | — | 0 | Missing | — |
```

**After relocation, recalculate the mode** based on the updated matrix:
- If relocation created coverage for previously missing levels → mode may shift from Mixed to Validation Only
- If relocation removed all tests from a level → that level is now Missing
- Feed the updated matrix into Step 3.6 for validation

**Proceeding to Step 3.6: Validate existing tests (including relocated tests at their new levels).**

### Step 3.6: Validate Existing Tests (Validation & Mixed Modes)

When existing tests are detected, dispatch review agents to validate them against the corresponding review skills. Each pyramid level has a dedicated review skill and a corresponding writing skill for refactoring:

#### Pyramid-Level Agent → Skill Mapping (Mandatory Reference)

Every agent dispatched by `/test` MUST have a skill assignment. This table is the authoritative mapping — no agent is dispatched without its corresponding skill.

| Pyramid Level | Validation Agent | Skill to Invoke (validation) | Refactoring/Writing Agent | Skill to Invoke (writing) |
|---------------|-----------------|------------------------------|--------------------------|--------------------------|
| Unit | `unit-tests-reviewer` | `/review-unit-tests` | `unit-tester` | `/test-unit` |
| Integration | `integration-tests-reviewer` | `/review-integration-tests` | `integration-tester` | `/test-Integration` |
| Contract | `contract-tests-reviewer` | `/review-contract-tests` | `contract-tester` | `/test-contract` |
| E2E | `e2e-tests-reviewer` | `/review-e2e-tests` | `e2e-tester` | `/test-e2e` |
| UI | `ui-tests-reviewer` | `/review-ui-tests` | `ui-tester` | `/test-ui` |
| Infrastructure | `python-implementer` | `/implement-python` | — | — |

#### Build Validation Proposal

Only propose review agents for pyramid levels where tests **exist**:

```markdown
## Validation: Proposed Review Agents

The following review agents will validate existing tests against our testing standards:

| # | Agent | Skill to Invoke | Files to Review | Focus |
|---|-------|-----------------|-----------------|-------|
| 1 | `unit-tests-reviewer` | `/review-unit-tests` | `tests/unit/.../test_create_payment.py` | Behavior-focus, refactor-resilience, AAA pattern |
| 2 | `contract-tests-reviewer` | `/review-contract-tests` | `tests/contract/.../test_payments_api.py` | Schema compliance, consumer-driven patterns |

**Approve validation?** You can:
- Approve as-is
- Remove reviewers (by number)
- Add reviewers
- Skip validation (proceed to writing missing tests only)
```

Never dispatch review agents without explicit approval.

#### Dispatch Review Agents

After approval, dispatch all approved review agents in parallel via the Task tool in a **single message**. Each agent receives:

```markdown
## Context

**Feature:** {feature-name}
**Feature Directory:** {feature-dir-path}
**Phase:** Testing — Validation of Existing Tests
**Task:** T-{N} — {task title}

## Skill to Invoke

You MUST invoke the `/{review-skill}` skill before starting your review. This skill defines the review criteria and standards for this pyramid level. Do not proceed without loading the skill first.

## Your Assignment

Review the existing {pyramid-level} tests for compliance with the project's testing standards defined in the `/{review-skill}` skill.

## Test Files to Review

{List of test files found for this pyramid level}

## Implementation Files Under Test

{List of implementation files these tests cover}

## Design Contracts

{From lld.md — OpenAPI, AsyncAPI, data model specs relevant to these tests}

## Review Criteria

Follow the `/{review-skill}` skill standards. Key dimensions:
- For unit: behavior-focus, refactor-resilience, AAA pattern, no implementation detail testing
- For integration: boundary isolation, real dependencies, test independence, factory-based data
- For contract: schema compliance, backward compatibility, consumer-driven patterns
- For e2e: user journey completeness, real system integration, behavioral validation
- For ui: locator strategies, assertion patterns, test isolation, async handling

## Codebase Conventions

- `.claude/rules/testing.md`, `.claude/rules/mocking.md`, `.claude/rules/factories.md`
- Test markers: `@pytest.mark.{level}`
- AAA pattern, behavior-focused, refactor-resilient
- Polyfactory factories for test data

## Expected Output

Produce a structured verdict:
- **PASS**: Tests meet standards — no changes needed. List what was validated.
- **FAIL**: Tests have issues — list specific findings with severity (critical/major/minor), locations (file:line), and recommended remediation.
```

#### Collect Review Results

After all review agents complete, present a consolidated summary:

```markdown
## Validation Results

| # | Pyramid Level | Verdict | Findings | Severity Breakdown |
|---|--------------|---------|----------|--------------------|
| 1 | Unit | FAIL | 3 findings | 2 critical, 1 minor |
| 2 | Contract | PASS | 0 findings | — |

### Detailed Findings (FAIL verdicts only)

#### Unit Tests — 3 Findings

| # | Severity | Finding | File:Line | Remediation |
|---|----------|---------|-----------|-------------|
| 1 | Critical | Tests mock internal methods instead of testing behavior | `test_create_payment.py:45` | Replace with behavior assertion through public interface |
| 2 | Critical | Missing edge case coverage for insufficient funds | `test_create_payment.py` | Add test for insufficient funds scenario |
| 3 | Minor | Test data constructed manually instead of using factories | `test_create_payment.py:23` | Use Polyfactory `CreatePaymentRequestFactory` |
```

If all review agents return **PASS**:
- In **Validation Only** mode → skip to Step 8 (summary) with "All existing tests comply with standards."
- In **Mixed** mode → proceed to Steps 4–7 for writing missing pyramid levels only.

If any review agents return **FAIL** → proceed to Step 3.7 (refactoring).

### Step 3.7: Refactor Failing Tests

When review agents return FAIL verdicts, propose tester agents to refactor the non-compliant tests. Each failing pyramid level gets a corresponding tester agent that refactors according to its writing skill.

#### Build Refactoring Proposal

```markdown
## Refactoring: Proposed Tester Agents for Failing Tests

The following tester agents will refactor existing tests based on review findings:

| # | Agent | Skill to Invoke | Files to Refactor | Findings to Address |
|---|-------|-----------------|-------------------|---------------------|
| 1 | `unit-tester` | `/test-unit` | `tests/unit/.../test_create_payment.py` | 2 critical + 1 minor |

**Approve refactoring?** You can:
- Approve as-is
- Skip refactoring (accept current test quality)
- Modify scope (e.g., address only critical findings)
```

Never dispatch refactoring agents without explicit approval.

#### Dispatch Refactoring Agents

After approval, dispatch agents in parallel. Each agent receives:

```markdown
## Context

**Feature:** {feature-name}
**Feature Directory:** {feature-dir-path}
**Phase:** Testing — Refactoring Existing Tests
**Task:** T-{N} — {task title}

## Skill to Invoke

You MUST invoke the `/{writing-skill}` skill before starting your work. This skill defines the testing standards and patterns for this pyramid level. Do not proceed without loading the skill first.

## Your Assignment

Refactor the existing {pyramid-level} tests to address the review findings below. Follow the `/{writing-skill}` skill standards strictly.

## Review Findings to Address

{Paste the detailed findings table from the review verdict for this pyramid level, including severity, location, and recommended remediation}

## Test Files to Refactor

{List of test files with issues}

## Implementation Files Under Test

{List of implementation files these tests cover}

## Design Contracts

{From lld.md — OpenAPI, AsyncAPI, data model specs relevant to these tests}

## Standards to Follow

Follow the `/{writing-skill}` skill. This means:
- For `test-unit`: behavior-driven, refactor-resilient, AAA, public interface only, Polyfactory
- For `test-Integration`: real boundaries, proper isolation, factory-based data, behavior-focused
- For `test-contract`: consumer-driven, schema compliance, backward compatibility validation
- For `test-e2e`: complete user journeys, real system integration, behavioral validation
- For `test-ui`: semantic locators, web-first assertions, proper isolation, async handling

## Shared Test Infrastructure

{If infrastructure exists (conftest.py, factories), list it here}

USE the shared infrastructure. Do NOT recreate factories, fixtures, or conftest configurations that already exist.

## Codebase Conventions

- `.claude/rules/testing.md`, `.claude/rules/mocking.md`, `.claude/rules/factories.md`
- Test markers: `@pytest.mark.{level}`
- AAA pattern, behavior-focused, refactor-resilient
- Polyfactory factories for test data

## Definition of Done

- All critical and major findings from the review are addressed
- Minor findings are addressed where practical
- Refactored tests pass when run locally (`uv run pytest {test-files}`)
- Tests maintain or improve coverage — no test removals without replacement
- Tests follow the `/{writing-skill}` standards
```

#### Present Refactoring Summary

```markdown
## Refactoring Complete

| Pyramid Level | Findings Addressed | Tests Modified | Tests Added | Status |
|---------------|-------------------|----------------|-------------|--------|
| Unit | 3/3 | 2 files | 1 new test | Complete |

All review findings have been addressed. Existing tests now comply with testing standards.
```

**After validation and refactoring (Steps 3.6–3.7):**
- In **Validation Only** mode → skip to Step 8 (summary).
- In **Mixed** mode → proceed to Step 4 for writing missing pyramid levels. The infrastructure analysis (Step 4) and agent proposals (Step 6) should only target pyramid levels that are still **missing** from the coverage matrix.

### Step 4: Analyze Implementation for Test Infrastructure Needs

Before proposing agents, analyze the implementation code to determine if shared test infrastructure is needed. This analysis drives the two-step flow that is central to `/test`.

#### What to Analyze

Scan the implementation code files (identified in Step 3) for patterns that require shared infrastructure:

| Code Pattern Found | Infrastructure Needed | Example |
|--------------------|----------------------|---------|
| Repository/adapter implementations | Database fixtures, test database setup | `conftest.py` with async DB session factory |
| External HTTP calls (`lib-http`, `httpx`) | HTTP mock fixtures, response factories | `conftest.py` with `httpx_mock` or `respx` fixtures |
| Event handlers/publishers | Message broker test fixtures | `conftest.py` with in-memory event bus |
| Pydantic models at boundaries | Polyfactory model factories | `factories.py` with `ModelFactory` classes |
| Domain entities/aggregates | Domain object factories | `factories.py` with entity builders |
| FastAPI route handlers | Test client fixture, auth fixtures | `conftest.py` with `AsyncClient` setup |
| Settings/configuration usage | Test settings override fixtures | `conftest.py` with `settings_override` |
| AWS service usage (`lib-aws`) | Mocked AWS fixtures (moto or stubs) | `conftest.py` with mocked S3/SQS/etc. |
| Multiple test files sharing setup | Shared conftest at package level | Package-level `conftest.py` |

#### Present Infrastructure Analysis

```markdown
## Step 1: Test Infrastructure Analysis

Based on the implementation code for Task T-{N}, the following shared test infrastructure is recommended:

### Recommended Infrastructure

| # | Component | Purpose | Files |
|---|-----------|---------|-------|
| 1 | Polyfactory factories | Generate test data for {models found} | `tests/factories.py` |
| 2 | Database fixtures | Async test DB session with rollback | `tests/conftest.py` |
| 3 | HTTP mock fixtures | Mock external service calls to {services} | `tests/conftest.py` |
| 4 | Test client fixture | FastAPI AsyncClient for route testing | `tests/conftest.py` |

### Why Infrastructure First?

Shared test infrastructure ensures all tester agents (unit, integration, contract, e2e) work against consistent mocks, factories, and fixtures. Without it, each agent independently invents its own test setup — leading to inconsistent test data, duplicated boilerplate, and brittle tests that break when one agent's setup conflicts with another's.

**Approve this infrastructure setup?** You can:
- Approve as-is
- Remove components (by number)
- Add components
- Skip infrastructure (proceed directly to tester agents)
```

If the analysis reveals no shared infrastructure is needed (e.g., purely stateless utility functions with no external dependencies), say so and offer to skip Step 1:

```markdown
## Step 1: Test Infrastructure Analysis

The implementation code for Task T-{N} involves primarily pure functions with no external dependencies, database access, or API boundaries. No shared test infrastructure is needed.

**Proceeding directly to Step 2: Tester Agent Discovery.**
```

### Step 5: Execute Test Infrastructure Setup (Step 1 of Two-Step Flow)

If the user approved infrastructure setup, present the infrastructure agent proposal before dispatching:

```markdown
## Step 1: Infrastructure Agent

| # | Agent | Skill to Invoke | Purpose |
|---|-------|-----------------|---------|
| 1 | `python-implementer` | `/implement-python` | Create shared test factories, fixtures, and conftest configurations |

**Approve infrastructure agent?**
```

After approval, dispatch the agent. The infrastructure agent receives a structured prompt:

```markdown
## Context

**Feature:** {feature-name}
**Feature Directory:** {feature-dir-path}
**Phase:** Testing — Step 1: Test Infrastructure
**Task:** T-{N} — {task title}

## Skill to Invoke

You MUST invoke the `/implement-python` skill before starting your work. This skill defines the code generation standards and patterns. Do not proceed without loading the skill first.

## Your Assignment

Create shared test infrastructure that all subsequent tester agents will use. This runs BEFORE any test code is written — you are building the foundations.

## Infrastructure to Create

{List the approved infrastructure components from Step 4, with details:}

### Polyfactory Factories
- Create factories for: {list Pydantic models and domain entities found in the implementation}
- Location: `tests/` directory mirroring the source structure
- Use `polyfactory.factories.pydantic_factory.ModelFactory` for Pydantic models
- Use `polyfactory.factories.dataclass_factory.DataclassFactory` for dataclasses

### Conftest Fixtures
- Create/update `conftest.py` files at the appropriate package levels
- Database fixtures: async session with transaction rollback per test
- HTTP fixtures: mock external service responses
- Test client: FastAPI AsyncClient with dependency overrides
- Settings: test-specific settings overrides

## Codebase Conventions

- Follow `.claude/rules/testing.md`, `.claude/rules/mocking.md`, `.claude/rules/factories.md`
- Use `lib-testing` utilities where available (see CLAUDE.md library guide)
- Use `@pytest.mark.unit`, `@pytest.mark.integration`, etc. for test markers
- Use AAA (Arrange-Act-Assert) pattern
- Follow existing test infrastructure patterns in the codebase

## Implementation Files to Reference

{List the implementation code files that the infrastructure supports}

## Definition of Done

- All approved infrastructure components are created
- Factories generate valid instances of all Pydantic models and domain entities
- Fixtures are properly scoped (function, module, or session as appropriate)
- conftest.py files are at the correct package levels
- No test assertions yet — infrastructure only
```

3. Wait for the infrastructure agent to complete before proceeding to Step 6.

4. Present a brief summary of what was created:

```markdown
## Step 1 Complete: Test Infrastructure

| Component | Status | Files Created |
|-----------|--------|--------------|
| Polyfactory factories | ✅ | `tests/factories.py` |
| Database fixtures | ✅ | `tests/conftest.py` |
| HTTP mock fixtures | ✅ | `tests/conftest.py` |

**Proceeding to Step 2: Tester Agent Discovery.**
```

### Step 6: Discover and Propose Tester Agents (Step 2 of Two-Step Flow)

#### Discover Tester Agents

Follow [sdlc-shared/refs/agent-discovery.md](../sdlc-shared/refs/agent-discovery.md):

1. Scan `.claude/agents/` for all `*-tester.md` files
2. For each tester agent found, parse the filename to extract domain and role
3. Read the agent's `description` from frontmatter to understand its expertise

Currently expected agents:

| Agent | Domain | Pyramid Level | Specialization |
|-------|--------|--------------|----------------|
| `unit-tester` | Unit | Base | Behavior-driven unit tests for pure logic, domain models, value objects |
| `integration-tester` | Integration | Middle | Component interaction tests at real boundaries (DB, HTTP, events) |
| `contract-tester` | Contract | Middle | API/event contract validation, schema compliance, backward compatibility |
| `e2e-tester` | End-to-End | Top | Complete user journey tests through real systems |
| `ui-tester` | UI | Top | Playwright browser tests for React frontend |

Future tester agents (e.g., `load-tester.md`, `security-tester.md`, `snapshot-tester.md`) will be automatically discovered and proposed when they appear in `.claude/agents/`.

#### Filter Agents by Implementation Context

Analyze the implementation code context to determine which tester agents are relevant. Not every tester is needed for every task — propose only what the code warrants:

| Implementation Context | Propose | Skip (unless user adds) |
|----------------------|---------|------------------------|
| **Backend logic only** (domain models, flows, services, adapters — no API routes, no frontend) | `unit-tester`, `integration-tester` | `contract-tester`, `ui-tester`, `e2e-tester` |
| **API routes changed** (new/modified FastAPI endpoints) | `unit-tester`, `integration-tester`, `contract-tester` | `ui-tester` (unless frontend consumes the API) |
| **Frontend changes** (React components, TypeScript) | `unit-tester`, `ui-tester` | `contract-tester` (unless API contracts changed too) |
| **Event handlers changed** (consumers, producers, handlers) | `unit-tester`, `integration-tester`, `contract-tester` | `ui-tester` |
| **Full-stack feature** (API + data + events + frontend) | `unit-tester`, `integration-tester`, `contract-tester`, `e2e-tester` | — (propose all) |
| **Infrastructure only** (K8s, Pulumi, CI/CD) | Skip all testers — suggest infrastructure-specific validation instead | All |

**Filtering rationale:** The testing pyramid guides agent selection. Unit tests are almost always needed. Integration tests cover boundary interactions. Contract tests matter when API or event schemas are involved. E2E tests validate complete user journeys for full features. UI tests are relevant only when frontend changes exist. Over-proposing agents wastes effort; under-proposing misses coverage — so propose what the code warrants and let the user adjust.

#### Build Proposal Table

Follow [sdlc-shared/refs/propose-approve-execute.md](../sdlc-shared/refs/propose-approve-execute.md):

The **Skill to Invoke** column is mandatory — every agent must have a skill assignment. Use the Pyramid-Level Agent → Skill Mapping table from Step 3.6 as the authoritative reference.

```markdown
## Step 2: Proposed Tester Agents — Task T-{N}: {Task Title}

| # | Agent | Skill to Invoke | Task-Specific Action | Estimated Scope |
|---|-------|-----------------|----------------------|-----------------|
| 1 | `unit-tester` | `/test-unit` | {action tailored to this task} | M |
| 2 | `integration-tester` | `/test-Integration` | {action tailored to this task} | M |
| 3 | `contract-tester` | `/test-contract` | {action tailored to this task} | M |
```

Tailor the "Task-Specific Action" based on the implementation context. Examples:

- `unit-tester` (invokes `/test-unit`): "Write behavior-driven unit tests for the CreatePaymentFlow, PaymentValidator, and MoneyValueObject with edge cases for currency conversion and insufficient funds"
- `integration-tester` (invokes `/test-Integration`): "Write integration tests for PaymentRepository (Postgres persistence), PaymentGatewayAdapter (HTTP calls), and EventPublisher (payment events)"
- `contract-tester` (invokes `/test-contract`): "Validate POST /v1/payments and GET /v1/payments/{id} against the OpenAPI contract in specs/openapi/v1.yaml, including error response schemas"
- `e2e-tester` (invokes `/test-e2e`): "Write end-to-end tests for the complete payment flow: create payment → process → confirm → query status"
- `ui-tester` (invokes `/test-ui`): "Write Playwright tests for the payment form: input validation, submission, success/error states, and payment history display"

**Test infrastructure reference:** If Step 1 produced shared infrastructure, note it in the proposal header:

```markdown
**Shared test infrastructure available from Step 1:** {list of factories, fixtures, conftest components created}

All tester agents should use the shared infrastructure — do not recreate factories or fixtures.
```

#### Present Proposal and Await Approval

Present the table and wait for user response. The user can:
- **Approve** — proceed to dispatch
- **Remove agents** — by number (e.g., "remove 3" to skip contract tests)
- **Add agents** — by name (e.g., "also add the e2e-tester")
- **Modify actions** — change what a tester will focus on
- **Reject** — skip testing for now

Never dispatch agents without explicit approval.

### Step 7: Dispatch Approved Tester Agents

After approval, dispatch all approved tester agents via the Task tool in a **single message** with multiple tool calls for parallel execution.

Each agent receives a structured prompt that includes the mandatory skill to invoke:

```markdown
## Context

**Feature:** {feature-name}
**Feature Directory:** {feature-dir-path}
**Phase:** Testing — Step 2: Test Implementation
**Task:** T-{N} — {task title}

## Skill to Invoke

You MUST invoke the `/{writing-skill}` skill before starting your work. This skill defines the testing standards, patterns, and conventions for your pyramid level. Do not proceed without loading the skill first.

## Your Assignment

{Approved task-specific action from the proposal table}

## Artifacts to Read

- `{feature-dir}/README.md` — Feature inception document with vision and goals
- `{feature-dir}/prd.md` — Requirements with acceptance criteria to validate
- `{feature-dir}/lld.md` — Low-level design with contracts, data models, and specs
- `{feature-dir}/tasks-breakdown.md` — Full task details (read Task T-{N} section)
- `{feature-dir}/sdlc-log.md` — Check /implement entries for files to test

## Implementation Files to Test

{List of code files produced by /implement that need testing, extracted from sdlc-log.md or git status}

## Shared Test Infrastructure (from Step 1)

{If Step 1 produced infrastructure, list what's available:}
- Factories: {file paths and what models they cover}
- Fixtures: {conftest.py locations and what they provide}
- Test client: {if created, how to use it}

USE the shared infrastructure. Do NOT recreate factories, fixtures, or conftest configurations that already exist.

## Design Contracts to Test Against

{From lld.md — include relevant specs:}
- OpenAPI: {if API routes involved, reference the spec path}
- AsyncAPI: {if event handlers involved, reference the spec path}
- Data models: {if persistence involved, reference the schema definitions}

## Codebase Conventions

- Follow `.claude/rules/testing.md`, `.claude/rules/mocking.md`, `.claude/rules/factories.md`
- Use `lib-testing` utilities where available
- Test markers: `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.contract`, `@pytest.mark.e2e`
- Test style: AAA pattern, behavior-focused, refactor-resilient
- Use Polyfactory factories — never construct test data by hand
- Test file location: `tests/` directory mirroring source structure (unit/, integration/, contract/, e2e/)

## Definition of Done

- Tests cover the task's acceptance criteria from prd.md
- Tests validate behavior through public interfaces (not implementation details)
- Tests use shared infrastructure from Step 1 (factories, fixtures, conftest)
- Tests are properly marked with pytest markers
- Tests follow the testing pyramid: more unit tests, fewer integration, fewer e2e
- All tests pass when run locally
```

If >6 tester agents are approved, batch into groups of 6 per [sdlc-shared/refs/propose-approve-execute.md](../sdlc-shared/refs/propose-approve-execute.md):

1. Dispatch batch 1 (agents 1-6) in a single message
2. Wait for completion, present brief summary
3. Dispatch batch 2 with batch 1 outcomes as additional context
4. Repeat until all batches complete

### Step 8: Collect Results and Present Summary

After all agents complete, present an execution summary:

```markdown
## Testing — Execution Summary

**Task:** T-{N} — {task title}
**Mode:** {Validation Only | Mixed | Writing Only}

### Pyramid Placement Results (if Validation Only or Mixed mode)

| # | Test File | From → To | Agent | Skill Invoked | Status |
|---|-----------|-----------|-------|---------------|--------|
| 1 | `test_create_payment.py` | Unit → Integration | `integration-tester` | `/test-Integration` | ✅ Relocated |
| — | — | — | — | — | All tests correctly placed (if no relocations needed) |

### Validation Results (if Validation Only or Mixed mode)

| Pyramid Level | Agent | Skill Invoked | Verdict | Findings | Action Taken |
|---------------|-------|---------------|---------|----------|-------------|
| Unit | `unit-tests-reviewer` | `/review-unit-tests` | {PASS/FAIL} | {count} | {None / Refactored by `unit-tester` via `/test-unit`} |
| Integration | `integration-tests-reviewer` | `/review-integration-tests` | {PASS/FAIL} | {count} | {None / Refactored by `integration-tester` via `/test-Integration`} |
| Contract | `contract-tests-reviewer` | `/review-contract-tests` | {PASS/FAIL} | {count} | {None / Refactored by `contract-tester` via `/test-contract`} |

### Step 1: Test Infrastructure (if Writing Only or Mixed mode)
| Agent | Skill Invoked | Component | Status | Files Created |
|-------|---------------|-----------|--------|--------------|
| `python-implementer` | `/implement-python` | {component} | ✅ | {files} |

### Step 2: Test Implementation (if Writing Only or Mixed mode — missing pyramid levels only)
| Agent | Skill Invoked | Status | Tests Written | Files Created | Key Outcomes |
|-------|---------------|--------|--------------|--------------|--------------|
| `unit-tester` | `/test-unit` | ✅ Complete | {count} tests | {file list} | {summary — e.g., "12 unit tests covering CreatePaymentFlow, 3 edge cases for currency conversion"} |
| `integration-tester` | `/test-Integration` | ✅ Complete | {count} tests | {file list} | {summary} |
| `contract-tester` | `/test-contract` | ✅ Complete | {count} tests | {file list} | {summary} |

### Test Coverage Summary
- **Unit tests:** {count} tests across {count} test files {validated/written/refactored}
- **Integration tests:** {count} tests across {count} test files {validated/written/refactored}
- **Contract tests:** {count} tests across {count} test files {validated/written/refactored}
- **E2E tests:** {count} tests across {count} test files (if applicable) {validated/written/refactored}
- **UI tests:** {count} tests across {count} test files (if applicable) {validated/written/refactored}

### Artifacts Produced
- **Infrastructure:** {bulleted list of conftest.py and factory files}
- **Test files:** {bulleted list of all test files created or refactored}
- **Validation verdicts:** {pyramid levels validated and their outcomes}

### Next Steps
Run `/review {feature-identifier}` to review the implementation and tests, or run `uv run pytest -m unit` to execute the tests locally.
```

If any agent failed, report the failure clearly and ask the user whether to retry, skip, or adjust and re-dispatch. Do not silently drop failed agents.

### Step 9: Write SDLC Log Entry

After execution completes (whether agents dispatched, gate block, or skip), append an entry to `{feature-dir}/sdlc-log.md` following [sdlc-shared/refs/sdlc-log-format.md](../sdlc-shared/refs/sdlc-log-format.md):

```markdown
## [YYYY-MM-DD HH:MM] — /test — Testing

- **Task:** {task identifier and title, or "N/A"}
- **Mode:** {Validation Only | Mixed | Writing Only}
- **Agents dispatched:** {list — e.g., "unit-tests-reviewer, contract-tests-reviewer (validation) + integration-tester (relocation: unit→integration) + unit-tester (refactoring) + integration-tester (writing) + python-implementer (Step 1: infrastructure)"}
- **Skills invoked:** {skills used — e.g., "review-unit-tests, review-contract-tests, test-unit, test-integration, implement-python"}
- **Relocations:** {if any — e.g., "2 tests relocated: test_create_payment.py (unit→integration), test_payment_validator.py (integration→unit)" or "None — all tests correctly placed"}
- **Artifacts produced:** {files created/modified — relocation results + validation verdicts + refactored files + infrastructure files from Step 1 + new test files from Step 2}
- **Outcome:** {what was accomplished — e.g., "Relocated 2 misplaced tests. Validated 3 pyramid levels (unit: PASS, integration: FAIL, contract: PASS). Refactored integration tests (2 findings addressed). Wrote 4 new e2e tests. All pyramid levels now correctly placed, covered, and compliant."}
- **Findings:** {any issues, gaps, failing tests — or "None"}
```

If `sdlc-log.md` doesn't exist, create it with the header first (see the shared ref for the header format).

---

## Acceptance Criteria Coverage

This skill addresses the following scenarios from FR-11:

### FR-11: `/test` — Testing Across the Pyramid

| # | Scenario | Covered By |
|---|----------|------------|
| 1 | Implementation code exists → analyze for shared test infrastructure, propose Step 1: Test Infrastructure | Step 4 — analyzes code patterns for infrastructure needs; Step 5 — proposes and executes infrastructure setup |
| 2 | User approves Step 1 → infrastructure created, then proposes Step 2 with dynamically discovered tester agents | Step 5 — creates infrastructure; Step 6 — discovers `*-tester.md` agents, builds context-filtered proposal |
| 3 | User approves Step 2 → tester agents execute in parallel using shared infrastructure from Step 1 | Step 7 — dispatches all approved agents in single message; agent prompts reference Step 1 infrastructure |
| 4 | Backend logic only, no API changes → skip contract-tester and ui-tester (user can add) | Step 6 — filtering table excludes contract-tester and ui-tester for backend-only tasks |
| 5 | New tester agents added in future → auto-appear in proposals | Step 6 — dynamic scan of `.claude/agents/*-tester.md`, no hardcoded list |
| 6 | /test completes → append entry to sdlc-log.md | Step 9 — log entry appended after every execution path |
| 7 | Tests already exist for all relevant pyramid levels → validate with review skills, refactor if failing | Step 3.5 detects existing tests → Step 3.6 dispatches review agents → Step 3.7 refactors failing tests |
| 8 | Tests exist for some pyramid levels, missing for others → validate existing + write missing | Step 3.5 determines Mixed mode → Steps 3.6-3.7 validate/refactor existing → Steps 4-7 write missing |
| 9 | Existing tests pass all review validations → no refactoring, skip to summary | Step 3.6 — all review agents return PASS → skip to Step 8 (Validation Only) or Steps 4-7 (Mixed) |
| 10 | Each pyramid level validated by its matching review skill | Step 3.6 — unit→`review-unit-tests`, integration→`review-integration-tests`, contract→`review-contract-tests`, e2e→`review-e2e-tests`, ui→`review-ui-tests` |
| 11 | Each failing pyramid level refactored by its matching writing skill | Step 3.7 — unit→`test-unit`, integration→`test-Integration`, contract→`test-contract`, e2e→`test-e2e`, ui→`test-ui` |
| 12 | Existing tests at wrong pyramid level detected and relocated | Step 3.55 — analyzes imports, fixtures, assertions, markers → builds misplacement report → proposes relocations with target writing skill |
| 13 | Unit test with real DB/HTTP relocated to integration | Step 3.55 — signal matrix detects `db_session` fixture or real HTTP client in unit test → proposes relocation to integration via `integration-tester` |
| 14 | Integration test with all deps mocked relocated to unit | Step 3.55 — signal matrix detects all `mocker.patch` and zero real I/O → proposes relocation to unit via `unit-tester` |
| 15 | Schema validation tests relocated to contract level | Step 3.55 — signal matrix detects `jsonschema.validate` or Pact matchers in unit/integration test → proposes relocation to contract via `contract-tester` |
| 16 | Coverage matrix updated after relocation before validation | Step 3.55 — after relocation agents complete, matrix reflects new file locations; mode recalculated; Step 3.6 validates at correct levels |
| 17 | No relocations when tests are correctly placed | Step 3.55 — when all signals match markers, reports "All tests correctly placed" and proceeds to Step 3.6 |

---

## Decision Tree (Full)

```
/test invoked
    |
    v
Resolve Feature Directory (refs/feature-resolution.md)
    |
    |-- Argument provided -> resolve path
    |-- No argument -> present selection list
    |-- No match -> error + selection list
    +-- Create new -> assign sequence, create directory
    |
    v
Phase Gate: Implementation code exists? (refs/phase-gating.md)
    |
    |-- No tasks-breakdown.md -> Block: "Run /tasks-breakdown first, then /implement."
    |-- No evidence of implementation -> Block: "Run /implement first."
    |          -> END
    |
    v
Identify implemented tasks from tasks-breakdown.md + sdlc-log.md
    |
    |-- Multiple tasks implemented?
    |       |
    |       v
    |   Present task list -> user selects which to test
    |
    |-- Single task -> proceed with that task
    |
    v
Read implementation code + design artifacts (lld.md, prd.md)
    |
    v
=== STEP 3.5: DETECT EXISTING TESTS ===
    |
    v
Scan test directories for existing test files per pyramid level
Build coverage matrix (Unit / Integration / Contract / E2E / UI)
    |
    v
Determine mode:
    |
    |-- ALL relevant levels have tests?  -> VALIDATION ONLY mode
    |-- SOME levels have tests?          -> MIXED mode
    |-- NO tests exist?                  -> WRITING ONLY mode -> skip to Step 1
    |
    v (if Validation Only or Mixed — existing tests found)
=== STEP 3.55: PYRAMID PLACEMENT ANALYSIS ===
    |
    v
Analyze each test file for misplacement signals:
  - Import analysis (DB sessions, HTTP clients, Playwright, schema validators)
  - Fixture analysis (db_session, httpx_mock, @mock_aws, @respx.mock)
  - Assertion analysis (DB state, response shapes, domain logic, schema compliance)
  - Marker vs. signal consistency check
    |
    v
Build misplacement report
    |
    |-- No misplaced tests? -> "All tests correctly placed" -> proceed to Step 3.6
    +-- Misplaced tests found?
            |
            v
        Present relocation proposal (From → To with tester agent + writing skill)
            |
            |-- Approved -> Dispatch relocation agents in parallel
            |       |
            |       v
            |   Each agent: read misplaced test → rewrite at target level → delete original
            |       |
            |       v
            |   Update coverage matrix (levels may gain/lose tests)
            |   Recalculate mode if coverage changed
            |
            |-- Skipped -> proceed with current placement
            +-- Modified -> adjust relocations, dispatch
    |
    v
=== STEP 3.6: VALIDATE EXISTING TESTS ===
    |
    v
Propose review agents (review-unit-tests, review-integration-tests, etc.)
    |
    v
Dispatch review agents in parallel -> collect verdicts
    |
    |-- All PASS?
    |       |
    |       |-- VALIDATION ONLY mode -> Skip to Step 8 (summary) -> END
    |       +-- MIXED mode -> proceed to Steps 4-7 for MISSING levels
    |
    +-- Some FAIL ->
            |
            v
        === STEP 3.7: REFACTOR FAILING TESTS ===
            |
            v
        Propose tester agents for FAIL levels (unit-tester w/ test-unit skill, etc.)
            |
            v
        Dispatch refactoring agents with review findings -> present summary
            |
            |-- VALIDATION ONLY mode -> Skip to Step 8 (summary) -> END
            +-- MIXED mode -> proceed to Steps 4-7 for MISSING levels
    |
    v
=== STEP 1: TEST INFRASTRUCTURE ===
    |
    v
Analyze implementation for shared infrastructure needs
    |
    |-- Infrastructure needed?
    |       |
    |       |-- Yes -> Present infrastructure proposal
    |       |       |
    |       |       |-- Approved -> Dispatch infrastructure agent
    |       |       |       |
    |       |       |       v
    |       |       |   Wait for completion -> present summary
    |       |       |
    |       |       |-- Skipped -> proceed without infrastructure
    |       |       +-- Modified -> update and dispatch
    |       |
    |       +-- No -> "No infrastructure needed. Proceeding to Step 2."
    |
    v
=== STEP 2: TESTER AGENT DISCOVERY ===
    |
    v
Discover *-tester.md agents (refs/agent-discovery.md)
    |
    v
Filter agents by implementation context (ONLY for MISSING pyramid levels):
    |-- Backend only -> unit-tester, integration-tester
    |-- API changes -> + contract-tester
    |-- Frontend changes -> + ui-tester
    |-- Full feature -> + e2e-tester
    |-- Infrastructure only -> skip testers, suggest validation
    |
    v
Build proposal table with task-specific actions
    |
    v
Present proposal -> await user approval
    |
    |-- Approved -> proceed to dispatch
    |-- Modified -> update proposal, re-present
    +-- Rejected -> END (log skip)
    |
    v
Dispatch tester agents in parallel (batch if >6)
    |
    v
Collect results -> present execution summary
    |
    v
Agent failures?
    |-- Yes -> report failures, ask: retry / skip / adjust
    +-- No  -> proceed
    |
    v
Append SDLC Log Entry (refs/sdlc-log-format.md)
    |
    v
END — "Run /review for this task"
```

---

## Patterns

### Do

- **Always include "Skill to Invoke" in every agent proposal table** — this is mandatory and non-negotiable. Every agent dispatched by `/test` must have a skill assignment visible to the user before approval. Use the Pyramid-Level Agent → Skill Mapping table as the authoritative reference. An agent without a skill is never dispatched.
- **Always include "## Skill to Invoke" in every agent dispatch prompt** — tell the agent which skill to invoke and instruct it to load the skill before starting work. The agent must invoke the skill, not just "follow" it.
- **Always detect existing tests first** (Step 3.5) before proposing to write new ones — never overwrite or duplicate tests that already exist
- **Always analyze pyramid placement** (Step 3.55) before validating — a test at the wrong level will fail validation for the wrong reasons; fix placement first, then validate quality
- **Use all four signal analyses** (imports, fixtures, assertions, markers) to determine misplacement — no single signal is conclusive on its own; the combination determines the correct level
- **Relocate misplaced tests using the target level's writing skill** — a unit test moving to integration should be rewritten by `integration-tester` using `test-Integration` standards, not just moved to a different directory
- **Preserve all behavioral coverage during relocation** — the rewritten test must validate the same behaviors as the original, translated to the target level's assertion style
- **Update the coverage matrix after relocation** — levels may gain or lose tests, which changes the mode calculation for subsequent steps
- **Validate existing tests against the matching review skill** — `review-unit-tests` for unit, `review-integration-tests` for integration, `review-contract-tests` for contract, `review-e2e-tests` for e2e, `review-ui-tests` for UI
- **Refactor non-compliant tests using the matching writing skill** — `test-unit` for unit, `test-Integration` for integration, `test-contract` for contract, `test-e2e` for e2e, `test-ui` for UI
- **Pass review findings as structured context** to refactoring agents — they need to know exactly what to fix, not just "make it better"
- Always execute Step 1 (infrastructure) before Step 2 (test agents) — agents that share infrastructure produce consistent, non-conflicting tests
- Analyze the actual implementation code before proposing agents — the code patterns (routes, repos, handlers, models) determine which testers are relevant
- Include design contracts (OpenAPI, AsyncAPI, data models from lld.md) as context for testers — tests validate against specs, not just current behavior
- Reference prd.md acceptance criteria in agent prompts — tests should prove requirements are met
- Explicitly tell Step 2 agents to USE the shared infrastructure from Step 1 — without this, agents will reinvent fixtures and factories
- Follow the testing pyramid: more unit tests, fewer integration, fewer e2e — the proposal table reflects this with scope estimates
- Present the infrastructure analysis transparently — the user should understand why each component is recommended
- In Mixed mode, **only propose writing agents for missing pyramid levels** — don't re-create tests that already exist and passed validation

### Don't

- **Propose or dispatch an agent without a "Skill to Invoke"** — every agent in every proposal table must have an explicit skill. If you can't determine the skill, the agent shouldn't be proposed. This applies to all steps: relocation, validation, refactoring, infrastructure, and writing.
- **Skip pyramid placement analysis** (Step 3.55) — validating a misplaced test against the wrong level's standards produces misleading results; always check placement before validation
- **Just move test files to a different directory** — relocation means rewriting the test to follow the target level's standards, not just changing the file path and marker
- **Rely on a single signal for misplacement** — a `db_session` import alone doesn't prove misplacement; combine import, fixture, assertion, and marker analysis for accurate detection
- **Lose behavioral coverage during relocation** — the rewritten test must validate the same behaviors; if an assertion can't translate to the target level, flag it rather than silently dropping it
- **Skip the existing test detection step** — always check before proposing to write new tests
- **Re-write tests that already pass validation** — if `review-unit-tests` says PASS, don't dispatch `unit-tester` to rewrite them
- **Validate without the matching review skill** — each pyramid level has a specific review skill; don't use a generic review
- **Refactor without passing review findings** — refactoring agents need the specific findings (severity, location, remediation) to know what to fix
- Skip the phase gate — writing tests for code that doesn't exist yet is impossible
- Dispatch agents without user approval — the propose-approve-execute pattern is non-negotiable
- Hardcode the agent list — always scan `.claude/agents/` dynamically so new tester agents are automatically discovered
- Propose all tester agents regardless of context — backend-only tasks don't need UI testers, and pure utility code doesn't need contract testers
- Dispatch Step 2 agents before Step 1 completes — agents need the shared infrastructure to exist before they write tests
- Write implementation code — that's `/implement`'s job
- Add observability instrumentation — that's `/observe`'s job
- Write review verdicts — that's `/review`'s job
- Produce design artifacts — that's `/design-system` and `/design-lld`'s job
