---
name: implement-api
version: 1.0.0
description: |
  Implement FastAPI route handlers from OpenAPI contracts with type-safe Pydantic models,
  async dependency injection, and proper authentication/authorization patterns.
  Use when creating REST endpoints, implementing API routes, adding/modifying HTTP handlers,
  setting up JWT auth, configuring CORS, or wiring service dependencies.
  Relevant for FastAPI, Starlette, async Python APIs, OAuth2/JWT, request validation.
  Prerequisite: design/api must be completed (OpenAPI spec exists).
---

# API Implementation

> Transform OpenAPI contracts into production-ready FastAPI endpoints with zero boilerplate errors.

| Aspect | Details |
|--------|---------|
| **Prerequisite** | `design/api` completed — OpenAPI spec must exist |
| **Invokes** | `implement/pydantic`, `implement/database`, `test/unit` |
| **Invoked By** | `design/api`, `implement/python` |

---

## Core Workflow

1. **Verify Contract**: Confirm OpenAPI spec exists; if missing → invoke `design/api` first
2. **Generate Schemas**: Create Pydantic request/response models → invoke `implement/pydantic`
3. **Structure Router**: Create `APIRouter` with prefix, tags, shared dependencies
4. **Implement Handlers**: Write async route functions with proper typing
5. **Wire Dependencies**: Inject services, DB sessions, auth via `Depends()`
6. **Handle Errors**: Register domain exception handlers for consistent responses
7. **Validate**: Run `pytest` + `ty check` → invoke `test/unit`

---

## Must / Never

### Route Handlers

**MUST:**







- Use `async def` for all I/O operations (DB, HTTP, file, cache)
- Define `response_model` on every endpoint explicitly

- Return correct status codes: `201` (POST create), `204` (DELETE), `200` (GET/PUT/PATCH)

- Use `Annotated[T, Depends()]` syntax for all dependencies (FastAPI 0.95+)

- Keep handlers thin: max 10 lines, delegate to service layer

- Use `*,` for keyword-only arguments when handler has 2+ parameters




**NEVER:**


- Block event loop with sync I/O (`requests`, `time.sleep`, sync DB) in `async def`
- Return ORM models directly — always filter through `response_model`

- Put business logic (calculations, validation, transformations) in handlers

- Use `Any` type annotations — be explicit

- Return 200 for errors — use proper 4xx/5xx codes

- Call dependencies directly — always wrap with `Depends()`



### Dependencies




**MUST:**



- Use `yield` pattern for resources requiring cleanup (DB sessions, HTTP clients)

- Re-raise exceptions after cleanup in `yield` dependencies — never swallow

- Chain dependencies: `get_db` → `get_repository` → `get_service`

- Use `@lru_cache` on `get_settings()` — parse config once


- Type all dependencies with proper return annotations



**NEVER:**



- Create DB connections per-request without connection pooling

- Commit in dependencies — let handler control transaction boundary

- Create circular dependency chains
- Use sync dependencies where async alternatives exist


- Store mutable state in global variables



### Schemas (invoke `implement/pydantic` for complex cases)



**MUST:**

- Separate schemas by operation: `*Create`, `*Update`, `*Response`, `*InDB`

- Use `model_config = ConfigDict(from_attributes=True)` for ORM conversion
- Make all `*Update` fields `T | None` with `exclude_unset=True` for PATCH


- Use `Field(description=...)` on all fields for OpenAPI docs

**NEVER:**

- Use single model for create/read/update operations
- Expose sensitive fields (`password`, `hashed_password`, `api_key`) in responses


- Use Pydantic V1 syntax (`class Config`, `.dict()`, `@validator`)
- Accept `dict` or `Any` at API boundaries

### Authentication & Security

**MUST:**


- Use `OAuth2PasswordBearer(tokenUrl="...")` for JWT flows
- Set short token expiration (15-30 min for access tokens)
- Use `SecretStr` for all secrets in settings
- Apply `Depends(get_current_user)` on every protected route
- Configure CORS with explicit allowed origins

**NEVER:**

- Store plaintext passwords — use `bcrypt` or `argon2`
- Put secrets in code — use environment variables via `pydantic-settings`
- Use `allow_origins=["*"]` with `allow_credentials=True`
- Trust client data without server-side validation
- Expose internal error details in responses

---

## When → Then

