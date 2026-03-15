# Engineering Principles

These principles define how we design, build, and evolve software systems. They are non-negotiable and apply to every
artifact produced.

---

## 1. System Architecture

### 1.1 API/Event-First Design

**MUST:**

- Version APIs explicitly in the URL or header
- Design for backward compatibility


- Implement endpoints without a documented contract
- Break existing API consumers without deprecation period
- Expose internal implementation details in API responses

**WHEN** designing a new service endpoint **THEN** write the OpenAPI spec first:

**WHEN** designing a new service event handler **THEN** write the AsyncAPI spec first:

---

### 1.2 Bounded Contexts & Service Boundaries

**MUST:**

- Align service boundaries with domain boundaries
- Define explicit public interfaces for each bounded context
- Use ubiquitous language within each context

**NEVER:**

- Share database tables across service boundaries
- Let domain logic leak across context boundaries
- Create "god services" that span multiple domains

**WHEN** two domains need to communicate **THEN** use explicit integration patterns:

---

### 1.3 Stateless Services

**MUST:**

- Externalize all state to dedicated stores (DB, cache, queue)
- Design request handlers to be stateless

**NEVER:**

- Store request-scoped data in module-level variables
- Rely on local filesystem for persistent state

**WHEN** state is required **THEN** externalize explicitly:

---

### 1.4 Resilience Patterns

- Implement circuit breakers for external service calls

- Define timeouts for all network operations
- Design bulkheads to isolate failures
- Isolate resource consumption per request, tenant, and operation class
- Propagate backpressure upstream rather than queueing unboundedly

**NEVER:**

- Retry indefinitely without backoff
- Let one failing dependency cascade to entire system

**WHEN** calling unreliable dependencies **THEN** apply resilience:

---

### 1.5 Graceful Degradation

- Provide fallback behavior when dependencies fail
- Prioritize partial functionality over complete failure
- Communicate degraded state to clients appropriately


- Return 500 errors for non-critical feature failures

- Hide degraded state from observability

**WHEN** a non-critical dependency fails **THEN** degrade gracefully:

### 1.6 Horizontal Scalability

**MUST:**

- Eliminate single points of failure


- Store locks in local memory
- Use local cron jobs for distributed work
- Assume sequential processing order across instances

---

### 1.7 Async-First Cross-Boundary Communication (Event Driven)

**MUST:**

- Use events for cross-domain integration
- Default to asynchronous communication across service/module boundaries
- Use synchronous calls only when response is required to continue (queries, not commands)
- Design all async handlers to be idempotent
- Include correlation IDs in all async messages for tracing
  **NEVER:**

- Chain synchronous calls across multiple services (latency multiplies, availability decreases)
- Design async flows that require ordering across different entity types

- Assume message delivery is instantaneous

**WHEN** operation can tolerate seconds of delay **THEN** use async (email, notifications, analytics, cross-service
sync)

**WHEN** user is waiting for response **THEN** use sync, but scope the sync call narrowly
**WHEN** starting without message queue **THEN** design interfaces as if async exists—implementation can use direct
calls initially, swap to queue later

---

### 1.8 Scale-Ready Design

**MUST:**

- Design interfaces for 100x load; implement for current load
- Minimize coordination points—each synchronous dependency multiplies latency


- Design queries that must touch all partitions to answer
- Accept work faster than downstream can complete (unbounded queues)
- Force N API calls for N items when one batch call suffices

**WHEN** designing any interface **THEN** ask: "Does this work at 100x load without architectural change?" Fix the
interface now; implementations can stay simple.

---


**WHEN** read and write patterns diverge significantly **THEN** separate them:

- Separate write models (domain entities) from read models (DTOs/projections)
- Accept eventual consistency in read models
- Use projections for complex query requirements


- Force CQRS on simple CRUD domains

- Expect immediate consistency between write and read models

---

### 1.10 Observability

**MUST:**

- Define observability contracts before implementation (logs, metrics, traces, health)
- Use structured logging with bounded, typed fields
- Implement separate health probes

- Propagate trace IDs across all boundaries
- Define SLIs based on user experience, not technical metrics

**NEVER:**

- Treat observability as post-implementation instrumentation
- Design high-cardinality metric labels (unbounded values)

- Create generic errors without diagnostic context

**WHEN** designing a service **THEN** define observability contract first

---

### 1.11 Security by Design

**MUST:**

- Use parameterized queries; never construct SQL/commands from strings

