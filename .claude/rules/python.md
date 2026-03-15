---
paths:
  - 'libs/**/*.py'
  - 'services/**/*.py'
  - 'tools/**/*.py'
  - 'tests/**/*.py'
---

# Python Code Standards

Python 3.13+ syntax, typing, and idiom rules for all Python files.

## Module Structure

1. First import: `from __future__ import annotations`
2. Import order: stdlib, third-party, local — blank line between groups
3. Heavy/circular imports behind `if TYPE_CHECKING:`

## Type Safety

6. Type all parameters and returns (including `-> None`)
7. Modern union: `str | None` not `Optional[str]`, `X | Y` not `Union[X, Y]`
8. Built-in generics: `list[str]`, `dict[K, V]` — never import `List`, `Dict` from typing
9. Accept abstract (`Sequence`, `Mapping`), return concrete (`list`, `dict`)
10. `NewType` for semantic IDs, `TypeAlias` for complex repeated types
11. `Protocol` for interfaces — prefer over ABC
12. No `Any` except at true boundaries; no bare `# type: ignore` without comment

## Style & Idioms

13. Keyword-only args (`*`) for 2+ parameters
14. `zip(..., strict=True)` always
15. `enumerate()` not `range(len(...))`
16. Walrus operator: `if (x := f()):` for assign-and-test
17. `match/case` for 3+ branches instead of `if/elif` chains
18. Dict merge: `d1 | d2` not `{**d1, **d2}`
19. `StrEnum` + `auto()` not `(str, Enum)` mixin
20. `pathlib.Path` for all path operations
21. `frozenset` for membership constant sets
22. f-strings — never `.format()` or `%`
23. Trailing commas in multi-line structures

## Naming

24. Booleans: `is_`, `has_`, `can_`, `should_` prefixes
25. Functions: verb + noun revealing action and result
26. Constants: `SCREAMING_SNAKE_CASE`
27. No single-letter names outside short loops
28. No abbreviations unless universally understood

## Structure

29. Functions <= 30 lines (prefer <= 20)
30. Nesting depth <= 3 — use early returns and guard clauses
31. One level of abstraction per function
32. Pure functions by default — push side effects to boundaries
33. No mutable default arguments — use `None` + `or []`
34. No module-level mutable state
35. Structured logging only — never `print()`

## Error Handling

36. Never swallow exceptions (`except: pass`)
37. Preserve context: `raise DomainError(...) from original`
38. No bare `except:` or `except Exception:` without re-raise or log
39. Expected failures: typed results (`Success | NotFound | Locked`), not None for errors
40. Timeouts on all external/blocking calls
