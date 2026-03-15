# Template: `docs/adrs/NNNN-{short-kebab-title}.md`

> Architectural Decision Records capture significant decisions that affect system structure,
> constrain future choices, or would not be obvious from reading the code alone.

## When to Write an ADR

| Signal | ADR Needed? |
|--------|-------------|
| New technology or library adopted | Yes |
| Architecture pattern chosen (with alternatives rejected) | Yes |
| Data model decision with trade-offs | Yes |
| Security or auth model change | Yes |
| Integration pattern decision (sync vs async, REST vs gRPC) | Yes |
| Decision to NOT do something (deliberate rejection) | Yes |
| Standard implementation following existing patterns | No |
| Bug fix or minor enhancement within existing boundaries | No |
| Deviation classified as "Improvement" in release.md | Maybe (if it establishes a new pattern) |

## Where to Source Decisions

- `hld.md` — Architecture style choices, technology selections, integration pattern decisions
- `lld.md` — Data model decisions, contract design decisions, component pattern choices
- `release.md` — Key Technical Decisions table, deviations classified as "Trade-off" or significant "Improvement"
- `sdlc-log.md` — Findings that led to design changes during implementation

## Template

Use this template when writing ADRs:

```markdown
# ADR-[NNNN]: [Short Decision Title in Present Tense]

---
id: "ADR-[NNNN]"
title: "[Short Decision Title]"
status: "[Proposed | Accepted | Deprecated | Superseded]"
date: "YYYY-MM-DD"
deciders: "[List of people or roles]"
tags: ["[domain]", "[component]", "[category]"]
supersedes: ""
superseded_by: ""
---

## Summary

In the context of **[system or component]**, facing **[problem or requirement]**,
we decided for **[chosen option]** and against **[rejected options]**, to achieve
**[desired outcome]**, accepting **[trade-off or downside]**.

## Context

[Describe the situation, problem, and forces creating tension. Be specific about
constraints, requirements, and assumptions. Include relevant metrics, deadlines,
or scale projections.]

## Decision Drivers

1. [Most important driver]
2. [Second driver]
3. [Third driver]

## Options Considered

### Option 1: [Name] — Chosen

[Brief description of this option and how it works.]

- **Good:** [Advantage]
- **Bad:** [Disadvantage or risk]

### Option 2: [Name]

[Brief description of this option and how it works.]

- **Good:** [Advantage]
- **Bad:** [Disadvantage or risk]

## Decision

We will **[state the decision clearly]**.

[1-3 sentences of essential detail: versions, configurations, boundaries, scope.]

## Consequences

**Positive:**
- [What we gain]

**Negative:**
- [What we accept]

**Risks:**
- [Identified risk + mitigation]

## Constraints & Boundaries

- **Applies to:** [What systems, services, or code areas this decision governs]
- **Does NOT apply to:** [What is explicitly out of scope]
- **Revisit when:** [Trigger conditions for re-evaluation]

## Related

- [ADR-NNNN: Related decision](./NNNN-related-decision.md)
- [Link to feature design directory](../designs/YYYY/NNN-{name}/)
```

## Writing Guidelines for ADRs

### File Naming

1. Check `docs/adrs/` for the highest existing sequence number
2. Use the next number: `docs/adrs/NNNN-{short-kebab-title}.md`
3. Set status to `Accepted` (the decision was made and implemented)

### Summary (Y-Statement)

The summary is the most important line — it's the TL;DR for humans skimming and for AI
assistants retrieving context. Follow the Y-Statement format exactly:

> In the context of **X**, facing **Y**, we decided for **Z** and against **W**,
> to achieve **A**, accepting **B**.

### Context

Write in neutral, factual language. State the forces at play: technical constraints,
business requirements, team capabilities, deadlines, scale projections, and dependencies.
An AI assistant reading this section should fully understand WHY a decision was needed.

### Options Considered

- At least 2 options, ideally 3
- Mark the chosen option clearly: `### Option N: [Name] — Chosen`
- Be honest about disadvantages of the chosen option and advantages of rejected options
- If an option was rejected, explain why its disadvantages outweighed its advantages

### Constraints & Boundaries

This is **critical for AI assistant consumption**. This section defines what is and isn't
covered by the decision. Future AI assistants use this to determine if the ADR applies to
a task they're working on.

- **Applies to:** Be specific — list service names, directory paths, or component names
- **Does NOT apply to:** Be explicit about out-of-scope areas to prevent over-application
- **Revisit when:** Define concrete trigger conditions, not vague timeframes

### Related Links

- Always link to the feature design directory: `../designs/YYYY/NNN-{name}/`
- Link to related ADRs (supersedes, complements, conflicts)
- Link to specific sections of HLD/LLD that motivated the decision

### Tags

Use tags that help with filtering and discovery:
- Domain tag: the bounded context or feature (e.g., `demo-mvp`, `auth`)
- Component tag: the affected component (e.g., `data`, `api`, `infrastructure`)
- Category tag: the decision category (e.g., `technology`, `pattern`, `security`)
