---
name: verify
description: |
  Systematically verify that a completed task meets its specification by executing every check
  defined in the task's dedicated file (tasks/{nnn}-{task-name}.md) — running "How to Verify" steps,
  testing each "Expected Behavior", validating "Boundary Conditions" and "Invariants", confirming
  sub-task completion, and ensuring all "Definition of Done" criteria are met. This is the behavioral
  correctness gate in the implementation loop (implement -> optimize -> observe -> test -> verify ->
  review -> refactor) that catches gaps between what was specified and what was actually delivered.
  It runs right after /test because there's no point reviewing or refactoring code that doesn't
  work — verification confirms the implementation actually delivers what the task promised before
  investing time in code quality. Produces a structured verification report with per-check
  PASS/FAIL verdicts and evidence.
  Use when completing a task, running `/verify`, or when the user says "verify", "verify task",
  "check if done", "is the task done", "validate task", "QA this", "acceptance check",
  "run verification", "did we meet the spec", "check definition of done", "verify the work",
  "manual QA", "acceptance testing", "are we done with the task", "check expected behaviors",
  "validate boundaries", "run the verify steps", "final check", "gate check", "check invariants",
  "verify completion", "task QA", or "end of loop check". This skill requires the task breakdown
  (tasks-breakdown.md + tasks/ directory) — it blocks if no task breakdown exists.
---

# /verify — Task Verification Gate

> Execute every verification criterion from the task breakdown — commands, expected behaviors,
> boundary conditions, invariants, sub-task completion, and Definition of Done — to produce a
> concrete PASS/FAIL verdict with evidence before marking a task complete.

## Quick Reference

| Aspect | Details |
|--------|---------|
| **Phase** | Verify (per-task, behavioral correctness gate — after /test, before /review) |
| **Gate** | Task breakdown must exist: `tasks-breakdown.md` (overview) + `tasks/{nnn}-{task-name}.md` (per-task details) |
| **Reads** | `tasks-breakdown.md` (task list + overview), `tasks/{nnn}-{task-name}.md` (selected task spec), `prd.md`, `lld.md`, actual source code and artifacts |
| **Produces** | Appends verification report to `tasks/{nnn}-{task-name}.md` |
| **Shared Refs** | `sdlc-shared/refs/feature-resolution.md`, `sdlc-shared/refs/phase-gating.md`, `sdlc-shared/refs/sdlc-log-format.md` |
| **Deep Refs** | `refs/check-strategies.md` |

### Where This Fits in the Implementation Loop

```
/implement -> /optimize -> /observe -> /test -> /verify -> /review -> /refactor
                                                  ^ YOU ARE HERE
```

After `/test` writes automated tests, `/verify` checks whether the implementation actually
delivers what the task breakdown promised. This happens **before** `/review` and `/refactor`
because there's no point reviewing code quality or refactoring code that doesn't work yet.
If verification fails, you go back to `/implement` to fix the behavior — only once the task
is verified do you invest time in code review and refactoring.

The distinction from `/test` is important: `/test` writes automated tests (unit, integration,
contract) that validate code correctness and guard against regressions. `/verify` executes
the manual and automated checks defined in the task breakdown to confirm the task delivers
what it promised — behavioral acceptance against the specification. Tests are permanent
regression guards; verification is a one-time acceptance gate per task.

The distinction from `/review` is equally important: `/review` evaluates code quality,
patterns, and maintainability. `/verify` evaluates whether the code *works as specified*.
Broken code shouldn't be reviewed for quality — fix it first, then review it.

---

## Core Workflow

### Step 1: Resolve Feature Directory

Follow [sdlc-shared/refs/feature-resolution.md](../sdlc-shared/refs/feature-resolution.md):

1. If the user passed an argument (e.g., `/verify 002-notification`) — resolve to the matching directory
2. If no argument — present feature selection list
3. If no match — report error and present selection list

The resolved path becomes `{feature-dir}` for all subsequent steps.

