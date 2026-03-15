# Extended Pydantic Patterns

> Load this reference for advanced patterns beyond the core SKILL.md.

---

## 1. Paginated Response Pattern

```python
from typing import Annotated, Generic, TypeVar
from pydantic import BaseModel, Field, ConfigDict, computed_field

T = TypeVar("T")

class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response wrapper."""
    model_config = ConfigDict(extra="forbid")

    items: Annotated[list[T], Field(description="Page items")]
    total: Annotated[int, Field(ge=0, description="Total item count")]
    page: Annotated[int, Field(ge=1, description="Current page number")]
    page_size: Annotated[int, Field(ge=1, le=100, description="Items per page")]

    @computed_field
    @property
    def total_pages(self) -> int:
        """Calculate total pages from total and page_size."""
        return (self.total + self.page_size - 1) // self.page_size

    @computed_field
    @property
    def has_next(self) -> bool:
        """Check if there's a next page."""
        return self.page < self.total_pages

    @computed_field
    @property
    def has_previous(self) -> bool:
        """Check if there's a previous page."""
        return self.page > 1

# Usage
users_page: PaginatedResponse[UserResponse] = PaginatedResponse(
    items=[user1, user2],
    total=42,
    page=1,
    page_size=20,
)
```

---

## 2. Nested Model Pattern

```python
from typing import Annotated
from pydantic import BaseModel, Field, ConfigDict

class Address(BaseModel):
    """Reusable address value object."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    street: Annotated[str, Field(min_length=1, description="Street address")]
    city: Annotated[str, Field(min_length=1, description="City name")]
    postal_code: Annotated[str, Field(pattern=r"^\d{5}(-\d{4})?$", description="ZIP code")]
    country: Annotated[str, Field(default="US", min_length=2, max_length=2, description="ISO country code")]

class Customer(BaseModel):
    """Customer with nested addresses."""
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    id: Annotated[str, Field(description="Customer identifier")]
    name: Annotated[str, Field(min_length=1, description="Customer name")]
    billing_address: Annotated[Address, Field(description="Billing address")]
    shipping_address: Annotated[Address | None, Field(default=None, description="Shipping address if different")]
```

---

## 3. Factory Pattern with Defaults

```python
from typing import Annotated
from uuid import UUID, uuid4
from datetime import datetime, UTC
from pydantic import BaseModel, Field, ConfigDict

class Order(BaseModel):
    """Order with factory-generated defaults."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: Annotated[UUID, Field(default_factory=uuid4, description="Order ID")]
    created_at: Annotated[datetime, Field(default_factory=lambda: datetime.now(UTC), description="Creation timestamp")]
    items: Annotated[list[OrderItem], Field(min_length=1, description="Order items")]
    total: Annotated[int, Field(ge=0, description="Total in cents")]

    @classmethod
    def create(cls, items: list[OrderItem]) -> "Order":
        """Factory method with computed total."""
        total = sum(item.price * item.quantity for item in items)
        return cls(items=items, total=total)

# Usage
order = Order.create(items=[item1, item2])  # id and created_at auto-generated
```

---

## 4. Request/Response DTO Pair

```python
from typing import Annotated
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict, computed_field, EmailStr

# Request DTO - Strict validation for untrusted input
class CreateUserRequest(BaseModel):
    """Request DTO for user creation."""
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    email: Annotated[EmailStr, Field(description="User email address")]
    name: Annotated[str, Field(min_length=1, max_length=100, description="Display name")]
    age: Annotated[int | None, Field(default=None, ge=0, le=150, description="Age in years")]

# Response DTO - Includes computed fields
class UserResponse(BaseModel):
    """Response DTO for user data."""
    model_config = ConfigDict(extra="forbid")

    id: Annotated[UUID, Field(description="User identifier")]
    email: Annotated[str, Field(description="User email")]
    name: Annotated[str, Field(description="Display name")]
    created_at: Annotated[datetime, Field(description="Account creation time")]

    @computed_field
    @property
    def profile_url(self) -> str:
        """Computed profile URL."""
        return f"/users/{self.id}"

# Update DTO - All fields optional for partial updates
class UpdateUserRequest(BaseModel):
    """Update DTO with optional fields."""
    model_config = ConfigDict(extra="forbid")

    email: Annotated[EmailStr | None, Field(default=None, description="New email")]
    name: Annotated[str | None, Field(default=None, min_length=1, max_length=100, description="New name")]

# Usage in service
def update_user(user_id: UUID, request: UpdateUserRequest) -> User:
    update_data = request.model_dump(exclude_unset=True)  # Only explicitly set fields
    return user_repo.update(user_id, **update_data)
```

