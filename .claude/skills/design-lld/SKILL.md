---
name: design-lld
description: |
  Orchestrate the Low-Level Design (LLD) phase — discover and dispatch domain-specific architect
  agents and design skills in parallel to produce a comprehensive lld.md. Coordinates API, data,
  event, frontend, infrastructure, and code design dimensions with cross-dimensional alignment
  checks and multi-wave execution. Requires hld.md from /design-system as architectural foundation.
  Use when entering LLD phase, running /design-lld, or when the user says "low-level design", "LLD",
  "detailed design", "design the domains", "design the contracts", "API design", "data model design",
  "design the components", "domain design", or "detail the architecture". This skill requires both
  prd.md and hld.md — it will block if either doesn't exist yet.
---

# /design-lld — Low-Level Design Orchestrator

> Discover domain-specific design skills and architect agents, coordinate them in parallel waves, and produce a unified lld.md grounded in the HLD's architectural decisions.

## Quick Reference

| Aspect | Details |
|--------|---------|
| **Phase** | Design — Low-Level (LLD) |
| **Gate In** | `prd.md` AND `hld.md` must exist (run `/discover-feature` → `/discover-requirements` → `/design-system` first if missing) |
| **Produces** | `lld.md` — domain-specific contracts and designs aligned to HLD |
| **Shared Refs** | `sdlc-shared/refs/feature-resolution.md`, `sdlc-shared/refs/phase-gating.md`, `sdlc-shared/refs/agent-discovery.md`, `sdlc-shared/refs/propose-approve-execute.md`, `sdlc-shared/refs/sdlc-log-format.md` |
| **Previous Phase** | `/design-system` (HLD) |
| **Next Phase** | `/tasks-breakdown` (after `lld.md` exists) |

---

## How LLD Relates to HLD

LLD operates **within** the architectural boundaries established by the HLD. Every LLD design decision must trace back to an HLD decision:

- **Bounded contexts** from HLD define *which* domains get designed — each LLD agent works within a specific context
- **Integration patterns** from HLD dictate *how* domains connect — LLD agents use the specified sync/async mechanisms, not their own
- **Technology choices** from HLD constrain *what tools* LLD agents design for — database type, messaging system, cache strategy
- **Cross-cutting concerns** from HLD provide *shared strategies* — auth, observability, resilience patterns that all domains honor

LLD agents that deviate from HLD boundaries must document the deviation and justification. Unexplained deviations are design defects.

---

## Core Workflow

### Step 1: Resolve Feature Directory

Follow the algorithm in [sdlc-shared/refs/feature-resolution.md](../sdlc-shared/refs/feature-resolution.md):

1. If the user passed an argument (e.g., `/design-lld 001-feature-name`) — resolve to the matching feature directory under `docs/designs/*/`
2. If no argument — scan `docs/designs/` across all years, present a selection list of existing features
3. If argument doesn't match — report the error and present the selection list

The resolved path becomes `{feature-dir}` for all subsequent steps.

### Step 2: Phase Gate — Require prd.md AND hld.md

Follow [sdlc-shared/refs/phase-gating.md](../sdlc-shared/refs/phase-gating.md):

```
Check: {feature-dir}/prd.md exists and is non-empty?
  ├── No  → Block: "No requirements found. Run /discover-feature then /discover-requirements first to produce prd.md." → END
  └── Yes → Check: {feature-dir}/hld.md exists and is non-empty?
              ├── No  → Block: "No high-level design found. Run /design-system first to produce hld.md." → END
              └── Yes → Proceed to Step 3
```

Both gates must pass. LLD without HLD produces isolated, potentially contradictory designs.

### Step 3: Detect Current State

```
{feature-dir} resolved, prd.md + hld.md exist
    │
    ├── lld.md does NOT exist?
    │       └── Enter FULL LLD (Step 4)
    │
    └── lld.md exists?
            └── Design COMPLETE (Step 9)
```

### Step 4: Read HLD Context and Extract Architectural Constraints

Before building proposals, thoroughly read the feature's artifacts:

1. Read `{feature-dir}/hld.md` — **this is the primary input**. Extract:
   - Bounded contexts (names, responsibilities, boundaries)
   - Integration patterns per boundary (sync/async, protocol, contract ownership)
   - Technology choices per context (database, messaging, cache)
   - Cross-cutting strategies (auth, observability, resilience)
   - Data ownership per context
2. Read `{feature-dir}/prd.md` — requirements, acceptance criteria, domain vocabulary
3. Read `{feature-dir}/README.md` — vision, goals, rationale (if exists)

Use this context to:
- Determine which LLD dimensions are needed (not every feature needs all dimensions)
- Craft specific, actionable descriptions in the proposal tables
- Identify dependencies between LLD dimensions (e.g., data model informs API contract)

#### 4a: Map Bounded Contexts to Service & Domain Structure

This sub-step is **mandatory**. Translate each HLD bounded context into the project's concrete ports-and-adapters layout. This mapping becomes the "Section 0" of `lld.md` and guides every subsequent agent.

For each bounded context from hld.md, determine:

1. **Service** — Which `services/<name>/` does this context live in? Is it a new service or an existing one? Scan `services/` to check.
2. **Domains** — Which `domains/<domain>/` within that service does this context map to? A bounded context may span multiple domains or map 1:1.
3. **Modules** — For each domain, which modules are needed? Map to the standard ports-and-adapters structure:

```
services/<service-name>/<service_name>/domains/<domain>/
├── routes/v1/          # Inbound HTTP — thin transport, no business logic
├── handlers/v1/        # Inbound event/message/stream adapters
├── jobs/               # Batch/scheduled/long-running adapters
├── flows/              # Application layer — orchestrates use cases
├── ports/              # Protocols/ABCs — what domain needs from outside
├── adapters/           # Implementations of ports — repos, clients, publishers
├── exceptions.py       # Domain-specific errors
├── models/
│   ├── domain/         # Entities, value objects, aggregates
│   ├── contracts/
│   │   ├── api/        # Pydantic request/response models
│   │   └── events/     # Pydantic event payloads
│   └── persistence/    # ORM/ODM mappings
```

4. **Shared libraries** — Which `libs/lib-*` are consumed? Which shared schemas in `libs/lib-schemas/` need new types?
5. **New vs existing** — Mark each service/domain/module as `[new]` or `[existing]`.

Apply the `design-code` structural design principles (Phase 4 — `refs/modularity.md`, `refs/coherence.md`):
- Align module boundaries with domain concepts, not technical layers
- Mirror existing module structures when creating new ones
- Keep modules cohesive (single reason to change)
- Define explicit contracts (protocols, DTOs, events) at module boundaries

**Output:** A structured service/domain/module map table that becomes Section 0 of lld.md.

### Step 5: Discover LLD Skills and Architect Agents

This step discovers both **skills** (best-practice guides loaded inline) and **agents** (parallel subprocesses that produce design artifacts).

- **Skills** — Loaded into context via the `Skill` tool. They provide design patterns, constraints, and domain-specific guidance. Skills run inline, not as separate processes.
- **Agents** — Dispatched via the `Agent` tool as parallel subprocesses. Each agent works independently on a design dimension and produces output for lld.md.

#### 5a: Discover LLD Skills

Scan `.claude/skills/` for all directories matching `design-*`. For each, read the `SKILL.md` frontmatter to extract name and description. Exclude `design-system` (HLD skill) and `design-lld` (this orchestrator).

| Skill | Domain | Purpose |
|-------|--------|---------|
| `design-code` | Code | Systematic design thinking, domain modeling, architectural patterns |
| `design-api` | API | REST API contracts, OpenAPI specs, resource modeling, versioning |
| `design-data` | Data | Data models, schemas, access patterns, aggregate boundaries |
| `design-event` | Events | Event schemas, async flows, messaging topology, AsyncAPI specs |
| `design-web` | Frontend | React component architecture, state management, data flow |
| `design-kubernetes` | K8s | Kubernetes configs, Helm charts, ArgoCD, EKS architecture |
| `design-pulumi` | IaC | Pulumi infrastructure architecture, cloud resource design |

Future skills (e.g., `design-security/`, `design-ml-pipeline/`) will be automatically discovered when they appear in `.claude/skills/`.

#### 5b: Discover Architect Agents