### Step 2: Phase Gate — Require Task Breakdown

```
Check: {feature-dir}/tasks-breakdown.md exists and is non-empty?
  AND {feature-dir}/tasks/ directory exists with .md files?
  |-- Both exist -> Proceed to Step 3
  |-- Only tasks-breakdown.md -> Proceed to Step 3 (legacy single-file format)
  +-- Neither -> Block:
            "No task breakdown found in {feature-dir}/."
            "Run `/tasks-breakdown` first to produce the breakdown."
            -> END
```

### Step 3: Parse Task List and Present Selection

Read `{feature-dir}/tasks-breakdown.md` to get the task overview (summary, tiers, dependencies), then scan `{feature-dir}/tasks/` for individual task files. Present:

```markdown
## Task List — {Feature Name}

| # | Task | Complexity | Status | Dependencies |
|---|------|-----------|--------|--------------|
| T-1 | {title} | M | ✅ Complete | None |
| T-2 | {title} | L | ✅ Verified | None |
| T-3 | {title} | M | 🔄 In Progress | Hard: T-1 |

**Select a task to verify** (by number or name).
```

Status values:
- `⬜ Pending` — not yet implemented
- `🔄 In Progress` — partially implemented
- `✅ Complete` — implemented but not yet verified
- `✅ Verified` — passed verification

If a task is `⬜ Pending`, warn that verification before implementation doesn't make sense — but
let the user proceed if they want a "dry run" to understand what will be checked.

### Step 4: Read Task Verification Spec

Read the selected task's dedicated file from `{feature-dir}/tasks/{nnn}-{task-name}.md`. Each
task file is self-contained with all verification dimensions. If the `tasks/` directory doesn't
exist (legacy single-file format), fall back to reading the task entry from `tasks-breakdown.md`.

Extract six verification dimensions from the task file:

| Dimension | Source in task file | What it specifies |
|-----------|----------------------------|-------------------|
| **How to Verify** | `## How to Verify` section | Concrete runnable steps — bash commands, curl calls, UI walkthroughs with expected outputs |
| **Expected Behaviors** | `## Expected Behaviors` section | Happy path input→output, error path input→output, state side effects |
| **Boundary Conditions** | `## Boundary Conditions` section | Edge cases, limits, constraint violations derived from contracts and domain rules |
| **Invariants** | `## Invariants` section | Postconditions that always hold after the task's code executes |
| **Sub-Tasks** | `## Sub-Tasks` checklist | Individual work items (`- [ ]` / `- [x]`) within the task |
| **Definition of Done** | `## Definition of Done` section | Files created, contracts satisfied, acceptance criteria met |

Not every task has every dimension. If a section is missing from the task file, skip it —
but note it as `SKIPPED (not specified)` in the report.

> **Context efficiency:** You only need to read the single task file being verified — not the
> full `tasks-breakdown.md` or other task files. The overview was already read in Step 3 for
> the task list and dependency context.

### Step 5: Read Design Context

Read design artifacts for reference — they provide the "why" behind each check:

1. `{feature-dir}/prd.md` — acceptance criteria that the task maps to
2. `{feature-dir}/lld.md` — contracts, data models, API specs that the task implements against

Also read:
3. `{feature-dir}/sdlc-log.md` — to understand what loop phases already ran (was `/test` run? `/review`?)
4. `{feature-dir}/reviews/{task-name}/` — review verdicts, if they exist, to check for unresolved findings

This context helps interpret ambiguous checks and surface issues the breakdown didn't anticipate.

### Step 6: Present Verification Plan

Before executing, present the full verification plan so the user understands what will be
checked and can adjust:

