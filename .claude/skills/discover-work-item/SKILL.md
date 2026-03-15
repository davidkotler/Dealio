---
name: discover-work-item
version: 1.0.0
description: |
  Identify and frame standalone work items (Task, Bug, Chore, Spike) before implementation
  begins. Use when starting any non-Epic work, fixing a bug, performing a chore, running
  a spike, making a small standalone improvement, or when the user says "fix this bug",
  "I need to...", "let's refactor", "investigate why", "update the config", "clean up",
  "small change", "quick fix", "tech debt", "spike on", "research how", "add a task",
  "create a work item", "before I start", or describes a change that is ≤ 1 day of work.
  Produces a work item README.md with mission statement, context, and acceptance criteria
  that gates entry into lightweight design (LLD) and the implementation loop.
  Escalates to discover/feature when scope exceeds a single PR or crosses service boundaries.
  Relevant for task framing, bug triage, chore scoping, spike definition, pre-implementation
  planning, and work item discovery.
---

# Discover Work Item

> Frame **what** a work item is, **why** it matters, and **where** it fits — before any code is written.

## Quick Reference

| Aspect | Details |
|--------|---------|
| **Invokes** | `design/code` (LLD), `discover/feature` (escalation) |
| **Invoked By** | None — entry point for standalone work |
| **Key Tools** | Read, Write, Bash |
| **Artifact** | `docs/work-items/YYYY/NNN-{type}-{name}/README.md` |

---

## Core Workflow

1. **Classify**: Determine the work item type from user input. Ask one clarifying question if the type is ambiguous. Do not guess.

2. **Scope-Check**: Assess whether the work fits within a single PR and ≤ 1 day. If it crosses service boundaries, introduces new bounded contexts, requires design across multiple domains, or will take multiple days — **escalate to `discover/feature`**. State why.

3. **Contextualize**: Identify the affected bounded context, service, module, or file area. Read relevant source code, specs, or docs to anchor the work item in the existing system. Do not frame in a vacuum.

4. **Frame**: Structure the work item into the README sections: Mission Statement, Context, Affected Area, Acceptance Criteria, and (for Bugs) Reproduction Steps. Each section has a distinct purpose — do not merge or skip.

5. **Assign Sequence Number**: Scan `docs/work-items/{current-year}/` for existing directories. Determine the next available sequence number (`NNN`). If the directory does not exist, start at `001`.

6. **Create Directory & README**: Create `docs/work-items/YYYY/NNN-{type}-{name}/` and write the README.md using the template below.

7. **Gate**: Confirm the README.md with the user. No implementation or design begins until confirmed. Once confirmed, inform the user of the next step: lightweight design (LLD) via `design/code`, or direct implementation if the change is trivial.

---

## Decision Tree

```
User Input
    │
    ├─► What type of work?
    │       ├─► Defect / incorrect behavior ──────────► Bug
    │       ├─► Tooling / deps / config / cleanup ────► Chore
    │       ├─► Timeboxed research / investigation ───► Spike
    │       └─► Small improvement / new behavior ─────► Task
    │
    ├─► Scope check: fits in single PR, ≤ 1 day?
    │       ├─► YES ──► Continue with work item framing
    │       └─► NO  ──► ESCALATE to discover/feature
    │                   Output: "This exceeds work-item scope because
    │                   {reason}. Escalating to discover/feature for
    │                   full Epic treatment."
    │
    ├─► Does this need lightweight design (LLD)?
    │       ├─► Trivial (rename, config, dep bump) ──► Skip LLD
    │       └─► Non-trivial (logic, schema, API) ────► Chain to design/code
    │
    └─► Existing work-items directory found?
            ├─► YES ──► Next sequence number
            └─► NO  ──► Create year directory, start at 001
```

---

## Work Item Types

| Type | Trigger Signals | Typical Scope | SDLC Flow |
|------|----------------|---------------|-----------|
| **Task** | "Add...", "improve...", "small feature", "enhancement" | ≤ 1 day, single PR | README → LLD → Implement loop → Ship |
| **Bug** | "Fix...", "broken", "doesn't work", "regression", "error" | ≤ 1 day, single PR | README (with repro) → LLD → Implement loop → Ship |
| **Chore** | "Update deps", "refactor", "clean up", "config change", "tooling" | ≤ 1 day, single PR | README → Implement → Ship |
| **Spike** | "Investigate", "research", "spike on", "explore", "POC" | ≤ 2 days, decision doc | README → Research → ADR or Decision doc |

---

## Escalation Criteria

**Escalate to `discover/feature`** when ANY of these are true:

- Change spans multiple bounded contexts or services
- Requires new API endpoints AND new event handlers AND new data models
- Estimated effort exceeds 1 day (2 days for Spikes)
- Introduces a new bounded context or domain
- Requires HLD-level architectural decisions
- Multiple engineers need to coordinate
- Change requires a phased delivery plan

When escalating, output:

```markdown
**Escalation to Epic:** This work exceeds standalone work-item scope.
**Reason:** {specific criterion that triggered escalation}
**Recommendation:** Invoke `discover/feature` to initiate full SDLC flow.
```

---

## README.md Template

