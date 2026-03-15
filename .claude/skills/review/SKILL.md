---
name: review
description: |
  Orchestrate the review phase of the SDLC — multi-dimensional code review where each review skill
  gets its own dedicated agent instance running in parallel for maximum speed and depth. Analyzes
  changed files to detect which domains are involved (Python, API, data, events, React, Kubernetes,
  Pulumi), dynamically discovers all reviewer agents from `.claude/agents/` and all review skills
  from `.claude/skills/`, maps each skill to an agent type (domain-matched 1:1 or quality-attribute
  skills to the primary code-quality agent), then spawns one agent instance per skill — so a
  `python-reviewer` with 9 quality-attribute skills becomes 9 parallel `python-reviewer` instances
  each focused on a single skill dimension. Proposes the full instance list for user approval,
  dispatches instances in parallel (batched if >6), collects structured verdicts written to
  `reviews/{task-name}/` in the feature directory, and presents an aggregated severity-grouped
  summary. If critical issues are found, suggests running `/refactor`.
  Use when entering the review phase, running `/review`, or when the user says "review",
  "code review", "review this", "review task", "review implementation", "check code quality",
  "run review", "do a review", "start review", "review the code", "quality review", "review changes",
  "review my code", "multi-dimensional review", "get feedback", "review before merge", "check the
  implementation", "review this task", or "let's review". This skill requires implementation code to
  exist — it will block if no implementation code has been produced yet for the selected task.
---

# /review — Review Phase Orchestrator

> Analyze changed files, discover reviewer agents and review skills, map each skill to a dedicated agent instance (one instance per skill for maximum parallelism), dispatch all instances in parallel batches with each reading its single assigned skill SKILL.md, collect structured verdicts written to the reviews directory, and present a severity-grouped summary.

## Quick Reference

| Aspect | Details |
|--------|---------|
| **Phase** | Review (per-task, within implementation loop) |
| **Gate** | Implementation code must exist for the selected task (run `/implement` first if missing) |
| **Produces** | Review verdicts in `{feature-dir}/reviews/{task-name}/{skill-name}.md` (one file per skill dimension), severity-grouped summary |
| **Discovers** | Reviewer agents from `.claude/agents/*-reviewer.md` AND review skills from `.claude/skills/review-*/SKILL.md` |
| **Architecture** | One agent instance per skill. Each instance reads and applies exactly one skill SKILL.md with full focus |
| **Shared Refs** | `sdlc-shared/refs/feature-resolution.md`, `sdlc-shared/refs/phase-gating.md`, `sdlc-shared/refs/agent-discovery.md`, `sdlc-shared/refs/propose-approve-execute.md`, `sdlc-shared/refs/sdlc-log-format.md` |
| **Next Phase** | `/refactor` (if BLOCKER/CRITICAL/MAJOR findings) or task complete (if PASS) |

---

## Core Architecture: One Agent Instance Per Skill

The `/review` orchestrator follows a simple principle: **every review skill gets its own dedicated agent instance, running in parallel**.

- **Review skills** (`.claude/skills/review-*/SKILL.md`) define structured criteria, checklists, and severity rubrics for specific quality dimensions (style, types, readability, API correctness, test quality, etc.)
- **Reviewer agents** (`.claude/agents/*-reviewer.md`) are the execution vehicles. Each agent **type** can be instantiated multiple times — one instance per assigned skill
- **One agent instance = one skill = one verdict file.** A `python-reviewer` assigned to 9 quality-attribute skills spawns 9 separate `python-reviewer` instances, each focused on exactly one skill dimension. This maximizes parallelism and review depth — each instance gives its full attention to a single quality dimension

This eliminates bottlenecks where a single agent must context-switch across many criteria. Every skill dimension runs independently, finishes at its own pace, and produces a focused, high-quality verdict.

### Skill-to-Agent Mapping

Each skill maps to an agent **type**. At dispatch time, every skill becomes its own agent instance:

**1. Domain-matched:** The skill name maps directly to an agent type. Each produces one instance.

| Skill | Agent Type | Domain |
|-------|------------|--------|
| `review-api` | `api-reviewer` | FastAPI routes, HTTP semantics, Pydantic models |
| `review-data` | `data-reviewer` | Data models, repositories, queries, persistence |
| `review-event` | `event-reviewer` | Event handlers, publishers, idempotency |
| `review-react` | `react-reviewer` | React components, TypeScript, state management |
| `review-kubernetes` | `kubernetes-reviewer` | K8s manifests, Helm charts, ArgoCD |
| `review-pulumi` | `pulumi-reviewer` | Pulumi IaC, cloud resources |
| `review-design` | `design-reviewer` | Architectural soundness, domain correctness |
| `review-performance` | `performance-reviewer` | CPU, memory, I/O, async efficiency |
| `review-observeability` | `observability-reviewer` | Logging, tracing, metrics instrumentation |
| `review-unit-tests` | `unit-tests-reviewer` | Unit test quality, behavior focus |
| `review-integration-tests` | `integration-tests-reviewer` | Integration test boundary isolation |
| `review-contract-tests` | `contract-tests-reviewer` | Contract test schema compliance |
| `review-e2e-tests` | `e2e-tests-reviewer` | E2E test user journey completeness |
| `review-ui-tests` | `ui-tests-reviewer` | Playwright test stability |
| `review-mcp` | `mcp-reviewer` | MCP servers, tools, resources, prompts, lifespan |

