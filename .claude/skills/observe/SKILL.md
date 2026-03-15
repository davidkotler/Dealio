---
name: observe
description: |
  Orchestrate the observability phase of the SDLC — instrument implementation code with structured
  logging, distributed tracing, and metrics across all three observability pillars. Dynamically
  discovers all observer/observability agents from `.claude/agents/`, proposes them with their
  respective skills (observe-logs, observe-traces, observe-metrics), checks for observability
  contracts in design artifacts, and dispatches approved agents in parallel to instrument code.
  Use when entering the observability phase, running `/observe`, or when the user says "observe",
  "add observability", "instrument", "add logging", "add tracing", "add metrics", "add telemetry",
  "instrument code", "add structured logging", "add spans", "add OpenTelemetry", "observability
  instrumentation", "make observable", "add monitoring", "instrument this", "add o11y", or
  "observe this task". This skill requires implementation code to exist — it will block if no
  implementation code has been produced yet for the selected task.
---

# /observe — Observability Phase Orchestrator

> Discover observer agents, check for observability contracts in the design, and dispatch agents in parallel to instrument implementation code with logging, tracing, and metrics.

## Quick Reference

| Aspect | Details |
|--------|---------|
| **Phase** | Observability (per-task, within implementation loop) |
| **Gate** | Implementation code must exist for the selected task (run `/implement` first if missing) |
| **Produces** | Instrumented code with structured logging, distributed tracing spans, and application metrics |
| **Shared Refs** | `sdlc-shared/refs/feature-resolution.md`, `sdlc-shared/refs/phase-gating.md`, `sdlc-shared/refs/agent-discovery.md`, `sdlc-shared/refs/propose-approve-execute.md`, `sdlc-shared/refs/sdlc-log-format.md` |
| **Next Phase** | `/test` or `/review` (after instrumentation is added) |

---

## Core Workflow

### Step 1: Resolve Feature Directory

Follow the algorithm in [sdlc-shared/refs/feature-resolution.md](../sdlc-shared/refs/feature-resolution.md):

1. If the user passed an argument (e.g., `/observe 001-sdlc-claude-commands`) — resolve to the matching feature directory under `docs/designs/*/`
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

### Step 3: Task Context — Identify What to Instrument

Read the feature's context to understand what code needs instrumentation:

1. Read `{feature-dir}/tasks-breakdown.md` — identify which tasks have been implemented (marked `✅ Complete` or `🔄 In Progress`)
2. Read `{feature-dir}/sdlc-log.md` — find `/implement` entries to identify which code files were produced and which agents participated
3. Read `{feature-dir}/lld.md` — understand the service boundaries, API contracts, data flows, and event schemas that need observability coverage

If multiple tasks have been implemented, present them and ask the user which task(s) to instrument:

```markdown
## Implemented Tasks

| # | Task | Status | Files Produced |
|---|------|--------|---------------|
| T-1 | {Task 1 title} | ✅ Complete | {files from sdlc-log} |
| T-3 | {Task 3 title} | ✅ Complete | {files from sdlc-log} |

**Select which task(s) to instrument with observability.** You can select one task, multiple tasks (e.g., "T-1 and T-3"), or "all" for all implemented tasks.
```

If only one task has been implemented, proceed directly with that task's context.

### Step 4: Check for Observability Contracts in Design

Before building the agent proposal, check if the design artifacts include observability specifications:

1. **Read `{feature-dir}/lld.md`** — scan for sections mentioning:
   - Observability contracts or requirements
   - SLI/SLO definitions
   - Logging requirements or structured log schemas
   - Tracing requirements or span specifications
   - Metrics definitions (counters, histograms, gauges)
   - Health check specifications

2. **Read `{feature-dir}/hld.md`** (if exists) — scan for:
   - Cross-service tracing requirements
   - Observability architecture decisions
   - Monitoring and alerting strategy

3. **Check `docs/cross-cutting/`** — look for existing observability standards or contracts that apply to all services

