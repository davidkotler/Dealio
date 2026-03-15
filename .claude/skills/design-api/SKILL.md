---
name: design-api
version: 2.0.0
description: |
  Design REST API endpoint contracts before implementation — producing endpoint descriptors,
  Pydantic request/response models, behavior specs, and status codes.
  Use when creating new endpoints, designing API resources, planning REST services,
  reviewing API contracts, or before implementing HTTP handlers.
  Relevant for REST design, endpoint planning, API-first development, Pydantic models.
---

# API Design

> Design production-ready REST endpoint contracts before writing implementation code.

## Quick Reference

| Aspect | Details |
|--------|---------|
| **Invokes** | `implement/api`, `implement/pydantic`, `design/event` |
| **Invoked By** | `design/code`, `implement/python` |
| **Key Artifacts** | Endpoint descriptors, Pydantic models, behavior specs |

---

## Why Not OpenAPI?

OpenAPI specs are auto-generated from implementation code (Pydantic models + FastAPI routes).
Writing OpenAPI by hand creates drift risk and duplicates what the code already produces.
Instead, design endpoint contracts that are clear enough to drive implementation directly.

---

## Core Workflow

1. **Identify Resources**: Extract domain nouns as API resources
2. **List Endpoints**: Write descriptive endpoint list with responsibilities
3. **Define Models**: Specify request/response Pydantic models with field constraints
4. **Specify Behavior**: Document happy path, edge cases, and error scenarios
5. **Assign Status Codes**: Map each outcome to the correct HTTP status
6. **Validate**: Check against REST principles before implementation

---

## Must / Never

### Resource Naming

**MUST:**
- Use plural nouns for collections: `/users`, `/orders`, `/products`
- Use lowercase with hyphens: `/user-profiles`, `/order-items`
- Use path parameters for identifiers: `/users/{userId}`
- Use query parameters for filtering: `/users?status=active`

**NEVER:**
- Use verbs in resource paths: ~~`/getUsers`~~, ~~`/createOrder`~~
- Use trailing slashes: ~~`/users/`~~
- Use CRUD names: ~~`/getAllUsers`~~, ~~`/deleteUser`~~
- Use camelCase/snake_case in URLs: ~~`/userProfiles`~~

### HTTP Methods

**MUST:**
- GET for retrieval (safe, idempotent)
- POST for creation with server-generated IDs
- PUT for full replacement (idempotent)
- PATCH for partial updates
- DELETE for removal (idempotent)

**NEVER:**
- Use POST for retrieval operations
- Use GET with request bodies
- Use PUT for partial updates
- Ignore idempotency semantics

### Contracts

**MUST:**
- Define Pydantic request/response models before implementation
- Version APIs from day one: `/v1/resources`
- Document all possible error responses and edge cases
- Include field constraints (types, limits, defaults) in models

**NEVER:**
- Implement endpoints without documented contracts
- Expose database schemas directly in responses
- Break existing consumers without deprecation
- Return 200 for error conditions

---

## When / Then

| When | Then |
|------|------|
| Creating new endpoint | Write endpoint descriptor + models first |
| Resource exists only within parent | Nest: `/users/{id}/addresses` |
| Resource exists independently | Top-level: `/orders` not `/users/{id}/orders` |
| Nesting exceeds 3 levels | Flatten the hierarchy |
| Action on resource needed | Sub-resource: `POST /orders/{id}/cancel` |
| Complex search with body | `POST /resources/search` |
| Long-running operation | Return `202 Accepted` + status URL |
| Read/write patterns diverge | Consider separate read endpoints |
| Client controls resource ID | Use PUT for creation |
| Server generates resource ID | Use POST for creation |

---

## Decision Tree

```
New Endpoint Request
    |
    +-- Is it a resource? --> Model as noun, not verb
    |       |
    |       +-- Collection? --> Plural: /resources
    |       +-- Instance?   --> /resources/{id}
    |
    +-- Is it an action? --> POST /resources/{id}/action
    |
    +-- Is it a search?
    |       +-- Simple filters --> GET /resources?filter=value
    |       +-- Complex body   --> POST /resources/search
    |
    +-- Is it async? --> POST -> 202 + Location: /jobs/{id}
```

---

## Status Code Reference

| Scenario | Code |
|----------|------|
| Successful GET/PUT/PATCH | `200 OK` |
| Successful POST (created) | `201 Created` |
| Async operation accepted | `202 Accepted` |
| Successful DELETE | `204 No Content` |
| Invalid request syntax | `400 Bad Request` |
| Authentication failed | `401 Unauthorized` |
| Permission denied | `403 Forbidden` |
| Resource not found | `404 Not Found` |
| State conflict | `409 Conflict` |
| Validation failed | `422 Unprocessable Entity` |
| Rate limit exceeded | `429 Too Many Requests` |