**2. Python-only quality-attribute skills:** These skills evaluate Python-specific quality dimensions (Python syntax patterns, Python type annotations). They are **ONLY proposed when Python files are detected** and always use `python-reviewer`. Never propose these for React/TypeScript code.

| Skill | Quality Dimension | Agent Type | Proposed When |
|-------|-------------------|------------|---------------|
| `review-style` | Python style consistency, walrus operators, modern Python syntax, idiomatic conventions | `python-reviewer` | Python files detected only |
| `review-types` | Python type annotations, typing module, modern typing practices | `python-reviewer` | Python files detected only |

**3. Language-agnostic quality-attribute skills:** These cross-cutting quality dimensions apply to any language. Each gets its own instance of the appropriate code-quality agent: `python-reviewer` for Python files, `react-reviewer` for React/TypeScript files.

| Skill | Quality Dimension | Agent Type (Python) | Agent Type (React/TS) |
|-------|-------------------|--------------------|-----------------------|
| `review-readability` | Naming clarity, structural simplicity, cognitive load | `python-reviewer` | `react-reviewer` |
| `review-functionality` | Functional correctness, edge cases, business logic | `python-reviewer` | `react-reviewer` |
| `review-modularity` | Coupling, cohesion, boundaries, dependency management | `python-reviewer` | `react-reviewer` |
| `review-robustness` | Failure handling, input validation, defensive patterns | `python-reviewer` | `react-reviewer` |
| `review-testability` | DI, pure function separation, determinism | `python-reviewer` | `react-reviewer` |
| `review-coherence` | Terminological consistency, structural uniformity | `python-reviewer` | `react-reviewer` |
| `review-evoleability` | Adaptation capacity, extension points, interface stability | `python-reviewer` | `react-reviewer` |
| `review-reusability` | Shared library usage, duplication detection, cross-service/domain reuse | `python-reviewer` | `react-reviewer` |

**Language separation rule:** When both Python and React/TypeScript files are changed, each language-agnostic skill spawns TWO instances — one `python-reviewer` instance reviewing `.py` files and one `react-reviewer` instance reviewing `.ts`/`.tsx` files. Python-only skills (`review-style`, `review-types`) still only spawn `python-reviewer` instances. When only React/TypeScript files are changed, Python-only skills are not proposed at all.

The mapping is **dynamically discovered** — new skills and agents are automatically detected and matched.

### Why One Instance Per Skill?

Bundling multiple skills into a single agent instance creates two problems:
1. **Sequential bottleneck** — one agent working through 9 skills takes ~9x longer than 9 agents working in parallel
2. **Attention dilution** — an agent juggling many criteria produces shallower reviews per dimension

By giving each skill its own agent instance, every dimension gets the agent's full context window and attention, and all dimensions complete in the wall-clock time of the slowest single review.

---

## Core Workflow

### Step 1: Resolve Feature Directory

Follow the algorithm in [sdlc-shared/refs/feature-resolution.md](../sdlc-shared/refs/feature-resolution.md):

1. If the user passed an argument (e.g., `/review 001-sdlc-claude-commands`) — resolve to the matching feature directory under `docs/designs/*/`
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

### Step 3: Task Context — Identify What to Review

Read the feature's context to understand what code needs review:

1. Read `{feature-dir}/tasks-breakdown.md` — identify which tasks have been implemented (marked `Complete` or `In Progress`)
2. Read `{feature-dir}/sdlc-log.md` — find `/implement` entries to identify which code files were produced and which agents participated
3. Read `{feature-dir}/lld.md` — understand API contracts, data models, event schemas, and service boundaries that define what to validate
4. Read `{feature-dir}/prd.md` — check acceptance criteria and requirements that reviewers should validate against

If multiple tasks have been implemented, present them and ask the user which task(s) to review:

```markdown
## Implemented Tasks

| # | Task | Status | Files Produced |
|---|------|--------|---------------|
| T-1 | {Task 1 title} | Complete | {files from sdlc-log} |
| T-3 | {Task 3 title} | Complete | {files from sdlc-log} |

**Select which task(s) to review.** You can select one task, multiple tasks (e.g., "T-1 and T-3"), or "all" for all implemented tasks.
```

If only one task has been implemented, proceed directly with that task's context.

### Step 4: Analyze Changed Files and Detect Domains

Before discovering agents and skills, analyze the changed files to determine which technical domains are involved. This analysis drives the intelligent selection of which agents to propose and which skills each agent needs.

#### Identify Changed Files

Gather the list of files associated with the selected task:

1. **From sdlc-log.md** — read `/implement` entries to find "Artifacts produced" for the task
2. **From git** — check for changes on the current branch:
   ```bash
   git diff --name-only main...HEAD
   ```
   Or for uncommitted changes:
   ```bash
   git diff --name-only HEAD
   ```
3. **From tasks-breakdown.md** — read the task's sub-tasks and "Files" from its Definition of Done to identify expected file paths

#### Map Files to Domains and Agents

Analyze each changed file's path and extension to detect which technical domains are involved. Each domain maps to exactly one agent:

| File Pattern | Domain | Agent |
|-------------|--------|-------|
| `*.py` files in `routes/` or `router.py` | API | `api-reviewer` |
| `*.py` files in `models/`, `adapters/`, `ports/` | Data | `data-reviewer` |
| `*.py` files in `handlers/`, event-related code | Events | `event-reviewer` |
| `*.tsx`, `*.ts` files in `web/` or component directories | React/Frontend | `react-reviewer` |
| Files in `k8s/`, `deploy/k8s/`, Helm charts | Kubernetes | `kubernetes-reviewer` |
| Pulumi files (`__main__.py` in `deploy/cloud/`) | Infrastructure | `pulumi-reviewer` |
| Design artifacts modified (`lld.md`, `hld.md`) | Design | `design-reviewer` |
| Test files in `tests/unit/` | Unit Tests | `unit-tests-reviewer` |
| Test files in `tests/integration/` | Integration Tests | `integration-tests-reviewer` |
| Test files in `tests/contract/` | Contract Tests | `contract-tests-reviewer` |
| Test files in `tests/e2e/` | E2E Tests | `e2e-tests-reviewer` |
| Test files with Playwright/browser tests | UI Tests | `ui-tests-reviewer` |

#### Cross-Cutting Agent Instances (Always Proposed)

Cross-cutting agent types are proposed based on the detected languages. Each skill spawns its own instance:

- **`python-reviewer`** — when Python code is involved. Spawns instances for: Python-only skills (`review-style`, `review-types` — 2 instances) + language-agnostic skills (`review-readability`, `review-functionality`, `review-modularity`, `review-robustness`, `review-testability`, `review-coherence`, `review-evoleability` — 7 instances). Total: up to 9 parallel instances. **Only proposed when `.py` files are detected.**
- **`react-reviewer`** (quality instances) — when React/TypeScript code is involved. Spawns instances for language-agnostic skills only (`review-readability`, `review-functionality`, `review-modularity`, `review-robustness`, `review-testability`, `review-coherence`, `review-evoleability` — 7 instances). **Never** spawns instances for Python-only skills (`review-style`, `review-types`). **Only proposed when `.ts`/`.tsx` files are detected.**
- **`performance-reviewer`** — when any implementation code is involved. Spawns 1 instance for `review-performance`
- **`observability-reviewer`** — when any implementation code is involved. Spawns 1 instance for `review-observeability`

### Step 5: Discover Agents and Skills, Build Mapping

This is the distinctive step of `/review` — it dynamically discovers agents and skills, maps skills to agents, and presents a unified proposal.

#### 5a: Discover Reviewer Agents

Follow [sdlc-shared/refs/agent-discovery.md](../sdlc-shared/refs/agent-discovery.md):

1. Scan `.claude/agents/` for all `*-reviewer.md` files
2. For each reviewer agent found, parse the filename to extract domain and role
3. Read the agent's `description` from frontmatter to understand its expertise

#### 5b: Discover Review Skills

Scan `.claude/skills/` for all `review-*/SKILL.md` directories:

1. Scan `.claude/skills/` for all directories matching `review-*`
2. For each skill found, read its `SKILL.md` frontmatter to extract `name` and `description`

#### 5c: Map Skills to Agent Types

Apply the mapping rules:

```
For each discovered review skill:
  1. Extract domain name from skill (e.g., "review-api" → "api", "review-unit-tests" → "unit-tests")
  2. Check if a matching agent type exists (e.g., "api" → "api-reviewer", "unit-tests" → "unit-tests-reviewer")
     |-- Match found → this skill uses that agent type (1:1 domain match)
     +-- No match → this is a quality-attribute skill. Check language specificity:
         |-- Python-only skill (review-style, review-types)?
         |       |-- Python code detected → uses python-reviewer
         |       +-- No Python code → SKIP (do not propose — these are Python-specific)
         +-- Language-agnostic skill (review-readability, review-functionality, etc.)?
                 |-- Python code detected → one python-reviewer instance (reviews .py files)
                 |-- React/TS code detected → one react-reviewer instance (reviews .ts/.tsx files)
                 +-- Both detected → TWO instances (one python-reviewer + one react-reviewer)
  3. Each skill becomes ONE agent instance per applicable language (never bundle multiple skills into one instance)
```

**Python-only quality-attribute skills** (only proposed when Python files are detected — never for React/TS):
`review-style`, `review-types`

**Language-agnostic quality-attribute skills** (proposed for any language, using the matching code-quality agent):
`review-readability`, `review-functionality`, `review-modularity`, `review-robustness`, `review-testability`, `review-coherence`, `review-evoleability`

#### 5d: Filter by Detected Domains

Only propose agents that have work to do:

- **Domain-specific agents** — only if matching files were detected in Step 4
- **Cross-cutting agents** — always proposed when their language is involved
- **Test agents** — only if matching test files exist
- **An agent is proposed only if it has at least one assigned skill**

If an agent has no matching domain files, it is not proposed — and its assigned skills are not proposed either.

#### 5e: Build and Present Unified Proposal

Follow [sdlc-shared/refs/propose-approve-execute.md](../sdlc-shared/refs/propose-approve-execute.md):

Present a single unified table showing each agent instance and its single assigned skill. Every row = one agent instance = one skill:

```markdown
## Proposed Review — Task T-{N}: {Task Title}

Based on the changed file analysis, the following agent instances will be dispatched. **Each instance runs exactly one review skill** for maximum parallelism and review depth.

### Domain-Specific Reviewers

| # | Agent Type | Skill | Files to Review |
|---|------------|-------|-----------------|
| 1 | api-reviewer | `review-api` | `routes/v1/payments.py`, `router.py` |
| 2 | data-reviewer | `review-data` | `models/domain/payment.py`, `adapters/payment_repo.py` |

### Python-Only Quality Reviewers (python-reviewer × 2 instances — only when .py files detected)

| # | Agent Type | Skill | Files to Review |
|---|------------|-------|-----------------|
| 3 | python-reviewer | `review-style` | {all .py files} |
| 4 | python-reviewer | `review-types` | {all .py files} |

### Language-Agnostic Quality Reviewers (python-reviewer × 7 instances — or react-reviewer if only .ts/.tsx)

| # | Agent Type | Skill | Files to Review |
|---|------------|-------|-----------------|
| 5 | python-reviewer | `review-readability` | {all .py files} |
| 6 | python-reviewer | `review-functionality` | {all .py files} |
| 7 | python-reviewer | `review-modularity` | {all .py files} |
| 8 | python-reviewer | `review-robustness` | {all .py files} |
| 9 | python-reviewer | `review-testability` | {all .py files} |
| 10 | python-reviewer | `review-coherence` | {all .py files} |
| 11 | python-reviewer | `review-evoleability` | {all .py files} |

### Performance & Observability Reviewers

| # | Agent Type | Skill | Files to Review |
|---|------------|-------|-----------------|
| 12 | performance-reviewer | `review-performance` | {all implementation files} |
| 13 | observability-reviewer | `review-observeability` | {all implementation files} |

### Test Quality Reviewers

| # | Agent Type | Skill | Files to Review |
|---|------------|-------|-----------------|
| 14 | unit-tests-reviewer | `review-unit-tests` | `tests/unit/test_payment_flow.py` |
| 15 | integration-tests-reviewer | `review-integration-tests` | `tests/integration/test_payment_repo.py` |

**Total: {N} agent instances across {N} skill dimensions across {N} files.**
{If >6 instances: "Instances will be dispatched in batches of 6."}

**Each instance reads exactly one skill SKILL.md** from `.claude/skills/review-*/SKILL.md` and gives it full attention.
```

Tailor the proposal based on the changed files and design context. Only include agents for domains that have changed files — if no event handlers changed, don't propose `event-reviewer`.

#### 5f: Await User Approval

Present the proposal and wait for user response. The user can:
- **Approve all** — proceed to dispatch all agents
- **Remove agents** — by number (e.g., "remove #5, #7")
- **Add agents** — by name (e.g., "also add the event-reviewer")
- **Reassign skills** — move a skill from one agent to another (e.g., "move review-readability to api-reviewer")
- **Add/remove skills** — from specific agents (e.g., "add review-robustness to api-reviewer")
- **Reject** — skip review for now

Never dispatch agents without explicit approval.

### Step 6: Dispatch Approved Agents

After approval, dispatch agent instances. Each instance reads its single assigned skill SKILL.md and applies those criteria with full focus.

#### Batching

Per [sdlc-shared/refs/propose-approve-execute.md](../sdlc-shared/refs/propose-approve-execute.md), if >6 instances are approved, batch into groups of 6:

1. **Batch 1** — dispatch instances 1-6 in a **single message** with multiple Agent tool calls for parallel execution
2. Wait for Batch 1 to complete, present brief batch summary
3. **Batch 2** — dispatch instances 7-12 in a single message, include any cross-cutting findings from Batch 1 as additional context
4. Repeat until all batches complete

If <=6 instances are approved, dispatch all in a **single message** for parallel execution.

**Example with 15 instances:**
- Batch 1 (instances 1-6): `api-reviewer:review-api`, `data-reviewer:review-data`, `python-reviewer:review-style`, `python-reviewer:review-types`, `python-reviewer:review-readability`, `python-reviewer:review-functionality`
- Batch 2 (instances 7-12): `python-reviewer:review-modularity`, `python-reviewer:review-robustness`, `python-reviewer:review-testability`, `python-reviewer:review-coherence`, `python-reviewer:review-evoleability`, `performance-reviewer:review-performance`
- Batch 3 (instances 13-15): `observability-reviewer:review-observeability`, `unit-tests-reviewer:review-unit-tests`, `integration-tests-reviewer:review-integration-tests`

#### Agent Instance Naming

When dispatching multiple instances of the same agent type, use descriptive names to distinguish them:

```
Agent tool call: name="{agent-type}:{skill-name}"
```

For example: `python-reviewer:review-style`, `python-reviewer:review-types`, `python-reviewer:review-readability`, etc.

#### Agent Prompt Structure

Each agent instance receives a structured prompt. The key element is that each instance focuses on **exactly one skill** — it reads that skill's SKILL.md file and applies its criteria with undivided attention.

**Each agent is responsible for writing its own verdict file to disk.** The orchestrator provides the exact output path; the agent creates the directory (if needed) and writes the file. This eliminates a post-collection bottleneck and ensures verdict files are written as soon as each agent finishes — not after all agents complete.

