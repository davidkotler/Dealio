# Mermaid Syntax Reference for Architecture Diagrams

Quick-access syntax for each diagram type. Jump to the section you need.

## Table of Contents

1. [Flowcharts](#flowcharts)
2. [C4 Diagrams](#c4-diagrams)
3. [Sequence Diagrams](#sequence-diagrams)
4. [Class Diagrams](#class-diagrams)
5. [ER Diagrams](#er-diagrams)
6. [State Diagrams](#state-diagrams)
7. [Architecture Diagrams (Beta)](#architecture-diagrams)
8. [Block Diagrams](#block-diagrams)
9. [Other Diagram Types](#other-diagram-types)
10. [Configuration & Styling](#configuration--styling)

---

## Flowcharts

**Keyword**: `flowchart` followed by direction (`TD`, `LR`, `BT`, `RL`)

### Node Shapes

| Shape | Syntax | Use For |
|-------|--------|---------|
| Rectangle | `A[text]` | Services, processes |
| Rounded | `A(text)` | Generic components |
| Stadium/Pill | `A([text])` | Terminals, API endpoints |
| Cylinder | `A[(text)]` | Databases, storage |
| Circle | `A((text))` | Actors, endpoints |
| Diamond | `A{text}` | Decisions |
| Hexagon | `A{{text}}` | Preparation steps |
| Subroutine | `A[[text]]` | Subprocesses, interfaces, ports |
| Double circle | `A(((text)))` | Stop/end points |
| Parallelogram | `A[/text/]` | Input/output |
| Asymmetric | `A>text]` | Signals, events, messages |
| Trapezoid | `A[/text\]` | Manual processes |

Since v11.3.0, expanded shape syntax: `A@{ shape: cloud }` — adds `cloud`, `document`, `bolt`,
`flag`, `hourglass`, `fork`/`join`, `text` blocks, and icons via `@{ icon: "fa:camera" }`.

### Edge Types

| Style | Syntax | With text |
|-------|--------|-----------|
| Solid arrow | `-->` | `-- text -->` or `-->\|text\|` |
| Dotted arrow | `-.->` | `-. text .->` |
| Thick arrow | `==>` | `== text ==>` |
| No arrow | `---` | `--- text ---` |
| Circle end | `--o` | |
| Cross end | `--x` | |
| Bidirectional | `<-->`, `o--o`, `x--x` | |
| Invisible | `~~~` | For layout control |

Extra dashes increase length: `---->` spans 2 ranks. Fan-out: `A --> B & C & D`.

### Subgraphs

```
flowchart LR
  subgraph name["Display Name"]
    direction TB
    A[Node] --> B[Node]
  end
```

Subgraphs nest to arbitrary depth. Style with `style subgraphId fill:#color`.
Each subgraph can have its own `direction` statement.

### Styling

```
classDef styleName fill:#hex,stroke:#hex,color:#hex,stroke-width:2px
class nodeId1,nodeId2 styleName
A[Node]:::styleName
style nodeId fill:#hex
linkStyle 0,1,2 stroke:#hex,stroke-width:2px
```

Since v11.10.0, named edge IDs: `A e1@--> B` enable per-edge styling and animations.

### Markdown in Labels

```
A["`**Bold Title**
  Description line
  *Technology*`"]
```

Wrap in `` "`...`" `` for markdown support (bold, italic, auto line wrap).

---

## C4 Diagrams

**Keywords**: `C4Context`, `C4Container`, `C4Component`, `C4Dynamic`, `C4Deployment`

C4 status in Mermaid is experimental — fixed CSS styling, limited layout control.

### Elements

| Level | Elements |
|-------|----------|
| Context | `Person(alias, "Name", "Desc")`, `System(alias, "Name", "Desc")`, `System_Ext()`, `SystemDb()`, `SystemQueue()` |
| Container | `Container(alias, "Name", "Tech", "Desc")`, `ContainerDb()`, `ContainerQueue()`, plus `_Ext` variants |
| Component | `Component(alias, "Name", "Tech", "Desc")`, `ComponentDb()`, `ComponentQueue()` |
| Deployment | `Deployment_Node(alias, "Name", "Tech")`, `Node()` |

### Boundaries

```
System_Boundary(alias, "Name") { ... }
Container_Boundary(alias, "Name") { ... }
Enterprise_Boundary(alias, "Name") { ... }
```

### Relationships

```
Rel(from, to, "label", "technology")
Rel_U(from, to, "label")    %% upward
Rel_D(from, to, "label")    %% downward
Rel_L(from, to, "label")    %% left
Rel_R(from, to, "label")    %% right
BiRel(from, to, "label")    %% bidirectional
```

### Layout Control

```
UpdateLayoutConfig($c4ShapeInRow="3", $c4BoundaryInRow="1")
UpdateRelStyle(from, to, $textColor="red", $lineColor="blue", $offsetX="-40")
UpdateElementStyle(alias, $fontColor="red", $bgColor="blue", $borderColor="green")
```

### C4 Best Practices

- Always include `title` to clarify level and system
- Use `_Ext` suffixes for anything outside your boundary
- Context diagram: 5-8 elements max
- Include technology in Container/Component (third parameter)
- Include protocol on all `Rel()` calls
- Statement order controls layout (rearrange for better positioning)

---

## Sequence Diagrams

**Keyword**: `sequenceDiagram`

### Participants

```
participant A as Alias Name
actor U as User
```

Stereotypes: `participant`, `actor`, `boundary`, `control`, `entity`, `database`, `collections`, `queue`.

Group with `box`:
```
box rgba(0,0,255,.1) Backend Services
  participant Auth
  participant Orders
end
```

### Arrow Types

| Arrow | Meaning |
|-------|---------|
| `->>` | Synchronous call (solid, filled arrow) |
| `-->>` | Synchronous return (dashed, filled arrow) |
| `-x` | Async fire-and-forget (solid, cross) |
| `-)` | Async message (solid, open arrow) |
| `--)` | Async response (dashed, open arrow) |

### Activation

```
A->>+B: call    %% activates B
B-->>-A: reply  %% deactivates B
```

Or explicit: `activate B` / `deactivate B`. Activations stack for nested calls.

### Interaction Fragments

| Fragment | Syntax | Use For |
|----------|--------|---------|
| Conditional | `alt...else...end` | If/else branching |
| Optional | `opt...end` | Optional execution |
| Loop | `loop condition...end` | Repeated interactions |
| Parallel | `par...and...end` | Concurrent operations |
| Critical | `critical...option...end` | Error-handling paths |
| Break | `break...end` | Early exit |

### Notes & Highlights

```
Note right of A: text
Note over A,B: shared note
rect rgb(200,220,255)
  A->>B: highlighted call
end
```

### Features

- `autonumber` — Sequential message numbers
- `create participant B` — Creates participant mid-flow (v10.3.0+)
- `destroy B` — Destroys participant

### Best Practices

- One use case per diagram
- Always use aliases: `participant US as User Service`
- Use `autonumber` for review discussions
- Limit to 6-8 participants
- Use `activate`/`deactivate` to show latency bottlenecks
- Use `alt`/`else` for error paths, not separate diagrams

---

## Class Diagrams

**Keyword**: `classDiagram`

### Class Definition

```
classDiagram
    direction LR

    class ClassName {
        +String publicField
        -int privateField
        #float protectedField
        ~String packageField
        +publicMethod() ReturnType
        -privateMethod(param Type) void
        +abstractMethod()* void
        +staticMethod()$ String
    }
```

Visibility: `+` public, `-` private, `#` protected, `~` package.
Classifiers: `*` abstract, `$` static.
Generics: `List~T~` renders as `List<T>`.

### Annotations

```
class Interface {
    <<interface>>
}
class AbstractClass {
    <<abstract>>
}
class MyEnum {
    <<enumeration>>
    VALUE_A
    VALUE_B
}
```

### Relationships

| Type | Syntax | Meaning |
|------|--------|---------|
| Inheritance | `<\|--` | "is-a" |
| Composition | `*--` | "owns" (lifecycle-dependent) |
| Aggregation | `o--` | "has" (independent lifecycle) |
| Association | `-->` | "uses" |
| Dependency | `..>` | "depends on" |
| Realization | `..\|>` | "implements" |

Cardinality: `Customer "1" --> "*" Order : places`
Namespaces: `namespace Domain { class Order }`

---

## ER Diagrams

**Keyword**: `erDiagram`

### Relationships

```
ENTITY_A ||--o{ ENTITY_B : "relationship label"
```

Cardinality markers:
| Symbol | Meaning |
|--------|---------|
| `\|\|` | Exactly one |
| `o\|` | Zero or one |
| `}o` | Zero or many |
| `}\|` | One or many |

Line types: `--` solid (identifying), `..` dashed (non-identifying).

### Attributes

```
ENTITY {
    type name PK "comment"
    type name FK
    type name UK
}
```

Key markers: `PK` (primary key), `FK` (foreign key), `UK` (unique key).

### Syntax Pitfalls

**Only ONE key marker per attribute.** Mermaid's ER parser accepts exactly one of `PK`, `FK`, or
`UK` per attribute line. Combining them (e.g., `uuid product_id FK UK`) causes a parse error.
If an attribute is both a foreign key and has a unique constraint, pick the more important one
for the marker and note the other in the comment:

```
%% CORRECT:
uuid product_id FK "Unique constraint enforced at DB level"

%% WRONG — parse error:
uuid product_id FK UK "One per product"
```

**Comments after attributes** must be quoted strings. Unquoted text after the key marker breaks parsing.

### Best Practices

- Singular nouns for entity names (CUSTOMER not CUSTOMERS)
- UPPERCASE entity names
- Relationship labels read from first entity's perspective
- Logical models: omit FKs (relationships convey associations)
- Physical models: include FKs, types, constraints
- Only one key marker (PK/FK/UK) per attribute — see Syntax Pitfalls above

---

## State Diagrams

**Keyword**: `stateDiagram-v2`

```
stateDiagram-v2
    [*] --> Idle
    Idle --> Processing : event
    state Processing {
        [*] --> Validating
        Validating --> Executing
        Executing --> [*]
    }
    Processing --> Done : success
    Processing --> Error : failure
```

Features:
- `[*]` — Start/end pseudostate
- Composite (nested) states
- `<<choice>>` — Decision pseudostate
- `<<fork>>` / `<<join>>` — Parallel states
- `--` separator for concurrent regions
- `note right of State : text`

### Best Practices

- **Always set `direction LR`** — without it, states pile up vertically and become unreadable.
  Left-to-right gives a clear start (left) to end (right) visual flow.
- Declare states in flow order: happy path first, then error/cancellation branches
- One entity lifecycle per diagram
- Use composite states to hide internal complexity (10-12 top-level states max)
- Include transition labels (trigger events)
- Use `note` directives for business rules directly in the diagram

---

## Architecture Diagrams

**Keyword**: `architecture-beta` (v11.1.0+)

```
architecture-beta
    group cloud(cloud)[AWS Cloud]
    group vpc(cloud)[VPC] in cloud

    service lb(server)[Load Balancer] in vpc
    service api(server)[API Server] in vpc
    service db(database)[PostgreSQL] in vpc

    lb:R --> L:api
    api:B --> T:db
```

Icons: `cloud`, `database`, `server`, `internet`, `disk`, plus 200,000+ via iconify.
Edge directions: `L`, `R`, `T`, `B`.
Groups nest: `group name(icon)[Label] in parent`.
Junctions for multi-way connections.

---

## Block Diagrams

**Keyword**: `block-beta`

```
block-beta
    columns 3
    space A["Service A"] space
    B["Service B"] C["Service C"] D["Service D"]
    E[("Database")] F[("Cache")] G[("Queue")]

    A --> B & C & D
    B --> E
    C --> F
    D --> G
```

`columns N` sets grid, `space` creates empty cells, `space:N` spans N columns.

---

## Other Diagram Types

### Gantt Charts
```
gantt
    title Timeline
    dateFormat YYYY-MM-DD
    section Phase 1
        Task A :done, a1, 2025-01-01, 30d
        Task B :active, a2, after a1, 15d
    section Phase 2
        Task C :b1, after a2, 45d
        Milestone :milestone, after b1, 0d
```

### Git Graph
```
gitGraph
    commit id: "Initial"
    branch develop
    commit id: "Feature"
    checkout main
    merge develop id: "Release" tag: "v1.0"
```

### Mindmap
```
mindmap
    root((Topic))
        Branch A
            Leaf 1
            Leaf 2
        Branch B
```

### Timeline
```
timeline
    title History
    2020 : Event A : Event B
    2021 : Event C
```

### Pie Chart
```
pie title Distribution
    "Category A" : 40
    "Category B" : 35
    "Category C" : 25
```

### Quadrant Chart
```
quadrantChart
    title Assessment
    x-axis Low --> High
    y-axis Low --> High
    quadrant-1 Do First
    quadrant-2 Plan
    quadrant-3 Quick Win
    quadrant-4 Skip
    Item A: [0.3, 0.9]
    Item B: [0.8, 0.4]
```

### Sankey Diagram
```
sankey-beta
    Source A,Process,100
    Process,Output A,60
    Process,Output B,40
```

### Radar Chart
```
radar
    title Comparison
    axis1: "Metric A" ; axis2: "Metric B" ; axis3: "Metric C"
    "Option 1" : [4, 3, 5]
    "Option 2" : [3, 5, 2]
```

---

## Configuration & Styling

### Frontmatter (Preferred)

```
---
config:
    theme: default|neutral|dark|forest|base
    look: classic|handDrawn
    layout: dagre|elk
---
```

### Theme Customization (base theme only)

```
---
config:
    theme: base
    themeVariables:
        primaryColor: "#E8F4FD"
        primaryBorderColor: "#2E75B6"
        primaryTextColor: "#1A1A1A"
        lineColor: "#5B9BD5"
        secondaryColor: "#FFF3E0"
        tertiaryColor: "#E8F5E9"
---
```

### Inline Directive (Legacy)

```
%%{init: {'theme': 'dark'}}%%
```

### classDef + Semantic Styling

```
classDef service fill:#4A90D9,stroke:#2E5C8A,color:#fff
classDef database fill:#2E86C1,stroke:#1B4F72,color:#fff
classDef external fill:#999999,stroke:#666666,color:#fff
classDef queue fill:#F5A623,stroke:#C68A1A,color:#fff
classDef user fill:#27AE60,stroke:#1E8449,color:#fff
classDef critical fill:#E74C3C,stroke:#C0392B,color:#fff

class nodeA,nodeB service
class dbNode database
```

### Edge Styling

```
linkStyle 0 stroke:#ff3,stroke-width:4px
linkStyle default stroke:#666,stroke-width:1px
```

### Curve Options

```
%%{init: {"flowchart": {"curve": "monotoneY"}}}%%
```

Options: `basis`, `linear`, `monotoneY` (recommended), `natural`, `step`, `stepBefore`, `stepAfter`.

### Accessibility

```
accTitle: Diagram Title
accDescr: Description for screen readers
```

### Layout: ELK for Complex Diagrams

```
---
config:
    layout: elk
---
```

Use ELK when dagre produces too many edge crossings or overlapping nodes.

### Hand-Drawn Look

```
---
config:
    look: handDrawn
    handDrawnSeed: 42
---
```

Signals "this is a draft" — useful for early-stage architecture exploration. Seed `42` for
deterministic rendering, `0` for random variation.
