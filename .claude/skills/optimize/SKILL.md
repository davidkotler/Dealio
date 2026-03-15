---
name: optimize
description: |
  Orchestrate the optimization phase of the SDLC — performance profiling, CPU/memory/I/O tuning,
  SQL query optimization (OLTP and OLAP), Redis optimization, PostgreSQL tuning, and targeted code
  optimization with dynamically discovered optimize skills. Scans `.claude/skills/optimize-*/SKILL.md`
  for all optimize skills (performance, sql-oltp, sql-olap, postgresql, redis, and any future
  optimize skills), analyzes implementation context to determine which optimization domains apply,
  checks for review findings that flagged performance or optimization issues, proposes relevant
  optimize skills for user approval, and dispatches approved skills — via matching agents when
  available, or directly via the Skill tool when no agent exists. Use when entering the optimization
  phase, running `/optimize`, or when the user says "optimize", "optimize code", "optimize performance",
  "make it faster", "performance tuning", "speed up", "reduce latency", "reduce memory",
  "improve throughput", "optimize queries", "optimize SQL", "slow query", "query optimization",
  "index tuning", "database optimization", "optimize Redis", "optimize cache", "optimize this",
  "run optimizer", "profile and optimize", "performance optimization", "optimize this task",
  "make it efficient", "tune performance", "optimize the implementation", "warehouse query
  optimization", or "OLTP/OLAP optimization". This skill requires implementation code to exist —
  it will block if no implementation code has been produced yet for the selected task.
---

# /optimize — Optimization Phase Orchestrator

> Discover optimize skills across all domains, enrich with review findings, and dispatch via agents (when available) or directly via the Skill tool to produce optimized code with before/after analysis.

## Quick Reference

| Aspect | Details |
|--------|---------|
| **Phase** | Optimization (per-task, within implementation loop) |
| **Gate** | Implementation code must exist for the selected task (run `/implement` first if missing) |
| **Produces** | Optimized code with before/after measurements or analysis |
| **Shared Refs** | `sdlc-shared/refs/feature-resolution.md`, `sdlc-shared/refs/phase-gating.md`, `sdlc-shared/refs/agent-discovery.md`, `sdlc-shared/refs/propose-approve-execute.md`, `sdlc-shared/refs/sdlc-log-format.md` |
| **Next Phase** | `/test` (to validate optimizations), `/review` (to re-review after optimization), or task complete |

---

## Core Workflow

### Step 1: Resolve Feature Directory

Follow [sdlc-shared/refs/feature-resolution.md](../sdlc-shared/refs/feature-resolution.md):

1. If argument provided (e.g., `/optimize 001-sdlc-claude-commands`) — resolve to matching feature directory under `docs/designs/*/`
2. If no argument — scan `docs/designs/` across all years, present selection list
3. If no match — error + selection list
4. If "create new" — assign next sequence number, create `docs/designs/YYYY/NNN-{kebab-case-name}/`

The resolved path becomes `{feature-dir}` for all subsequent steps.

### Step 2: Phase Gate — Require Implementation Code

Follow [sdlc-shared/refs/phase-gating.md](../sdlc-shared/refs/phase-gating.md):

1. **Check `{feature-dir}/tasks-breakdown.md`** — exists? If not, block: "Run `/tasks-breakdown` first, then `/implement`."
2. **Check `{feature-dir}/sdlc-log.md`** — look for `/implement` entries with successful outcome
3. **Check git** — `git log --oneline --grep="{feature-name}" -- '*.py' '*.ts' '*.tsx' '*.sql'`
4. **Check task status** — if any implementation sub-tasks are marked started/complete
5. **Fallback** — ask the user

Be pragmatic: if there's evidence code exists, proceed. Don't block users who wrote code outside the orchestrator flow.

### Step 3: Task Context — Identify What to Optimize

1. Read `{feature-dir}/tasks-breakdown.md` — identify implemented tasks (marked `✅ Complete` or `🔄 In Progress`)
2. Read `{feature-dir}/sdlc-log.md` — find `/implement` entries for produced files and participating agents
3. Read `{feature-dir}/lld.md` — understand service boundaries, data flows, performance-critical paths

If multiple tasks implemented, present selection:

```markdown
## Implemented Tasks

| # | Task | Status | Files Produced |
|---|------|--------|---------------|
| T-1 | {Task 1 title} | ✅ Complete | {files from sdlc-log} |

**Select which task(s) to optimize.** Select one, multiple (e.g., "T-1 and T-3"), or "all".
```

If only one task, proceed directly.

### Step 4: Check for Review Findings Related to Optimization

Scan `{feature-dir}/reviews/{task-name}/` for review verdicts containing optimization-related findings:

- **Performance findings** — CPU, memory, I/O, async efficiency issues
- **Data/SQL findings** — N+1 queries, missing indexes, SARGability violations, partition pruning failures, transaction design issues
- **API findings** — response time concerns, payload size, missing pagination
- **Python findings** — O(n^2) algorithms, string concatenation in loops, sequential awaits
- **Observability findings** — high-cardinality metrics, expensive logging

Filter keywords: performance, slow, latency, memory, CPU, N+1, query, index, cache, batch, parallel, sequential, O(n), timeout, throughput, bottleneck, inefficient, optimize, pagination, eager loading, lazy loading, connection pool, SARGability, partition, warehouse, execution plan, deadlock, transaction, lock contention, covering index, implicit conversion

If findings found, present them in a table grouped by domain (application performance vs SQL). If none, note that optimization will be analysis-driven rather than review-driven.

### Step 5: Discover and Propose Optimize Skills

#### Discover Skills (Primary)

Skills are the source of truth for optimization capabilities. Scan skills first, then look for agents.

1. **Scan `.claude/skills/optimize-*/SKILL.md`** for all optimize skills
2. Parse directory name to extract domain (e.g., `optimize-redis` → `redis`, `optimize-sql-oltp` → `sql-oltp`)
3. Read each skill's `description` from frontmatter to understand its scope

#### Discover Agents (Secondary)

After discovering skills, check for matching agents that can dispatch them:

1. Scan `.claude/agents/` for `*-optimizer.md` files
2. Match agents to skills by naming convention: `{domain}-optimizer.md` → `optimize-{domain}/SKILL.md`
3. Note which skills have agents and which don't — both are dispatchable

#### Discovery Result Table

Present the discovered skills with their agent status:

| Skill | Domain | Agent Available | Dispatch Method |
|-------|--------|----------------|-----------------|
| `optimize-performance` | Application Performance | `performance-optimizer` | Pre-Built Agent (parallel) |
| `optimize-sql-oltp` | SQL OLTP | `sql-oltp-optimizer` | Pre-Built Agent (parallel) |
| `optimize-sql-olap` | SQL OLAP | `sql-olap-optimizer` | Pre-Built Agent (parallel) |
| `optimize-postgresql` | PostgreSQL | `postgresql-optimizer` | Pre-Built Agent (parallel) |
| `optimize-redis` | Redis | `redis-optimizer` | Pre-Built Agent (parallel) |
| `optimize-cache` *(example)* | Caching | *none* | Inline Agent (parallel) |

This table is for reference — always discover dynamically. New skills (e.g., `optimize-cache/SKILL.md`)
are automatically discovered and usable even without a matching agent.

**Dispatch methods (in priority order):**
- **With agent**: Dispatch via Agent tool using the pre-built agent definition for parallel execution (preferred — richest context)
- **Inline agent**: Dispatch via Agent tool with a dynamically constructed prompt from the skill's SKILL.md (parallel execution without a pre-built agent)
- **Direct**: Invoke via Skill tool in the current session (sequential — use only when inline agent is impractical)

#### Determine Optimization Dimensions

Analyze the implementation code to determine which optimization dimensions are relevant. Match code patterns to discovered skills using their descriptions — don't hardcode skill-to-pattern mappings:

| Code Pattern | Optimization Dimension | Matching Skill |
|--------------|----------------------|----------------|
| Async functions with multiple `await` calls | Async efficiency | `optimize-performance` |
| Loop-heavy processing, data transforms | CPU efficiency | `optimize-performance` |
| Large object creation, collection materialization | Memory efficiency | `optimize-performance` |
| External HTTP calls, service integrations | I/O optimization | `optimize-performance` |
| Event handlers, message consumers | Throughput optimization | `optimize-performance` |
| Repository methods with SQL, ORM queries, inline SQL in OLTP context | OLTP query optimization | `optimize-sql-oltp` |
| Stored procedures, transaction-heavy code, migration DDL, index design | OLTP schema & transaction design | `optimize-sql-oltp` |
| Analytical SQL, aggregations, window functions, GROUP BY queries | OLAP query optimization | `optimize-sql-olap` |
| Star/snowflake schema queries, dbt models, warehouse SQL | Warehouse optimization | `optimize-sql-olap` |
| PostgreSQL config, VACUUM, autovacuum, PG-native indexes, partitioning | PostgreSQL infrastructure | `optimize-postgresql` |
| Redis client usage (redis-py, ioredis), cache get/set patterns | Redis data modeling & caching | `optimize-redis` |
| Redis Streams, consumer groups, XREADGROUP, pub/sub | Redis message processing | `optimize-redis` |
| Redis configuration, connection pooling, `maxmemory`, eviction | Redis infrastructure tuning | `optimize-redis` |
| Rate limiting with Redis, distributed locks, Lua scripts | Redis advanced patterns | `optimize-redis` |