If an observability contract is found, it will be included as context for the dispatched agents, so they can validate their instrumentation against the specified requirements. If no contract exists, the agents instrument based on best practices and the codebase's existing observability patterns (from `libs/lib-observability`).

#### Observability Contract Summary

If a contract is found, present it to the user:

```markdown
## Observability Contract Found

The design artifacts include observability specifications:

- **Logging:** {summary of logging requirements — e.g., "structured JSON logs with correlation IDs for all domain events"}
- **Tracing:** {summary of tracing requirements — e.g., "spans for all HTTP endpoints, database queries, and event handlers"}
- **Metrics:** {summary of metrics requirements — e.g., "request duration histograms, error counters, queue depth gauges"}
- **SLIs/SLOs:** {if defined — e.g., "p99 latency < 200ms, error rate < 0.1%"}

Agents will validate instrumentation against these contracts.
```

If no contract is found:

```markdown
## No Observability Contract Found

No explicit observability specifications found in the design artifacts. Agents will instrument based on:
- Codebase observability patterns (lib-observability conventions)
- Engineering principles (Section 1.10: Observability)
- Best practices for the identified service boundaries and data flows
```

### Step 5: Discover and Propose Observer Agents

#### Discover Observer Agents

Follow [sdlc-shared/refs/agent-discovery.md](../sdlc-shared/refs/agent-discovery.md):

1. Scan `.claude/agents/` for all `*-engineer.md` files
2. For each agent found, parse the filename to extract domain and role
3. Read the agent's `description` from frontmatter to understand its expertise

Currently expected agents:

| Agent | Domain | Specialization | Skills Used |
|-------|--------|----------------|-------------|
| `observability-engineer` | Observability | Structured logging, distributed tracing, metrics, dashboards, alerts | `observe-logs`, `observe-traces`, `observe-metrics` |

Future observer agents (e.g., `security-engineer.md`, `reliability-engineer.md`) will be automatically discovered and proposed when they appear in `.claude/agents/`.

#### Determine Observability Dimensions

Analyze the implementation code context to determine which observability pillars are relevant:

| Code Pattern | Observability Dimension | Agent Action Focus |
|--------------|------------------------|-------------------|
| HTTP routes, API endpoints | All three pillars | Request/response logging, endpoint spans, request duration metrics |
| Database queries, repository calls | Tracing + Metrics | DB operation spans, query duration histograms |
| Event handlers, consumers, producers | All three pillars | Event processing logs, message spans, throughput counters |
| Domain flows, orchestration logic | Logging + Tracing | Decision point logging, flow spans with business context |
| External service calls | Tracing + Metrics | Outbound spans, latency histograms, error counters |
| Background jobs, scheduled tasks | All three pillars | Job execution logs, job spans, success/failure counters |

Use this analysis to tailor the agent's task-specific action in the proposal.

#### Build Proposal Table

Follow [sdlc-shared/refs/propose-approve-execute.md](../sdlc-shared/refs/propose-approve-execute.md):

```markdown
## Proposed Agent Team — Observability Instrumentation

| # | Agent Name | Subagent Type | Task-Specific Action | Estimated Scope |
|---|------------|---------------|----------------------|-----------------|
| 1 | observability-engineer | observability-engineer | {action tailored to this task — see examples below} | M |
```

Tailor the "Task-Specific Action" based on the implementation context. Examples:

- If the task involves API endpoints and domain flows: "Instrument the CreateProduct API route with request/response logging, add distributed tracing spans for the flow and repository calls, and expose request duration and error rate metrics"
- If the task involves event handlers: "Add structured logging for event processing decisions, distributed tracing spans for handler execution and downstream calls, and throughput/latency metrics for the event consumer"
- If the task involves infrastructure setup: "Instrument health checks, startup/shutdown logging, and expose readiness/liveness probe metrics"

If an observability contract exists, append to the action: "Validate instrumentation against the observability contract in lld.md"