---

## 5. Enum Integration

```python
from enum import Enum
from typing import Annotated
from pydantic import BaseModel, Field, ConfigDict

class OrderStatus(str, Enum):
    """Order lifecycle states."""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"

class Order(BaseModel):
    """Order with enum status."""
    model_config = ConfigDict(
        strict=True,
        frozen=True,
        extra="forbid",
        use_enum_values=True,  # Serialize as "pending" not OrderStatus.PENDING
    )

    id: Annotated[str, Field(description="Order ID")]
    status: Annotated[OrderStatus, Field(description="Current status")]
```

---

## 6. Conditional Validation

```python
from typing import Annotated, Self
from pydantic import BaseModel, Field, ConfigDict, model_validator

class Payment(BaseModel):
    """Payment with conditional validation."""
    model_config = ConfigDict(strict=True, extra="forbid")

    method: Annotated[str, Field(description="Payment method: card, bank, crypto")]
    card_number: Annotated[str | None, Field(default=None, description="Card number if method=card")]
    bank_account: Annotated[str | None, Field(default=None, description="Bank account if method=bank")]
    wallet_address: Annotated[str | None, Field(default=None, description="Wallet if method=crypto")]

    @model_validator(mode="after")
    def validate_method_fields(self) -> Self:
        """Ensure correct field is present for payment method."""
        match self.method:
            case "card":
                if not self.card_number:
                    raise ValueError("card_number required for card payment")
            case "bank":
                if not self.bank_account:
                    raise ValueError("bank_account required for bank payment")
            case "crypto":
                if not self.wallet_address:
                    raise ValueError("wallet_address required for crypto payment")
        return self
```

---

## 7. Recursive/Self-Referential Models

```python
from __future__ import annotations  # Required for forward references
from typing import Annotated
from pydantic import BaseModel, Field, ConfigDict

class TreeNode(BaseModel):
    """Self-referential tree structure."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    value: Annotated[str, Field(description="Node value")]
    children: Annotated[list[TreeNode], Field(default_factory=list, description="Child nodes")]

# Works because of `from __future__ import annotations`
root = TreeNode(
    value="root",
    children=[
        TreeNode(value="child1"),
        TreeNode(value="child2", children=[TreeNode(value="grandchild")]),
    ],
)
```

---

## 8. JSON Schema Customization

```python
from typing import Annotated
from pydantic import BaseModel, Field, ConfigDict

class Product(BaseModel):
    """Product with JSON Schema examples."""
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {"sku": "WIDGET-001", "name": "Blue Widget", "price": 999}
            ]
        },
    )

    sku: Annotated[str, Field(
        description="Stock keeping unit",
        json_schema_extra={"examples": ["WIDGET-001", "GADGET-002"]},
    )]
    name: Annotated[str, Field(description="Product name")]
    price: Annotated[int, Field(ge=0, description="Price in cents")]

# Generate schema
schema = Product.model_json_schema()
```

---

## 9. Private Attributes

```python
from typing import Annotated
from pydantic import BaseModel, Field, ConfigDict, PrivateAttr

class CacheableModel(BaseModel):
    """Model with internal cache (not serialized)."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    data: Annotated[list[int], Field(description="Raw data")]

    _cache: dict = PrivateAttr(default_factory=dict)  # Not in schema, not serialized

    def get_sum(self) -> int:
        """Cached computation."""
        if "sum" not in self._cache:
            self._cache["sum"] = sum(self.data)
        return self._cache["sum"]
```

---

## 10. Context-Aware Validation

```python
from typing import Annotated
from pydantic import BaseModel, Field, ConfigDict, ValidationInfo, field_validator

class FormData(BaseModel):
    """Form with context-aware validation."""
    model_config = ConfigDict(extra="forbid")

    password: Annotated[str, Field(min_length=8, description="Password")]
    confirm_password: Annotated[str, Field(description="Password confirmation")]

    @field_validator("confirm_password", mode="after")
    @classmethod
    def passwords_match(cls, v: str, info: ValidationInfo) -> str:
        """Validate password confirmation matches."""
        if "password" in info.data and v != info.data["password"]:
            raise ValueError("passwords do not match")
        return v
```
