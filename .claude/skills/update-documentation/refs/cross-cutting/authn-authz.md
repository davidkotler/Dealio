# Template: `docs/cross-cutting/authn-authz/`

> Documents authentication flows, authorization models, and multi-tenancy isolation.

## When to Update

- New auth flow introduced (e.g., API key, OAuth, service-to-service)
- Permission model changed
- Role definitions added or modified
- Multi-tenancy isolation approach changed
- New enforcement points added

## Template

```markdown
# Authentication & Authorization

## Authentication

| Flow | Mechanism | Where Enforced |
|------|-----------|----------------|
| {flow name} | {JWT / API key / OAuth / etc.} | {middleware / guard / gateway} |

## Authorization

| Resource | Permission Model | Where Enforced |
|----------|-----------------|----------------|
| {resource} | {RBAC / ABAC / tenant isolation} | {decorator / middleware / service} |

## Multi-Tenancy

| Aspect | Mechanism |
|--------|-----------|
| **Tenant Resolution** | {how tenant context is established} |
| **Data Isolation** | {row-level security / separate schemas / partition key} |
| **Cross-Tenant Prevention** | {how cross-tenant access is prevented} |
```

## Guidelines

- Authentication flows should describe where enforcement happens (middleware, gateway, decorator)
- Authorization should be documented per-resource, not per-role
- Multi-tenancy isolation is critical — document every layer of defense
- Reference the relevant ADR for auth architecture decisions
