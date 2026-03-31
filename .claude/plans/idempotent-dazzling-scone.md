# Plan: Task 12 — FastAPI App Shell + All Routes + DI

## Context

Task 12 wires all existing domain work (flows, adapters, models from T-7–T-10) into a running FastAPI HTTP service.
The domain layer is complete; this task implements the HTTP boundary: app factory, DI, Pydantic API contracts,
route handlers, exception handlers, JWT cookie auth middleware, and the health endpoint.

---

## Design Target

| Service | Domain | Status | Layers Affected |
|---------|--------|--------|-----------------|
| webapp | shared infra | existing | `main.py` (rewrite), `dependencies.py` (fill), `models/contracts/api/errors.py` (update shape) |
| webapp | identity | existing | `routes/v1/auth.py` (new), `models/contracts/api/auth.py` (new) |
| webapp | tracker | existing | `routes/v1/products.py` (new), `routes/v1/notifications.py` (new), `models/contracts/api/{products,notifications}.py` (new) |

`config.py` — **no changes**; already complete with all required fields.

---

## Key Finding: ErrorResponse Shape Conflict

The existing `services/webapp/webapp/models/contracts/api/errors.py` defines:
```python
class ErrorResponse:
    errors: list[ErrorDetail]  # ErrorDetail has field + message
```

The task spec requires a flat shape:
```python
class ErrorResponse:
    detail: str   # human-readable
    code: str     # machine-readable
```

**Resolution:** Rewrite `errors.py` to the flat `detail`/`code` shape. `ErrorDetail` is removed.

---

## Files to Create / Modify

### Modify (rewrite)
1. `services/webapp/webapp/models/contracts/api/errors.py` — flat `detail`/`code` ErrorResponse
2. `services/webapp/webapp/dependencies.py` — `get_db_session`, `get_current_user`, `get_settings`
3. `services/webapp/webapp/main.py` — `create_app()`, lifespan, routers, exception handlers, CORS, health

### Create
4. `services/webapp/webapp/domains/identity/models/contracts/api/__init__.py`
5. `services/webapp/webapp/domains/identity/models/contracts/api/auth.py` — RegisterRequest/Response, LoginRequest/Response, ChangePasswordRequest, RequestPasswordResetRequest, ConfirmPasswordResetRequest
6. `services/webapp/webapp/domains/tracker/models/contracts/api/__init__.py`
7. `services/webapp/webapp/domains/tracker/models/contracts/api/products.py` — AddProductRequest, ProductResponse, DashboardResponse
8. `services/webapp/webapp/domains/tracker/models/contracts/api/notifications.py` — NotificationResponse, NotificationListResponse
9. `services/webapp/webapp/domains/identity/routes/v1/auth.py` — 8 identity endpoints
10. `services/webapp/webapp/domains/tracker/routes/v1/products.py` — 3 product endpoints
11. `services/webapp/webapp/domains/tracker/routes/v1/notifications.py` — 2 notification endpoints

---

## Implementation Details

### 1. `errors.py` (rewrite)
```python
class ErrorResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    detail: str   # human-readable
    code: str     # machine-readable (snake/SCREAMING_SNAKE)
```

### 2. `dependencies.py`
```python
async def get_db_session(request: Request) -> AsyncGenerator[AsyncSession, None]:
    async with request.app.state.session_factory() as session:
        yield session

def get_settings() -> Settings:  # re-export for DI
    return _get_settings()  # calls lru_cache version from config.py

async def get_current_user(
    session: AsyncSession = Depends(get_db_session),
    session_cookie: str | None = Cookie(default=None, alias="session"),
    settings: Settings = Depends(get_settings),
) -> User:
    if not session_cookie:
        raise HTTPException(status_code=401, detail="AUTHENTICATION_REQUIRED")
    try:
        user_id = decode_jwt(session_cookie, settings.jwt_secret)
    except JWTError:
        raise HTTPException(status_code=401, detail="AUTHENTICATION_REQUIRED")
    user = await SQLAlchemyUserRepository(session).get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=401, detail="AUTHENTICATION_REQUIRED")
    return user
```

### 3. `main.py`

**Lifespan:**
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    app.state.session_factory = async_sessionmaker(engine, expire_on_commit=False)
    app.state.token_store = InMemoryTokenStore()  # shared across requests for OIDC nonce
    yield
    await engine.dispose()
