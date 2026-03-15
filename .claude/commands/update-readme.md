Analyze changes on the current branch and update the README.md of each affected service, lib, or tool to keep documentation accurate and up-to-date.

READMEs describe **what** a package does and **why** it exists — not **how** it's implemented. They should remain accurate even as the internal code evolves. A reader should finish the README understanding the package's purpose, boundaries, patterns, and role in the system — without needing to open a single source file.

## Context

Current branch: !`git branch --show-current`
Default branch: main
Merge base commit: !`git merge-base HEAD main 2>/dev/null || echo HEAD~1`

## Arguments

`$ARGUMENTS` is interpreted as:
- **Empty** — detect changed packages from the branch diff and update only their READMEs
- **A package name** (e.g., `lib-settings`, `cli`, `my-service`) — read the package thoroughly and rewrite its README.md from scratch
- **`--all`** — rewrite README.md for every package under `services/`, `libs/`, and `tools/`
- **`--dry-run`** — show what would be updated without writing files

## Steps

### 1. Identify Packages to Update

**If `$ARGUMENTS` specifies a package name:**
- Locate it under `services/`, `libs/`, or `tools/`
- If not found, report the error and list available packages

**If `$ARGUMENTS` is `--all`:**
- Collect every directory under `services/`, `libs/`, and `tools/` that contains a `pyproject.toml`

**If `$ARGUMENTS` is empty (default — diff mode):**
- Determine the merge base:
  ```bash
  MERGE_BASE=$(git merge-base HEAD main 2>/dev/null || echo "")
  ```
- Get changed files:
  ```bash
  git diff --name-only --diff-filter=ACMR $MERGE_BASE..HEAD
  ```
- Map each changed file to its parent package by matching paths:
  - `libs/<lib-name>/...` → package is `libs/<lib-name>`
  - `services/<svc-name>/...` → package is `services/<svc-name>`
  - `tools/<tool-name>/...` → package is `tools/<tool-name>`
- Deduplicate to get the set of affected packages
- If no packages are affected, report "No services, libs, or tools changed on this branch" and stop

### 2. Analyze Each Package

Focus on understanding the package's **purpose, role, and design** — not cataloging its implementation.

**a. Read `pyproject.toml`** — extract:
  - Package name and description
  - Workspace dependencies (other `lib-*` packages)
  - Notable external dependencies that shape the package's identity (e.g., FastAPI, FastStream, httpx)

**b. Understand the package's intent:**
  - Use `get_symbols_overview` on the top-level module to understand the public surface area
  - Read key files enough to understand **what problems the package solves** and **what patterns it follows**
  - For services: understand the domain boundaries, what the service owns, and how it communicates
  - For libs: understand what capability it provides and what contract it offers to consumers
  - For tools: understand what workflows it enables

**c. Identify architectural patterns:**
  - Which architectural patterns does it implement? (ports-and-adapters, event-driven, CQRS, etc.)
  - What are its integration boundaries? (HTTP APIs, events, database, external services)
  - What resilience/observability/security patterns does it apply?
  - What design decisions shape its structure?

