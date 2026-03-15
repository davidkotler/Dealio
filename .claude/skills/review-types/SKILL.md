---
name: review-types
version: 1.0.0

description: |
  Review Python code for type annotation quality and modern typing practices.
  Evaluates completeness, correctness, and adherence to modern Python typing conventions.
  Use when reviewing Python modules, validating type hints after implementation,
  or assessing typing consistency across a codebase.
  Relevant for Python 3.10+, ty validation, type-safe codebases.

chains:
  invoked-by:
    - skill: implement/python
      context: "Post-implementation type safety gate"
    - skill: implement/api
      context: "Validate API type contracts"
    - skill: implement/pydantic
      context: "Verify Pydantic model typing"
    - skill: review/style
      context: "Type review as part of style compliance"
  invokes:
    - skill: implement/python
      when: "Critical or major type violations detected"
    - skill: review/readability
      when: "Type issues resolved, continue review pipeline"
---

# Type Safety Review

> Validate type annotation completeness and modern typing practices through systematic static analysis.

## Quick Reference

| Aspect | Details |
|--------|---------|
| **Dimension** | Type Safety |
| **Scope** | Python modules, functions, classes, type aliases |
| **Invoked By** | `implement/python`, `implement/api`, `/review` command |
| **Invokes** | `implement/python` (on failure) |
| **Verdict Options** | `PASS` · `PASS_WITH_SUGGESTIONS` · `NEEDS_WORK` · `FAIL` |

---

## Review Objective

Ensure all Python code uses complete, correct, and modern type annotations that enable static analysis tools to catch errors before runtime.

### This Review Answers

1. Are all functions and methods fully annotated with parameter and return types?
2. Does the code use modern Python 3.10+ typing syntax consistently?
3. Are generic types, protocols, and type aliases used appropriately?
4. Will the code pass strict ty checks without suppression?

### Out of Scope

- Runtime type validation (covered by `review/robustness`)
- Pydantic model field validation (covered by `review/data`)

---

## Core Workflow

```
┌─────────────────────────────────────────────────────────────┐
│                    REVIEW WORKFLOW                          │
├─────────────────────────────────────────────────────────────┤
│  1. SCOPE    →  Identify Python files to review             │
│  2. CONTEXT  →  Load typing principles & conventions        │
│  3. ANALYZE  →  Apply evaluation criteria systematically    │
│  4. CLASSIFY →  Assign severity to each finding             │
│  5. VERDICT  →  Determine pass/fail based on findings       │
│  6. REPORT   →  Output structured review results            │
│  7. CHAIN    →  Invoke downstream skills if needed          │
└─────────────────────────────────────────────────────────────┘
```

### Step 1: Scope Definition

Identify review targets:

```bash
# All Python source files (exclude tests for separate review)
src/**/*.py
app/**/*.py
lib/**/*.py

# Exclude generated files
!**/*_pb2.py
!**/migrations/*.py
```

### Step 2: Context Loading

Before analysis, internalize:







- **Principles:** `rules/principles.md` → Type Safety, Fail Fast
- **Conventions:** `rules/python.md` → Python-specific typing rules
- **Patterns:** `skills/implement/python/refs/typing.md` → Detailed typing patterns

### Step 3: Systematic Analysis

For each artifact, evaluate against criteria in order of severity:

| Priority | Criterion Category | Weight |
|----------|-------------------|--------|
| P0 | Module Structure | Blocker |
| P1 | Annotation Completeness | Critical |
| P2 | Modern Syntax | Major |
| P3 | Advanced Patterns | Minor |

### Step 4: Severity Classification

| Severity | Definition | Action Required |
|----------|------------|-----------------|
| **🔴 BLOCKER** | Missing `from __future__ import annotations` or bare `# type: ignore` | Must fix before merge |
| **🟠 CRITICAL** | Missing return type, untyped function parameter | Must fix, may defer |
| **🟡 MAJOR** | Legacy typing imports (`Optional`, `Union`, `List`), bare `Callable` | Should fix |
| **🔵 MINOR** | Concrete param types where abstract would work, missing `TypeAlias` | Consider fixing |
| **⚪ SUGGESTION** | Protocol could replace ABC, `NewType` for semantic IDs | Optional improvement |
| **🟢 COMMENDATION** | Exemplary typing patterns, proper variance usage | Positive reinforcement |

### Step 5: Verdict Determination

```
Findings Analysis
       │
       ├─► Any BLOCKER? ──────────────► FAIL
       │
       ├─► Any CRITICAL? ─────────────► NEEDS_WORK
       │
       ├─► Multiple MAJOR? ───────────► NEEDS_WORK
       │
       ├─► Few MAJOR or MINOR only? ──► PASS_WITH_SUGGESTIONS
       │
       └─► SUGGESTION/COMMENDATION ───► PASS
```

---

## Evaluation Criteria

### Module Structure (MS)

