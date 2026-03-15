# Template: `docs/services/{name}/README.md`

> The service's landing page — purpose, ownership, and quick reference.

## When to Update

- Service purpose or responsibilities changed
- New domain added to or removed from the service
- Dependencies changed significantly
- Data store or API technology changed

## Template

```markdown
# {Service Name}

> {1-2 sentence description of the service's purpose and domain}

## Responsibilities

- {What this service owns}
- {What it does NOT own (explicit boundaries)}

## Quick Reference

| Aspect | Details |
|--------|---------|
| **Package** | `services/{name}/` |
| **Domain(s)** | {bounded contexts this service implements} |
| **API** | {OpenAPI spec location and base URL} |
| **Events** | {AsyncAPI spec location, topics published/consumed} |
| **Data Store** | {database technology and purpose} |
| **Dependencies** | {other services and infrastructure it depends on} |
```

## Guidelines

- The README is the entry point — keep it concise, link to detailed docs
- Explicit "does NOT own" boundaries prevent scope creep
- Quick reference table should always be current — it's what people scan first
- Link to OpenAPI/AsyncAPI specs rather than duplicating contract details
