# Template: `docs/architecture/technology-stack.md`

> Documents technology choices and the reasoning behind them.

## When to Update

- New technology or framework adopted
- Significant version upgrade
- New shared library added to the monorepo
- Technology replaced or deprecated

## Template

```markdown
# Technology Stack

## Core Technologies

| Technology | Version | Purpose | ADR |
|-----------|---------|---------|-----|
| {tech} | {version} | {why we use it} | {link to ADR if exists} |

## Key Libraries

| Library | Purpose | Package |
|---------|---------|---------|
| {name} | {what it does for us} | {package path in monorepo or pypi name} |
```

## Guidelines

- Every technology choice should link to its ADR if one exists
- Include version numbers — they matter for compatibility and upgrade planning
- Key libraries are monorepo shared libs (`libs/`) and critical third-party dependencies
- When a technology is deprecated, mark it with a note rather than removing it
