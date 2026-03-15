# Troubleshooting Reference

> Common issues, debugging techniques, and solutions for GitHub Actions workflows. Load on-demand when diagnosing failures or unexpected behavior.

---

## 1. Debugging Techniques

### Enable Debug Logging

```yaml
# Option 1: Repository secrets (persistent)
# Set these in Settings → Secrets → Actions
ACTIONS_RUNNER_DEBUG: true
ACTIONS_STEP_DEBUG: true

# Option 2: Re-run with debug (one-time)
# In the Actions UI → Re-run jobs → Enable debug logging checkbox
```

### Print Contexts for Inspection

```yaml
- name: Dump contexts
  env:
    GITHUB_CONTEXT: ${{ toJSON(github) }}
    STEPS_CONTEXT: ${{ toJSON(steps) }}
    NEEDS_CONTEXT: ${{ toJSON(needs) }}
  run: |
    echo "::group::GitHub Context"
    echo "$GITHUB_CONTEXT"
    echo "::endgroup::"
    echo "::group::Steps Context"
    echo "$STEPS_CONTEXT"
    echo "::endgroup::"
```

**Important**: Always assign contexts to `env:` variables first—never inline `toJSON()` in `run:` blocks (prevents injection and escaping issues).

### Resource Monitoring

```yaml
- name: System resources
  run: |
    echo "::group::Resources"
    free -h
    df -h
    nproc
    echo "::endgroup::"
```

### Conditional Debug Steps

```yaml
- name: Extended diagnostics
  if: runner.debug == '1'
  run: |
    env | sort
    cat /etc/os-release
```

### Upload Artifacts on Failure

```yaml
- uses: actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02  # v4.6.2
  if: failure()
  with:
    name: failure-diagnostics
    path: |
      test-results/
      screenshots/
      **/*.log
    retention-days: 3
```

### Job Summaries for Visibility

```yaml
- name: Write summary
  if: always()
  run: |
    echo "### Build Results 🚀" >> $GITHUB_STEP_SUMMARY
    echo "| Metric | Value |" >> $GITHUB_STEP_SUMMARY
    echo "|--------|-------|" >> $GITHUB_STEP_SUMMARY
    echo "| Status | ${{ job.status }} |" >> $GITHUB_STEP_SUMMARY
    echo "| Commit | \`${{ github.sha }}\` |" >> $GITHUB_STEP_SUMMARY
```

---

## 2. Common Failures

### Workflow Not Triggering

| Symptom | Cause | Fix |
|---------|-------|-----|
| PR workflow doesn't run | `paths` filter excludes changed files | Check `paths`/`paths-ignore` filters match the changed files |
| Schedule never fires | Cron runs only on default branch | Ensure workflow is on `main`/`master`, not a feature branch |
| `workflow_dispatch` missing button | Workflow not on default branch | Merge to default branch first |
| Workflow triggers on wrong events | Missing `types` filter | Add `types: [opened, synchronize, reopened]` for `pull_request` |
| `workflow_run` never triggers | Upstream workflow name mismatch | The `workflows:` array must exactly match the `name:` of the upstream workflow |

### Permission Errors

| Symptom | Cause | Fix |
|---------|-------|-----|
| `Resource not accessible by integration` | Missing `permissions` | Add required permission to job (e.g., `pull-requests: write`) |
| `HttpError: Bad credentials` | `GITHUB_TOKEN` lacks scope | Check org-level token permission defaults |
| OIDC `AccessDenied` | IAM trust policy mismatch | Verify `sub` claim matches repo/environment/branch pattern |
| `actions/upload-artifact` fails | Missing `contents: read` | Artifact actions need at minimum `contents: read` |

### Cache Issues

| Symptom | Cause | Fix |
|---------|-------|-----|
| Cache never restores | Key mismatch | Check `hashFiles()` pattern matches actual lock file path |
| Cache grows unbounded | Stale entries | Cache evicts after 7 days unused; verify key includes OS |
| Cross-branch cache miss | Branch scoping | Feature branches can only access default branch caches via `restore-keys` |
| Cache hit but deps still install | Wrong path | Verify `path` matches where the package manager actually caches |
| 10 GB limit hit | Over-caching | Cache only dependency directories, not build outputs |

### Concurrency Issues

| Symptom | Cause | Fix |
|---------|-------|-----|
| Deploy cancelled mid-flight | `cancel-in-progress: true` on deploy | Use `cancel-in-progress: false` for deployment workflows |
| Jobs queued indefinitely | Same concurrency group | Ensure group includes `github.ref` for branch isolation |
| PR checks overlap | Missing concurrency | Add `group: ${{ github.workflow }}-${{ github.ref }}` |

---

## 3. Expression Pitfalls

### Ternary Gotcha

```yaml
# ⚠️ BROKEN: If truthy value is itself falsy ('', 0, false), falls through
env:
  COUNT: ${{ steps.check.outputs.count == '0' && '0' || 'default' }}
  # When count == '0': returns 'default' because '0' is falsy!

# ✅ FIX: Use separate if blocks for falsy true-values
- run: echo "count=0" >> $GITHUB_OUTPUT
  if: steps.check.outputs.count == '0'
- run: echo "count=default" >> $GITHUB_OUTPUT
  if: steps.check.outputs.count != '0'
```