Follow [sdlc-shared/refs/agent-discovery.md](../sdlc-shared/refs/agent-discovery.md):

1. Scan `.claude/agents/` for all `*-architect.md` files
2. Exclude `system-architect` (HLD agent — belongs to `/design-system`)
3. For each architect agent, parse filename and read description from frontmatter

| Agent | Domain | Purpose |
|-------|--------|---------|
| `api-architect` | API | REST API contracts, OpenAPI specs |
| `data-architect` | Data | Data models, persistence, access patterns |
| `event-architect` | Events | Event schemas, async flows, messaging topology |
| `python-architect` | Code | Python system architecture, DDD, clean boundaries |
| `web-architect` | Frontend | React component architecture, state management |
| `kubernetes-architect` | K8s | K8s configurations, Helm, ArgoCD |
| `pulumi-architect` | IaC | Pulumi infrastructure architecture |
| `mcp-architect` | MCP | MCP server design, tool/resource/prompt catalogs, lifespan, transport |

Future architect agents will be automatically discovered when they appear in `.claude/agents/`.

### Step 6: Build Execution Plan — Waves and Dependencies

Not all LLD dimensions are independent. Some agents produce outputs that other agents need. Organize agents into **execution waves** based on dependencies:

#### Wave Analysis

Analyze the HLD to determine inter-dimension dependencies:

```
Wave 1 (Foundation — no dependencies on other LLD outputs):
  ├── design-code / python-architect  — Domain model, aggregates, value objects
  ├── design-data / data-architect    — Data schemas, access patterns, persistence
  └── (these two often inform everything else)

Wave 2 (Contract — may depend on Wave 1 data model):
  ├── design-api / api-architect      — REST contracts referencing domain entities
  ├── design-event / event-architect  — Event schemas referencing domain events
  └── design-web / web-architect      — Component contracts consuming APIs

Wave 3 (Infrastructure — depends on all above):
  ├── design-kubernetes / kubernetes-architect — Deployment specs for designed services
  └── design-pulumi / pulumi-architect         — Cloud resources for designed data stores
```

The wave structure is a recommendation, not rigid. If the feature is simple enough that all dimensions are independent, propose a single wave. If dependencies exist, explain why certain agents should wait.

Present the execution plan to the user:

```markdown
## Execution Plan

Based on the HLD, I've identified the following LLD dimensions and execution waves:

### Wave 1 — Foundation (parallel)
These dimensions have no LLD-internal dependencies and establish the domain model.

| Agent | Skill | Task | Why This Wave |
|-------|-------|------|---------------|
| python-architect | design-code | {specific action from prd/hld} | Domain model needed by API and event design |
| data-architect | design-data | {specific action from prd/hld} | Schema needed by API responses and event payloads |

### Wave 2 — Contracts (parallel, after Wave 1)
These dimensions reference the domain model and data schemas from Wave 1.

| Agent | Skill | Task | Depends On |
|-------|-------|------|------------|
| api-architect | design-api | {specific action} | Wave 1: domain entities, data schemas |
| event-architect | design-event | {specific action} | Wave 1: domain events, data schemas |
| web-architect | design-web | {specific action} | Wave 1: domain model; Wave 2: API contracts |
```

#### If All Dimensions Are Independent

For simpler features where LLD dimensions don't depend on each other, skip the wave structure and dispatch all agents in a single parallel batch. Note this in the proposal:

```markdown
## Execution Plan — Single Wave

All LLD dimensions are independent for this feature. Dispatching all agents in parallel.
```

### Step 7: Propose Skills + Agent Team — Await Approval

Follow [sdlc-shared/refs/propose-approve-execute.md](../sdlc-shared/refs/propose-approve-execute.md):

Present **both** the skill selection table and the agent team in the execution plan format:

```markdown
## Proposed LLD Skills

Select which skills should guide this design. Selected skills will be loaded as best-practice context.

| # | Skill | Domain | Why Proposed | Select |
|---|-------|--------|--------------|--------|
| S1 | `design-code` | Code | Feature requires domain modeling | ✅ |
| S2 | `design-api` | API | prd.md mentions REST endpoints | ✅ |
| S3 | `design-data` | Data | prd.md mentions data persistence | ✅ |
| S4 | `design-event` | Events | HLD specifies async integration | ✅ |
| S5 | `design-web` | Frontend | prd.md mentions UI components | ⬜ |
| S6 | `design-kubernetes` | K8s | No K8s requirements detected | ⬜ |
| S7 | `design-pulumi` | IaC | No IaC requirements detected | ⬜ |

**Select skills by number** (e.g., "use S1-S4" or "all" or "remove S5-S7").

## Proposed Agent Team

{Execution plan from Step 6 with agent proposal tables}

**Approve, modify, or reject.** You can:
- Approve the plan as-is
- Remove agents/skills by number
- Change execution wave assignments
- Add custom agents or adjust task descriptions
- Choose skills-only mode (no agents — inline design)
```

Mark domain-matched skills as pre-selected (✅) based on prd.md and hld.md content. Include all discovered agents — let the user prune.

Never dispatch agents or invoke skills without explicit approval.

### Step 8: Execute Approved Plan

#### 8a: Invoke Approved Skills

Invoke approved LLD skills via the `Skill` tool to load domain-specific design patterns into context:

```markdown
## LLD Skills Loaded

- ✅ `design-code` — Domain modeling, aggregates, value objects, architectural patterns
- ✅ `design-api` — REST API contracts, OpenAPI specs, resource modeling
- ✅ `design-data` — Data models, schemas, aggregate boundaries, access patterns
- ✅ `design-event` — Event schemas, AsyncAPI specs, messaging topology
```

After loading each skill, briefly note the key constraints it provides (1-2 lines). Do not present the full skill content to the user.

#### 8b: Dispatch Wave 1 Agents

Dispatch all Wave 1 agents via the `Agent` tool in a **single message** for parallel execution.

Each agent receives a structured prompt:

```markdown
## Context

**Feature:** {feature-name}
**Feature Directory:** {feature-dir-path}
**Phase:** Design — Low-Level Architecture
**Wave:** 1 (Foundation)

## Your Assignment

{Approved task-specific action from the proposal table}

## Design Skills to Follow

The following skills have been approved for this phase. Invoke each relevant skill via the `Skill` tool before writing design artifacts, and follow their patterns:

{List each approved LLD skill relevant to this agent's domain, e.g.:}
- `design-code` — Follow for domain modeling, aggregate design, value objects
- `design-data` — Follow for data model design, schema patterns, access pattern enumeration

Only invoke skills relevant to YOUR domain.

## Artifacts to Read (in this order)

1. `{feature-dir}/hld.md` — **Read this first.** Defines bounded contexts, service boundaries, integration patterns, technology decisions. Your domain design must align with these.
2. `{feature-dir}/prd.md` — Requirements with acceptance criteria
3. `{feature-dir}/README.md` — Feature inception document (if exists)

## Architectural Constraints from HLD

Your design operates within the boundaries established by the high-level design:

- **Bounded contexts:** Design within the context boundaries defined in hld.md. Do not introduce new service boundaries.
- **Integration patterns:** Use the integration mechanisms specified in hld.md. Do not invent alternatives.
- **Technology choices:** Align with the technology stack in hld.md. Document any necessary deviations.
- **Cross-cutting concerns:** Honor auth, observability, and resilience strategies from hld.md.

## Service & Domain Structure

Map your design to the project's concrete ports-and-adapters layout. For each component you design, specify where it lives:

```
services/<service-name>/<service_name>/domains/<domain>/
├── routes/v1/          # Inbound HTTP — thin transport, no business logic
├── handlers/v1/        # Inbound event/message/stream adapters
├── jobs/               # Batch/scheduled/long-running adapters
├── flows/              # Application layer — orchestrates use cases
├── ports/              # Protocols/ABCs — what domain needs from outside
├── adapters/           # Implementations of ports — repos, clients, publishers
├── exceptions.py       # Domain-specific errors
├── models/
│   ├── domain/         # Entities, value objects, aggregates
│   ├── contracts/
│   │   ├── api/        # Pydantic request/response models
│   │   └── events/     # Pydantic event payloads
│   └── persistence/    # ORM/ODM mappings
```

Include a table mapping each designed component to its target path, marking `[new]` or `[existing]`.

## Artifacts to Produce

- Write your output to `{feature-dir}/lld-{your-domain}.md` (e.g., `lld-api.md`, `lld-data.md`)

## Design Constraints

- Follow contracts-first: OpenAPI specs, AsyncAPI specs, and data models before implementation code
- Reference engineering principles from `.claude/rules/principles.md`
- Follow `design-code` structural design principles: align module boundaries with domain concepts, mirror existing module structures, keep modules cohesive

## Definition of Done

- Domain-specific contracts are fully specified
- Design decisions are justified with rationale
- Design is traceable to HLD — every component maps to a bounded context from hld.md
- Integration points use the patterns specified in hld.md
- **Structural mapping is complete** — every designed component has a concrete service/domain/module path
- The design is implementable — an implementer agent can produce code from this spec
```

