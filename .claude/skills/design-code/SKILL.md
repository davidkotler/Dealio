---
name: design-code
version: 1.0.0
description: |
  Systematic design thinking before implementation. Use when planning features,
  architecting systems, low level design, modeling domains, or starting any non-trivial task.
  Activates in plan mode. Produces design artifacts that guide implementation.
  Relevant for: architecture decisions, domain modeling,
  system boundaries, interface contracts.

triggers:
  - plan-mode
  - /design-system command
  - /design-lld command
---

# Design Skill

> *"Think before you code. Design decisions made now determine implementation quality later."*

## Quick Reference

| Aspect | Details |
|--------|---------|
| **Phase** | Pre-implementation (Plan Mode) |
| **Invokes** | Implementation skills after design complete |
| **Invoked By** | Plan mode, `/design-system` command, `/design-lld` command, complex task detection |
| **Output** | Design decisions documented inline or in design doc |

---

## Core Workflow

Execute these phases **in order**. Skip phases only when explicitly not applicable.

### Phase 1: Scope Assessment (Always)

#### 1A: Identify Design Target (Always)

Before any design work, explicitly identify **what** you are designing and **where** it lives. This applies to greenfield and existing systems alike.

**Answer these questions:**

| Question | Answer Format |
|----------|---------------|
| Which **service(s)** are affected? | `services/<name>` — new or existing? |
| Which **domain(s)** within each service? | `domains/<domain>` — new or existing? |
| Which **layers** will change? | routes, flows, ports, adapters, models, infra? |
| Are new domains or services needed? | If yes, name them and state their responsibility |

**For existing services/domains** — scan the current structure:
```bash
# Examine service layout
ls services/<name>/<name>/domains/
# Examine domain internals
ls services/<name>/<name>/domains/<domain>/
```

**For new services/domains** — state where they will be created and what they own.

**Output:** A clear **Design Target** table:

```markdown
| Service | Domain | Status | Layers Affected |
|---------|--------|--------|-----------------|
| notification | delivery | existing | flows, adapters, models/domain |
| notification | templates | **new** | all (greenfield domain) |
| gateway | routing | **new** | all (new service + domain) |
```

#### 1B: Determine Design Depth

```
Task Complexity Assessment
│
├─► Trivial (bug fix, config change, typo)
│   └─► SKIP detailed design → proceed to implementation
│
├─► Small (single function, simple endpoint, unit test)
│   └─► LIGHT design → Phases 2, 6 only
│
├─► Medium (new feature, API endpoint, service method)
│   └─► STANDARD design → All phases, summary depth
│
└─► Large (new service, domain model, system integration)
    └─► FULL design → All phases, detailed depth
        └─► Consider: refs/domain-driven-design.md, refs/modularity.md, refs/data-model.md
```

**Output:** State the assessed complexity and design depth.

---

### Phase 2: Context Gathering (Always)

**Before designing, understand:**

1. **What exists?**
   - Scan relevant directories for existing patterns
   - Identify conventions already established
   - Note naming patterns, file organization, abstractions

2. **What are the constraints?**
   - Technical: language, framework, dependencies
   - Domain: business rules, terminology, entities
   - Quality: performance requirements, SLAs, compliance

3. **Who are the stakeholders?**
   - Consumers of this code (other services, UI, users)
   - Maintainers (team, future developers)

**Action:** Use `Glob` and `Read` to examine:







- Similar existing implementations
- Related domain models
- Adjacent API endpoints or services
- Existing test patterns

**Output:** Brief summary of relevant existing patterns and constraints.

---

### Phase 3: Domain Analysis (Medium+ Tasks)

**→ Reference: `refs/domain-driven-design.md`, `refs/data-model.md`**

Answer these questions:

| Question | Design Decision |
|----------|-----------------|
| What **ubiquitous language** applies? | Use domain terms in code, not technical jargon |
| What **bounded context** does this belong to? | Identify ownership, don't cross boundaries |
| What are the **aggregates**? | Define consistency boundaries |
| **Entities vs Value Objects?** | Identity-based vs attribute-based equality |
| What **domain events** should be emitted? | Cross-aggregate/context communication |

**Decision Framework:**
```
Is this concept...
├─► Tracked by identity over time? ──► Entity
├─► Defined by its attributes? ──► Value Object
├─► A consistency boundary? ──► Aggregate
├─► A significant state change? ──► Domain Event
└─► A cross-aggregate operation? ──► Domain Service
```

**Output:** List key domain concepts with their classifications.

---

### Phase 3B: Boundary & Responsibility Analysis (Existing Systems)

**Trigger:** Working on an existing service or domain — adding features, fixing pain points, or noticing code smells that suggest misaligned boundaries. Skip for greenfield work.

**→ Reference: `refs/domain-driven-design.md`, `refs/modularity.md`, `refs/coherence.md`**

**Responsibility Smell Detection — scan for these signals:**

| Smell | Symptom | Likely Action |
|-------|---------|---------------|
| **Divergent change** | One domain/module changes for unrelated business reasons | Split into separate domains |
| **Shotgun surgery** | One business change touches many domains/services | Merge related logic or realign boundaries |
| **Feature envy** | Domain A constantly reaches into Domain B's models/data | Move the logic to where the data lives |
| **God domain** | Single domain with 10+ models, 15+ routes, mixed vocabularies | Decompose along sub-domain seams |
| **Shared mutable state** | Multiple domains read/write the same DB tables or models | Assign clear ownership; others consume via events/APIs |
| **Circular dependencies** | Domain A imports from B, B imports from A | Extract shared concept into its own module or re-draw boundary |

**Domain Split Analysis:**

```
Should this domain be split?
│
├─► Does it serve multiple distinct business capabilities?
│   └─► YES → Identify sub-domains by grouping models/routes that change together
│
├─► Do parts of it have different rates of change or different stakeholders?
│   └─► YES → Split along those seams — fast-changing vs stable
│
├─► Does it use multiple vocabularies? (e.g., "order" means different things)
│   └─► YES → Each vocabulary = separate bounded context → separate domain
│
└─► Is one team struggling to own it all?
    └─► YES → Split to align with team boundaries (Conway's Law)
```

**Service Split Analysis:**

```
Should this service become multiple services?
│
├─► Do domains within it need independent scaling or deployment?
│   └─► YES → Extract to separate service
│
├─► Does a failure in one domain take down unrelated domains?
│   └─► YES → Separate for fault isolation
│
├─► Is the service exceeding 5-6 domains or becoming hard to reason about?
│   └─► YES → Group related domains into new services by business capability
│
└─► Are there cross-cutting concerns (auth, notifications) embedded in a business service?
    └─► YES → Extract to dedicated infrastructure/platform service
```

**Module Restructuring for Loose Coupling & High Cohesion:**

1. **Map current dependencies** — trace imports between modules/domains to find tight coupling
2. **Identify coupling hotspots** — modules that import from 5+ other modules are coupling magnets
3. **Apply dependency inversion** — introduce ports (protocols/ABCs) where concrete cross-domain imports exist
4. **Consolidate scattered logic** — if the same business concept is spread across modules, gather it into one cohesive module
5. **Extract shared kernel** — if two domains legitimately share types, extract to an explicit shared module rather than one domain importing from another

**Output:** List of proposed boundary changes with rationale:
- Domains to split (with proposed new domains and their responsibilities)
- Domains to merge (with justification for combining)
- Services to extract (with ownership and communication pattern)
- Module restructuring steps (dependency inversions, extractions, consolidations)

---

### Phase 4: Structural Design (Medium+ Tasks)



**→ Reference: `refs/modularity.md`, `refs/coherence.md`**





**Modularity Checklist:**


- [ ] Single responsibility per module/class?

