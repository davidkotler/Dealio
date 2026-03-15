# Python Style Reference

> **Target:** Python 3.13+ | **Enforcement:** ruff + ty strict

---

## Quick Reference Table

| ✅ MUST | ❌ NEVER |
|---------|----------|
| `if (x := func()):` | `x = func(); if x:` |
| `match event:` | `if/elif/elif` chains (3+ branches) |
| `d1 \| d2` | `{**d1, **d2}` |
| `enumerate(items)` | `range(len(items))` |
| `zip(..., strict=True)` | `zip(...)` without strict |
| `frozenset({...})` | `list` for membership tests |
| `StrEnum` + `auto()` | `(str, Enum)` mixin |
| `Path() / "x"` | `os.path.join()` |
| `f"{x}"` | `.format()` or `%` |
| `*, kwarg` | Positional args (2+ params) |
| `None` + `or []` | Mutable default `=[]` |
| `@contextmanager` | Manual `try/finally` |
| `except*` for TaskGroup | Bare `except:` |
| `@wraps(func)` | Bare wrapper function |
| `partial(fn, arg)` | `lambda x: fn(arg, x)` |
| `batched(items, n)` | Manual chunking loops |

---

## 1. Modern Syntax

### Assignment Expressions (Walrus)

**MUST** use walrus operator for assign-and-test patterns.

```python
# ✅ Pattern
if (match := pattern.search(text)) is not None:
    process(match.group())

while (chunk := file.read(8192)):
    handle(chunk)

if (user := get_user(id)) and user.is_active:
    return user
```

```python
# ❌ Anti-pattern
match = pattern.search(text)
if match is not None:
    process(match.group())
```

---

### Structural Pattern Matching

**WHEN** branching on structured data with 3+ cases **THEN** use `match/case`.

```python
# ✅ Pattern
match event:
    case {"type": "click", "x": x, "y": y}:
        handle_click(x, y)
    case {"type": "key", "code": code} if code in ALLOWED_KEYS:
        handle_key(code)
    case _:
        raise UnhandledEventError(event)
```

```python
# ❌ Anti-pattern
if event.get("type") == "click":
    handle_click(event["x"], event["y"])
elif event.get("type") == "key" and event.get("code") in ALLOWED_KEYS:
    handle_key(event["code"])
else:
    raise UnhandledEventError(event)
```

---

### Dictionary Operations

**MUST** use union operators for dict merging.

```python
# ✅ Pattern
merged = defaults | overrides          # Union
config |= runtime_settings             # In-place union
```

```python
# ❌ Anti-pattern
merged = {**defaults, **overrides}
config.update(runtime_settings)
```

---

### Iteration

**MUST** use `enumerate` and `zip(strict=True)`.

```python
# ✅ Pattern
for idx, item in enumerate(items):
    process(idx, item)

for a, b in zip(xs, ys, strict=True):  # Raises if lengths differ
    combine(a, b)
```

```python
# ❌ Anti-pattern
for i in range(len(items)):
    process(i, items[i])

for a, b in zip(xs, ys):  # Silent truncation bug
    combine(a, b)
```

---

### Collections

**MUST** use `frozenset` for O(1) membership constants.  
**MUST** use `StrEnum` for string-valued enums.

```python
# ✅ Pattern
VALID_STATUSES: frozenset[str] = frozenset({"pending", "active", "closed"})

class Status(StrEnum):
    PENDING = auto()
    ACTIVE = auto()

from collections import defaultdict, Counter, deque
word_counts = Counter(words)
graph: defaultdict[str, list[str]] = defaultdict(list)
buffer: deque[Event] = deque(maxlen=100)
```

```python
# ❌ Anti-pattern
VALID_STATUSES = ["pending", "active", "closed"]  # O(n) lookup

class Status(str, Enum):  # Verbose mixin
    PENDING = "pending"
```

---

## 2. Itertools & Functools

**MUST** use standard library utilities over manual implementations.

