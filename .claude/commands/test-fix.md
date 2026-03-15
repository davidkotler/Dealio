Run `uv run devx test run --format json --no-cov --sequential` and fix all failed tests.

## Steps

1. Run `uv run devx test run --format json --no-cov --sequential` and capture the full JSON output
2. If all tests pass (`overall_exit_code` is 0), report success and stop
3. If any tests fail, parse the JSON output to identify:
   - Which suites failed (from `suite_results` where `status` is `FAILED` or `ERROR`)
   - Which specific tests failed (from `test_failures` in each failed suite: `classname`, `test_name`, `message`)
4. For each failed test, investigate with `uv run pytest` to get detailed tracebacks:
   - Run `uv run pytest <path/to/test_file.py>::<test_name> -vvs --tb=long` for each failed test
   - This gives full stdout, stderr, and long tracebacks that `devx test run` truncates
   - Read the test file and understand what it expects
   - Read the source code being tested to understand the actual behavior
   - Determine whether the test or the source is wrong:
     - If the source code has a bug, fix the source code
     - If the test expectation is outdated or incorrect due to intentional changes, fix the test
   - Apply the minimal fix that resolves the failure
5. After fixing all failures, re-run only the specific failed tests with `uv run pytest <path>::<test> -vvs` to verify each fix
6. Once individual fixes are verified, do a final confirmation run: `uv run devx test run --format json --no-cov --sequential --suite <name>` for each previously failed suite
7. If new failures appear, repeat the fix cycle
8. Once all tests pass, run `ruff check --fix . && ruff format .` to ensure fixes conform to style
9. Show a summary of what was fixed

## Fix Guidelines

- Always read both the test and the source before deciding what to fix
- Prefer fixing source bugs over changing test expectations
- Only change test expectations when the behavior change was intentional
- Do not weaken assertions — if a test checks something important, preserve that check
- Do not delete or skip failing tests unless explicitly told to
- Keep fixes minimal — do not refactor surrounding code
- If a test failure is unclear after reading the code, ask the user before guessing

## Flags Explained

- `--format json` — structured output for reliable parsing of failures
- `--no-cov` — skip coverage collection for faster iteration
- `--sequential` — run suites one at a time for clearer error output

## Optional Arguments

If the user provides arguments like `$ARGUMENTS`, pass them through to the devx command.
For example: `/test-fix --marker unit` → `uv run devx test run --format json --no-cov --sequential --marker unit`
