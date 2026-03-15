---
name: diagram-architecture
description: |
  Generate Mermaid.js architecture diagrams that communicate system structure, component boundaries,
  integration patterns, data models, data flow, infrastructure, and architectural decisions. Use
  whenever the user asks to "draw", "diagram", "visualize", "illustrate", or "show" architecture,
  system design, data flow, infrastructure, or component interactions. Also use when producing
  design artifacts (HLD, LLD, ADRs) that need embedded diagrams, when documenting API flows or
  event-driven interactions, when modeling database schemas or domain entities, or when creating
  deployment/infrastructure topology views. If a task involves architecture documentation and a
  visual would help communicate the design, use this skill.
---

# Architecture Diagram Generation

Generate Mermaid diagrams that answer specific architectural questions with clarity, consistency,
and appropriate detail. The goal is communication — every diagram should help someone understand
something about the system that words alone cannot convey as effectively.

## Core Principle: One Diagram, One Question

A diagram should answer exactly one question for one audience. When you catch yourself cramming
multiple concerns into a single diagram, split it. The C4 model's zoom levels exist because
"show me everything" produces diagrams that show nothing clearly.

---

## Step 1: Identify What to Communicate

Before writing any Mermaid syntax, determine:

| Question | Determines |
|----------|-----------|
| **What architectural question does this answer?** | Diagram type |
| **Who will read this?** | Detail level |
| **What abstraction level?** | Scope and granularity |
| **Structure or behavior?** | Structural vs. behavioral diagram |

### Diagram Selection Guide

| You want to show... | Use | Keyword |
|---------------------|-----|---------|
| System landscape + external actors | C4 Context or Flowchart | `C4Context` / `flowchart` |
| Major technical building blocks | C4 Container or Block Diagram | `C4Container` / `block-beta` |
| Internal structure of a service | C4 Component | `C4Component` |
| Runtime API/service interaction | Sequence Diagram | `sequenceDiagram` |
| Numbered runtime flow (use case) | C4 Dynamic | `C4Dynamic` |
| Database schema / data model | ER Diagram | `erDiagram` |
| Domain model / class structure | Class Diagram | `classDiagram` |
| Object lifecycle / workflow states | State Diagram | `stateDiagram-v2` |
| Deployment / infrastructure | C4 Deployment or Architecture | `C4Deployment` / `architecture-beta` |
| Data pipeline / flow quantities | Sankey or Flowchart | `sankey-beta` / `flowchart` |
| Decision rationale | Flowchart (decision tree) | `flowchart` |
| Project timeline / migration plan | Gantt or Timeline | `gantt` / `timeline` |
| Branching strategy | Git Graph | `gitGraph` |
| Technology comparison | Quadrant or Radar | `quadrantChart` / `radar` |
| Brainstorming / knowledge map | Mindmap | `mindmap` |

### Audience-Based Selection

| Audience | Show them | Avoid |
|----------|-----------|-------|
| Executives / stakeholders | C4 Context, User Journey, Timeline | Class diagrams, ER diagrams |
| Architects | C4 Container/Component, Sequence, State | Implementation details |
| Developers | Sequence, Class, ER, State | High-level overviews they already know |
| DevOps / SRE | C4 Deployment, Architecture-beta, Flowchart | Domain model details |
| Database teams | ER Diagram, Class Diagram | Deployment topology |

---

## Step 2: Compose the Diagram

### Structural Conventions

**Node IDs**: Short, camelCase, self-documenting — `orderSvc`, `paymentDB`, `authGW`. Never use
generic `A`, `B`, `C`.

**Display names**: Human-readable text in brackets — `orderSvc[Order Service]`. The ID is for
diagram logic; the display name is for humans.

**Edge labels**: Verb phrases describing intent + protocol/technology:
- `-->|"Reads orders via"|` (intent)
- `-->|REST/HTTPS|` (protocol)
- `-->|"Publishes OrderCreated"|` (event name)

Unlabeled arrows are architectural debt. Every connection should describe what flows across it.

