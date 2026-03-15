---
name: qa-review
version: 2.0.0
description: |
  Perform deep code analysis and release validation of a completed feature. Goes beyond document
  comparison — actually reads the implemented services, domains, modules, and source code to
  understand what architecture was built, what value it delivers, and how it compares to the
  original design. Produces a release retrospective that traces goals and requirements to real
  code evidence: module structures, domain models, integration patterns, test coverage, and
  architectural decisions visible in the implementation.
  Use when all tasks are complete, a feature is ready to ship, running `/qa-review`, or when
  the user says "feature retrospective", "release review", "are we done", "did we meet
  requirements", "compare to prd", "what did we deliver", "ship review", "close the feature",
  "feature complete", "wrap up", "final review", "check against requirements", "qa review",
  "product review", "validate delivery", "release notes", "what did we build", "analyze the
  implementation", "code review the feature", or "architecture review".
---

# /qa-review — Feature Retrospective & Release Validation

> Compare what was planned against what was built — by reading the actual code, not just the
> documents. Produce a release document that traces every goal and requirement to concrete
> implementation evidence, documents deviations, maps the architecture that was delivered,
> and defines next steps.

## Quick Reference

| Aspect | Details |
|--------|---------|
| **Phase** | QA & Product Review (Stage 11 — final gate before feature closure) |
| **Gate** | `tasks-breakdown.md` exists AND all tasks marked complete |
| **Invoked By** | Developer after all tasks pass their implementation loops |
| **Produces** | `{feature-dir}/release.md` |
| **Reads** | `README.md`, `prd.md`, `hld.md`, `lld.md`, `tasks-breakdown.md`, `sdlc-log.md`, **actual source code** |
| **Shared Refs** | [feature-resolution.md](../sdlc-shared/refs/feature-resolution.md), [sdlc-log-format.md](../sdlc-shared/refs/sdlc-log-format.md) |
| **Deep Refs** | [refs/release-template.md](refs/release-template.md) |

---

## Core Workflow

### Step 1: Resolve Feature Directory

Resolve the target feature using [sdlc-shared/refs/feature-resolution.md](../sdlc-shared/refs/feature-resolution.md).
Never create a new feature directory — this skill only operates on existing features.

### Step 2: Gate Check — All Tasks Complete

This skill gates on implementation completeness:

```
Check: {feature-dir}/tasks-breakdown.md exists?
  ├─► No  → Block:
  │         "No task breakdown found. Run /tasks-breakdown first."
  └─► Yes → Parse tasks-breakdown.md for task statuses
              │
              ├─► All tasks marked ✅ Complete → Proceed to Step 3
              │
              └─► Some tasks incomplete → Present status and ask:
                    "N of M tasks are incomplete. Options:
                     1. Proceed anyway (partial release review)
                     2. Go back and complete remaining tasks"
```

The gate is advisory, not absolute — a developer may want a partial review to understand where
things stand mid-feature. If they choose to proceed, the release document clearly marks which
tasks were not completed.

### Step 3: Gather Design & Process Evidence

Read every artifact in the feature directory. Build a picture of what was planned and what the
process recorded:

**Design artifacts** (what was planned):
1. `README.md` — Extract goals, vision, value proposition, non-goals
2. `prd.md` — Extract all FRs (with acceptance criteria), NFRs, MoSCoW priorities, risks,
   constraints, delivery plan, assumptions
3. `hld.md` (if exists) — Extract architectural decisions, bounded contexts, integration patterns
4. `lld.md` — Extract contracts, data models, component designs, technical decisions

**Process artifacts** (what was recorded):
5. `tasks-breakdown.md` — Extract each task with its status, completion notes, deviations,
   sub-task checklist status, and Definition of Done
6. `sdlc-log.md` — Extract the full activity timeline: commands run, outcomes recorded
7. `reviews/` — Read review verdicts and resolution reports for each task

### Step 4: Deep Code Analysis — Map the Implementation

This is the heart of the review. The design artifacts tell you what was *planned*; now you
need to understand what was *actually built* by reading the code itself. Task completion notes
and review verdicts are a starting point, but they are summaries written during development —
the code is the ground truth.

