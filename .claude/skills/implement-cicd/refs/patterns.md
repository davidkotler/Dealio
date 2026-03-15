# CI/CD Patterns Reference

> Extended patterns with complete YAML examples. Load on-demand when implementing specific pipeline types.

---

## 1. Standard CI Pipeline

The foundational build-and-test pattern. Parallelize independent jobs, gate deployments on all checks.

```yaml
name: CI Pipeline
on:
  push:
    branches: [main, develop]
    paths-ignore: ['docs/**', '**.md', '.github/dependabot.yml']
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
    runs-on: ubuntu-24.04
    timeout-minutes: 20
    permissions:
      contents: read
    strategy:
      matrix:
        node: [20, 22]
      fail-fast: false
    steps:
      - uses: actions/checkout@a12a3943b4bdde767164f792f33f40b04645d846  # v4.2.2
      - uses: actions/setup-node@1d0ff469b7ec7b3cb9d8673fde0c81c44821de2a  # v4.2.0
        with:
          node-version: ${{ matrix.node }}
          cache: 'npm'
      - run: npm ci
      - run: npm test

  build:
    needs: [lint, test]
    runs-on: ubuntu-24.04
    timeout-minutes: 15
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@a12a3943b4bdde767164f792f33f40b04645d846  # v4.2.2
      - uses: actions/setup-node@1d0ff469b7ec7b3cb9d8673fde0c81c44821de2a  # v4.2.0
        with:
          node-version: '22'
          cache: 'npm'
      - run: npm ci
      - run: npm run build
      - uses: actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02  # v4.6.2
        with:
          name: dist
          path: dist/
          retention-days: 5
```

### Key Design Decisions

- **`fail-fast: false` on matrix**: Get results from all versions, not just the first failure.
- **`paths-ignore`**: Skip CI for docs-only changes to conserve runner minutes.
- **`lint` and `test` parallel**: Both run independently; `build` waits for both.
- **Artifact upload**: Share build output with downstream CD workflows.

---

## 2. Python CI Pipeline

```yaml
name: CI Pipeline
on:
  push:
    branches: [main]
    paths: ['src/**', 'tests/**', 'pyproject.toml', 'requirements*.txt']
  pull_request:
    branches: [main]
    paths: ['src/**', 'tests/**', 'pyproject.toml', 'requirements*.txt']

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
      - uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065  # v5.6.0
        with:
          python-version: '3.13'
          cache: 'pip'
      - run: pip install ruff ty
      - run: ruff check src/
      - run: ruff format --check src/
      - run: ty src/ --strict

  test:
    runs-on: ubuntu-24.04
    timeout-minutes: 20
    permissions:
      contents: read
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_PASSWORD: test
          POSTGRES_DB: testdb
        ports: ['5432:5432']
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    steps:
      - uses: actions/checkout@a12a3943b4bdde767164f792f33f40b04645d846  # v4.2.2
      - uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065  # v5.6.0
        with:
          python-version: '3.13'
          cache: 'pip'
      - run: pip install -e ".[test]"
      - run: pytest --cov=src --cov-report=xml -v
        env:
          DATABASE_URL: postgresql://postgres:test@localhost:5432/testdb
      - uses: actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02  # v4.6.2
        if: always()
        with:
          name: coverage-report
          path: coverage.xml
```

---

## 3. CD Pipeline with Environment Promotion

Deploy through staging with smoke tests, then promote to production with approval gates.