**d. Check for specs/** — if the package has `specs/openapi/` or `specs/asyncapi/`, note the API surface at a conceptual level (what resources/events, not endpoint details).

**e. Read existing README.md** (if present) — preserve any sections the user manually wrote that are still accurate. Note what needs updating.

### 2a. Analyze Domains (services only)

For every package under `services/`, define the **Service Boundary** and build a **Domain Taxonomy** — giving developers both the big picture of what this service owns in the system and a detailed map of its internal bounded contexts.

**Analyze the service boundary:**

The service boundary defines what this service owns in the broader system — the line between "ours" and "theirs." To determine it:

- Read `settings.py`, `router.py`, `event_registry.py`, and `main.py` to understand what the service exposes and connects to
- Read `specs/openapi/` and `specs/asyncapi/` (if present) to understand the external contract surface
- Scan `infra/` to understand what infrastructure the service owns (databases, queues, caches, external clients)
- Look across all domains to synthesize the aggregate picture:
  - **What data does this service own?** — which databases/tables/collections are exclusively managed here
  - **What external contracts does it expose?** — HTTP APIs, event topics, gRPC services (conceptual, not paths)
  - **What does it consume from outside?** — other services it calls, events it subscribes to, external APIs
  - **What it explicitly does NOT own** — adjacent concerns handled by other services (this prevents scope creep and clarifies responsibility)

**Discover domains:**
- List directories under `services/<svc>/<svc>/domains/` — each subdirectory is a domain
- In diff mode, identify which domains were affected by changes:
  - Map changed files matching `services/<svc>/<svc>/domains/<domain>/...` to their parent domain
  - Update the taxonomy entry for each affected domain
  - Preserve existing taxonomy entries for unchanged domains

**For each domain, analyze:**

1. **Purpose** — What business capability does this domain own? Read `flows/`, `models/domain/`, and `exceptions.py` to understand the domain's responsibility. Frame it as the business problem it solves, using ubiquitous language from the domain.

2. **Architecture** — What layers are active? Check which directories have content beyond `__init__.py`:
   - `routes/v1/` → exposes HTTP endpoints (note API version)
   - `handlers/v1/` → consumes events/messages
   - `jobs/` → runs scheduled/background work
   - `flows/` → orchestration layer present
   - `ports/` + `adapters/` → ports-and-adapters pattern in use
   - `models/persistence/` → owns persistent state
   - Describe the domain's internal architecture in terms of which layers it uses and how they interact. Not all domains use every layer — a domain that only publishes events won't have `handlers/`.

3. **Boundary** — What does this domain own exclusively?
   - What aggregates/entities does it define? (name the business concepts, not class names)
   - What state does it manage? (what persistence models exist)
   - What domain exceptions does it raise? (what error conditions are specific to this domain)
   - What contracts does it define? (API request/response shapes, event payloads)
   - Frame boundaries in terms of data ownership: "This domain is the single source of truth for X."

4. **Integration Points** — How does this domain connect to the rest of the service and the broader system?
   - **Inbound**: What HTTP resources does it expose? What events does it consume?
   - **Outbound**: What events does it publish? What ports does it depend on? What external services does it call through adapters?
   - **Internal**: Does it interact with other domains in the same service? Through what mechanism (shared flows, internal events, direct port calls)?
   - Use conceptual descriptions: "Listens for payment confirmation events and transitions order state" — not class or function names.

### 3. Write the README.md

Generate or update the README following the template below. The README should help a developer understand **what** the package does, **why** it exists, and **where** it fits in the system — without coupling to implementation details that change frequently.

#### README Template

```markdown
# <package-name>

<One-line description. Bold the key domain concept or capability this package owns.>

## Purpose

<2-4 sentences explaining why this package exists, what problem it solves, and who its consumers are.
Frame this from the perspective of the system — what would be missing or broken without it?>

## Architecture

<Describe the architectural approach. For services: domain boundaries, layer structure, communication style.
For libs: the abstraction it provides, the contract it offers, how consumers interact with it.
Use prose, not file trees. Reference patterns by name (e.g., "follows ports-and-adapters",
"provides a protocol-based abstraction over X").>

## Key Patterns

<Bullet list of the important design patterns and decisions. Each bullet should name the pattern
and briefly explain why it's used here. Only include patterns that are central to understanding
the package — skip generic ones that apply to every package in the repo.>

## Integration Points

<How does this package connect to the rest of the system? Describe:
- What it exposes (HTTP APIs, events, importable modules)
- What it consumes (other services, external APIs, databases, message queues)
- Where it sits in the dependency graph

Use conceptual descriptions, not endpoint paths or class names.>

## Dependencies

<List workspace dependencies (other libs) and notable external dependencies that shape
the package's behavior. Explain the role each dependency plays — don't just list names.>

## Service Boundary _(services only — omit for libs and tools)_

<Define the overall boundary of this service in the system. Answer four questions:

- **Owns**: What data and business capabilities does this service exclusively own?
  List the databases, tables, or collections it manages. Name the business concepts
  it is the authoritative source for.
- **Exposes**: What does this service offer to the outside world?
  HTTP APIs, event topics it publishes, gRPC services — described conceptually.
- **Consumes**: What does this service depend on from outside?
  Other services it calls, events it subscribes to, external APIs, shared infrastructure.
- **Does not own**: What adjacent concerns are explicitly outside this service's scope?
  Name the sibling services or systems that handle those concerns instead.

This section draws the line between "ours" and "theirs" — a developer should finish reading
it knowing exactly what this service is responsible for and what falls outside its remit.>

## Domain Taxonomy _(services only — omit for libs and tools)_

<For each domain under `domains/`, add a subsection. Order domains by dependency:
domains that other domains depend on come first.>

### <domain-name>

<One-line summary of the business capability this domain owns.>

**Purpose**: <2-3 sentences. What business problem does this domain solve? Who are its
consumers (end users, other domains, external systems)? What would break if it didn't exist?>

**Architecture**: <Which layers does this domain use and how do they interact?
Example: "Exposes versioned REST endpoints that delegate to flows. Flows orchestrate
domain logic through repository and publisher ports. Adapters implement persistence
via PostgreSQL and event publishing via SNS.">

**Boundary**: <What does this domain own exclusively? What data is it the source of truth for?
What business concepts (aggregates, entities, value objects) does it define?
What domain-specific error conditions does it handle?>

**Integration**:
- _Inbound_: <What HTTP resources does it expose? What events/messages does it consume?>
- _Outbound_: <What events does it publish? What external services does it call?>
- _Internal_: <How does it interact with sibling domains in the same service, if at all?>
```

#### Template Rules

- **Purpose section**: Should be understandable by someone who has never seen the codebase. Avoid jargon unless it's domain-specific and necessary.
- **Architecture section**: Describe the design, not the files. "Routes delegate to flows which orchestrate domain logic through ports" is good. "routes/v1/users.py calls flows/create_user.py" is bad.
- **Key Patterns section**: Only patterns that are distinctive or important. If every package uses dependency injection, don't list it unless this package does something unusual with it.
- **Integration Points section**: Conceptual boundaries. "Publishes domain events when orders change state" is good. "Uses EventPublisher.publish(OrderCreatedEvent)" is bad.
- **Dependencies section**: Only workspace deps (`lib-*`) and notable externals. Skip `pydantic`, `pytest`, and other ubiquitous deps unless they're central to the package's identity.
- **Service Boundary section** (services only):
  - Include ONLY for packages under `services/`. Omit entirely for libs and tools.
  - This is the service-level "what's ours vs. what's theirs" — a higher-level view than individual domain boundaries.
  - **Owns**: Aggregate data ownership across all domains. "This service is the system of record for customers, addresses, and preferences."
  - **Exposes**: Synthesize from specs and domain routes. Conceptual, not paths.
  - **Consumes**: Derive from `infra/` clients, adapter ports, and event handlers.
  - **Does not own**: Explicitly name adjacent services and what they handle. This prevents scope creep and helps new developers understand where this service ends and others begin.
  - Update this section whenever domains are added, removed, or change their external contracts.
- **Domain Taxonomy section** (services only):
  - Include ONLY for packages under `services/`. Omit entirely for libs and tools.
  - One subsection per domain directory found under `domains/`.
  - Order domains by dependency — foundational domains (depended on by others) come first.
  - Use the domain's **ubiquitous language** — the business terms that appear in its models, flows, and exceptions.
  - **Purpose**: Frame as a business capability, not a technical layer. "Manages the lifecycle of customer orders from placement through fulfillment" — not "Contains CRUD operations for the orders table."
  - **Architecture**: Describe only the layers this specific domain uses. If a domain has no `handlers/`, don't mention event consumption. If it has no `jobs/`, don't mention scheduling.
  - **Boundary**: Emphasize data ownership. Each domain should be the single source of truth for its aggregates. Mention what it does NOT own (e.g., "relies on the Pricing domain for cost calculations").
  - **Integration**: Distinguish inbound (what it exposes), outbound (what it calls/publishes), and internal (sibling domain interaction). If a domain is self-contained with no cross-domain interactions, say so explicitly.
  - In diff mode, only re-analyze domains that had file changes. Preserve existing taxonomy entries for unchanged domains verbatim.
  - Do NOT fabricate domains, capabilities, or integrations. Only document what exists in the code.
- **Do NOT include**: badges, license sections, contributing guides, changelog, installation instructions (this is a monorepo — `make init` handles everything), file trees, import paths, class/function names, code examples.
- **Do NOT fabricate**: capabilities, patterns, or integrations that don't exist.
- **Preserve user-added sections**: If the existing README has sections not in the template (e.g., "Migration Guide", "Design Decisions"), keep them if they're still accurate. Remove them if the code they describe no longer exists.

#### Why No Code Examples or File Trees?

Implementation details change frequently — function signatures evolve, files get renamed, modules get restructured. READMEs that reference specific code become misleading fast and create maintenance burden. Developers who need implementation details should read the code directly; the README's job is to give them the **mental model** they need before they start reading code.

### 4. Apply Updates

- Write the README.md using the Edit tool (if updating) or Write tool (if creating)
- For each package, show a brief summary of what changed in the README

### 5. Report

Output a summary:
- How many packages were analyzed
- Which READMEs were created vs updated
- For services: which domains were added, updated, or unchanged in the taxonomy
- A one-line summary of changes for each (e.g., "lib-settings: clarified purpose, added integration points section")
- A one-line summary per affected domain (e.g., "order-service/orders: updated integration points after new event handler added")
- If in dry-run mode, show the planned changes without writing

## Constraints

- NEVER include implementation details: no file trees, no class names, no function names, no import paths, no code examples
- NEVER remove accurate content from an existing README without replacement
- NEVER add badges, license info, or boilerplate that doesn't add value
- ONLY update READMEs — do not modify any source code
- Keep READMEs concise — prefer 30-60 lines. The goal is a quick mental model, not exhaustive documentation
- Write for a developer who is new to the package — they should finish reading with a clear picture of what it does and why, ready to dive into code with the right mental model
