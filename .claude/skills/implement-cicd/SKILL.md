---
name: implement-cicd
version: 1.0.0
description: |
  Implement production-ready GitHub Actions workflows, reusable workflows, composite actions,
  and CI/CD pipeline configurations with security hardening, caching, and environment promotion.
  Use when creating or modifying: workflow YAML files in .github/workflows/, composite actions
  in .github/actions/, CI pipelines, CD pipelines, release workflows, scheduled maintenance
  workflows, matrix builds, or any GitHub Actions automation.
  Triggers on "create workflow", "add CI", "set up CD", "GitHub Actions", "deploy pipeline",
  "release workflow", "add a workflow", "automate tests", "CI/CD", "workflow_dispatch",
  "reusable workflow", "composite action", or when producing/editing .yml/.yaml files
  in .github/ directories. Also triggers when fixing workflow failures, optimizing pipeline
  speed, adding caching, configuring environments, setting up OIDC, or hardening workflow
  security. Relevant for GitHub Actions, CI/CD, DevOps, deployment automation, YAML pipelines.
---

# CI/CD Implementation

> Implement secure, performant, and maintainable GitHub Actions workflows and CI/CD pipelines.

## Quick Reference

| Aspect | Details |
|--------|---------|
| **Invokes** | `implement/docker`, `review/cicd` |
| **Invoked By** | `implement/kubernetes`, `implement/python`, `implement/react` |
| **Key Tools** | Write, Edit, Bash(actionlint) |

---

## Core Workflow

1. **Analyze**: Examine `.github/workflows/` and `.github/actions/` for existing patterns, naming conventions, and reuse opportunities
2. **Classify**: Determine pipeline type—CI, CD, release, utility, or scheduled—and select the matching pattern from [refs/patterns.md](refs/patterns.md)
3. **Scaffold**: Build workflow structure following the Decision Tree below
4. **Harden**: Apply every item from the Security Baseline (Section below)
5. **Optimize**: Add caching, concurrency controls, path filters, and parallelism
6. **Validate**: Run `actionlint` on every workflow file before completion
7. **Chain**: Invoke `review/cicd` for comprehensive review after implementation

---

## Decision Tree

```
User Request
    │
    ├─► New CI pipeline?
    │     └─► Pattern: Standard CI (lint → test → build)
    │           └─► Add: concurrency, path filters, matrix if multi-version
    │
    ├─► New CD pipeline?
    │     └─► Pattern: Environment Promotion (staging → production)
    │           └─► Add: OIDC auth, environment protection, approval gates
    │           └─► Invoke: implement/docker (if container builds needed)
    │
    ├─► Release workflow?
    │     └─► Pattern: Tag-triggered release
    │           └─► Add: artifact attestation, changelog generation
    │
    ├─► Reusable workflow or composite action?
    │     └─► Determine: workflow_call (full jobs) vs composite (shared steps)
    │           └─► Add: typed inputs/outputs, secrets handling, version tags
    │
    ├─► Scheduled / maintenance?
    │     └─► Pattern: Cron-based utility
    │           └─► Add: default branch awareness, failure notifications
    │
    └─► Modify existing workflow?
          └─► Read current file → Identify concern → Apply targeted changes
                └─► Preserve existing patterns and naming conventions
```

---

## Security Baseline

**Apply ALL of these to EVERY workflow. Non-negotiable.**

1. **Permissions**: Set `permissions: {}` at workflow level; grant minimum per-job
2. **Action Pinning**: Pin ALL third-party actions to full commit SHA with version comment
3. **Injection Prevention**: NEVER interpolate untrusted contexts (`github.event.*.title`, `github.event.*.body`, `github.head_ref`) directly in `run:` blocks—assign to `env:` first
4. **OIDC**: Use OpenID Connect for cloud auth (AWS, Azure, GCP) instead of static secrets
5. **Timeouts**: Set `timeout-minutes` on every job (CI: 15-30, deploy: 10-15)
6. **Concurrency**: Add `concurrency` group to CI workflows with `cancel-in-progress: true`; use `cancel-in-progress: false` for deploy workflows
7. **Environments**: Use environment protection rules for production deployments
8. **Dependabot**: Include `.github/dependabot.yml` for GitHub Actions ecosystem updates

```yaml
# ✅ Security baseline template
permissions: {}

jobs:
  build:
    runs-on: ubuntu-24.04
    timeout-minutes: 20
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@a12a3943b4bdde767164f792f33f40b04645d846  # v4.2.2
```

---

## Structural Conventions

| Element | Convention | Example |
|---------|-----------|---------|
| Workflow files | `kebab-case.yml` | `ci-pipeline.yml`, `deploy-production.yml` |
| Workflow names | Title Case, descriptive | `CI Pipeline`, `Deploy Production` |
| Job names | `snake_case` or `kebab-case` | `build_and_test`, `deploy` |
| Step names | Descriptive sentence | `Install dependencies` |
| Secrets | `UPPER_SNAKE_CASE` with prefix | `AWS_PROD_ROLE_ARN` |
| Variables | `UPPER_SNAKE_CASE` | `APP_NAME`, `DEPLOY_REGION` |
| Custom actions | `.github/actions/kebab-case/` | `.github/actions/setup-env/` |
| Environments | Lowercase | `staging`, `production` |

