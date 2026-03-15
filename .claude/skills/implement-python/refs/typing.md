# Python Typing Reference

> **Philosophy**: Types are documentation the compiler enforces. Be precise, explicit, and leverage modern Python.

---

## Quick Reference

| Pattern | Syntax |
|---------|--------|
| List/Dict | `list[str]`, `dict[str, int]` |
| Optional | `str \| None` |
| Callable | `Callable[[int], bool]` |
| Type alias | `Name: TypeAlias = ...` |
| Semantic ID | `Name = NewType("Name", str)` |
| Duck typing | `class X(Protocol): ...` |
| Self-return | `-> Self` |
| Constant | `X: Final = value` |

---

## 1. Hard Rules (Non-Negotiable)

### 1.1 Module Header

**MUST:**







- Include `from __future__ import annotations` as the first import in every module

```python
# ✅ REQUIRED

from __future__ import annotations

```





### 1.2 Modern Generics





**MUST:**


- Use built-in generic syntax (`list[str]`, `dict[str, int]`)
- Use union syntax with pipe (`str | None`, `User | Admin`)


**NEVER:**


- Import `List`, `Dict`, `Set`, `Tuple`, `Optional`, `Union` from `typing`

```python


# ❌ NEVER
from typing import List, Dict, Optional, Union
items: List[str]


config: Optional[Dict[str, int]]
result: Union[User, None]



# ✅ ALWAYS
items: list[str]
config: dict[str, int] | None


result: User | None
```



### 1.3 Explicit Return Types


**MUST:**



- Declare return type on every function

- Use `-> None` explicitly for side-effect functions

**NEVER:**


- Omit return type annotations


```python
# ❌ NEVER

def get_config(key: str):
    return config.get(key)



def log_event(event: Event):
    logger.info(event.serialize())


# ✅ ALWAYS


def get_config(key: str) -> str | None:
    return config.get(key)


def log_event(event: Event) -> None:
    logger.info(event.serialize())


```

### 1.4 Precise Callables


**MUST:**


- Specify full signature for all `Callable` types

**NEVER:**

- Use bare `Callable` without type parameters

```python

# ❌ NEVER
def register(callback: Callable) -> None: ...

# ✅ ALWAYS
def register(callback: Callable[[Event], None]) -> None: ...
```


---

## 2. Core Patterns

### 2.1 Accept Abstract, Return Concrete

**MUST:**

- Accept abstract types (`Sequence`, `Mapping`, `Iterable`) in parameters
- Return concrete types (`list`, `dict`, `set`) from functions

| Parameter Type | Return Type |
|----------------|-------------|
| `Sequence[T]` | `list[T]` |
| `Mapping[K, V]` | `dict[K, V]` |
| `Iterable[T]` | `list[T]`, `set[T]` |

```python
# ❌ Restricts callers unnecessarily
def process(items: list[str]) -> list[str]: ...

# ✅ Flexible input, predictable output
from collections.abc import Sequence

def process(items: Sequence[str]) -> list[str]:
    return [item.upper() for item in items]
```

### 2.2 Protocol Over ABC

**WHEN** defining interfaces for duck typing **THEN** use `Protocol`:

```python
# ❌ AVOID: Inheritance coupling
from abc import ABC, abstractmethod

class Repository(ABC):
    @abstractmethod
    def save(self, entity: Entity) -> None: ...

# ✅ PREFER: Structural typing
from typing import Protocol

class Repository(Protocol):
    def save(self, entity: Entity) -> None: ...

class UserRepo:  # No inheritance required
    def save(self, entity: Entity) -> None: ...
```

**Decision Matrix:**

| Scenario | Use |
|----------|-----|
| Duck typing / external code | `Protocol` |
| Shared implementation / mixins | `ABC` |

### 2.3 Sentinel for Missing vs None

**WHEN** `None` is a valid explicit value **THEN** use a sentinel:

```python
# ❌ Ambiguous: was None passed or omitted?
def update(name: str | None = None) -> None:
    if name is None:  # Cannot distinguish
        ...

# ✅ Sentinel distinguishes missing from explicit None
from typing import Final

class _Missing:
    __slots__ = ()
    def __repr__(self) -> str:
        return "<MISSING>"

MISSING: Final = _Missing()

def update(name: str | None | _Missing = MISSING) -> None:
    if name is MISSING:
        return  # Not provided
    # name is str | None — explicit value
    user.name = name
```

---

## 3. Generics & TypeVar

### Bound vs Constrained

```python
from typing import TypeVar

# Bound: Accepts Base and ALL subclasses
T_Comparable = TypeVar("T_Comparable", bound="Comparable")

# Constrained: EXACT types only (no subclasses, no mixing)
T_Number = TypeVar("T_Number", int, float)
```

### Variance Rules

| Variance | Use Case | Declaration |
|----------|----------|-------------|
| Covariant | Read-only (producers) | `T_co = TypeVar("T_co", covariant=True)` |
| Contravariant | Write-only (consumers) | `T_contra = TypeVar("T_contra", contravariant=True)` |
| Invariant | Read-write (default) | `T = TypeVar("T")` |

---

## 4. Function Signatures

### ParamSpec for Decorators

**WHEN** writing decorators that preserve signatures **THEN** use `ParamSpec`:

```python
from typing import ParamSpec, TypeVar
from collections.abc import Callable
from functools import wraps

P = ParamSpec("P")
R = TypeVar("R")

def retry(times: int) -> Callable[[Callable[P, R]], Callable[P, R]]:
    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            for attempt in range(times):
                try:
                    return func(*args, **kwargs)
                except Exception:
                    if attempt == times - 1:
                        raise
            raise RuntimeError("Unreachable")
        return wrapper
    return decorator
```

