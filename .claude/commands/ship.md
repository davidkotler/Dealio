Analyze all changes on the current branch, ensure proper branch naming, commit with Conventional Commits, push, and open a PR with a descriptive template.

## Context

Current branch: !`git branch --show-current`
Default branch: main
Repo: !`gh repo view --json nameWithOwner -q .nameWithOwner`
Staged/unstaged changes: !`git status --short`
Recent commits on this branch: !`git log --oneline -10`

## Steps

### 1. Analyze Changes

Determine the merge base and understand what work has been done:

```bash
MERGE_BASE=$(git merge-base HEAD main 2>/dev/null || echo "")
```

- If `MERGE_BASE` is empty (no common ancestor with main), use all commits on the branch.
- Run `git diff --stat $MERGE_BASE..HEAD` to see changed files.
- Run `git diff $MERGE_BASE..HEAD` to understand the full scope of changes.
- Read the diffs carefully to identify:
  - Which packages/services/libs were modified
  - The nature of changes (new feature, bug fix, refactor, docs, chore, test, ci, etc.)
  - A concise summary of what was accomplished

### 2. Validate Branch Name

The branch MUST follow Conventional Branch naming: `<type>/<ticket-id>/<short-description>`

**Accepted types:** `feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `ci`, `perf`, `build`, `style`

**Ticket ID:** A ticket/issue identifier (e.g., `TESS-123`, `GH-45`, or `no-ticket` if none applies).

**Short description:** Lowercase, hyphen-separated, 2-5 words summarizing the work.

**Examples:**
- `feat/TESS-42/user-profile-api`
- `fix/GH-12/null-pointer-settings`
- `chore/no-ticket/update-dependencies`

**If the current branch name does NOT follow this convention:**
- Infer the correct type from the changes analyzed in Step 1
- Ask the user for the ticket ID (suggest `no-ticket` if none is obvious)
- Propose a descriptive short-description based on the changes
- Present the suggested branch name and ask for confirmation
- Rename the branch:
  ```bash
  git branch -m <old-name> <new-name>
  ```

**If already on `main`:** Create a new branch with the proper name before proceeding.

### 3. Stage and Commit

Stage all relevant changes and create a commit following the [Conventional Commits](https://www.conventionalcommits.org/) specification.

**Commit message format:**
```
<type>(<scope>): <subject>

<body>

<footer>
```

**Rules:**
- **type**: One of `feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `ci`, `perf`, `build`, `style`
- **scope**: The affected package, service, or lib (e.g., `lib-settings`, `api`, `cli`, `infra`). Use comma-separated for multiple scopes.
- **subject**: Imperative mood, lowercase, no period, max 72 characters. Describe WHAT changed.
- **body**: Explain WHY the change was made. Bullet points for multiple changes. Wrap at 120 chars.
- **footer**: `Breaking-Change:` if applicable. Reference issues: `Closes #123`, `Refs TESS-42`.

**Examples:**
```
feat(lib-settings): add Pact utilities for contract testing

- Add PactSettings model for broker configuration
- Add helper functions for provider/consumer test setup
- Integrate with BaseServiceSettings composition pattern

Refs TESS-42
```

```
fix(api): handle null pointer in settings deserialization

The settings parser would crash when optional fields were missing
from the environment. Now defaults are applied before validation.

Closes GH-12
```

**Process:**
1. Run `git status` to see all changes (staged, unstaged, untracked)
2. Do NOT stage files that contain secrets (`.env`, `credentials.*`, `*.pem`, `*.key`)
3. Stage files by name — avoid `git add -A` or `git add .`
4. If there are logically separate groups of changes, ask the user if they want multiple commits
5. Create the commit using a HEREDOC for proper formatting:
   ```bash
   git commit -m "$(cat <<'EOF'
   <type>(<scope>): <subject>

   <body>

   <footer>
   EOF
   )"
   ```
6. Verify the commit succeeded with `git log -1 --oneline`

### 4. Push to Remote

```bash
git push -u origin $(git branch --show-current)
```

If the push is rejected (e.g., branch was renamed), handle accordingly:
- If the old remote branch exists, ask the user before force-pushing
- If the branch is new, the `-u` flag sets up tracking

### 5. Open Pull Request

Create a PR using `gh` CLI with the following strict template:

```bash
gh pr create --title "<type>(<scope>): <subject>" --body "$(cat <<'EOF'
## Summary

<1-3 sentence high-level description of what this PR accomplishes and why.>

## Changes

<Bulleted list of specific changes, grouped by area:>

### <Area 1> (e.g., `libs/lib-settings`)
- Change description
- Change description

### <Area 2> (if applicable)
- Change description

## Type of Change

- [ ] New feature (`feat`)
- [ ] Bug fix (`fix`)
- [ ] Refactoring (`refactor`)
- [ ] Documentation (`docs`)
- [ ] Tests (`test`)
- [ ] Chore / maintenance (`chore`)
- [ ] CI/CD (`ci`)
- [ ] Performance (`perf`)

<!-- Check the applicable type above -->

## Testing

<Describe how the changes were tested:>
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing performed
- [ ] No tests needed (explain why)

## Checklist

- [ ] Code follows project conventions (ruff, ty, Google docstrings)
- [ ] Self-reviewed the diff before submitting
- [ ] No secrets, credentials, or PII committed
- [ ] Breaking changes documented (if any)

## Related

- Ticket: <ticket-id or "N/A">
- Closes: #<issue-number> (if applicable)

---
> Generated with [Claude Code](https://claude.ai/code)
EOF
)"
```

**PR Title:** Must match the commit's conventional format: `<type>(<scope>): <subject>`

**Fill in the template:**
- Check the applicable "Type of Change" checkbox based on the commit type
- Fill in the Summary from the commit body context
- List all Changes with specific details from the diff analysis
- Check applicable Testing items based on what was observed in the changes
- Check Checklist items that apply
- Fill in Related ticket/issue references

### 6. Report

After the PR is created, output:
- PR URL (clickable)
- Branch name
- Commit hash and message
- Summary of what was shipped

## Constraints

- NEVER commit `.env`, credentials, secrets, or PII
- NEVER force-push without explicit user confirmation
- NEVER skip pre-commit hooks (no `--no-verify`)
- NEVER amend existing commits without asking
- If `gh` CLI is not authenticated, instruct the user to run `gh auth login`
- If there are no changes to commit, report that and stop
- If pre-commit hooks fail, fix the issues and create a NEW commit (do not amend)

## Optional Arguments

If the user provides `$ARGUMENTS`, interpret them as:
- `--dry-run` — show what would be committed and the PR body, but do not execute
- `--no-pr` — commit and push only, skip PR creation
- `--amend` — amend the last commit instead of creating a new one
- A ticket ID (e.g., `TESS-123`) — use as the ticket reference