```markdown
# {Type}: {Work Item Name}

> One-sentence mission statement: what changes and why.

## Context

What situation, observation, incident, or request triggered this work item?
Connect to evidence where available — error logs, metrics, user reports,
code smells, dependency alerts, or team discussion. Enough context for
someone unfamiliar to understand why this matters.

## Affected Area

| Aspect | Details |
|--------|---------|
| **Service** | {service name} |
| **Domain** | {bounded context} |
| **Modules** | {specific modules, files, or paths affected} |
| **Dependencies** | {upstream/downstream impacts, if any} |

## Acceptance Criteria

Concrete, verifiable conditions that define "done." Each criterion is
testable — someone can look at the result and confirm yes or no.

- [ ] {Criterion 1}
- [ ] {Criterion 2}
- [ ] {Criterion 3}

## Reproduction Steps (Bug only)

1. {Step to reproduce}
2. {Step to reproduce}
3. **Expected:** {what should happen}
4. **Actual:** {what happens instead}

## Approach Hint (optional)

Brief technical direction if the path is obvious. Not a design — just
enough to orient the LLD or implementation. Omit if multiple approaches
exist and design thinking is needed.

## Open Questions

- {Unresolved question} — {who or what might answer it}
```

---

## Skill Chaining

### Invoke Downstream Skills When

| Condition | Invoke | Handoff Context |
|-----------|--------|-----------------|
| Non-trivial Task or Bug confirmed | `design/code` | README path, affected area, acceptance criteria |
| Scope exceeds single PR or ≤ 1 day | `discover/feature` | User input, reason for escalation |
| Spike completed with decision | `docs/adrs/` | Spike README path, decision outcome |

### Chaining Syntax

When the README.md is confirmed, output:

```markdown
**Work Item Framed:** `docs/work-items/YYYY/NNN-{type}-{name}/README.md`

**Next Step:**
- **Non-trivial**: Invoke `design/code` for lightweight design (LLD) in the same directory
- **Trivial (chore/config)**: Proceed directly to implementation
- **Spike**: Begin timeboxed research; output ADR or decision doc when complete
```

---

## Patterns & Anti-Patterns

### ✅ Do

- Read existing code in the affected area before framing — context prevents wrong assumptions
- Keep the mission statement to one sentence — it is a compass, not a document
- State acceptance criteria as verifiable checkboxes — "done" must be unambiguous
- Escalate early — a misclassified Epic disguised as a Task wastes more time than escalation
- Include the Affected Area table — it anchors the work to the real codebase
- For Bugs, always include reproduction steps — a bug without repro is a guess

### ❌ Don't

- Write implementation details in the README — that belongs in LLD or code
- Skip the scope check — the most common failure is a "quick fix" that becomes an Epic
- Create the README without confirming with the user — this is a gate, not a formality
- Frame work items in isolation — always read the relevant code, specs, or docs first
- Merge acceptance criteria into prose — each criterion must stand alone as a checkbox
- Assume the type — ask if ambiguous; a "bug" might be a missing feature (Task)

---

## Examples

### Example 1: Bug

**Input:** "The /users endpoint returns 500 when the email field is missing"
**Output:** `docs/work-items/2026/007-bug-users-endpoint-missing-email-500/README.md`

```markdown
# Bug: Users Endpoint Returns 500 on Missing Email
> Fix the /users endpoint to return 422 with a validation error when email is missing.

## Context
Production logs show ~340 KeyError occurrences in user creation over 48 hours.
The route handler accesses request.email without Pydantic validation.

## Affected Area
| Aspect | Details |
|--------|---------|
| **Service** | user-service |
| **Domain** | identity |
| **Modules** | `domains/identity/routes/v1/users.py`, `models/contracts/api/requests.py` |
| **Dependencies** | None — contained within the identity domain |

## Acceptance Criteria
- [ ] POST /users with missing email returns 422 with structured error body
- [ ] Pydantic request model enforces email as required field
- [ ] Existing tests updated to cover missing-field validation

## Reproduction Steps
1. POST /users with body `{"name": "Test"}` (no email field)
2. **Expected:** 422 with validation error — **Actual:** 500
```

### Example 2: Chore

**Input:** "We need to update our Python dependencies"
**Output:** `docs/work-items/2026/008-chore-python-dependency-update/README.md`

```markdown
# Chore: Python Dependency Update
> Update all Python dependencies to latest compatible versions and resolve deprecation warnings.

## Context
Last update was 6 weeks ago. Dependabot flagged 3 moderate security advisories.
CI logs show 12 deprecation warnings from outdated library versions.

## Affected Area
| Aspect | Details |
|--------|---------|
| **Service** | All services |
| **Domain** | Cross-cutting |
| **Modules** | `pyproject.toml` files, `uv.lock` |

## Acceptance Criteria
- [ ] All dependencies updated to latest compatible versions
- [ ] Security advisories resolved
- [ ] CI pipeline passes with zero new failures
```

---

## Quality Gates

Before completing work item discovery:

- [ ] Work item type is explicitly classified (Task, Bug, Chore, or Spike)
- [ ] Scope check confirms the work fits within a single PR and ≤ 1 day (≤ 2 for Spikes)
- [ ] README.md contains all required sections for the work item type
- [ ] Mission statement is one sentence, outcome-oriented, with no implementation details
- [ ] Acceptance criteria are verifiable checkboxes (not prose)
- [ ] Affected Area table references real services, domains, and modules from the codebase
- [ ] Sequence number is correct (scanned from existing directories, no duplicates)
- [ ] Directory follows naming convention: `docs/work-items/YYYY/NNN-{type}-{name}/`
- [ ] User has confirmed the README.md before any downstream work begins
- [ ] Escalation was considered and either applied or explicitly ruled out
