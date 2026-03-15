# Template: `docs/services/{name}/api/`

> Operational context for the service's API. The OpenAPI spec is the contract source of truth — these docs add operational context.

## When to Update

- New API endpoints added
- Contract changes (request/response models)
- New consumers discovered
- Endpoints deprecated
- Auth or rate limiting changes

## Template

```markdown
# {Service Name} — API Documentation

## Overview

- **Base URL:** {base path}
- **Authentication:** {auth mechanism required}
- **Rate Limits:** {if applicable}
- **Versioning:** {strategy — URL path, header, etc.}
- **OpenAPI Spec:** `services/{name}/specs/openapi/v1.yaml`

## Endpoints Summary

| Method | Path | Purpose | Auth Required |
|--------|------|---------|---------------|
| {GET/POST/etc.} | {/path} | {what it does} | {yes/no} |

## Known Consumers

| Consumer | Endpoints Used | Notes |
|----------|---------------|-------|
| {service or client name} | {which endpoints} | {any special considerations} |

## Deprecation Notices

{List any deprecated endpoints with migration guidance and sunset dates}
```

## Guidelines

- Don't duplicate the OpenAPI spec — these docs provide context the spec can't (consumers, operational notes, deprecation timelines)
- Known consumers help with impact analysis before making breaking changes
- For event-driven services, add an equivalent `asyncapi.md` with ordering guarantees, idempotency, and retry behavior
- Deprecation notices should include sunset dates and migration paths