Wait for all Wave 1 agents to complete.

#### 8c: Wave 1 Results — Feed Forward

After Wave 1 completes:

1. Read the outputs from Wave 1 agents
2. Present a brief summary of Wave 1 outcomes to the user
3. Extract key artifacts that Wave 2 agents need (domain entities, data schemas, etc.)
4. Include these as additional context in Wave 2 agent prompts

#### 8d: Dispatch Wave 2+ Agents

Dispatch Wave 2 agents with the same structured prompt format, plus:

```markdown
## Upstream LLD Context (from previous waves)

The following LLD artifacts have already been produced. Your design should reference and align with them:

{List Wave 1 output files with brief summaries, e.g.:}
- `{feature-dir}/lld-code.md` — Domain model: {key entities and aggregates}
- `{feature-dir}/lld-data.md` — Data schemas: {key tables and access patterns}

Read these files to ensure your contracts reference the correct entity names, field types, and relationships.
```

Repeat for each subsequent wave.

If >6 agents are approved in a single wave, batch into groups of 6 per [sdlc-shared/refs/propose-approve-execute.md](../sdlc-shared/refs/propose-approve-execute.md).

#### 8e: Cross-Dimensional Alignment Check

After all waves complete, perform a coherence check across all LLD outputs:

1. Read all `lld-*.md` files produced by agents
2. Check for contradictions:
   - Do API request/response schemas match the data model's entity definitions?
   - Do event payloads use the same field names and types as the domain model?
   - Do frontend components consume the API contracts that were designed?
   - Are aggregate boundaries consistent between code design and data design?
   - Do integration patterns match what HLD specified?
   - **Structural coherence:** Do all agents agree on service/domain/module paths? Are there conflicts where two agents place different components in the same module, or the same component in different locations?
   - **Module boundary consistency:** Do port/adapter interfaces match across domains? If domain A defines a port that domain B implements, do both sides use the same protocol?
3. Present findings to the user:

```markdown
## Cross-Dimensional Alignment Report

### Aligned
- API entities match data model ✅
- Event schemas use domain vocabulary ✅

### Misalignments Found
- ⚠️ `lld-api.md` uses `customer_id` but `lld-data.md` uses `client_id` — reconcile naming
- ⚠️ `lld-event.md` publishes `OrderPlaced` but no consumer is defined in `lld-api.md`

### Recommendations
- {specific fix suggestions}
```

If misalignments are found, offer to re-dispatch specific agents with updated context.

#### 8f: Consolidate into lld.md

After alignment is verified (or user accepts current state), consolidate all `lld-*.md` files into a unified `{feature-dir}/lld.md`:

```markdown
# Low-Level Design: {Feature Name}

## 0. Service & Domain Architecture

This section maps the feature to the project's concrete service/domain/module structure.
It is the structural blueprint that all subsequent sections reference.

### Services Involved

| Service | Status | HLD Bounded Context | Purpose |
|---------|--------|---------------------|---------|
| `services/<name>/` | [new] / [existing] | {context from hld.md} | {responsibility} |

### Domain & Module Map

For each service, list the domains and modules this feature touches:

| Service | Domain | Module | Status | Responsibility |
|---------|--------|--------|--------|----------------|
| `<service>` | `<domain>` | `routes/v1/` | [new] | {e.g., POST /api/v1/notifications} |
| `<service>` | `<domain>` | `flows/` | [new] | {e.g., SendNotificationFlow} |
| `<service>` | `<domain>` | `ports/` | [new] | {e.g., NotificationSender protocol} |
| `<service>` | `<domain>` | `adapters/` | [new] | {e.g., SESNotificationSender} |
| `<service>` | `<domain>` | `models/domain/` | [new] | {e.g., Notification entity} |
| `<service>` | `<domain>` | `models/contracts/api/` | [new] | {e.g., NotificationResponse} |
| `<service>` | `<domain>` | `models/contracts/events/` | [new] | {e.g., NotificationSent payload} |
| `<service>` | `<domain>` | `models/persistence/` | [new] | {e.g., NotificationRecord} |

### Shared Libraries

| Library | Usage | New Types |
|---------|-------|-----------|
| `libs/lib-schemas/` | {shared domain types, enums, event envelopes} | {list new types if any} |
| `libs/lib-events/` | {event registry, publisher} | — |

### Filesystem Layout (Tree View)

{Concrete directory tree showing where new files will be created,
following the ports-and-adapters structure from CLAUDE.md}

## 1. Domain Model
{From lld-code.md}

## 2. Data Architecture
{From lld-data.md}

## 3. API Contracts
{From lld-api.md}

## 4. Event Architecture
{From lld-event.md}

## 5. Frontend Architecture
{From lld-web.md — if applicable}

## 6. Infrastructure
{From lld-kubernetes.md, lld-pulumi.md — if applicable}

## 7. Cross-Dimensional Alignment
{Summary of how dimensions connect, any resolved misalignments}

## 8. Design Traceability
{How each LLD section traces back to HLD bounded contexts and decisions}
```

