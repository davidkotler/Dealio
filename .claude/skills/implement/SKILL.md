---
name: implement
description: |
  Orchestrate the implementation phase of the SDLC — per-task code production with dynamically
  discovered implementation skills and implementer agents. Presents the task list from the breakdown,
  lets the user select a task, checks dependency readiness, discovers all implement-* skills and
  *-implementer agents, proposes domain-matched skills and agents for user approval, invokes approved
  skills for best-practice guidance, and dispatches approved agents in parallel to produce code.
  Supports multi-instance dispatch — when a task spans multiple loosely coupled domains, proposes
  running multiple agents of the same type in parallel (e.g., two python-implementers for independent
  bounded contexts) while keeping tightly coupled areas under a single agent for coherence.
  Supports skills-only mode (inline implementation) or skills+agents mode. Tracks task completion
  by updating tasks-breakdown.md with status and notes. Use when entering the implementation phase,
  running `/implement`, or when the user says "implement", "start implementing", "build this",
  "code this", "write the code", "implement task", "start coding", "begin implementation",
  "let's implement", "work on task", "pick a task", "next task", "implement next", "start the build",
  "write code for", "produce code", or "execute task". This skill requires tasks-breakdown.md from
  the breakdown phase — it will block if no task breakdown exists yet.
---

# /implement — Implementation Phase Orchestrator

> Present the task list, let the user select a task, discover implementation skills and implementer agents matched to the task's domain, let the user select which skills and agents to use, invoke skills for best-practice guidance, and dispatch agents in parallel to produce code.

## Quick Reference

| Aspect | Details |
|--------|---------|
| **Phase** | Implementation (per-task) |
| **Gate** | `tasks-breakdown.md` must exist (run `/tasks-breakdown` first if missing) |
| **Produces** | Code changes for the selected task, updated `tasks-breakdown.md` (task status) |
| **Shared Refs** | `sdlc-shared/refs/feature-resolution.md`, `sdlc-shared/refs/phase-gating.md`, `sdlc-shared/refs/agent-discovery.md`, `sdlc-shared/refs/propose-approve-execute.md`, `sdlc-shared/refs/sdlc-log-format.md` |
| **Next Phase** | `/observe`, `/test`, or `/review` (after code is produced for the task) |

---

## Core Workflow

### Step 1: Resolve Feature Directory

Follow the algorithm in [sdlc-shared/refs/feature-resolution.md](../sdlc-shared/refs/feature-resolution.md):

1. If the user passed an argument (e.g., `/implement 001-sdlc-claude-commands`) — resolve to the matching feature directory under `docs/designs/*/`
2. If no argument — scan `docs/designs/` across all years, present a selection list of existing features
3. If argument doesn't match — report the error and present the selection list
4. If "create new" — assign next sequence number, create `docs/designs/YYYY/NNN-{kebab-case-name}/`

The resolved path becomes `{feature-dir}` for all subsequent steps.

### Step 2: Phase Gate — Require tasks-breakdown.md

Follow [sdlc-shared/refs/phase-gating.md](../sdlc-shared/refs/phase-gating.md):

```
Check: {feature-dir}/tasks-breakdown.md exists and is non-empty?
  |-- Yes -> Proceed to Step 3
  +-- No  -> Block:
            "No task breakdown found in {feature-dir}/."
            "Run `/tasks-breakdown` first to produce tasks-breakdown.md."
            -> END
```

This is an existence check only — if tasks-breakdown.md exists and is non-empty, the gate passes.

### Step 3: Parse Task List and Present Task Selection

Read `{feature-dir}/tasks-breakdown.md` and extract all tasks with their current status.

#### Parse Tasks

Scan the breakdown for task entries. Each task has a structure like:

```
#### Task N: {Title}
- **Complexity:** {S|M|L}
- **Dependencies:** {None | Hard: [T-N] | Soft: [T-N]}
```

Tasks that have been marked `✅ Complete` (via previous `/implement` runs) should show that status. All others are `⬜ Pending`.

#### Present the Task List

```markdown
## Task List — {Feature Name}

| # | Task | Complexity | Status | Dependencies |
|---|------|-----------|--------|--------------|
| T-1 | {Task 1 title} | M | ✅ Complete | None |
| T-2 | {Task 2 title} | S | ✅ Complete | None |
| T-3 | {Task 3 title} | L | ⬜ Pending | Hard: T-1 |
| T-4 | {Task 4 title} | M | ⬜ Pending | Hard: T-1, Soft: T-3 |
| T-5 | {Task 5 title} | S | ⬜ Pending | Hard: T-3 |

**Select a task to implement.** You can refer to a task by number (e.g., "T-3") or by name.
```

If all tasks are complete, inform the user:

```markdown
## All Tasks Complete

All {N} tasks in the breakdown are marked as complete.

**Next step:** Run `/sdlc {feature-identifier}` to view the full lifecycle status, or begin the ship phase.
```

→ END

### Step 4: Dependency Check

When the user selects a task, check whether its hard dependencies are satisfied:

```
Selected task: T-{N}
    |
    +-- Read task's "Dependencies" field from tasks-breakdown.md
    |
    +-- For each hard dependency (Hard: [T-X]):
    |       |
    |       +-- Is T-X marked as "Complete" in tasks-breakdown.md?
    |           |-- Yes -> Dependency satisfied
    |           +-- No  -> Dependency NOT satisfied
    |
    +-- All hard dependencies satisfied?
        |-- Yes -> Proceed to Step 5
        +-- No  -> Warn the user
```

#### Dependency Warning

If hard dependencies are not satisfied, present a warning:

```markdown
## Dependency Warning

Task T-{N} ({task title}) has unsatisfied hard dependencies:

| Dependency | Task | Status |
|-----------|------|--------|
| T-{X} | {dependency title} | ⬜ Pending |
| T-{Y} | {dependency title} | ⬜ Pending |

Implementing this task before its dependencies may result in missing foundations, broken contracts, or rework.

**Proceed anyway?** (yes/no)
```

- If the user confirms → proceed to Step 5
- If the user declines → return to Step 3 (task selection)

Soft dependencies do not trigger warnings — they are advisory only. Mention them in a note if present:

```
Note: This task has soft dependencies on T-{X} (for end-to-end testing). These don't block implementation.
```

### Step 5: Read Feature Context and Task Details

Before building the agent proposal, read the feature's design artifacts and the selected task's full details:

1. Read `{feature-dir}/README.md` — vision, goals, rationale
2. Read `{feature-dir}/prd.md` — requirements, acceptance criteria, constraints
3. Read `{feature-dir}/hld.md` — high-level design, service boundaries (if exists)
4. Read `{feature-dir}/lld.md` — low-level design, contracts, data models
5. Read the selected task's full entry from `{feature-dir}/tasks-breakdown.md`:
   - Description, vertical slice, complexity
   - Sub-tasks with their dimensions (Data, API, Event, Web/UI, Infra, etc.)
   - Agent assignment suggestions from the breakdown
   - Definition of Done criteria

Use this context to match implementer agents to the task's specific requirements.

### Step 6: Discover Implementation Skills and Agents

This step discovers both **skills** (best-practice guides that Claude Code follows inline) and **agents** (parallel subprocesses that produce code). Skills and agents serve different roles:

- **Skills** — Loaded into Claude Code's context via the `Skill` tool. They provide patterns, constraints, and domain-specific guidance that Claude Code (or agents) follows while writing code. Skills run **inline**, not as separate processes.
- **Agents** — Dispatched as parallel subprocesses via the `Agent` tool. Each agent works independently on a dimension of the task and produces code artifacts.

#### 6a: Discover Implementation Skills

Scan `.claude/skills/` for all directories matching `implement-*`. For each, read the `SKILL.md` frontmatter to extract the skill's `name` and `description`.

1. List all `implement-*` directories under `.claude/skills/`
2. For each directory, read the first few lines of `SKILL.md` to get the frontmatter `name` and `description`
3. Build a skill catalog from the discovered skills

Currently expected skills:

| Skill | Domain | Purpose |
|-------|--------|---------|
| `implement-python` | Python | Production-quality Python 3.13+ with modern idioms, strict typing, clean architecture |
| `implement-api` | API | FastAPI route handlers from OpenAPI contracts, Pydantic models, async DI |
| `implement-data` | Data | Data models, repositories, queries, migrations from design specs |
| `implement-event` | Events | Event producers, consumers, handlers from AsyncAPI specs |
| `implement-react` | Frontend | React 18+ components with TypeScript, state management, accessibility |
| `implement-pydantic` | Pydantic | Pydantic V2 models with strict validation, immutability, serialization |
| `implement-kubernetes` | K8s | K8s manifests, Helm charts, ArgoCD configs from design specs |
| `implement-pulumi` | IaC | Pulumi Python infrastructure programs from design specs |
| `implement-docker` | Docker | Dockerfiles, Docker Compose, .dockerignore, multi-stage builds |
| `implement-cicd` | CI/CD | GitHub Actions workflows, reusable workflows, composite actions |
| `implement-cli` | CLI | Python CLI applications using Typer and Rich |

Future skills (e.g., `implement-graphql/`, `implement-ml-pipeline/`) will be automatically discovered when they appear in `.claude/skills/`.

#### 6b: Discover Implementer Agents

