# Acceptance Criteria & Decision Tree

> Full coverage tracing and decision tree for the /optimize orchestrator.

---

## Acceptance Criteria Coverage

### FR-9: `/optimize` — Optimization

| # | Scenario | Covered By |
|---|----------|------------|
| 1 | Implementation code exists -> scan for optimizer agents, propose relevant ones | Step 5 — scans `*-optimizer.md` agents, analyzes code patterns, builds proposal |
| 2 | New optimizer agents added -> auto-appear without modifying skill | Step 5 — dynamic scan of `.claude/agents/*-optimizer.md`, no hardcoded list |
| 3 | Review findings flagged optimization issues -> include as context | Step 4 — reads verdicts, filters findings by domain, routes to agents in Step 6 |
| 4 | User approves -> agents produce optimized code with before/after | Step 6 — dispatches with DoD; Step 7 — summary shows impact |
| 5 | /optimize completes -> append entry to sdlc-log.md | Step 8 — log entry for every execution path |

### Additional FR Coverage

| FR | Scenario | Covered By |
|----|----------|------------|
| FR-1 | Feature directory selection | Step 1 — feature resolution via shared ref |
| FR-2 | Phase gating (implementation code required) | Step 2 — blocks if no implementation code, directs to `/implement` |
| FR-3 | Propose -> Approve -> Execute pattern | Steps 5-6 — proposal table, user approval, parallel dispatch |
| FR-4 | Dynamic agent discovery | Step 5 — scans `.claude/agents/*-optimizer.md` dynamically |
| FR-16 | SDLC log entry | Step 8 — structured log entry with per-agent outcomes |

---

## Decision Tree (Full)

```
/optimize invoked
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
    |   Present task list -> user selects which to optimize
    |
    |-- Single task -> proceed with that task
    |
    v
=== REVIEW CONTEXT INTEGRATION ===
    |
    v
Check {feature-dir}/reviews/{task-name}/ for review verdicts
    |
    |-- Verdicts exist -> read all verdict files
    |       |
    |       v
    |   Filter for optimization-related findings (all domains)
    |       |
    |       |-- Findings found -> present table, classify by domain
    |       |                     (app performance / SQL OLTP / SQL OLAP)
    |       +-- No relevant findings -> note: "analyze independently"
    |
    +-- No verdicts -> note: "no review context available"
    |
    v
=== OPTIMIZER AGENT DISCOVERY ===
    |
    v
Discover *-optimizer.md agents (refs/agent-discovery.md)
    |
    v
Analyze code patterns to determine optimization dimensions
    |
    |-- Python app code (async, I/O, CPU, memory) -> match to app performance agents
    |-- SQL in OLTP context (repos, adapters, migrations) -> match to SQL OLTP agents
    |-- SQL in OLAP context (analytics, aggregations, dbt) -> match to SQL OLAP agents
    |-- Multiple dimensions present -> propose multiple agents
    |
    v
Build proposal table with domain-tailored actions
    |
    |-- Route review findings to appropriate agent domains
    |
    v
Present proposal -> await user approval
    |
    |-- Approved -> proceed to dispatch
    |-- Modified -> update proposal, re-present
    +-- Rejected -> END (log skip)
    |
    v
=== DISPATCH ===
    |
    v
Load refs/agent-routing.md for domain-specific prompt sections
    |
    v
Dispatch agents in parallel (batch if >6)
    |
    v
Collect results -> present execution summary with before/after analysis
    |
    |-- Review findings included? -> report which were addressed
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
