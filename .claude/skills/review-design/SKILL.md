---
name: review-design
version: 1.0.0
description: |
  Review code designs for architectural soundness, domain correctness, and quality attribute coverage.
  Evaluates scope assessment, context completeness, DDD alignment, structural coherence, and risks.
  Use when validating design documents, reviewing architectural decisions, assessing domain models,
  or gate-checking before implementation. Relevant for pre-implementation reviews, architecture validation.
chains:
  invoked-by:
    - skill: design/code
      context: "Post-design quality gate"
    - skill: design/api
      context: "API contract validation"
  invokes:
    - skill: design/code
      when: "Critical findings require revision"
    - skill: implement/python
      when: "Design passes, Python implementation needed"
---

# Design Review

> Validate architectural soundness before implementation. Catch design flaws when cheapest to fix.

## Quick Reference

| Aspect | Details |
|--------|---------|
| **Scope** | Design documents, architecture decisions, domain models, interface contracts |
| **Invoked By** | `design/*`, `/review` command |
| **Invokes** | `design/code` (failure) → `implement/*` (pass) |
| **Verdicts** | `PASS` · `PASS_WITH_SUGGESTIONS` · `NEEDS_WORK` · `FAIL` |

---

## Core Workflow

```
1. SCOPE    →  Locate design artifacts (**/design*.md, **/architecture*.md)
2. CONTEXT  →  Load principles.md, design/code/SKILL.md, refs/ddd.md
3. ANALYZE  →  Evaluate against 7 design phases
4. CLASSIFY →  Assign severity (BLOCKER → SUGGESTION)
5. VERDICT  →  Determine pass/fail from severity distribution
6. REPORT   →  Output structured findings
7. CHAIN    →  Route to revision or implementation
```

---

## Evaluation Criteria

### Phase 1: Scope Assessment (SA)

| ID | Criterion | Severity |
|----|-----------|----------|
| SA.1 | Complexity matches task reality (Large≠Light design) | 🔴 BLOCKER |
| SA.2 | Design depth explicitly stated | 🟡 MAJOR |
| SA.3 | Appropriate phases executed for complexity | 🟠 CRITICAL |

### Phase 2: Context Gathering (CG)

| ID | Criterion | Severity |
|----|-----------|----------|
| CG.1 | Existing patterns examined (evidence of Glob/Read) | 🟡 MAJOR |
| CG.2 | Constraints documented (technical, domain, quality) | 🔵 MINOR |
| CG.3 | Stakeholders identified | 🔵 MINOR |

### Phase 3: Domain Analysis (DA)

| ID | Criterion | Severity |
|----|-----------|----------|
| DA.1 | Ubiquitous language applied (domain terms, not jargon) | 🟠 CRITICAL |
| DA.2 | Bounded context identified (clear ownership) | 🟠 CRITICAL |
| DA.3 | Aggregates correctly defined (consistency boundaries) | 🟠 CRITICAL |
| DA.4 | Entity vs Value Object distinction correct | 🟡 MAJOR |
| DA.5 | Domain events identified for state changes | 🟡 MAJOR |

### Phase 4: Structural Design (SD)

| ID | Criterion | Severity |
|----|-----------|----------|
| SD.1 | Single responsibility per module | 🟠 CRITICAL |
| SD.2 | Dependencies injected (no internal instantiation) | 🟠 CRITICAL |
| SD.3 | Public interface minimal | 🟡 MAJOR |
| SD.4 | Implementation details hidden | 🟡 MAJOR |
| SD.5 | Testable in isolation | 🟡 MAJOR |
| SD.6 | Follows existing conventions | 🟡 MAJOR |

### Phase 5: Quality Attributes (QA)

| ID | Criterion | Severity |
|----|-----------|----------|
| QA.1 | Testability: dependencies injectable, pure functions identified | 🟡 MAJOR |
| QA.2 | Robustness: validation, error types, timeouts planned | 🟡 MAJOR |
| QA.3 | Observability: logging, tracing, metrics identified | 🟡 MAJOR |
| QA.4 | Performance: data structures match access patterns | 🔵 MINOR |
| QA.5 | Evolvability: extension points, adapters noted | 🔵 MINOR |

