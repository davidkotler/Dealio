---
name: review-style
version: 1.0.0

description: |
  Review Python code for style consistency, modern syntax patterns, and idiomatic conventions.
  Evaluates walrus operators, pattern matching, comprehensions, naming, imports, and formatting.
  Use when reviewing Python modules, validating code changes, or assessing style compliance.
  Relevant for Python development, code review, post-implementation quality gates.

chains:
  invoked-by:
    - skill: implement/python
      context: "Post-implementation style validation"
    - skill: review/readability
      context: "Style subset of readability review"
  invokes:
    - skill: implement/python
      when: "Critical or major style violations detected"
    - skill: review/types
      when: "Type annotation issues surface during style review"
---

# Style Review

> Validate Python code adheres to modern idioms, consistent conventions, and team standards.

## Quick Reference

| Aspect | Details |
|--------|---------|
| **Dimension** | Style |
| **Scope** | Python modules, functions, classes, imports, docstrings |
| **Invoked By** | `implement/python`, `review/readability`, `/review` command |
| **Invokes** | `implement/python` (on failure), `review/types` |
| **Verdict Options** | `PASS` · `PASS_WITH_SUGGESTIONS` · `NEEDS_WORK` · `FAIL` |

---

## Review Objective

Ensure Python code leverages modern Python 3.13+ features, follows established naming conventions, maintains consistent formatting, and uses idiomatic patterns that maximize readability and maintainability.

### This Review Answers

1. Does the code use modern Python syntax where appropriate (walrus, match/case, dict union)?
2. Are naming conventions consistent and intention-revealing (boolean prefixes, snake_case)?
3. Is import organization clean and explicit?
4. Do comprehensions, iteration, and functional utilities follow best practices?

### Out of Scope

- Type correctness beyond basic annotation presence (see `review/types`)
- Architectural decisions and domain modeling (see `review/design`)
- Performance optimization patterns (see `review/performance`)

---

## Core Workflow

```
SCOPE → CONTEXT → ANALYZE → CLASSIFY → VERDICT → REPORT → CHAIN
```

1. **Scope:** `**/*.py` (exclude `__pycache__`, `migrations`)
2. **Context:** Load `rules/python.md`, `rules/principles.md`
3. **Analyze:** Apply criteria by priority (P0→P3)
4. **Classify:** Assign severity per finding
5. **Verdict:** Determine from severity distribution
6. **Report:** Structured markdown output
7. **Chain:** `implement/python` if needed

### Priority & Severity

| Priority | Category | Severity |
|----------|----------|----------|
| P0 | Anti-patterns (mutable defaults) | 🔴 BLOCKER |
| P1 | Modern Syntax (walrus, match) | 🟠 CRITICAL |
| P2 | Structure & Naming | 🟡 MAJOR |
| P3 | Formatting & Docs | 🔵 MINOR |

### Verdict Algorithm

```
BLOCKER present?     → FAIL
CRITICAL present?    → NEEDS_WORK
Multiple MAJOR?      → NEEDS_WORK
Few MAJOR/MINOR?     → PASS_WITH_SUGGESTIONS
Otherwise            → PASS
```

---

## Evaluation Criteria

### Modern Syntax Patterns (MS)

| ID | Criterion | Severity | Check |
|----|-----------|----------|-------|
| MS.1 | Walrus operator for assign-and-test | CRITICAL | `if (x := func()):` not `x = func(); if x:` |
| MS.2 | Pattern matching for 3+ branches | CRITICAL | `match/case` not `if/elif/elif` chains |
| MS.3 | Dict union operators | MAJOR | `d1 \| d2` not `{**d1, **d2}` |
| MS.4 | `enumerate()` for indexed iteration | MAJOR | Not `range(len(items))` |
| MS.5 | `zip(strict=True)` for paired iteration | CRITICAL | Prevents silent truncation bugs |
| MS.6 | `frozenset` for membership constants | MAJOR | O(1) lookup, not list O(n) |
| MS.7 | `StrEnum` with `auto()` | MAJOR | Not `(str, Enum)` mixin |
| MS.8 | `pathlib.Path` for path operations | MAJOR | Not `os.path.join()` |

### Code Structure & Organization (CS)

| ID | Criterion | Severity | Check |
|----|-----------|----------|-------|
| CS.1 | Comprehensions for simple transforms | MAJOR | Not manual accumulation loops |
| CS.2 | Keyword-only args for 2+ params | MAJOR | `def func(*, arg1, arg2):` |
| CS.3 | Early returns reduce nesting | MAJOR | Guard clauses, not deep nesting |
| CS.4 | No mutable default arguments | BLOCKER | `None` + `or []` pattern |
| CS.5 | Functions under 30 lines | MAJOR | Extract helpers for long functions |
| CS.6 | `@wraps` + `ParamSpec` for decorators | CRITICAL | Preserve signature and introspection |
| CS.7 | `@contextmanager` over `try/finally` | MAJOR | Use contextlib utilities |
| CS.8 | `except*` for TaskGroup exceptions | CRITICAL | Not bare `except:` |
| CS.9 | `partial()` over lambdas | MINOR | `partial(fn, arg)` not `lambda x: fn(arg, x)` |