| Use Case | ✅ MUST | ❌ NEVER |
|----------|---------|----------|
| Chunking | `batched(items, n)` | Manual slice loops |
| Flatten | `chain.from_iterable(nested)` | Nested comprehension |
| Lazy slice | `islice(gen, n)` | `list(gen)[:n]` |
| Partial app | `partial(fn, arg)` | `lambda x: fn(arg, x)` |
| Unbounded cache | `@cache` | Manual dict cache |
| Bounded cache | `@lru_cache(maxsize=N)` | Custom LRU |

```python
# ✅ Pattern
from itertools import chain, islice, batched
from functools import cache, lru_cache, partial

for batch in batched(items, 100):
    process_batch(batch)

all_items = chain.from_iterable(nested_lists)
first_100 = islice(infinite_generator, 100)

@cache
def fib(n: int) -> int:
    return n if n < 2 else fib(n - 1) + fib(n - 2)

send_alert = partial(send_message, channel="alerts")
```

---

## 3. Decorators

**MUST** use `@wraps` + `ParamSpec`/`TypeVar` for typed decorators.

```python
# ✅ Pattern
from functools import wraps
from typing import ParamSpec, TypeVar, Callable

P = ParamSpec("P")
R = TypeVar("R")

def logged(func: Callable[P, R]) -> Callable[P, R]:
    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        logger.info(f"Calling {func.__name__}")
        return func(*args, **kwargs)
    return wrapper

# Decorator order: outermost executes first
@logged      # 1st
@retry(3)    # 2nd
def fetch(): ...
```

```python
# ❌ Anti-pattern
def logged(func):  # Untyped, loses signature
    def wrapper(*args, **kwargs):  # No @wraps breaks introspection
        logger.info(f"Calling {func.__name__}")
        return func(*args, **kwargs)
    return wrapper
```

---

## 4. Context Management

**MUST** use `contextlib` utilities.

| Use Case | Tool |
|----------|------|
| Ignore specific exceptions | `suppress(ExcType)` |
| Dynamic context manager count | `ExitStack` |
| Conditional context manager | `nullcontext()` |
| Request-scoped state | `ContextVar` |
| Task isolation | `copy_context()` |

```python
# ✅ Pattern
from contextlib import suppress, ExitStack, nullcontext
from contextvars import ContextVar, copy_context

with suppress(FileNotFoundError):
    path.unlink()

with ExitStack() as stack:
    files = [stack.enter_context(p.open()) for p in paths]

lock_cm = lock if use_lock else nullcontext()
with lock_cm:
    do_work()

request_id: ContextVar[str] = ContextVar("request_id", default="")
```

---

## 5. Metaprogramming

**PREFER** `__init_subclass__` over metaclasses.  
**PREFER** `__set_name__` for descriptor naming.

```python
# ✅ Pattern: Subclass registration without metaclass
class Plugin:
    _registry: ClassVar[dict[str, type[Plugin]]] = {}

    def __init_subclass__(cls, *, name: str, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        Plugin._registry[name] = cls

class JSONPlugin(Plugin, name="json"): ...
```

```python
# ✅ Pattern: Descriptor with automatic naming
class Field:
    def __set_name__(self, owner: type, name: str) -> None:
        self.name = f"_{name}"
```

| ✅ PREFER | ❌ AVOID |
|-----------|----------|
| `__init_subclass__` | Metaclass for registration |
| `__set_name__` | Manual descriptor naming |
| `typing.get_type_hints()` | `__annotations__` directly |
| `Protocol` | ABC for structural typing |

---

## 6. Code Structure

### Comprehensions

**MUST** use comprehensions for simple transforms.  
**WHEN** logic exceeds one condition **THEN** use explicit loop.

```python
# ✅ Pattern
squares = [x ** 2 for x in numbers if x > 0]
lookup = {user.id: user for user in users}
total = sum(order.amount for order in orders)  # Generator for aggregation
```

```python
# ❌ Anti-pattern: Manual accumulation
result = []
for x in numbers:
    if x > 0:
        result.append(x ** 2)
```