Follow [sdlc-shared/refs/agent-discovery.md](../sdlc-shared/refs/agent-discovery.md):

1. Scan `.claude/agents/` for all `*-implementer.md` files
2. For each implementer agent found, parse the filename to extract domain and role
3. Read the agent's `description` from frontmatter to understand its expertise

Currently expected agents:

| Agent | Domain | Specialization |
|-------|--------|----------------|
| `api-implementer` | API | FastAPI route handlers, OpenAPI contracts, Pydantic models |
| `data-implementer` | Data | Data models, repositories, queries, migrations |
| `event-implementer` | Events | Event producers, consumers, handlers, AsyncAPI |
| `react-implementer` | Frontend | React components, TypeScript, state management |
| `kubernetes-implementer` | Infrastructure | K8s manifests, Helm charts, ArgoCD |
| `pulumi-implementer` | Infrastructure | Pulumi IaC programs, cloud resources |
| `python-implementer` | Python | Python modules, domain logic, flows, services |

Future implementer agents (e.g., `graphql-implementer.md`, `ml-pipeline-implementer.md`) will be automatically discovered and proposed when they appear in `.claude/agents/`.

#### 6c: Match Skills and Agents to Task Domain

Analyze the selected task's sub-tasks, dimensions, and description to determine which skills and agents are relevant:

| Task mentions / Sub-task dimensions | Propose Skill | Propose Agent |
|-------------------------------------|---------------|---------------|
| API endpoints, routes, HTTP, REST, OpenAPI | `implement-api` | `api-implementer` |
| Database, models, persistence, queries, migrations, repositories | `implement-data` | `data-implementer` |
| Events, handlers, consumers, producers, messages, AsyncAPI | `implement-event` | `event-implementer` |
| React, components, UI, frontend, TypeScript, web | `implement-react` | `react-implementer` |
| Kubernetes, deployments, Helm, K8s, ArgoCD | `implement-kubernetes` | `kubernetes-implementer` |
| Pulumi, infrastructure, IaC, cloud resources, AWS | `implement-pulumi` | `pulumi-implementer` |
| Python logic, domain, flows, services, ports, adapters | `implement-python` | `python-implementer` |
| Pydantic models, validation, serialization, DTOs | `implement-pydantic` | — |
| Docker, containers, images, Compose | `implement-docker` | — |
| CI/CD, GitHub Actions, pipelines, workflows | `implement-cicd` | — |
| CLI, command-line, Typer, Rich | `implement-cli` | — |

**Cross-cutting rules:**
- Always propose `implement-python` when any Python code is involved (most tasks in this codebase).
- Always propose `python-implementer` agent when any Python code is involved — it handles domain logic, application flows, and service orchestration.
- Propose `implement-pydantic` whenever the task involves Pydantic models (API contracts, event payloads, domain value objects) — even if another skill like `implement-api` is also proposed.

**Note:** Some skills have no corresponding agent (e.g., `implement-docker`, `implement-cicd`, `implement-cli`, `implement-pydantic`). These skills guide Claude Code directly when it writes code inline, or are loaded into agent prompts as additional context.

**Agent/Skill assignment hint:** The task's `Agent assignment` field in the breakdown provides a suggestion for which categories are relevant. Use this as a starting point, but still scan all available skills and agents — the breakdown may not have anticipated new ones added after it was written.

#### 6c-multi: Assess Domain Coupling for Multi-Instance Agent Dispatch

After matching agent types to the task, check whether any single agent type maps to **multiple distinct code areas** (different domains, services, or bounded contexts). When it does, assess whether those areas are loosely or tightly coupled to decide if multiple instances of the same agent type should run in parallel.

**Why this matters:** A single agent working sequentially across two unrelated domains carries all context from the first into the second — wasting time and gaining nothing. Two parallel agents, each scoped to one domain, finish faster and produce equally good code because the domains don't depend on each other. But when domains are tightly coupled — sharing types, calling each other's ports, or co-evolving contracts — a single agent that sees both produces more coherent code than two isolated agents that might make conflicting assumptions.

**Coupling assessment:**

For each agent type that maps to 2+ code areas, evaluate the relationship between those areas:

```
Agent type X matched to areas [A, B]:
    |
    +-- Do A and B share domain types (entities, value objects, aggregates)?
    |       Yes -> Tightly coupled -> Single agent
    |
    +-- Does A's implementation call B's ports/interfaces (or vice versa)?
    |       Yes -> Tightly coupled -> Single agent
    |
    +-- Do A and B co-define a contract (e.g., producer/consumer of same event)?
    |       Yes -> Tightly coupled -> Single agent
    |
    +-- Are A and B in different bounded contexts / services / domain directories?
    |       Yes -> Likely loosely coupled -> Check further
    |
    +-- Can A's code compile and function without any knowledge of B's implementation?
    |       Yes -> Loosely coupled -> Propose multi-instance
    |
    +-- Default: keep single agent (err on the side of coherence)
```