```markdown
## Verification Plan — Task T-{N}: {Title}

### 1. How to Verify ({count} checks)
| # | Check | Method |
|---|-------|--------|
| V-1 | `curl -X POST ...` → expect 201 | Automated (run command) |
| V-2 | Open localhost:3000/products → confirm list | Automated (Playwright) |

### 2. Expected Behaviors ({count} checks)
| # | Category | Check |
|---|----------|-------|
| B-1 | Happy path | POST valid product → 201 + response shape |
| B-2 | Error path | POST empty name → 422 validation error |
| B-3 | Side effect | After POST → row in products table |

### 3. Boundary Conditions ({count} checks)
| # | Check |
|---|-------|
| BC-1 | Name at max length (255 chars) → accepted |
| BC-2 | Price of 0 → rejected |

### 4. Invariants ({count} checks)
| # | Invariant |
|---|-----------|
| I-1 | Every product has non-null id, name, price, created_at |

### 5. Sub-Tasks ({done}/{total} complete)
| # | Sub-Task | Status |
|---|----------|--------|
| ST-1 | Data: Product table migration | ✅ |
| ST-2 | Logic: Product aggregate | ✅ |

### 6. Definition of Done ({count} criteria)
| # | Criterion | Check Method |
|---|-----------|-------------|
| D-1 | Files: services/products/.../create_product.py | File exists check |
| D-2 | Contract: POST /v1/products matches OpenAPI | Schema comparison |
| D-3 | Acceptance: Products can be created via API | Behavioral check |

**Total: {N} checks** ({cli} CLI-automated, {playwright} Playwright-automated)

**Proceed with verification?** You can:
- **Run all** — execute all checks (CLI commands, API calls, Playwright UI checks)
- **Run subset** — specify which sections or check numbers to run
- **Dry run** — show what would be checked without executing
- **Adjust** — modify checks before running
```

### Step 7: Execute Verification

Execute each check and record the result. The approach depends on the check type:

#### Automated Checks (Claude can execute directly)

These are checks where Claude can run a command, inspect a file, or evaluate a condition
programmatically. Execute them and record the output as evidence.

**How to Verify steps:**
- Run each bash command, curl call, or script
- Compare actual output against the expected output stated in the breakdown
- Verdict: PASS if output matches expectation, FAIL if it doesn't

**Expected Behaviors:**
- For API behaviors: construct and execute the request, compare response status and body
- For state side effects: run the mutation, then query the state to confirm the change
- For error paths: send the invalid input, confirm the error response matches

**Boundary Conditions:**
- Construct inputs at the boundary values specified in the breakdown
- Execute them and confirm the system accepts/rejects as specified

**Invariants:**
- After running the verification steps above, query the system state
- Confirm each invariant holds (e.g., query the DB to verify all products have non-null fields)

**Sub-Task completion:**
- Check if the sub-task checkbox is marked `[x]` in the task file (`tasks/{nnn}-{task-name}.md`)
- For file-creation sub-tasks: verify the file exists via Glob
- For code sub-tasks: verify the expected symbols exist (class, function, module)

**Definition of Done — Files:**
- Use Glob to verify each listed file exists
- Optionally read key files to confirm they're non-trivial (not empty stubs)

**Definition of Done — Contracts:**
- Read the implemented code and compare against the OpenAPI/AsyncAPI spec in lld.md
- Check that endpoint paths, methods, request/response schemas align

#### Writing Verification Scripts

When a check is too complex for a single command — for example, validating a data model
against an LLD spec, or testing multiple boundary conditions in sequence — write a temporary
verification script:

```python
# {feature-dir}/verifications/{task-name}/verify_{check_name}.py
"""Verification script for {check description}. Auto-generated by /verify."""
```

Run the script, capture the output, and include the result in the report. Leave the script
in the verifications directory so it can be re-run later.

#### UI & Visual Checks (Playwright-automated)

Checks that involve UI walkthroughs, visual verification, or UX assessment are automated
using Playwright — either via the Playwright MCP tools or by writing Playwright test scripts.
These are NOT delegated to the human; they are executed programmatically.

**Strategy selection:**

| Check complexity | Approach |
|-----------------|----------|
| Single page load + element check | Playwright MCP tools (navigate, snapshot, click) |
| Multi-step user journey | Write a Playwright verification script |
| Visual comparison | Playwright MCP screenshot + snapshot inspection |
| Form interaction + validation | Playwright MCP fill_form + snapshot to confirm |

