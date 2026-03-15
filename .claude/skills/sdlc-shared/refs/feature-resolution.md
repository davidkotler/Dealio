# Feature Directory Resolution

> How orchestrator skills identify the target feature directory for artifact reads and writes.

---

## Resolution Algorithm

Every orchestrator skill starts by resolving which feature directory to operate on. The feature directory is the single source of truth for all SDLC artifacts: `docs/designs/YYYY/NNN-{feature-name}/`.

### Case 1: Argument Provided

When the user passes a feature identifier (e.g., `/discover 001-sdlc-claude-commands`):

1. Search `docs/designs/*/` across all year directories for a match
2. Match against the directory name using the argument as a substring:
   - Exact match: `docs/designs/2026/001-sdlc-claude-commands/` matches `001-sdlc-claude-commands`
   - Prefix match: `001` matches `001-sdlc-claude-commands`
   - Substring match: `sdlc-claude` matches `001-sdlc-claude-commands`
3. If exactly one match → use it
4. If multiple matches → present them as a selection list for the user to choose
5. If no match → report error and fall through to Case 2 (selection list)

```
/discover 001-sdlc-claude-commands
    │
    ├─► Scan: docs/designs/*/001-sdlc-claude-commands/
    │
    ├─► Found: docs/designs/2026/001-sdlc-claude-commands/
    │
    └─► Resolved ✓
```

### Case 2: No Argument Provided

When the user invokes a skill without an argument (e.g., `/discover`):

1. Scan `docs/designs/` for all year directories
2. Within each year, list all feature directories
3. Present as a numbered selection list with feature status:

```markdown
## Select a Feature

| # | Feature | Year | Current Phase |
|---|---------|------|---------------|
| 1 | 001-sdlc-claude-commands | 2026 | Discovery |
| 2 | 002-auth-service | 2026 | Design |
| 3 | 001-payment-gateway | 2025 | Implementation |
| N | **Create new feature** | — | — |
```

4. Wait for user to select by number
5. If user selects "Create new feature" → proceed to Case 3

### Case 3: Create New Feature

When the user wants to create a new feature directory:

1. Determine the current year: `YYYY` (e.g., `2026`)
2. Scan `docs/designs/YYYY/` for existing directories
3. Extract sequence numbers from directory names (the `NNN` prefix)
4. Assign next sequence number: `max(existing) + 1`, zero-padded to 3 digits
5. Ask the user for a feature name
6. Convert to kebab-case: lowercase, spaces to hyphens, strip special characters
7. Create directory: `docs/designs/YYYY/NNN-{kebab-case-name}/`

```
User: "Create new feature"
    │
    ├─► Scan: docs/designs/2026/ → found 001-*, 002-*
    │
    ├─► Next sequence: 003
    │
    ├─► User provides: "User Profile Management"
    │
    ├─► Kebab-case: "user-profile-management"
    │
    └─► Created: docs/designs/2026/003-user-profile-management/
```

### Case 4: Argument Doesn't Match

When the argument doesn't match any existing directory:

1. Report the error clearly:
   ```
   No feature directory found matching "xyz-feature".
   ```
2. Present the full selection list (same as Case 2)
3. Include the "Create new feature" option in case the user intended to start a new one

---

## Directory Structure Reference

A fully populated feature directory looks like this:

```
docs/designs/YYYY/NNN-{feature-name}/
├── README.md              # Inception: vision, goals, rationale (created by /discover)
├── prd.md                 # Requirements: FRs, NFRs, acceptance criteria (created by /discover)
├── hld.md                 # High-level design: boundaries, integration (created by /design, optional)
├── lld.md                 # Low-level design: contracts, data models (created by /design)
├── tasks-breakdown.md     # Task decomposition with dependencies (created by /tasks-breakdown)
├── sdlc-log.md            # Chronological activity log (appended by all skills)
├── release.md             # Release report: retrospective and delivery validation (created by /qa-review)
└── reviews/               # Review verdicts organized by task (created by /review)
    └── {task-name}/
        ├── api-reviewer.md
        ├── python-reviewer.md
        └── performance-reviewer.md
```

---

## Path Construction Helper

When constructing paths within a resolved feature directory:

| Artifact | Path |
|----------|------|
| Feature README | `{feature-dir}/README.md` |
| Requirements | `{feature-dir}/prd.md` |
| High-level design | `{feature-dir}/hld.md` |
| Low-level design | `{feature-dir}/lld.md` |
| Task breakdown | `{feature-dir}/tasks-breakdown.md` |
| SDLC log | `{feature-dir}/sdlc-log.md` |
| Release report | `{feature-dir}/release.md` |
| Review verdicts | `{feature-dir}/reviews/{task-name}/{reviewer-name}.md` |

---

## Validation

After resolution, verify the directory exists and is accessible:

```
Resolved: docs/designs/2026/001-sdlc-claude-commands/
├── Directory exists? ✓
└── Readable? ✓
```

If the directory was just created (Case 3), it will be empty — that's expected. The orchestrator skill proceeds to create the first artifact for the current phase.
