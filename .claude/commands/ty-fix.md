Run `ty check .` from the project root and fix every reported type error.

## Steps

1. Run `ty check .` and capture the full output
2. Parse the errors — each error includes a file path, line number, error code, and message
3. For each error, read the relevant code context and apply the minimal fix that resolves the type issue
4. After fixing all errors, run `ty check .` again to verify
5. If new errors were introduced by fixes, repeat until clean
6. Run `ruff check --fix . && ruff format .` to ensure fixes conform to style

## Fix Guidelines

- Prefer fixing the actual type issue over adding `# type: ignore` comments
- Only use `# type: ignore[code]` (with specific code) as a last resort when the checker is wrong
- Never use bare `# type: ignore` without a specific error code
- When adding type annotations, follow existing patterns in the file
- Do not change runtime behavior — fixes should be type-level only
- If a fix requires importing a type, use the project's import conventions (full paths, isort-compatible)
