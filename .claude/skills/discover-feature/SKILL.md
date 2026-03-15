---
name: discover-feature
version: 1.0.0
description: |
  Initiate a new feature (Epic) by defining its high-level goals, rationale, purpose, and
  value proposition before any SDLC phase begins. Use when starting a new feature, kicking off
  an Epic, initiating a project, receiving a raw idea or opportunity, or when the user says
  "new feature", "start an Epic", "I want to build...", "we need to add...", "initialize feature",
  "create feature README", "kick off", "new initiative", or "feature inception".
  Produces the feature README.md that gates entry into Discover (requirements, scope) and all
  downstream SDLC phases. Relevant for feature planning, Epic initiation, product ideation,
  initiative framing, and pre-discovery inception.
---

# Discover Feature

> Define **what** a feature is and **why** it matters — before requirements, scope, or design.

## Quick Reference

| Aspect | Details |
|--------|---------|
| **Invokes** | `/discover-requirements` |
| **Invoked By** | None — this is the SDLC entry point |
| **Key Tools** | Read, Write, Bash |
| **Artifact** | `docs/designs/YYYY/NNN-{feature-name}/README.md` |
| **Shared Refs** | `sdlc-shared/refs/sdlc-log-format.md` |

---

## Core Workflow

1. **Elicit**: Extract the core idea from user input — what problem exists, what opportunity was identified, or what stakeholder need triggered this initiative. Ask clarifying questions if the input is ambiguous. Do not proceed with assumptions.

2. **Frame**: Structure the idea into the six README sections: Vision, Goals, Rationale, Value Proposition, Non-Goals, and Open Questions. Each section serves a distinct framing purpose — do not merge or skip sections.

3. **Assign Sequence Number**: Scan `docs/designs/{current-year}/` for existing feature directories. Determine the next available sequence number (`NNN`). If the directory does not exist, start at `001`.

4. **Create Directory**: Create `docs/designs/YYYY/NNN-{feature-name}/` using kebab-case for the feature name. The directory is the feature's home for all future SDLC artifacts.

5. **Write README.md**: Generate the README.md using the template below. Keep language outcome-oriented, not implementation-oriented. No technical solutions, architecture choices, or task breakdowns belong here.

6. **Gate**: Confirm the README.md with the user. No downstream SDLC work (requirements, scope, design, breakdown, implementation) begins until the feature README is ratified. Once confirmed, inform the user of the next step: invoke `/discover-requirements`.

7. **Write SDLC Log Entry**: After the README.md is confirmed, append an entry to `{feature-dir}/sdlc-log.md` following [sdlc-shared/refs/sdlc-log-format.md](../sdlc-shared/refs/sdlc-log-format.md). If `sdlc-log.md` doesn't exist, create it with the header first (see the shared ref for the header format).

   ```markdown
   ## [YYYY-MM-DD HH:MM] — /discover-feature — Discovery

   - **Task:** N/A
   - **Agents dispatched:** None (inception handled directly)
   - **Skills invoked:** discover-feature
   - **Artifacts produced:** README.md
   - **Outcome:** {summary of what was framed — e.g., "Feature inception complete for Multi-Tenant Workspaces with 3 goals and 2 non-goals defined."}
   - **Findings:** {any open questions or concerns — or "None"}
   ```

---

## Decision Tree

```
User Input
    │
    ├─► Clear problem/opportunity stated?
    │       ├─► YES ──► Frame directly into README sections
    │       └─► NO  ──► Elicit: ask targeted questions (see Elicitation Prompts)
    │
    ├─► Product-initiated (user-facing feature)?
    │       └─► YES ──► Emphasize user value, business outcomes in Value Proposition
    │
    ├─► Engineering-initiated (tech debt, platform, enabler)?
    │       └─► YES ──► Emphasize technical rationale, cost of inaction, risk reduction
    │
    └─► Existing feature directory found?
            ├─► YES ──► Next sequence number
            └─► NO  ──► Create year directory, start at 001
```

---

## Elicitation Prompts

When user input is vague or incomplete, use these targeted questions to extract what is needed. Ask only what is missing — never interrogate exhaustively.

| Gap | Prompt |
|-----|--------|
| Problem unclear | "What problem does this solve? Who experiences it and when?" |
| Value undefined | "If this ships successfully, what changes for the user or the business?" |
| Rationale missing | "Why now? What triggered this initiative — user feedback, a metric, a strategic bet?" |
| Boundaries fuzzy | "What should this feature explicitly NOT do? What's the nearest related concern we should leave out?" |
| Goals too vague | "Can you describe a concrete outcome that would mean this feature succeeded?" |

---

## README.md Template

