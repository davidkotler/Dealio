---
name: sdlc
description: |
  Show SDLC lifecycle status for a feature or across all features. Scans artifact
  directories to determine current phase, completed phases, per-task progress, and
  the next recommended command. Use when checking progress, determining next steps,
  viewing feature status, running `/sdlc`, or when the user says "where are we",
  "what's next", "show status", "sdlc status", "feature progress", "what phase",
  "show dashboard", "lifecycle status", "how far along", "what's been done",
  "what's left", "check progress", or "project status". Also use when the user
  wants an overview of all features or asks "which features are in progress".
  This is a read-only dashboard — it writes nothing except an SDLC log entry.
---

# /sdlc — Lifecycle Status Dashboard

> Scan artifacts, determine where the feature stands, and recommend what to do next.

## Quick Reference

| Aspect | Details |
|--------|---------|
| **Phase** | Cross-cutting (read-only dashboard) |
| **Gate** | None — `/sdlc` can always run |
| **Produces** | Dashboard output (displayed, not written to file) |
| **Reads** | All artifacts: README.md, prd.md, hld.md, lld.md, tasks-breakdown.md, sdlc-log.md, reviews/ |
| **Shared Refs** | `sdlc-shared/refs/feature-resolution.md`, `sdlc-shared/refs/sdlc-log-format.md` |

---

## Core Workflow

### Step 1: Determine Scope (Single Feature vs Cross-Feature)

Check whether the user provided a feature argument:

```
/sdlc invoked
    │
    ├─► Argument provided (e.g., /sdlc 001-sdlc-claude-commands)
    │       └─► Single-Feature Dashboard (Step 2)
    │
    └─► No argument
            └─► Cross-Feature Summary (Step 5)
```

If an argument is provided, resolve the feature directory using [sdlc-shared/refs/feature-resolution.md](../sdlc-shared/refs/feature-resolution.md). Then proceed to Step 2.

If no argument is provided, go directly to Step 5 (Cross-Feature Summary).

### Step 2: Scan Feature Artifacts

Scan the resolved feature directory for all SDLC artifacts. Check existence and non-emptiness of each:

| Artifact | Path | Check |
|----------|------|-------|
| Inception README | `{feature-dir}/README.md` | exists and non-empty? |
| Requirements PRD | `{feature-dir}/prd.md` | exists and non-empty? |
| High-Level Design | `{feature-dir}/hld.md` | exists and non-empty? |
| Low-Level Design | `{feature-dir}/lld.md` | exists and non-empty? |
| Task Breakdown | `{feature-dir}/tasks-breakdown.md` | exists and non-empty? |
| SDLC Activity Log | `{feature-dir}/sdlc-log.md` | exists and non-empty? |
| Review Verdicts | `{feature-dir}/reviews/` | directory exists and contains `.md` files? |
| Release Report | `{feature-dir}/release.md` | exists and non-empty? |

Use Glob to check for file existence (e.g., `Glob("{feature-dir}/*.md")` and `Glob("{feature-dir}/reviews/**/*.md")`).

### Step 3: Determine Phase Status

Apply these rules **in order** to determine which phase each artifact represents. A phase is complete when its artifact exists; it's the "current" phase when the next expected artifact is missing.

```
Phase Detection Rules (evaluate top-to-bottom, stop at first incomplete):

1. No README.md          → Current phase: Inception (not started)
                            Status: "Feature not yet initiated"

2. README.md exists,     → Current phase: Discovery (in progress)
   no prd.md               Completed: Inception
                            Status: "Requirements gathering needed"

3. prd.md exists,        → Current phase: Design (needed)
   no lld.md               Completed: Inception, Discovery
                            Status: "Design phase needed"

4. lld.md exists,        → Current phase: Breakdown (needed)
   no tasks-breakdown.md   Completed: Inception, Discovery, Design
                            Status: "Task decomposition needed"

5. tasks-breakdown.md    → Current phase: Implementation (in progress)
   exists                   Completed: Inception, Discovery, Design, Breakdown
                            Status: Check per-task status (Step 3A)

6. All tasks complete,   → Current phase: QA & Product Review (needed)
   no release.md            Completed: Inception, Discovery, Design, Breakdown, Implementation
                            Status: "All tasks complete. Run /qa-review"

7. release.md exists,    → Current phase: Update Documentation (needed)
   no /update-docs log      Completed: Inception, Discovery, Design, Breakdown, Implementation, QA Review
                            Status: "QA Review complete. Run /update-documentation"

8. release.md exists     → Current phase: Done
   AND /update-docs log     Completed: All phases
                            Status: "Feature shipped. Epic is Done."
```

Note: `hld.md` is optional — its absence does not block any phase. If it exists, include it in the completed artifacts. If not, simply note "HLD: skipped (optional)" in the dashboard.

#### Step 3A: Per-Task Status (When tasks-breakdown.md Exists)

When a task breakdown exists, parse `tasks-breakdown.md` to extract individual task statuses. Tasks can have these statuses:

| Status | Indicator | Meaning |
|--------|-----------|---------|
| Pending | `- [ ]` or no status marker | Task not yet started |
| Complete | `✅ Complete` or `- [x]` | Task finished |

For each task, also determine which implementation loop steps have been executed by scanning `sdlc-log.md` for entries mentioning the task name:

| Loop Step | How to Detect |
|-----------|---------------|
| Implement | Log entry: `/implement` with matching task name |
| Observe | Log entry: `/observe` with matching task name |
| Test | Log entry: `/test` with matching task name |
| Review | Log entry: `/review` with matching task name, OR review verdict files exist in `reviews/{task-name}/` |
| Refactor | Log entry: `/refactor` with matching task name |
| Optimize | Log entry: `/optimize` with matching task name |

Read `sdlc-log.md` once and extract all entries. Match each entry's `**Task:**` field against known task names from the breakdown.

### Step 4: Present Single-Feature Dashboard

Present the dashboard using this format:

```markdown
# SDLC Status: {Feature Name}

**Feature directory:** `{feature-dir}`
**Current phase:** {phase name}
**Status:** {status description}

## Phase Progress

| Phase | Status | Artifacts |
|-------|--------|-----------|
| Inception | ✅ Complete | README.md |
| Discovery | ✅ Complete | prd.md |
| Design | ✅ Complete | lld.md (hld.md skipped) |
| Breakdown | ✅ Complete | tasks-breakdown.md |
| Implementation | 🔄 In Progress | 2/5 tasks complete |
| QA & Product Review | ⬜ Pending | — |
| Update Documentation | ⬜ Pending | — |

## Task Progress

| # | Task | Status | Implement | Observe | Test | Review | Refactor |
|---|------|--------|-----------|---------|------|--------|----------|
| 1 | Shared References | ✅ Complete | ✅ | — | — | — | — |
| 2 | /discover Skill | ✅ Complete | ✅ | — | — | — | — |
| 3 | /sdlc Dashboard | 🔄 In Progress | ✅ | — | — | — | — |
| 4 | /design-system + /design-lld Skills | ⬜ Pending | — | — | — | — | — |
| 5 | /tasks-breakdown Skill | ⬜ Pending | — | — | — | — | — |

## SDLC Activity Log Summary

{If sdlc-log.md exists, show the last 5 entries in condensed form:}

| Date | Command | Task | Outcome |
|------|---------|------|---------|
| 2026-02-26 10:15 | /discover | N/A | Requirements structured into 8 FRs |
| 2026-02-26 14:30 | /implement | Task 1 | Shared references created |

## Next Action

Run `/implement {feature-identifier}` to implement Task 3: /sdlc Dashboard.
```

#### Dashboard Presentation Rules

- **Phase Progress table**: Show all phases from Inception through Implementation. Use ✅ for complete, 🔄 for in-progress, ⬜ for pending/not started.
- **Task Progress table**: Only show if `tasks-breakdown.md` exists. Use ✅, 🔄, ⬜ for task status. For loop steps, use ✅ if the step has been executed (found in log or evidence exists), `—` if not.
- **SDLC Activity Log Summary**: Only show if `sdlc-log.md` exists. Show the most recent 5 entries in condensed tabular form. If more than 5 entries exist, note "Showing last 5 of {N} entries."
- **Next Action**: Always end with a concrete, actionable recommendation — the exact command to run next with the feature identifier.

### Step 5: Cross-Feature Summary

When invoked without an argument, scan `docs/designs/` across all year directories and present a summary of all features.

#### Scanning Algorithm

1. List all year directories under `docs/designs/` (e.g., `2025/`, `2026/`)
2. Within each year, list all feature directories
3. For each feature, run the same artifact scan as Step 2 (but without per-task detail — just determine the current phase)
4. Present as a summary table

#### Summary Table Format

```markdown
# SDLC Status — All Features

| # | Feature | Year | Current Phase | Artifacts | Next Action |
|---|---------|------|---------------|-----------|-------------|
| 1 | 001-sdlc-claude-commands | 2026 | Implementation | README, PRD, LLD, Breakdown | `/implement 001-sdlc` |
| 2 | 002-auth-service | 2026 | Design | README, PRD | `/design-system 002-auth` + `/design-lld 002-auth` |
| 3 | 001-payment-gateway | 2025 | Discovery | README | `/discover 001-payment` |
```

- **Artifacts**: Abbreviated list of existing artifacts (README, PRD, HLD, LLD, Breakdown, Log, Reviews)
- **Next Action**: The command to advance this feature to its next phase, using the shortest unambiguous feature identifier

After presenting the summary, ask the user if they want to drill into a specific feature for the full dashboard.

### Step 6: Write SDLC Log Entry

After presenting the dashboard, append an entry to `{feature-dir}/sdlc-log.md` following [sdlc-shared/refs/sdlc-log-format.md](../sdlc-shared/refs/sdlc-log-format.md):