```yaml
name: Deploy
on:
  push:
    branches: [main]

permissions: {}

concurrency:
  group: deploy-${{ github.ref }}
  cancel-in-progress: false  # Never cancel in-progress deploys

jobs:
  deploy-staging:
    runs-on: ubuntu-24.04
    timeout-minutes: 15
    permissions:
      contents: read
      id-token: write  # OIDC
    environment:
      name: staging
      url: https://staging.example.com
    steps:
      - uses: actions/checkout@a12a3943b4bdde767164f792f33f40b04645d846  # v4.2.2
      - uses: aws-actions/configure-aws-credentials@e3dd6a429d7300a6a4c196c26e071d42e0343502  # v4.0.2
        with:
          role-to-assume: ${{ vars.AWS_STAGING_ROLE_ARN }}
          aws-region: ${{ vars.AWS_REGION }}
      - run: ./scripts/deploy.sh staging

  smoke-test:
    needs: deploy-staging
    runs-on: ubuntu-24.04
    timeout-minutes: 10
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@a12a3943b4bdde767164f792f33f40b04645d846  # v4.2.2
      - run: ./scripts/smoke-test.sh https://staging.example.com

  deploy-production:
    needs: smoke-test
    runs-on: ubuntu-24.04
    timeout-minutes: 15
    permissions:
      contents: read
      id-token: write
    environment:
      name: production
      url: https://example.com
    steps:
      - uses: actions/checkout@a12a3943b4bdde767164f792f33f40b04645d846  # v4.2.2
      - uses: aws-actions/configure-aws-credentials@e3dd6a429d7300a6a4c196c26e071d42e0343502  # v4.0.2
        with:
          role-to-assume: ${{ vars.AWS_PROD_ROLE_ARN }}
          aws-region: ${{ vars.AWS_REGION }}
      - run: ./scripts/deploy.sh production

  notify:
    needs: deploy-production
    if: always()
    runs-on: ubuntu-24.04
    timeout-minutes: 5
    permissions: {}
    steps:
      - name: Notify on failure
        if: needs.deploy-production.result == 'failure'
        env:
          SLACK_WEBHOOK: ${{ secrets.SLACK_WEBHOOK }}
        run: |
          curl -X POST "$SLACK_WEBHOOK" \
            -H 'Content-Type: application/json' \
            -d '{"text":"🚨 Production deploy failed for ${{ github.repository }}@${{ github.sha }}"}'
```

### Key Design Decisions

- **`cancel-in-progress: false`**: Never cancel a deploy mid-flight.
- **OIDC over static secrets**: `id-token: write` enables credential-less cloud auth.
- **Environment protection**: Configure required reviewers on `production` in GitHub Settings.
- **`if: always()` on notify**: Runs regardless of upstream outcomes.

---

## 4. Release Pipeline (Tag-Triggered)

```yaml
name: Release
on:
  push:
    tags: ['v*.*.*']

permissions: {}

jobs:
  release:
    runs-on: ubuntu-24.04
    timeout-minutes: 20
    permissions:
      contents: write
      id-token: write
      attestations: write
    steps:
      - uses: actions/checkout@a12a3943b4bdde767164f792f33f40b04645d846  # v4.2.2
        with:
          fetch-depth: 0  # Full history for changelog
      - uses: actions/setup-node@1d0ff469b7ec7b3cb9d8673fde0c81c44821de2a  # v4.2.0
        with:
          node-version: '22'
          cache: 'npm'
      - run: npm ci
      - run: npm run build

      - name: Create GitHub Release
        uses: softprops/action-gh-release@c95fe1489396fe8a9eb87c0abf8aa5b2ef267fda  # v2.2.1
        with:
          files: dist/*
          generate_release_notes: true

      - name: Attest build provenance
        uses: actions/attest-build-provenance@c074443f1aee8d4aeeae555aebba3282517141b2  # v2.2.3
        with:
          subject-path: dist/*
```

---

## 5. Reusable Workflow (Pipeline Template)

**Definition** (`.github/workflows/reusable-deploy.yml`):

```yaml
name: Reusable Deploy
on:
  workflow_call:
    inputs:
      environment:
        required: true
        type: string
      app-name:
        required: true
        type: string
      version:
        required: true
        type: string
    secrets:
      DEPLOY_KEY:
        required: true
    outputs:
      deploy-url:
        description: "Deployed URL"
        value: ${{ jobs.deploy.outputs.url }}

permissions: {}

jobs:
  deploy:
    runs-on: ubuntu-24.04
    timeout-minutes: 15
    permissions:
      contents: read
      id-token: write
    environment:
      name: ${{ inputs.environment }}
      url: ${{ steps.deploy.outputs.url }}
    outputs:
      url: ${{ steps.deploy.outputs.url }}
    steps:
      - uses: actions/checkout@a12a3943b4bdde767164f792f33f40b04645d846  # v4.2.2
      - id: deploy
        env:
          DEPLOY_KEY: ${{ secrets.DEPLOY_KEY }}
        run: |
          echo "Deploying ${{ inputs.app-name }}@${{ inputs.version }} to ${{ inputs.environment }}"
          echo "url=https://${{ inputs.app-name }}.${{ inputs.environment }}.example.com" >> $GITHUB_OUTPUT
```