| ID | Criterion | Severity | Check |
|----|-----------|----------|-------|
| MS.1 | Future annotations import | BLOCKER | First import is `from __future__ import annotations` |
| MS.2 | No legacy typing imports | MAJOR | No `List`, `Dict`, `Set`, `Tuple`, `Optional`, `Union` from `typing` |
| MS.3 | TYPE_CHECKING guard | MINOR | Heavy/circular imports guarded with `if TYPE_CHECKING:` |

### Annotation Completeness (AC)

| ID | Criterion | Severity | Check |
|----|-----------|----------|-------|
| AC.1 | All parameters typed | CRITICAL | Every function parameter has type annotation |
| AC.2 | All returns typed | CRITICAL | Every function has explicit return type (including `-> None`) |
| AC.3 | Class attributes typed | MAJOR | Class-level attributes have type annotations |
| AC.4 | No implicit `Any` | CRITICAL | No untyped variables that resolve to `Any` |

### Modern Syntax (SY)

| ID | Criterion | Severity | Check |
|----|-----------|----------|-------|
| SY.1 | Union syntax | MAJOR | Uses `X \| Y` not `Union[X, Y]` |
| SY.2 | Optional syntax | MAJOR | Uses `X \| None` not `Optional[X]` |
| SY.3 | Built-in generics | MAJOR | Uses `list[T]`, `dict[K, V]` not `List[T]`, `Dict[K, V]` |
| SY.4 | Precise Callable | MAJOR | `Callable[[Args], Return]` not bare `Callable` |

### Advanced Patterns (AP)

| ID | Criterion | Severity | Check |
|----|-----------|----------|-------|
| AP.1 | Abstract params, concrete returns | MINOR | Params use `Sequence`/`Mapping`, returns use `list`/`dict` |
| AP.2 | Protocol for duck typing | SUGGESTION | `Protocol` preferred over `ABC` for interfaces |
| AP.3 | TypeAlias for complex types | MINOR | Repeated complex types extracted to `TypeAlias` |
| AP.4 | NewType for semantic IDs | SUGGESTION | Domain IDs use `NewType` to prevent mixing |
| AP.5 | Proper TypeVar usage | MINOR | Correct bound vs constrained, proper variance |
| AP.6 | Self return type | MINOR | Methods returning `self` use `-> Self` |

---

## Patterns & Anti-Patterns

### ✅ Indicators of Quality

```python
from __future__ import annotations

from collections.abc import Sequence, Mapping
from typing import TypeAlias, NewType, Protocol, Self, Final

UserId = NewType("UserId", str)
JsonValue: TypeAlias = str | int | float | bool | None | list["JsonValue"] | dict[str, "JsonValue"]

class Repository(Protocol):
    def save(self, entity: Entity) -> None: ...

class Builder:
    def with_name(self, name: str) -> Self:
        self.name = name
        return self

def process_items(items: Sequence[str]) -> list[str]:
    return [item.upper() for item in items]

def get_config(key: str) -> str | None:
    return _config.get(key)
```

**Why this works:** Uses future annotations, modern union syntax, abstract params with concrete returns, Protocol for interfaces, Self for fluent builders, NewType for semantic safety.

### ❌ Red Flags

```python
from typing import List, Dict, Optional, Union, Callable

def get_config(key: str):  # Missing return type
    return config.get(key)

def process(items: list[str]) -> list[str]:  # Concrete param type
    return [i.upper() for i in items]

def register(callback: Callable) -> None:  # Bare Callable
    callbacks.append(callback)

result: Union[User, None]  # Legacy Union syntax
items: Optional[List[str]]  # Legacy Optional + List

# type: ignore  # Bare suppression without explanation
```

**Why this fails:** Missing future annotations, legacy imports, omitted return types, bare Callable, concrete parameter types, unexplained type ignores.

---

## Finding Output Format

Structure each finding as:

```markdown
### [🔴 BLOCKER] Missing future annotations import

**Location:** `src/services/user_service.py:1`
**Criterion:** MS.1 - Future annotations import

**Issue:**
Module does not start with `from __future__ import annotations`, preventing
modern typing syntax from working correctly in all Python versions.

**Evidence:**
```python
from typing import List, Optional  # First import is legacy typing
```

**Suggestion:**
Add as the first import line:
```python
from __future__ import annotations
```

**Rationale:**
Future annotations enable PEP 604 union syntax (`X | Y`), forward references
without quotes, and reduce runtime overhead of type annotations.
```

---

## Review Summary Format

```markdown
# Type Safety Review Summary

## Verdict: 🟠 NEEDS_WORK

| Metric | Count |
|--------|-------|
| Files Reviewed | 12 |
| Blockers | 0 |
| Critical | 3 |
| Major | 7 |
| Minor | 4 |
| Suggestions | 2 |
| Commendations | 1 |

## Key Findings

1. **3 functions missing return types** - AC.2 violations in `user_service.py`
2. **7 legacy typing imports** - SY.1-3 violations across multiple modules
3. **Excellent Protocol usage** - Commendation for `repository.py` interfaces

## Recommended Actions

1. Add missing return type annotations (Critical)
2. Replace `Optional[X]` with `X | None` throughout (Major)
3. Replace `List`, `Dict` imports with built-in generics (Major)

## Skill Chain Decision

Chaining to `implement/python` to remediate 3 Critical and 7 Major findings.
```