**Important:** Even though there is currently only one observer agent, the proposal table is still presented for user approval. The user may want to:
- Adjust the action's scope or focus
- Skip instrumentation for now
- Add additional agents if new observer agents have been added to the ecosystem

#### Present Proposal and Await Approval

Present the table and wait for user response. The user can:
- **Approve** — proceed to dispatch
- **Remove agents** — by number
- **Add agents** — by name (e.g., add an implementer agent to help with instrumentation wiring)
- **Modify actions** — change what the agent will focus on
- **Reject** — skip observability for now

Never dispatch agents without explicit approval.

### Step 6: Dispatch Approved Agents

After approval, dispatch all approved agents via the Task tool in a **single message** with multiple tool calls for parallel execution.

Each agent receives a structured prompt:

```markdown
## Context

**Feature:** {feature-name}
**Feature Directory:** {feature-dir-path}
**Phase:** Observability
**Task:** {task identifier and title, or "All implemented tasks"}

## Your Assignment

{Approved task-specific action from the proposal table}

## Artifacts to Read

- `{feature-dir}/README.md` — Feature inception document with vision and goals
- `{feature-dir}/prd.md` — Requirements (check for observability-related NFRs)
- `{feature-dir}/lld.md` — Low-level design (check for observability contracts, SLI/SLO definitions)
- `{feature-dir}/hld.md` — High-level design (if exists, check for cross-service tracing requirements)
- `{feature-dir}/sdlc-log.md` — Check /implement entries for files to instrument

## Implementation Files to Instrument

{List of code files produced by /implement that need instrumentation, extracted from sdlc-log.md or git status}

## Observability Contract

{If found: paste the relevant observability specifications from lld.md/hld.md}
{If not found: "No explicit observability contract. Instrument based on lib-observability conventions and engineering principles (Section 1.10)."}

## Codebase Conventions

- Use `lib-observability` for all instrumentation: `get_logger` for logging, `get_tracer` for tracing, `get_meter` for metrics
- Never use `print()` or stdlib `logging` — always use `lib-observability`
- Follow `.claude/rules/principles.md` Section 1.10: Observability
- Structured logging with bounded, typed fields
- Propagate trace IDs across all boundaries
- Health probes: separate liveness and readiness
- See existing service o11y/ directories for patterns

## Definition of Done

- Structured logging added to all decision points, error paths, and business events
- Distributed tracing spans for all I/O operations (HTTP, DB, events, external calls)
- Application metrics exposed for key business and operational indicators
- Trace IDs propagated across all service boundaries
- Health check probes instrumented (if applicable)
- {If contract exists: "All observability contract requirements from lld.md are satisfied"}
- No `print()` or stdlib `logging` usage — all through lib-observability
```

If >6 agents are approved (unlikely for observe, but future-proof), batch into groups of 6 per [sdlc-shared/refs/propose-approve-execute.md](../sdlc-shared/refs/propose-approve-execute.md).

### Step 7: Collect Results and Present Summary

After all agents complete, present an execution summary:

```markdown
## Observability — Execution Summary

**Task:** {task identifier and title}

| Agent | Status | Files Modified | Key Outcomes |
|-------|--------|---------------|--------------|
| observability-engineer | ✅ Complete | {file list} | {summary — e.g., "Added structured logging to 3 flows, tracing spans to 5 I/O operations, 4 metrics exposed"} |

### Instrumentation Added
- **Logging:** {summary of logging additions}
- **Tracing:** {summary of tracing spans added}
- **Metrics:** {summary of metrics exposed}
- **Contract compliance:** {if contract exists: "All contract requirements met" or "N of M requirements met — see findings"}

### Artifacts Modified
- {bulleted list of all files modified with brief description of changes}

### Next Steps
Run `/test {feature-identifier}` to generate tests (including observability validation), or `/review {feature-identifier}` to review the implementation and instrumentation.
```