### Phase 6: Interface Design (ID)

| ID | Criterion | Severity |
|----|-----------|----------|
| ID.1 | Contracts defined before implementation | 🟠 CRITICAL |
| ID.2 | Request/response shapes explicit (Pydantic/types) | 🟡 MAJOR |
| ID.3 | Error contracts documented | 🟡 MAJOR |
| ID.4 | Events self-contained (no callback required) | 🟡 MAJOR |

### Phase 7: Risk Assessment (RA)

| ID | Criterion | Severity |
|----|-----------|----------|
| RA.1 | Complexity risks identified (YAGNI evaluated) | 🔵 MINOR |
| RA.2 | Coupling risks documented with mitigation | 🟡 MAJOR |
| RA.3 | Breaking change risks assessed | 🟡 MAJOR |
| RA.4 | Security boundaries explicit | 🟠 CRITICAL |

---

## Verdict Logic

```
Any BLOCKER?           → FAIL (redesign required)
Any CRITICAL?          → NEEDS_WORK (targeted fixes)
Multiple MAJOR?        → NEEDS_WORK (quality debt)
Few MAJOR/MINOR only?  → PASS_WITH_SUGGESTIONS
SUGGESTION only?       → PASS (ready for implementation)
```

---

## Patterns

### ✅ Quality Design Indicators

- Explicit complexity + design depth declaration
- DDD terminology (Aggregate, Entity, Value Object, Domain Event)
- Clear module structure with separation of concerns
- Interface contracts (Protocol/ABC, OpenAPI specs)
- Quality attributes addressed for each relevant dimension

### ❌ Red Flags

- "Manager" or "Handler" classes (violates single responsibility)
- Direct database/service access (no abstraction layer)
- Missing complexity assessment
- No interface contracts
- Mixed concerns in single module

---

## Finding Format

```markdown
### [🟠 CRITICAL] {{Finding Title}}

**Location:** `{{file}}:{{line}}`
**Criterion:** {{ID}} - {{Name}}

**Issue:** {{Description}}

**Evidence:**
\`\`\`
{{code_snippet}}
\`\`\`

**Suggestion:** {{Remediation}}
**Rationale:** {{Why this matters}}
```

---

## Summary Format

```markdown
# Design Review Summary

## Verdict: {{EMOJI}} {{VERDICT}}

| Metric | Count |
|--------|-------|
| Phases Reviewed | {{N}} |
| Blockers | {{N}} |
| Critical | {{N}} |
| Major | {{N}} |
| Minor | {{N}} |

## Key Findings
1. {{Finding 1}}
2. {{Finding 2}}
3. {{Finding 3}}

## Chain Decision
**Target:** `{{skill}}` | **Reason:** {{rationale}}
```

---

## Skill Chaining

| Verdict | Action | Target |
|---------|--------|--------|
| `FAIL` | Mandatory redesign | `design/code` |
| `NEEDS_WORK` | Targeted fixes | `design/code` |
| `PASS_WITH_SUGGESTIONS` | Optional improvements | None → implement |
| `PASS` | Continue pipeline | `implement/{domain}` |

**Handoff to design/code:**
```
Priority: {{BLOCKER/CRITICAL IDs}}
Constraint: Preserve {{passed phases}}
Focus: {{failed criterion categories}}
```

**Handoff to implement:**
```
Design: {{design document link}}
Interfaces: {{key contracts}}
Quality: {{requirements from QA phase}}
```

**Re-review:** Max 3 iterations before human escalation.

---

## Deep References

| Reference | When to Load |
|-----------|--------------|
| `skills/design/code/refs/ddd.md` | Complex domain model evaluation |
| `skills/design/code/refs/modularity.md` | Structural design concerns |
| `rules/principles.md` | Validation against standards |
| `refs/testability.md` | Quality attribute depth |
| `refs/robustness.md` | Resilience requirements |

---

## Quality Gates

Before finalizing:







- [ ] All 7 phases evaluated (or N/A with rationale)
- [ ] Each finding has location + criterion + severity
- [ ] Severity distribution justifies verdict
- [ ] BLOCKER/CRITICAL have actionable remediation
- [ ] Chain decision explicit with handoff context
