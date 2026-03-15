# Template: `docs/architecture/component-boundaries.md`

> Documents service boundaries, bounded contexts, and what each context owns.

## When to Update

- New bounded context or service introduced
- Service responsibilities changed
- New domain boundaries defined
- Context relationships changed (partnerships, customer-supplier, etc.)

## Template

```markdown
# Component Boundaries

## Bounded Contexts

### {Context Name}

- **Owns:** {data, behavior, and contracts this context is responsible for}
- **Service(s):** {which service(s) implement this context}
- **Public interface:** {API endpoints, events published, shared contracts}
- **Dependencies:** {what this context depends on from other contexts}

## Context Map

{Mermaid diagram showing contexts and their relationships — partnerships, customer-supplier,
conformist, anticorruption layers, shared kernel, etc.}

## Boundary Rules

- {Rule about what crosses boundaries and what doesn't}
```

## Guidelines

- Each bounded context should explicitly state what it owns and what it does NOT own
- The context map diagram is critical — use DDD relationship types (Shared Kernel, Customer-Supplier, Conformist, ACL, etc.)
- When adding a new context, also update relationships with existing contexts
- Boundary rules capture decisions about data ownership, event direction, and synchronous vs. async
