---
name: tasks-breakdown
description: >
  Decompose a designed feature into ordered, parallelizable, independently deliverable implementation
  tasks with dependency mapping and clear definitions of done. Use when breaking features into work
  items, planning implementation sequences, or when the user says "break this down", "create tasks",
  "plan the implementation", "what do I build first", "task breakdown", or runs /tasks-breakdown.
  This skill requires completed discovery (prd.md) and design (lld.md) artifacts — it bridges the
  gap between design and implementation. Always use this skill before starting /implement on an Epic.
---

# /tasks-breakdown — Task Decomposition

> Decompose designed features into ordered, parallelizable, independently deliverable implementation tasks — bridging the gap between design and the per-task implementation loop.

## Quick Reference

| Aspect | Details |
|--------|---------|
| **Phase** | Breakdown (between Design and Implementation) |
| **Gates** | `prd.md` + `lld.md` must exist |
| **Reads** | `README.md`, `prd.md`, `hld.md` (if exists), `lld.md` |
| **Produces** | `tasks-breakdown.md` (overview) + `tasks/{nnn}-{task-name}.md` (per-task details) |
| **Shared Refs** | `sdlc-shared/refs/feature-resolution.md`, `sdlc-shared/refs/phase-gating.md`, `sdlc-shared/refs/sdlc-log-format.md` |
| **Deep Refs** | `refs/slicing-patterns.md`, `refs/dependency-graph.md`, `refs/dimensions-checklist.md` |
| **Next Phase** | `/implement` (per-task implementation loop) |

### Where This Fits in the SDLC

```
/discover-feature → /discover-requirements → /design-system → /design-lld → /tasks-breakdown → /implement
                                                                                  ▲ YOU ARE HERE
```

The Discover phase produces the **business and product context** (`README.md`, `prd.md`). The Design phase produces the **technical blueprint** (`hld.md`, `lld.md`). This skill reads both to produce an actionable task list that the implementation loop consumes task by task.

### Output Structure

The skill produces two complementary artifacts — a high-level overview and per-task detail files:

```
{feature-dir}/
├── tasks-breakdown.md          # Overview: summary, dependency graph, tier map, PRD coverage, risks
└── tasks/
    ├── 001-{task-name}.md      # Full details for task 1
    ├── 002-{task-name}.md      # Full details for task 2
    └── ...
```

The separation serves a purpose: when working on a specific task during `/implement`, you only need to read that task's file — not the entire breakdown. The overview document provides navigation and high-level context without the noise of every sub-task and verification step.

---

## Core Workflow

### Step 1: Resolve Feature Directory

Follow the algorithm in [sdlc-shared/refs/feature-resolution.md](../sdlc-shared/refs/feature-resolution.md):

1. If the user passed an argument (e.g., `/tasks-breakdown 001-auth-service`) — resolve to the matching feature directory under `docs/designs/*/`
2. If no argument — scan `docs/designs/` across all years, present a selection list of existing features
3. If argument doesn't match — report the error and present the selection list
4. If "create new" — assign next sequence number, create `docs/designs/YYYY/NNN-{kebab-case-name}/`

The resolved path becomes `{feature-dir}` for all subsequent steps.

### Step 2: Phase Gate

Two gates must pass before decomposition can begin:

#### Gate A: Requirements Exist

```
Check: {feature-dir}/prd.md exists and is non-empty?
  ├─► Yes → Proceed to Gate B
  └─► No  → Block:
            "No requirements found in {feature-dir}/."
            "Run `/discover-feature` then `/discover-requirements` to produce prd.md."
            → END
```

#### Gate B: Low-Level Design Exists

```
Check: {feature-dir}/lld.md exists and is non-empty?
  ├─► Yes → Proceed to Step 3
  └─► No  → Block:
            "No low-level design found in {feature-dir}/."
            "Run `/design-lld` first to produce lld.md."
            → END
```

These are existence checks only — if the files exist and are non-empty, the gates pass.

### Step 3: Detect Current State

Scan the feature directory to determine whether a breakdown already exists:

```
{feature-dir} resolved, gates passed
    │
    ├─► tasks-breakdown.md exists OR tasks/ directory exists?
    │       └─► Breakdown EXISTS → Step 3A
    │
    └─► Neither exists?
            └─► Enter DECOMPOSITION → Step 4
```

#### Step 3A: Existing Breakdown Detected

Read the existing breakdown and present its summary with options:

```markdown
## Breakdown Exists

A task breakdown already exists for this feature:
- `{feature-dir}/tasks-breakdown.md`
- `{feature-dir}/tasks/` ({N} task files)

**Summary:** {total tasks, estimated complexity, critical path, parallelization tiers}

**Options:**
1. **Refine** — Keep the existing breakdown and adjust specific tasks based on feedback
2. **Regenerate** — Start fresh with a new decomposition from the design artifacts
3. **Advance** — Proceed to `/implement {feature-identifier}` to start implementation

Which would you prefer?
```

