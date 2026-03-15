---
name: design-system
version: 2.1.0
description: |
  Own the High-Level Design (HLD) phase — architect system designs with bounded contexts, quality
  attributes, and technology selection. This is the single source of truth for HLD creation. Produces
  `hld.md` which gates all downstream Low-Level Design (LLD) work. Use when starting new features,
  designing new systems, planning major changes, architecting domains, or when user mentions
  "architecture", "system design", "HLD", "high-level", or "how should we build". Relevant for
  greenfield projects, system evolution, domain modeling, microservices, distributed systems.
  Activates in plan mode. Requires `prd.md` from the discovery phase.
---

# System Design (High-Level Architecture)

> Define the architectural skeleton before any detail design begins. Answer "what are the major components and how do they interact?" — not "how is each component built internally?"

## Quick Reference

| Aspect | Details |
|--------|---------|
| **Phase** | Design — High-Level (HLD) |
| **Gate In** | `prd.md` must exist (run `/discover` first if missing) |
| **Produces** | `hld.md` — architecture blueprint that gates all LLD work |
| **Outputs** | Mermaid architecture diagrams (context, component, ER, sequence), ADRs, Technology Selection Matrix, Risk Register |
| **Invokes** | `diagram-architecture` (Mermaid diagrams), `design-code` (domain modeling), downstream LLD skills via chaining |
| **Next Phase** | `/design-lld` (low-level design, grounded in this HLD) |
| **Shared Refs** | `sdlc-shared/refs/feature-resolution.md`, `sdlc-shared/refs/phase-gating.md` |

---

## Why HLD Runs First

The design phase has a strict ordering: **HLD must be produced before LLD begins**. This is an architectural dependency, not a preference:

- **HLD defines the skeleton** — bounded contexts, service boundaries, integration patterns, technology choices, and cross-cutting concerns. These are system-level decisions that constrain all downstream design.
- **LLD fills in the details** — API contracts, data schemas, event flows, and component internals. Each LLD dimension operates within the boundaries established by the HLD. Without those boundaries, LLD work happens in isolation and produces contradictory or misaligned designs.

Think of it as building a house: HLD is the structural blueprint (foundation, load-bearing walls, plumbing runs). LLD is the room-by-room detail (fixtures, finishes, wiring). You don't wire a room before you know where the walls go.

**Consequence:** The `/design-lld` orchestrator requires `hld.md` as input. Every LLD architect must trace their design decisions back to bounded contexts and integration patterns defined here.

---

## SDLC Lifecycle Integration

When invoked as part of the SDLC feature delivery flow:

### Resolve Feature Directory

Follow [sdlc-shared/refs/feature-resolution.md](../sdlc-shared/refs/feature-resolution.md):
1. If argument provided (e.g., `/design-system 001-feature-name`) — resolve to matching feature directory under `docs/designs/*/`
2. If no argument — scan `docs/designs/` across all years, present selection list
3. Resolved path becomes `{feature-dir}` for all subsequent steps

### Phase Gate — Require prd.md

Follow [sdlc-shared/refs/phase-gating.md](../sdlc-shared/refs/phase-gating.md):
- Check: `{feature-dir}/prd.md` exists and is non-empty
- If yes: proceed to Core Workflow
- If no: block with "No requirements found. Run `/discover` first to produce prd.md."

### State Detection

- `{feature-dir}/hld.md` already exists? → Offer re-run or proceed to `/design-lld`
- No `hld.md`? → Execute Core Workflow below

### Output Target

Write the HLD to `{feature-dir}/hld.md` using the Output Template below.

---

## Core Workflow

### Phase 1: Context Discovery

1. **Clarify Business Context**: What problem? Who are users? Business-critical capabilities? Success metrics?
2. **Gather Constraints**: Budget, timeline, team size/expertise, existing stack, regulatory requirements
3. **Examine Existing System**: `Glob: **/README.md, **/docs/architecture/**` | `Grep: "service", "module" in src/`

### Phase 2: Requirements Analysis

4. **Functional Requirements**: Core use cases, data I/O, integration points, batch vs. real-time needs

5. **Quality Attributes (NFRs)**:







   | Attribute | Question | Target |
   |-----------|----------|--------|
   | **Availability** | Uptime required? | 99.9%? 99.99%? |
   | **Scalability** | Expected load/growth? | Users, RPS, data volume |
   | **Latency** | Response time? | p50, p95, p99 targets |
   | **Durability** | Data loss tolerance? | RPO, RTO |
   | **Security** | Sensitivity/compliance? | PCI, HIPAA, SOC2 |
   | **Evolvability** | Change rate? | Weekly? Monthly? |