| When | Then |
|------|------|
| Route has DB/HTTP/file I/O | Use `async def` + `await` |
| Route is CPU-bound only | Use `def` (FastAPI runs in threadpool) |
| Need sync library in async route | Use `await run_in_threadpool(sync_fn)` |
| Multiple routes share validation | Create reusable `Depends()` function |
| Need entity existence check | Create `valid_<entity>_id` dependency |
| Creating a resource (POST) | Return `status_code=201` |
| Deleting a resource (DELETE) | Return `status_code=204` |
| Partial update (PATCH) | Use `.model_dump(exclude_unset=True)` |
| Resource doesn't exist | Raise `HTTPException(status_code=404)` |
| User input invalid | Let Pydantic raise 422 automatically |
| Business rule violated | Raise domain exception → handle globally |
| Complex schemas needed | Invoke `implement/pydantic` |
| DB queries needed | Invoke `implement/database` |
| Implementation complete | Invoke `test/unit` |
| Need auth on all router routes | Add `dependencies=[Depends(auth)]` to `APIRouter` |

---

## Decision Trees

### Async vs Sync

```
Route Implementation?
├─► Has I/O (DB, HTTP, file)?
│   ├─► Async library (asyncpg, httpx, aiofiles)? → async def
│   └─► Sync library (psycopg2, requests)? → def (threadpool)
├─► CPU-bound computation?
│   └─► Yes → def + consider ProcessPoolExecutor
└─► Trivial/pure logic only? → def
```

### Auth Dependency Selection

```
Endpoint Protection Level?
├─► Public (no auth) → No dependency
├─► Any authenticated user → Depends(get_current_user)
├─► Must be active/verified → Depends(get_current_active_user)
├─► Specific roles required → Depends(RoleChecker([roles]))
└─► Resource ownership → Depends(get_owned_<resource>)
```

### Error Handling

```
Error Scenario?
├─► Resource not found → HTTPException(404, detail="<Resource> not found")
├─► Invalid request data → Pydantic 422 (automatic)
├─► Not authenticated → HTTPException(401) + WWW-Authenticate header
├─► Not authorized → HTTPException(403, detail="Insufficient permissions")
├─► Duplicate/conflict → HTTPException(409, detail="Already exists")
├─► Rate limited → HTTPException(429, detail="Too many requests")
└─► Domain rule violation → Custom AppException + global handler
```

---

## Skill Chaining

| Condition | Invoke | Handoff Context |
|-----------|--------|-----------------|
| No OpenAPI spec exists | `design/api` | Resource requirements, endpoints needed |
| Complex Pydantic models | `implement/pydantic` | Field types, validators, config |
| Database queries/repos | `implement/database` | Table names, relationships, queries |
| Implementation complete | `test/unit` | Route paths, schemas, expected responses |
| Security concerns | `review/security` | Auth flows, input handling |

**Chaining Syntax:**
```markdown
**Invoking:** `implement/pydantic`
**Reason:** Complex nested request model with cross-field validation
**Context:** OrderCreate schema with items array, shipping address, discount validation
```

---

## Essential Patterns

### Router Module Structure

```python
"""User management API routes."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, status

from app.users.dependencies import get_user_service, valid_user_id
from app.users.schemas import UserCreate, UserResponse, UserUpdate
from app.users.service import UserService
from app.auth.dependencies import get_current_active_user, RoleChecker, Role
from app.database import User

router = APIRouter(prefix="/users", tags=["users"])

# Type aliases for cleaner signatures
CurrentUser = Annotated[User, Depends(get_current_active_user)]
UserServiceDep = Annotated[UserService, Depends(get_user_service)]
ValidUser = Annotated[User, Depends(valid_user_id)]
```

### CRUD Route Handlers

```python
@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(*, data: UserCreate, service: UserServiceDep) -> User:
    """Create a new user account."""
    return await service.create(data)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(*, user: ValidUser) -> User:
    """Get user by ID."""
    return user


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    *,
    user: ValidUser,
    data: UserUpdate,
    service: UserServiceDep,
) -> User:
    """Update user fields (partial update)."""
    return await service.update(user, data)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(*, user: ValidUser, service: UserServiceDep) -> None:
    """Delete a user account."""
    await service.delete(user.id)
```

### Entity Validation Dependency

```python
async def valid_user_id(
    user_id: Annotated[int, Path(ge=1, description="User ID")],
    service: Annotated[UserService, Depends(get_user_service)],
) -> User:
    """Validate user exists and return it."""
    user = await service.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
```

### Database Session Dependency

```python
from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

async def get_db(
    session_maker: Annotated[async_sessionmaker, Depends(get_session_maker)],
) -> AsyncGenerator[AsyncSession, None]:
    async with session_maker() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise

SessionDep = Annotated[AsyncSession, Depends(get_db)]
```

### Global Exception Handler