**Signals of loose coupling (favor multi-instance):**
- Areas live in different `domains/` directories within a service, or in different services entirely
- Areas communicate only through events or well-defined API contracts (not shared in-memory state)
- Areas have independent data models and repositories with no cross-references
- The sub-tasks for each area have no ordering dependency between them
- Each area's Definition of Done criteria are independently verifiable

**Signals of tight coupling (keep single agent):**
- One area imports types defined in the other
- Areas share a database table, aggregate, or repository interface
- One area's flow orchestrates calls to the other area's ports
- The lld.md describes a sequence where A's output feeds directly into B
- Areas are in the same domain directory or share the same bounded context

**Naming convention for multi-instance agents:**

When proposing multiple instances of the same agent type, suffix each with the scoped domain area:

```
{agent-type}:{domain-area}
```

Examples:
- `python-implementer:orders` and `python-implementer:inventory`
- `react-implementer:dashboard` and `react-implementer:settings`
- `data-implementer:payments` and `data-implementer:ledger`

Each instance gets its own scoped action, scoped file paths, and scoped Definition of Done subset.

#### 6d: Build Proposal — Skills Selection

Present discovered skills matched to the task domain as a **skill selection table**. The user selects which skills Claude Code should load during implementation:

```markdown
## Proposed Implementation Skills — Task T-{N}: {Task Title}

Select which skills should guide this implementation. Selected skills will be loaded as best-practice context for Claude Code and/or agents.

| # | Skill | Domain | Why Proposed | Select |
|---|-------|--------|--------------|--------|
| 1 | `implement-python` | Python | Task involves Python domain logic and flows | ✅ |
| 2 | `implement-api` | API | Task includes REST endpoint implementation | ✅ |
| 3 | `implement-data` | Data | Task includes data model and repository work | ✅ |
| 4 | `implement-pydantic` | Pydantic | Task involves request/response model definitions | ✅ |

**Select skills by number** (e.g., "use 1, 2, 3" or "all" or "remove 4"). Skills provide patterns and constraints — they don't dispatch separate processes.
```

Mark all domain-matched skills as pre-selected (✅) by default. The user can:
- **Approve all** — "approve" or "all look good"
- **Remove skills** — by number (e.g., "remove 4")
- **Add skills** — by name (e.g., "also add implement-docker")
- **Skip skills entirely** — "no skills, just agents"

#### 6e: Build Proposal — Agent Team

Follow [sdlc-shared/refs/propose-approve-execute.md](../sdlc-shared/refs/propose-approve-execute.md).

If Step 6c-multi identified loosely coupled areas for any agent type, the proposal table should show **multiple rows** for that agent type — one per scoped domain area. Use the `{agent-type}:{domain-area}` naming convention and give each instance its own scoped action.

**Standard proposal (no multi-instance):**

```markdown
## Proposed Agent Team — Task T-{N}: {Task Title}

| # | Agent Name | Subagent Type | Task-Specific Action | Estimated Scope |
|---|------------|---------------|----------------------|-----------------|
| 1 | python-implementer | python-implementer | {action tailored to this task} | M |
| 2 | api-implementer | api-implementer | {action tailored to this task} | M |
| 3 | data-implementer | data-implementer | {action tailored to this task} | M |
```

**Multi-instance proposal (when loosely coupled areas detected):**

```markdown
## Proposed Agent Team — Task T-{N}: {Task Title}

| # | Agent Name | Subagent Type | Scope | Task-Specific Action | Est. |
|---|------------|---------------|-------|----------------------|------|
| 1 | python-implementer:orders | python-implementer | `domains/orders/` | Implement CreateOrderFlow, OrderRepository port, and order domain models | M |
| 2 | python-implementer:inventory | python-implementer | `domains/inventory/` | Implement ReserveStockFlow, InventoryRepository port, and stock domain models | M |
| 3 | api-implementer | api-implementer | `domains/orders/routes/` | Implement POST /v1/orders endpoint from OpenAPI contract | S |
| 4 | data-implementer:orders | data-implementer | `domains/orders/` | Implement Order aggregate, OrderRepository, and migration | M |
| 5 | data-implementer:inventory | data-implementer | `domains/inventory/` | Implement StockItem aggregate, InventoryRepository, and migration | M |

**Multi-instance agents:** Rows 1-2 and 4-5 dispatch the same agent type to different domains in parallel. Each agent works only within its scoped directory and produces code independently. This is proposed because `orders` and `inventory` are loosely coupled bounded contexts with no shared types or cross-domain calls.
```