- **Refine** → proceed to Step 4 with the existing breakdown as additional context (evolve, don't recreate)
- **Regenerate** → proceed to Step 4 without the existing breakdown
- **Advance** → suggest running `/implement {feature-identifier}` and END

### Step 4: Gather Context — Read All Upstream Artifacts

Before decomposing, read every available design artifact to build a complete picture of both business intent and technical design:

1. **`{feature-dir}/README.md`** — Vision, goals, rationale, value proposition (from `/discover-feature`)
2. **`{feature-dir}/prd.md`** — Functional requirements, non-functional requirements, acceptance criteria, MoSCoW classification, risk register (from `/discover-requirements`)
3. **`{feature-dir}/hld.md`** — System boundaries, bounded contexts, integration patterns, technology decisions (from `/design-system`, if exists)
4. **`{feature-dir}/lld.md`** — API contracts (OpenAPI), event schemas (AsyncAPI), data models, component designs, module structures (from `/design-lld`)

Also examine the existing codebase to understand:
- Current service structure and module conventions
- Existing domain patterns that the feature must integrate with
- Shared libraries already in use
- Infrastructure already provisioned

The goal is to decompose against concrete contracts and real codebase context — not against abstract requirements.

#### Build the Upstream Context Map

As you read each artifact, build a map of which requirements, architectural decisions, and technical designs apply to which areas of the system. This map feeds into Step 7 where you populate per-task context sections. Track:

- **From prd.md:** Which functional requirements (FRs) and their specific acceptance criteria govern each capability. Which non-functional requirements (NFRs) constrain it — performance targets, security policies, reliability guarantees. Which business rules, constraints, and glossary terms apply.
- **From hld.md:** Which architectural decisions (ADRs) and their rationale apply to each component area. Which technology choices, integration patterns, resilience strategies, quality attributes, and security requirements are relevant. Which bounded context relationships and ubiquitous language terms matter.
- **From lld.md / lld-*.md:** Which data model definitions (tables, columns, indexes, access patterns), API contracts (endpoint signatures, request/response models), event schemas (event types, field definitions, consumer topology), port interfaces (method signatures, protocols), adapter specifications, and flow designs define the implementation.

Each task file must be self-contained for implementation — an implementer reading only that task file should have the business rules, architectural constraints, and technical specifications needed to build it correctly and coherently with the overall design, without referencing the upstream documents.

### Step 5: Identify Vertical Slices

Decompose the feature into **vertical slices** — thin end-to-end increments that each deliver a testable, reviewable, committable capability.

```
 Vertical slice (correct):
   "Create product → persist → expose via API → display in UI"
   One thin path through ALL layers for one capability.

 Horizontal slice (wrong):
   "Build all database models" → "Build all API routes" → "Build all UI"
   Complete layers in isolation with no deliverable until the end.
```

Each slice must deliver a **working increment** that can be:
- Merged via a single Pull Request
- Verified through concrete manual checks
- Demonstrated as "something the system couldn't do before"

#### Slicing Strategies (choose based on feature shape)

| Strategy | When to use |
|----------|------------|
| **By user-facing operation** (CRUD) | Domain entities with clear lifecycle — most common |
| **By business rule variant** | Same operation with meaningfully different behavior per variant |
| **By integration point** | Feature connects to multiple external systems |
| **By domain boundary** | Feature spans multiple bounded contexts |
| **By data complexity** | Complex data model — start minimal, enrich |

For detailed slicing patterns, when horizontal extraction is justified, and splitting heuristics, see **[refs/slicing-patterns.md](refs/slicing-patterns.md)**.

### Step 6: Apply the Dimension Checklist

For each vertical slice, walk through every **implementation dimension** to identify concrete sub-tasks:

| Dimension | What to identify |
|-----------|-----------------|
| **Data** | Schema changes, migrations, models, seeds, indexes |
| **Code/Logic** | Domain entities, value objects, flows, validation, errors |
| **API** | Route handlers, request/response models, middleware, pagination |
| **Event** | Producers, consumers, handlers, schemas, idempotency |
| **Web/UI** | Components, pages, state, data fetching, accessibility |
| **Infra** | Cloud resources, config, secrets, networking, K8s manifests |
| **Verification** | Manual checks — bash commands, API calls, UI walkthrough to confirm the slice works |

Not every slice touches every dimension. Skip dimensions that don't apply, but **consciously evaluate each one** — missed dimensions are the primary source of scope creep mid-implementation.

> **Note:** Tests and observability telemetry are handled by the dedicated `/test` and `/observe` skills during the implementation loop. Do not include test or observability sub-tasks in the breakdown — focus on what the code *does*, not how it's tested or instrumented.

For per-dimension questions, common artifacts, and frequently missed items, see **[refs/dimensions-checklist.md](refs/dimensions-checklist.md)**.

### Step 7: Structure Tasks and Sub-Tasks

Each **Task** is a vertical slice — independently deliverable, committed as a single branch, reviewed through a PR.

Each Task contains **Sub-Tasks** — the dimension-level work items within that slice.

```
Task 1: Create Product (vertical slice)
├── Sub-Task 1.1: Data — Product table migration + persistence model
├── Sub-Task 1.2: Logic — Product aggregate + CreateProduct flow
├── Sub-Task 1.3: API — POST /v1/products route + request/response models
├── How to Verify: [manual checks]
└── Definition of Done: [what "done" means]
```

**Task granularity rule:** Each task should be completable in **1-3 focused sessions**. If larger, split into thinner vertical slices. If smaller, combine with related work.

**Complexity estimates:**
- **S** (Small) — < 1 session
- **M** (Medium) — 1-2 sessions
- **L** (Large) — 2-3 sessions
- If anything is **XL** — decompose further. XL tasks are a signal that the slice is too thick.

#### Map Upstream Context to Each Task

For each task, identify and extract the specific upstream context that governs its implementation:

1. **Requirements:** Which FRs, NFRs, and acceptance criteria from `prd.md` does this task address? Quote the specific acceptance criteria verbatim — they are the behavioral contract the implementation must satisfy. Include relevant business rules and constraints.
2. **Architecture:** Which ADRs, technology decisions, integration patterns, resilience policies, security requirements, and quality attributes from `hld.md` constrain or guide this task? Include the decision rationale so the implementer understands *why*, not just *what*.
3. **Technical Design:** Which data model definitions (table schemas, columns, indexes), API contracts (endpoints, request/response shapes), event schemas (event types, fields), port interfaces (method signatures), adapter specifications, and flow designs from `lld.md` / `lld-*.md` does this task implement? Include enough detail (field names, types, method signatures, sequence of operations) that the implementer can build against the design specification without opening the LLD.

Extract only what is relevant to the specific task — not the entire upstream document. The task file should contain the minimum necessary context for correct, aligned, and coherent implementation.

### Step 8: Map Dependencies and Parallelization

#### Identify Dependencies

For each task, determine:

- **Hard dependencies** — must complete before this task can start (e.g., data model before the API route that queries it)
- **Soft dependencies** — easier if done first but not strictly required (e.g., shared library before consumer, but consumer can mock against a port)

Express dependencies as a **directed acyclic graph (DAG)**. If circular dependencies appear, the breakdown is wrong — extract the shared concern into a separate task.

#### Group into Parallelization Tiers

Tasks with no mutual hard dependencies can execute concurrently. Group them into tiers:

```
Tier 0 (Foundation):  [Task 1: Data models]  [Task 2: Shared types]
                              ↓                       ↓
Tier 1 (Core Logic):  [Task 3: Domain logic] ←── depends on T1 + T2
                              ↓
Tier 2 (Integration): [Task 4: API routes]   [Task 5: Event handlers]  ← parallel
                              ↓                       ↓
Tier 3 (Frontend):    [Task 6: UI components] ←── depends on T4
```

#### Identify Critical Path

The critical path is the longest chain of hard dependencies — it determines the minimum elapsed time regardless of parallelization. Document it explicitly so scope-cutting decisions can be informed.

For detailed dependency mapping techniques, critical path analysis, and parallelization strategies, see **[refs/dependency-graph.md](refs/dependency-graph.md)**.

### Step 9: Assign Ordering and Complexity

Produce a **topologically sorted** implementation sequence that:

1. Respects hard dependencies
2. Prioritizes foundational work (data models, domain types, shared contracts) before dependent work
3. Enables early integration testing
4. Front-loads riskier or more uncertain work — discovering that something is harder than expected is cheaper early

Estimate complexity per task: **S**, **M**, or **L**. If anything exceeds L, decompose further.

### Step 10: Define Definition of Done

Every task gets a **Definition of Done (DoD)** that specifies:

| DoD Element | Description |
|-------------|-------------|
| **Files created/modified** | Explicit list of paths |
| **How to verify** | Manual verification steps — bash commands, curl/httpie calls, UI walkthrough, DB queries |
| **Acceptance criteria** | Observable behavior from the user's perspective |
| **Contract compliance** | Which specs (OpenAPI, AsyncAPI, data schema) the task satisfies |
| **Expected behaviors** | Concrete input→output mappings for happy path, error paths, and state side effects (see below) |
| **Boundary conditions** | Edge cases and limits derived from the design contracts and domain rules |
| **Invariants** | Always-true postconditions that hold after the task's code executes successfully |

#### Writing Expected Behaviors

Expected behaviors are the behavioral specification of the task — they define *what correct looks like* without prescribing how to verify it programmatically. Think of them as QA-ready acceptance criteria precise enough that someone could understand correct behavior without reading the upstream design docs.

For each task, specify behaviors across three categories:

| Category | What to capture | Example |
|----------|----------------|---------|
| **Happy path** | Input→output for the primary success scenario | `POST /v1/products {"name": "Widget", "price": 9.99}` → `201` with `{"id": "<uuid>", "name": "Widget", "price": 9.99, "created_at": "<iso8601>"}` |
| **Error paths** | Input→output for each expected failure mode | `POST /v1/products {"name": ""}` → `422` with validation error naming the `name` field; `POST /v1/products {"name": "Widget", "price": -1}` → `422` with constraint violation on `price` |
| **State side effects** | What changes in the system after the operation | After successful `POST /v1/products`: a new row exists in `products` table with matching `id`; `product.created` domain event is published with the product ID |

#### Writing Boundary Conditions

Boundary conditions capture the edge cases and limits that the design implies but doesn't always spell out. Derive them from:

- Field constraints in the data model (max lengths, allowed ranges, nullability)
- API contract limits (pagination bounds, payload size, rate limits)
- Domain rules (minimum quantity = 1, price must be positive, name uniqueness per tenant)
- Concurrency scenarios (duplicate submission, concurrent updates to same entity)

**Example:** For a "Create Product" task: empty name rejected, name at max length (255 chars) accepted, duplicate name within same tenant rejected, price of 0.01 accepted (minimum), price of 0 rejected.

#### Writing Invariants

Invariants are postconditions that must always hold after the task's code runs — regardless of which path was taken. They express system-level correctness guarantees.

**Example invariants:**
- Every product in the database has a non-null `id`, `name`, `price`, and `created_at`
- The `products` table row count never decreases (soft-delete only)
- Every successful mutation publishes exactly one domain event
- Response `id` always matches the persisted entity's `id`

> **Important distinction:** Expected behaviors, boundary conditions, and invariants define *what correct behavior is* — the specification. They never prescribe test structure, test tooling, assertion libraries, or how to verify programmatically. The `/test` skill handles that translation. Think: "what does QA need to know?" not "what should the test file look like?"

#### Writing "How to Verify" Steps

Every task needs concrete, runnable verification steps that confirm functional correctness. These are **manual checks** — not automated tests (those come later in the implementation loop).

Pick verification methods appropriate to the dimension:

| Dimension | Verification examples |
|-----------|----------------------|
| **Data** | `psql -c "SELECT * FROM products LIMIT 5;"`, check migration ran, inspect table schema |
| **Logic** | `python -c "from myservice.domains.products.models.domain import Product; ..."` — instantiate and exercise domain objects |
| **API** | `curl -X POST http://localhost:8000/v1/products -H 'Content-Type: application/json' -d '{"name":"Widget"}'` — verify 201 + response shape |
| **Event** | Publish test event, confirm handler processes it, verify DLQ is empty |
| **Web/UI** | Open `http://localhost:3000/products`, click "Create", fill form, submit — confirm redirect, toast, list update |
| **Infra** | `pulumi preview`, `kubectl get pods -n <ns>`, `aws s3 ls s3://bucket-name` — confirm resources provisioned |

**Good verification is:**
- **Specific** — exact command, URL, payload, or UI action (not "verify the API works")
- **Observable** — describes expected output
- **Quick** — under 2 minutes per task
- **Covers happy + error** — e.g., POST with valid data (201) and POST with missing field (422)

### Step 11: Tiered Approval

Present the decomposition to the user progressively — tier by tier. This gives the user control at each level of detail and prevents wasted effort on fine-grained details if the high-level structure is wrong.

#### Tier 1 Gate — Epic-Level Slices

Extract the major vertical slices and present them:

```markdown
## Tier 1 — Epic-Level Slices

The feature decomposes into these major vertical slices:

| # | Slice | Description | Estimated Tasks |
|---|-------|-------------|-----------------|
| 1 | {slice name} | {what capability it delivers end-to-end} | ~{N} |
| 2 | {slice name} | {what capability it delivers} | ~{N} |

**Total estimated tasks:** {N across all slices}

**Approve these slices?** You can:
- **Approve** — continue to Tier 2
- **Add/Remove/Merge/Split** slices
- **Reject** with feedback
```

If rejected or modified: adjust and re-present Tier 1. For substantial changes, re-run decomposition with feedback.

#### Tier 2 Gate — Task-Level Breakdown

Once Tier 1 is approved, present the task-level breakdown for each slice:

```markdown
## Tier 2 — Task-Level Breakdown

### {Slice 1 Name}

| # | Task | Complexity | Hard Dependencies | Parallelizable With |
|---|------|-----------|-------------------|---------------------|
| T-1 | {task title} | M | None (foundation) | T-2 |
| T-2 | {task title} | S | None | T-1 |
| T-3 | {task title} | L | Hard: T-1 | T-4 |

### Summary
- **Total tasks:** {N}
- **Estimated complexity:** {X}S + {Y}M + {Z}L
- **Critical path:** T-1 → T-3 → T-7 ({description})
- **Parallelization tiers:** {N} tiers, max {M} concurrent

### Dependency Graph
(Mermaid diagram showing task DAG)

**Approve?** You can: Approve, Split, Merge, Reorder, Adjust complexity, Reject
```

#### Tier 3 Gate — Task Details

Once Tier 2 is approved, write the full breakdown to files — task details are too voluminous for inline conversation and are better reviewed in the user's editor. This is a write-first, review-in-editor, iterate-on-feedback loop.

##### Step A: Write Artifacts

Write both artifact types using the templates defined in Step 12:

1. **Write `{feature-dir}/tasks-breakdown.md`** — the navigational overview using the Step 12A template (summary, dependency graph, tier map, implementation sequence with per-task summaries linking to detail files, PRD coverage matrix, risk notes)
2. **Create `{feature-dir}/tasks/` and write one file per task** — using the Step 12B template (description, vertical slice, sub-tasks, verification steps, expected behaviors, boundary conditions, invariants, definition of done)

Each task file must be self-contained — readable without opening other task files or the overview.

##### Step B: Present Summary and Request Review

After writing, present a concise summary in the conversation — not the full task content:

```markdown
## Tier 3 — Task Details Written

Artifacts written for review:
- `{feature-dir}/tasks-breakdown.md` — overview with {N} tasks across {M} tiers
- `{feature-dir}/tasks/` — {N} task detail files:
  - `001-{name}.md` — {one-line description} ({complexity})
  - `002-{name}.md` — {one-line description} ({complexity})
  - ...

**Summary:** {total tasks} tasks, {X}S + {Y}M + {Z}L complexity, critical path: {description}

**Please review the files in your editor**, then come back and tell me:
- **Approve** — proceed to implementation
- **Request changes** — which tasks or sections to modify (e.g., "T-3 needs an additional sub-task for X", "split T-5 into two tasks", "the verification steps for T-2 are too vague")
- **Reject** — I'll rework the breakdown from scratch based on your feedback
```

The summary gives the user a map of what was written and where to look, without repeating the content that's already in the files.

##### Step C: Iterate on Feedback

When the user requests changes:

1. **Edit only the specific files mentioned** — don't rewrite everything. If the user says "T-3 needs X", edit `tasks/003-{name}.md`
2. **If structural changes affect the overview** (task added, removed, reordered, renamed), update `tasks-breakdown.md` as well
3. **Re-present the updated summary** showing what changed — e.g., "Updated `tasks/003-{name}.md` — added sub-task 3.4 for {description}. Updated `tasks-breakdown.md` to reflect new complexity estimate."
4. **Wait for the next round of feedback**
5. Repeat until the user approves

The goal is tight, file-based iteration: write once, refine in-place, minimize conversation noise. The user's editor is the review surface, the conversation is for coordination.

### Step 12: Artifact Templates

The Tier 3 gate writes two complementary artifact types using these templates:

#### 12A: Write `{feature-dir}/tasks-breakdown.md` (Overview)

This document is the navigational hub — it provides high-level context without per-task noise. Anyone reading this file should understand the feature's implementation plan, task ordering, and coverage without needing to open individual task files.

```markdown
# Task Breakdown: {Feature Name}

## Summary

- **Total tasks:** {N}
- **Estimated complexity:** {X}S + {Y}M + {Z}L
- **Critical path:** {longest dependency chain with description}
- **Parallelization tiers:** {N} tiers, max {M} tasks concurrent

## Dependency Graph

{Mermaid diagram showing task DAG with tier coloring}

## Implementation Sequence

### Tier 0 — {Name}

#### T-1: {Title}
- **Description:** {what this task delivers}
- **Vertical slice:** {the thin end-to-end capability}
- **Complexity:** {S|M|L}
- **Dependencies:** None (foundation)
- **Parallelizable with:** {[T-N, T-N]}
- **Details:** [001-{name}.md](tasks/001-{name}.md)

#### T-2: {Title}
- **Description:** {what this task delivers}
- **Vertical slice:** {the thin end-to-end capability}
- **Complexity:** {S|M|L}
- **Dependencies:** None
- **Parallelizable with:** {[T-N, T-N]}
- **Details:** [002-{name}.md](tasks/002-{name}.md)

### Tier 1 — {Name}

#### T-3: {Title}
- **Description:** {what this task delivers}
- **Vertical slice:** {the thin end-to-end capability}
- **Complexity:** {S|M|L}
- **Dependencies:** Hard: T-1, T-2
- **Parallelizable with:** {[T-N, T-N]}
- **Details:** [003-{name}.md](tasks/003-{name}.md)

### Tier {N} — {Name}
...

## PRD Coverage Matrix

| PRD Requirement / Acceptance Criteria | Task(s) | Status |
|---------------------------------------|---------|--------|
| {AC from prd.md} | T-{N} | Covered |
| {AC from prd.md} | T-{N}, T-{M} | Covered |

## Risk Notes

- {risks identified during decomposition — uncertain areas, missing info, spikes needed}
```

#### 12B: Write `{feature-dir}/tasks/{nnn}-{task-name}.md` (Per-Task Details)

Create the `tasks/` directory inside the feature directory, then write one file per task. The filename uses zero-padded task number and kebab-case name (e.g., `001-create-product.md`, `002-list-products.md`).

Each task file is self-contained — it has everything needed to implement that task without reading the full breakdown or other task files.

```markdown
# Task {N}: {Title}

## Description

{What this task delivers — the capability, not the implementation steps}

## Vertical Slice

{The thin end-to-end path this task cuts through the system}

- **Complexity:** {S|M|L}
- **Dependencies:** {None | Hard: [T-N] | Soft: [T-N]}
- **Parallelizable with:** {[T-N, T-N]}

## Relevant Requirements

### Functional Requirements
- **{FR-ID}: {FR Title}** — {Quoted acceptance criteria from prd.md that this task must satisfy}
- **{FR-ID}: {FR Title}** — {Another relevant acceptance criterion}

### Non-Functional Requirements
- **{NFR-ID}: {NFR Title}** — {Specific performance target, reliability guarantee, or security constraint from prd.md that applies to this task}

### Business Rules & Constraints
- {Specific business rules, domain invariants, or constraints from prd.md that the implementation must enforce — e.g., "Mandatory categories cannot be disabled by org admins", "90-day retention policy"}

## Architecture & System Context

### Technology & Decisions
- {Relevant ADR with rationale — e.g., "ADR-002: Redis Streams over Kafka — simplicity, existing stack, lib-faststream abstraction enables future swap"}
- {Technology choices affecting this task — e.g., "FastStream via lib-faststream for event consumption", "asyncpg for DB access"}
- {Shared library usage — e.g., "lib-resilience http_call_policy wraps email provider calls"}

### Integration Patterns
- {How this task's component integrates — e.g., "Inbound: consumes NotificationRequested from Redis Streams consumer group via lib-faststream"}
- {Cross-component data flow — e.g., "After persist, publishes to Redis Pub/Sub for SSE fan-out"}

### Quality Attributes
- {Resilience requirements — e.g., "Circuit breaker: 5 consecutive failures → open, 30s half-open. Retry: exponential backoff, max 3 attempts"}
- {Security requirements — e.g., "organization_id mandatory on all queries; zero cross-org data leakage"}
- {Observability requirements — e.g., "Structured log events: notification.received, notification.delivered, notification.delivery_failed"}

## Technical Design Reference

### Data Models
- {Relevant table schemas, columns, types, and indexes from lld-data.md — e.g., "notifications table: id (UUIDv7 PK), organization_id, user_id, category, title, body, deep_link, priority, created_at, read_at, dismissed_at"}
- {Access patterns — e.g., "AP-1: List by user, sorted by created_at DESC, filtered by category, cursor-paginated"}

### API Contracts
- {Relevant endpoint signatures from lld-api.md — e.g., "GET /api/v1/notifications → ListNotificationsResponse (cursor-paginated)"}
- {Request/response model fields — e.g., "UpdateNotificationRequest: { read_at: datetime | null } strict=True, frozen=True"}

### Event Schemas
- {Relevant event types and fields from lld-event.md — e.g., "NotificationRequested: category, priority, recipient_ids, title, body, deep_link, template_context"}
- {Consumer topology — e.g., "Consumer group: notification-worker, topic: notification.requested"}

### Ports & Adapters
- {Relevant port interface methods from lld-code.md — e.g., "NotificationRepository.save(notification, org_id) → Notification"}
- {Adapter specifications — e.g., "PostgresNotificationRepository implements NotificationRepository using asyncpg"}

### Flows & Logic
- {Flow orchestration design from lld-code.md — e.g., "ProcessNotificationFlow: validate category → check idempotency → load org preferences → for each recipient: create Notification → persist → deliver per channel → record delivery → publish fan-out"}

## Sub-Tasks

- [ ] {N}.1 {Dimension}: {Description} — {Acceptance criteria}
- [ ] {N}.2 {Dimension}: {Description} — {Acceptance criteria}
- [ ] {N}.3 {Dimension}: {Description} — {Acceptance criteria}

## How to Verify

- `{bash command or curl call}` — expected: {what you should see}
- Open `{URL}` → {UI action} → confirm: {expected behavior}
- `{DB query}` — expected: {row shape or count}

## Expected Behaviors

### Happy Path
- `{input}` → `{output}` — {description of correct result}

### Error Paths
- `{invalid input}` → `{error output}` — {which constraint is violated}
- `{another invalid input}` → `{error output}` — {which constraint is violated}

### State Side Effects
- After `{operation}`: {what state changed in the system}

## Boundary Conditions

- {field/parameter} at minimum accepted value → {expected result}
- {field/parameter} at maximum accepted value → {expected result}
- {field/parameter} beyond limit → {expected rejection}
- {concurrency/duplication scenario} → {expected behavior}

## Invariants

- {postcondition that always holds after this task's code executes}
- {data integrity guarantee}
- {consistency rule across related state}

## Definition of Done

- **Files:** {explicit file paths created/modified}
- **Contracts:** {which specs (OpenAPI, AsyncAPI, data schema) satisfied}
- **Acceptance:** {observable behavior from user's perspective}
```

#### After Approval

When the user approves the breakdown (after the Tier 3 review loop), present a brief completion message and suggest the next phase:

```markdown
## Breakdown Complete

All artifacts finalized:
- `{feature-dir}/tasks-breakdown.md` — overview with {N} tasks across {tiers} tiers
- `{feature-dir}/tasks/` — {N} task detail files

**Next step:** Run `/implement {feature-identifier}` to start the implementation loop.
Each task file is self-contained — `/implement` reads one task at a time.
```

### Step 13: Write SDLC Log Entry

After the artifacts are written, append an entry to `{feature-dir}/sdlc-log.md` following [sdlc-shared/refs/sdlc-log-format.md](../sdlc-shared/refs/sdlc-log-format.md):

```markdown
## [YYYY-MM-DD HH:MM] — /tasks-breakdown — Breakdown

- **Task:** N/A
- **Agents dispatched:** None (direct decomposition)
- **Skills invoked:** tasks-breakdown
- **Artifacts produced:** tasks-breakdown.md, tasks/{nnn}-{task-name}.md ({N} files)
- **Outcome:** {what was accomplished — e.g., "Feature decomposed into N tasks across M tiers. Critical path: T-1 → T-3 → T-7."}
- **Findings:** {risks, scope gaps, deviations — or "None"}
```

If `sdlc-log.md` doesn't exist, create it with the header first (see the shared ref for the header format).

---

## Decision Tree

```
/tasks-breakdown invoked
    │
    ▼
Resolve Feature Directory (sdlc-shared/refs/feature-resolution.md)
    │
    ├─► Argument provided → resolve path
    ├─► No argument → present selection list
    ├─► No match → error + selection list
    └─► Create new → assign sequence, create directory
    │
    ▼
Phase Gate A: prd.md exists?
    │
    ├─► No → Block: "Run /discover-feature then /discover-requirements first." → END
    │
    ▼
Phase Gate B: lld.md exists?
    │
    ├─► No → Block: "Run /design-lld first." → END
    │
    ▼
Detect Current State
    │
    ├─► tasks-breakdown.md or tasks/ exists?
    │       │
    │       ▼
    │   Present summary, offer options
    │       │
    │       ├─► Advance → suggest /implement → END
    │       ├─► Refine → proceed with existing as context
    │       └─► Regenerate → proceed fresh
    │
    └─► Neither exists
    │
    ▼
Gather Context (README, prd, hld, lld + codebase)
    │
    ▼
Identify Vertical Slices (refs/slicing-patterns.md)
    │
    ▼
Apply Dimension Checklist (refs/dimensions-checklist.md)
    │
    ▼
Structure Tasks & Sub-Tasks
    │
    ▼
Map Dependencies & Parallelization (refs/dependency-graph.md)
    │
    ▼
Assign Ordering & Complexity
    │
    ▼
Define Definition of Done + How to Verify
    │
    ▼
Tier 1 Gate: Present epic-level slices ◄──┐
    │                                     │
    ├─► Approved → proceed                │
    ├─► Modified → adjust, re-present ────┘
    └─► Rejected → re-decompose
    │
    ▼
Tier 2 Gate: Present task-level breakdown ◄──┐
    │                                        │
    ├─► Approved → proceed                   │
    ├─► Modified → adjust, re-present ───────┘
    └─► Rejected → re-decompose
    │
    ▼
Tier 3 Gate: Write artifacts to files
    │
    ▼
Write tasks-breakdown.md (overview)
    │
    ▼
Write tasks/{nnn}-{task-name}.md (per task)
    │
    ▼
Present summary + file paths ◄─────────────┐
    │                                       │
    ▼                                       │
User reviews files in editor                │
    │                                       │
    ├─► Approved → proceed                  │
    ├─► Changes requested → edit files ─────┘
    └─► Rejected → re-decompose
    │
    ▼
Append SDLC Log Entry
    │
    ▼
END — "Run /implement {feature} to start the implementation loop"
```

---

## Quality Gates

Before finalizing the task breakdown, verify:

- [ ] Every task is a vertical slice delivering a verifiable increment
- [ ] Every task has explicit hard/soft dependencies
- [ ] Every task has a Definition of Done with files, verification steps, and acceptance criteria
- [ ] Every task has concrete "How to Verify" steps with runnable commands and expected outputs
- [ ] No task exceeds L complexity (2-3 sessions)
- [ ] Dimension checklist was applied to every task (consciously skipped or addressed)
- [ ] Critical path is identified and total tiers are documented
- [ ] Parallelization groups are assigned
- [ ] All prd.md acceptance criteria are covered in the PRD Coverage Matrix
- [ ] Every task specifies expected behaviors (happy path, error paths, and state side effects)
- [ ] Boundary conditions are listed for tasks that touch data validation, API contracts, or domain rules
- [ ] Invariants are defined for tasks that mutate state or enforce consistency guarantees
- [ ] Every task includes the specific FRs, NFRs, and acceptance criteria from prd.md that it addresses
- [ ] Every task includes relevant architectural decisions, integration patterns, and quality attributes from hld.md
- [ ] Every task includes relevant data models, API contracts, event schemas, and port/adapter specifications from lld.md / lld-*.md
- [ ] Upstream context in each task is scoped to that task only — no full-document dumps
- [ ] Each task file is self-contained — an implementer can build correctly without opening prd.md, hld.md, or lld.md
- [ ] Overview written to `{feature-dir}/tasks-breakdown.md`
- [ ] Per-task details written to `{feature-dir}/tasks/{nnn}-{task-name}.md`

---

## Patterns

### Do

- Read ALL upstream artifacts (README, prd, hld, lld) before starting — business context shapes decomposition as much as technical design
- Slice vertically — every task delivers a verifiable, deployable increment
- Reference concrete design artifacts in each task (spec paths, model names, contract versions)
- Front-load data models and shared types — they unblock everything downstream
- Include concrete "How to Verify" steps for every task — bash commands, curl calls, UI walkthroughs
- Map dependencies explicitly — unstated dependencies cause blocked work
- Apply the dimension checklist exhaustively — the dimension you skip is the one that bites mid-implementation
- Present each tier separately and wait for approval — users validate incrementally
- Include the existing breakdown as context when refining — evolve, don't recreate from scratch
- Cross-reference prd.md acceptance criteria against proposed tasks via the PRD Coverage Matrix — every AC should map to at least one task
- Write expected behaviors precise enough that someone could write tests from them without reading upstream design docs — they are the behavioral specification, not a summary
- Derive boundary conditions from concrete contract constraints (field lengths, value ranges, uniqueness rules) rather than inventing abstract edge cases
- Make each task file self-contained — it should be understandable without reading other task files
- Extract and embed relevant upstream context (requirements, architecture decisions, technical designs) in each task file — the implementer should not need to reference prd.md, hld.md, or lld.md during implementation
- Quote specific acceptance criteria from prd.md verbatim rather than paraphrasing — precision prevents misinterpretation and implementation drift from business intent
- Include ADR rationale, not just the decision — understanding *why* helps implementers make correct micro-decisions when edge cases arise
- Include concrete technical design details (table columns, endpoint signatures, port methods, flow sequences) from lld.md — vague references like "see LLD" defeat the purpose of self-contained tasks

### Don't

- Skip the phase gates — if prd.md or lld.md don't exist, decomposition has no foundation
- Decompose without reading prd.md — technical design without business context produces correct but wrong features
- Slice horizontally — "all models, then all routes, then all UI" delivers nothing until everything is done
- Create tasks without a Definition of Done — ambiguous completion leads to rework
- Assume sequential execution — identify parallelization, even if current team is one person
- Create XL tasks — if you can't describe the DoD concisely, the task is too big
- Include test or observability sub-tasks — those are handled by `/test` and `/observe` in the implementation loop
- Prescribe which implementation loop skills to use per task — the skills self-select based on context
- Write vague verification like "check it works" — be specific: exact command, expected output
- Copy entire sections of prd.md, hld.md, or lld.md into task files — extract only the relevant subset for each task
- Omit upstream context because "it's in the design docs" — task files must be self-contained for implementation
- Paraphrase acceptance criteria loosely — quote them precisely from prd.md to prevent implementation drift from business intent
- Write vague technical design references like "see LLD for data model" — include the actual column names, types, method signatures, and flow sequences
- Present all 3 tiers at once — tiered approval exists so users validate incrementally
- Dump Tier 3 task details into the conversation — write to files and let the user review in their editor; the conversation is for coordination, not content
- Write implementation code — that's `/implement`'s job
- Write design artifacts — that's `/design-system` and `/design-lld`'s job
- Design test cases, test structure, or specify testing tools — only define what correct behavior is; the `/test` skill decides how to verify it programmatically
- Confuse behavioral specification with test plans — expected behaviors describe *what correct looks like*, not *how to check it*
- Duplicate information across the overview and task files — the overview has the map, task files have the territory

---

## Deep References

Load these refs as needed for detailed guidance:

- **[refs/slicing-patterns.md](refs/slicing-patterns.md)** — Vertical vs horizontal slicing, when horizontal extraction is justified, splitting heuristics, ordering strategies
- **[refs/dimensions-checklist.md](refs/dimensions-checklist.md)** — Per-dimension guiding questions, common artifacts, frequently missed items
- **[refs/dependency-graph.md](refs/dependency-graph.md)** — Dependency mapping techniques, critical path analysis, parallelization strategies, anti-patterns