### Naming & Imports (NI)

| ID | Criterion | Severity | Check |
|----|-----------|----------|-------|
| NI.1 | Boolean auxiliary verb prefixes | MAJOR | `is_`, `has_`, `can_`, `should_`, `was_` |
| NI.2 | Intent-revealing function names | MAJOR | Action + context, not abbreviations |
| NI.3 | `SCREAMING_SNAKE` for constants | MINOR | Module-level immutable values |
| NI.4 | Import grouping: stdlib → 3rd → local | MINOR | Blank line between groups |
| NI.7 | f-strings with double quotes | MINOR | Not `.format()` or `%` |
| NI.8 | Trailing commas in multi-line | MINOR | Cleaner diffs |

### Documentation (DC)

| ID | Criterion | Severity | Check |
|----|-----------|----------|-------|
| DC.1 | Google-style docstrings | MINOR | Args, Returns, Raises sections |
| DC.2 | Document what/why, not how | MINOR | No implementation details |
| DC.3 | Document `Raises:` for exceptions | MAJOR | Failure modes explicit |
| DC.4 | No type repetition in docstrings | MINOR | Types in signature, not docstring |

---

## Patterns & Anti-Patterns

### ✅ Quality Indicators

```python
# Modern syntax: walrus + match + dict union + strict zip
if (user := get_user(id)) and user.is_active:
    match user.role:
        case Role.ADMIN: perms = base_perms | admin_perms
        case _: perms = base_perms

for idx, (n, v) in enumerate(zip(names, values, strict=True)):
    process(idx, n, v)

# Safe defaults + keyword-only + boolean naming
def process(items: list[Item], *, filters: list[Filter] | None = None) -> list[Result]:
    is_valid: bool = validate(items)
    filters = filters or []
```

### ❌ Red Flags

```python
def process(items, cache={}):    # BLOCKER: mutable default
    ...

valid = check()                   # MAJOR: ambiguous boolean
for i in range(len(items)):       # MAJOR: use enumerate
    zip(a, b)                     # CRITICAL: missing strict=True
```

---

## Finding Output Format

```markdown
### [🟠 CRITICAL] <Title>

**Location:** `path/file.py:line`
**Criterion:** <ID> - <Name>

**Issue:** <Description>

**Evidence:**
\`\`\`python
<code>
\`\`\`

**Suggestion:** <Fix guidance>
```

---

## Review Summary Format

```markdown
# Style Review Summary

## Verdict: 🟡 NEEDS_WORK

| Metric | Count |
|--------|-------|
| Files Reviewed | 12 |
| Blockers | 0 |
| Critical | 2 |
| Major | 5 |

## Key Findings
1. **MS.5** - `zip()` without `strict=True` (2 instances)
2. **CS.4** - Mutable default in `cache_manager.py:23`

## Chain Decision
Invoking `implement/python` for CRITICAL findings.
```

---

## Skill Chaining

| Verdict | Action | Target |
|---------|--------|--------|
| `FAIL` | Mandatory | `implement/python` |
| `NEEDS_WORK` | Targeted fixes | `implement/python` |
| `PASS_WITH_SUGGESTIONS` | None | Suggestions only |
| `PASS` | Continue | `review/types` |

**Handoff:** Priority findings (criterion IDs) + file paths + suggested fixes.
**Re-review:** Scope to modified files, max 3 iterations.

---

## Automated Checks

```bash
# Ruff comprehensive check
ruff check --select=E,W,F,I,N,UP,B,A,C4,SIM,PIE src/
ruff format --check src/

# Pattern detection
grep -rn "def.*=\[\]" src/            # Mutable defaults
grep -rn "zip(" src/ | grep -v strict  # zip without strict
```

---

## Examples

### Example: Legacy Iteration → Modern

**Before:**
```python
def process_records(records, labels):
    results = []
    for i in range(len(records)):
        results.append(transform(records[i], labels[i]))
    return results
```

**Finding:** `[🟠 CRITICAL] MS.5 - Missing strict zip`

**After:**
```python
def process_records(records, labels):
    return [transform(r, l) for r, l in zip(records, labels, strict=True)]
```

**Verdict:** `NEEDS_WORK` → Chain to `implement/python`

---

## Deep References

Load on-demand for complex reviews:

| Reference | When to Load | Path |
|-----------|--------------|------|
| Python Style Guide | Detailed pattern examples | `skills/implement/python/refs/style.md` |
| Type Hints Reference | Annotation questions | `skills/implement/python/refs/typing.md` |
| Principles | Architectural alignment | `rules/principles.md` |

---

## Quality Gates

- [ ] All Python files in scope analyzed
- [ ] Each finding has location + criterion + severity
- [ ] Automated ruff checks executed
- [ ] Verdict aligns with severity distribution
- [ ] Chain decision explicit if not PASS
