# Template: `docs/architecture/integration-patterns.md`

> Documents how services communicate — synchronous and asynchronous paths.

## When to Update

- New sync/async communication path between services
- New event type published or consumed
- Integration pattern changed (e.g., REST to event-driven)
- New external service integration

## Template

```markdown
# Integration Patterns

## Synchronous Communication

| Source | Target | Method | Purpose | Contract |
|--------|--------|--------|---------|----------|
| {caller} | {callee} | {REST/gRPC} | {why this call exists} | {link to OpenAPI spec} |

## Asynchronous Communication

| Publisher | Event | Consumers | Purpose | Contract |
|-----------|-------|-----------|---------|----------|
| {publisher} | {event type} | {list of consumers} | {why this event exists} | {link to AsyncAPI spec} |

## Event Flow Diagrams

{Mermaid sequence or flow diagrams for key async workflows}
```

## Guidelines

- Every cross-service call (sync or async) should appear in one of the tables
- Link to the actual OpenAPI/AsyncAPI specs — these docs provide context, specs are the contract
- Event flow diagrams should cover multi-step async workflows where the sequence matters
- When adding a new integration path, check if it creates circular dependencies