---

## Skill Chaining

| Condition | Invoke | Handoff Context |
|-----------|--------|-----------------|
| Ready to implement routes | `implement/api` | Endpoint descriptors |
| Complex request/response models | `implement/pydantic` | Model definitions |
| Cross-service events needed | `design/event` | Event triggers |
| Database queries required | `design/data` | Resource-to-table mapping |

---

## Output Format

For each endpoint group, produce a design document with this structure:

### 1. Endpoint List

A table summarizing all endpoints with their responsibility:

```markdown
| Method | Path | Responsibility |
|--------|------|----------------|
| POST | /v1/orders | Create a new order for the authenticated user |
| GET | /v1/orders/{order_id} | Retrieve order details by ID |
| PATCH | /v1/orders/{order_id} | Update mutable order fields before fulfillment |
| POST | /v1/orders/{order_id}/cancel | Cancel a pending or confirmed order |
| GET | /v1/orders | List orders with filtering and pagination |
```

### 2. Pydantic Models

Define request and response models with field types, constraints, and descriptions:

```python
class CreateOrderRequest(BaseModel):
    """Request to create a new order."""
    items: list[OrderItemInput] = Field(..., min_length=1, max_length=50, description="Line items")
    shipping_address_id: AddressId = Field(..., description="Reference to saved address")
    notes: str | None = Field(None, max_length=500, description="Optional delivery instructions")

class OrderItemInput(BaseModel):
    product_id: ProductId
    quantity: int = Field(..., gt=0, le=100)

class OrderResponse(BaseModel):
    """Single order representation."""
    id: OrderId
    status: OrderStatus
    items: list[OrderItemResponse]
    total: Decimal = Field(..., decimal_places=2)
    created_at: datetime
    updated_at: datetime

class OrderListResponse(BaseModel):
    """Paginated order list."""
    data: list[OrderResponse]
    pagination: CursorPagination
```

### 3. Endpoint Behavior

For each endpoint, describe the happy path, edge cases, and error scenarios:

```markdown
#### POST /v1/orders — Create Order

**Happy Path:**
- Validate request body against CreateOrderRequest
- Verify all product_ids exist and are available
- Calculate totals from current product prices
- Create order in PENDING status
- Publish OrderCreated event
- Return 201 with OrderResponse

**Edge Cases:**
- Product price changed since client loaded catalog — use current price, include price in response
- Product out of stock after validation — return 409 with detail per unavailable item
- Duplicate request (idempotency key match) — return existing order, 200

**Errors:**
| Status | Condition | Error Code |
|--------|-----------|------------|
| 400 | Malformed request body | INVALID_REQUEST |
| 401 | Missing or invalid auth token | UNAUTHORIZED |
| 404 | shipping_address_id not found | ADDRESS_NOT_FOUND |
| 409 | One or more items unavailable | ITEMS_UNAVAILABLE |
| 422 | Validation failure (e.g. quantity=0) | VALIDATION_ERROR |
```

---

## Anti-Patterns

### Verbs in URLs

```
# Wrong
POST /createUser
GET /getAllOrders

# Correct
POST /users
GET /orders
```

### Exposing Database Schema

```python
# Wrong — leaks implementation
@app.get("/users/{id}")
def get_user(id: int):
    return db.execute("SELECT * FROM users WHERE id = ?", id)

# Correct — shaped response
@app.get("/users/{id}", response_model=UserResponse)
def get_user(id: int):
    user = user_service.get(id)
    return UserResponse.from_entity(user)
```

### Deep Nesting

```
# Wrong — too deep
GET /users/{id}/orders/{oid}/items/{iid}/reviews/{rid}

# Correct — flattened
GET /order-items/{itemId}/reviews
GET /reviews?orderId=123
```

---

## Quality Gates

Before proceeding to implementation:

- [ ] All endpoints listed with clear responsibilities
- [ ] Request/response Pydantic models defined with field constraints
- [ ] Happy path documented for every endpoint
- [ ] Edge cases and error scenarios covered
- [ ] Status codes assigned to every outcome
- [ ] All resources use plural nouns
- [ ] URLs use lowercase-hyphenated format
- [ ] HTTP methods match operation semantics
- [ ] Pagination defined for collection endpoints
- [ ] Version included in URL path
- [ ] Nesting depth <= 3 levels