**Direction**:
- `LR` (left-to-right): Data flows, pipelines, request chains — reads like a sentence
- `TD`/`TB` (top-down): Hierarchies, layered architectures, call stacks
- One direction per diagram, consistently

**Visual Clarity** — these matter more than you think for readability:
- Minimize edge crossings by ordering node declarations to match the flow direction.
  Mermaid lays out nodes in declaration order — put upstream nodes first, downstream last.
- Keep total visible nodes under 15 for flowcharts. When tempted to show internal details
  (pipeline steps, individual tables, adapter implementations), ask: does this level of
  detail serve the reader, or should it be a separate zoom-in diagram?
- Avoid `graph TB` with many subgraphs — it produces dense vertical layouts with crossing
  lines. Prefer `flowchart LR` for service integration views and `flowchart TB` only for
  strict layered hierarchies.

### Shape Conventions

| Component Type | Shape | Example |
|---------------|-------|---------|
| Service / process | Rectangle | `svc[Service Name]` |
| API endpoint / terminal | Stadium | `api([API Gateway])` |
| Database / storage | Cylinder | `db[(PostgreSQL)]` |
| Decision point | Diamond | `check{Valid?}` |
| External system | Rectangle (styled) | `ext[External]:::external` |
| Message queue / event bus | Asymmetric or Cylinder | `queue>Event Bus]` or `queue[(Kafka)]` |
| Subprocess / interface | Subroutine | `port[[Repository Port]]` |

### Color Conventions

Apply consistent semantic colors using `classDef`:

```
classDef service fill:#4A90D9,stroke:#2E5C8A,color:#fff
classDef database fill:#2E86C1,stroke:#1B4F72,color:#fff
classDef external fill:#999999,stroke:#666666,color:#fff
classDef queue fill:#F5A623,stroke:#C68A1A,color:#fff
classDef user fill:#27AE60,stroke:#1E8449,color:#fff
classDef critical fill:#E74C3C,stroke:#C0392B,color:#fff
```

Pair colors with distinct shapes — never rely on color alone for meaning.

### Size Limits

| Diagram Type | Max Elements | If exceeded |
|-------------|-------------|-------------|
| Flowchart | 15–20 nodes | Split into sub-diagrams |
| Sequence | 6–8 participants | Split into separate use case diagrams |
| C4 Context | 5–8 elements | You're probably including too much detail |
| ER Diagram | 8–12 entities | Split by bounded context |
| Class Diagram | 8–10 classes | Split by aggregate or module |
| State Diagram | 10–12 states | Use composite states to hide internal complexity |

### State Diagram Readability

State diagrams become unreadable fast. Follow these rules to keep them clear:

- **Use `direction LR`** — left-to-right flow gives readers a clear start (left) to end (right).
  Without explicit direction, Mermaid renders states in a dense vertical cluster.
- **Declare states in flow order** — Mermaid positions states by declaration order. Declare
  the happy path first (top-to-bottom in source = left-to-right in diagram), then add
  error/cancellation paths after.
- **Use composite states** to group related sub-flows (e.g., payment processing internals)
  rather than exposing every sub-state at the top level.
- **Add `note` directives** for business rules directly on the diagram — don't relegate
  them to separate markdown. The diagram should be self-contained.
- **Limit to 10-12 visible states** at the top level. If you have more, either use composite
  states to hide internals or split into separate diagrams per phase.

---

## Step 3: Apply Architecture Patterns

When the diagram involves a recognized architecture pattern, consult the pattern templates in
[refs/architecture-patterns.md](refs/architecture-patterns.md) for proven layouts:

- **Microservices topology** — Subgraph layers (clients, gateway, services, data)
- **Event-driven / CQRS** — Command/query path separation with event bus
- **Hexagonal / Ports & Adapters** — Concentric layers with port interfaces
- **Data flow pipeline** — Source → Processing → Storage → Consumption
- **Saga / choreography** — Sequence diagrams with compensation flows
- **API Gateway pattern** — Fan-out from gateway to backend services