```markdown
## [YYYY-MM-DD HH:MM] — /sdlc — Status

- **Task:** N/A
- **Agents dispatched:** None (dashboard is read-only)
- **Skills invoked:** sdlc
- **Artifacts produced:** None (dashboard displayed only)
- **Outcome:** {summary — e.g., "Status dashboard displayed. Feature in Implementation phase, 2/5 tasks complete."}
- **Findings:** {any notable observations — e.g., "Task 4 has unresolved critical findings from review" or "None"}
```

For cross-feature summaries, write the log entry to each feature directory that was scanned? No — skip the log entry for cross-feature summaries. Only write a log entry when a single feature was inspected.

If `sdlc-log.md` doesn't exist, create it with the header first (see the shared ref for the header format).

---

## Acceptance Criteria Coverage

This skill addresses all five Given/When/Then scenarios from FR-15:

| # | Scenario | Covered By |
|---|----------|------------|
| 1 | Feature directory exists → scan artifacts → present dashboard | Steps 2-4 — scans all artifacts and presents structured dashboard |
| 2 | Dashboard shows current phase, completed phases, per-task status, next command | Step 4 — Phase Progress table, Task Progress table, Next Action section |
| 3 | tasks-breakdown.md exists → per-task status with loop steps | Step 3A — parses task statuses and cross-references sdlc-log.md for loop step evidence |
| 4 | sdlc-log.md has entries → uses log for agent/skill history | Step 3A + Step 4 — reads log to detect loop steps and shows Activity Log Summary |
| 5 | No argument → cross-feature summary | Step 5 — scans all features across all years, presents summary table |

---

## Decision Tree (Full)

```
/sdlc invoked
    │
    ▼
Argument provided?
    │
    ├─► Yes
    │       │
    │       ▼
    │   Resolve Feature Directory (refs/feature-resolution.md)
    │       │
    │       ▼
    │   Scan all artifacts in feature directory
    │       │
    │       ▼
    │   Determine current phase
    │       │
    │       ├─► No README.md → Inception (not started)
    │       ├─► README.md, no prd.md → Discovery (in progress)
    │       ├─► prd.md, no lld.md → Design (needed)
    │       ├─► lld.md, no tasks-breakdown.md → Breakdown (needed)
    │       ├─► tasks-breakdown.md exists → Parse per-task status
    │       │       │
    │       │       ▼
    │       │   Read sdlc-log.md for loop step evidence
    │       │       │
    │       │       ▼
    │       │   Build per-task progress table
    │       │
    │       └─► All tasks complete → Check release.md + update-docs log
    │       │
    │       ▼
    │   Present Single-Feature Dashboard
    │       │
    │       ▼
    │   Recommend next action
    │       │
    │       ▼
    │   Append SDLC log entry
    │       │
    │       ▼
    │   END
    │
    └─► No
            │
            ▼
        Scan docs/designs/ across all years
            │
            ▼
        For each feature: quick artifact scan → determine phase
            │
            ▼
        Present Cross-Feature Summary table
            │
            ▼
        Ask if user wants to drill into a specific feature
            │
            ▼
        END (no log entry for cross-feature view)
```

---

## Next-Action Recommendation Logic

The "Next Action" recommendation follows a deterministic mapping from the current phase:

| Current Phase | Next Action |
|---------------|-------------|
| Inception (not started) | `Run /discover-feature` to start feature inception |
| Discovery (in progress) | `Run /discover-requirements {feature}` to complete requirements gathering |
| Design (needed) | `Run /design-system {feature}` to produce the high-level design, then `/design-lld {feature}` for the low-level design |
| Breakdown (needed) | `Run /tasks-breakdown {feature}` to decompose into tasks |
| Implementation (in progress) | `Run /implement {feature}` to implement the next pending task: {task name} |
| Implementation (task has review findings) | `Run /refactor {feature}` to address review findings for {task name} |
| QA & Product Review (needed) | `Run /qa-review {feature}` to validate delivery against requirements |
| Update Documentation (needed) | `Run /update-documentation {feature}` to capture decisions, architecture, and service docs |
| Done | Feature shipped. Epic is Done. No further action needed. |

When in the Implementation phase, be specific — name the next pending task that should be worked on (the first pending task whose dependencies are complete).

---

## Patterns

### Do

- Read `sdlc-log.md` to enrich the dashboard with history — dates, agents used, findings raised
- Present concrete next-action commands with the feature identifier filled in so the user can copy-paste
- Show the loop step columns (Implement, Observe, Test, Review, Refactor) only when `tasks-breakdown.md` exists
- Use the abbreviated feature identifier in next-action commands (shortest unambiguous prefix)
- Cross-reference review verdicts directory to detect review completion even if the log is incomplete

### Don't

- Write or modify any feature artifacts — this is a read-only dashboard
- Run any agents — `/sdlc` is purely analytical, it dispatches nothing
- Block on missing artifacts — report what's missing, don't gate
- Show empty sections — if there's no task breakdown, skip the Task Progress table; if there's no log, skip the Activity Log Summary
- Parse task content deeply — use existence checks and status markers, not structural validation of artifact content