---

### RORO Pattern (Receive Object, Return Object)

**WHEN** function has 3+ params or complex returns **THEN** use structured I/O.

```python
# ✅ Pattern
@dataclass(frozen=True, slots=True)
class CreateUserRequest:
    email: str
    name: str
    role: UserRole = UserRole.MEMBER

@dataclass(frozen=True, slots=True)
class CreateUserResponse:
    user_id: UUID
    created_at: datetime

def create_user(request: CreateUserRequest) -> CreateUserResponse: ...
```

---

### Function Design

| Rule | Implementation |
|------|----------------|
| Keyword-only args | `def func(*, arg1, arg2)` for 2+ params |
| Max length | 30 lines; extract helpers |
| Single return type | No `X \| None` for success paths |
| No mutable defaults | `None` + `or []` pattern |

```python
# ✅ Pattern
def process_items(
    items: list[Item],
    *,
    filters: list[Filter] | None = None,
    limit: int = 100,
) -> list[Result]:
    filters = filters or []
    ...
```

```python
# ❌ Anti-pattern: Mutable default bug
def process_items(items, filters=[]):  # Shared across calls!
    ...
```

---

### Control Flow

**MUST** use early returns to reduce nesting.  
**ALLOWED** one-line guards for simple cases.

```python
# ✅ Pattern
def process(data: Data) -> Result:
    if not data.is_valid:
        raise ValidationError(data.errors)
    if data.is_cached:
        return cache.get(data.key)
    return compute(data)

# One-line guard (allowed)
if not user.is_active: raise InactiveUserError(user.id)
```

```python
# ❌ Anti-pattern: Deep nesting
def process(data: Data) -> Result:
    if data.is_valid:
        if not data.is_cached:
            return compute(data)
        else:
            return cache.get(data.key)
    else:
        raise ValidationError(data.errors)
```

---

### Exception Groups (3.11+)

**MUST** use `except*` for concurrent exception handling.

```python
# ✅ Pattern
async def fetch_all(urls: list[str]) -> list[Response]:
    try:
        async with TaskGroup() as tg:
            tasks = [tg.create_task(fetch(url)) for url in urls]
    except* ConnectionError as eg:
        logger.error(f"Connection failures: {len(eg.exceptions)}")
        raise
```

---

### Path Handling

**MUST** use `pathlib` for all path operations.

```python
# ✅ Pattern
from pathlib import Path
config_path = Path(__file__).parent / "config" / "settings.yaml"
```

```python
# ❌ Anti-pattern
import os
config_path = os.path.join(os.path.dirname(__file__), "config", "settings.yaml")
```

---

## 7. Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Modules | `snake_case` | `user_service.py` |
| Classes | `PascalCase` | `UserRepository` |
| Functions/Vars | `snake_case` | `get_active_users` |
| Constants | `SCREAMING_SNAKE` | `MAX_RETRIES` |
| TypeVars | `PascalCase` + `T` | `ItemT`, `ResponseT` |
| Protocols | Descriptive | `Comparable`, `Serializable` |

### Boolean Naming

**MUST** use auxiliary verbs for booleans.

| Prefix | Meaning | Example |
|--------|---------|---------|
| `is_` | State | `is_active`, `is_valid` |
| `has_` | Possession | `has_permission`, `has_children` |
| `can_` | Capability | `can_edit`, `can_delete` |
| `should_` | Recommendation | `should_retry`, `should_cache` |
| `was_` | Past state | `was_processed`, `was_deleted` |

```python
# ✅ Pattern
is_active: bool
has_permission: bool
def is_valid_email(email: str) -> bool: ...
def has_exceeded_limit(user: User) -> bool: ...
```

```python
# ❌ Anti-pattern: Ambiguous
active: bool      # Adjective? Noun?
permission: bool  # Has it? Is it?
valid: bool       # Valid what?
```

---

## 8. Imports

### Module-Level Only

