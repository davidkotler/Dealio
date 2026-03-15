---
name: discover-requirements
description: |
  Elicit, structure, and validate product and feature requirements from natural language
  descriptions, user stories, or stakeholder input. Use when starting a new feature,
  receiving a product brief, translating business needs to engineering requirements,
  or when the user says "I need to build...", "product wants...", "new feature request",
  "here's the PRD", "requirements for...", "what do we need to build", or "translate this
  brief into requirements". Produces structured requirement artifacts that gate downstream
  scoping and design. Relevant for feature planning, product requirements, stakeholder
  alignment, pre-design discovery, and requirements engineering.
---

# Discover Requirements

> Surface what the system must do, how well it must do it, and what remains unknown—before any design or code.

## Quick Reference

| Aspect | Details |
|--------|---------|
| **Invokes** | `/design-system` (HLD), `/design-lld` (LLD) |
| **Invoked By** | Direct user request, after `/discover-feature` completes |
| **Key Tools** | Read, Write, Edit |
| **Output** | `{feature-dir}/prd.md` — Structured requirements document |
| **Shared Refs** | `sdlc-shared/refs/feature-resolution.md`, `sdlc-shared/refs/sdlc-log-format.md` |

---

## Core Workflow

### 0. Resolve Feature Directory

Before gathering requirements, resolve which feature directory to operate on. Follow the algorithm in [sdlc-shared/refs/feature-resolution.md](../sdlc-shared/refs/feature-resolution.md):

1. If the user passed an argument (e.g., `/discover-requirements 001-sdlc-claude-commands`) — resolve to the matching feature directory under `docs/designs/*/`
2. If no argument — scan `docs/designs/` across all years, present a selection list of existing features that have `README.md` (inception complete)
3. If argument doesn't match — report the error and present the selection list
4. If the resolved feature directory has no `README.md` — block and instruct the user to run `/discover-feature` first

The resolved path becomes `{feature-dir}` for all subsequent steps. Read `{feature-dir}/README.md` to understand the feature's vision, goals, rationale, and non-goals — this is the primary input context for requirements elicitation.

### 1. Gather Context

Read all input the user provides: PRDs, briefs, Slack threads, tickets, verbal descriptions.
Identify the input type:

- **Formal PRD/brief** → Extract and restructure
- **Verbal/chat description** → Elicit missing details
- **User stories** → Validate completeness, normalize format
- **Existing system change** → Read current code/docs first to understand baseline

### 2. Elicit Missing Information

Never accept vague requirements at face value. Ask targeted questions to surface:

- **Unstated assumptions** — "Who is the user? What's the happy path? What exists today?"
- **Edge cases** — "What happens when X fails? What if the input is empty? What about concurrent access?"
- **Constraints** — "What can't change? What's the deadline? What tech is mandated?"
- **Scale** — "How many users/requests/records? What growth is expected?"

Batch questions into a single focused message. Do not scatter questions across many turns.
Prioritize questions that would change the architecture or scope if answered differently.

### 3. Structure Requirements

Parse all gathered input into these categories:

**Functional Requirements (what the system does):**
Normalize each into user story format with acceptance criteria.
See [refs/user-stories.md](refs/user-stories.md) for patterns, Given/When/Then format, and splitting techniques.

**Non-Functional Requirements (how well it does it):**
Walk through quality attribute categories systematically.
See [refs/nfr-checklist.md](refs/nfr-checklist.md) for the full checklist.

At minimum, explicitly address:







- Performance (latency targets, throughput)

- Availability (uptime target, failure tolerance)

- Security (authentication, authorization, data sensitivity)

- Observability (logging, tracing, metrics, alerting)


- Scalability (expected load, growth trajectory)





**Constraints:**



- Technical: existing stack, backward compatibility, infrastructure limits


- Business: deadlines, budget, compliance, regulatory
- Organizational: team capacity, skill gaps, cross-team dependencies



**Dependencies:**



- Upstream systems this feature consumes from
- Downstream systems this feature produces for


- Third-party integrations required
- Data dependencies (schemas, migrations, shared state)



### 4. Resolve Ambiguity

After structuring, audit for:


- **Contradictions** — requirements that conflict with each other or existing system behavior
- **Undefined terms** — domain language used without definition
- **Gaps** — scenarios with no specified behavior

- **Implicit scope** — features assumed but never stated

Produce an explicit **Open Questions** list. Each question must state why it matters (what decision it blocks).


### 5. Validate and Output

Produce the requirements document and write it to `{feature-dir}/prd.md`.
Before finalizing, verify:

- Every functional requirement has at least one acceptance criterion
- NFRs include measurable targets, not vague qualities ("fast" → "p95 < 200ms")
- Dependencies list includes system names, not just concepts
- Open questions are specific and actionable

### 6. Write SDLC Log Entry

After requirements are confirmed by the user, append an entry to `{feature-dir}/sdlc-log.md` following [sdlc-shared/refs/sdlc-log-format.md](../sdlc-shared/refs/sdlc-log-format.md). If `sdlc-log.md` doesn't exist, create it with the header first (see the shared ref for the header format).