> **Important distinction:** Verification scripts are ephemeral QA artifacts stored in
> `verifications/`, not codebase tests in `tests/`. They validate task completion, not
> long-term regression. However, they follow the same Playwright best practices as the
> `/test-ui` skill to ensure reliable, non-flaky checks.

**Playwright best practices (aligned with `/test-ui` and `/review-ui-tests`):**

Follow the same locator priority hierarchy and assertion patterns used across the codebase:

| Priority | Locator | When to use |
|----------|---------|-------------|
| 1 | `get_by_role()` | Buttons, links, headings, form controls |
| 2 | `get_by_label()` | Form inputs with labels |
| 3 | `get_by_placeholder()` | Inputs with placeholder text |
| 4 | `get_by_text()` | Visible text content |
| 5 | `get_by_test_id()` | When semantics are unavailable |
| 6 | `locator("[attr]")` | Last resort |

Rules that apply equally to verification scripts:
- Use web-first assertions (`expect().to_be_visible()`) — they auto-retry
- Never use `time.sleep()` or `page.wait_for_timeout()` — use condition-based waits
- Never use CSS class selectors (`.btn-primary`, `.card--active`)
- Never use XPath or structural selectors (`//div[3]/form/button`)
- Never use immediate assertions (`assert element.is_visible()`) — use `expect()`
- Use `page.expect_response()` when clicking triggers an API call

**Using Playwright MCP tools (preferred for simple checks):**

Execute UI checks step-by-step using Playwright MCP. The MCP tools use the accessibility
tree via `browser_snapshot`, which naturally aligns with semantic locator best practices:

1. `browser_navigate` to the target URL
2. `browser_snapshot` to capture the accessibility tree — verify elements by role and name
3. `browser_click` using role-based refs from the snapshot (e.g., click "Create" button)
4. `browser_fill_form` to populate form fields
5. `browser_snapshot` again to verify the resulting state
6. `browser_take_screenshot` if visual evidence is needed for the report

Example flow for a "Create Product" check:

```
1. browser_navigate → http://localhost:3000/products
2. browser_snapshot → verify button[name="Create"] exists in accessibility tree
3. browser_click → ref from snapshot for "Create" button
4. browser_fill_form → fill by label: Name="Widget", Price="9.99"
5. browser_click → ref from snapshot for "Submit" button
6. browser_wait_for → wait for navigation or network idle
7. browser_snapshot → verify "Widget" appears in product list, success toast visible
8. Record PASS/FAIL based on whether expected elements appear in the snapshot
```

**Writing Playwright verification scripts (for complex journeys):**

When a UI check involves multiple steps, conditional logic, or needs to be re-run.
Use `sync_api` (not async) since these are standalone verification scripts, not pytest tests:

```python
# {feature-dir}/verifications/{task-name}/verify_ui_{check_name}.py
"""Playwright UI verification for {check description}. Auto-generated by /verify."""
from playwright.sync_api import sync_playwright, expect

def verify():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()

        # Navigate and verify initial state
        page.goto("http://localhost:3000/products")
        expect(page.get_by_role("button", name="Create")).to_be_visible()

        # Interact using semantic locators (get_by_role, get_by_label)
        page.get_by_role("button", name="Create").click()
        page.get_by_label("Name").fill("Widget")
        page.get_by_label("Price").fill("9.99")

        # Wait for API response before asserting outcome
        with page.expect_response("**/api/v1/products") as response_info:
            page.get_by_role("button", name="Submit").click()

        assert response_info.value.ok

        # Verify outcome with web-first assertions (auto-retry)
        expect(page.get_by_text("Widget")).to_be_visible()
        expect(page.get_by_text("Product created")).to_be_visible()

        browser.close()
        print("[PASS] Product creation UI flow")

if __name__ == "__main__":
    verify()
```