```

**create_app():**
- `FastAPI(title="Dealio Webapp", version="1.0.0", lifespan=lifespan)`
- Add `CORSMiddleware(allow_origins=[settings.app_base_url], allow_credentials=True, ...)`
- Register all exception handlers (see map below)
- Include routers: `auth_router` at `/api/v1/auth`, `products_router` at `/api/v1`, `notifications_router` at `/api/v1`
- Register `GET /api/v1/health` inline

**Exception handler map:**
```python
_HANDLERS = {
    EmailAlreadyRegisteredError:      (409, "EMAIL_ALREADY_REGISTERED"),
    InvalidCredentialsError:          (401, "INVALID_CREDENTIALS"),
    WeakPasswordError:                (422, "WEAK_PASSWORD"),
    PasswordChangeNotAllowedError:    (422, "PASSWORD_CHANGE_NOT_ALLOWED"),
    InvalidResetTokenError:           (400, "INVALID_RESET_TOKEN"),
    InvalidOIDCStateError:            (400, "INVALID_OIDC_STATE"),
    OIDCExchangeError:                (502, "OIDC_EXCHANGE_FAILED"),
    OIDCTokenVerificationError:       (401, "OIDC_TOKEN_VERIFICATION_FAILED"),
    InvalidProductUrlError:           (422, "INVALID_PRODUCT_URL"),
    ProductLimitExceededError:        (422, "PRODUCT_LIMIT_EXCEEDED"),
    DuplicateProductError:            (409, "DUPLICATE_PRODUCT"),
    ScrapingFailedError:              (422, "SCRAPING_FAILED"),
    ProductNotFoundError:             (404, "PRODUCT_NOT_FOUND"),
    NotificationNotFoundError:        (404, "NOTIFICATION_NOT_FOUND"),
}
```

Additional handlers:
- `HTTPException` → `ErrorResponse(detail=exc.detail, code=exc.detail)` (handles 401 AUTHENTICATION_REQUIRED from `get_current_user`)
- `RequestValidationError` → collapse to first error message → `ErrorResponse(detail=..., code="VALIDATION_ERROR")`
- `Exception` → `ErrorResponse(detail="Internal server error", code="INTERNAL_ERROR")` (500, no stack trace)

**Health endpoint (registered in main.py):**
```python
@app.get("/api/v1/health")
async def health(session: AsyncSession = Depends(get_db_session)):
    await session.execute(text("SELECT 1"))
    return {"status": "ok", "db": "ok"}
```

### 4. Pydantic API Models

**`auth.py`** (all `frozen=True`, `extra="forbid"`):
- `RegisterRequest`: `email: EmailStr`, `password: str = Field(min_length=8)`
- `RegisterResponse`: `id: str`, `email: str`, `created_at: datetime`
- `LoginRequest`: `email: EmailStr`, `password: str`
- `LoginResponse`: `id: str`, `email: str`
- `ChangePasswordRequest`: `current_password: str`, `new_password: str = Field(min_length=8)`
- `RequestPasswordResetRequest`: `email: EmailStr`
- `ConfirmPasswordResetRequest`: `token: str`, `new_password: str = Field(min_length=8)`

**`products.py`**:
- `AddProductRequest`: `url: str`
- `ProductResponse`: `id: str`, `url: str`, `product_name: str`, `current_price: str`, `previous_price: str | None`, `last_checked_at: datetime`, `created_at: datetime`
- `DashboardResponse`: `products: list[ProductResponse]`, `unread_notification_count: int`

**`notifications.py`**:
- `NotificationResponse`: `id: str`, `tracked_product_id: str`, `old_price: str`, `new_price: str`, `created_at: datetime`, `read_at: datetime | None`
- `NotificationListResponse`: `notifications: list[NotificationResponse]`, `next_cursor: str | None`

### 5. Auth Routes (`auth.py`)

Key adapters instantiated per-request (from `request.app.state` for stateful ones):

| Endpoint | Method | Auth | Adapter(s) | Flow | Response |
|----------|--------|------|------------|------|----------|
| `POST /register` | 201 | No | `SQLAlchemyUserRepository` | `RegisterUser` | `RegisterResponse` + set_cookie |
| `POST /login` | 200 | No | `SQLAlchemyUserRepository` | `LoginUser` | `LoginResponse` + set_cookie |
| `POST /logout` | 204 | Yes | — | `LogoutUser` | delete cookie (`Max-Age=0`) |
| `GET /google/login` | 302 | No | `AuthlibGoogleOIDCClient`, `app.state.token_store` | `InitiateGoogleLogin` | `RedirectResponse` |
| `GET /google/callback` | 303 | No | `AuthlibGoogleOIDCClient`, `app.state.token_store`, `SQLAlchemyUserRepository` | `HandleGoogleCallback` | redirect `/dashboard` + set_cookie; OIDC errors → redirect `/login?error=<code>` (handled locally, NOT via global handlers) |
| `POST /password-reset` | 204 | No | `SQLAlchemyUserRepository`, `SQLAlchemyTokenRepository`, `SESEmailSender` | `RequestPasswordReset` | 204 (silent) |
| `POST /password-reset/confirm` | 204 | No | `SQLAlchemyTokenRepository`, `SQLAlchemyUserRepository` | `ConfirmPasswordReset` | 204 |
| `PUT /password` | 204 | Yes | `SQLAlchemyUserRepository` | `ChangePassword` | 204 |

Cookie spec: `set_cookie("session", token, httponly=True, secure=True, samesite="lax", max_age=86400, path="/")`

**Important: `GET /google/callback` handles OIDC exceptions locally** with `try/except` and redirects to `/login?error=<code>`. These exceptions must NOT bubble to the global JSON handlers.

### 6. Product Routes (`products.py`)

| Endpoint | Method | Auth | Flow | Response |
|----------|--------|------|------|----------|
| `GET /products` | 200 | Yes | `GetDashboard(product_repo, notif_read_repo)` | `DashboardResponse`; prices as `str(p.current_price.value)` |
| `POST /products` | 201 | Yes | `AddTrackedProduct(product_repo, scraper)` | `ProductResponse` |
| `DELETE /products/{product_id}` | 204 | Yes | `RemoveTrackedProduct(product_repo)` | 204; `product_id: uuid.UUID` path param → cast to `TrackedProductId` |

`scraper` adapter: `ScraperLambdaClient(lambda_name=settings.scraper_lambda_name)` (instantiated per-request; stateless).

### 7. Notification Routes (`notifications.py`)

| Endpoint | Method | Auth | Flow | Response |
|----------|--------|------|------|----------|
| `GET /notifications` | 200 | Yes | `ListNotifications(notif_read_repo)` | `NotificationListResponse`; query params `cursor: str \| None`, `limit: int = Query(default=20, ge=1, le=50)` |
| `PATCH /notifications/{notification_id}/read` | 200 | Yes | `DismissNotification(notif_read_repo)` | `NotificationResponse` |

---

## Reused Existing Code (do NOT reimplement)

| Symbol | File |
|--------|------|
| `Settings`, `get_settings` | `webapp/config.py` |
| `RegisterUser`, `LoginUser`, `LogoutUser`, `ChangePassword`, `RequestPasswordReset`, `ConfirmPasswordReset` | `webapp/domains/identity/flows/` |
| `InitiateGoogleLogin`, `HandleGoogleCallback` | `webapp/domains/identity/flows/` |
| `SQLAlchemyUserRepository`, `SQLAlchemyTokenRepository`, `AuthlibGoogleOIDCClient`, `InMemoryTokenStore`, `SESEmailSender` | `webapp/domains/identity/adapters/` |
| `decode_jwt`, `JWTError` | `webapp/domains/identity/adapters/jwt_service.py` |
| `GetDashboard`, `AddTrackedProduct`, `RemoveTrackedProduct`, `ListNotifications`, `DismissNotification` | `webapp/domains/tracker/flows/` |
| `SQLAlchemyTrackedProductRepository`, `SQLAlchemyNotificationReadRepository` | `webapp/domains/tracker/adapters/` |
| `ScraperLambdaClient` | `webapp/domains/scraper_client/adapters/` |
| All domain exception classes | `identity/exceptions.py`, `tracker/exceptions.py`, `notifier/exceptions.py` |
| `User` | `webapp/domains/identity/models/domain/user.py` |
| `TrackedProductId` | `webapp/domains/tracker/models/domain/types.py` |

---

## Implementation Order

Execute in this sequence (each step depends on the previous):

1. `errors.py` — flat shape; everything else imports it
2. `dependencies.py` — shared DI; all routes depend on it
3. `auth.py` (models) + `products.py` (models) + `notifications.py` (models) — parallel
4. `auth.py` (routes) + `products.py` (routes) + `notifications.py` (routes) — parallel
5. `main.py` — wires all of the above together

---

## Verification

```bash
cd services/webapp

