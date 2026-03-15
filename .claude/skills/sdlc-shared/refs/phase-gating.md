# Phase Gating

> How orchestrator skills enforce phase dependencies by checking for required upstream artifacts before executing.

---

## Purpose

Phase gating prevents engineers from skipping SDLC phases. Each orchestrator skill checks that required artifacts from upstream phases exist before proceeding. If an artifact is missing, the skill blocks with a clear message directing the user to the correct upstream command.

This is an existence check only — if the file exists and is non-empty, the gate passes. Structural validation of artifact content is not performed (the upstream skill that produced it is responsible for quality).

---

## Phase Dependency Chain

```
/discover-feature       → produces → README.md
/discover-requirements  → produces → prd.md
     │
     ▼
/design-system  → produces → hld.md
     │
     ▼
/design-lld     → produces → lld.md
     │
     ▼
/tasks-breakdown  → produces → tasks-breakdown.md
     │
     ▼
/implement  → produces → code changes (per task)
     │
     ├──► /observe  → produces → instrumented code
     ├──► /test     → produces → test code
     ├──► /review   → produces → review verdicts in reviews/
     │        │
     │        ▼
     │    /refactor  → produces → fixed code + resolution report
     │
     └──► /optimize  → produces → optimized code
```

---

## Gate Checks by Skill

### `/discover-feature`

**Required artifacts:** None (SDLC entry point)

`/discover-feature` is the SDLC entry point. It has no gate — it can always run. It creates the feature directory and produces `README.md`.

### `/discover-requirements`

**Required artifacts:** `README.md`

```
Check: {feature-dir}/README.md exists and is non-empty?
  ├─► Yes → Proceed with /discover-requirements
  └─► No  → Block:
            "No feature inception found in {feature-dir}/."
            "Run `/discover-feature` first to produce README.md."
```

### `/design-system`

**Required artifacts:** `prd.md`

```
Check: {feature-dir}/prd.md exists and is non-empty?
  ├─► Yes → Proceed with /design-system
  └─► No  → Block:
            "No requirements found in {feature-dir}/."
            "Run `/discover-feature` then `/discover-requirements` to produce prd.md."
```

### `/design-lld`

**Required artifacts:** `prd.md`, `hld.md`

```
Check: {feature-dir}/prd.md exists and is non-empty?
  ├─► No  → Block:
            "No requirements found in {feature-dir}/."
            "Run `/discover` first to produce prd.md."
  └─► Yes → Check: {feature-dir}/hld.md exists and is non-empty?
              ├─► Yes → Proceed with /design-lld
              └─► No  → Block:
                        "No high-level design found in {feature-dir}/."
                        "Run `/design-system` first to produce hld.md."
```

### `/tasks-breakdown`

**Required artifacts:** `prd.md`, `lld.md`

```
Check: {feature-dir}/prd.md exists and is non-empty?
  ├─► No  → Block:
            "No requirements found in {feature-dir}/."
            "Run `/discover-feature` then `/discover-requirements` to produce prd.md."
  └─► Yes → Check: {feature-dir}/lld.md exists and is non-empty?
              ├─► Yes → Proceed with /tasks-breakdown
              └─► No  → Block:
                        "No low-level design found in {feature-dir}/."
                        "Run `/design-lld` first to produce lld.md."
```

### `/implement`

**Required artifacts:** `tasks-breakdown.md`

```
Check: {feature-dir}/tasks-breakdown.md exists and is non-empty?
  ├─► Yes → Proceed with /implement
  └─► No  → Block:
            "No task breakdown found in {feature-dir}/."
            "Run `/tasks-breakdown` first to produce tasks-breakdown.md."
```

### `/observe`

**Required artifacts:** Implementation code exists for the selected task

```
Check: Implementation code exists?
  ├─► Yes → Proceed with /observe
  └─► No  → Block:
            "No implementation code found for this task."
            "Run `/implement` first to produce code."
```

### `/test`

**Required artifacts:** Implementation code exists for the selected task

```
Check: Implementation code exists?
  ├─► Yes → Proceed with /test
  └─► No  → Block:
            "No implementation code found for this task."
            "Run `/implement` first to produce code."
```

### `/review`

**Required artifacts:** Implementation code exists for the selected task

```
Check: Implementation code exists?
  ├─► Yes → Proceed with /review
  └─► No  → Block:
            "No implementation code found for this task."
            "Run `/implement` first to produce code."
```

### `/refactor`