Run the script, capture output, and include the result in the report. Leave the script
in the verifications directory for re-runs.

**Error path UI checks:**

Verify error states through Playwright — submit invalid inputs and confirm the UI
shows appropriate validation messages:

```
1. browser_navigate → http://localhost:3000/products/create
2. browser_snapshot → verify form is rendered
3. browser_click → "Submit" button (without filling required fields)
4. browser_snapshot → verify validation error text visible by role/text, not CSS class
5. Record PASS if error message visible, FAIL if form submitted or no error shown
```

**When Playwright can't reach the UI:**

If the UI is not running or not accessible (e.g., no frontend for this task, SSR-only,
or environment limitations):
1. Mark UI checks as SKIPPED with reason "UI not available"
2. Fall back to API-level verification if the same behavior can be checked via endpoints
3. Note in the report that UI verification was not performed

### Step 8: Present Verification Results

After all checks complete, present a structured summary:

```markdown
## Verification Results — Task T-{N}: {Title}

### Summary
| Dimension | Checks | Passed | Failed | Skipped |
|-----------|--------|--------|--------|---------|
| How to Verify | 4 | 3 | 1 | 0 |
| Expected Behaviors | 6 | 6 | 0 | 0 |
| Boundary Conditions | 5 | 4 | 0 | 1 |
| Invariants | 2 | 2 | 0 | 0 |
| Sub-Tasks | 3/3 | 3 | 0 | 0 |
| Definition of Done | 4 | 4 | 0 | 0 |
| **Total** | **24** | **22** | **1** | **1** |

### Failed Checks
| # | Check | Expected | Actual | Evidence |
|---|-------|----------|--------|----------|
| V-3 | `curl POST /v1/products {"name":""}` → 422 | 422 with validation error | 500 Internal Server Error | Response body: {"detail": "Internal Server Error"} |

### Skipped Checks
| # | Check | Reason |
|---|-------|--------|
| BC-4 | Concurrent duplicate submission | Requires multi-client setup not available locally |

### Passed Checks (collapsed)
<details>
<summary>22 checks passed — expand for details</summary>

| # | Check | Evidence |
|---|-------|----------|
| V-1 | POST valid product → 201 | Response: {"id": "...", "name": "Widget", ...} |
| ...
</details>
```

### Step 9: Determine Verdict

```
All checks passed (no failures)?
    |
    |-- Yes, zero failures -> PASS
    |       "Task T-{N} verification: PASS. All {N} checks satisfied."
    |
    |-- Some failures but non-blocking -> PARTIAL
    |       "Task T-{N} verification: PARTIAL. {N} checks passed, {M} failed."
    |       Present the failures and ask:
    |       "These failures may indicate bugs or missing implementation.
    |        Options:
    |        1. Accept — mark task as verified despite failures (with notes)
    |        2. Fix — re-enter the implementation loop to address failures
    |        3. Defer — log failures as known issues for a follow-up task"
    |
    +-- Critical failures -> FAIL
            "Task T-{N} verification: FAIL. {M} critical checks failed."
            "Re-enter the implementation loop to fix these issues before the task
             can be marked complete."
            Suggest which loop phase to re-enter based on the failure type:
            - Missing/wrong behavior → /implement
            - Performance issue → /optimize
            - Missing instrumentation → /observe
            - Missing/failing tests → /test
            Once verified, the task proceeds to /review and /refactor.
```