---

## Step 4: Multi-Diagram Documentation Sets

For comprehensive architecture documentation, produce complementary diagrams at different
abstraction levels. A typical set for a microservices system:

| Diagram | Type | Lives In | Audience |
|---------|------|----------|----------|
| System Context | C4Context or Flowchart | Repo root README or `docs/architecture/` | Everyone |
| Container / Service Map | C4Container or Flowchart | `docs/architecture/` | Architects, leads |
| Component Internals | C4Component | Service-level README | Developers |
| Key Flows | sequenceDiagram | `docs/flows/` or design docs | Developers |
| Data Model | erDiagram | `docs/data/` or alongside migrations | Developers, DBAs |
| Deployment Topology | C4Deployment / architecture-beta | `docs/infrastructure/` | DevOps, SRE |
| Entity Lifecycles | stateDiagram-v2 | Service docs | Developers |

### Progressive Disclosure (C4 Zoom)

Start broad, zoom in where detail matters:

```
C4 Context (whole system)
  └─► C4 Container (inside the system)
       └─► C4 Component (inside a container)
            └─► classDiagram / erDiagram (code-level)
```

At each level, add a sequence diagram for key runtime behavior.

---

## Step 5: Quality Checklist

Before finalizing any diagram:

- [ ] **Title present** — Every diagram has a descriptive title (via `title` or comment)
- [ ] **All edges labeled** — No unlabeled arrows; include intent/protocol
- [ ] **Element count within limits** — Under 20 nodes for flowcharts, 8 for sequences
- [ ] **Consistent naming** — Same naming convention throughout (camelCase IDs, readable display names)
- [ ] **Consistent styling** — `classDef` used for semantic colors, not inline `style` everywhere
- [ ] **Single concern** — Answers one question, not three
- [ ] **Correct diagram type** — Structure shown with structural diagrams, behavior with behavioral
- [ ] **Accessibility** — `accTitle` and `accDescr` included for SVG accessibility
- [ ] **Renders correctly** — Valid Mermaid syntax that GitHub/GitLab will render
- [ ] **Comments explain why** — `%%` comments document architectural decisions in the source

---

## Syntax Reference

For complete syntax details of each diagram type (node shapes, arrow types, C4 elements,
ER notation, interaction fragments, styling), consult:

- [refs/syntax-reference.md](refs/syntax-reference.md) — Full syntax for all diagram types
- [refs/architecture-patterns.md](refs/architecture-patterns.md) — Ready-to-adapt pattern templates

Read the relevant section based on which diagram type you're generating. You don't need to read
the entire reference — just the section for the diagram type you're about to write.

---

## Common Mistakes to Avoid

| Mistake | Why it hurts | Fix |
|---------|-------------|-----|
| One mega-diagram | Communicates nothing clearly | Split by abstraction level |
| Generic node IDs (`A`, `B`) | Source text is unreadable | Use semantic IDs (`orderSvc`) |
| Unlabeled edges | Reader guesses what flows | Label with intent + protocol |
| Wrong diagram type | Structure shown as sequence, behavior as flowchart | Match type to question |
| Inconsistent colors | Reader can't build mental model | Use `classDef` with semantic palette |
| Too many elements | Visual noise | Decompose, follow size limits |
| Missing context | "What system is this?" | Add title, notes, comments |
| Using `end` as node text | Breaks subgraph parsing | Capitalize or quote it |
| Mixing concerns in edges | Data flow AND control flow | One relationship type per diagram |
| Multiple key markers in ER (`FK UK`) | Parse error — Mermaid allows only one per attribute | Pick one marker, note the other in comment |
| State diagram without `direction` | Dense vertical cluster, hard to follow | Add `direction LR` for left-to-right readability |
| Flat state diagram with 15+ states | Unreadable pile, no visual grouping | Use composite states, limit to 10-12 top-level |
| `graph TB` for integration views | Too many crossing lines, messy | Use `flowchart LR` for service topology |