```markdown
## Context

**Feature:** {feature-name}
**Feature Directory:** {feature-dir-path}
**Phase:** Review
**Task:** T-{N} — {task title}

## Your Assignment

Review the files listed below by applying the evaluation criteria from your single assigned review skill. When done, write your verdict file to the exact output path specified below.

## Verdict Output Path — YOU MUST WRITE THIS FILE

**Output file:** `{feature-dir}/reviews/{task-name}/{skill-name}.md`

Create the directory `{feature-dir}/reviews/{task-name}/` if it does not exist, then write your verdict to the file path above. This is your primary deliverable — the review is not complete until the verdict file exists on disk. Do not just return the verdict as text; you must write it to the file.

## Review Skill to Apply

Read this skill file and apply its criteria, checklists, and severity rubrics:

- `.claude/skills/{skill-name}/SKILL.md` — {skill description}

**How to apply the skill:** Read the SKILL.md file. Extract the evaluation criteria, checklist items, and severity definitions. Review each file against ALL of this skill's criteria. Report findings for this single skill dimension only.

## Artifacts to Read for Context

- `{feature-dir}/README.md` — Feature inception document with vision and goals
- `{feature-dir}/prd.md` — Requirements with acceptance criteria to validate against
- `{feature-dir}/lld.md` — Low-level design with contracts, data models, and specs
- `{feature-dir}/tasks-breakdown.md` — Full task details (read Task T-{N} section)
- `{feature-dir}/sdlc-log.md` — Check /implement, /observe, /test entries for context

## Files to Review

{List of changed files relevant to this agent's domain, extracted from Step 4}

## Design Contracts to Validate Against

{From lld.md — include relevant specs:}
- OpenAPI: {if API routes involved, reference the spec path}
- AsyncAPI: {if event handlers involved, reference the spec path}
- Data models: {if persistence involved, reference the schema definitions}
- Observability contracts: {if instrumentation involved}

## Codebase Conventions

- Follow `.claude/rules/principles.md` — engineering principles are the quality bar
- Follow `.claude/rules/testing.md`, `.claude/rules/mocking.md`, `.claude/rules/factories.md` (for test reviewers)
- Use shared libraries from `libs/` (see CLAUDE.md for library guide)
- Follow the ports-and-adapters service structure (see CLAUDE.md)

## Verdict File Format

**Each agent instance writes exactly one verdict file** to the output path above. The file is self-contained and covers one skill dimension with full depth.

Use this format for the verdict file content:

### {Skill Name} — Review Verdict

**Skill Dimension:** {skill-name} (e.g., review-style, review-api, review-unit-tests)
**Task:** T-{N} — {task title}
**Reviewed by:** {agent-name}
**Date:** {YYYY-MM-DD}

#### Summary
{1-2 sentence assessment for this specific skill dimension}

#### Findings

Each finding uses this format:

### [{SEVERITY_EMOJI} {SEVERITY}] {Title}

**Location:** `{file}:{line}`
**Criterion:** {ID} - {Name} (from the skill's criteria)

**Issue:** {Description}

**Evidence:**
\`\`\`{language}
{code snippet}
\`\`\`

**Suggestion:** {Fix guidance}
**Rationale:** {Why it matters}

**Severity definitions:**
- **BLOCKER** — Wrong output, crashes, data corruption, silent failures. Must fix before merge
- **CRITICAL** — Missing required feature, logic flaw, lost error context. Must fix
- **MAJOR** — Unhandled edge case, incomplete validation, design concern. Should fix
- **MINOR** — Suboptimal logic, minor inconsistency, missing best practice. Consider fixing
- **SUGGESTION** — Alternative approach, optional improvement. Optional
- **COMMENDATION** — Excellent implementation, positive reinforcement. No action needed

#### Summary Table

| Metric | Count |
|--------|-------|
| Files Reviewed | {N} |
| Blockers | {N} |
| Critical | {N} |
| Major | {N} |
| Minor | {N} |
| Suggestions | {N} |
| Commendations | {N} |

#### Verdict
{PASS | PASS_WITH_SUGGESTIONS | NEEDS_WORK | FAIL}
- PASS: Only SUGGESTION/COMMENDATION findings (or none)
- PASS_WITH_SUGGESTIONS: Few MAJOR/MINOR findings, no CRITICAL or BLOCKER
- NEEDS_WORK: CRITICAL findings present, or multiple (>=3) MAJOR findings
- FAIL: One or more BLOCKER findings

## Definition of Done

- Verdict file written to `{feature-dir}/reviews/{task-name}/{skill-name}.md` (directory created if needed)
- The skill's SKILL.md file was read and ALL its criteria applied with full depth
- Findings include severity emoji, location, criterion ID, and actionable suggestion
- Verdict (PASS/PASS_WITH_SUGGESTIONS/NEEDS_WORK/FAIL) is explicitly stated
- Findings are specific and actionable — not vague or generic
- The file exists on disk — do not just return text output without writing the file
```

### Step 7: Verify Verdict Files Written by Agents

Each agent instance writes its own verdict file to `{feature-dir}/reviews/{task-name}/{skill-name}.md` as part of its Definition of Done (see Step 6 prompt). After all agent instances complete (across all batches), verify that the expected files exist.

#### Compute the Reviews Directory Path

```
{feature-dir}/reviews/{task-name}/
```

Where `{task-name}` is derived from the task title in kebab-case (e.g., task "Shared References and Directory Structure" -> `shared-references-and-directory-structure`).

#### Verify Expected Verdict Files

For each dispatched agent instance, check that the corresponding verdict file exists:

```
{feature-dir}/reviews/{task-name}/{skill-name}.md
```

The file is named after the **skill**, not the agent. Each file contains exactly one skill dimension's verdict.

Expected directory structure after all agents complete:
```
docs/designs/2026/001-demo-mvp/reviews/mcp-server-core/
  ├── review-api.md                 # written by: api-reviewer
  ├── review-data.md                # written by: data-reviewer
  ├── review-style.md               # written by: python-reviewer
  ├── review-types.md               # written by: python-reviewer
  ├── review-readability.md         # written by: python-reviewer
  ├── review-functionality.md       # written by: python-reviewer
  ├── review-modularity.md          # written by: python-reviewer
  ├── review-robustness.md          # written by: python-reviewer
  ├── review-testability.md         # written by: python-reviewer
  ├── review-coherence.md           # written by: python-reviewer
  ├── review-evoleability.md        # written by: python-reviewer
  ├── review-performance.md         # written by: performance-reviewer
  ├── review-observeability.md      # written by: observability-reviewer
  ├── review-unit-tests.md          # written by: unit-tests-reviewer
  └── review-integration-tests.md   # written by: integration-tests-reviewer
```

#### Handle Missing Verdict Files

If any expected verdict file is missing after an agent completes, it means the agent failed to write its deliverable. Report the missing files and offer the user options: retry the failed agent instance, skip that dimension, or manually write the verdict based on the agent's text output (if any was returned).

Each verdict file maps 1:1 to a skill dimension. This means `/refactor` can read a specific dimension's verdict (e.g., `review-types.md`) and address exactly those findings without parsing a combined file.

If verdict files already exist from a previous review cycle, agents overwrite them — previous versions are preserved in git history.

### Step 8: Present Aggregated Summary

After all verdicts are written, aggregate findings across all skill dimension verdict files and present a severity-grouped summary.

#### Aggregate Findings

Read all verdict files from Step 7. Each file is one skill dimension. Collect every finding into a single list, grouped by severity:

```markdown
## Review Summary — Task T-{N}: {Task Title}

### Per-Skill Verdicts

| Skill Dimension | Verdict File | Reviewed By | Verdict | BLOCKER | CRITICAL | MAJOR | MINOR | SUGGESTION | COMMENDATION |
|----------------|-------------|-------------|---------|---------|----------|-------|-------|------------|-------------|
| review-api | `review-api.md` | api-reviewer | NEEDS_WORK | 0 | 1 | 2 | 1 | 0 | 0 |
| review-data | `review-data.md` | data-reviewer | FAIL | 1 | 1 | 0 | 0 | 0 | 0 |
| review-style | `review-style.md` | python-reviewer | PASS | 0 | 0 | 0 | 0 | 1 | 0 |
| review-types | `review-types.md` | python-reviewer | PASS_WITH_SUGGESTIONS | 0 | 0 | 1 | 0 | 0 | 0 |
| review-readability | `review-readability.md` | python-reviewer | PASS | 0 | 0 | 0 | 0 | 0 | 1 |
| review-functionality | `review-functionality.md` | python-reviewer | PASS | 0 | 0 | 0 | 1 | 1 | 0 |
| review-modularity | `review-modularity.md` | python-reviewer | PASS | 0 | 0 | 0 | 0 | 0 | 0 |
| review-robustness | `review-robustness.md` | python-reviewer | PASS | 0 | 0 | 0 | 0 | 0 | 0 |
| review-testability | `review-testability.md` | python-reviewer | PASS | 0 | 0 | 0 | 0 | 0 | 0 |
| review-coherence | `review-coherence.md` | python-reviewer | PASS | 0 | 0 | 0 | 0 | 0 | 0 |
| review-evoleability | `review-evoleability.md` | python-reviewer | PASS | 0 | 0 | 0 | 0 | 0 | 0 |
| review-performance | `review-performance.md` | performance-reviewer | PASS_WITH_SUGGESTIONS | 0 | 0 | 1 | 2 | 0 | 0 |
| review-observeability | `review-observeability.md` | observability-reviewer | PASS | 0 | 0 | 0 | 0 | 1 | 0 |
| review-unit-tests | `review-unit-tests.md` | unit-tests-reviewer | PASS | 0 | 0 | 0 | 0 | 0 | 2 |
| **Total** | — | — | — | **1** | **2** | **4** | **4** | **3** | **3** |

**Severity key:** BLOCKER (must fix) > CRITICAL (must fix) > MAJOR (should fix) > MINOR (consider) > SUGGESTION (optional) > COMMENDATION (praise)

### BLOCKER Findings (Must Fix Before Merge)

| # | Skill Dimension | Criterion | Finding | Location | Suggestion |
|---|----------------|-----------|---------|----------|------------|
| 1 | review-data | IS.1 | Missing unique constraint on payment_id allows duplicate processing | `models/persistence/payment.py:45` | Add unique constraint to payment_id column in the Alembic migration |

### CRITICAL Findings (Must Fix)

| # | Skill Dimension | Criterion | Finding | Location | Suggestion |
|---|----------------|-----------|---------|----------|------------|
| 1 | review-api | IV.1 | Missing auth middleware on POST /v1/payments endpoint | `routes/v1/payments.py:23` | Add `Depends(require_auth)` to the route handler |
| 2 | review-data | CA.1 | N+1 query risk in PaymentRepository.list_by_customer | `adapters/payment_repo.py:78` | Use eager loading or batch query |

### MAJOR Findings (Should Fix)

| # | Skill Dimension | Criterion | Finding | Location | Suggestion |
|---|----------------|-----------|---------|----------|------------|
| 1 | review-api | EH.3 | Error responses don't follow ApiError envelope format | `routes/v1/payments.py:45-60` | Use `raise ApiError(...)` instead of raw HTTPException |
| 2 | review-performance | — | Sequential async calls in CreatePaymentFlow could be parallelized | `flows/create_payment.py:34-42` | Use `asyncio.gather()` for independent I/O calls |
| 3 | review-types | TYP.3 | Missing return type annotation on process_payment | `flows/create_payment.py:20` | Add `-> PaymentResult` return type |

### MINOR / SUGGESTION / COMMENDATION

| # | Severity | Skill Dimension | Finding | Location |
|---|----------|----------------|---------|----------|
| 1-9 | {various} | {various} | {lower-severity findings summarized} | — |

### Verdicts Written To

All verdict files are saved in:
```
{feature-dir}/reviews/{task-name}/
```

Each file is named `{skill-name}.md` and contains exactly one skill dimension's review.

### Next Steps

{If BLOCKER findings exist:}
**BLOCKER issues found.** Run `/refactor {feature-identifier}` to address the {N} blocker and {N} critical findings. `/refactor` can read individual skill verdict files (e.g., `review-data.md`) to target specific dimensions. Merge is blocked until resolved.

{If CRITICAL findings but no BLOCKER:}
**CRITICAL issues found.** Run `/refactor {feature-identifier}` to address the {N} critical and {N} major findings with targeted implementer agents.

{If MAJOR findings but no CRITICAL or BLOCKER:}
**MAJOR issues found.** {N} major findings — consider running `/refactor {feature-identifier}` to address them, or proceed to the next task if they are acceptable.

{If only MINOR/SUGGESTION/COMMENDATION findings:}
**Clean review.** No blocker, critical, or major issues found. The task is ready for completion. Run `/implement {feature-identifier}` to mark the task complete, or proceed to the next task.
```

