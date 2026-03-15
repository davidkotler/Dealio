# Template: `docs/architecture/system-overview.md`

> Provides a high-level view of the entire system: what services exist, what each does, and how they relate.

## When to Update

- New service or major component added
- Existing service purpose or domain changed significantly
- Technology stack changed at the system level

## Template

```markdown
# System Overview

> {1-2 sentence description of the system's purpose and scope}

## System Context

{Mermaid context diagram showing the system boundary, external actors, and key interactions}

## Services

| Service | Domain | Purpose | Key Dependencies |
|---------|--------|---------|------------------|
| {name} | {bounded context} | {what it does} | {databases, queues, external APIs} |

## Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| {layer} | {tech} | {why this technology for this layer} |
```

## Guidelines

- Keep the services table comprehensive — every service should be listed
- The context diagram should show the system boundary clearly (what's inside vs. outside)
- Technology stack here is system-level only; per-service details go in service docs
- When updating, add new rows to existing tables rather than restructuring