If any agent failed, report the failure clearly and ask the user whether to retry, skip, or adjust and re-dispatch. Do not silently drop failed agents.

### Step 8: Write SDLC Log Entry

After execution completes (whether agents dispatched, gate block, or skip), append an entry to `{feature-dir}/sdlc-log.md` following [sdlc-shared/refs/sdlc-log-format.md](../sdlc-shared/refs/sdlc-log-format.md):

```markdown
## [YYYY-MM-DD HH:MM] — /observe — Observability

- **Task:** {task identifier and title, or "N/A"}
- **Agents dispatched:** {list of agents that ran, or "None (gate blocked)" or "None (user skipped)"}
- **Skills invoked:** {skills used by agents — e.g., "observe-logs, observe-traces, observe-metrics"}
- **Artifacts produced:** {files modified with observability instrumentation}
- **Outcome:** {what was accomplished — e.g., "Instrumented CreateProduct flow: structured logging at 5 decision points, tracing spans for 3 I/O operations, 4 metrics exposed. Observability contract validated."}
- **Findings:** {any issues, missing coverage, contract gaps — or "None"}
```

If `sdlc-log.md` doesn't exist, create it with the header first (see the shared ref for the header format).

---

## Acceptance Criteria Coverage

This skill addresses all four Given/When/Then scenarios from FR-10:

### FR-10: `/observe` — Observability Instrumentation

| # | Scenario | Covered By |
|---|----------|------------|
| 1 | Implementation code exists → discover observer/observability agents, propose with skills | Step 5 — scans `*-engineer.md` agents, proposes with observe-logs/traces/metrics skills |
| 2 | User approves → structured logging, tracing spans, and metrics added to code | Step 6 — dispatches agents with instrumentation assignment; Step 7 — reports what was added |
| 3 | Observability contract exists in design → validate instrumentation against contract | Step 4 — checks lld.md/hld.md for contract; Step 6 — includes contract in agent prompt |
| 4 | /observe completes → append entry to sdlc-log.md | Step 8 — log entry appended after every execution path |

---

## Decision Tree (Full)

```
/observe invoked
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
    |   Present task list -> user selects which to instrument
    |
    |-- Single task -> proceed with that task
    |
    v
Check for observability contracts in lld.md / hld.md
    |
    |-- Contract found -> summarize and include in agent context
    +-- No contract -> note: agents instrument based on best practices
    |
    v
Discover *-engineer.md agents (refs/agent-discovery.md)
    |
    v
Analyze code patterns to determine observability dimensions
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
Dispatch agents in parallel (batch if >6)
    |
    v
Collect results -> present execution summary
    |
    |-- Contract exists? -> report compliance status
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
END — "Run /test or /review for this task"
```

---

## Patterns

### Do

- Check for observability contracts in the design before proposing agents — contract-driven instrumentation is more valuable than ad-hoc additions
- Read sdlc-log.md to identify which files were produced by `/implement` — these are the primary instrumentation targets
- Include codebase conventions (lib-observability, principles.md Section 1.10) in every agent prompt — consistency matters
- Propose the observability-engineer even as the only agent — the user may want to adjust scope or skip, and the proposal pattern is consistent
- Tailor the agent action to the specific code patterns found (API routes, event handlers, domain flows) rather than using generic "add observability" instructions
- Report instrumentation coverage across all three pillars (logging, tracing, metrics) in the execution summary

### Don't

- Skip the phase gate — instrumenting code that doesn't exist yet is wasteful
- Dispatch agents without user approval — the propose-approve-execute pattern is non-negotiable
- Hardcode the agent list — always scan `.claude/agents/` dynamically so new observer agents are automatically discovered
- Add observability as a checkbox exercise — instrumentation should be meaningful and aligned with the service's operational needs
- Modify business logic — observability instrumentation adds signals without changing behavior
- Write tests — that's `/test`'s job
- Write review verdicts — that's `/review`'s job
- Produce design artifacts — that's `/design-system` and `/design-lld`'s job
