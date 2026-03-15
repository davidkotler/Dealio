# Template: `docs/services/{name}/sli-slo/`

> Documents the service's reliability targets and how they are measured.

## When to Update

- New SLI/SLO definitions added
- Reliability targets changed
- New dashboards or alerts created
- Measurement methodology changed

## Template

```markdown
# {Service Name} — SLIs and SLOs

## Service Level Indicators

| SLI | Definition | Measurement |
|-----|-----------|-------------|
| {name} | {what it measures from user perspective} | {how it's measured — metric query or log pattern} |

## Service Level Objectives

| SLO | Target | Window | Alert Threshold |
|-----|--------|--------|-----------------|
| {name} | {target — e.g., 99.9% availability} | {rolling window} | {when to alert} |

## Dashboards

| Dashboard | URL | Purpose |
|-----------|-----|---------|
| {name} | {link} | {what it shows} |
```

## Guidelines

- SLIs should be defined from the user's perspective, not technical metrics
- SLOs should have explicit alert thresholds — when does the team need to act?
- Dashboard links should point to the actual dashboard, not a search page
- Only update when the feature changes what reliability means for this service
