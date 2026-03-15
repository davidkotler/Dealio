# Template: `docs/services/{name}/data-model/`

> Documents the service's persistence layer, schema decisions, and access patterns.

## When to Update

- New entities or tables added
- Schema changes (new columns, constraints, indexes)
- Access patterns changed or added
- Storage engine or schema management approach changed
- Data lifecycle policies changed

## Template

```markdown
# {Service Name} — Data Model

## Overview

| Aspect | Details |
|--------|---------|
| **Storage Engine** | {PostgreSQL/DuckDB/DynamoDB/etc.} |
| **Schema Management** | {Alembic migrations / manual / etc.} |
| **Key Design Decision** | {link to ADR if exists} |

## Entities

### {Entity Name}

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| {field} | {type} | {PK, FK, NOT NULL, UNIQUE, etc.} | {purpose or business rule} |

**Access Patterns:**

| Pattern | Query | Frequency | Index |
|---------|-------|-----------|-------|
| {what the app does} | {simplified query} | {hot/warm/cold} | {index name} |

## Schema Evolution

| Date | Change | Migration | ADR |
|------|--------|-----------|-----|
| {date} | {what changed} | {migration file} | {ADR link if applicable} |

## Data Lifecycle

- **Retention:** {how long data is kept}
- **Soft delete:** {yes/no, mechanism}
- **Archival:** {strategy, if any}
```

## Guidelines

- Document the **why** behind schema decisions, not just the schema itself
- Access patterns are critical — they explain why indexes exist and inform future optimization
- Schema evolution provides a history of changes for debugging and migration planning
- Data lifecycle policies should be explicit about retention and deletion