- Store secrets in vaults, never in code or config files
- Apply principle of least privilege to all service accounts and APIs
- Encrypt sensitive data at rest and in transit
- Authenticate and authorize every request at service boundaries
  **NEVER:**


- Log secrets, tokens, or PII
- Trust client-side validation alone
- Expose stack traces or internal errors to external clients
- Store passwords in plaintext or reversible encryption

---

## 2. Software Engineering

### 2.1 Readability First

**MUST:**

- Write code for humans to read, machines to execute
- Use descriptive names that reveal intent
- Keep functions short and focused (< 20 lines preferred)

**NEVER:**

- Sacrifice clarity for cleverness
- Use abbreviations that aren't universally understood
- Write dense one-liners when multi-line is clearer

---


**MUST:**

- Use domain expert terminology in code, not technical jargon
- Design aggregates around transactional consistency boundaries
- Access aggregate internals only through the root
- Reference other aggregates by ID, not object reference
- Make value objects immutable with attribute-based equality
- Define repository interfaces in domain layer, implement in infrastructure

**NEVER:**

- Use generic names (`Handler`, `Processor`) when domain terms exist
- Use entities when value objects suffice
- Put business logic in repositories

**WHEN** "is this the same X?" matters **THEN** model as Entity

**WHEN** equality is by attributes only **THEN** model as Value Object

**WHEN** objects must be transactionally consistent **THEN** same aggregate

**WHEN** objects can be eventually

### 2.2 Domain-Driven Design

**MUST:**
- Use domain expert terminology in code, not technical jargon
- Design aggregates around transactional consistency boundaries
- Access aggregate internals only through the root
- Reference other aggregates by ID, not object reference
- Make value objects immutable with attribute-based equality
- Define repository interfaces in domain layer, implement in infrastructure
- Create anti-corruption layers for external system integration

### 2.3 Modularity

**MUST:**

- Use full import paths for all module imports
- Depend on abstractions (protocols/ABCs) at module boundaries
- Inject all dependencies through constructors or parameters
- Design each module to be testable in isolation
- Use anti-corruption layers when integrating external systems
- Import private/internal symbols from other modules

- Share database tables or ORM models across module boundaries
- Create circular dependencies between modules
- Instantiate collaborators inside classes (hardcoded coupling)

- Build "god modules" spanning multiple unrelated concepts
- Expose mutable internal data structures

**WHEN** code changes together for the same business reason **THEN** keep it in the same module

**WHEN** code has different reasons to change **THEN** separate into distinct modules

**WHEN** modules need to communicate **THEN** define explicit contracts (protocols, DTOs, events)

**WHEN** a module exceeds ~500 lines or ~10 public exports **THEN** split along domain seams

**WHEN** testing requires mocking >3 collaborators **THEN** re-evaluate module boundaries

### 2.4 Evolvability

**MUST:**

- Version all public interfaces (APIs, events, schemas) from day one
- Define explicit extension points for anticipated variation
- Wrap third-party dependencies behind adapter interfaces you control

- Provide migration paths and tooling for any breaking change
- Use additive schema changes; new fields must be optional with defaults

**NEVER:**

- Expose internal data structures through public interfaces
- Assume current requirements are final
- Remove functionality without migration tooling
- Hardcode behavior that stakeholders may want to change

**WHEN** adding new behavior to an existing module **THEN** extend through composition or strategy, not modification

---

### 2.5 Single Responsibility

**MUST:**

- Give each module/class/function one reason to change
- Separate orchestration from computation

**NEVER:**

- Create "manager" or "handler" classes that do everything
- Mix I/O with business logic
  **WHEN** a function does multiple things **THEN** decompose:

**MUST:**

- Prefer composition and delegation over class hierarchies
- Favor mixins over deep inheritance when behavior sharing needed

**NEVER:**

- Create inheritance hierarchies deeper than 2-3 levels
- Use inheritance for code reuse alone

**WHEN** sharing behavior **THEN** compose:

---

- Write pure functions without side effects where possible
- Make side effects explicit and push to boundaries
- Use immutable data structures by default

- Mutate input arguments
- Mix queries (return data) with commands (change state)

**WHEN** transforming data **THEN** use pure functions:


---

**MUST:**

- Model expected failures as explicit union types (`Success | ErrorA | ErrorB`)
- Preserve error context by chaining causes (`raise X from e`)
- Bound all collections and queues with explicit size limits

**NEVER:**

- Return `None` to indicate errors (ambiguous with "not found")
- Use silent defaults (`.get(key, default)`) for required data
- Swallow exceptions with empty `except` blocks