- [ ] Dependencies injected, not instantiated?
- [ ] Public interface minimal and stable?

- [ ] Implementation details hidden?
- [ ] Can be tested in isolation?


**Coherence Checklist:**

- [ ] Follows existing naming conventions?
- [ ] Uses established patterns in codebase?
- [ ] Consistent abstraction level?
- [ ] No new conventions without migration plan?

**Boundary Definition:**
```
New code location decision:
│
├─► Changes for same business reason as existing module?

│   └─► Add to existing module
│
├─► Different rate of change or ownership?

│   └─► Create new module
│
└─► Needs to communicate with other modules?


    └─► Define explicit contract (Protocol/ABC/DTO)
```



**Output:** Proposed file/module structure with responsibilities.

---




### Phase 5: Quality Attribute Analysis (Medium+ Tasks)





Evaluate design against quality attributes. **Reference the specific doc when the attribute is critical.**

#### 5.1 Testability Check




**→ Reference: `refs/testability.md`**


- [ ] All dependencies injectable?

- [ ] Pure functions separable from I/O?


- [ ] No hidden global state?

- [ ] Observable behavior via return values?


#### 5.2 Robustness Check


**→ Reference: `refs/robustness.md`**



- [ ] Input validation at boundaries?

- [ ] Explicit error types for failure modes?
- [ ] Timeouts on external calls?


- [ ] Idempotent operations where retries possible?



#### 5.3 Evolvability Check


**→ Reference: `refs/evolvability.md`**



- [ ] Extension points for anticipated variation?


- [ ] Third-party dependencies wrapped in adapters?
- [ ] Configuration externalized?
- [ ] Versioning strategy for public interfaces?


#### 5.4 Performance Check


**→ Reference: `refs/performance.md`**



- [ ] Data structure matches access pattern?
- [ ] Algorithm complexity acceptable for expected scale?

- [ ] I/O operations async and batchable?
- [ ] Caching strategy defined (if applicable)?


#### 5.5 Observability Check


**→ Reference: `refs/observability.md`**

- [ ] What events should be logged?

- [ ] What spans for distributed tracing?
- [ ] What metrics indicate health?
- [ ] What errors require alerts?


#### 5.6 Reusability Check

**→ Reference: `refs/reusability.md`**

- [ ] Does this functionality already exist in a shared library (`libs/`)?
- [ ] Will 2+ services need this behavior? → Extract to `libs/lib-<name>`
- [ ] Will 2+ domains within this service need it? → Extract to shared module/sub-package
- [ ] Does extracted code define a stable interface (Protocol/ABC)?
- [ ] Is the shared code generic (no service-specific assumptions)?

**Output:** Note any quality concerns and mitigations.


---


### Phase 6: Interface Design (Always for new interfaces)

**Define contracts before implementation:**


For **APIs/Endpoints:**

- Request/response shapes (Pydantic models)
- HTTP methods and status codes
- Error response format

- Authentication/authorization requirements

For **Internal Interfaces:**

- Protocol/ABC definition
- Method signatures with types
- Pre/post conditions
- Exception contracts

For **Events:**

- Event name (past tense)
- Payload structure (self-contained)
- Producer and expected consumers

**Output:** Interface definitions or pseudocode signatures.

---

### Phase 7: Risk Assessment (Large Tasks)

**Identify risks before implementation:**

| Risk Category | Question | Mitigation |
|---------------|----------|------------|
| **Complexity** | Is this overengineered? | Simplify; YAGNI |
| **Coupling** | Does this create tight coupling? | Introduce abstraction |
| **Breaking Changes** | Will this break existing consumers? | Version; deprecation path |
| **Performance** | Could this become a bottleneck? | Profile assumptions; design for scale |
| **Security** | Are there trust boundaries crossed? | Validate; authenticate; authorize |

**Output:** List identified risks with mitigation strategies.

---

## Design Output Template

After completing relevant phases, summarize:

```markdown
## Design Summary

**Task:** [Brief description]
**Complexity:** [Trivial/Small/Medium/Large]
**Design Depth:** [Skip/Light/Standard/Full]

### Design Target
| Service | Domain | Status | Layers Affected |
|---------|--------|--------|-----------------|
| ... | ... | new/existing | ... |

### Context
[Existing patterns, constraints, stakeholders]

### Boundary Changes (if applicable)
[Domains to split/merge, services to extract, module restructuring]

### Domain Model (if applicable)
[Key concepts, aggregates, events]

### Structure
[Proposed files/modules with responsibilities]

### Interfaces
[Key interface definitions]

### Quality Considerations
[Testability, robustness, performance, observability notes]

### Risks & Mitigations
[Identified risks and how they're addressed]

### Implementation Guidance
[Specific guidance for implementation phase]
```

---

## Decision Shortcuts

**Common Design Decisions:**

| Situation | Decision | Reference |
|-----------|----------|-----------|
| Need external service call | Wrap in adapter; add timeout/retry/circuit breaker | robustness.md |
| Data transformation logic | Pure function; no side effects | testability.md |
| Cross-domain communication | Domain event; ACL for translation | domain-driven-design.md |
| State that changes together | Single aggregate | domain-driven-design.md |
| Behavior varies by type | Strategy pattern; inject at runtime | evolvability.md |
| Complex query requirements | Consider CQRS; separate read model | domain-driven-design.md |
| High-throughput path | Async; bounded queues; consider batching | performance.md |
| User-facing operation | Structured logging; trace span; latency metric | observability.md |
| Data models across layers | Layered: Common → Domain → Contracts/Persistence; inherit, don't redeclare | data-model.md |
| Domain model consumed by other services | Place in shared schemas; contracts inherit from domain | data-model.md |
| Storage-specific fields (soft-delete, versioning) | Add only at persistence layer; use model_dump() for mapping | data-model.md |
| Logic needed by 2+ services | Extract to `libs/lib-<name>`; define Protocol interface | reusability.md |
| Logic needed by 2+ domains in same service | Extract to shared module/sub-package within service | reusability.md |
| Duplicate implementations found across services | Consolidate into shared library; migrate all consumers | reusability.md |

---

## Quality Gates

**Before proceeding to implementation, verify:**

- [ ] **Design target declared** — services, domains, layers, and new/existing status identified
- [ ] Complexity assessed and design depth appropriate
- [ ] Existing patterns reviewed and followed (or deviation justified)
- [ ] Domain concepts identified with correct classifications
- [ ] **Boundary health assessed** (existing systems) — no responsibility smells left unaddressed
- [ ] Module boundaries respect single responsibility
- [ ] Interfaces defined with types before implementation
- [ ] Critical quality attributes addressed
- [ ] Reusability assessed: cross-service → `libs/`, cross-domain → shared module
- [ ] No design contradicts established principles

**If any gate fails:** Address before implementation. Technical debt from poor design compounds.

---

## Skill Chaining

**After design phase completes, invoke:**

| Condition | Next Skill | Handoff |
|-----------|------------|---------|
| Python implementation needed | `implement/python` | Design summary, interfaces |
| API endpoints designed | `implement/api` | Endpoint specs, models |
| Database changes needed | `implement/data` | Entity models, queries |
| React components designed | `implement/react` | Component hierarchy, props |
| Infrastructure required | `infra/*` | Resource requirements |

---

## Anti-Patterns to Avoid

❌ **Skipping design for "simple" tasks** that grow complex  
❌ **Designing in isolation** without checking existing patterns  
❌ **Over-designing** trivial changes  
❌ **Ignoring quality attributes** until implementation  
❌ **Copying patterns blindly** without understanding context  
❌ **Designing mutable interfaces** that will break consumers
❌ **Duplicating logic** across services instead of extracting to shared library
❌ **Inlining cross-cutting concerns** (auth, validation, formatting) per-service instead of reusing from `libs/`