```markdown
## [YYYY-MM-DD HH:MM] — /discover-requirements — Discovery

- **Task:** N/A
- **Agents dispatched:** None (requirements handled directly)
- **Skills invoked:** discover-requirements
- **Artifacts produced:** prd.md
- **Outcome:** {summary — e.g., "Requirements structured into 6 FRs and 4 NFRs with acceptance criteria. 3 open questions identified."}
- **Findings:** {any issues or notes — or "None"}
```

---

## Output Template

```markdown
# Requirements: [Feature/Project Name]

**Date:** [date]
**Status:** Draft | Under Review | Approved
**Author:** [who produced this]
**Stakeholders:** [who needs to sign off]

---

## 1. Overview

[2-3 sentence summary: what is being built and why.]

## 2. Functional Requirements

### FR-1: [Short Title]
**As a** [role], **I want** [capability], **so that** [benefit].

**Acceptance Criteria:**
- **Given** [precondition], **when** [action], **then** [expected result]
- **Given** [precondition], **when** [action], **then** [expected result]

### FR-2: [Short Title]
[repeat pattern]

## 3. Non-Functional Requirements

### NFR-1: [Category] — [Short Title]
- **Target:** [measurable value]
- **Rationale:** [why this matters]
- **Validation:** [how to test/measure]

### NFR-2: [Category] — [Short Title]
[repeat pattern]

## 4. Constraints

### Technical Constraints
- [constraint and its implication]

### Business Constraints
- [constraint and its implication]

### Organizational Constraints
- [constraint and its implication]

## 5. Dependencies

| Dependency | Type | Direction | Impact if Unavailable |
|------------|------|-----------|----------------------|
| [system/service] | [data/API/infra] | [upstream/downstream] | [what breaks] |

## 6. Open Questions

| # | Question | Why It Matters | Blocks |
|---|----------|----------------|--------|
| Q1 | [specific question] | [decision it affects] | [what can't proceed] |

## 7. Glossary

| Term | Definition |
|------|-----------|
| [domain term] | [agreed meaning in this context] |
```

---

## Decision Tree

```
/discover-requirements invoked
    │
    ▼
Resolve Feature Directory (refs/feature-resolution.md)
    │
    ├─► No README.md? → Block: "Run /discover-feature first"
    │
    ▼
Read README.md for context → Gather user input
    │
    ├─► Formal PRD/brief?
    │     └─► Extract → Structure → Identify gaps → Ask targeted questions
    │
    ├─► Verbal/vague description?
    │     └─► Elicit broadly → Structure → Validate with user
    │
    ├─► User stories already written?
    │     └─► Validate format → Check acceptance criteria → Fill NFR gaps
    │
    └─► Change to existing system?
          └─► Read current code/docs → Identify delta → Structure change requirements
    │
    ▼
Write prd.md → Confirm with user → Write SDLC log → Suggest /design
```



---

## Skill Chaining

| Condition | Invoke | Handoff Context |
|-----------|--------|-----------------|
| Requirements approved, ready for design | `/design-system` | Feature directory path, prd.md, README.md |
| Requirements reveal major architectural decisions | `/design-system` | NFRs, constraints, dependencies |

When requirements are confirmed, output:

```markdown
**Requirements Complete:** `{feature-dir}/prd.md`

**Next step:** Run `/design-system {feature-identifier}` to produce the high-level design, then `/design-lld` for low-level design.
```


---


## Patterns

### ✅ Do

- Batch clarifying questions into a single focused message

- Make every NFR measurable with a specific target
- Flag assumptions explicitly rather than silently embedding them
- Include a glossary when domain terms appear
- Separate what the system must do from how well it must do it

### ❌ Don't

- Accept "the system should be fast" without quantifying "fast"
- Invent requirements the user didn't state or imply
- Skip NFRs because the user only mentioned functional needs
- Ask open-ended questions when specific options narrow scope faster
- Combine multiple unrelated features into a single requirement

---

## Examples

### Example 1: Vague Input → Structured Output

**Input:**
```
"We need a notification system so users know when their orders ship."
```

**Action:**
Ask: "Which channels (email, push, SMS)? What order states trigger notifications?
Should users configure preferences? What volume—orders per day? Latency tolerance
between state change and notification delivery?"

Then structure answers into FR/NFR/constraints/dependencies using the output template.

### Example 2: PRD Extraction

**Input:** A product brief document describing a new feature.

**Action:**
Read the document. Extract functional requirements as user stories.
Identify NFRs implied but not stated (e.g., brief says "real-time" but no latency target).
List contradictions (e.g., "simple MVP" but lists 12 features).
Produce open questions for anything blocking design.

---

## Deep References

- **[user-stories.md](refs/user-stories.md)**: User story patterns, acceptance criteria formats (Given/When/Then), INVEST criteria, and story splitting techniques
- **[nfr-checklist.md](refs/nfr-checklist.md)**: Systematic checklist of non-functional requirement categories with elicitation prompts for each

---

## Quality Gates

Before completing a requirements artifact:

- [ ] Every functional requirement follows user story format with acceptance criteria
- [ ] NFRs cover at minimum: performance, availability, security, observability, scalability
- [ ] Every NFR has a measurable target and validation approach
- [ ] All dependencies list concrete system/service names with impact analysis
- [ ] Open questions specify what decision each blocks
- [ ] No undefined domain terms remain (glossary covers all)
- [ ] Constraints distinguish technical, business, and organizational categories