### Phase 3: Architecture Synthesis

6. **Select Architecture Style**
   ```
   Simple domain, single team ──────────────► Modular Monolith (DEFAULT)
   Multiple domains, independent scaling ───► Microservices
   High throughput, loose coupling ─────────► Event-Driven
   Read/write divergence ───────────────────► CQRS + Event Sourcing
   Mixed requirements ──────────────────────► Hybrid (start monolith, extract)
   ```
   See: [refs/architecture-styles.md](refs/architecture-styles.md)

7. **Identify Bounded Contexts**
   - Group by business capability, not technical function
   - Each context owns its ubiquitous language
   - Define context relationships (upstream/downstream, conformist, ACL)
   - One team should own one bounded context



8. **Classify Domains**: **Core** (build custom) | **Supporting** (build/buy) | **Generic** (OSS/buy)



### Phase 4: Technical Design





9. **Data Architecture** — See: [refs/technology-selection.md](refs/technology-selection.md)


   | Decision | Options | Criteria |

   |----------|---------|----------|
   | Storage | SQL / NoSQL / Hybrid | Access patterns, consistency |

   | Ownership | DB per service / Shared | Coupling tolerance, team structure |
   | Caching | Local / Distributed / CDN | Read patterns, staleness tolerance |


10. **Integration Patterns** — See: [refs/integration-patterns.md](refs/integration-patterns.md)

    | Pattern | When to Use |
    |---------|-------------|
    | Sync (REST/gRPC) | Queries, user-blocking operations |
    | Async (Events) | Cross-domain, eventual consistency OK |
    | Saga | Distributed transactions |
    | API Gateway | External client access |

11. **Resilience Strategy**: Circuit breakers, exponential backoff + jitter, bulkheads, fallbacks, DLQs
    See: [refs/resilience-patterns.md](refs/resilience-patterns.md)

12. **Security Boundaries**: AuthN (where/how?), AuthZ (RBAC/ABAC?), encryption (rest/transit), secrets management, network segmentation


### Phase 5: Validation & Documentation


13. **Validate Against Quality Attributes**: For each NFR, trace through design. How does this achieve availability? Where are scaling bottlenecks? Failure blast radius? See: [refs/quality-attributes.md](refs/quality-attributes.md)

14. **Produce Architecture Diagrams** — invoke `/diagram-architecture` for each:

    Generate Mermaid diagrams directly in `hld.md` using the `/diagram-architecture` skill's conventions
    (semantic node IDs, labeled edges with intent+protocol, `classDef` colors, size limits). Each diagram
    answers one architectural question — never cram multiple concerns into a single diagram.

    | HLD Section | Diagram Type | What It Shows | Mermaid Keyword |
    |-------------|-------------|---------------|-----------------|
    | §4 Bounded Contexts | C4 Context or Flowchart LR | System boundary, external actors, context relationships | `C4Context` / `flowchart LR` |
    | §5 Component Architecture | C4 Container or Flowchart LR | Services, databases, queues, and their connections | `C4Container` / `flowchart LR` |
    | §6 Data Architecture | ER Diagram | Entity relationships, ownership per context | `erDiagram` |
    | §7 Integration Architecture | Sequence Diagram | Key runtime flows across service boundaries | `sequenceDiagram` |

    **Required diagrams** (minimum set for every HLD):
    - [ ] **System Context Diagram** (§4) — the system as a box, external actors around it, labeled interactions
    - [ ] **Component/Container Diagram** (§5) — internal services, data stores, message buses with protocol labels

    **Situational diagrams** (produce when the HLD section warrants it):
    - [ ] **Data Model Diagram** (§6) — when multiple bounded contexts own distinct data, show ER per context
    - [ ] **Integration Sequence Diagram** (§7) — for the 1-2 most important cross-boundary flows
    - [ ] **State Diagram** (§8) — when entity lifecycles are central to resilience (e.g., order states, saga steps)
    - [ ] **Deployment Topology** — when infrastructure decisions are part of the HLD scope

    Follow `/diagram-architecture` conventions: `accTitle`/`accDescr` for accessibility, `%%` comments for
    architectural rationale, consistent `classDef` palette, ≤15 nodes per flowchart, ≤8 participants per sequence.

