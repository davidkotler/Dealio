Analyze all changes on the current branch compared to main and update docstrings of changed modules, classes, and functions to accurately reflect the current implementation.

## Steps

1. Identify the base branch and changed files:
   ```
   git merge-base HEAD main
   git diff --name-only --diff-filter=ACMR $(git merge-base HEAD main)..HEAD -- '*.py'
   ```
   Only process `.py` files that were Added, Copied, Modified, or Renamed.

2. For each changed file, get the detailed diff to understand what changed:
   ```
   git diff $(git merge-base HEAD main)..HEAD -- <file>
   ```

3. Read each changed file fully to understand the current state of the code.

4. For each file, identify all symbols (modules, classes, functions, methods) whose **behavior, signature, parameters, return type, or raised exceptions** changed based on the diff.

5. For each changed symbol, evaluate its existing docstring:
   - **Missing docstring on a public symbol** — write one following the conventions below
   - **Outdated docstring** (describes old behavior, wrong params, wrong return, wrong exceptions) — update it
   - **Accurate docstring** — leave it alone, do not touch it
   - **Private symbols** (prefixed with `_`) — only update if they already have a docstring; do not add new ones

6. Apply docstring updates using the Edit tool. Do NOT change any runtime code — only docstrings.

7. After all updates, run:
   ```
   ruff check --fix . && ruff format .
   ```

8. Show a summary of what was updated:
   - How many files were analyzed
   - How many docstrings were added/updated
   - List of updated symbols (file:symbol format)

## Docstring Conventions (Google Style)

Follow the existing codebase conventions exactly:

### Module-level
```python
"""Brief summary of what this module provides.

Extended description if the module is non-trivial, explaining key concepts,
states, or patterns.
"""
```

### Class
```python
class Foo:
    """Brief summary of the class purpose.

    Extended description with usage context.

    Args:
        name: Description of the parameter.
        timeout: Seconds before giving up.
    """
```

### Function / Method
```python
def bar(self, x: int) -> str:
    """Brief summary of what this function does.

    Extended description if non-trivial.

    Args:
        x: Description of the parameter.

    Returns:
        Description of the return value (only for non-obvious returns).

    Raises:
        ValueError: When x is negative.
    """
```

### Properties
```python
@property
def name(self) -> str:
    """Brief description of what this property represents."""
```

## Rules

- **Summary line**: Always present, concise, ends with period
- **Type hints**: In signature only, never in docstring
- **Code references**: Use double backticks (``` `` ` `` ```) for param names, exceptions, code
- **Sections**: `Args:`, `Returns:`, `Raises:` — only include sections that apply
- **Line length**: 120 characters max
- **Tone**: Factual and direct; describe what the code does, not what it used to do
- **Do NOT add docstrings** to trivial one-line functions, private helpers without existing docstrings, or test files
- **Do NOT modify** any runtime code, imports, or type annotations — only docstrings
- **Do NOT add docstrings** to unchanged symbols just because you're in the file
- **Preserve** existing docstring style if a file uses a slightly different convention — consistency within a file matters more than cross-file uniformity

## Optional Arguments

If the user provides `$ARGUMENTS`, interpret them as:
- A file path or glob → only process matching files
- `--dry-run` → report what would change without applying edits
- `--verbose` → show the diff of each docstring change before/after