**WHEN** a failure is expected (not found, insufficient funds, locked) **THEN** return typed Result, not exception
**WHEN** re-raising exceptions **THEN** chain: `raise DomainError(...) from original`

**WHEN** accepting external collections **THEN** enforce bounds: `Field(max_length=100)`

### 2.8 Robustness

**MUST:**
- Model expected failures as explicit union types (`Success | ErrorA | ErrorB`)
- Preserve error context by chaining causes (`raise X from e`)
- Bound all collections and queues with explicit size limits
- Use direct access for required data; let `KeyError`/`AttributeError` surface problems

**NEVER:**
- Return `None` to indicate errors (ambiguous with "not found")
- Use silent defaults (`.get(key, default)`) for required data
- Swallow exceptions with empty `except` blocks
- Use stringly-typed errors or string matching for error handling

### 2.9 Testability

**MUST:**

- Separate pure logic from I/O operations (functional core, imperative shell)

- Keep constructors trivial (assignment only—no logic, no I/O)
- Design for determinism (same input → same output)
- Return values rather than mutating state
- Expose observable behavior through explicit outputs


- Use global or module-level mutable state
- Instantiate collaborators inside methods (no seam for substitution)
- Perform I/O in constructors
- Create static methods with side effects
- Hide dependencies in method bodies

**WHEN** logic depends on time or randomness **THEN** inject an abstraction (Clock, RandomSource)

**WHEN** testing requires mocking >3 collaborators **THEN** decompose—the unit has too many responsibilities

**WHEN** an operation has side effects **THEN** separate the decision (pure) from the action (effectful)

**WHEN** external systems are involved **THEN** define a port (protocol) and implement adapters

---




**MUST:**

- Use identical patterns for structurally similar problems
- Mirror existing module structures when creating new ones
- Apply glossary terms consistently within each bounded context
- Maintain uniform abstraction levels within components
- Migrate all usages when adopting new patterns—partial adoption creates confusion

**NEVER:**

- Use synonyms for the same domain concept (`client`/`customer`/`user`)
- Introduce new conventions without a migration plan for existing code
- Create "snowflake" implementations when established patterns exist

**WHEN** implementing new functionality **THEN** audit existing codebase for similar features and mirror their patterns
exactly

**WHEN** discovering two patterns solving the same problem **THEN** select the superior one and create a migration
task—never add a third

**WHEN** one bounded context needs data from another **THEN** translate through an anti-corruption layer using the
receiving context's language

### 2.11 Performance Awareness

**MUST:**

- Use generators for large sequence processing
- Document time/space complexity for public methods
- Set explicit timeouts on all external calls

**NEVER:**

- Use O(n²) algorithms on unbounded inputs

- Materialize collections when streaming suffices
- Await sequentially when operations are independent
- Concatenate strings in loops—collect and join

**WHEN** designing hot paths **THEN** minimize allocations and prefer immutable structures

**WHEN** performing multiple independent I/O calls **THEN** parallelize with bounded concurrency

**WHEN** returning collections via API **THEN** paginate with explicit limits

---


**MUST:**

- Define domain types (NewType, TypedDict, dataclasses)
- Run static type checking in CI (ty strict mode)
  **NEVER:**

- Use `Any` except at true boundaries
- Ignore type checker errors with `# type: ignore` without comment
  **WHEN** modeling domain concepts **THEN** create explicit types:

---

### 2.13 Pydantic Validation

**MUST:**

- Use Pydantic models for all external data boundaries (APIs, configs, messages)

- Define constraints using Pydantic's built-in validators and types

- Leverage `model_validate` and `model_dump` for serialization
  **NEVER:**

- Parse unvalidated dicts into domain objects manually
- Skip validation for "internal" data that crosses boundaries

**WHEN** receiving external input **THEN** validate with Pydantic:

### 2.14 Test Behavior, Not Implementation

- Test public interfaces and observable behavior
- Write tests that survive refactoring
- Use the testing pyramid: many unit, fewer integration, few E2E, few UI

**NEVER:**

- Test private methods directly

- Assert on implementation details (method call counts, internal state)
- Write tests that break when refactoring without behavior change

**WHEN** writing tests **THEN** focus on behavior:

### 2.15 Reusability

Single source of truth for shared behavior — consistency first, efficiency second.

**MUST:**

- Search `libs/` before implementing cross-cutting logic — the library likely exists
- Cross-service functionality → `libs/lib-<name>`; cross-domain within one service → shared module
- Define stable interfaces (Protocol/ABC) for shared code — consumers depend on abstractions
- Keep shared code generic — no service-specific assumptions