#### 4a: Discover the Feature's Code Footprint

Start by identifying every directory, package, and module the feature touched. Use the
Definition of Done file lists from `tasks-breakdown.md` as seeds, then expand:

1. **Map modified directories** — Glob for the directories mentioned in task DoDs.
   List each directory's contents to understand the module structure.
2. **Discover related code** — Features often touch shared libraries, test directories,
   configuration files, infrastructure, and tooling beyond what task DoDs list. Grep for
   feature-specific imports, class names, or identifiers across `services/`, `libs/`,
   `tools/`, and `tests/` to find the full footprint.
3. **Map test directories** — Identify all test files (unit, integration, contract, e2e)
   that validate this feature's code. Note the test-to-source ratio.

Produce a **Code Footprint Map** — an organized inventory of every directory and its role:

```
Feature Code Footprint:
  services/<name>/<name>/          — Service package root
    domains/<domain>/              — Domain module (if applicable)
    models/                        — Domain models, contracts, persistence
    ...
  tools/<name>/                    — CLI tools or utilities
  libs/<name>/                     — Shared library contributions
  tests/unit/                      — Unit test modules
  tests/integration/               — Integration test modules
  Total: N source files, M test files, across K directories
```

#### 4b: Analyze Module Architecture

For each major directory/package the feature created or modified, understand its internal
architecture by reading the actual source:

1. **Get symbol overviews** — For each key Python file, read the module's classes, functions,
   and their relationships. Use `get_symbols_overview` with depth=1 on important files to
   understand the public API without reading every line.
2. **Read critical implementations** — For the feature's core logic (domain models, flows,
   adapters, tool handlers), read the actual source bodies. Focus on:
   - Domain models: What entities, value objects, and enums were defined? Do they match the
     LLD contracts?
   - Business logic: What flows, handlers, or orchestrators were built? How do they compose?
   - Integration points: How does the code connect to external systems (DB, APIs, message
     queues, file I/O)?
   - Configuration and settings: What is configurable? What is hardcoded?
3. **Trace data flow** — Follow one or two critical paths end-to-end through the code
   (e.g., from CLI entry point → orchestrator → processors → output). This reveals whether
   the architecture is coherent or fragmented across independently implemented tasks.

#### 4c: Evaluate Architecture Against Design

Compare what the HLD/LLD specified against what the code actually implements:

| Design Aspect | Check Against Code |
|---------------|-------------------|
| **Architecture style** (HLD §3) | Does the module structure match? (monolith, microservice, modular) |
| **Component boundaries** (HLD) | Are the boundaries in the code where the HLD said they'd be? |
| **Data models** (LLD) | Do Pydantic models / DB schemas match the LLD contracts? Compare field names, types, constraints |
| **API/Tool contracts** (LLD) | Do implementations match their specified input/output schemas? |
| **Integration patterns** (HLD/LLD) | Are external dependencies wrapped in adapters? Is communication sync/async as designed? |
| **Error handling** (LLD) | Are error types defined? Is error propagation following the designed patterns? |
| **Observability** (LLD) | Is logging/tracing configured as specified? |

For mismatches, note whether the implementation improved on the design (good deviation)
or drifted from it (potential issue).

#### 4d: Assess Code Quality Dimensions

Evaluate the implemented code against the project's engineering principles (`.claude/rules/principles.md`):

1. **Modularity** — Are modules cohesive? Do they have clear boundaries? Are dependencies
   injected rather than hardcoded?
2. **Domain modeling** — Do domain types express the business language? Are value objects
   immutable? Are aggregates properly bounded?
3. **Testability** — Is logic separated from I/O? Can components be tested in isolation?
4. **Type safety** — Are type annotations complete? Are Pydantic models used at boundaries?
5. **Error handling** — Are errors explicit (typed results or custom exceptions)? Are failures
   propagated with context?
6. **Code organization** — Does the file/directory structure follow the project's conventions
   (ports-and-adapters for services, or appropriate patterns for tools/libs)?

