---
name: refactor
description: |
  Orchestrate the refactor phase of the SDLC — review-driven remediation that reads review verdicts,
  presents findings grouped by severity, lets the user select which to fix, maps reviewer domains to
  both implementer agents AND implementation skills, and dispatches agents (with user-approved skills)
  in parallel to produce targeted fixes with a resolution report. Reads verdict files from
  `reviews/{task-name}/` written by `/review`, parses findings with severities (Critical, Warning, Info),
  builds a reviewer-to-implementer mapping for agents (who do the work) and skills (which guide how
  the work is done — e.g., `implement-api`, `implement-data`, `optimize-performance`). The user selects
  which implement-* / optimize-* / observe-* / test-* skills each agent should use, then approved agents
  are dispatched in parallel (batched if >6) with skill invocation as their first step. Produces a
  structured resolution report showing what was fixed, which skills were applied, what needs manual
  attention, and what changed. Use when entering the refactor phase, running `/refactor`, or when the
  user says "refactor", "fix review findings", "address findings", "fix issues", "fix critical",
  "resolve findings", "fix warnings", "remediate", "apply review fixes", "fix the review", "address
  review comments", "fix what review found", "resolve review issues", "refactor after review", "fix
  code review", "address critical issues", "handle review feedback", or "run refactor". This skill
  requires review verdicts to exist — it will block if no review verdicts have been produced yet for
  the selected task.
---

# /refactor — Review-Driven Remediation Orchestrator

> Read review verdicts, present findings by severity, let the user select which to fix, map reviewer domains to implementer agents **and** implementation skills, let the user approve which skills each agent uses, dispatch agents in parallel, and produce a resolution report.

## Quick Reference

| Aspect | Details |
|--------|---------|
| **Phase** | Refactor (per-task, within implementation loop) |
| **Gate** | Review verdicts must exist in `{feature-dir}/reviews/{task-name}/` (run `/review` first if missing) |
| **Produces** | Fixed code, resolution report in `{feature-dir}/reviews/{task-name}/resolution-report.md` |
| **Shared Refs** | `sdlc-shared/refs/feature-resolution.md`, `sdlc-shared/refs/phase-gating.md`, `sdlc-shared/refs/agent-discovery.md`, `sdlc-shared/refs/propose-approve-execute.md`, `sdlc-shared/refs/sdlc-log-format.md` |
| **Next Phase** | `/review` (re-review to validate fixes) or task complete (if all findings resolved) |

---

## Core Workflow

### Step 1: Resolve Feature Directory

Follow the algorithm in [sdlc-shared/refs/feature-resolution.md](../sdlc-shared/refs/feature-resolution.md):

1. If the user passed an argument (e.g., `/refactor 001-sdlc-claude-commands`) — resolve to the matching feature directory under `docs/designs/*/`
2. If no argument — scan `docs/designs/` across all years, present a selection list of existing features
3. If argument doesn't match — report the error and present the selection list
4. If "create new" — assign next sequence number, create `docs/designs/YYYY/NNN-{kebab-case-name}/`

The resolved path becomes `{feature-dir}` for all subsequent steps.

### Step 2: Phase Gate — Require Review Verdicts

Follow [sdlc-shared/refs/phase-gating.md](../sdlc-shared/refs/phase-gating.md):

```
Check: {feature-dir}/reviews/ directory exists?
  |-- No -> Block:
  |         "No review verdicts found in {feature-dir}/reviews/."
  |         "Run `/review` first to produce review verdicts."
  |         -> END
  |
  v
Check: reviews/ contains at least one task subdirectory with .md files?
  |-- No -> Block:
  |         "No review verdicts found. The reviews/ directory is empty."
  |         "Run `/review` first to produce review verdicts."
  |         -> END
  +-- Yes -> Proceed to Step 3
```

### Step 3: Task Context — Identify What to Refactor

Scan the `{feature-dir}/reviews/` directory to identify which tasks have review verdicts:

1. List all subdirectories in `{feature-dir}/reviews/` — each subdirectory corresponds to a reviewed task (e.g., `reviews/shared-references/`, `reviews/implement-api/`)
2. For each task directory, count the verdict files (`.md` files)
3. Read `{feature-dir}/tasks-breakdown.md` to cross-reference task names with their breakdown entries

If multiple tasks have review verdicts, present them and ask the user which task to refactor:

```markdown
## Reviewed Tasks with Verdicts

| # | Task | Verdict Files | Critical | Warning | Info |
|---|------|---------------|----------|---------|------|
| 1 | {task-1-name} | 5 reviewers | 2 | 3 | 4 |
| 2 | {task-2-name} | 7 reviewers | 0 | 5 | 8 |

**Select which task to refactor.** You can refer to a task by number or name.
```

If only one task has verdicts, proceed directly with that task.

### Step 4: Read and Parse All Verdict Files

Scan `{feature-dir}/reviews/{task-name}/` and read every `.md` file to extract findings:

1. List all `.md` files in the task's review directory
2. For each verdict file:
   - Parse the **Findings** table to extract each finding's `#`, `Severity`, `Finding`, `File`, `Line(s)`, `Recommendation`
   - Parse the **Verdict** line (`PASS`, `PASS WITH WARNINGS`, `FAIL`)
   - Note the reviewer agent name from the filename (e.g., `api-reviewer.md` → `api-reviewer`)
3. Build a consolidated findings list with the reviewer attribution attached to each finding

#### Findings Data Structure

For each finding, capture:

| Field | Source |
|-------|--------|
| `reviewer` | Verdict filename without `.md` |
| `severity` | From the Findings table (Critical, Warning, Info) |
| `finding` | Description from the Findings table |
| `file` | File path from the Findings table |
| `lines` | Line range from the Findings table |
| `recommendation` | Recommendation from the Findings table |
| `verdict_file` | Full path to the verdict `.md` file |

### Step 5: Present Consolidated Findings by Severity

Group all findings across all reviewers by severity and present them in a single actionable view:

```markdown
## Review Findings — Task: {task-name}

**Total:** {N} findings from {M} reviewers
**Breakdown:** {critical_count} Critical, {warning_count} Warning, {info_count} Info

### Critical Findings (Must Fix)

| # | Reviewer | Finding | File | Line(s) | Recommendation |
|---|----------|---------|------|---------|----------------|
| 1 | data-reviewer | Missing unique constraint on payment_id | `models/persistence/payment.py` | 45 | Add unique constraint in Alembic migration |
| 2 | api-reviewer | Missing auth middleware on POST endpoint | `routes/v1/payments.py` | 23 | Add `Depends(require_auth)` |

### Warning Findings (Should Fix)

| # | Reviewer | Finding | File | Line(s) | Recommendation |
|---|----------|---------|------|---------|----------------|
| 3 | performance-reviewer | Sequential async calls could be parallelized | `flows/create_payment.py` | 34-42 | Use `asyncio.gather()` |
| 4 | data-reviewer | N+1 query risk in list_by_customer | `adapters/payment_repo.py` | 78 | Use eager loading |
| 5 | api-reviewer | Error responses don't follow ApiError envelope | `routes/v1/payments.py` | 45-60 | Use `raise ApiError(...)` |

### Info Findings (Consider)

| # | Reviewer | Finding | File | Line(s) | Recommendation |
|---|----------|---------|------|---------|----------------|
| 6 | python-reviewer | Could use walrus operator for clarity | `flows/create_payment.py` | 12 | Refactor conditional assignment |
| 7 | observability-reviewer | Missing span for DB call | `adapters/payment_repo.py` | 55 | Add tracing span |
```

### Step 6: User Selects Findings to Address

Present selection options — the user controls which findings are worth fixing:

```markdown
## Select Findings to Address

Choose which findings to fix. Options:
- **"all"** — address all {N} findings
- **"all critical"** — address all critical findings only
- **"all critical and warning"** — address critical + warning findings
- **By number** — e.g., "1, 2, 3, 5" to select specific findings
- **"none"** — skip refactoring (proceed to re-review or next task)

**Recommended:** Address all critical findings at minimum. Warnings are strongly recommended.
```