**Multiple skills are common.** A feature with Python API code that queries PostgreSQL and caches in Redis
may need `optimize-performance` (async/I/O in Python), `optimize-postgresql` (PG config and queries),
and `optimize-redis` (caching patterns and memory). Propose all relevant skills.

#### Build Proposal Table

Follow [sdlc-shared/refs/propose-approve-execute.md](../sdlc-shared/refs/propose-approve-execute.md). Tailor "Task-Specific Action" per skill's domain. Examples:

- **`optimize-performance`**: "Profile and optimize the {flow}: parallelize independent async calls, optimize I/O patterns, and produce before/after latency analysis"
- **`optimize-sql-oltp`**: "Analyze SQL in {repositories/adapters}: SARGability, indexing (ESR rule), transaction design, concurrency patterns. Produce optimized SQL with execution plan analysis"
- **`optimize-sql-olap`**: "Optimize analytical queries in {path}: CTE pipeline architecture, partition pruning, platform-specific tuning for {platform}. Estimate scan reduction"
- **`optimize-postgresql`**: "Analyze PostgreSQL config, VACUUM health, index types, and partitioning. Produce exact postgresql.conf changes with engine-level rationale"
- **`optimize-redis`**: "Analyze Redis usage in {adapters/infra}: key design, data structure selection, memory optimization, connection management, caching patterns, and pipelining opportunities. Produce before/after memory and latency analysis"
- **With review findings**: "Address reviewer-identified issues: {list}. Also analyze for additional opportunities beyond review findings."

Present the proposal table with dispatch method for each skill:

```markdown
## Optimization Proposal

| # | Skill | Domain | Task-Specific Action | Dispatch |
|---|-------|--------|---------------------|----------|
| 1 | `optimize-redis` | Redis | Analyze Redis caching in {path}... | Agent: `redis-optimizer` |
| 2 | `optimize-performance` | App Perf | Profile async patterns in {flow}... | Agent: `performance-optimizer` |
| 3 | `optimize-cache` | Caching | Review cache invalidation strategy... | Inline Agent (no pre-built agent) |

**Approve, modify, or reject.** All skills dispatch via Agent tool for parallel execution — pre-built agents provide richer context, inline agents are constructed dynamically from the skill's SKILL.md. Direct Skill tool invocation is the fallback.
```

Never dispatch without explicit approval.

### Step 6: Dispatch Approved Skills

**Three dispatch methods** — choose based on agent availability. Every skill is dispatchable; a missing agent never blocks execution.

#### Method A: Pre-Built Agent (preferred — richest context)

When a matching agent definition exists in `.claude/agents/{domain}-optimizer.md`, dispatch via the Agent tool. The pre-built agent carries identity, workflow, quality gates, and handoff protocols.

**Load [refs/agent-routing.md](refs/agent-routing.md) for domain-specific prompt sections** — it contains codebase conventions, domain context, and Definition of Done items per optimization domain.

Base prompt structure for both Method A and Method B:

```markdown
## Context

**Feature:** {feature-name}
**Feature Directory:** {feature-dir-path}
**Phase:** Optimization
**Task:** {task identifier and title, or "All implemented tasks"}

## Your Assignment

{Approved task-specific action from the proposal table}

## Skill Reference

Read and follow: `.claude/skills/{skill-name}/SKILL.md`
{If skill has references: "Deep reference: `.claude/skills/{skill-name}/references/*.md`"}

## Artifacts to Read

- `{feature-dir}/README.md` — Feature inception document
- `{feature-dir}/prd.md` — Requirements (performance NFRs, SLA targets)
- `{feature-dir}/lld.md` — Low-level design (performance budgets, scalability)
- `{feature-dir}/hld.md` — High-level design (if exists)
- `{feature-dir}/sdlc-log.md` — /implement entries for files to optimize

## Implementation Files to Optimize

{List of code files from sdlc-log.md or git status}

## Review Findings Context

{Filtered findings routed to this skill's domain from Step 4, or "No review-identified issues. Analyze independently."}

## Domain-Specific Context

{Include the appropriate section from refs/agent-routing.md based on the skill's domain}

## Definition of Done

- All identified bottlenecks profiled with measurement data or analysis justification
- Targeted optimizations applied to hot paths and reviewer-identified issues
- Before/after measurements or analysis provided for every optimization
- No behavioral changes — optimizations preserve existing functionality
- No new `print()` or stdlib `logging` — use lib-observability if adding metrics
{Include domain-specific DoD items from refs/agent-routing.md}
```

Dispatch all agent-backed skills in a **single message** for parallel execution.
If >6 skills have agents, batch into groups of 6 per propose-approve-execute shared ref.

#### Method B: Inline Agent (when no pre-built agent exists)

When a skill has no matching agent definition, **construct an inline agent dynamically** and dispatch via the Agent tool. This enables parallel execution for any skill — a missing agent file never forces sequential processing.

1. Read the skill's `SKILL.md` — extract its description, workflow, and analysis lenses
2. Construct the agent prompt using the **same base prompt structure** from Method A above
3. Add a preamble that sets the agent's role from the skill's description:

```markdown
## Role

You are a {domain} optimization specialist. Follow the workflow defined in
`.claude/skills/{skill-name}/SKILL.md` to analyze and optimize the implementation files below.
```

4. Dispatch via the Agent tool alongside Method A agents in the **same message** for parallel execution

**Key difference from Method A:** The inline agent lacks the pre-built agent's identity, handoff protocols, and quality gates — but it has the full skill SKILL.md and references, which contain the domain expertise. This is sufficient for effective optimization.

#### Method C: Direct Skill Invocation (fallback)

Invoke the skill directly using the Skill tool in the current session. Use this only when:
- The skill is very lightweight and doesn't warrant a subagent
- You need to run the skill interactively with user input at intermediate steps

Run direct-invocation skills **after** agent-dispatched skills complete. This ensures all optimization domains are covered.

### Step 7: Collect Results and Present Summary

```markdown
## Optimization — Execution Summary

**Task:** {task identifier and title}

| Skill | Dispatch | Status | Files Modified | Key Outcomes |
|-------|----------|--------|---------------|--------------|
| {skill} | {Pre-Built Agent / Inline Agent / Direct} | ✅ Complete | {files} | {summary} |

### Optimizations Applied

| # | Optimization | File | Before | After | Impact |
|---|-------------|------|--------|-------|--------|
| 1 | {description} | {file:line} | {before} | {after} | {impact} |

### Review Findings Addressed
{Table of which reviewer findings were resolved, if any — omit if none}

### Next Steps
Run `/test` to validate optimizations, or `/review` to re-review the optimized implementation.
```

Report skill failures clearly. Ask whether to retry, skip, or adjust and re-dispatch.

### Step 8: Write SDLC Log Entry

Append to `{feature-dir}/sdlc-log.md` per [sdlc-shared/refs/sdlc-log-format.md](../sdlc-shared/refs/sdlc-log-format.md):

```markdown
## [YYYY-MM-DD HH:MM] — /optimize — Optimization

- **Task:** {task identifier and title, or "N/A"}
- **Skills invoked:** {skills used — e.g., "optimize-performance, optimize-sql-oltp, optimize-redis"}
- **Dispatch method:** {per skill — "Agent: {name}" or "Direct (Skill tool)"}
- **Artifacts produced:** {files modified}
- **Outcome:** {summary}
- **Findings:** {issues, trade-offs, or "None"}
```

---

## Patterns

### Do

- Discover skills first — scan `.claude/skills/optimize-*/SKILL.md` as the source of truth for optimization capabilities
- Check review verdicts before proposing skills — targeted optimization beats speculative optimization
- Include before/after measurements in every skill's Definition of Done
- Read design artifacts for performance budgets and SLA targets
- Propose multiple skills when code spans domains (e.g., Python API code + SQL queries + Redis caching)
- Route review findings to the right skill domain (SQL findings → SQL skill, app findings → perf skill, cache findings → Redis skill)
- Tailor skill actions to specific code patterns, not generic "optimize the code"
- Match discovered skills to code dimensions using skill descriptions, not hardcoded rules
- Check for agents after discovering skills — agents are optional dispatchers, not required
- Report trade-offs — some optimizations increase complexity

### Don't

- Skip the phase gate — can't optimize code that doesn't exist
- Dispatch without user approval — propose-approve-execute is non-negotiable
- Hardcode the skill list — always scan `.claude/skills/optimize-*/SKILL.md` dynamically
- Fall back to sequential Direct invocation when an inline agent would work — construct an inline agent from the skill's SKILL.md for parallel execution even without a pre-built agent
- Optimize prematurely — target measured or reviewer-identified bottlenecks
- Change business logic — preserve existing behavior
- Send SQL findings to the application performance skill or vice versa — route to the right domain
- Overlap with other phases: tests → `/test`, reviews → `/review`, observability → `/observe`

---

## Deep References

| Reference | When to Load |
|-----------|-------------|
| [refs/agent-routing.md](refs/agent-routing.md) | Step 6 — domain-specific context, conventions, and DoD items for agent-dispatched skills |
| [refs/coverage.md](refs/coverage.md) | When verifying acceptance criteria or tracing the full decision tree |