### Step 9: Write SDLC Log Entry

After execution completes (whether agents dispatched, gate block, or skip), append an entry to `{feature-dir}/sdlc-log.md` following [sdlc-shared/refs/sdlc-log-format.md](../sdlc-shared/refs/sdlc-log-format.md):

```markdown
## [YYYY-MM-DD HH:MM] — /review — Review

- **Task:** T-{N} — {task title}
- **Agent instances dispatched:** {list of instances grouped by batch — e.g., "Batch 1: api-reviewer:review-api, data-reviewer:review-data, python-reviewer:review-style, python-reviewer:review-types, python-reviewer:review-readability, python-reviewer:review-functionality. Batch 2: python-reviewer:review-modularity, python-reviewer:review-robustness, python-reviewer:review-testability, python-reviewer:review-coherence, python-reviewer:review-evoleability, performance-reviewer:review-performance"}
- **Skill dimensions covered:** {total count of skills applied across all agents}
- **Artifacts produced:** {verdict files written — e.g., "reviews/mcp-server-core/review-api.md, reviews/mcp-server-core/review-data.md, reviews/mcp-server-core/review-style.md, reviews/mcp-server-core/review-types.md, ..."}
- **Outcome:** {summary — e.g., "6 agents dispatched covering 14 skill dimensions. 1 blocker, 2 critical, 3 major, 4 minor, 3 suggestion, 3 commendation findings. Overall: 1 FAIL, 1 NEEDS_WORK, 1 PASS_WITH_SUGGESTIONS, 3 PASS. /refactor recommended."}
- **Findings:** {high-level summary of blocker/critical/major findings — e.g., "Blocker: missing unique constraint on payment_id (review-data). Critical: missing auth middleware (review-api), N+1 query risk (review-data). Major: error envelope format (review-api), sequential async calls (review-performance), missing return type (review-types)."}
```

If `sdlc-log.md` doesn't exist, create it with the header first (see the shared ref for the header format).

---

## Decision Tree (Full)