Wait for user response. If the user selects "none", skip to Step 11 (SDLC log) and end.

### Step 7: Map Reviewer Domains to Implementer Agents and Skills

For each selected finding, map the reviewer that found it to **both** the implementer agent best suited to fix it **and** the implementation skill that provides domain-specific best practices. Agents do the work; skills guide _how_ the work is done.

#### Reviewer-to-Implementer Mapping Table (Agents + Skills)

| Reviewer | Maps to Agent | Maps to Skill | Rationale |
|----------|--------------|---------------|-----------|
| `api-reviewer` | `api-implementer` | `implement-api` | API domain — routes, contracts, HTTP semantics |
| `data-reviewer` | `data-implementer` | `implement-data` | Data domain — models, repos, queries, migrations |
| `event-reviewer` | `event-implementer` | `implement-event` | Event domain — handlers, publishers, async flows |
| `react-reviewer` | `react-implementer` | `implement-react` | Frontend — React components, TypeScript |
| `kubernetes-reviewer` | `kubernetes-implementer` | `implement-kubernetes` | K8s — manifests, Helm charts, ArgoCD |
| `pulumi-reviewer` | `pulumi-implementer` | `implement-pulumi` | Infrastructure — Pulumi IaC, cloud resources |
| `python-reviewer` | `python-implementer` | `implement-python` | Python — idioms, patterns, domain logic |
| `performance-reviewer` | `performance-optimizer` | `optimize-performance` | Performance — profiling, optimization, async |
| `observability-reviewer` | `observability-engineer` | `observe-logs` / `observe-traces` / `observe-metrics` | Observability — pick skill by finding type |
| `design-reviewer` | `python-implementer` | `implement-python` | Design issues → domain logic refactoring |
| `unit-tests-reviewer` | `unit-tester` | `test-unit` | Unit test quality |
| `integration-tests-reviewer` | `integration-tester` | `test-Integration` | Integration test quality |
| `contract-tests-reviewer` | `contract-tester` | `test-contract` | Contract test quality |
| `e2e-tests-reviewer` | `e2e-tester` | `test-e2e` | E2E test quality |
| `ui-tests-reviewer` | `ui-tester` | `test-ui` | UI test quality |

#### Handling Unknown Reviewers

If a verdict file comes from a reviewer not in the mapping table (a future reviewer agent):

1. Parse the reviewer filename to extract the domain prefix (e.g., `security-reviewer` → `security`)
2. Look for a matching implementer: `{domain}-implementer.md` in `.claude/agents/`
3. Look for a matching skill: `implement-{domain}` in `.claude/skills/`
4. If no exact match, fall back to `python-implementer` agent + `implement-python` skill for general code fixes
5. If the finding is about tests, look for `{domain}-tester.md` agent + `test-{domain}` skill as the fixer

#### Consolidate by Implementer

Multiple findings from different reviewers may map to the same implementer agent. Group them, noting the skill each group maps to:

```
api-implementer (skill: implement-api):
  - Finding #1 (from api-reviewer): Missing auth middleware → Add Depends(require_auth)
  - Finding #5 (from api-reviewer): Error responses wrong format → Use raise ApiError(...)

data-implementer (skill: implement-data):
  - Finding #2 (from data-reviewer): Missing unique constraint → Add constraint in migration
  - Finding #4 (from data-reviewer): N+1 query risk → Use eager loading

performance-optimizer (skill: optimize-performance):
  - Finding #3 (from performance-reviewer): Sequential async → Use asyncio.gather()
```

### Step 8: Discover and Propose Agents + Skills

This step has two parts: discover what's available, then present **both agents and skills** for user approval. Skills provide domain-specific best practices that guide how agents write their fixes — agents do the work, skills ensure quality.

#### 8a: Discover Available Agents

Follow [sdlc-shared/refs/agent-discovery.md](../sdlc-shared/refs/agent-discovery.md):

1. Scan `.claude/agents/` for all `*-implementer.md`, `*-optimizer.md`, `*-engineer.md`, and `*-tester.md` files — refactor uses the same agent roles as implementation, optimization, observability, and testing
2. For each agent found, check if any selected findings map to it (from Step 7)
3. Only propose agents that have findings assigned to them — don't propose agents with no work to do