**Caller** (`.github/workflows/deploy.yml`):

```yaml
name: Deploy
on:
  push:
    branches: [main]

permissions: {}

jobs:
  staging:
    uses: ./.github/workflows/reusable-deploy.yml
    with:
      environment: staging
      app-name: my-app
      version: ${{ github.sha }}
    secrets:
      DEPLOY_KEY: ${{ secrets.STAGING_DEPLOY_KEY }}

  production:
    needs: staging
    uses: ./.github/workflows/reusable-deploy.yml
    with:
      environment: production
      app-name: my-app
      version: ${{ github.sha }}
    secrets:
      DEPLOY_KEY: ${{ secrets.PROD_DEPLOY_KEY }}
```

### When to Use

- **Reusable workflows**: Full pipeline templates shared across repos (entire jobs with their own runners)
- **Composite actions**: Shared step sequences reused within jobs (run on the caller's runner)

---

## 6. Composite Action (Shared Steps)

**Definition** (`.github/actions/setup-and-test/action.yml`):

```yaml
name: 'Setup and Test'
description: 'Install dependencies and run tests'
inputs:
  node-version:
    description: 'Node.js version'
    required: false
    default: '22'
  test-command:
    description: 'Test command to run'
    required: false
    default: 'npm test'
outputs:
  test-result:
    description: 'Test outcome (pass/fail)'
    value: ${{ steps.test.outputs.result }}
runs:
  using: "composite"
  steps:
    - uses: actions/setup-node@1d0ff469b7ec7b3cb9d8673fde0c81c44821de2a  # v4.2.0
      with:
        node-version: ${{ inputs.node-version }}
        cache: 'npm'
    - run: npm ci
      shell: bash
    - id: test
      run: |
        if ${{ inputs.test-command }}; then
          echo "result=pass" >> $GITHUB_OUTPUT
        else
          echo "result=fail" >> $GITHUB_OUTPUT
          exit 1
        fi
      shell: bash
```

**Usage**:

```yaml
steps:
  - uses: actions/checkout@a12a3943b4bdde767164f792f33f40b04645d846  # v4.2.2
  - uses: ./.github/actions/setup-and-test
    with:
      node-version: '22'
      test-command: 'npm run test:unit'
```

---

## 7. Monorepo with Change Detection

```yaml
name: CI (Monorepo)
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

permissions: {}

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  detect-changes:
    runs-on: ubuntu-24.04
    timeout-minutes: 5
    permissions:
      contents: read
    outputs:
      api: ${{ steps.filter.outputs.api }}
      web: ${{ steps.filter.outputs.web }}
      shared: ${{ steps.filter.outputs.shared }}
    steps:
      - uses: actions/checkout@a12a3943b4bdde767164f792f33f40b04645d846  # v4.2.2
      - uses: dorny/paths-filter@de90cc6fb38fc0963ad72b210f1f284cd68cea36  # v3.0.2
        id: filter
        with:
          filters: |
            api:
              - 'services/api/**'
              - 'shared/**'
            web:
              - 'services/web/**'
              - 'shared/**'
            shared:
              - 'shared/**'

  api-ci:
    needs: detect-changes
    if: needs.detect-changes.outputs.api == 'true'
    runs-on: ubuntu-24.04
    timeout-minutes: 20
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@a12a3943b4bdde767164f792f33f40b04645d846  # v4.2.2
      - run: cd services/api && make ci

  web-ci:
    needs: detect-changes
    if: needs.detect-changes.outputs.web == 'true'
    runs-on: ubuntu-24.04
    timeout-minutes: 20
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@a12a3943b4bdde767164f792f33f40b04645d846  # v4.2.2
      - run: cd services/web && make ci
```

---

## 8. Manual Deployment with Dispatch

```yaml
name: Manual Deploy
on:
  workflow_dispatch:
    inputs:
      environment:
        description: 'Target environment'
        required: true
        type: choice
        options: [staging, production]
      version:
        description: 'Version/SHA to deploy'
        required: true
        type: string
      dry-run:
        description: 'Dry run (no actual deploy)'
        type: boolean
        default: false

permissions: {}

jobs:
  deploy:
    runs-on: ubuntu-24.04
    timeout-minutes: 15
    permissions:
      contents: read
      id-token: write
    environment:
      name: ${{ inputs.environment }}
    steps:
      - uses: actions/checkout@a12a3943b4bdde767164f792f33f40b04645d846  # v4.2.2
        with:
          ref: ${{ inputs.version }}
      - uses: aws-actions/configure-aws-credentials@e3dd6a429d7300a6a4c196c26e071d42e0343502  # v4.0.2
        with:
          role-to-assume: ${{ vars.AWS_DEPLOY_ROLE_ARN }}
          aws-region: ${{ vars.AWS_REGION }}
      - name: Deploy
        env:
          DRY_RUN: ${{ inputs.dry-run }}
        run: |
          if [ "$DRY_RUN" = "true" ]; then
            echo "::notice::Dry run — no changes applied"
            ./scripts/deploy.sh ${{ inputs.environment }} --dry-run
          else
            ./scripts/deploy.sh ${{ inputs.environment }}
          fi
      - name: Write job summary
        run: |
          echo "### Deployment Summary" >> $GITHUB_STEP_SUMMARY
          echo "| Field | Value |" >> $GITHUB_STEP_SUMMARY
          echo "|-------|-------|" >> $GITHUB_STEP_SUMMARY
          echo "| Environment | ${{ inputs.environment }} |" >> $GITHUB_STEP_SUMMARY
          echo "| Version | ${{ inputs.version }} |" >> $GITHUB_STEP_SUMMARY
          echo "| Dry Run | ${{ inputs.dry-run }} |" >> $GITHUB_STEP_SUMMARY
```

---

## 9. Scheduled Maintenance

```yaml
name: Maintenance
on:
  schedule:
    - cron: '0 3 * * 0'  # Weekly, Sunday 3 AM UTC

permissions: {}

jobs:
  dependency-audit:
    runs-on: ubuntu-24.04
    timeout-minutes: 15
    permissions:
      contents: read
      security-events: write
    steps:
      - uses: actions/checkout@a12a3943b4bdde767164f792f33f40b04645d846  # v4.2.2
      - run: npm audit --audit-level=high
        continue-on-error: true  # Report but don't fail maintenance
      - name: Write audit summary
        if: always()
        run: |
          echo "### Dependency Audit" >> $GITHUB_STEP_SUMMARY
          npm audit --json 2>/dev/null | jq -r '.metadata.vulnerabilities | to_entries[] | "| \(.key) | \(.value) |"' >> $GITHUB_STEP_SUMMARY || true
```

---

## 10. Container Build and Push

```yaml
name: Build Container
on:
  push:
    branches: [main]
    paths: ['src/**', 'Dockerfile', 'package.json']

permissions: {}

jobs:
  build-push:
    runs-on: ubuntu-24.04
    timeout-minutes: 20
    permissions:
      contents: read
      id-token: write
      packages: write
    steps:
      - uses: actions/checkout@a12a3943b4bdde767164f792f33f40b04645d846  # v4.2.2

      - uses: docker/login-action@74a5d142397b4f367a81961eba4e8cd7edddf772  # v3.4.0
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - uses: docker/setup-buildx-action@b5ca514318bd6ebac0fb2aedd5d36ec1b5c232a2  # v3.10.0

      - uses: docker/build-push-action@14487ce63c7a62a4a324b0bfb37086795e31c6c1  # v6.16.0
        with:
          context: .
          push: true
          tags: |
            ghcr.io/${{ github.repository }}:${{ github.sha }}
            ghcr.io/${{ github.repository }}:latest
          cache-from: type=gha
          cache-to: type=gha,mode=max
```

---

## 11. Dependabot Configuration

Always include this alongside any CI/CD implementation:

```yaml
# .github/dependabot.yml
version: 2
updates:
  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
    groups:
      github-actions:
        patterns: ["*"]
```