```python
class AppException(Exception):
    """Base application exception."""
    status_code: int = 400
    error_code: str = "APP_ERROR"
    message: str = "An error occurred"

    def __init__(self, message: str | None = None, **extra: Any) -> None:
        self.message = message or self.message
        self.extra = extra

class NotFoundError(AppException):
    status_code = 404
    error_code = "NOT_FOUND"

class ConflictError(AppException):
    status_code = 409
    error_code = "CONFLICT"

@app.exception_handler(AppException)
async def handle_app_exception(request: Request, exc: AppException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"error_code": exc.error_code, "message": exc.message},
    )
```

### Role-Based Access Control

```python
class RoleChecker:
    """Dependency that checks user has required role."""
    def __init__(self, allowed_roles: list[Role]) -> None:
        self.allowed_roles = allowed_roles

    def __call__(self, user: CurrentUser) -> User:
        if user.role not in self.allowed_roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user

# Usage
allow_admin = RoleChecker([Role.ADMIN])
allow_editors = RoleChecker([Role.ADMIN, Role.EDITOR])

@router.delete("/users/{user_id}", dependencies=[Depends(allow_admin)])
async def delete_user(user_id: int) -> None: ...
```

---

## Anti-Patterns

### ❌ Business Logic in Routes

```python
# WRONG: Handler does calculations
@router.post("/orders")
async def create_order(order: OrderCreate, db: SessionDep):
    total = sum(i.price * i.qty for i in order.items)
    if order.discount:
        total *= 0.9
    db.add(Order(total=total))
    await db.commit()
    return {"total": total}

# CORRECT: Delegate to service
@router.post("/orders", response_model=OrderResponse, status_code=201)
async def create_order(*, data: OrderCreate, service: OrderServiceDep) -> Order:
    return await service.create(data)
```

### ❌ Blocking Async Event Loop

```python
# WRONG: Blocks entire event loop
@router.get("/external")
async def fetch_external():
    response = requests.get("https://api.example.com")  # BLOCKS!
    return response.json()

# CORRECT: Use async HTTP client
@router.get("/external")
async def fetch_external(client: Annotated[httpx.AsyncClient, Depends()]):
    response = await client.get("https://api.example.com")
    return response.json()
```

### ❌ Exposing Internal Models

```python
# WRONG: Leaks hashed_password, internal IDs, audit fields
@router.get("/users/{user_id}")
async def get_user(user_id: int, db: SessionDep):
    return await db.get(User, user_id)

# CORRECT: Filter through response_model
@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(user: ValidUser) -> User:
    return user
```

### ❌ Swallowing Exceptions in Dependencies

```python
# WRONG: Exception disappears
async def get_db():
    async with session_maker() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            # BUG: Missing raise!

# CORRECT: Always re-raise
async def get_db():
    async with session_maker() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise  # MUST re-raise
```

---

## Status Code Reference

| Scenario | Code | Notes |
|----------|------|-------|
| GET success | `200 OK` | Default |
| POST created | `201 Created` | Include `Location` header if applicable |
| DELETE success | `204 No Content` | No response body |
| Async accepted | `202 Accepted` | Return job/status URL |
| Invalid syntax | `400 Bad Request` | Malformed JSON, etc. |
| Not authenticated | `401 Unauthorized` | Include `WWW-Authenticate` header |
| Not authorized | `403 Forbidden` | Authenticated but lacks permission |
| Not found | `404 Not Found` | Resource doesn't exist |
| Conflict | `409 Conflict` | Duplicate, state conflict |
| Validation error | `422 Unprocessable Entity` | Pydantic validation failures |
| Rate limited | `429 Too Many Requests` | Include `Retry-After` header |

---

## Quality Gates

Before completing implementation:

- [ ] OpenAPI spec from `design/api` is implemented faithfully
- [ ] All routes have explicit `response_model` parameter
- [ ] All `async def` routes use `await` for I/O — no blocking calls
- [ ] Dependencies use `Annotated[T, Depends()]` syntax
- [ ] `yield` dependencies re-raise exceptions after cleanup
- [ ] Protected routes have appropriate auth dependencies
- [ ] Global exception handlers return consistent error schema
- [ ] No business logic in route handlers (max 10 lines)
- [ ] `from __future__ import annotations` present in all modules
- [ ] Handler parameters use keyword-only (`*,`) syntax
- [ ] `ruff check` and `ty check` pass

---

## Deep References

- **[refs/testing.md](refs/testing.md)**: TestClient, AsyncClient, dependency overrides
- **[refs/performance.md](refs/performance.md)**: Pagination, filtering, caching, streaming responses
- **[refs/middleware.md](refs/middleware.md)**: CORS, request ID, timing middleware