When presenting multi-instance proposals, always include the **"Multi-instance agents"** footnote explaining:
1. Which rows are multi-instance and why
2. That each agent is scoped to its own domain directory
3. The coupling rationale (why parallel is safe here)

This helps the user make an informed decision — they may know about coupling that isn't visible in the design artifacts and can merge instances back into a single agent if needed.

Tailor the "Task-Specific Action" column by reading the task's sub-tasks and lld.md contracts. For example:

- If the task involves creating a payment API endpoint: `api-implementer` action = "Implement POST /v1/payments endpoint from the OpenAPI contract in lld.md with request validation and error handling"
- If the task involves a data model: `data-implementer` action = "Implement Payment aggregate, PaymentRepository, and Alembic migration from the data model specification in lld.md"
- If the task is primarily about domain logic: `python-implementer` action = "Implement the CreatePaymentFlow orchestrating validation, persistence, and event publishing"

Only include agents relevant to the task — if the task has no frontend sub-tasks, don't propose `react-implementer`. Let the user add agents if they want broader coverage.

#### 6f: Present Combined Proposal and Await Approval

Present **both** the skills selection table and the agent team table together, then wait for user response. The user can:
- **Approve both** — proceed to dispatch
- **Modify skills** — add/remove skills by number or name
- **Modify agents** — add/remove agents by number or name, change actions
- **Merge multi-instance agents** — combine two instances of the same type back into one (e.g., "merge 1 and 2 into a single python-implementer") if they know the domains are more coupled than the analysis detected
- **Split a single agent** — request multi-instance dispatch for an agent that was proposed as single (e.g., "split the python-implementer into orders and inventory")
- **Approve skills only** — skip agents, Claude Code implements inline using selected skills
- **Approve agents only** — skip skills, agents work without skill context
- **Reject** — provide different direction

Never dispatch agents or invoke skills without explicit approval.

### Step 7: Invoke Skills and Dispatch Agents

After approval, execute in two phases: **skills first** (inline context), then **agents** (parallel dispatch).

#### 7a: Invoke Approved Skills

For each approved skill, invoke it via the `Skill` tool **before** dispatching agents. This loads the skill's patterns and constraints into Claude Code's context so that:

1. Any inline implementation work follows the skill's guidance
2. Agent prompts can reference the skill's key constraints

Invoke skills in dependency order (foundational skills first):
1. `implement-python` (if approved) — foundational patterns for all Python code
2. `implement-pydantic` (if approved) — model patterns used by API, data, and event skills
3. Domain-specific skills in any order: `implement-api`, `implement-data`, `implement-event`, `implement-react`, `implement-kubernetes`, `implement-pulumi`, `implement-docker`, `implement-cicd`, `implement-cli`

After loading each skill, briefly note the key constraints it provides (1-2 lines). Do **not** present the full skill content to the user — just confirm it was loaded.

```markdown
## Skills Loaded

- ✅ `implement-python` — Python 3.13+ patterns, strict typing, clean architecture
- ✅ `implement-api` — FastAPI handler patterns, OpenAPI compliance, Pydantic integration
- ✅ `implement-pydantic` — Pydantic V2 strict mode, immutability, validation patterns
```

#### 7b: Dispatch Approved Agents

Dispatch all approved agents via the Agent tool in a **single message** with multiple tool calls for parallel execution. This includes multi-instance agents — each instance is a separate Agent tool call dispatched in the same message.

Each agent receives a structured prompt that includes **references to the approved skills** so agents know which patterns to follow.

**Standard agent prompt (single-instance):**

```markdown
## Context

**Feature:** {feature-name}
**Feature Directory:** {feature-dir-path}
**Phase:** Implementation
**Task:** T-{N} — {task title}

## Your Assignment

{Approved task-specific action from the proposal table}

## Implementation Skills to Follow

The following skills have been approved for this task. Invoke each relevant skill via the `Skill` tool before writing code, and follow their patterns:

{List each approved skill with a one-line description of what it provides, e.g.:}
- `implement-python` — Follow for Python 3.13+ idioms, typing, and architecture patterns
- `implement-api` — Follow for FastAPI route handler structure and OpenAPI compliance
- `implement-pydantic` — Follow for Pydantic V2 model definitions and validation

Only invoke skills that are relevant to YOUR agent domain. For example, `api-implementer` should invoke `implement-api` and `implement-pydantic` but not `implement-kubernetes`.

## Artifacts to Read

- `{feature-dir}/README.md` — Feature inception document with vision and goals
- `{feature-dir}/prd.md` — Requirements with acceptance criteria
- `{feature-dir}/hld.md` — High-level design with service boundaries (if exists)
- `{feature-dir}/lld.md` — Low-level design with contracts, data models, and specs
- `{feature-dir}/tasks-breakdown.md` — Full task details (read Task T-{N} section)

## Task Details

{Copy the selected task's full entry from tasks-breakdown.md, including:}
- Description
- Sub-tasks relevant to this agent's domain
- Vertical slice definition

## Design Constraints

- Follow contracts-first: implement against the specs in lld.md
- Follow engineering principles from `.claude/rules/principles.md`
- Use shared libraries from `libs/` (see CLAUDE.md for library guide)
- Follow the ports-and-adapters service structure (see CLAUDE.md)

## Definition of Done

{Copy the task's Definition of Done from tasks-breakdown.md, highlighting the criteria relevant to this agent's domain:}
- Files: {specific file paths this agent should create/modify}
- Tests: {which test types this agent should produce, if any}
- Contracts: {which specs this agent's code must satisfy}
```