Remove the individual `lld-*.md` files after successful consolidation (they're now part of the unified document).

#### Skills-Only Mode (No Agents)

If the user approved skills but no agents, Claude Code produces lld.md **inline** using the loaded skills as guidance:

1. Follow the approved skills' patterns and constraints directly
2. Write `{feature-dir}/lld.md` in the main session (no subprocesses)
3. Still follow the wave structure mentally — design domain model first, then contracts, then infrastructure
4. This is appropriate for smaller features or when the user prefers direct control

### Step 8g: Present Execution Summary

```markdown
## LLD — Execution Summary

### Skills Used
| Skill | Purpose |
|-------|---------|
| `design-code` | Domain modeling, architectural patterns |
| `design-api` | REST API contracts, OpenAPI specs |
| `design-data` | Data models, schemas, access patterns |
| `design-event` | Event schemas, AsyncAPI specs |

### Agent Results
| Wave | Agent | Status | Key Outcomes |
|------|-------|--------|--------------|
| 1 | python-architect | ✅ Complete | {summary} |
| 1 | data-architect | ✅ Complete | {summary} |
| 2 | api-architect | ✅ Complete | {summary} |
| 2 | event-architect | ✅ Complete | {summary} |

### Alignment
- Cross-dimensional check: {passed / N misalignments resolved}

### Artifacts
- `{feature-dir}/lld.md` — Unified low-level design

**Next step:** Run `/tasks-breakdown {feature-identifier}` to decompose the design into implementable tasks.
```

If skills-only mode was used:

```markdown
### Inline Design
- **Mode:** Skills-only (no agents dispatched)
- **Artifacts Produced:** lld.md
- **Key Outcomes:** {summary of what was designed}
```

If any agent failed, report the failure and ask the user whether to retry, skip, or adjust and re-dispatch.

### Step 9: Design Complete (lld.md exists)

```markdown
## LLD Complete

Low-level design already exists for this feature:
- `{feature-dir}/lld.md` ✅

**Next step:** Run `/tasks-breakdown {feature-identifier}` to decompose the design into implementable tasks.

If you want to re-run LLD (e.g., after HLD changes or requirement updates), let me know and I'll propose the LLD skills and architect agent team again.
```

If the user wants to re-run, proceed to Step 4.

### Step 10: Write SDLC Log Entry

After execution completes, append an entry to `{feature-dir}/sdlc-log.md` following [sdlc-shared/refs/sdlc-log-format.md](../sdlc-shared/refs/sdlc-log-format.md):

```markdown
## [YYYY-MM-DD HH:MM] — /design-lld — Low-Level Design

- **Task:** N/A
- **Agents dispatched:** {list of agents by wave, or "None (skills-only mode)" or "None (LLD already complete)"}
- **Skills invoked:** {skills used — e.g., "design-code, design-api, design-data, design-event"}
- **Artifacts produced:** {files created — e.g., "lld.md"}
- **Waves executed:** {e.g., "2 waves (foundation → contracts)"}
- **Alignment check:** {passed / N misalignments found and resolved}
- **Outcome:** {what was accomplished}
- **Findings:** {any issues, warnings, or notes — or "None"}
```

If `sdlc-log.md` doesn't exist, create it with the header first (see the shared ref for the header format).

---

## Decision Tree (Full)

```
/design-lld invoked
    |
    v
Resolve Feature Directory (refs/feature-resolution.md)
    |
    v
Phase Gate: prd.md exists?
    |
    |-- No -> Block: "Run /discover-feature then /discover-requirements first." -> END
    |
    v
Phase Gate: hld.md exists?
    |
    |-- No -> Block: "Run /design-system first." -> END
    |
    v
Detect Current State: lld.md exists?
    |
    |-- Yes -> "LLD complete. Run /tasks-breakdown next." Offer re-run.
    |
    v
Read HLD + prd.md + README.md for context
    |
    v
Extract architectural constraints from hld.md
    |
    v
Discover design-* skills + *-architect.md agents (exclude system-level)
    |
    v
Analyze inter-dimension dependencies -> assign execution waves
    |
    v
Build skill selection table + agent team with wave structure
    |
    v
Present proposal -> await user approval
    |
    |-- Approved (skills + agents) -> invoke skills, dispatch by wave
    |-- Approved (skills only)     -> invoke skills, design inline
    |-- Modified                   -> update proposals, re-present
    +-- Rejected                   -> END
    |
    v
Invoke approved LLD skills
    |
    v
Wave 1: Dispatch foundation agents (parallel)
    |
    v
Wave 1 complete -> summarize, extract context for Wave 2
    |
    v
Wave 2: Dispatch contract agents (parallel, with Wave 1 context)
    |
    v
(Repeat for additional waves)
    |
    v
Cross-Dimensional Alignment Check
    |
    |-- Misalignments found -> present to user, offer re-dispatch
    |-- Aligned             -> proceed
    |
    v
Consolidate lld-*.md files into unified lld.md
    |
    v
Present execution summary
    |
    v
Append SDLC Log Entry (refs/sdlc-log-format.md)
    |
    v
END — "Run /tasks-breakdown next."
```

---

## Patterns

### Do

- Discover skills and agents dynamically — new additions are automatically proposed
- Read hld.md thoroughly before proposing agents — tailor each agent's task to the specific bounded contexts and patterns
- Organize agents into execution waves when dependencies exist — foundation before contracts before infrastructure
- Feed Wave N outputs into Wave N+1 prompts — agents in later waves should reference earlier designs
- Run cross-dimensional alignment checks — catch contradictions before they reach implementation
- Consolidate into a unified lld.md — implementers need one document, not scattered fragments
- Include all discovered agents in the proposal — let the user prune
- Support skills-only mode for simpler features
- Require every LLD agent to read hld.md first and trace decisions back to it

### Don't

- Skip the phase gates — without prd.md there's no "what", without hld.md there's no "within what boundaries"
- Dispatch agents without user approval — the propose-approve-execute pattern is non-negotiable
- Hardcode the skill or agent list — always scan dynamically
- Include `design-system` or `system-architect` in LLD proposals — HLD is a separate phase
- Dispatch all agents in parallel when dependencies exist — data model should inform API contracts
- Skip the alignment check — contradictions between LLD dimensions are the most common design defect
- Leave individual `lld-*.md` files without consolidation — the unified lld.md is the deliverable
- Invoke skills the user explicitly removed — respect user choices
- Write requirements (prd.md) or HLD (hld.md) — those are other skills' responsibilities
- Write task breakdowns — that's `/tasks-breakdown`'s job