---

## Skill Chaining

### Chain Triggers

| Verdict | Chain Action | Target Skill |
|---------|--------------|--------------|
| `FAIL` | Mandatory fix | `implement/python` |
| `NEEDS_WORK` | Targeted fixes | `implement/python` |
| `PASS_WITH_SUGGESTIONS` | Optional | None (suggestions only) |
| `PASS` | Continue pipeline | `review/readability` |

### Handoff Protocol

When chaining to implement:

```markdown
**Chain Target:** `implement/python`
**Priority Findings:** MS.1, AC.1, AC.2, SY.1-4
**Context:** Review identified type annotation issues requiring remediation

**Constraint:** Preserve existing logic; modify only type annotations

```



### Re-Review Loop



After implement completes, re-invoke this review with:

- Scope limited to modified files
- Focus on previously-failed criteria
- Maximum 3 iterations before escalation

---

## Automated Checks

Run these commands for objective validation:

```bash
# Check for missing annotations (ruff)
ruff check --select=ANN --output-format=json $FILES

# Strict type checking (ty)
ty check --no-error-summary $FILES

```

### Interpreting Tool Output

| Tool | Exit Code | Interpretation |
|------|-----------|----------------|
| ruff ANN | 0 | All annotations present |
| ty check | 0 | Type-safe |

---

## Integration Points

### Upstream Integration

| Source | Trigger | Context Provided |
|--------|---------|------------------|
| `implement/python` | Post-implementation | Changed files list |
| `implement/api` | After route handlers | API module paths |
| `/review` command | Explicit invocation | User-specified scope |

### Downstream Integration

| Target | Condition | Handoff |
|--------|-----------|---------|
| `implement/python` | Verdict ≠ PASS | Findings + file list |
| `review/readability` | Verdict = PASS | Continue pipeline |

---

## Examples


### Example 1: Legacy Imports Remediation


**Input:** Review `src/services/order_service.py`


```python
from typing import List, Dict, Optional, Union


def get_orders(user_id: str) -> Optional[List[Dict[str, str]]]:

    ...
```


**Analysis:**

- MS.1: Missing future annotations (BLOCKER)
- SY.1: Using `Union` pattern indirectly via Optional (MAJOR)
- SY.2: Using `Optional` instead of `| None` (MAJOR)
- SY.3: Using `List`, `Dict` instead of builtins (MAJOR)

**Output:**
```markdown
### [🔴 BLOCKER] Missing future annotations import

**Location:** `src/services/order_service.py:1`
**Criterion:** MS.1

**Issue:** Module lacks `from __future__ import annotations`.

### [🟡 MAJOR] Legacy typing imports

**Location:** `src/services/order_service.py:1`
**Criterion:** SY.2, SY.3

**Issue:** Using `List`, `Dict`, `Optional` from typing module.

**Suggestion:**
```python
from __future__ import annotations

def get_orders(user_id: str) -> list[dict[str, str]] | None:
    ...
```
```

**Verdict:** `NEEDS_WORK` → Chain to `implement/python`

### Example 2: Excellent Typing Practices


**Input:** Review `src/domain/repository.py`


```python
from __future__ import annotations


from collections.abc import Sequence
from typing import Protocol, TypeVar


T = TypeVar("T", bound="Entity")

class Repository(Protocol[T]):

    async def get(self, id: str) -> T | None: ...
    async def save(self, entity: T) -> None: ...
    async def find_all(self, ids: Sequence[str]) -> list[T]: ...

```

**Analysis:**

- All criteria pass
- Exemplary use of Protocol, TypeVar with bound, abstract params, concrete returns

**Output:**
```markdown
### [🟢 COMMENDATION] Exemplary Protocol Pattern

**Location:** `src/domain/repository.py`
**Criterion:** AP.2, AP.5, AP.1

**Observation:**
Excellent use of generic Protocol with properly bounded TypeVar.
Abstract `Sequence` parameter with concrete `list` return follows best practices.
```

**Verdict:** `PASS`

---

## Deep References

Load on-demand for complex reviews:

| Reference | When to Load | Path |
|-----------|--------------|------|
| Typing Patterns | Complex generics, variance questions | `refs/typing-patterns.md` |
| Engineering Principles | Type safety rationale | `rules/principles.md` |
| Python Conventions | Style integration | `rules/python.md` |

---

## Quality Gates

Before finalizing review output:

- [ ] All Python files in scope were analyzed
- [ ] Each finding has location + criterion ID + severity
- [ ] Verdict aligns with severity distribution
- [ ] Actionable code suggestions provided for non-PASS verdicts
- [ ] Chain decision is explicit and justified
- [ ] Output follows structured format
- [ ] Automated tool checks were executed where available
