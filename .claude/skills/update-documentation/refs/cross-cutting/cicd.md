# Template: `docs/cross-cutting/cicd/overview.md`

> Documents CI/CD pipeline stages, quality gates, and deployment flow.

## When to Update

- Pipeline stages added or changed
- New quality gates introduced
- Deployment strategy changed
- New CI/CD tooling adopted

## Template

```markdown
# CI/CD Pipeline

## Pipeline Stages

| Stage | Trigger | What It Does | Failure Action |
|-------|---------|-------------|----------------|
| {stage} | {on PR / on merge / manual} | {what runs} | {what happens on failure} |

## Quality Gates

| Gate | Tool | Threshold | Where |
|------|------|-----------|-------|
| {gate name} | {tool} | {pass criteria} | {CI step or hook} |

## Deployment Flow

{Mermaid diagram showing the deployment pipeline from merge to production}
```

## Guidelines

- Every quality gate should have a clear pass/fail threshold
- Failure actions should explain what happens — auto-block, notify, or advisory
- The deployment flow diagram should show the full path from merge to production including rollback points
- When adding new stages, update the trigger chain so ordering is clear
