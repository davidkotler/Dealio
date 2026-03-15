Diagnose failed CI workflows on the current branch using `gh` CLI and produce a report with suggested fixes.

## Steps

1. Get the current branch name:
   ```
   git branch --show-current
   ```

2. List recent workflow runs for this branch:
   ```
   gh run list --branch <branch> --limit 10
   ```

3. Identify all failed or failing runs from the output

4. For each failed run, get detailed info:
   ```
   gh run view <run-id>
   ```
   This shows the jobs and their statuses.

5. For each failed job, fetch the logs:
   ```
   gh run view <run-id> --log-failed
   ```
   If `--log-failed` output is too large, try fetching logs for a specific job:
   ```
   gh run view <run-id> --job <job-id> --log
   ```

6. Analyze the logs to identify root causes — look for:
   - Test failures (parse test names, assertion errors, tracebacks)
   - Lint/type check errors (ruff, ty, mypy violations)
   - Build failures (dependency issues, missing modules, compilation errors)
   - Infrastructure issues (timeouts, rate limits, service unavailability)
   - Permission/auth errors

7. For each failure, check the relevant source code to understand context and formulate a fix suggestion

8. Produce a structured report with this format:

   ```
   # CI Diagnosis Report
   ## Branch: <branch-name>

   ### Workflow: <workflow-name> (Run #<id>)
   **Status:** Failed
   **Triggered:** <timestamp>
   **URL:** <run-url>

   #### Failed Job: <job-name>
   **Step:** <failed-step-name>
   **Root Cause:** <concise description>
   **Error:**
   <relevant error snippet>

   **Suggested Fix:**
   <actionable fix description with file paths and code changes if applicable>

   ---
   ```

9. After the report, summarize:
   - Total failed workflows / jobs
   - Common patterns across failures (if any)
   - Priority order for fixes (quick wins first)

## Notes

- If no failed runs exist on the current branch, report that CI is green
- If `gh` is not authenticated, instruct the user to run `gh auth login`
- Do not apply fixes automatically — only report and suggest
- If a failure is flaky (passed on re-run), note it as potentially flaky
- Truncate very long log outputs — focus on the relevant error sections
