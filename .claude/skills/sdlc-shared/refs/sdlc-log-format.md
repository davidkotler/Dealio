# SDLC Log Format

> How orchestrator skills write structured activity entries to `sdlc-log.md` for full traceability.

---

## Purpose

Every orchestrator skill appends a structured entry to `{feature-dir}/sdlc-log.md` after execution completes. The log provides a chronological record of all SDLC activity for a feature — which commands were run, which agents were dispatched, what artifacts were produced, and what the outcomes were.

The log is append-only. Entries are never modified or deleted. Only the orchestrator skill writes to the log — individual agents never write to it directly (to prevent concurrent write conflicts).

---

## File Creation

If `sdlc-log.md` does not exist when the first orchestrator skill runs, create it with this header:

```markdown
# SDLC Activity Log

> Chronological record of all SDLC orchestrator activity for this feature.

---
```

Then append the first entry below the header.

---

## Entry Format

Each entry follows this structure:

```markdown
## [YYYY-MM-DD HH:MM] — /{command} — {phase}

- **Task:** {task name, or "N/A" if not task-specific}
- **Agents dispatched:** {comma-separated list of agent names}
- **Skills invoked:** {comma-separated list of skills used by agents, or "N/A"}
- **Artifacts produced:** {comma-separated list of files created or modified}
- **Outcome:** {1-2 sentence summary of what was accomplished}
- **Findings:** {issues, warnings, or notes — or "None"}
```

### Field Descriptions

| Field | Description | Example |
|-------|-------------|---------|
| **Timestamp** | ISO date + time when the skill completed | `2026-02-26 14:30` |
| **Command** | The orchestrator skill that was invoked | `/discover`, `/implement`, `/review` |
| **Phase** | The SDLC phase this execution belongs to | `Discovery`, `Design`, `Implementation`, `Testing`, `Review`, `Optimization`, `Observability`, `Refactoring` |
| **Task** | The specific task from the breakdown being worked on, or `N/A` for phase-level commands | `Task 3: CreateProduct Flow` |
| **Agents dispatched** | List of all agents that were dispatched during this execution | `requirements-analyst, scope-analyst` |
| **Skills invoked** | Skills that agents used during execution (if known from agent output) | `discover-requirements, discover-work-item` |
| **Artifacts produced** | Files that were created or modified by this execution | `prd.md, README.md` |
| **Outcome** | Brief summary of what was accomplished | `Requirements structured into 6 FRs and 4 NFRs. Scope defined with 3 identified risks.` |
| **Findings** | Any issues, warnings, deviations, or notes worth recording | `Scope-analyst identified dependency on external payment provider not mentioned in README.` |

---

## Entry Examples

### Discovery Phase

```markdown
## [2026-02-26 10:15] — /discover — Discovery

- **Task:** N/A
- **Agents dispatched:** requirements-analyst, scope-analyst
- **Skills invoked:** discover-requirements
- **Artifacts produced:** prd.md
- **Outcome:** Requirements elicited and structured into 8 FRs and 5 NFRs. Scope defined with risk register.
- **Findings:** None
```

### Implementation Phase

```markdown
## [2026-02-27 14:30] — /implement — Implementation

- **Task:** Task 3: CreateProduct Flow
- **Agents dispatched:** python-implementer, api-implementer, data-implementer
- **Skills invoked:** implement-python, implement-api, implement-data
- **Artifacts produced:** services/products/products/domains/product/flows/create_product.py, routes/v1/products.py, models/persistence/product.py
- **Outcome:** CreateProduct flow implemented with API route, persistence model, and domain logic. All 3 sub-tasks complete.
- **Findings:** data-implementer noted that the products table requires a compound index on (tenant_id, sku) not specified in lld.md. Added as deviation.
```

### Review Phase

```markdown
## [2026-02-28 09:00] — /review — Review

- **Task:** Task 3: CreateProduct Flow
- **Agents dispatched:** python-reviewer, api-reviewer, data-reviewer, performance-reviewer, unit-tests-reviewer
- **Skills invoked:** review-functionality, review-api, review-data, review-performance, review-unit-tests
- **Artifacts produced:** reviews/task-3-create-product-flow/python-reviewer.md, reviews/task-3-create-product-flow/api-reviewer.md, reviews/task-3-create-product-flow/data-reviewer.md, reviews/task-3-create-product-flow/performance-reviewer.md, reviews/task-3-create-product-flow/unit-tests-reviewer.md
- **Outcome:** 5 reviewers completed. 2 critical findings, 3 warnings, 5 info items.
- **Findings:** Critical: missing auth middleware on POST endpoint (api-reviewer). Critical: N+1 query in list operation (performance-reviewer). Suggest running /refactor.
```

---

## Writing the Entry

### When to Write

Write the log entry **after all agents have completed** and the execution summary has been presented to the user. The log entry is the last action an orchestrator skill takes before finishing.

### How to Write

1. Read the current `sdlc-log.md` (or create it if it doesn't exist)
2. Append the new entry at the end of the file
3. Ensure a blank line separates entries for readability

### Timestamp

Use the current date and time at the moment the entry is written:

```
Format: YYYY-MM-DD HH:MM
Example: 2026-02-26 14:30
```

Use 24-hour format. Do not include seconds (unnecessary precision for a human-readable log).

---

## Reading the Log

The `/sdlc` dashboard skill reads `sdlc-log.md` to determine:

- Which commands have been run and when
- Which agents have been dispatched for each phase/task
- Which artifacts have been produced
- Whether any findings or issues were raised

Other orchestrator skills may also read the log for context — for example, `/optimize` checks if review findings flagged performance issues.

---

## Constraints

- **Append-only**: Never modify or delete existing entries
- **Single writer**: Only the orchestrator skill writes to the log, never individual agents
- **One entry per invocation**: Each skill invocation produces exactly one log entry (with per-agent details nested within)
- **No sensitive data**: Do not log secrets, credentials, or PII. Log file paths, agent names, and outcome summaries only