```markdown
# {Feature Name}

> One-sentence summary of what this feature is.

## Vision

A single paragraph describing the desired future state once this feature exists. Paint the
picture of what changes — for users, for the system, or for the team. Stay outcome-oriented.
No implementation details.

## Goals

Outcome-oriented goals that define success. Each goal answers "what changes when this is done?"
not "what do we build." Limit to 3–5 goals.

- **Goal 1**: {Outcome statement}
- **Goal 2**: {Outcome statement}
- **Goal 3**: {Outcome statement}

## Rationale

Why are we building this now? Explain the trigger — user pain, business opportunity, technical
risk, strategic alignment, or cost of inaction. Connect to measurable evidence where available
(metrics, incidents, customer feedback, competitive pressure).

## Value Proposition

Who benefits and how? State the value for each stakeholder group affected. Be specific about
the expected impact — faster workflows, reduced errors, unlocked capabilities, risk mitigation.

| Stakeholder | Value |
|-------------|-------|
| {User/Role} | {Concrete benefit} |
| {User/Role} | {Concrete benefit} |

## Non-Goals

What this feature explicitly does NOT address. Every feature has boundaries — stating them
early prevents scope creep before scope even begins. List concerns that are adjacent but
excluded from this initiative.

- {Adjacent concern that is out of scope}
- {Related feature that will not be addressed here}

## Open Questions

Unknowns that require resolution during discovery. These may trigger Spikes. Each question
should indicate who might have the answer or what research is needed.

- {Question} — {Suggested resolution path}

## Status

| Phase | State |
|-------|-------|
| **Inception** | ✅ Complete |
| **Discovery** | ⬜ Not Started |
| **Design** | ⬜ Not Started |
| **Breakdown** | ⬜ Not Started |
| **Implementation** | ⬜ Not Started |
| **Ship** | ⬜ Not Started |
```

---

## Skill Chaining

### Invoke Downstream Skills When

| Condition | Invoke | Handoff Context |
|-----------|--------|-----------------|
| README.md ratified by user | `/discover-requirements` | Feature README path, goals, vision |

### Chaining Syntax

When the README.md is confirmed, output:

```markdown
**Feature Inception Complete:** `docs/designs/YYYY/NNN-{feature-name}/README.md`

**Next Phase — Discovery:**
The feature README is ratified. The next step is to invoke:
- `/discover-requirements` to structure detailed requirements with acceptance criteria

The requirements artifact will be created in the same feature directory.
```

---

## Patterns & Anti-Patterns

### ✅ Do

- Keep README.md outcome-oriented — describe **what changes**, not **how to build it**
- State Non-Goals explicitly — boundaries set early prevent scope creep downstream
- Include Open Questions — unknowns surfaced early become Spikes, not surprises
- Use the stakeholder value table — forces concrete thinking about who benefits
- Assign sequence numbers by scanning existing directories — never hardcode or guess

### ❌ Don't

- Include technical solutions, architecture choices, or technology selections — that is Design
- Write user stories, acceptance criteria, or detailed requirements — that is `/discover-requirements`
- Break down into tasks or list implementation steps — that is `/tasks-breakdown`
- Skip Non-Goals — an unbounded feature is a feature that will grow uncontrollably
- Create the README without user confirmation — this is a gate, not a formality

---

## Examples

### Example 1: Product-Initiated Feature

**Input:**

```
We need to add multi-tenant support so enterprise customers can manage
separate workspaces for different teams.
```

**Output:** `docs/designs/2026/003-multi-tenant-workspaces/README.md`

```markdown
# Multi-Tenant Workspaces

> Enable enterprise customers to manage isolated workspaces per team within a single account.

## Vision

Enterprise customers operate a single account with multiple isolated workspaces — each
with its own data, users, and configuration. Teams work independently without cross-
contamination while administrators maintain centralized oversight and billing.

## Goals

- **Workspace isolation**: Each workspace operates with complete data separation
- **Centralized administration**: Account owners manage all workspaces from one dashboard
- **Self-service provisioning**: Team leads create and configure workspaces without support tickets

## Rationale

Three of our five largest enterprise prospects have stalled in procurement due to the
absence of workspace isolation. Current workaround — separate accounts per team — creates
billing complexity and prevents centralized administration. This is blocking $2.4M ARR
in pipeline.

## Non-Goals

- Per-workspace billing (billing remains at account level)
- Cross-workspace data sharing or queries
- Custom branding per workspace
```

### Example 2: Engineering-Initiated Feature

**Input:**

```
Our event handlers have no idempotency. We reprocess duplicates constantly.
```

**Output:** `docs/designs/2026/004-event-idempotency/README.md`

```markdown
# Event Processing Idempotency

> Eliminate duplicate event processing across all async message handlers.

## Vision

Every event handler in the system processes each unique event exactly once, even under
retry storms, infrastructure failover, or consumer rebalancing. Duplicate detection is
automatic and does not require per-handler implementation effort.

## Goals

- **Exactly-once processing semantics**: Duplicate events are detected and skipped silently
- **Zero per-handler boilerplate**: Idempotency is a cross-cutting concern, not per-handler code
- **Observable duplicate rates**: Metrics expose duplicate frequency per handler and source

## Rationale

Post-mortem from January 15 incident traces root cause to duplicate SQS deliveries during
a scaling event. Three handlers lacked deduplication, causing 12,000 duplicate records and
a 4-hour manual cleanup. This is the third duplicate-processing incident in 8 weeks. Cost
of inaction: recurring data corruption and engineer time spent on manual remediation.

## Non-Goals

- Changing message broker technology
- Implementing full event sourcing
- Addressing message ordering guarantees
```

---

## Quality Gates

Before completing feature inception:

- [ ] README.md contains all six sections: Vision, Goals, Rationale, Value Proposition, Non-Goals, Open Questions
- [ ] Goals are outcome-oriented (no implementation details, technology names, or architecture choices)
- [ ] Non-Goals explicitly exclude at least one adjacent concern
- [ ] Feature directory follows naming convention: `docs/designs/YYYY/NNN-{kebab-case-name}/`
- [ ] Sequence number is correct (scanned from existing directories, no duplicates)
- [ ] User has confirmed the README.md before any downstream skill is invoked
