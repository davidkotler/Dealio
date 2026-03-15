---
name: update-documentation
version: 1.1.0
description: |
  Capture every architectural decision, boundary change, infrastructure evolution, and service
  responsibility shift from a completed feature into the system's knowledge base documentation.
  This is the final mandatory SDLC stage (Stage 12 / Phase 6) — code without updated
  documentation is incomplete delivery.
  Reads the feature's design artifacts (README.md, prd.md, hld.md, lld.md, release.md) and the
  actual codebase to understand what was built, then systematically updates docs/adrs/,
  docs/architecture/, docs/services/, docs/cross-cutting/, and writes the design reconciliation.
  Invokes `/diagram-architecture` to generate high-quality Mermaid architecture diagrams
  (C4, sequence, ER, state, deployment) for every documentation area that describes boundaries,
  flows, or topology — ensuring consistent styling, labeled edges, and accessibility.
  Use when a feature has passed QA & Product Review, running `/update-documentation`, or when
  the user says "update docs", "update documentation", "document the feature", "write ADRs",
  "capture decisions", "close the epic", "finalize documentation", "update architecture docs",
  "update service docs", "reconcile design", "document what we built", "feature documentation",
  "sync docs", "knowledge base update", or "docs for this feature".
---

# /update-documentation — System Documentation Update

> Read what was planned, what was built, and what changed — then update the system's knowledge
> base so the codebase remains understood, maintainable, and evolvable. Documentation reflects
> the **as-built** system, not the as-designed intent.

## Quick Reference