**MUST** organize imports in groups: stdlib → third-party → local.

```python
# ✅ Pattern
from __future__ import annotations

import json                              # stdlib
from collections.abc import Iterator

from pydantic import BaseModel           # third-party

from app.core.config import settings     # local
from app.domain.user import User

if TYPE_CHECKING:                        # Cycle-breaking only
    from app.services.email import EmailService
```

### Explicit Import Paths

**MUST** import from defining module or package `__init__.py`.

---

## 9. Strings & Formatting

**MUST** use f-strings with double quotes.  
**MUST** use parentheses for continuation.  
**MUST** include trailing commas in multi-line structures.

```python
# ✅ Pattern
message = f"User {user.name} created at {user.created_at:%Y-%m-%d}"

result = (
    some_long_function_name(arg1, arg2)
    .chain_method()
    .another_method()
)

config = {
    "host": "localhost",
    "port": 8080,
    "debug": True,  # <- trailing comma
}
```

```python
# ❌ Anti-pattern
message = "User {} created at {}".format(user.name, user.created_at)
message = "User %s created at %s" % (user.name, user.created_at)

result = some_long_function_name(arg1, arg2) \
    .chain_method() \
    .another_method()
```

---

## 10. Entry Point

**MUST** guard executable modules.

```python
# ✅ Pattern
def main() -> None:
    app.run()

if __name__ == "__main__":
    main()
```

---

## 11. Documentation (Google Style)

**MUST** document what and why, not how.  
**MUST** document failure modes with `Raises:`.  
**NEVER** repeat types from signature.

```python
# ✅ Pattern
def calculate_discount(
    order: Order,
    *,
    coupon_code: str | None = None,
) -> Decimal:
    """Calculate final discount for an order.

    Applies tiered pricing based on order total, then stacks
    any valid coupon. Coupons cannot reduce price below $1.

    Args:
        order: The order to calculate discount for.
        coupon_code: Optional promotional code.

    Returns:
        The discount amount as a positive Decimal.

    Raises:
        InvalidCouponError: If coupon_code is expired or invalid.

    Example:
        >>> discount = calculate_discount(order, coupon_code="SAVE20")
        >>> order.total - discount
        Decimal("80.00")
    """
```

| ✅ MUST | ❌ NEVER |
|---------|----------|
| Document *what* and *why* | Repeat types from signature |
| Document `Raises:` | Describe *how* (implementation) |
| `Example:` for complex APIs | Over-document obvious code |

---

## Decision Tree

```
New Python Code
    │
    ├─► 3+ branches on structured data?
    │       └─► Use match/case
    │
    ├─► Merging dicts?
    │       └─► Use `d1 | d2` or `d |= other`
    │
    ├─► Iterating with index?
    │       └─► Use enumerate()
    │
    ├─► Pairing two sequences?
    │       └─► Use zip(strict=True)
    │
    ├─► Membership test constant?
    │       └─► Use frozenset
    │
    ├─► String-valued enum?
    │       └─► Use StrEnum + auto()
    │
    ├─► Path manipulation?
    │       └─► Use pathlib.Path
    │
    ├─► 3+ function params?
    │       └─► Use keyword-only (*)
    │
    ├─► Complex return + params?
    │       └─► Use RORO pattern (dataclasses)
    │
    ├─► Need caching?
    │       └─► Pure + unbounded → @cache
    │       └─► Bounded → @lru_cache(maxsize=N)
    │
    └─► Writing decorator?
            └─► Use @wraps + ParamSpec + TypeVar
```

---

## Quality Gates

Before completing Python implementation:

- [ ] All functions have type hints
- [ ] No mutable default arguments
- [ ] `zip()` calls use `strict=True`
- [ ] Paths use `pathlib.Path`
- [ ] Booleans use auxiliary verb prefixes
- [ ] Imports are from defining modules or package `__init__.py`
- [ ] Comprehensions used for simple transforms
- [ ] Early returns reduce nesting
- [ ] Docstrings follow Google style (if public API)
