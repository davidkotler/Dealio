---
name: implement-pydantic
version: 2.0.0
description: |
  Generate Pydantic V2 models with strict validation, immutability, and proper serialization.
  Use when creating data models, DTOs, request/response schemas, events schemas, settings, or validation logic.
  Relevant for Python type-safe data handling, API contracts, Events contracts, configuration management.
---

# Pydantic V2 Implementation

> Generate type-safe, immutable Pydantic models with strict validation and V2 patterns.

## Quick Reference

| Aspect | Details |
|--------|---------|
| **Invokes** | `implement/database` (ORM), `implement/api` (routes) |
| **Invoked By** | `implement/python`, `implement/api`, `implement/event` |
| **Key Tools** | Write, Edit, Bash(pytest) |

---

## 1. Hard Rules

### Module Header — REQUIRED







```python
from __future__ import annotations
```

### V2 Migration — NEVER Use V1 Patterns

| ❌ NEVER (V1) | ✅ ALWAYS (V2) |
|---------------|----------------|
| `class Config:` | `model_config = ConfigDict(...)` |
| `.dict()` / `.json()` | `.model_dump()` / `.model_dump_json()` |
| `.parse_obj(data)` | `.model_validate(data)` |
| `@validator` | `@field_validator` + `@classmethod` |
| `@root_validator` | `@model_validator` |
| `Optional[X]` / `List[str]` | `X \| None` / `list[str]` |

### ConfigDict — REQUIRED for All Models

**MUST:** Include `model_config = ConfigDict(...)` in every model. Use `strict=True` for DTOs, `frozen=True` for domain models, `extra="forbid"` for API contracts.

**NEVER:** Use `class Config:` (V1), `extra="ignore"` for request DTOs.

---

## 2. Field Definitions — Annotated Syntax REQUIRED

**MUST:** Use `Annotated[type, Field(description=...)]` for all fields. Use built-in constraints over custom validators.

```python
from typing import Annotated
from pydantic import BaseModel, Field, ConfigDict

class Order(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    id: Annotated[str, Field(description="Order identifier")]
    amount: Annotated[int, Field(ge=0, description="Amount in cents")]
    email: Annotated[str, Field(pattern=r"^[\w\.-]+@[\w\.-]+\.\w+$", description="Email")]
```

| Constraint | Type | Example |
|------------|------|---------|
| `ge`, `gt`, `le`, `lt` | Numeric | `Field(ge=0, lt=100)` |
| `min_length`, `max_length` | Str/List | `Field(min_length=1)` |
| `pattern` | String | `Field(pattern=r"^[A-Z]+$")` |

---

## 3. Validators

### Field Validator — MUST include `@classmethod` and explicit `return`

```python
from pydantic import field_validator

class Product(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    sku: Annotated[str, Field(description="Stock keeping unit")]

    @field_validator("sku", mode="before")  # mode="before" for normalization
    @classmethod
    def normalize_sku(cls, v: str) -> str:
        return v.upper().strip() if isinstance(v, str) else v
```

### Model Validator — For cross-field validation

```python
from pydantic import model_validator
from typing import Self

class DateRange(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    start: Annotated[datetime, Field(description="Start date")]
    end: Annotated[datetime, Field(description="End date")]

    @model_validator(mode="after")
    def validate_order(self) -> Self:
        if self.end <= self.start:
            raise ValueError("end must be after start")
        return self
```

---

## 4. Serialization

```python
user.model_dump()                    # → dict (not .dict())
user.model_dump_json()               # → JSON string (not .json())
request.model_dump(exclude_unset=True)  # PATCH: only explicit fields
model.model_dump(mode="json")        # JSON-compatible (converts datetime, UUID)
```

---

## 5. Settings

**MUST:** Use `SecretStr` for secrets, `@lru_cache` + `get_settings()`, no default for required config.

```python
from functools import lru_cache
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="forbid")

    database_url: Annotated[str, Field(description="PostgreSQL URL")]  # Required: no default
    api_key: Annotated[SecretStr, Field(description="API key")]        # Secret: SecretStr
    debug: Annotated[bool, Field(default=False, description="Debug")]  # Optional: has default

@lru_cache
def get_settings() -> Settings:
    return Settings()
```

---

## 6. Decision Tree

```
Model Type?
├─► Request DTO  → strict=True, frozen=True, extra="forbid"
├─► Response DTO → extra="forbid", computed_field for derived
├─► Domain Model → frozen=True, model_validator for invariants
├─► Update/Patch → All fields T | None, exclude_unset=True
└─► Settings     → pydantic-settings, SecretStr, @lru_cache
```

---

## 7. Common Patterns

### Discriminated Union — For polymorphism

```python
from typing import Annotated, Literal, Union

class CardPayment(BaseModel):
    type: Literal["card"]
    card_number: Annotated[str, Field(description="Card number")]

class BankPayment(BaseModel):
    type: Literal["bank"]
    account: Annotated[str, Field(description="Account")]

Payment = Annotated[Union[CardPayment, BankPayment], Field(discriminator="type")]
```

### Computed Field

```python
from pydantic import computed_field

class Rectangle(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    width: Annotated[float, Field(gt=0, description="Width")]
    height: Annotated[float, Field(gt=0, description="Height")]

    @computed_field
    @property
    def area(self) -> float:
        return self.width * self.height
```

---

## 8. Error Handling — Preserve structure

```python
from pydantic import ValidationError

try:
    return User.model_validate(data)
except ValidationError as e:
    return {"errors": [
        {"field": ".".join(str(loc) for loc in err["loc"]), "msg": err["msg"]}
        for err in e.errors()
    ]}
# ❌ NEVER: str(e) — loses structure
```

---

## 9. Skill Chaining

| Condition | Invoke | Handoff |
|-----------|--------|---------|
| ORM mapping | `implement/database` | Table schema |
| API routes | `implement/api` | Request/response models |
| Event payloads | `implement/event` | Event types |
| Tests needed | `test/unit` | Model classes, edge cases |



---



## 10. Patterns & Anti-Patterns





### ✅ Do


- `from __future__ import annotations` at module top
- `Annotated[T, Field(description=...)]` for all fields

- `model_config = ConfigDict(...)` in every model
- `SecretStr` for secrets, `@lru_cache` + `get_settings()`

- `Field(ge=, pattern=)` built-in constraints
- Explicit `return` in all validators with `@classmethod`


### ❌ Don't

- `class Config:` / `.dict()` / `.json()` / `@validator` (V1)
- `Optional[X]` / `List[str]` (use `X | None` / `list[str]`)
- `extra="ignore"` for request DTOs
- Implicit return in validators
- `str` for secrets (use `SecretStr`)

- Direct import of settings (use `get_settings()`)

---


## Quality Gates


- [ ] `from __future__ import annotations` at module top
- [ ] All fields: `Annotated[T, Field(description=...)]`
- [ ] `model_config = ConfigDict(...)` in every model

- [ ] DTOs: `strict=True`, `extra="forbid"`
- [ ] No V1 patterns (`class Config`, `.dict()`, `@validator`)
- [ ] Validators: explicit `return`, `@classmethod`

- [ ] Secrets: `SecretStr`; Settings: `@lru_cache` + `get_settings()`
- [ ] Discriminated unions: `Field(discriminator=...)`


---

## Deep References

- **[refs/patterns.md](refs/patterns.md)**: Pagination, nested models, factories
- **[refs/typing.md](../python/refs/typing.md)**: Python typing integration
