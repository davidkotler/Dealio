# Template: `docs/cross-cutting/security/standard.md`

> Documents security standards: input validation, secrets management, and encryption.

## When to Update

- New threat mitigations added
- Input validation patterns changed
- Secrets management approach changed
- Encryption standards updated

## Template

```markdown
# Security Standards

## Input Validation

| Boundary | Validation | Mechanism |
|----------|-----------|-----------|
| {API endpoints / event handlers / etc.} | {what's validated} | {Pydantic / custom / etc.} |

## Secrets Management

| Secret Type | Storage | Access Pattern |
|-------------|---------|---------------|
| {type} | {vault / env var / external-secrets} | {how services access it} |

## Encryption

| Data | At Rest | In Transit |
|------|---------|------------|
| {data type} | {encryption mechanism} | {TLS / mTLS / etc.} |
```

## Guidelines

- Input validation should be documented at every system boundary, not just APIs
- Secrets management should describe the full lifecycle (creation, rotation, access)
- Encryption standards should be explicit about both at-rest and in-transit for each data type
- Reference security ADRs for rationale behind specific choices