15. **Produce Written Artifacts**:

    - [ ] Architecture Decision Records (decisions + rationale)
    - [ ] Technology Selection Matrix (choices + justification)
    - [ ] Risk Register (risks + mitigations)




---



## Decision Framework


### Distribution Decision


| KEEP TOGETHER | DISTRIBUTE |

|---------------|------------|
| Single team | Independent scaling needs |
| Shared data model | Different release cadences |

| Strong consistency | Clear domain boundaries |

| Simple deployment | Team autonomy required |


### Technology Selection Principles

1. **Boring Technology**: roven over novel

2. **Team Expertise**: Weight toward known tech

3. **Operational Cost**: Consider maintenance burden
4. **Escape Hatches**: Avoid vendor lock-in

5. **Right Tool**: Match to access patterns


---


## Skill Chaining


### Invoke Downstream When

| Condition | Invoke | Handoff Context |

|-----------|--------|-----------------|
| Architecture diagrams needed in HLD | `diagram-architecture` | Diagram type, section context, audience, size limits |
| Component internals need design | `design/code` | Bounded context, quality attributes |

| REST/HTTP interfaces identified | `design/api` | Resource model, consumers, versioning |
| Async messaging required | `design/event` | Event types, producers, consumers |
| Data storage decisions needed | `design/data` | Access patterns, consistency, volume |
| Frontend components identified | `design/web` | User journeys, state requirements |


**Chaining Syntax**:

```
**Invoking:** `design/api` | **Context:** Payment bounded context requires REST API
**Handoff:** Resources: /payments, /refunds | Consumers: Mobile, Partner API | NFRs: <100ms p99
```


---


## Anti-Patterns & Principles

### ❌ Avoid

| Anti-Pattern | Why Bad | Instead |
|--------------|---------|---------|

| Distributed Monolith | Worst of both worlds | Clear boundaries OR true monolith |
| Shared Database | Hidden coupling | Database per bounded context |
| Sync Chain | Latency × availability ↓ | Async where possible |

| Big Bang Rewrite | High risk | Strangler fig pattern |
| Resume-Driven Design | Unnecessary complexity | Boring technology |

### ✅ Apply

- **API/Event-First**: Contracts before implementation
- **Async-First**: Default async across boundaries
- **Stateless Services**: Externalize all state

- **Design for Failure**: Assume everything fails
- **Scale-Ready**: Design for 100x, implement for 1x

---

## Output Template

```markdown

# System Architecture: [Name]
## 1. Business Context — Problem, users, success metrics
## 2. Quality Attributes — | Attribute | Target | Rationale |
## 3. Architecture Style — Selected style + justification

## 4. Bounded Contexts — Context map + relationships
<!-- REQUIRED DIAGRAM: System Context — shows the system boundary, external actors, and context relationships -->
<!-- Use C4Context or flowchart LR. Label every edge with what flows across it (data, events, API calls). -->

## 5. Component Architecture — Services, responsibilities, interactions
<!-- REQUIRED DIAGRAM: Container/Component — shows internal services, databases, queues, and connections -->
<!-- Use C4Container or flowchart LR. Group by bounded context using subgraphs. Label edges with protocol. -->

## 6. Data Architecture — Storage, ownership, caching
<!-- SITUATIONAL DIAGRAM: ER Diagram — when multiple contexts own distinct data stores -->
<!-- One ER diagram per bounded context if schemas diverge. Show ownership boundaries. -->

## 7. Integration Architecture — Sync/async patterns, external integrations
<!-- SITUATIONAL DIAGRAM: Sequence Diagram — for the 1-2 most critical cross-boundary flows -->
<!-- Keep to ≤8 participants. Show sync vs async clearly. Include error/fallback paths for critical flows. -->

## 8. Resilience Strategy — Failure modes + mitigations
## 9. Security Architecture — AuthN, AuthZ, data protection
## 10. Technology Decisions — | Decision | Choice | Alternatives | Rationale |
## 11. Risks & Mitigations — | Risk | Impact | Likelihood | Mitigation |
## 12. Next Steps — Downstream skills to invoke
```

### Diagram Generation Rules

When writing Mermaid diagrams in `hld.md`, follow `/diagram-architecture` conventions:

1. **One diagram, one question** — never combine system context with component internals
2. **Semantic node IDs** — `orderSvc`, `paymentDB`, not `A`, `B`, `C`
3. **Every edge labeled** — intent + protocol (e.g., `-->|"Creates order via REST/HTTPS"|`)
4. **`classDef` palette** — use consistent semantic colors for services, databases, external systems, queues
5. **Size limits** — ≤15 nodes per flowchart, ≤8 participants per sequence, ≤12 entities per ER diagram
6. **Accessibility** — include `accTitle` and `accDescr` on every diagram
7. **Architectural rationale** — use `%%` comments in diagram source to explain non-obvious decisions

For diagram type selection, syntax details, or pattern templates, read the relevant section from
`/diagram-architecture` refs: [syntax-reference.md](../diagram-architecture/refs/syntax-reference.md)
and [architecture-patterns.md](../diagram-architecture/refs/architecture-patterns.md).

---

## LLD-Ready Output Requirements

The HLD you produce is the foundation that all LLD work builds on. Every LLD architect (API, data, event, frontend, infrastructure) will read `hld.md` first and must align their domain design within these boundaries. Your output must be explicit enough that LLD work can proceed without ambiguity:

| Requirement | What LLD Architects Need | Where in HLD |
|-------------|--------------------------|--------------|
| **Bounded Contexts** | Clear context names, responsibilities, and boundaries. Each LLD architect needs to know which context they're designing within. | Section 4 |
| **Integration Patterns** | For each cross-context interaction: sync or async? REST or events? Who owns the contract? LLD architects must not invent their own integration approach. | Section 7 |
| **Technology Choices** | Database type, messaging system, cache strategy per context. LLD architects align their schemas and contracts to these choices. | Section 10 |
| **Cross-Cutting Concerns** | AuthN/AuthZ strategy, observability approach, resilience patterns. LLD architects honor these rather than designing their own. | Sections 8, 9 |
| **Data Ownership** | Which context owns which data. Prevents LLD architects from creating conflicting data models across boundaries. | Section 6 |

If any of these are left vague, LLD architects will make independent assumptions that may contradict each other. Be explicit.

---

## Quality Gates

### Architecture Quality
- [ ] All quality attributes have **measurable targets**
- [ ] Architecture style **justified** against requirements
- [ ] Bounded contexts **align with business** capabilities
- [ ] **No shared databases** across context boundaries
- [ ] Resilience strategy addresses **all external dependencies**
- [ ] Security boundaries **explicitly defined**
- [ ] Technology choices justified with **trade-offs**
- [ ] Risks identified with **mitigation strategies**
- [ ] **Downstream skills identified** for each component

### Diagram Quality (per `/diagram-architecture`)
- [ ] **System Context diagram present** — every HLD has at minimum this diagram
- [ ] **Component/Container diagram present** — shows internal service topology
- [ ] All edges **labeled** with intent + protocol — no unlabeled arrows
- [ ] Node IDs are **semantic** — `orderSvc`, `paymentDB`, not `A`, `B`
- [ ] Each diagram answers **one question** — not overloaded with multiple concerns
- [ ] Diagrams have **`accTitle` and `accDescr`** for accessibility
- [ ] **Size limits respected** — ≤15 nodes (flowchart), ≤8 participants (sequence)
- [ ] Diagrams **render correctly** as valid Mermaid syntax

### LLD-Readiness (HLD Definition of Done)
- [ ] Service boundaries are **unambiguous** — an LLD architect can identify which context they operate in
- [ ] Integration patterns are **specified per boundary** — sync vs async, protocol, contract ownership
- [ ] Technology choices are **decided, not "TBD"** — LLD architects need concrete targets
- [ ] Cross-cutting concerns have **concrete strategies** — not just "we need auth" but "OAuth2 + RBAC at API gateway"
- [ ] The HLD is **self-contained** — an LLD architect can read it without needing to ask "what did you mean by...?"
- [ ] Architecture diagrams are **embedded in the document** — not referenced as separate files

---

## Deep References

- **[architecture-styles.md](refs/architecture-styles.md)**: Monolith, microservices, event-driven, CQRS patterns
- **[quality-attributes.md](refs/quality-attributes.md)**: NFR analysis framework, trade-off matrices
- **[technology-selection.md](refs/technology-selection.md)**: Database, messaging, cloud service decisions
- **[integration-patterns.md](refs/integration-patterns.md)**: Sync, async, saga, API gateway patterns
- **[resilience-patterns.md](refs/resilience-patterns.md)**: Circuit breakers, bulkheads, fallbacks
- **`/diagram-architecture`**: Mermaid diagram conventions, syntax reference, architecture pattern templates