```
/review invoked
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
    |   Present task list -> user selects which to review
    |
    |-- Single task -> proceed with that task
    |
    v
=== CHANGED FILE ANALYSIS ===
    |
    v
Gather changed files (sdlc-log + git + breakdown)
    |
    v
Map files to domains (API, Data, Events, React, K8s, Pulumi, Python, Tests)
    |
    v
Identify cross-cutting agents (python, performance, observability)
    |
    v
=== DISCOVER AGENTS AND SKILLS ===
    |
    v
Discover *-reviewer.md agents (refs/agent-discovery.md)
    |
    v
Discover review-*/SKILL.md skills (.claude/skills/)
    |
    v
Map skills to agent types:
    |-- Domain-matched (1:1) -> skill uses matching agent type
    |-- Python-only quality-attribute (review-style, review-types) -> python-reviewer ONLY if Python detected, else SKIP
    |-- Language-agnostic quality-attribute -> python-reviewer for .py, react-reviewer for .ts/.tsx, both if mixed
    |-- Each skill = one agent instance per applicable language (never bundle)
    |
    v
Filter by detected domains:
    |-- Domain agent instances -> only if matching files exist
    |-- Cross-cutting instances -> always proposed when language matches
    |-- Test instances -> only if test files exist
    |-- Drop instances with no matching domain files
    |
    v
Build unified proposal table (one row per instance: agent type + skill + files)
    |
    v
Present proposal -> await user approval
    |
    |-- Approved (all/subset) -> proceed
    |-- Modified (add/remove/reassign) -> update proposal, re-present
    +-- Rejected -> END (log skip)
    |
    v
=== DISPATCH AGENT INSTANCES ===
    |
    v
>6 instances approved?
    |-- Yes -> Batch into groups of 6
    |       |
    |       v
    |   Dispatch Batch 1 (instances 1-6) in parallel
    |       |
    |       v
    |   Wait for completion -> present batch summary
    |       |
    |       v
    |   Dispatch Batch 2 (instances 7-12) in parallel
    |       |
    |       v
    |   (repeat until all batches complete)
    |
    +-- No -> Dispatch all instances in parallel (single message)
    |
    v
Each agent writes its verdict to reviews/{task-name}/{skill-name}.md
    |
    v
=== VERDICT VERIFICATION ===
    |
    v
Verify all expected verdict files exist on disk
    |
    v
Missing files?
    |-- Yes -> report missing, ask: retry agent / skip / write manually
    +-- No  -> proceed
    |
    v
=== SUMMARY ===
    |
    v
Aggregate findings by severity across all skill verdict files
    |
    v
Present severity-grouped summary table with skill dimension attribution
    |
    v
Present skill coverage table (which skills found issues)
    |
    v
BLOCKER or CRITICAL findings?
    |-- BLOCKER -> "Run /refactor. Merge blocked until resolved."
    |-- CRITICAL -> "Run /refactor to address critical issues."
    |-- MAJOR only -> "Consider /refactor, or proceed if acceptable."
    +-- MINOR/SUGGESTION/COMMENDATION only -> "Clean review. Task ready for completion."
    |
    v
Append SDLC Log Entry (refs/sdlc-log-format.md)
    |
    v
END
```

---

## Patterns

### Do

- Analyze changed files before proposing agent instances — the file analysis drives intelligent selection
- Map each skill to its own agent instance — **never bundle multiple skills into one instance**
- Spawn `python-reviewer` instances only for Python files: 2 Python-only skills (`review-style`, `review-types`) + 7 language-agnostic skills = up to 9 parallel instances
- Spawn `react-reviewer` quality instances only for React/TS files: 7 language-agnostic skills only — **never** `review-style` or `review-types` (these are Python-specific)
- When both Python and React/TS files are changed, language-agnostic skills spawn TWO instances each (one per language)
- Always include performance-reviewer and observability-reviewer when implementation code is involved
- Include the single skill file path in each agent prompt so it can read the full criteria with undivided attention
- Present a unified proposal showing each instance on its own row (agent type + skill + files)
- Let users add/remove instances in the approval step — flexibility is important
- Match test-quality instances to the test files that actually exist — if no e2e tests were written, don't propose e2e-tests-reviewer
- Batch dispatch when >6 instances are approved — context window safety prevents dispatching all at once
- Dispatch all instances within each batch in a single message for parallel execution — every instance works independently
- Use descriptive instance names like `python-reviewer:review-style` to distinguish multiple instances of the same agent type
- Require skill dimension attribution on every finding — this enables `/refactor` to trace issues back to specific quality dimensions
- Include the verdict output path in each agent prompt so agents write their own files — each agent creates `{feature-dir}/reviews/{task-name}/{skill-name}.md` directly
- Verify all expected verdict files exist after agents complete — report missing files as agent failures
- Include the skill coverage table in the summary — shows which quality dimensions were evaluated and where issues were found
- Include design contracts (OpenAPI, AsyncAPI, data models from lld.md) in agent prompts — instances validate implementation against specs

### Don't

- **Bundle multiple skills into a single agent instance** — this is the most important rule. Each skill gets its own instance for maximum parallelism and review depth
- **Propose Python-only skills (`review-style`, `review-types`) for React/TypeScript code** — these evaluate Python-specific patterns (walrus operators, Python type annotations) and are meaningless for TS/TSX files
- **Propose `react-reviewer` instances for `review-style` or `review-types`** — these are Python-only dimensions; `react-reviewer` should only get language-agnostic quality skills
- Run skills separately from agents — skills are criteria that agents apply, not independent executors
- Dispatch agents without telling them which skill to read — each instance needs its single skill criteria to produce a focused verdict
- Dispatch agents without the verdict output path — each instance must know where to write `{feature-dir}/reviews/{task-name}/{skill-name}.md`
- Collect agent text output and write verdict files from the orchestrator — agents write their own files; the orchestrator only verifies they exist
- Skip the phase gate — reviewing code that doesn't exist yet is impossible
- Dispatch instances without user approval — the propose-approve-execute pattern is non-negotiable
- Hardcode the agent or skill list — always scan `.claude/agents/` and `.claude/skills/` dynamically
- Propose all instances regardless of context — if only backend Python code changed, don't propose react-reviewer, kubernetes-reviewer, etc.
- Write implementation code — that's `/implement`'s job
- Fix the findings — that's `/refactor`'s job
- Add observability instrumentation — that's `/observe`'s job
- Write tests — that's `/test`'s job
- Produce design artifacts — that's `/design-system` and `/design-lld`'s job