This is not a full code review (that's `/review`). The goal is to assess whether the code, as
a whole, reflects sound engineering — and to surface any systemic patterns (good or bad) that
the per-task reviews might have missed because they looked at each task in isolation.

#### 4e: Measure Test Coverage Breadth

Analyze the test suite for this feature:

1. **Count tests by type** — How many unit, integration, contract, e2e, and UI tests exist?
2. **Map test-to-module coverage** — Which source modules have corresponding test modules?
   Which don't?
3. **Assess test quality signals** — Do tests use proper markers (`@pytest.mark.unit`, etc.)?
   Do they follow AAA pattern? Are they testing behavior or implementation?
4. **Run the tests** if possible — Execute `uv run pytest <feature-test-path> -v --tb=short`
   to verify all tests pass and capture the actual pass/fail count.

#### 4f: Quantify What Was Built

Produce concrete metrics about the implementation:

- **Lines of source code** (excluding tests, configs, generated files)
- **Lines of test code**
- **Number of source modules** vs **number of test modules**
- **Number of domain models / entities / value objects defined**
- **Number of public API endpoints or tool handlers**
- **Key technology choices** (databases, frameworks, protocols used)

These metrics ground the release document in reality rather than letting it be a pure
document-to-document comparison.

### Step 5: Analyze — Requirements Traceability (Code-Backed)

For each requirement in `prd.md`, determine its delivery status — but now backed by actual
code evidence from Step 4, not just task completion notes:

| Status | Criteria |
|--------|----------|
| **Met** | Acceptance criteria satisfied. Implementation exists *and was read*. Tests pass. |
| **Partially Met** | Some acceptance criteria satisfied, others missing or incomplete in the code. |
| **Not Met** | No implementation found, or implementation does not satisfy acceptance criteria. |
| **Descoped** | Explicitly removed during implementation with documented reason. |
| **Deferred** | Moved to a future iteration with documented reason. |

For each requirement, record:
- The specific task(s) that implemented it (traceability link)
- **Concrete code evidence**: file paths, class/function names, SQL schemas, tool handlers —
  not just "Task 5 completed this" but "implemented in `demo_mcp/tools/query_findings.py::query_findings()`,
  with SQL builder in `demo_mcp/queries/findings.py`, tested by `tests/unit/tools/test_query_findings.py`
  (12 tests)"
- If not met: the reason (technical blocker, scope change, time constraint, discovered complexity)

### Step 6: Analyze — Goal Alignment (Architecture-Informed)

For each goal in `README.md`, assess whether the delivered implementation achieves it,
informed by your understanding of the actual code architecture:

- Does the implementation deliver the intended business value? (Look at what the code
  actually does, not what the task notes say it does)
- Is the user experience coherent across independently implemented tasks? (Trace a few
  user journeys through the code to verify end-to-end coherence)
- Did any implementation choices drift from the original intent?
- Does the architecture as built support the goals, or does it technically work but in a
  way that undermines the vision?

### Step 7: Analyze — Deviations (Design vs. Code)

Compare the original plan against what was actually built, using evidence from both the
process artifacts and the code analysis:

**Source deviations from documents:**
- `Completion Notes` and `Deviations` fields in tasks-breakdown.md
- `Findings` fields in sdlc-log.md entries
- Review verdicts and resolution reports

**Source deviations from code analysis:**
- Data models that differ from LLD specs (extra fields, missing fields, type changes)
- Architecture patterns that differ from HLD (different boundaries, different integration style)
- Contracts that evolved during implementation (input/output schema changes)
- Components that were added but not in the original design
- Components that were designed but not implemented

Classify each deviation:
- **Improvement** — The code is better than the design (discovered a simpler approach,
  added necessary error handling, etc.)
- **Trade-off** — A conscious compromise (scope reduction for deadline, simpler implementation
  at cost of flexibility, etc.)
- **Drift** — Unintentional divergence that should be either reconciled or documented

### Step 8: Synthesize — Architecture Diagrams (from Code)

Generate two mermaid diagrams that represent the **implemented** architecture, derived from
your code analysis in Step 4 — not copied from the HLD/LLD. These diagrams capture what the
code actually does, which may differ from what was designed.

#### 8a: Component & Boundary Diagram

Create a mermaid diagram showing the components, their boundaries, and how they connect.
Derive this from the actual module structure, imports, and dependencies you discovered in
Step 4b:

- Each major package/module becomes a node
- Group related nodes into subgraphs representing boundaries (service, domain, infrastructure)
- Edges represent actual dependencies (imports, function calls, data passing)
- External systems (DB, file I/O, APIs, message queues) are separate nodes
- Use styles to distinguish component types (domain, infrastructure, tools, tests)

If the implemented architecture differs from the HLD diagram, note specifically what changed
and why (based on deviation analysis from Step 7). Include a brief explanation beneath the
diagram: "This diagram reflects the implemented architecture. Differences from the HLD: ..."

#### 8b: Feature Flow Diagram

Create a mermaid flowchart or sequence diagram showing the primary data/execution flow through
the feature end-to-end. Derive this from the data flow traces you performed in Step 4b:

- Show the entry point (CLI command, API endpoint, event handler)
- Show each processing stage with the actual module/function responsible
- Show data transformations (input format → intermediate → output format)
- Show decision points and error paths if they are architecturally significant
- Show the final output (DB writes, API responses, file outputs, events published)

If the flow changed from what the LLD specified, explain what changed and whether it was an
improvement or a concerning drift.

For features with multiple distinct flows (e.g., a data pipeline AND a query API), diagram the
2-3 most important flows rather than trying to capture everything.

### Step 9: Synthesize — Manual Verification Guide

Create a practical guide for manually verifying that the feature works correctly. This is not
a test plan — it's a runbook that a developer or QA person can follow to confirm the feature
delivers its intended value with their own eyes.

#### 9a: Prerequisites

List everything needed before verification can begin:
- Environment setup steps (install dependencies, configure env vars, start services)
- Data or state that must exist (seed data, database migrations, config files)
- External dependencies (running services, API keys, network access)
- Tools needed (CLI commands, browser, API client)

#### 9b: Verification Scenarios

For each major capability the feature delivers, write a concrete scenario:

```
Scenario: {what you're verifying — maps to a goal or key FR}
  Setup:    {any scenario-specific preparation}
  Steps:    {numbered commands or actions to perform}
  Expected: {what you should see — specific output, behavior, or state change}
  Verify:   {how to confirm it actually worked — check DB, inspect output, etc.}
```

Derive scenarios from:
- The goals in README.md (each goal should have at least one verification scenario)
- The "Must" FRs in prd.md (critical requirements deserve explicit verification)
- The NFRs that are manually verifiable (performance targets, error handling behavior)
- The demo scenarios or user journeys from the feature's context

#### 9c: Quality Assurance Checklist

A quick checklist for confirming the feature meets quality standards beyond functional
correctness:

- [ ] All tests pass (`uv run pytest <path> -v`)
- [ ] No lint errors (`uv run ruff check <path>`)
- [ ] No type errors (`uv run ty check`)
- [ ] Code formatted (`uv run ruff format --check <path>`)
- [ ] No regressions in existing functionality
- [ ] Error cases handled gracefully (try invalid inputs, missing data, etc.)
- [ ] Logs are structured and useful (check log output during verification scenarios)
- [ ] Performance is acceptable for the use case (note any sluggish operations)

Adapt this checklist based on the feature's scope — a data pipeline needs data validation
checks, an API needs endpoint testing, a CLI tool needs help text and error messages.

### Step 10: Synthesize — Implementation Value Assessment

This is a section that doesn't exist in traditional requirement traceability. Based on
your deep code analysis, write a narrative assessment of what the feature actually delivers:

1. **Architecture Summary** — In 3-5 sentences, describe the architecture that was built
   (not the architecture that was designed). What patterns does it use? How do the pieces
   fit together? What is the data flow?
2. **Key Technical Decisions** — What significant implementation choices were made? Were they
   sound? Are there any that should be revisited?
3. **Strengths** — What aspects of the implementation are particularly well-done?
   (Domain modeling, test coverage, error handling, modularity, etc.)
4. **Technical Debt** — What shortcuts, TODOs, or known limitations exist in the code?
   Are they acceptable for the current scope, or do they need immediate attention?
5. **Reusability & Extensibility** — Which components could be reused in future features?
   How hard would it be to extend the feature with new capabilities?

### Step 11: Produce release.md

Write `{feature-dir}/release.md` following [refs/release-template.md](refs/release-template.md).

Before writing, present a summary to the developer for review:

```markdown
## Release Review Summary

**Feature:** {name}
**Overall Assessment:** {Delivered as Planned | Delivered with Deviations | Partially Delivered}

**Code Footprint:** {N source files}, {M test files}, across {K directories}
**Requirements:** {N met} / {M total} ({X partially met}, {Y not met/deferred})
**Goals:** {N aligned} / {M total}
**Deviations:** {N documented} ({improvements} improvements, {tradeoffs} trade-offs, {drifts} drifts)
**Tests:** {N total} ({unit} unit, {integration} integration, {e2e} e2e) — {pass/fail status}

### Architecture Snapshot
{2-3 sentence description of what was actually built}

### Key Findings
- {top 3-5 findings from the code analysis — both positive and concerning}

Shall I write the full release.md with this assessment?
```

Wait for confirmation before writing the document. The developer may want to adjust the
assessment or add context before the document is produced.

### Step 12: Determine Outcome

Based on the analysis, recommend one of three outcomes:

```
Assessment
    │
    ├─► All requirements met, all goals aligned, architecture sound, no significant deviations
    │       → Outcome: PASS
    │       → "Feature is ready to ship. Close the Epic."
    │
    ├─► Some requirements partially met, minor deviations, manageable tech debt
    │       → Outcome: PASS WITH NOTES
    │       → "Feature can ship. Document follow-up items as new tickets."
    │
    └─► Requirements not met, goals misaligned, architectural concerns, or major scope gaps
            → Outcome: FAIL
            → "Feature needs additional work. Create new tasks for gaps."
```

For PASS WITH NOTES and FAIL, the Next Steps section in release.md captures the specific
actions needed — each as a concrete work item ready to enter the backlog.

### Step 13: Write SDLC Log Entry

Append entry to `{feature-dir}/sdlc-log.md` per [sdlc-shared/refs/sdlc-log-format.md](../sdlc-shared/refs/sdlc-log-format.md):

```markdown
## [YYYY-MM-DD HH:MM] — /qa-review — QA & Product Review

- **Task:** N/A (feature-level review)
- **Agents dispatched:** None (single-agent analysis)
- **Skills invoked:** qa-review
- **Artifacts produced:** release.md
- **Outcome:** {assessment} — {N}/{M} requirements met, {deviations} deviations,
  {source_files} source files across {directories} directories, {test_count} tests ({pass/fail}).
  {1-sentence summary of the overall finding}
- **Findings:** {key gaps, architectural observations, or "All requirements satisfied. Feature ready to ship."}
```

---

## Decision Tree

```
/qa-review invoked
    │
    ▼
Resolve feature directory (refs/feature-resolution.md)
    │
    ▼
tasks-breakdown.md exists?
    │
    ├─► No → Block: "Run /tasks-breakdown first"
    │
    └─► Yes → All tasks complete?
                │
                ├─► Yes → Gather design & process evidence (Step 3)
                │
                └─► No  → Ask: proceed with partial review or go back?
                            │
                            ├─► Proceed → Gather evidence (mark incomplete tasks)
                            └─► Go back → END (suggest next /implement)
    │
    ▼
Deep code analysis (Step 4)
    ├── 4a: Discover code footprint
    ├── 4b: Analyze module architecture
    ├── 4c: Evaluate architecture vs design
    ├── 4d: Assess code quality dimensions
    ├── 4e: Measure test coverage breadth
    └── 4f: Quantify what was built
    │
    ▼
Analyze: Requirements traceability with code evidence (Step 5)
    │
    ▼
Analyze: Goal alignment informed by architecture (Step 6)
    │
    ▼
Analyze: Deviations from design vs code comparison (Step 7)
    │
    ▼
Synthesize: Architecture diagrams from code (Step 8)
    ├── 8a: Component & boundary mermaid diagram
    └── 8b: Feature flow mermaid diagram
    │
    ▼
Synthesize: Manual verification guide (Step 9)
    ├── 9a: Prerequisites
    ├── 9b: Verification scenarios
    └── 9c: Quality assurance checklist
    │
    ▼
Synthesize: Implementation value assessment (Step 10)
    │
    ▼
Present summary to developer (Step 11)
    │
    ▼
Developer confirms?
    │
    ├─► Yes → Write release.md
    │           │
    │           ▼
    │         Determine outcome (PASS / PASS WITH NOTES / FAIL)
    │           │
    │           ▼
    │         Write SDLC log entry
    │           │
    │           ▼
    │         END
    │
    └─► No → Developer provides corrections → Re-analyze → loop
```

---

## Code Analysis Strategies

The depth of code reading should be proportional to the feature's scope. A 3-task feature
touching one module needs less analysis than a 13-task feature spanning services, tools, and
libraries. Use these heuristics:

### Small features (1-5 tasks, single package)
- Read all source files directly
- Read all test files
- Compare every model against the LLD

### Medium features (5-10 tasks, 2-3 packages)
- Use `get_symbols_overview` on each package first
- Read the bodies of domain models, main entry points, and critical business logic
- Spot-check 2-3 test files for quality patterns
- Trace one end-to-end path through the code

### Large features (10+ tasks, multiple packages/services)
- Map the directory structure first, then prioritize reading based on architectural importance
- Read domain models and contracts in full (they define the feature's shape)
- Read entry points and orchestrators (they reveal the architecture)
- Use `find_symbol` and `find_referencing_symbols` to trace key abstractions
- Spot-check implementations against LLD contracts for a representative sample
- Focus test analysis on coverage gaps rather than reading every test

---

## Patterns

### Do

- **Read the code, not just the documents** — Task completion notes are summaries; the code is truth
- Trace every requirement to concrete code evidence (file paths, class names, function signatures)
- Map the feature's full code footprint before starting analysis (features spread beyond task DoDs)
- Compare implemented data models field-by-field against LLD contracts
- Assess whether the code as a whole is coherent, not just whether each task individually passed
- Surface deviations objectively — classify as improvement, trade-off, or drift
- Make Next Steps actionable: each item should be ready to become a backlog ticket
- Present the summary before writing — the developer's context matters
- Run tests if possible to get actual pass/fail counts

### Don't

- Skip requirements — every FR and NFR in the PRD must have a status
- **Treat code analysis as optional** — this is the most important part of the review
- Assume "task complete" means "requirement met" — tasks are slices, requirements span tasks
- Judge deviations negatively — sometimes deviating from the plan is the right call
- Write release.md without developer confirmation
- Invent evidence — if you can't verify a requirement was met, mark it as "Unverified"
- Modify any file other than release.md and sdlc-log.md
- Skim code superficially — if you're going to read a module, understand it
- Confuse lines of code with value — a well-designed 50-line module can deliver more than a 500-line one

---

## Quality Gates

Before completing:

- [ ] Code footprint mapped — all directories, packages, and modules identified
- [ ] Key source files read and understood (domain models, entry points, critical business logic)
- [ ] Architecture compared against HLD/LLD with specific code references
- [ ] Every functional requirement in prd.md has a status with code evidence
- [ ] Every non-functional requirement in prd.md has a status
- [ ] Every goal in README.md has an alignment assessment informed by code analysis
- [ ] All deviations from the plan are documented with reasons and classified
- [ ] Mermaid component & boundary diagram generated from actual code structure
- [ ] Mermaid flow diagram generated from actual data/execution flow
- [ ] If architecture/flow differs from HLD/LLD, differences are explained
- [ ] Manual verification guide written with prerequisites, scenarios, and QA checklist
- [ ] Verification scenarios cover all goals and critical requirements
- [ ] Implementation value assessment written (architecture summary, strengths, tech debt)
- [ ] Test count and pass/fail status captured
- [ ] Next Steps section contains actionable items for anything not fully delivered
- [ ] Developer has confirmed the assessment before release.md was written
- [ ] SDLC log entry has been appended