**Multi-instance agent prompt (scoped to a domain area):**

When dispatching a multi-instance agent (e.g., `python-implementer:orders`), add a **Scope Boundary** section to the standard prompt. This section constrains the agent to its assigned domain area so that parallel instances don't step on each other's files:

```markdown
## Scope Boundary

**Your domain scope:** {domain-area} (`{path-to-domain-directory}`)

You are one of multiple `{agent-type}` agents working on this task in parallel, each scoped to a different domain. Stay within your assigned scope:

- **Create/modify files only under:** `{path-to-domain-directory}/` and its corresponding test directory
- **Do NOT touch files in:** {list other domain directories being handled by sibling instances}
- **Shared types:** If you need types from shared libraries (`libs/`), import them — do not redefine them. If you need a type that doesn't exist yet in shared libraries, define it within your scoped domain and note it in your output summary for potential promotion to shared later.
- **Cross-domain contracts:** If your domain produces events consumed by a sibling domain, implement your side of the contract (the producer or consumer) per the specs in lld.md. The sibling agent handles the other side independently.
```

Use the scoped agent name (e.g., `python-implementer:orders`) as the Agent tool's `name` parameter and `description` parameter prefix so results are easy to identify.

If >6 agents are approved (including multi-instances), batch into groups of 6 per [sdlc-shared/refs/propose-approve-execute.md](../sdlc-shared/refs/propose-approve-execute.md):

1. Dispatch batch 1 (agents 1-6) in a single message
2. Wait for completion, present brief summary
3. Dispatch batch 2 (agents 7-12) with batch 1 outcomes as additional context
4. Repeat until all batches complete

#### 7c: Skills-Only Mode (No Agents)

If the user approved skills but no agents, Claude Code implements the task **inline** using the loaded skills as guidance. In this mode:

1. Follow the approved skills' patterns and constraints directly
2. Write code in the main Claude Code session (no subprocesses)
3. Work through the task's sub-tasks sequentially, applying each relevant skill's guidance
4. This is appropriate for smaller tasks or when the user prefers direct control over implementation

### Step 8: Collect Results and Present Summary

After all agents complete (or inline implementation finishes in skills-only mode), present an execution summary:

```markdown
## Implementation — Execution Summary

**Task:** T-{N} — {task title}

### Skills Used
| Skill | Purpose |
|-------|---------|
| `implement-python` | Python 3.13+ patterns, strict typing |
| `implement-api` | FastAPI handler patterns, OpenAPI compliance |
| `implement-pydantic` | Pydantic V2 model definitions |

### Agent Results
| Agent | Status | Files Created/Modified | Key Outcomes |
|-------|--------|----------------------|--------------|
| python-implementer:orders | ✅ Complete | {file list} | {summary of what was produced} |
| python-implementer:inventory | ✅ Complete | {file list} | {summary} |
| api-implementer | ✅ Complete | {file list} | {summary} |
| data-implementer | ✅ Complete | {file list} | {summary} |

### Artifacts Produced
- {bulleted list of all files created or modified across all agents}

### Next Steps
Run `/observe {feature-identifier}` to add observability instrumentation, `/test {feature-identifier}` to generate tests, or `/review {feature-identifier}` to review the implementation.
```

If skills-only mode was used (no agents), replace the "Agent Results" section with:

```markdown
### Inline Implementation
- **Mode:** Skills-only (no agents dispatched)
- **Files Created/Modified:** {file list}
- **Key Outcomes:** {summary of what was produced}
```

If any agent failed, report the failure clearly and ask the user whether to retry, skip, or adjust and re-dispatch. Do not silently drop failed agents.

### Step 9: Task Completion Tracking (FR-14)

After agents complete successfully and the user is satisfied with the results, update `tasks-breakdown.md` to reflect the task's progress:

#### Mark Task Status

Find the selected task's entry in `{feature-dir}/tasks-breakdown.md` and update it:

1. Add `✅ Complete` status indicator to the task heading or status field
2. Check off completed sub-tasks (`- [x]` instead of `- [ ]`)
3. Append a completion notes section after the task's Definition of Done:

```markdown
**Completion Notes:**
- **Status:** ✅ Complete
- **Date:** {YYYY-MM-DD}
- **Agents participated:** {list of agents that ran}
- **DoD criteria met:**
  - Files: {actual files created — compared against DoD file list}
  - Tests: {test status — created/pending}
  - Contracts: {which specs are satisfied}
- **Deviations:** {any deviations from the original plan, or "None"}
- **Work summary:** {1-2 sentence summary of what was implemented}
```

#### Handle Partial Completion

If some agents failed or produced incomplete output:
- Mark the task as `🔄 In Progress` rather than `✅ Complete`
- Note which sub-tasks are done and which need attention
- Do not mark the task complete until all Definition of Done criteria are met

#### Handle Deviations

If the implementation deviated from the original plan (scope changed, approach modified, new dependency discovered), document it explicitly in the completion notes:

```markdown
- **Deviations:**
  - Changed from REST to GraphQL for the product query endpoint (better fit for nested data)
  - Added T-4.5 sub-task for cache invalidation (discovered during implementation)
  - Dependency on T-2 was stronger than expected — required T-2's repository interface
```

### Step 10: Write SDLC Log Entry

After execution completes (whether agents dispatched, all-tasks-complete detected, or gate block), append an entry to `{feature-dir}/sdlc-log.md` following [sdlc-shared/refs/sdlc-log-format.md](../sdlc-shared/refs/sdlc-log-format.md):

```markdown
## [YYYY-MM-DD HH:MM] — /implement — Implementation

- **Task:** T-{N} — {task title}
- **Agents dispatched:** {list of agents that ran, or "None (all tasks complete)" or "None (gate blocked)"}
- **Skills invoked:** {skills used by agents — e.g., "implement-python, implement-api, implement-data"}
- **Artifacts produced:** {files created or modified}
- **Outcome:** {what was accomplished — e.g., "Task T-3 implemented: API endpoints, data models, and domain flows created. Task marked complete."}
- **Findings:** {any issues, dependency surprises, deviations — or "None"}
```

If `sdlc-log.md` doesn't exist, create it with the header first (see the shared ref for the header format).

---

## Acceptance Criteria Coverage

This skill addresses all six Given/When/Then scenarios from FR-8 plus all four from FR-14:

### FR-8: `/implement` — Per-Task Implementation

| # | Scenario | Covered By |
|---|----------|------------|
| 1 | tasks-breakdown.md exists → present task list with status, ask user to select | Step 3 — parses breakdown, displays task table with status |
| 2 | User selects task → discover implementer agents, propose relevant ones | Step 6 — scans agents, matches domains, builds proposal |
| 3 | New implementer agents added in future → auto-appear in proposals | Step 6 — dynamic scan of `.claude/agents/*-implementer.md` |
| 4 | User approves → agents execute in parallel per dimension | Step 7 — dispatches all approved agents in single message |
| 5 | Task has unsatisfied dependencies → warn user | Step 4 — dependency check with confirmation gate |
| 6 | /implement completes → append to sdlc-log.md | Step 10 — log entry appended after every execution path |

### FR-14: Task Completion Tracking

| # | Scenario | Covered By |
|---|----------|------------|
| 1 | Task passes implementation loop → mark ✅ Complete in tasks-breakdown.md | Step 9 — status update with completion notes |
| 2 | Task marked complete → notes section with DoD criteria, agents, summary | Step 9 — completion notes appended with structured fields |
| 3 | Implementation deviated from plan → notes document deviation with rationale | Step 9 — deviations section captures scope changes and surprises |
| 4 | User views task list → completed tasks show status, pending tasks distinguishable | Step 3 — task list displays ✅ Complete vs ⬜ Pending |

---

## Decision Tree (Full)