#### 8b: Discover Available Skills

Scan `.claude/skills/` for all `implement-*`, `optimize-*`, `observe-*`, and `test-*` skill directories:

1. List skill directories matching: `implement-*/SKILL.md`, `optimize-*/SKILL.md`, `observe-*/SKILL.md`, `test-*/SKILL.md`
2. For each skill found, check if any selected findings map to it (from Step 7's reviewer-to-skill mapping)
3. Build the list of recommended skills — only skills with mapped findings

#### 8c: Build Agent Proposal Table

Follow [sdlc-shared/refs/propose-approve-execute.md](../sdlc-shared/refs/propose-approve-execute.md):

```markdown
## Proposed Agent Team — Refactor Task: {task-name}

Based on the selected findings and reviewer-to-implementer mapping:

| # | Agent Name | Subagent Type | Findings to Fix | Task-Specific Action | Estimated Scope |
|---|------------|---------------|-----------------|----------------------|-----------------|
| 1 | api-implementer | api-implementer | #1, #5 | Fix missing auth middleware on POST /v1/payments and correct error response format to ApiError envelope | M |
| 2 | data-implementer | data-implementer | #2, #4 | Add unique constraint on payment_id in migration and fix N+1 query in PaymentRepository.list_by_customer | M |
| 3 | performance-optimizer | performance-optimizer | #3 | Parallelize sequential async calls in CreatePaymentFlow using asyncio.gather() | S |

**Total: {N} agents to address {M} selected findings.**
{If >6: "These will be dispatched in batches of 6."}
```

#### 8d: Build Skills Selection Table

Present the recommended skills alongside the agents. Each skill is mapped to the agent(s) that will use it. The user selects which skills to activate — agents dispatched without a skill will rely on their own general capabilities.

```markdown
## Recommended Skills for Agents

Each skill provides domain-specific best practices that the assigned agent will invoke via `/skill-name`
before writing code. Skills are optional — deselecting a skill means the agent works without skill guidance.

| # | Skill Name | Used By Agent(s) | Domain | Why Recommended |
|---|------------|-------------------|--------|-----------------|
| 1 | `implement-api` | api-implementer | API routes, Pydantic models, FastAPI patterns | Findings #1, #5 involve route handlers and error responses |
| 2 | `implement-data` | data-implementer | Data models, repos, queries, migrations | Findings #2, #4 involve schema constraints and query patterns |
| 3 | `optimize-performance` | performance-optimizer | Async patterns, CPU/memory optimization | Finding #3 involves async parallelization |

**Select which skills to use.** Options:
- **"all"** — activate all recommended skills (default)
- **By number** — e.g., "1, 3" to activate only specific skills
- **"none"** — dispatch agents without skill guidance
- **Add skills** — e.g., "also add implement-pydantic for agent 2" to assign additional skills

**Recommended:** Use all mapped skills. They ensure agents follow project conventions and produce consistent code.
```

#### 8e: Present Combined Proposal and Await Approval

Present both tables together (agents + skills) and wait for user response. The user can:
- **Approve** — proceed to dispatch with selected agents and skills
- **Remove agents** — by number (e.g., "remove 3" to skip the performance fix)
- **Add agents** — by name (e.g., "also add python-implementer for general cleanup")
- **Add/remove skills** — by number or name (e.g., "add implement-pydantic for data-implementer", or "skip skill 2")
- **Reassign skills** — move a skill from one agent to another
- **Modify actions** — change what an agent will focus on or reassign findings
- **Reject** — skip refactoring for now

Never dispatch agents without explicit approval of both the agent team and the skill selection.

### Step 9: Dispatch Approved Agents in Parallel

After approval, dispatch all approved agents via the Agent tool in a **single message** with multiple tool calls for parallel execution.

#### Agent Prompt Structure

Each implementer/fixer agent receives a structured prompt. If a skill was approved for this agent, the prompt includes a **mandatory skill invocation step** as the first action.

```markdown
## Context

**Feature:** {feature-name}
**Feature Directory:** {feature-dir-path}
**Phase:** Refactor (review-driven remediation)
**Task:** {task-name}

{If skill(s) approved for this agent:}
## Required Skill — Invoke FIRST

Before writing any code, invoke the following skill(s) using the Skill tool to load domain-specific
best practices and implementation patterns:

- **Invoke:** `/{skill-name}` (e.g., `/implement-api`, `/implement-data`, `/optimize-performance`)

The skill will provide conventions, patterns, and constraints specific to this domain.
Follow its guidance alongside the findings below.

{If multiple skills approved for this agent (e.g., implement-data + implement-pydantic):}
Invoke each skill in order:
1. `/{primary-skill-name}` — primary domain skill
2. `/{secondary-skill-name}` — supplementary skill

{End skill section}

## Your Assignment

{Approved task-specific action from the proposal table}

## Findings to Fix

{For each finding assigned to this agent, include the full details:}

### Finding #{N} (from {reviewer-name})

- **Severity:** {Critical|Warning|Info}
- **Finding:** {description}
- **File:** {file path}
- **Line(s):** {line range}
- **Recommendation:** {what the reviewer recommended}
- **Full verdict:** Read `{feature-dir}/reviews/{task-name}/{reviewer-name}.md` for complete context

{Repeat for each finding assigned to this agent}

## Artifacts to Read

- `{feature-dir}/reviews/{task-name}/{relevant-reviewer}.md` — Full review verdict(s) with context
- `{feature-dir}/README.md` — Feature inception document with vision and goals
- `{feature-dir}/prd.md` — Requirements with acceptance criteria
- `{feature-dir}/lld.md` — Low-level design with contracts, data models, and specs
- `{feature-dir}/tasks-breakdown.md` — Full task details

## Design Constraints

- Fix the specific findings listed above — don't refactor unrelated code
- Follow engineering principles from `.claude/rules/principles.md`
- Use shared libraries from `libs/` (see CLAUDE.md for library guide)
- Follow the ports-and-adapters service structure (see CLAUDE.md)
- Preserve existing tests — if a fix changes behavior, update tests accordingly
- Follow `.claude/rules/testing.md`, `.claude/rules/mocking.md`, `.claude/rules/factories.md` if fixing test code
{If skill approved:}
- Follow the patterns and conventions from the `/{skill-name}` skill you invoked

## Definition of Done

- Each assigned finding is addressed with a code change
- Changes are minimal and targeted — fix the finding, don't rewrite the module
- If a finding cannot be auto-fixed, explain why and what manual steps are needed
- Existing tests still pass after changes
- Report what was changed for each finding
{If skill approved:}
- Code follows the conventions loaded from `/{skill-name}`
```

#### Batching Strategy

Per [sdlc-shared/refs/propose-approve-execute.md](../sdlc-shared/refs/propose-approve-execute.md), if >6 agents are approved, batch into groups of 6:

1. **Batch 1** — dispatch agents 1-6 in a **single message** with multiple Agent tool calls for parallel execution
2. Wait for Batch 1 to complete, present brief batch summary
3. **Batch 2** — dispatch agents 7-12 in a single message, include any cross-cutting observations from Batch 1 as additional context
4. Repeat until all batches complete

If <=6 agents are approved, dispatch all in a **single message** for parallel execution.

### Step 10: Collect Results and Produce Resolution Report

After all agents complete (across all batches), collect their outputs and produce the resolution report.

#### Build the Resolution Report

```markdown
## Resolution Report — {task-name}

**Date:** {YYYY-MM-DD}
**Feature:** {feature-name}
**Findings addressed:** {N} of {total findings} ({critical addressed}/{total critical} critical, {warning addressed}/{total warning} warning, {info addressed}/{total info} info)

### Resolution Summary

| # | Finding | Severity | Reviewer | Agent | Status | Changes |
|---|---------|----------|----------|-------|--------|---------|
| 1 | Missing auth middleware | Critical | api-reviewer | api-implementer | ✅ Resolved | Added `Depends(require_auth)` to POST /v1/payments |
| 2 | Missing unique constraint | Critical | data-reviewer | data-implementer | ✅ Resolved | Added unique constraint in Alembic migration rev-003 |
| 3 | Sequential async calls | Warning | performance-reviewer | performance-optimizer | ✅ Resolved | Refactored to `asyncio.gather()` in CreatePaymentFlow |
| 4 | N+1 query risk | Warning | data-reviewer | data-implementer | ⚠️ Requires Manual Attention | Requires schema change — eager loading not viable with current model |
| 5 | Error response format | Warning | api-reviewer | api-implementer | ✅ Resolved | Replaced HTTPException with ApiError in 3 handlers |

### Status Legend

- **✅ Resolved** — Finding addressed with code changes
- **⚠️ Requires Manual Attention** — Agent could not fully resolve; explanation provided
- **⏭️ Skipped** — Finding was not selected for this refactor cycle

### Findings Requiring Manual Attention

{For each finding marked ⚠️:}

#### Finding #{N}: {title}

- **Why it couldn't be auto-fixed:** {explanation from the agent}
- **Suggested manual approach:** {what the engineer should do}
- **Files involved:** {file paths}

### Files Modified

{Bulleted list of all files created or modified across all agents:}
- `routes/v1/payments.py` — Added auth middleware, corrected error responses
- `adapters/payment_repo.py` — (no changes — N+1 fix deferred)
- `flows/create_payment.py` — Parallelized async calls with asyncio.gather()
- `migrations/versions/003_add_payment_id_unique.py` — New migration

### Next Steps

**Re-review recommended.** Run `/review {feature-identifier}` to validate the fixes and ensure no new issues were introduced.

{If all critical findings resolved:}
All critical findings have been resolved. After re-review confirms the fixes, the task can be marked complete.

{If some critical findings remain:}
**{N} critical findings still require manual attention.** Address them before proceeding to re-review.
```

#### Write the Resolution Report

Write the resolution report to:

```
{feature-dir}/reviews/{task-name}/resolution-report.md
```

This places it alongside the verdict files for easy reference and version control.

### Step 11: Write SDLC Log Entry and Suggest Re-Review

After execution completes (whether agents dispatched, gate block, or skip), append an entry to `{feature-dir}/sdlc-log.md` following [sdlc-shared/refs/sdlc-log-format.md](../sdlc-shared/refs/sdlc-log-format.md):

```markdown
## [YYYY-MM-DD HH:MM] — /refactor — Refactor

- **Task:** {task-name}
- **Agents dispatched:** {list of all agents that ran — e.g., "api-implementer, data-implementer, performance-optimizer"}
- **Skills invoked:** {user-approved skills used by agents — e.g., "implement-api, implement-data, optimize-performance"}
- **Artifacts produced:** {files modified + resolution report — e.g., "routes/v1/payments.py, flows/create_payment.py, migrations/versions/003_add_payment_id_unique.py, reviews/{task-name}/resolution-report.md"}
- **Outcome:** {summary — e.g., "5 findings addressed: 2/2 critical resolved, 2/3 warnings resolved, 1 warning requires manual attention. Resolution report written."}
- **Findings:** {what was fixed and what remains — e.g., "Resolved: auth middleware added (api-reviewer), unique constraint added (data-reviewer), async parallelized (performance-reviewer), error format fixed (api-reviewer). Remaining: N+1 query requires manual schema change (data-reviewer)."}
```

If `sdlc-log.md` doesn't exist, create it with the header first (see the shared ref for the header format).

After writing the log entry, explicitly suggest re-review:

```markdown
## Refactor Complete

**Resolution report:** `{feature-dir}/reviews/{task-name}/resolution-report.md`

**Next step:** Run `/review {feature-identifier}` to validate the fixes and check for any newly introduced issues.
```

---

## Acceptance Criteria Coverage

This skill addresses all six Given/When/Then scenarios from FR-13:

### FR-13: `/refactor` — Review-Driven Remediation

| # | Scenario | Covered By |
|---|----------|------------|
| 1 | Review verdicts exist in `reviews/{task-name}/` → read all verdict files, present consolidated findings grouped by severity | Steps 4-5 — reads all verdict `.md` files, parses findings tables, groups by severity (Critical, Warning, Info) |
| 2 | Findings presented → user selects which to fix → propose implementer agents AND implementation skills, user selects which skills to activate | Steps 6-8 — user selects findings, reviewer-to-implementer mapping for agents + skills, user approves agents and selects skills |
| 3 | User approves agent team + skills → agents execute in parallel, each invokes approved skill first then fixes assigned findings | Step 9 — dispatches agents in single message; each agent invokes its approved skill via Skill tool then fixes findings |
| 4 | Agents complete → produce resolution report listing each finding, agent, changes, and resolution status | Step 10 — structured resolution report with per-finding status, agent attribution, and file changes |
| 5 | Some findings cannot be auto-fixed → marked as "requires manual attention" with explanation | Step 10 — resolution report includes ⚠️ status with explanation and suggested manual approach |
| 6 | /refactor completes → append to sdlc-log.md and suggest re-running /review to validate fixes | Step 11 — SDLC log entry appended, explicit re-review recommendation |

### Additional FR Coverage

| FR | Scenario | Covered By |
|----|----------|------------|
| FR-1 | Feature directory selection | Step 1 — feature resolution via shared ref |
| FR-2 | Phase gating (review verdicts required) | Step 2 — blocks if no verdicts, directs to `/review` |
| FR-3 | Propose → Approve → Execute pattern | Steps 8-9 — proposal table (agents + skills), user approval of both, parallel dispatch |
| FR-4 | Dynamic agent and skill discovery | Step 8a — scans `.claude/agents/` for agents; Step 8b — scans `.claude/skills/` for implement-*, optimize-*, observe-*, test-* skills |
| FR-16 | SDLC log entry | Step 11 — structured log entry with per-agent outcomes and resolution status |

---

## Decision Tree (Full)

```
/refactor invoked
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
Phase Gate: reviews/ directory exists with verdict files? (refs/phase-gating.md)
    |
    |-- No reviews/ directory -> Block: "Run /review first."
    |-- Empty reviews/ directory -> Block: "Run /review first."
    |          -> END
    |
    v
Scan reviews/ for task subdirectories with verdicts
    |
    |-- Multiple tasks have verdicts?
    |       |
    |       v
    |   Present task list with verdict counts -> user selects task
    |
    |-- Single task -> proceed with that task
    |
    v
=== VERDICT READING ===
    |
    v
Read all .md files in reviews/{task-name}/
    |
    v
Parse each verdict file: extract findings (severity, file, line, recommendation)
    |
    v
Build consolidated findings list with reviewer attribution
    |
    v
=== FINDING PRESENTATION ===
    |
    v
Group findings by severity: Critical -> Warning -> Info
    |
    v
Present consolidated findings table
    |
    v
User selects findings to address
    |
    |-- "none" -> skip to SDLC log -> END
    |-- "all critical" -> filter critical only
    |-- "all critical and warning" -> filter critical + warning
    |-- "all" -> all findings
    |-- By number -> selected findings
    |
    v
=== REVIEWER-TO-IMPLEMENTER MAPPING (AGENTS + SKILLS) ===
    |
    v
Map each selected finding's reviewer to both the implementer agent AND the implementation skill
    |
    v
Consolidate findings by target implementer (group multiple findings per agent, note mapped skill)
    |
    v
=== AGENT + SKILL DISCOVERY + PROPOSAL ===
    |
    v
Discover agents: *-implementer.md, *-optimizer.md, *-engineer.md, *-tester.md in .claude/agents/
    |
    v
Discover skills: implement-*, optimize-*, observe-*, test-* in .claude/skills/
    |
    v
Build agent proposal table (only agents with mapped findings)
    |
    v
Build skill selection table (skills mapped to agents, with rationale)
    |
    v
Present BOTH tables -> user approves agents AND selects skills
    |
    |-- Approved (agents + skills) -> proceed to dispatch
    |-- Modified (add/remove agents or skills) -> update proposal, re-present
    +-- Rejected -> END (log skip)
    |
    v
=== DISPATCH ===
    |
    v
>6 agents approved?
    |-- Yes -> Batch into groups of 6
    |       |
    |       v
    |   Dispatch Batch 1 (agents 1-6) in parallel via Agent tool
    |       |
    |       v
    |   Wait for completion -> present batch summary
    |       |
    |       v
    |   Dispatch Batch 2 (agents 7+) in parallel
    |       |
    |       v
    |   (repeat until all batches complete)
    |
    +-- No -> Dispatch all agents in parallel (single message)
    |
    v
Collect all agent results
    |
    v
Agent failures?
    |-- Yes -> report failures, ask: retry / skip / adjust
    +-- No  -> proceed
    |
    v
=== RESOLUTION REPORT ===
    |
    v
Build resolution report:
    |-- Per-finding: status (Resolved / Requires Manual Attention / Skipped)
    |-- Per-agent: what was changed
    |-- Unresolvable findings: explanation + manual approach
    |
    v
Write resolution report to reviews/{task-name}/resolution-report.md
    |
    v
=== SDLC LOG + RE-REVIEW ===
    |
    v
Append SDLC Log Entry (refs/sdlc-log-format.md)
    |
    v
Suggest: "Run /review to validate the fixes."
    |
    v
END
```

---

## Patterns

### Do

- Read all verdict files before presenting findings — the user needs the full picture to make informed selection decisions
- Group findings by severity with Critical first — severity drives prioritization and the user should see the most important issues at the top
- Let the user select findings granularly (by number, by severity level, or all) — not every finding needs to be fixed in every cycle
- Use the reviewer-to-implementer mapping to match domain expertise — `api-reviewer` findings go to `api-implementer` because the API specialist understands the code patterns, contracts, and conventions involved
- Map each reviewer domain to both an agent AND a skill — agents do the work, skills ensure the work follows project conventions and best practices
- Present skills as a separate selection table alongside the agent proposal — the user controls which skills are activated, since some findings may not need full skill guidance
- Include approved skill invocation (`/skill-name`) as the **first instruction** in agent prompts — skills must be loaded before code is written so their patterns inform the fix
- Consolidate multiple findings per implementer into a single agent dispatch — sending `api-implementer` one prompt with 3 findings is more efficient than dispatching it 3 times
- Dispatch all approved agents in a **single message** with multiple Agent tool calls for parallel execution — the agents work on independent code domains and don't need to coordinate
- Include the full verdict file path in agent prompts — agents should read the complete review for context, not just the finding summary
- Write the resolution report alongside the verdict files in `reviews/{task-name}/` — this keeps all review artifacts together and version-controlled
- Mark unresolvable findings as "requires manual attention" with clear explanations — transparency about what automation can and cannot fix builds trust
- Always suggest re-running `/review` after refactoring — fixes may introduce new issues, and the review-refactor cycle should iterate until clean
- Record which skills were invoked in both the resolution report and the SDLC log — traceability of which best practices were applied

### Don't

- Skip the phase gate — refactoring without review verdicts means there's nothing to fix against
- Dispatch agents without user approval of **both** the agent team **and** the skill selection — the propose-approve-execute pattern covers agents and skills together
- Force skills on agents the user deselected — if the user removes a skill from the selection, dispatch the agent without it
- Hardcode the reviewer-to-implementer mapping — if a new reviewer appears (e.g., `security-reviewer.md`), infer the mapping from the domain prefix and look for `security-implementer.md` in `.claude/agents/` and `implement-{domain}` in `.claude/skills/`
- Propose agents that have no findings assigned — every proposed agent should have specific work to do
- Propose skills that have no matching agent — only suggest skills that map to a dispatched agent
- Fix findings the user didn't select — respect the user's selection; they may have reasons to defer certain findings
- Rewrite modules beyond what the findings require — targeted fixes, not full refactors
- Write new tests (unless fixing test-quality findings) — that's `/test`'s job
- Produce design artifacts — that's `/design-system` and `/design-lld`'s job
- Add observability instrumentation (unless fixing observability findings) — that's `/observe`'s job
- Mark the task complete — that's `/implement`'s job via FR-14 completion tracking
