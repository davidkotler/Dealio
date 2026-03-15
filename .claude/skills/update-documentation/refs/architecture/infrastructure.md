# Template: `docs/architecture/infrastructure.md`

> Documents shared infrastructure components and how services consume them.

## When to Update

- New data store, message broker, or cache added
- New external service integration
- Infrastructure component purpose or consumers changed
- Technology swap (e.g., SQS to Kafka)

## Template

```markdown
# Infrastructure

## Data Stores

| Store | Technology | Purpose | Consumers |
|-------|-----------|---------|-----------|
| {name} | {PostgreSQL/DuckDB/Redis/etc.} | {what it stores} | {which services use it} |

## Message Infrastructure

| Component | Technology | Purpose | Topics/Queues |
|-----------|-----------|---------|---------------|
| {name} | {SQS/SNS/EventBridge/etc.} | {what it does} | {key channels} |

## External Services

| Service | Purpose | Integration Pattern |
|---------|---------|-------------------|
| {name} | {what we use it for} | {how we connect — SDK, REST, webhook} |
```

## Guidelines

- This is the system-level view; per-service infrastructure details go in `docs/services/{name}/infrastructure/`
- Include all consumers for shared components — this is how teams discover dependencies
- External services should note the integration pattern (SDK, REST, webhook, etc.)
- When adding new infrastructure, also check if `technology-stack.md` needs updating