```
/implement invoked
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
Phase Gate: tasks-breakdown.md exists? (refs/phase-gating.md)
    |
    |-- No -> Block: "No task breakdown found. Run /tasks-breakdown first."
    |          -> END
    |
    v
Parse tasks-breakdown.md for task list and statuses
    |
    |-- All tasks complete?
    |       |
    |       v
    |   "All tasks complete. Run /sdlc for status."
    |       -> END
    |
    v
Present task list with status (Complete / Pending)
    |
    v
User selects a task (T-N)
    |
    v
Dependency Check: hard dependencies satisfied?
    |
    |-- No -> Warn user with dependency table
    |       |
    |       |-- User confirms -> proceed
    |       +-- User declines -> return to task selection
    |
    v
Read feature artifacts (README, prd, hld, lld) + task details
    |
    v
Discover implement-* skills (.claude/skills/) + *-implementer.md agents (.claude/agents/)
    |
    v
Match skills and agents to task's sub-tasks and dimensions
    |
    v
For each agent type matched to 2+ areas: assess domain coupling
    |
    |-- Loosely coupled (different contexts, no shared types) -> propose multi-instance
    +-- Tightly coupled (shared types, cross-calls, same context) -> keep single agent
    |
    v
Build skill selection table (pre-selected by domain match)
    |
    v
Build agent proposal table (with multi-instance rows where applicable)
    |
    v
Present BOTH proposals -> await user approval
    |
    |-- Approved (skills + agents) -> invoke skills, then dispatch agents
    |-- Approved (skills only)     -> invoke skills, implement inline
    |-- Approved (agents only)     -> dispatch agents without skill context
    |-- Modified                   -> update proposals, re-present
    +-- Rejected                   -> END
    |
    v
Invoke approved skills via Skill tool (foundational first)
    |
    v
Dispatch agents in parallel (batch if >6) OR implement inline (skills-only mode)
    |
    v
Collect results -> present execution summary (skills used + agent results)
    |
    v
Agent failures?
    |-- Yes -> report failures, ask: retry / skip / adjust
    +-- No  -> proceed
    |
    v
Update tasks-breakdown.md (Step 9)
    |
    |-- All DoD met -> mark task Complete + completion notes
    +-- Partial     -> mark task In Progress + partial notes
    |
    v
Append SDLC Log Entry (refs/sdlc-log-format.md)
    |
    v
END — "Run /observe, /test, or /review for task T-{N}"
```

---

## Patterns

### Do

- Discover both skills (`.claude/skills/implement-*`) and agents (`.claude/agents/*-implementer.md`) dynamically — new skills and agents are automatically proposed when added
- Present skills and agents as separate selection tables — skills guide how to write code, agents produce code in parallel
- Invoke approved skills via the `Skill` tool before dispatching agents — skills load patterns into context that agents can reference
- Include `implement-python` skill and `python-implementer` agent as cross-cutting when any Python code is involved
- Include approved skill names in agent prompts so agents know which skills to follow
- Read the task's full entry from tasks-breakdown.md before building the proposal — use sub-tasks, dimensions, and assignment hints to match skills and agents to the work
- Read lld.md contracts before crafting agent actions — agents implement against specs, not vague descriptions
- Present the dependency warning clearly but let the user proceed — they may have valid reasons to implement out of order
- Support skills-only mode — for smaller tasks the user may prefer inline implementation with skill guidance and no agents
- Track completion with structured notes — future `/sdlc` and `/implement` invocations rely on status accuracy
- Document deviations from the plan — the breakdown is a living document, not a rigid contract
- Dispatch all approved agents in a single message for parallel execution — sequential dispatch wastes time when agents work on independent dimensions
- Propose multi-instance agents for loosely coupled domains — two `python-implementer` agents scoped to independent bounded contexts finish faster than one working sequentially, with no quality loss since neither domain needs the other's implementation details
- Include a Scope Boundary section in multi-instance agent prompts — this prevents parallel agents of the same type from editing each other's files
- Always explain the coupling rationale in multi-instance proposals — the user may know about coupling invisible in the design artifacts and can merge instances back into one
- Default to single-agent when coupling is ambiguous — coherence from a single agent seeing both domains outweighs the speed gain of parallelism when domains interact

### Don't

- Skip the phase gate — if tasks-breakdown.md doesn't exist, there's nothing to implement against
- Dispatch agents or invoke skills without user approval — the propose-approve-execute pattern is non-negotiable
- Hardcode the skill or agent list — always scan `.claude/skills/` and `.claude/agents/` dynamically so new entries are automatically discovered
- Propose all skills and agents regardless of task domain — match to what the task actually needs
- Invoke skills that the user explicitly removed from the selection — respect user choices
- Mark a task complete when Definition of Done criteria are not met — partial completion should be marked as In Progress
- Propose multi-instance agents for tightly coupled domains — when one area imports types from the other, calls its ports, or shares aggregates, a single agent produces more coherent code
- Split agents across areas that share the same bounded context — code within a single bounded context is inherently coupled and benefits from one agent's holistic understanding
- Propose multi-instance for trivially small areas — if the work in each area is S-complexity (a few files), the overhead of scoping and coordinating two agents isn't worth the parallelism
- Write design artifacts (hld.md, lld.md) — that's `/design-system` and `/design-lld`'s job
- Write test code — that's `/test`'s job
- Write review verdicts — that's `/review`'s job
- Add observability instrumentation — that's `/observe`'s job