**Required artifacts:** Review verdicts in `reviews/{task-name}/`

```
Check: {feature-dir}/reviews/{task-name}/ exists and contains at least one .md file?
  ├─► Yes → Proceed with /refactor
  └─► No  → Block:
            "No review verdicts found for task '{task-name}'."
            "Run `/review` first to produce review verdicts."
```

### `/optimize`

**Required artifacts:** Implementation code exists

```
Check: Implementation code exists?
  ├─► Yes → Proceed with /optimize
  └─► No  → Block:
            "No implementation code found."
            "Run `/implement` first to produce code."
```

### `/qa-review`

**Required artifacts:** `tasks-breakdown.md` with all tasks complete

```
Check: {feature-dir}/tasks-breakdown.md exists and is non-empty?
  ├─► No  → Block:
  │         "No task breakdown found in {feature-dir}/."
  │         "Run `/tasks-breakdown` first to produce tasks-breakdown.md."
  └─► Yes → Check: all tasks marked ✅ Complete?
              ├─► Yes → Proceed with /qa-review
              └─► No  → Advisory:
                        "N of M tasks are incomplete. Proceed with partial review or go back?"
```

Note: The gate is advisory when tasks are incomplete — the developer can choose to proceed
with a partial release review. The release document will clearly mark incomplete tasks.

### `/update-documentation`

**Required artifacts:** `release.md` with PASS or PASS WITH NOTES assessment

```
Check: {feature-dir}/release.md exists and is non-empty?
  ├─► No  → Block:
  │         "No release document found in {feature-dir}/."
  │         "Run `/qa-review` first to produce release.md."
  └─► Yes → Check: Assessment field is PASS or PASS WITH NOTES?
              ├─► Yes → Proceed with /update-documentation
              └─► FAIL → Advisory:
                        "Release assessment is FAIL. Documentation typically happens
                         after a passing QA review. Proceed anyway or go back?"
```

Note: The gate is advisory when the assessment is FAIL — the developer may want to document
the current state for reference even if the feature needs additional work.

### `/sdlc`

**Required artifacts:** None (read-only dashboard)

`/sdlc` is a status dashboard. It reads all available artifacts without gating — it reports what exists and what's missing.

---

## Checking "Implementation Code Exists"

Several skills gate on "implementation code exists." This is less straightforward than checking for a named file. Use this algorithm:

1. **Check `sdlc-log.md`** for entries recording `/implement` execution for the selected task. If an entry exists with a successful outcome, code exists.

2. **Check git status** — look for code changes associated with the task:
   ```bash
   # Check if any commits reference the task name
   git log --oneline --grep="{task-name}" -- '*.py' '*.ts' '*.tsx'
   ```

3. **Check task status in `tasks-breakdown.md`** — if the task's implementation sub-tasks are marked as started or complete, code exists.

4. **Fallback: Ask the user** — if the above checks are inconclusive, ask: "Has implementation code been written for this task? The SDLC log doesn't show a `/implement` run."

The intent is pragmatic: don't block a user who has already written code outside the orchestrator flow. If there's evidence that code exists, proceed.

---

## Gate Message Format

All gate messages follow this structure:

```
{What's missing} in {where it should be}.
Run `/{upstream-command}` first to produce {artifact name}.
```

The message is direct and actionable — it tells the user exactly what to do next. No ambiguity, no multi-step recovery path. One command to unblock.

---

## Completion Detection

Beyond gating, some skills also detect when their phase is already complete and offer to re-run or advance:

| Skill | Completion artifact | Message |
|-------|--------------------|---------|
| `/discover-feature` | `README.md` exists | "Inception is complete. Run `/discover-requirements` next." |
| `/discover-requirements` | `prd.md` exists | "Requirements are complete. Run `/design-system` next." |
| `/design-system` | `hld.md` exists | "HLD is complete. Run `/design-lld` next. Re-run HLD?" |
| `/design-lld` | `lld.md` exists | "LLD is complete. Run `/tasks-breakdown` next. Re-run LLD?" |
| `/tasks-breakdown` | `tasks-breakdown.md` exists | "Breakdown exists. Refine or regenerate?" |
| `/qa-review` | `release.md` exists | "Release review is complete. Run `/update-documentation` next. Re-run?" |
| `/update-documentation` | SDLC log entry for `/update-documentation` exists | "Documentation is complete. Epic is Done. Re-run?" |

Completion detection is advisory — the user can always choose to re-run a phase.