**What makes a failure "critical"?**
- A "How to Verify" step that fails (these are the task's primary acceptance checks)
- A happy-path Expected Behavior that fails (the core use case doesn't work)
- A Definition of Done criterion not met (files missing, contracts violated)

**What's "non-blocking"?**
- A boundary condition edge case that fails
- An invariant that's partially satisfied
- A skipped check due to environment limitations
- An error-path behavior that returns a different error format than specified

### Step 10: Append Verification Report to Task File

The verification report is appended directly to the task file `{feature-dir}/tasks/{nnn}-{task-name}.md` — keeping everything about a task in one place.

Append the following section at the end of the task file:

```markdown
---

## Verification Report

**Date:** {YYYY-MM-DD}
**Verdict:** {PASS | PARTIAL | FAIL}
**Checks:** {passed}/{total} passed, {failed} failed, {skipped} skipped

### Summary

{1-2 sentence summary of the verification outcome}

### How to Verify Results

| # | Check | Verdict | Evidence |
|---|-------|---------|----------|
| V-1 | {check description} | PASS | {output or observation} |
| V-2 | {check description} | FAIL | Expected: {X}, Actual: {Y} |

### Expected Behaviors Results

| # | Category | Behavior | Verdict | Evidence |
|---|----------|----------|---------|----------|
| B-1 | Happy path | {description} | PASS | {evidence} |
| B-2 | Error path | {description} | FAIL | {evidence} |

### Boundary Conditions Results

| # | Condition | Verdict | Evidence |
|---|-----------|---------|----------|
| BC-1 | {description} | PASS | {evidence} |

### Invariants Results

| # | Invariant | Verdict | Evidence |
|---|-----------|---------|----------|
| I-1 | {description} | PASS | {evidence} |

### Sub-Tasks Completion

| # | Sub-Task | Complete |
|---|----------|----------|
| ST-1 | {description} | Yes |

### Definition of Done Results

| # | Criterion | Met | Evidence |
|---|-----------|-----|----------|
| D-1 | {description} | Yes | {evidence} |

### Failures & Recommendations

{For each failure: what failed, why it likely failed, and which implementation loop
phase should address it. "None" if all passed.}

### Verification Scripts

{List of any scripts written during verification, with their paths, so they can be
re-run after fixes. "None" if no scripts were needed.}
```

Additionally:
- Update `{feature-dir}/tasks-breakdown.md` — mark the task as verified in the overview

On FAIL verdict:
- Still append the verification report to the task file (for reference when fixing)
- Do NOT mark the task as verified in the overview
- The task remains in its current status until re-verified after fixes

On re-verification (after fixes):
- Replace the existing `## Verification Report` section in the task file with the new results
- Add a note: `**Previous verification:** {date} — {verdict}`

### Step 11: Write SDLC Log Entry

Append to `{feature-dir}/sdlc-log.md` per [sdlc-shared/refs/sdlc-log-format.md](../sdlc-shared/refs/sdlc-log-format.md):

```markdown
## [YYYY-MM-DD HH:MM] — /verify — Verification

- **Task:** T-{N} — {task title}
- **Agents dispatched:** None (direct verification)
- **Skills invoked:** verify
- **Artifacts produced:** Verification report appended to tasks/{nnn}-{task-name}.md
- **Outcome:** {verdict} — {passed}/{total} checks passed, {failed} failed, {skipped} skipped.
  {1-sentence summary}
- **Findings:** {key failures or "All checks passed"}
```

---

## Decision Tree

```
/verify invoked
    |
    v
Resolve Feature Directory (sdlc-shared/refs/feature-resolution.md)
    |
    v
Phase Gate: tasks-breakdown.md + tasks/ exist?
    |
    |-- No -> Block: "Run /tasks-breakdown first." -> END
    |
    v
Parse task list from tasks-breakdown.md, present selection with statuses
    |
    v
User selects task T-{N}
    |
    |-- Task is Pending? -> Warn: "Not yet implemented. Dry run only."
    |
    v
Read task spec from tasks/{nnn}-{task-name}.md
    |
    |-- Extract: How to Verify, Expected Behaviors, Boundary Conditions,
    |            Invariants, Sub-Tasks, Definition of Done
    |
    v
Read design context (prd.md, lld.md, sdlc-log.md, reviews/)
    |
    v
Present verification plan with check counts and methods
    |
    |-- User approves -> Execute all
    |-- User selects subset -> Execute subset
    |-- User requests dry run -> Show plan only -> END
    |-- User adjusts -> Update plan, re-present
    |
    v
Execute all checks:
    |-- CLI checks (commands, file checks, API calls, scripts)
    |-- Playwright checks (UI walkthroughs, visual verification, form interactions)
    |
    v
Collect all results -> present verification summary
    |
    v
Determine verdict
    |
    |-- PASS -> Append report to task file, update overview (Verified), log
    |       -> Task proceeds to /review -> /refactor -> END
    |
    |-- PARTIAL -> Present failures, ask user
    |       |-- Accept -> Append report, update overview (Verified with notes), log
    |       |       -> Task proceeds to /review -> /refactor -> END
    |       |-- Fix -> Append report, suggest re-entry phase (/implement, /test) -> END
    |       +-- Defer -> Append report, log as known issues
    |               -> Task proceeds to /review -> /refactor -> END
    |
    +-- FAIL -> Append report, suggest re-entry phase (/implement, /optimize, /observe, /test)
            -> Do NOT proceed to /review or /refactor until verified -> END
```

---

## Patterns

### Do

- Execute every "How to Verify" command literally — these are the task author's primary acceptance checks
- Capture actual output as evidence for every check, even passing ones — evidence makes the report trustworthy
- Write verification scripts for complex checks rather than trying to eyeball them — scripts can be re-run after fixes
- Store verification scripts in `{feature-dir}/verifications/{task-name}/` so they can be re-run after fixes
- Read the actual code when verifying Definition of Done — a file existing doesn't mean it's correct
- Cross-reference review verdicts if they exist — unresolved critical findings from `/review` are automatic failures
- Distinguish between "check failed" (the system behaves wrong) and "check couldn't run" (environment issue) — these need different responses
- Use Playwright MCP tools or Playwright scripts for all UI/UX verification — never delegate visual checks to the human when Playwright can automate them
- Suggest the specific loop phase to re-enter based on failure type — "fix the bug" is less helpful than "the error handling is wrong, re-enter at `/implement`"
- Run checks in dependency order when possible — verify data models exist before testing API endpoints that query them
- Block progression to `/review` and `/refactor` when verification fails — there's no point polishing code that doesn't work

### Don't

- Skip checks because they "probably pass" — the whole point is systematic verification, not spot-checking
- Write automated tests — that's `/test`'s job. Verification scripts are throwaway QA checks, not part of the test suite
- Mark a task as verified when critical checks fail — the user can accept partial, but the skill should never auto-pass failures
- Modify implementation code — verification is read-only. If something needs fixing, re-enter the implementation loop
- Invent checks not in the breakdown — verify what was specified. If you notice gaps, note them in the report as "suggested additions" but don't fail the task on unspecified criteria
- Treat this as a code review — `/review` does that. Verification confirms behavioral correctness against the task spec, not code quality. `/review` and `/refactor` come after `/verify` passes
- Allow progression to `/review` or `/refactor` when critical verification checks fail — broken code shouldn't be polished
- Run verification in production environments — this is for local/staging verification only

---

## Quality Gates

Before completing:

- [ ] Every "How to Verify" step was executed with output captured
- [ ] Every Expected Behavior was tested (happy path, error paths, side effects)
- [ ] Every Boundary Condition was validated (or explicitly skipped with reason)
- [ ] Every Invariant was checked against actual system state
- [ ] Sub-task completion status was confirmed
- [ ] Every Definition of Done criterion was verified (files, contracts, acceptance)
- [ ] UI/UX checks were executed via Playwright MCP or Playwright scripts
- [ ] Verification report appended to `{feature-dir}/tasks/{nnn}-{task-name}.md`
- [ ] Overview (`tasks-breakdown.md`) updated with verification status (if PASS or accepted PARTIAL)
- [ ] On PASS/accepted PARTIAL: task cleared to proceed to `/review` → `/refactor`
- [ ] On FAIL: task blocked from `/review` and `/refactor` — re-entry to earlier phase suggested
- [ ] SDLC log entry appended
