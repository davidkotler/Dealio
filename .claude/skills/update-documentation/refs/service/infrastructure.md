# Template: `docs/services/{name}/infrastructure/`

> Documents the service's infrastructure dependencies and deployment configuration.

## When to Update

- New infrastructure dependency added (database, cache, queue, external API)
- Deployment configuration changed (Helm values, scaling, environments)
- Environment-specific settings changed
- Connection pool, timeout, or other operational config changed

## Template

```markdown
# {Service Name} — Infrastructure

## Dependencies

| Dependency | Type | Configuration | Notes |
|-----------|------|---------------|-------|
| {name} | {database/cache/queue/external API} | {key config — connection pool, timeout, etc.} | {operational notes} |

## Deployment

| Aspect | Details |
|--------|---------|
| **Helm Chart** | `services/{name}/deploy/k8s/` |
| **Cloud Resources** | `services/{name}/deploy/cloud/` |
| **Environments** | {which environments this service runs in} |
| **Scaling** | {HPA config, min/max replicas} |

## Environment-Specific Configuration

| Setting | Dev | Staging | Pre-prod | Prod |
|---------|-----|---------|----------|------|
| {setting} | {value} | {value} | {value} | {value} |
```

## Guidelines

- Configuration details should include operational values (pool sizes, timeouts, batch sizes)
- Environment-specific table helps operations teams understand config differences
- Link to the actual Helm chart and Pulumi code for full details
- This is per-service infrastructure; system-level infrastructure goes in `docs/architecture/infrastructure.md`