### Concatenate for Injected Args

**WHEN** a decorator injects arguments **THEN** use `Concatenate`:

```python
from typing import Concatenate

def with_context(
    func: Callable[Concatenate[Context, P], R]
) -> Callable[P, R]:
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        return func(get_current_context(), *args, **kwargs)
    return wrapper
```

---

## 5. Type Aliases & NewType

### TypeAlias for Complex Types

**WHEN** a type expression is long or repeated **THEN** create a `TypeAlias`:

```python
from typing import TypeAlias

JsonValue: TypeAlias = str | int | float | bool | None | list["JsonValue"] | dict[str, "JsonValue"]
Headers: TypeAlias = dict[str, str | list[str]]
```

### NewType for Semantic Safety

**WHEN** preventing accidental value mixing **THEN** use `NewType`:

```python
from typing import NewType

UserId = NewType("UserId", str)
OrderId = NewType("OrderId", str)

def get_user(user_id: UserId) -> User: ...

get_user(OrderId("ord_456"))  # ❌ Type error!
get_user(UserId("usr_123"))   # ✅ Correct
```

| Goal | Use |
|------|-----|
| Shorten complex types | `TypeAlias` |
| Prevent value mixing | `NewType` |

---

## 6. Advanced Patterns

### TYPE_CHECKING Guard

**WHEN** imports cause circular dependencies or are expensive **THEN** guard with `TYPE_CHECKING`:

```python
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from expensive_module import HeavyClass  # Zero runtime cost
    from .models import User  # Breaks circular import
```

### Overloads for Conditional Returns

**WHEN** return type depends on argument values **THEN** use `@overload`:

```python
from typing import overload, Literal

@overload
def fetch(id: str, required: Literal[True]) -> User: ...
@overload
def fetch(id: str, required: Literal[False] = ...) -> User | None: ...

def fetch(id: str, required: bool = False) -> User | None:
    user = db.get(id)
    if user is None and required:
        raise UserNotFoundError(id)
    return user
```

### TypeGuard for Custom Narrowing

**WHEN** type checker cannot infer narrowing **THEN** use `TypeGuard`:

```python
from typing import TypeGuard

def is_string_list(val: list[object]) -> TypeGuard[list[str]]:
    return all(isinstance(item, str) for item in val)

def process(items: list[object]) -> None:
    if is_string_list(items):
        # Type checker knows: items is list[str]
        print(items[0].upper())
```

### Self Type

**WHEN** returning `self` from methods **THEN** use `Self`:

```python
from typing import Self

class Builder:
    def with_name(self, name: str) -> Self:
        self.name = name
        return self
```

---

## 7. TypedDict & Literal

### TypedDict for Structured Dicts

**WHEN** dicts have known keys **THEN** use `TypedDict`:

```python
from typing import TypedDict, NotRequired

class UserPayload(TypedDict):
    id: str
    email: str
    metadata: NotRequired[dict[str, str]]
```

### Literal for Exact Values

**WHEN** restricting to specific values **THEN** use `Literal`:

```python
from typing import Literal

Status = Literal["pending", "active", "suspended"]

def set_status(user_id: str, status: Status) -> None: ...
```

---

## Patterns & Anti-Patterns

### ✅ Do

- Use `from __future__ import annotations` at module top
- Use built-in generics (`list[str]`) not `typing` imports
- Use union syntax (`X | Y`) not `Union[X, Y]`
- Declare `-> None` explicitly for procedures
- Accept abstract (`Sequence`, `Mapping`), return concrete (`list`, `dict`)
- Use `Protocol` for duck typing interfaces
- Specify full `Callable` signatures
- Use `TYPE_CHECKING` guard for circular/heavy imports

### ❌ Don't

- Import `List`, `Dict`, `Optional`, `Union` from `typing`
- Omit return type annotations
- Use bare `Callable` without signature
- Accept concrete types when abstract would work
- Use `ABC` when only interface shape matters
- Use `Any` without documented reason
- Ignore type checker errors with bare `# type: ignore`

---

## Decision Tree

```
Need a type annotation?
    │
    ├─► Function parameter?
    │       └─► Use abstract type (Sequence, Mapping, Iterable)
    │
    ├─► Function return?
    │       └─► Use concrete type (list, dict, set)
    │       └─► Side-effect only? → -> None
    │
    ├─► Optional value?
    │       └─► T | None (not Optional[T])
    │
    ├─► Callback/function?
    │       └─► Callable[[ArgTypes], ReturnType]
    │
    ├─► Need interface?
    │       ├─► Duck typing? → Protocol
    │       └─► Shared implementation? → ABC
    │
    ├─► Prevent ID mixing?
    │       └─► NewType
    │
    └─► Complex repeated type?
            └─► TypeAlias
```

---

## Pre-Commit Checklist

- [ ] `from __future__ import annotations` at module top
- [ ] No imports from `typing` for built-in generics
- [ ] Union syntax (`X | Y`) not `Union[X, Y]`
- [ ] Explicit `-> None` for procedures
- [ ] Abstract params (`Sequence`, `Mapping`), concrete returns
- [ ] Protocol for duck typing interfaces
- [ ] Precise `Callable` signatures (no bare `Callable`)
- [ ] `TYPE_CHECKING` guard for circular/heavy imports
- [ ] No `Any` without documented reason
- [ ] No bare `# type: ignore` without explanation
