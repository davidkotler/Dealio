# Template: `docs/cross-cutting/o11y/overview.md`

> Documents system-wide observability conventions: logging, metrics, tracing, dashboards, and alerts.

## When to Update

- New metrics, dashboards, or alert definitions
- New tracing spans added
- Log schema or standard fields changed
- New observability tooling adopted

## Template

```markdown
# Observability

## Logging

| Convention | Details |
|-----------|---------|
| **Library** | {structlog / stdlib / etc.} |
| **Format** | {JSON structured} |
| **Standard Fields** | {list of fields always present — service, trace_id, etc.} |

## Metrics

| Metric | Type | Labels | Purpose |
|--------|------|--------|---------|
| {name} | {counter/histogram/gauge} | {bounded label set} | {what it measures} |

## Tracing

| Span | Service | Purpose |
|------|---------|---------|
| {span name} | {which service} | {what operation it traces} |

## Dashboards & Alerts

| Dashboard/Alert | Type | Purpose | Link |
|-----------------|------|---------|------|
| {name} | {dashboard/alert} | {what it monitors} | {link} |
```

## Guidelines

- Metrics labels must be bounded — never use user IDs, request IDs, or other high-cardinality values
- Standard fields in logging should be consistent across all services
- Tracing spans should cover all cross-service communication and significant I/O operations
- Dashboard links should be concrete and point to the actual dashboards