### Type Coercion

```yaml
# ⚠️ All outputs are strings
# needs.build.outputs.should_deploy is "true" (string), not true (boolean)
if: needs.build.outputs.should_deploy == 'true'  # ✅ Compare as string
if: needs.build.outputs.should_deploy == true     # ❌ May not match
```

### Multi-line Output

```yaml
# ⚠️ Single-line echo truncates at newlines
- run: echo "changelog=$CHANGELOG" >> $GITHUB_OUTPUT  # ❌ Truncated

# ✅ Use heredoc delimiter for multi-line
- run: |
    echo "changelog<<EOF" >> $GITHUB_OUTPUT
    cat CHANGELOG.md >> $GITHUB_OUTPUT
    echo "EOF" >> $GITHUB_OUTPUT
```

### Empty Matrix

```yaml
# ⚠️ Empty matrix causes the job to silently skip
# If detect-changes outputs an empty array [], the build job never runs
strategy:
  matrix:
    service: ${{ fromJSON(needs.detect.outputs.services) }}

# ✅ Guard with if condition
if: needs.detect.outputs.services != '[]'
```

---

## 4. Service Container Issues

### Health Check Failures

```yaml
# ✅ Always configure health checks with retries for service containers
services:
  postgres:
    image: postgres:16
    env:
      POSTGRES_PASSWORD: test
    ports: ['5432:5432']
    options: >-
      --health-cmd pg_isready
      --health-interval 10s
      --health-timeout 5s
      --health-retries 5

  redis:
    image: redis:7
    ports: ['6379:6379']
    options: >-
      --health-cmd "redis-cli ping"
      --health-interval 10s
      --health-timeout 5s
      --health-retries 5
```

### Network Connectivity

| Scenario | Host | Port |
|----------|------|------|
| Job runs directly on runner | `localhost` | Mapped port |
| Job runs in container | Service label (e.g., `postgres`) | Container port |

```yaml
# When job runs on runner (no container: key)
env:
  DATABASE_URL: postgresql://postgres:test@localhost:5432/testdb

# When job runs in container
container: node:20
env:
  DATABASE_URL: postgresql://postgres:test@postgres:5432/testdb
```

---

## 5. Matrix Strategy Debugging

### Identify Failing Combination

```yaml
- name: Matrix info
  run: |
    echo "::notice::Running on ${{ matrix.os }} with Node ${{ matrix.node }}"
    echo "| Key | Value |" >> $GITHUB_STEP_SUMMARY
    echo "|-----|-------|" >> $GITHUB_STEP_SUMMARY
    echo "| OS | ${{ matrix.os }} |" >> $GITHUB_STEP_SUMMARY
    echo "| Node | ${{ matrix.node }} |" >> $GITHUB_STEP_SUMMARY
```

### Isolate Failures

```yaml
strategy:
  fail-fast: false  # Run ALL combinations even when one fails
  matrix:
    os: [ubuntu-24.04, windows-latest]
    node: [20, 22]
```

---

## 6. Reusable Workflow Debugging

### Caller Can't Find Reusable Workflow

| Cause | Fix |
|-------|-----|
| Wrong path | Use `org/repo/.github/workflows/file.yml@ref` for cross-repo |
| Wrong ref | Use branch name, tag, or SHA for `@ref` |
| Missing `workflow_call` trigger | Add `on: workflow_call` to the reusable workflow |
| Access restriction | Ensure repo settings allow workflow access from callers |

### Input/Output Mismatch

```yaml
# ✅ Verify input types match
# Reusable defines: type: string
# Caller passes: with: { version: 123 }  # ❌ Number, not string
# Fix: with: { version: '123' }          # ✅ String
```

### Secret Inheritance

```yaml
# Option 1: Explicit passing (preferred for clarity)
secrets:
  DEPLOY_KEY: ${{ secrets.DEPLOY_KEY }}

# Option 2: Inherit all (convenient but less explicit)
secrets: inherit
```

---

## 7. Performance Diagnostics

### Identify Bottlenecks

1. Check **Actions tab** → Click workflow run → Observe job/step timing
2. Look for steps taking >50% of total duration
3. Common bottlenecks: dependency install, docker build, test execution

### Quick Wins

| Bottleneck | Solution | Impact |
|------------|----------|--------|
| Dependency install | Add caching via `setup-*` action `cache` param | 30-70% faster |
| Full git clone | Use `fetch-depth: 1` (shallow clone) | 10-30% faster |
| Sequential jobs | Remove unnecessary `needs:` for parallel execution | 20-50% faster |
| Redundant runs | Add `paths` filters and `concurrency` cancellation | Saves runner minutes |
| Large Docker builds | Use BuildKit `cache-from: type=gha` | 40-80% faster |
| Full repo checkout | Use `sparse-checkout` for needed paths only | 5-15% faster |