**File organization**: One workflow per concern. Separate CI, CD, release, and utility workflows.

---

## Caching Strategy

Always cache dependencies. Use lock file hashes as cache keys.

```yaml
# Built-in setup action caching (preferred)
- uses: actions/setup-node@1d0ff469b7ec7b3cb9d8673fde0c81c44821de2a  # v4.2.0
  with:
    node-version: '22'
    cache: 'npm'

# Explicit cache (when setup actions lack built-in support)
- uses: actions/cache@5a3ec84eff668545956fd18022155c47e93e2684  # v4.2.3
  with:
    path: ~/.cache/pip
    key: pip-${{ runner.os }}-${{ hashFiles('**/requirements.lock') }}
    restore-keys: pip-${{ runner.os }}-
```

---

## Skill Chaining

| Condition | Invoke | Handoff Context |
|-----------|--------|-----------------|
| Container builds needed | `implement/docker` | Dockerfile path, registry, tagging strategy |
| Kubernetes deployments | `implement/kubernetes` | Manifest paths, environments, rollout strategy |
| Implementation complete | `review/cicd` | Workflow file paths, pipeline type, security checklist |

### Chaining Syntax

```markdown
**Invoking Sub-Skill:** `review/cicd`
**Reason:** Validate security hardening, performance, and structural conventions
**Handoff Context:** Workflow paths: .github/workflows/ci.yml, Pipeline type: CI
```

---

## Patterns & Anti-Patterns

### ✅ Do

- Pin third-party actions to full commit SHAs with version comments
- Use `permissions: {}` at workflow level and grant per-job
- Set explicit `timeout-minutes` on every job
- Use `concurrency` groups to prevent redundant runs
- Cache all cacheable dependencies with lock file hashes
- Use reusable workflows for shared pipeline templates
- Use composite actions for shared step sequences
- Add `if: failure()` notification steps for critical pipelines
- Use path and branch filters to skip irrelevant runs
- Write job summaries to `$GITHUB_STEP_SUMMARY` for visibility
- Prefer `ubuntu-24.04` over `ubuntu-latest` for reproducibility

### ❌ Don't

- Interpolate `github.event.*` contexts directly in `run:` blocks (injection risk)
- Use `actions/checkout@v4` without SHA pinning in production workflows
- Store long-lived cloud credentials as secrets (use OIDC)
- Use `ubuntu-latest` (silently shifts to newer images)
- Skip `timeout-minutes` (default is 6 hours)
- Put CI and CD logic in the same workflow file
- Use YAML anchors (not supported in GitHub Actions)
- Duplicate step sequences across workflows (extract composite actions)
- Use `continue-on-error: true` on security or test steps
- Echo or log secrets, even during debugging

---

## Examples

### Example 1: CI Pipeline with Security Baseline

**Input:** "Create a CI pipeline for a Node.js project"

**Output:**
```yaml
name: CI Pipeline
on:
  push:
    branches: [main]
    paths-ignore: ['docs/**', '**.md']
  pull_request:
    branches: [main]
    paths-ignore: ['docs/**', '**.md']

permissions: {}

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  lint:
    runs-on: ubuntu-24.04
    timeout-minutes: 10
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@a12a3943b4bdde767164f792f33f40b04645d846  # v4.2.2
      - uses: actions/setup-node@1d0ff469b7ec7b3cb9d8673fde0c81c44821de2a  # v4.2.0
        with:
          node-version: '22'
          cache: 'npm'
      - run: npm ci
      - run: npm run lint

  test:
    needs: lint
    runs-on: ubuntu-24.04
    timeout-minutes: 20
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@a12a3943b4bdde767164f792f33f40b04645d846  # v4.2.2
      - uses: actions/setup-node@1d0ff469b7ec7b3cb9d8673fde0c81c44821de2a  # v4.2.0
        with:
          node-version: '22'
          cache: 'npm'
      - run: npm ci
      - run: npm test
```

---

## Deep References

For detailed guidance, load these refs as needed:

- **[patterns.md](refs/patterns.md)**: CI, CD, release, monorepo, reusable workflow, and composite action patterns with complete YAML examples
- **[security-hardening.md](refs/security-hardening.md)**: OIDC setup, fork security, script injection prevention, supply chain security, action allowlisting
- **[troubleshooting.md](refs/troubleshooting.md)**: Common failures, debugging techniques, expression pitfalls, caching issues

---

## Quality Gates

Before completing any CI/CD implementation:

- [ ] `actionlint` passes on all workflow files with zero errors
- [ ] `permissions: {}` set at workflow level with per-job grants
- [ ] All third-party actions pinned to full commit SHAs
- [ ] `timeout-minutes` set on every job
- [ ] `concurrency` group configured on CI workflows
- [ ] No direct interpolation of untrusted contexts in `run:` blocks
- [ ] Caching configured for all dependency installation steps
- [ ] Path/branch filters applied to avoid unnecessary runs
- [ ] OIDC used for cloud authentication (no static credentials)
- [ ] Environment protection rules configured for production deployments