| Aspect | Details |
|--------|---------|
| **Phase** | Update Documentation (Stage 12 — final stage before Epic closure) |
| **Gate** | `release.md` exists (QA & Product Review has passed) |
| **Invoked By** | Developer after `/qa-review` produces `release.md` with PASS or PASS WITH NOTES |
| **Produces** | ADRs, architecture docs, service docs, cross-cutting docs, design reconciliation |
| **Reads** | `README.md`, `prd.md`, `hld.md`, `lld.md`, `tasks-breakdown.md`, `release.md`, `sdlc-log.md`, **actual source code** |
| **Updates** | `docs/adrs/`, `docs/architecture/`, `docs/services/`, `docs/cross-cutting/`, `{feature-dir}/release.md` |
| **Shared Refs** | [feature-resolution.md](../sdlc-shared/refs/feature-resolution.md), [sdlc-log-format.md](../sdlc-shared/refs/sdlc-log-format.md), [phase-gating.md](../sdlc-shared/refs/phase-gating.md) |
| **Deep Refs** | See per-type template refs below |
| **ADR Ref** | [refs/adr.md](refs/adr.md) |
| **Architecture Refs** | [refs/architecture/system-overview.md](refs/architecture/system-overview.md), [component-boundaries.md](refs/architecture/component-boundaries.md), [integration-patterns.md](refs/architecture/integration-patterns.md), [infrastructure.md](refs/architecture/infrastructure.md), [technology-stack.md](refs/architecture/technology-stack.md) |
| **Service Refs** | [refs/service/readme.md](refs/service/readme.md), [api.md](refs/service/api.md), [data-model.md](refs/service/data-model.md), [sli-slo.md](refs/service/sli-slo.md), [infrastructure.md](refs/service/infrastructure.md) |
| **Cross-Cutting Refs** | [refs/cross-cutting/observability.md](refs/cross-cutting/observability.md), [cicd.md](refs/cross-cutting/cicd.md), [security.md](refs/cross-cutting/security.md), [authn-authz.md](refs/cross-cutting/authn-authz.md) |
| **Diagram Skill** | `/diagram-architecture` — invoke for all Mermaid diagram generation (see [Diagram Generation Guide](#diagram-generation-guide)) |
| **Writing Ref** | [refs/writing-guidelines.md](refs/writing-guidelines.md) |

---

## Core Workflow

### Step 1: Resolve Feature Directory

Resolve the target feature using [sdlc-shared/refs/feature-resolution.md](../sdlc-shared/refs/feature-resolution.md).
Never create a new feature directory — this skill only operates on existing features with
completed QA review.

### Step 2: Gate Check — QA Review Complete

This skill gates on QA & Product Review completion:

```
Check: {feature-dir}/release.md exists and is non-empty?
  ├── Yes → Proceed to Step 3
  └── No  → Block:
            "No release document found in {feature-dir}/."
            "Run `/qa-review` first to produce release.md."
```

Additionally, check the assessment in release.md:

```
Parse release.md for Assessment field
  ├── PASS or PASS WITH NOTES → Proceed to Step 3
  └── FAIL → Advisory:
            "Release assessment is FAIL. Documentation typically happens after
             a passing QA review. Options:
             1. Proceed anyway (document current state for reference)
             2. Go back and address the failures first"
```

### Step 3: Gather Feature Context

Read every artifact in the feature directory to build a complete picture of what was planned
and what was delivered:

**Design artifacts** (what was planned):
1. `README.md` — Goals, vision, value proposition, non-goals
2. `prd.md` — FRs, NFRs, MoSCoW priorities, risks, constraints, scope
3. `hld.md` (if exists) — Architectural decisions, bounded contexts, integration patterns,
   technology selections, quality attribute trade-offs
4. `lld.md` — Contracts (OpenAPI, AsyncAPI), data models, component designs, technical decisions

**Delivery artifacts** (what was built and validated):
5. `tasks-breakdown.md` — Task list with statuses, completion notes, deviations
6. `release.md` — The QA review output: architecture summary, requirements traceability,
   deviations, code quality assessment, implementation value assessment
7. `sdlc-log.md` — Chronological activity log of all SDLC phases

The release.md is your primary source of truth for what was actually built — it was produced
by `/qa-review` which read the actual source code. The design artifacts tell you what was
planned. The delta between them drives the documentation updates.

### Step 4: Identify Code Changes

Understand the scope of what changed in the codebase. Use the release.md's Code Footprint
and Component Map as your primary guide, supplemented by:

1. **Code footprint from release.md** — The organized inventory of directories, files, and
   their roles. This tells you which services, libraries, and infrastructure were touched.
2. **Git history** — Review commits associated with this feature to identify all changed files:
   ```bash
   git log --oneline --name-only --grep="{feature-related-terms}" -- '*.py' '*.ts' '*.yaml' '*.md'
   ```
3. **Deviations from release.md** — Every deviation (improvement, trade-off, or drift)
   represents a potential documentation update.

Produce an **Impact Map** — which documentation areas need updating:

```
Documentation Impact Map:
  ADRs needed:           {Y/N — significant decisions found?}
  Architecture updates:  {Y/N — component boundaries, integration patterns, or tech stack changed?}
  Service docs affected: {list of service names whose docs need updating}
  Cross-cutting updates: {list of concerns affected — o11y, security, cicd, auth, libs}
  Diagrams needed:       {list — see Diagram Generation Guide for which types per doc area}
  Design reconciliation: {Y/N — implementation diverged from design?}
```

Present this impact map to the user before proceeding. They may know about additional
documentation needs or want to skip certain areas.

### Step 5: Inventory Existing Documentation

Before writing anything, understand what documentation already exists:

1. **Scan `docs/adrs/`** — List existing ADRs. Note the highest sequence number for new ADRs.
2. **Scan `docs/architecture/`** — Which files exist? Read their current content.
3. **Scan `docs/services/`** — Which services have documentation? What does it cover?
4. **Scan `docs/cross-cutting/`** — Which cross-cutting concern areas have documentation?

For each area, determine whether you are:
- **Creating** new documentation (file doesn't exist)
- **Updating** existing documentation (file exists, needs additions or modifications)
- **Skipping** (this feature didn't affect this area)

### Step 6: Present Documentation Plan

Present a structured plan for user approval before writing any documentation:

```markdown
## Documentation Update Plan

**Feature:** {name}
**Impact:** {N} ADRs, {N} architecture docs, {N} service docs, {N} cross-cutting docs

### ADRs to Write

| # | Title | Context | Decision |
|---|-------|---------|----------|
| 1 | {ADR title} | {1-sentence context} | {1-sentence decision} |

### Architecture Docs to Update

| # | File | Action | What Changes |
|---|------|--------|--------------|
| 1 | `docs/architecture/{file}.md` | {Create / Update} | {what will be added or changed} |

### Service Docs to Update

| # | Service | File | Action | What Changes |
|---|---------|------|--------|--------------|
| 1 | {service-name} | `docs/services/{name}/{file}.md` | {Create / Update} | {what} |

### Cross-Cutting Docs to Update

| # | Concern | File | Action | What Changes |
|---|---------|------|--------|--------------|
| 1 | {concern} | `docs/cross-cutting/{area}/{file}.md` | {Create / Update} | {what} |

### Diagrams to Generate

| # | Target Document | Diagram Type | What It Communicates |
|---|-----------------|-------------|---------------------|
| 1 | `docs/architecture/{file}.md` | {C4 Context / Flowchart / Sequence / ...} | {1-sentence description} |

### Design Reconciliation

{Summary of what will be noted in the release summary — design-vs-reality divergences}

Shall I proceed with this documentation plan?
```

Wait for explicit approval before writing. The user may want to adjust the plan, add
decisions they want captured, or skip certain areas.

### Step 7: Write ADRs

For each significant decision identified from the feature's design and implementation,
consult [refs/adr.md](refs/adr.md) for the full template, writing guidelines, and decision
sourcing guidance.

**Writing each ADR:**
1. Determine the next sequence number from `docs/adrs/`
2. Follow the template in [refs/adr.md](refs/adr.md)
3. File name: `docs/adrs/NNNN-{short-kebab-title}.md`
4. Set status to `Accepted` (the decision was made and implemented)
5. Fill the **Constraints & Boundaries** section carefully — this is how AI assistants
   determine if the ADR applies to a future task
6. Link to the feature design directory and any related ADRs

### Step 8: Update Architecture Documentation

Update `docs/architecture/` to reflect the as-built system. Only update what this feature
changed — don't rewrite documentation for unrelated parts of the system.

**For each relevant architecture document, consult the corresponding template ref:**

| Document | Update When | Template |
|----------|------------|----------|
| `system-overview.md` | New service, bounded context, or major component added | [refs/architecture/system-overview.md](refs/architecture/system-overview.md) |
| `component-boundaries.md` | Service responsibilities changed, new domain boundaries defined | [refs/architecture/component-boundaries.md](refs/architecture/component-boundaries.md) |
| `integration-patterns.md` | New sync/async communication paths between services | [refs/architecture/integration-patterns.md](refs/architecture/integration-patterns.md) |
| `infrastructure.md` | New infrastructure components (databases, caches, queues, cloud resources) | [refs/architecture/infrastructure.md](refs/architecture/infrastructure.md) |
| `technology-stack.md` | New technology adopted or significant version upgrade | [refs/architecture/technology-stack.md](refs/architecture/technology-stack.md) |

**When creating or updating** (see [refs/writing-guidelines.md](refs/writing-guidelines.md) for tone and style):
1. Read the existing document first (if it exists)
2. Add the new content in the appropriate section — don't reorganize existing content
3. **Generate diagrams by invoking `/diagram-architecture`** — see the
   [Diagram Generation Guide](#diagram-generation-guide) for which diagram types to use per
   architecture document. Every architecture doc that describes boundaries, flows, or topology
   should include at least one diagram.
4. Reference the feature's design directory for detailed context
5. Ensure the documentation reflects the **as-built** state from `release.md`, not the
   as-designed state from `hld.md`/`lld.md`

### Step 9: Update Service Documentation

For each service affected by the feature, update or create documentation in
`docs/services/{service-name}/`.

**Identify affected services from:**
- `release.md` Code Footprint — which `services/` directories were touched
- `lld.md` — which services had contracts defined
- `tasks-breakdown.md` — which tasks targeted specific services

**For each affected service, consult the corresponding template ref:**

| Document | Path | Update When | Template |
|----------|------|------------|----------|
| `README.md` | `docs/services/{name}/README.md` | Service purpose, ownership, or responsibilities changed | [refs/service/readme.md](refs/service/readme.md) |
| API docs | `docs/services/{name}/api/` | New or modified endpoints, contract changes, deprecations | [refs/service/api.md](refs/service/api.md) |
| Data model | `docs/services/{name}/data-model/` | New entities, schema changes, access pattern changes | [refs/service/data-model.md](refs/service/data-model.md) |
| SLI/SLO | `docs/services/{name}/sli-slo/` | New performance targets, reliability objectives | [refs/service/sli-slo.md](refs/service/sli-slo.md) |
| Infrastructure | `docs/services/{name}/infrastructure/` | DB changes, cache configs, queue subscriptions, dependencies | [refs/service/infrastructure.md](refs/service/infrastructure.md) |

**Guidelines:**
- OpenAPI/AsyncAPI specs in `services/{name}/specs/` are the source of truth for contracts.
  Service docs provide **operational context** — rate limits, auth requirements, known consumers,
  deployment notes — not contract details.
- Data model docs should cover the **why** behind schema decisions, not just the schema itself.
  Access patterns, retention policies, and migration history belong here.
- SLI/SLO docs only need updating if the feature changes what reliability means for this service.

**Diagram generation:** For each affected service, invoke `/diagram-architecture` to generate
diagrams appropriate to the documentation being written. See the
[Diagram Generation Guide](#diagram-generation-guide) for the mapping of service doc types to
diagram types (ER diagrams for data models, sequence diagrams for API flows, etc.).

### Step 10: Update Cross-Cutting Documentation

Update `docs/cross-cutting/` for changes that span multiple services or affect shared
infrastructure.

**Identify cross-cutting changes from:**
- `release.md` — Look at the Component Map for shared components, the Code Quality Assessment
  for observability/security patterns, and any cross-service dependencies
- `lld.md` — Integration patterns, shared contracts, event schemas
- Code footprint — changes to `libs/`, shared infrastructure, CI/CD pipelines

**For each affected area, consult the corresponding template ref:**

| Area | Path | Update When | Template |
|------|------|------------|----------|
| Observability | `docs/cross-cutting/o11y/` | New metrics, dashboards, alerts, tracing spans, log schemas | [refs/cross-cutting/observability.md](refs/cross-cutting/observability.md) |
| CI/CD | `docs/cross-cutting/cicd/` | Pipeline changes, new quality gates, deployment strategy changes | [refs/cross-cutting/cicd.md](refs/cross-cutting/cicd.md) |
| Security | `docs/cross-cutting/security/` | New threat mitigations, encryption changes, input validation additions | [refs/cross-cutting/security.md](refs/cross-cutting/security.md) |
| Auth | `docs/cross-cutting/authn-authz/` | New auth flows, permission models, role definitions, tenant isolation | [refs/cross-cutting/authn-authz.md](refs/cross-cutting/authn-authz.md) |
| Shared Libs | Reference in relevant docs | Changes to `libs/` that affect multiple consumers | — |

**Diagram generation:** For cross-cutting documentation, invoke `/diagram-architecture` to
generate flow diagrams that show how the concern spans services. See the
[Diagram Generation Guide](#diagram-generation-guide) for the mapping (auth flows as sequence
diagrams, telemetry pipelines as flowcharts, etc.).

### Step 11: Design Reconciliation

The original design artifacts in `{feature-dir}/` are **immutable historical records** — they
are never modified. Instead, where implementation diverged from design, the divergences are
noted in a reconciliation section.

**Check if release.md already has a "Deviations from Design" section** (it should, from
`/qa-review`). If it does, this step verifies it's complete and adds a reconciliation
summary if missing. If it doesn't, write one.

The reconciliation captures:
- What the design specified vs. what was actually built
- Why the implementation diverged (improvement, trade-off, or drift)
- Whether the divergence should inform future design practices

If `release.md` already has comprehensive deviation documentation from `/qa-review`, this
step may only need to verify completeness. Don't duplicate what `/qa-review` already captured.

### Step 12: Present Summary and Confirm

After completing all documentation updates, present a summary:

```markdown
## Documentation Update Summary

**Feature:** {name}

### Artifacts Written

| # | Type | Path | Action | Summary |
|---|------|------|--------|---------|
| 1 | ADR | `docs/adrs/NNNN-{title}.md` | Created | {1-sentence decision} |
| 2 | Architecture | `docs/architecture/{file}.md` | Updated | {what was added} |
| 3 | Service | `docs/services/{name}/{file}.md` | Created | {what was documented} |
| 4 | Cross-cutting | `docs/cross-cutting/{area}/{file}.md` | Updated | {what changed} |

### Coverage Check

- [ ] Every significant decision has an ADR
- [ ] Architecture docs reflect the as-built system
- [ ] All affected services have updated documentation
- [ ] Cross-cutting changes are captured
- [ ] Design-vs-reality divergences are noted

### Epic Status

Documentation is complete. The Epic can be closed.
Next command: update the Epic ticket status to **Done**.
```

### Step 13: Write SDLC Log Entry

Append entry to `{feature-dir}/sdlc-log.md` per [sdlc-shared/refs/sdlc-log-format.md](../sdlc-shared/refs/sdlc-log-format.md):

```markdown
## [YYYY-MM-DD HH:MM] — /update-documentation — Update Documentation

- **Task:** N/A (feature-level documentation)
- **Agents dispatched:** None (single-agent execution)
- **Skills invoked:** update-documentation, diagram-architecture
- **Artifacts produced:** {comma-separated list of all files created or updated}
- **Outcome:** {N} ADRs written, {N} architecture docs updated, {N} service docs updated,
  {N} cross-cutting docs updated. Design reconciliation {complete / not needed}.
  {1-sentence summary}.
- **Findings:** {any gaps identified, documentation debt noted, or "Documentation complete.
  Epic ready for closure."}
```

---

## Decision Tree

```
/update-documentation invoked
    │
    ▼
Resolve feature directory (refs/feature-resolution.md)
    │
    ▼
release.md exists?
    │
    ├── No → Block: "Run /qa-review first"
    │
    └── Yes → Assessment is PASS or PASS WITH NOTES?
                │
                ├── Yes → Proceed
                │
                └── FAIL → Ask: proceed anyway or go back?
    │
    ▼
Gather feature context (Step 3)
    ├── Read design artifacts: README, prd, hld, lld
    ├── Read delivery artifacts: tasks-breakdown, release, sdlc-log
    └── Extract: decisions, changes, deviations, code footprint
    │
    ▼
Identify code changes and build Impact Map (Step 4)
    │
    ▼
Inventory existing documentation (Step 5)
    │
    ▼
Present documentation plan to user (Step 6)
    │
    ├── User approves → Proceed
    ├── User modifies → Update plan → Re-present
    └── User rejects → END
    │
    ▼
Execute documentation updates (Steps 7-11)
    ├── Step 7:  Write ADRs
    ├── Step 8:  Update architecture docs
    ├── Step 9:  Update service docs
    ├── Step 10: Update cross-cutting docs
    └── Step 11: Design reconciliation
    │
    ▼
Present summary and confirm (Step 12)
    │
    ▼
Write SDLC log entry (Step 13)
    │
    ▼
END — Epic ready for closure
```

---

## Determining What Needs Documentation

Not every feature change requires documentation in every area. Use these heuristics:

### ADRs — When to Write

| Signal | ADR Needed? |
|--------|-------------|
| New technology or library adopted | Yes |
| Architecture pattern chosen (with alternatives rejected) | Yes |
| Data model decision with trade-offs | Yes |
| Security or auth model change | Yes |
| Decision to NOT do something (deliberate rejection) | Yes |
| Standard implementation following existing patterns | No |
| Bug fix or minor enhancement within existing boundaries | No |
| Deviation classified as "Improvement" in release.md | Maybe (if it establishes a new pattern) |

### Architecture Docs — When to Update

| Signal | Update Needed? |
|--------|---------------|
| New service or bounded context | Yes — component-boundaries.md, system-overview.md |
| New integration path between services | Yes — integration-patterns.md |
| New infrastructure component | Yes — infrastructure.md |
| New technology in the stack | Yes — technology-stack.md |
| Changes within existing service boundaries | No |
| Performance optimization that doesn't change boundaries | No |

### Service Docs — When to Update

| Signal | Update Needed? |
|--------|---------------|
| New API endpoints or contract changes | Yes — api/ docs |
| New or changed data models | Yes — data-model/ docs |
| New SLI/SLO definitions | Yes — sli-slo/ docs |
| Infrastructure changes for the service | Yes — infrastructure/ docs |
| Internal refactoring with same external behavior | No |

### Cross-Cutting — When to Update

| Signal | Update Needed? |
|--------|---------------|
| New metrics, dashboards, or alert definitions | Yes — o11y/ |
| CI/CD pipeline changes | Yes — cicd/ |
| Security model changes | Yes — security/ |
| Auth flow or permission changes | Yes — authn-authz/ |
| New shared library or breaking change to existing | Yes — reference in relevant area |

---

## Scaling Guidance

### Small features (1-5 tasks, single service)

- Typically 0-1 ADRs
- Architecture docs rarely need updating (within existing boundaries)
- 1 service doc may need updating
- Cross-cutting updates unlikely
- Focus on design reconciliation

### Medium features (5-10 tasks, 2-3 services)

- Typically 1-3 ADRs
- Architecture docs may need updating if new integration patterns
- 2-3 service docs may need updating
- Cross-cutting updates possible (especially o11y)
- Full documentation pass needed

### Large features (10+ tasks, new bounded contexts)

- Typically 3-5+ ADRs
- Architecture docs almost certainly need updating
- Multiple service docs need creating or updating
- Cross-cutting updates likely across multiple areas
- Comprehensive documentation effort — consider breaking into sub-steps

---

## Diagram Generation Guide

Every documentation area that describes boundaries, flows, or topology benefits from a visual.
When generating diagrams, **invoke `/diagram-architecture`** — it enforces the project's diagram
quality standards (labeled edges, semantic colors, size limits, accessibility attributes).

The table below maps each documentation area to the diagram types that communicate most
effectively. Use it when building the "Diagrams to Generate" section of the documentation plan
(Step 6) and when writing each documentation area (Steps 8-10).

### Architecture Docs → Diagram Types

| Architecture Document | Primary Diagram | Secondary Diagram | What to Show |
|-----------------------|----------------|-------------------|-------------|
| `system-overview.md` | C4 Context (`C4Context`) or Flowchart (`flowchart LR`) | — | System landscape: external actors, system boundary, major components. Keep to 5-8 elements. |
| `component-boundaries.md` | C4 Container (`C4Container`) or Flowchart with subgraphs | — | Service boundaries, bounded contexts, ownership areas. Subgraphs per domain. |
| `integration-patterns.md` | Sequence Diagram (`sequenceDiagram`) | C4 Dynamic (`C4Dynamic`) | Runtime request/event flows between services. One diagram per key integration path. |
| `infrastructure.md` | C4 Deployment (`C4Deployment`) or Architecture (`architecture-beta`) | Flowchart (`flowchart LR`) | Deployment topology: databases, caches, queues, cloud resources, and how services connect to them. |
| `technology-stack.md` | — | — | Rarely needs diagrams. Consider a Quadrant chart only if comparing technology alternatives. |

### Service Docs → Diagram Types

| Service Document | Primary Diagram | What to Show |
|-----------------|----------------|-------------|
| API docs (`api/`) | Sequence Diagram (`sequenceDiagram`) | Key API request flows — show the happy path through routes → flows → ports → adapters. Limit to 6-8 participants. |
| Data model (`data-model/`) | ER Diagram (`erDiagram`) | Entity relationships, aggregate boundaries, cardinality. Split by bounded context if > 8-12 entities. |
| Infrastructure (`infrastructure/`) | Flowchart (`flowchart LR`) | Service's infrastructure dependencies — databases, caches, queues, external services it calls. |

### Cross-Cutting Docs → Diagram Types

| Cross-Cutting Area | Primary Diagram | What to Show |
|-------------------|----------------|-------------|
| Observability (`o11y/`) | Flowchart (`flowchart LR`) | Telemetry pipeline: service → OTel Collector → backends (Tempo, Loki, Prometheus → Grafana). |
| Auth (`authn-authz/`) | Sequence Diagram (`sequenceDiagram`) | Auth flows: token issuance, validation, refresh. One diagram per flow (e.g., login, API auth, service-to-service). |
| Security (`security/`) | Flowchart (`flowchart TB`) | Threat model or security boundary diagram showing trust zones. |
| CI/CD (`cicd/`) | Flowchart (`flowchart LR`) | Pipeline stages: commit → lint → test → build → deploy. |

### Diagram Quality Checklist (from `/diagram-architecture`)

When invoking `/diagram-architecture`, it applies these quality standards automatically. If you
generate a diagram outside the skill for any reason, verify these manually:

- **Title**: Every diagram has a descriptive title
- **Labeled edges**: No unlabeled arrows — include intent and/or protocol
- **Semantic IDs**: `orderSvc`, `paymentDB` — never `A`, `B`, `C`
- **Semantic colors**: Use `classDef` with the project palette (service=blue, database=teal,
  external=gray, queue=orange, user=green, critical=red)
- **Size limits**: Flowcharts ≤ 15-20 nodes, sequences ≤ 6-8 participants, ER ≤ 8-12 entities
- **Accessibility**: Include `accTitle` and `accDescr` for SVG rendering
- **Single concern**: One diagram answers one architectural question

### When NOT to Generate Diagrams

Not every documentation update needs diagrams. Skip diagram generation when:

- The documentation area describes **internal implementation** only (no boundaries or flows)
- The change is a **text-only update** (e.g., updating SLI/SLO thresholds, adding deployment notes)
- An existing diagram in the document **already accurately reflects** the as-built state — don't
  regenerate diagrams that haven't changed
- The feature is a **bug fix or minor enhancement** within existing boundaries

---

## Patterns

### Do

- Read existing documentation before writing — understand the current state before adding to it
- Use the `release.md` as your source of truth for what was actually built
- Document the **as-built** system, not the as-designed intent
- Write ADRs for decisions that would not be obvious from reading the code alone
- Reference the feature design directory (`docs/designs/YYYY/NNN-{feature}/`) for detailed context
- Invoke `/diagram-architecture` for every diagram — it ensures consistent styling, correct
  diagram types, labeled edges, semantic colors, and accessibility attributes
- Include diagrams in every documentation area that describes boundaries, flows, or topology
- Keep architecture docs at the system level — detailed component internals belong in service docs
- Fill the **Constraints & Boundaries** section of ADRs carefully for AI assistant consumption
- Present the documentation plan before writing — the developer knows context you don't
- Create directories that don't exist yet when needed (`docs/services/{name}/api/`, etc.)

### Don't

- Modify design artifacts (`README.md`, `prd.md`, `hld.md`, `lld.md`, `tasks-breakdown.md`) —
  they are immutable historical records
- Write documentation for unrelated parts of the system — only document what this feature changed
- Copy the HLD/LLD diagrams into architecture docs — create diagrams reflecting the as-built state
- Write ad-hoc Mermaid diagrams without invoking `/diagram-architecture` — it enforces quality
  standards (labeled edges, semantic colors, size limits, accessibility)
- Write ADRs for routine implementation choices that follow existing patterns
- Skip the documentation plan presentation — the developer may have additional context
- Leave empty placeholder sections — if a section doesn't apply, omit it rather than writing "N/A"
- Duplicate information already captured in release.md — reference it instead
- Reorganize existing documentation structure — add to it, preserve what others wrote

---

## Quality Gates

Before completing:

- [ ] Every significant decision from design and implementation has an ADR
- [ ] ADR Constraints & Boundaries sections are filled for AI assistant consumption
- [ ] Architecture docs reflect the as-built system (not as-designed)
- [ ] All affected services have updated or created documentation
- [ ] Cross-cutting changes are captured in the appropriate concern areas
- [ ] Design-vs-reality divergences are noted (reconciliation complete)
- [ ] No design artifacts were modified (README, prd, hld, lld are immutable)
- [ ] Documentation plan was presented to and approved by the developer
- [ ] Every doc describing boundaries, flows, or topology includes at least one diagram
- [ ] All diagrams were generated via `/diagram-architecture` (consistent styling, labeled edges,
      semantic colors, `accTitle`/`accDescr` for accessibility, element count within limits)
- [ ] All documentation references the feature design directory for detailed context
- [ ] Summary of all artifacts written was presented to the developer
- [ ] SDLC log entry has been appended