# Start app
DATABASE_URL=postgresql+asyncpg://postgres:test@localhost:5432/dealio \
JWT_SECRET=test-secret-minimum-32-chars-ok! \
AWS_REGION=us-east-1 \
SCRAPER_LAMBDA_NAME=scraper \
SES_FROM_ADDRESS=noreply@example.com \
GOOGLE_CLIENT_ID=fake \
GOOGLE_CLIENT_SECRET=fake \
GOOGLE_REDIRECT_URI=http://localhost:8000/api/v1/auth/google/callback \
APP_BASE_URL=http://localhost:3000 \
  uv run uvicorn webapp.main:app --host 0.0.0.0 --port 8000

# Health
curl http://localhost:8000/api/v1/health
# → {"status":"ok","db":"ok"}

# Register
curl -c cookies.txt -X POST http://localhost:8000/api/v1/auth/register \
  -H 'Content-Type: application/json' -d '{"email":"test@example.com","password":"password123"}'
# → 201 {"id":"...","email":"test@example.com","created_at":"..."}  + Set-Cookie: session=<jwt>

# Login
curl -c cookies.txt -X POST http://localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' -d '{"email":"test@example.com","password":"password123"}'
# → 200 {"id":"...","email":"test@example.com"}

# Dashboard
curl -b cookies.txt http://localhost:8000/api/v1/products
# → 200 {"products":[],"unread_notification_count":0}

# 401 without cookie
curl http://localhost:8000/api/v1/products
# → 401 {"detail":"AUTHENTICATION_REQUIRED","code":"AUTHENTICATION_REQUIRED"}

# 409 duplicate email
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H 'Content-Type: application/json' -d '{"email":"test@example.com","password":"password123"}'
# → 409 {"detail":"...","code":"EMAIL_ALREADY_REGISTERED"}

# 422 invalid URL
curl -b cookies.txt -X POST http://localhost:8000/api/v1/products \
  -H 'Content-Type: application/json' -d '{"url":"http://192.168.1.1/product"}'
# → 422 {"detail":"...","code":"INVALID_PRODUCT_URL"}
```
