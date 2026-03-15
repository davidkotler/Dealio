Run all pre-commit hooks across all stages and fix all issues.

## Instructions

1. Run `pre-commit run --all-files` using the Bash tool
2. Run `pre-commit run --hook-stage pre-push --all-files` using the Bash tool
3. If all hooks pass on both stages, report success and stop
4. If any hooks fail:
   - Read the output carefully to identify which hooks failed and why
   - For auto-fixable issues (ruff, codespell, trailing whitespace, end-of-file-fixer, pyproject-fmt, ruff-format): the hooks auto-fix these — re-run the failing stage to confirm fixes applied
   - For non-auto-fixable issues: fix them manually using Edit tool, then re-run
5. Repeat until all hooks pass cleanly on all stages
6. Show a summary of what was fixed

## Notes

- Do NOT use `--no-verify` or skip any hooks
- Do NOT commit changes — just fix the issues
- If a hook keeps failing after 3 attempts, report the issue to the user instead of looping