**NEVER:**

- Copy-paste code between services — if copying, extract
- Put service-specific logic in `libs/` — libraries serve all consumers equally
- Create "util" or "helpers" grab-bags — each shared module needs cohesive responsibility
- Duplicate types defined in `lib-schemas` — import from canonical source

**WHEN** 2+ services implement the same pattern **THEN** extract to `libs/`, migrate all consumers, delete duplicates

**WHEN** 2+ domains in one service share logic **THEN** extract to a `shared/` sub-package within the service

**WHEN** only one consumer exists and no second is foreseeable **THEN** keep it local — premature extraction creates coupling

---

## 3. Data Engineering

### 3.1 Schema as Code

**MUST:**

- Version all schema definitions in source control
- Use migrations for schema changes

- Document schema evolution decisions

**NEVER:**

- Create schemas without versioning

- Break schema compatibility without migration path

### 3.2 Data Contracts

**MUST:**

- Specify SLAs for data freshness, quality, and availability
- Validate data at ingestion points

**NEVER:**

- Change producer schemas without consumer coordination

- Skip validation for "trusted" sources

### 3.3 Immutability by Default

**MUST:**

- Treat data mutations as explicit events


- Design for append-only where possible

**NEVER:**

- Delete data without soft-delete or tombstone
- Update records without preserving history
- Lose lineage through in-place mutations

**WHEN** data changes **THEN** record as event:

### 3.4 Idempotent Operations

**MUST:**

- Design all data operations to be safely repeatable
- Use idempotency keys for mutations

- Handle duplicate processing gracefully


- Assume operations run exactly once

- Create duplicate records on retry

**WHEN** processing messages/events **THEN** ensure idempotency:

### 3.5 Design for Failure

**MUST:**

- Implement dead letter queues for failed processing
- Design for partial failure recovery

**NEVER:**

- Drop messages on processing failure
- Require full reprocessing for partial failures
- Ignore pipeline failures silently

### 3.6 Data Model Design

**MUST:**

- Enumerate all access patterns before designing schema
- Define the grain of each table (what does one row represent?)
- Use globally unique identifiers (UUIDv7, ULID, or structured IDs) for all entities
- Design IDs to be valid partition keys (high cardinality, even distribution)
- Generate IDs and Enforce constraints at the data layer, not in application code
- Keep primary keys immutable
- Ensure every query can use an index
- Use correct types (DECIMAL for money, dates for dates—never strings)

**NEVER:**

- Design storage without knowing the queries
- Create unbounded queries (always paginate)

**WHEN** natural keys might change **THEN** use immutable surrogate keys

**WHEN** strong consistency is required (financial, inventory) **THEN** accept latency—never compromise correctness

**WHEN** starting with single database **THEN** still use distributed-ready IDs—migration cost is near-zero now,
enormous later

---


**MUST:**

- Design aggregates to be independently persistable (one aggregate = one transaction)
- Reference other aggregates by ID only, never by object reference
- Accept eventual consistency between aggregates as the default
- Design aggregate boundaries assuming they could live in separate databases

**NEVER:**

- Update multiple aggregates in a single transaction
- Create foreign key constraints across aggregate boundaries
- Assume aggregates will always share a database
- Design aggregates that require joins to load

**WHEN** two entities must be atomically consistent **THEN** they belong in the same aggregate
**WHEN** business process spans aggregates **THEN** use domain events and eventual consistency (not distributed
transactions)

**WHEN** "but we need consistency" **THEN** challenge the requirement—true cross-aggregate atomicity is rare and
expensive

---

### 3.8 Explicit Scaling Seams

**MUST:**

- Define repository interfaces for all data access (enables database swap)
- Abstract external service calls behind interfaces (enables async swap)
- Isolate cache access behind interfaces (enables cache technology swap)
- Design configuration for per-environment scaling parameters (pool sizes, timeouts, batch sizes)

**NEVER:**

- Hardcode database queries in business logic
- Call external services directly without abstraction
- Embed scaling assumptions in business logic
- Assume current deployment topology is permanent

**WHEN** implementing simple version **THEN** still define the interface as if complex version exists

**WHEN** using single database **THEN** design repository interfaces that could support sharding (accept partition key
even if ignored initially)

**WHEN** "we don't need abstraction yet" **THEN** create thin abstraction anyway—cost is minimal, refactoring cost
without it is high

—
