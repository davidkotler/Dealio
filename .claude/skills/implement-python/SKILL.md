---
name: implement-python
version: 1.0.0
description: |
  Generate production-quality Python 3.13+ code with modern idioms, strict typing, and clean architecture.
  Use when implementing Python modules, classes, functions, scripts, or refactoring existing Python code.
  Relevant for backend services, CLI tools, data processing, domain logic, and library development.
---

# Python Implementation

> Write Python that humans love to read and machines love to verify.

| Aspect | Details |
|--------|---------|
| **Target** | Python 3.13+ with strict ty |
| **Invokes** | `implement/pydantic`, `implement/api`, `implement/database`, `test/unit` |
| **Invoked By** | `design/*`, `refactor/*`, commands (`/implement`) |

---

## Core Workflow

1. **Contextualize**: Read existing code structure and conventions
2. **Design**: Plan types and signatures before implementation
3. **Implement**: Write code following decision trees below
4. **Type**: Apply strict typing (see [refs/typing.md](refs/typing.md))
5. **Style**: Apply modern idioms (see [refs/style.md](refs/style.md))
6. **Chain**: Invoke downstream skills for specialized concerns

---

## Module Template

```python
"""<Module purpose - one line>."""
from __future__ import annotations

import <stdlib>
from collections.abc import <abstract-types>
from typing import TYPE_CHECKING, Final

import <third-party>
from <local> import <specific-names>

if TYPE_CHECKING:
    from <circular-or-heavy> import <types-only>
```

---

## Decision Trees

### Function vs Class

```
Need behavior?
    ├─► Stateless transformation? ──► Pure function
    ├─► Multiple ops on same data? ──► @dataclass + functions
    ├─► Encapsulated mutable state? ──► Class (minimal interface)
    ├─► Polymorphic behavior?
    │       ├─► Structural typing? ──► Protocol
    │       └─► Shared impl? ──► ABC + mixins
    └─► Dependency injection? ──► Class accepting collaborators
```

### Sync vs Async

```
I/O operation?
    ├─► Network/DB/File? ──► async def
    ├─► CPU-bound? ──► def (sync)
    └─► Pure transformation? ──► def (sync)
```

### Error Handling

```
Can fail?
    ├─► Programmer error? ──► raise immediately
    ├─► Expected failure?
    │       ├─► Must handle? ──► Custom exception
    │       └─► Recoverable? ──► Return T | None
    └─► Infrastructure? ──► Propagate + log
```

### Type Choice

```
Need a type?
    ├─► Data container? ──► @dataclass(frozen=True, slots=True)
    ├─► API boundary? ──► Pydantic BaseModel → invoke implement/pydantic
    ├─► Semantic ID? ──► NewType
    ├─► Complex annotation? ──► TypeAlias
    └─► Interface? ──► Protocol
```

---

## Essential Patterns

### Pure Function (Default)

```python
def calculate_discount(
    subtotal: Money,
    *,
    tier: CustomerTier,
    codes: Sequence[str] | None = None,
) -> Money:
    """Calculate discount for order subtotal."""
    codes = codes or []
    tier_discount = _get_tier_discount(tier, subtotal)
    return Money(tier_discount + _apply_promos(codes, subtotal))
```

### Service with DI

```python
class OrderService:
    def __init__(
        self,
        repository: OrderRepository,
        payment: PaymentGateway,
    ) -> None:
        self._repository = repository
        self._payment = payment

    async def place_order(self, request: PlaceOrderRequest) -> Order:
        order = Order.from_request(request)
        await self._payment.authorize(order.total, request.payment_token)
        await self._repository.save(order)
        return order
```

### Protocol Interface

```python
@runtime_checkable
class Repository(Protocol[T]):
    async def get(self, id: str) -> T | None: ...
    async def save(self, entity: T) -> None: ...
```

---

## Skill Chaining

| Condition | Invoke | Handoff |
|-----------|--------|---------|
| Pydantic models | `implement/pydantic` | Field types, validation |
| FastAPI routes | `implement/api` | Routes, request/response |
| Database queries | `implement/database` | Tables, patterns |
| Complete | `test/unit` | Signatures, edge cases |

---

## Critical Rules

### ✅ MUST

- `from __future__ import annotations` first
- Type hints on all functions (params + return + `-> None`)
- Keyword-only args (`*`) for 2+ parameters
- `zip(..., strict=True)` always
- `pathlib.Path` for paths
- `frozenset` for membership constants
- Early returns to reduce nesting
- Structured logging (never `print()`)

### ❌ NEVER

- Import `List`, `Dict`, `Optional`, `Union` from typing
- Mutable default arguments (`def f(x=[])`)
- Bare `except:` or `except Exception:`
- `type: ignore` without explanation
- In-place mutation of inputs
- Module-level mutable state
- Functions > 30 lines

---

## Modern Syntax

| ✅ Use | ❌ Avoid |
|--------|----------|
| `str \| None` | `Optional[str]` |
| `list[str]` | `List[str]` |
| `d1 \| d2` | `{**d1, **d2}` |
| `if (x := f()):` | `x = f(); if x:` |
| `match val:` (3+ branches) | `if/elif/elif` |
| `enumerate(items)` | `range(len(items))` |
| `StrEnum + auto()` | `(str, Enum)` |
| `@cache` / `@lru_cache` | Manual cache |

---

## Docstring (Google Style)

```python
def process(order: Order, *, token: str) -> PaymentResult:
    """Process payment for an order.

    Args:
        order: The order to process.
        token: Payment provider token.

    Returns:
        Payment result with transaction ID.

    Raises:
        PaymentDeclinedError: If authorization fails.
    """
```

---

## Quality Gates

Before completing:

- [ ] `from __future__ import annotations` present
- [ ] All functions have type hints (params + return)
- [ ] No typing imports for built-in generics
- [ ] Union syntax (`X | Y`) not `Union[X, Y]`
- [ ] Keyword-only (`*`) for 2+ args
- [ ] No mutable defaults
- [ ] `zip()` uses `strict=True`
- [ ] Paths use `pathlib.Path`
- [ ] Booleans use `is_`, `has_`, `can_`
- [ ] Functions ≤ 30 lines
- [ ] Public APIs have docstrings
- [ ] No bare `except:`

---

## Deep References

- **[refs/style.md](refs/style.md)**: Complete style guide
- **[refs/typing.md](refs/typing.md)**: Comprehensive typing patterns

*Target: Code passes `ruff check`, `ty check`, and human review on first pass.*
