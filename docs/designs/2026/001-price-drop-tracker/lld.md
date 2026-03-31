# Low-Level Design: Price Drop Tracker

**Date:** 2026-03-13
**Status:** Draft
**Feature:** 001-price-drop-tracker
**Phase:** LLD — Complete
**Sources:** lld-code.md (python-architect), lld-data.md (data-architect), lld-api.md (api-architect)
**Traceable to:** hld.md Sections 4, 5, 6, 14

---

## 0. Service & Domain Architecture

### Deployment Units

| Service | Runtime | Network | Status |
|---------|---------|---------|--------|
| `services/webapp` | FastAPI on ECS Fargate | Private subnet, ALB-fronted | [new] |
| `services/monitor_lambda` | AWS Lambda (Python) | VPC private subnet | [new] |
| `services/scraper_lambda` | AWS Lambda (Python) | No VPC | [new] |

### Domain & Module Map

#### services/webapp — FastAPI Monolith

| Domain | Module | Status | Responsibility |
|--------|--------|--------|----------------|
| `identity` | `routes/v1/` | [new] | Auth HTTP endpoints (register, login, logout, OIDC, password reset, change password) |
| `identity` | `flows/` | [new] | RegisterUser, LoginUser, LogoutUser, InitiateGoogleLogin, HandleGoogleCallback, RequestPasswordReset, ConfirmPasswordReset, ChangePassword |
| `identity` | `ports/` | [new] | UserRepository, TokenRepository, TokenStore, EmailSender, OIDCClient protocols |
| `identity` | `adapters/` | [new] | SQLAlchemy UserRepository, SES EmailSender, Authlib GoogleOIDCClient, in-memory TokenStore |
| `identity` | `exceptions.py` | [new] | IdentityError hierarchy |
| `identity` | `models/domain/` | [new] | User entity, PasswordResetToken entity, HashedPassword value object |
| `identity` | `models/contracts/api/` | [new] | RegisterRequest/Response, LoginRequest/Response, GoogleCallbackParams, PasswordResetRequest/Response, ConfirmResetRequest/Response, ChangePasswordRequest/Response |
| `identity` | `models/persistence/` | [new] | UserRecord, PasswordResetTokenRecord (SQLAlchemy 2.x ORM) |
| `tracker` | `routes/v1/` | [new] | Product + notification HTTP endpoints |
| `tracker` | `flows/` | [new] | AddTrackedProduct, RemoveTrackedProduct, GetDashboard, ListNotifications, DismissNotification |
| `tracker` | `ports/` | [new] | TrackedProductRepository, NotificationReadRepository, ScraperPort protocols |
| `tracker` | `adapters/` | [new] | SQLAlchemy TrackedProductRepository, NotificationReadRepository, ScraperLambdaClient ACL |
| `tracker` | `exceptions.py` | [new] | TrackerError hierarchy |
| `tracker` | `models/domain/` | [new] | TrackedProduct aggregate, ProductUrl value object, Price value object, PriceDropOccurred event |
| `tracker` | `models/contracts/api/` | [new] | AddProductRequest, ProductResponse, DashboardResponse, NotificationResponse, NotificationListResponse |
| `tracker` | `models/persistence/` | [new] | TrackedProductRecord (SQLAlchemy 2.x ORM) |
| `notifier` | `ports/` | [new] | NotificationWriteRepository protocol |
| `notifier` | `adapters/` | [new] | SQLAlchemy NotificationWriteRepository |
| `notifier` | `models/domain/` | [new] | Notification entity |
| `notifier` | `models/persistence/` | [new] | NotificationRecord (SQLAlchemy 2.x ORM) |
| `scraper_client` | `ports/` | [new] | ScraperPort protocol (canonical definition) |
| `scraper_client` | `adapters/` | [new] | ScraperLambdaClient (boto3 invoke, retry, backoff, ACL translation) |
| `scraper_client` | `models/domain/` | [new] | ScraperResult union, ScraperSuccess, ScraperFailure, ScraperErrorType |
| *(root)* | `config.py` | [new] | Pydantic BaseSettings (DB URL, JWT secret, AWS config) |
| *(root)* | `dependencies.py` | [new] | FastAPI DI wiring: `get_current_user`, repository factories |
| *(root)* | `main.py` | [new] | FastAPI application factory, exception handler registration |
| *(root)* | `models/contracts/api/errors.py` | [new] | Shared ErrorResponse model |

#### services/monitor_lambda — Price Monitor Lambda

| Domain | Module | Status | Responsibility |
|--------|--------|--------|----------------|
| `monitor` | `jobs/` | [new] | Lambda handler entry point (EventBridge event in) |
| `monitor` | `flows/` | [new] | PriceCheckCycleFlow (enumerate → scrape → compare → notify) |
| `monitor` | `ports/` | [new] | TrackedProductRepository, PriceCheckLogRepository, NotificationWriteRepository, ScraperPort, EmailSender protocols |
| `monitor` | `adapters/` | [new] | SQLAlchemy repos, ScraperLambdaClient, SESEmailSender |
| `monitor` | `exceptions.py` | [new] | MonitorError hierarchy |
| `monitor` | `models/domain/` | [new] | PriceCheckResult value object, PriceCheckLog entity, TrackedProductSummary |

#### services/scraper_lambda — Scraper Lambda

| Domain | Module | Status | Responsibility |
|--------|--------|--------|----------------|
| `scraper` | `jobs/` | [new] | Lambda handler entry point (URL in → price+name out) |
| `scraper` | `flows/` | [new] | ScrapeFlow (fetch → classify → parse → extract) |
| `scraper` | `exceptions.py` | [new] | ScraperInternalError |
| `scraper` | `models/domain/` | [new] | ScraperResult, ScraperSuccess, ScraperFailure, ScraperErrorType enum |

### Filesystem Layout

```
services/
  webapp/
    webapp/
      domains/
        identity/
          routes/v1/
          flows/
          ports/
          adapters/
          exceptions.py
          models/
            domain/
            contracts/api/
            persistence/
      domains/
        tracker/
          routes/v1/
          flows/
          ports/
          adapters/
          exceptions.py
          models/
            domain/
            contracts/api/
            persistence/
        notifier/
          ports/
          adapters/
          models/domain/
          models/persistence/
        scraper_client/
          ports/
          adapters/
          models/domain/
      models/contracts/api/errors.py
      config.py
      dependencies.py
      main.py
    alembic/
      env.py
      versions/
        0001_initial_schema.py
    pyproject.toml

  monitor_lambda/
    monitor_lambda/
      domains/
        monitor/
          jobs/
          flows/
          ports/
          adapters/
          exceptions.py
          models/domain/
      infrastructure/database/base.py
    pyproject.toml

  scraper_lambda/
    scraper_lambda/
      domains/
        scraper/
          jobs/
          flows/
          exceptions.py
          models/domain/
    pyproject.toml
```

### Shared Libraries

| Library | Usage |
|---------|-------|
| None at MVP scale | No cross-service shared code identified; `scraper_client` adapter duplicated between webapp and monitor_lambda by design (independent deployments) |

---

## 1. Domain Model

### 1.1 Ubiquitous Language

| Term | Definition | Context |
|------|------------|---------|
| User | Registered individual; owns TrackedProducts and Notifications | Identity |
| PasswordResetToken | Single-use expiring credential authorising a password change | Identity |
| Session | Signed JWT stored as HttpOnly cookie; identifies authenticated User | Identity |
| TrackedProduct | Aggregate root: product URL + scraped name + prices + check timestamp; owned by one User | Tracker |
| ProductUrl | Validated HTTP/HTTPS URL; RFC-1918 and localhost rejected (SSRF prevention) | Tracker |
| Price | Monetary value as `Decimal(10,2)` | Tracker, Monitor |
| PriceDropOccurred | Domain event: price fell below previous current price | Tracker |
| PriceCheckResult | Value object: outcome of one scrape invocation during a monitoring cycle | Monitor |
| PriceCheckLog | Immutable audit record of one price check for one TrackedProduct | Monitor |
| PriceDrop | State transition: scraped Price < stored current Price | Monitor |
| Notification | In-app record of a PriceDrop event; linked to User and TrackedProduct by ID | Notifier |
| ScraperResult | Value object from Scraper Lambda: price+name or structured error | Scraper |
| PriceCheckCycle | One complete Monitor Lambda execution checking all TrackedProducts | Monitor |

### 1.2 Identity Context

**User** (Entity — aggregate root)

| Field | Type | Constraints |
|-------|------|-------------|
| `id` | `UserId` (UUID) | Immutable PK |
| `email` | `str` | Unique; lowercase-normalised before storage |
| `password_hash` | `str \| None` | bcrypt cost 14; `None` for Google-only; never in responses |
| `google_sub` | `str \| None` | Unique when present; `None` for email-only |
| `created_at` | `datetime` | UTC; immutable |
| `updated_at` | `datetime` | UTC; updated on every save |

Invariants: `password_hash IS NOT NULL OR google_sub IS NOT NULL`; email lowercase before storage.

**PasswordResetToken** (Entity — member of Identity aggregate)

| Field | Type | Constraints |
|-------|------|-------------|
| `id` | `PasswordResetTokenId` (UUID) | Immutable PK |
| `user_id` | `UserId` | Immutable FK |
| `token_hash` | `str` | bcrypt hash of raw token; raw token never stored |
| `expires_at` | `datetime` | UTC; `now + 1h` |
| `used_at` | `datetime \| None` | Set on redemption; immutable once set |

`is_valid()` → `True` when `used_at is None and expires_at > now`.

**HashedPassword** (Value Object — `frozen=True`): `HashedPassword.create(raw, cost=14)` — bcrypt at construction.

### 1.3 Tracker Context

**TrackedProduct** (Entity — aggregate root)

| Field | Type | Constraints |
|-------|------|-------------|
| `id` | `TrackedProductId` (UUID) | Immutable PK |
| `user_id` | `UserId` | Immutable; scopes ownership |
| `url` | `ProductUrl` | Validated on construction; immutable |
| `product_name` | `str` | Scraped at add time |
| `current_price` | `Price` | `Decimal(10,2)`; non-negative |
| `previous_price` | `Price \| None` | `None` until first price change |
| `last_checked_at` | `datetime \| None` | Updated on successful scrape only |
| `created_at` | `datetime` | UTC; immutable |

Invariants: max 5 per user (enforced before insert); unique `(user_id, url)`.

Domain method: `record_price_check(new_price, checked_at) -> PriceDropOccurred | None` — **pure**; updates fields, returns event on drop.

**ProductUrl** (Value Object — `frozen=True`): `ProductUrl.parse(raw)` validates scheme, rejects RFC-1918 + localhost.

**Price** (Value Object — `frozen=True`): positive `Decimal`; supports `<` comparison.

**PriceDropOccurred** (Domain Event — `frozen=True`): `tracked_product_id`, `user_id`, `product_name`, `product_url`, `old_price`, `new_price`, `occurred_at`.

### 1.4 Notifier Context

**Notification** (Entity — aggregate root)

| Field | Type | Constraints |
|-------|------|-------------|
| `id` | `NotificationId` (UUID) | Immutable PK |
| `user_id` | `UserId` | Immutable |
| `tracked_product_id` | `TrackedProductId` | Reference by ID only |
| `old_price` | `Price` | Snapshot; immutable |
| `new_price` | `Price` | Snapshot; immutable |
| `created_at` | `datetime` | UTC; immutable |
| `read_at` | `datetime \| None` | `None` = unread; set once on dismiss |

Invariant: `new_price < old_price` always.

### 1.5 Monitor Context

**PriceCheckResult** (Value Object — `frozen=True`): `tracked_product_id`, `outcome` (`"success"|"failure"`), `scraped_price?`, `scraped_name?`, `error_type?`, `retry_count`, `checked_at`. Factory methods: `PriceCheckResult.success(...)`, `.failure(...)`.

**PriceCheckLog** (Entity — append-only): `id`, `tracked_product_id`, `checked_at`, `result`, `retry_count` (0–3), `error_message?`. Immutable after creation.

### 1.6 Scraper Context

`ScraperResult = ScraperSuccess | ScraperFailure`

- **ScraperSuccess** (`frozen=True`): `price: Decimal`, `product_name: str`
- **ScraperFailure** (`frozen=True`): `error_type: ScraperErrorType`, `message: str`, `status_code: int | None`
- **ScraperErrorType** enum: `timeout | http_error | parse_error | blocked`

### 1.7 Application Flows

#### Identity

| Flow | Key Steps | Errors |
|------|-----------|--------|
| RegisterUser | normalise email → check uniqueness → hash password → save User → generate JWT → set cookie | `EmailAlreadyRegisteredError` (409) |
| LoginUser | load by email → verify bcrypt → generate JWT | `InvalidCredentialsError` (401) — no enumeration |
| LogoutUser | stateless JWT; no server-side revocation in MVP; expire cookie | — |
| InitiateGoogleLogin | generate state+nonce → store in TokenStore (TTL 300s) → build authorization URL | — |
| HandleGoogleCallback | verify state → exchange code → verify id_token → find-or-create User → link google_sub → generate JWT | `InvalidOIDCStateError` (400), `OIDCExchangeError` (502), `OIDCTokenVerificationError` (401) |
| RequestPasswordReset | silent if email not found → generate raw token → bcrypt hash → save → send email → always return 200 | — |
| ConfirmPasswordReset | load valid unused tokens → bcrypt-verify → mark used → update password | `InvalidResetTokenError` (400) |
| ChangePassword | user_id from JWT only → reject Google-only → verify current password → hash new → save | `InvalidCredentialsError` (401), `PasswordChangeNotAllowedError` (422) |

#### Tracker

| Flow | Key Steps | Errors |
|------|-----------|--------|
| AddTrackedProduct | parse ProductUrl (SSRF) → check 5-product limit → check duplicate URL → invoke ScraperPort → construct TrackedProduct → save | `InvalidProductUrlError` (422), `ProductLimitExceededError` (422), `DuplicateProductError` (409), `ScrapingFailedError` (422) |
| RemoveTrackedProduct | load product → verify ownership (failure = 404) → hard delete | `ProductNotFoundError` (404) |
| GetDashboard | `asyncio.gather(list_products, count_unread)` → assemble DashboardResponse | — |
| ListNotifications | load notifications ordered `created_at DESC` with cursor pagination | — |
| DismissNotification | load → verify ownership → idempotent if dismissed → set `read_at` → save | `NotificationNotFoundError` (404) |

#### Monitor

**PriceCheckCycleFlow**: load all products → `Semaphore(20)` → `asyncio.gather(*tasks, return_exceptions=True)` → per-product: scrape with retry (3× max, exponential backoff, only `timeout`/`http_error` retried) → compare price → update product + write Notification + send SES email on drop → always write PriceCheckLog. Each product in `try/except Exception` — one failure never stops others.

#### Scraper

**ScrapeFlow**: `fetch_page` (I/O, httpx 10s timeout) → `classify_response` (pure) → `extract_price` (pure; JSON-LD → meta tags → CSS selectors) → `extract_name` (pure). Returns `ScraperSuccess | ScraperFailure` — never raises.

### 1.8 Port Definitions (Protocols)

#### Identity
- **UserRepository**: `get(UserId)`, `get_by_email(str)`, `get_by_google_sub(str)`, `exists_by_email(str)`, `save(User)`
- **TokenRepository**: `save(PasswordResetToken)`, `find_valid_unused() -> list[PasswordResetToken]`
- **TokenStore**: `set(key, value, ttl_seconds)`, `get(key) -> str | None`, `delete(key)`
- **EmailSender**: `send_password_reset(to, raw_token)`
- **OIDCClient**: `build_authorization_url(state, nonce)`, `exchange_code(code)`, `verify_id_token(id_token, nonce)`

#### Tracker
- **TrackedProductRepository**: `get`, `list_by_user`, `count_by_user`, `exists_by_user_and_url`, `save`, `delete`
- **NotificationReadRepository**: `get`, `list_by_user`, `count_unread_by_user`, `save`
- **ScraperPort**: `async scrape(url) -> ScraperResult` — never raises

#### Monitor (declared independently — no webapp imports)
- **TrackedProductRepository**: `list_all_active()`, `update_prices(...)`, `update_last_checked_at(...)`
- **PriceCheckLogRepository**: `save(PriceCheckLog)`
- **NotificationWriteRepository**: `save(Notification)`
- **ScraperPort**: same semantic contract as tracker's; declared independently
- **EmailSender**: `send_price_drop(to, product_name, product_url, old_price, new_price)`

### 1.9 Error Taxonomy

```
IdentityError
├── EmailAlreadyRegisteredError    → HTTP 409
├── InvalidCredentialsError        → HTTP 401
├── WeakPasswordError              → HTTP 422
├── PasswordChangeNotAllowedError  → HTTP 422
├── InvalidResetTokenError         → HTTP 400
├── InvalidOIDCStateError          → HTTP 400
├── OIDCExchangeError              → HTTP 502
└── OIDCTokenVerificationError     → HTTP 401

TrackerError
├── InvalidProductUrlError         → HTTP 422
├── ProductLimitExceededError      → HTTP 422
├── DuplicateProductError          → HTTP 409
├── ScrapingFailedError            → HTTP 422
└── ProductNotFoundError           → HTTP 404

NotifierError
└── NotificationNotFoundError      → HTTP 404

MonitorError
├── PriceCheckCycleError           (cycle-level → CloudWatch alarm)
├── ProductCheckError              (per-product; caught in gather; cycle continues)
└── EmailDeliveryError             (SES failure; in-app notification still persisted)

ScraperErrorType (enum — returned in ScraperFailure, never raised)
  timeout | http_error | parse_error | blocked
```

---

## 2. Data Architecture

### 2.1 Access Patterns

| ID | Pattern | Table | Key Filters | Index | Freq |
|----|---------|-------|-------------|-------|------|
| R1 | Login by email | `users` | `email = ?` | `uq_users_email` | Per login |
| R2 | Google login by google_sub | `users` | `google_sub = ?` | `uq_users_google_sub` | Per OAuth |
| R3 | Google login by email (linking) | `users` | `email = ?` | `uq_users_email` | Per OAuth |
| R4 | Validate password reset token | `password_reset_tokens` | `token_hash = ?, expires_at > NOW(), used_at IS NULL` | `idx_password_reset_tokens_token_hash` | Per reset |
| R5 | Dashboard load | `tracked_products` | `user_id = ?` ORDER BY `created_at DESC` | `idx_tracked_products_user_id_created_at` | Hot path |
| R6 | Count products (5-limit check) | `tracked_products` | `user_id = ?` | `idx_tracked_products_user_id_created_at` | Per add |
| R7 | Duplicate URL check | `tracked_products` | `user_id = ? AND url = ?` | `uq_tracked_products_user_url` | Per add |
| R8 | Enumerate all products (price cycle) | `tracked_products` | none — full table keyset paginated | PK | Per Lambda cycle |
| R9 | Load unread notifications | `notifications` | `user_id = ? AND read_at IS NULL` ORDER BY `created_at DESC` | `idx_notifications_user_id_unread_created_at` | Hot path |

### 2.2 Schema Definitions

#### Table: `users`

```sql
CREATE TABLE users (
    id            UUID         NOT NULL DEFAULT gen_random_uuid(),
    email         VARCHAR(255) NOT NULL,
    password_hash TEXT,
    google_sub    VARCHAR(255),
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW(),

    CONSTRAINT pk_users PRIMARY KEY (id),
    CONSTRAINT uq_users_email UNIQUE (email),
    CONSTRAINT uq_users_google_sub UNIQUE (google_sub),
    CONSTRAINT chk_users_has_auth CHECK (
        password_hash IS NOT NULL OR google_sub IS NOT NULL
    )
);
-- PostgreSQL UNIQUE on nullable google_sub: NULLs are distinct → multiple email-only rows permitted ✓
```

#### Table: `password_reset_tokens`

```sql
CREATE TABLE password_reset_tokens (
    id         UUID         NOT NULL DEFAULT gen_random_uuid(),
    user_id    UUID         NOT NULL,
    token_hash VARCHAR(255) NOT NULL,
    expires_at TIMESTAMPTZ  NOT NULL,
    used_at    TIMESTAMPTZ,
    created_at TIMESTAMPTZ  NOT NULL DEFAULT NOW(),

    CONSTRAINT pk_password_reset_tokens PRIMARY KEY (id),
    CONSTRAINT fk_password_reset_tokens_user
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
```

#### Table: `tracked_products`

```sql
CREATE TABLE tracked_products (
    id              UUID          NOT NULL DEFAULT gen_random_uuid(),
    user_id         UUID          NOT NULL,
    url             TEXT          NOT NULL,
    product_name    VARCHAR(500)  NOT NULL,
    current_price   DECIMAL(10,2) NOT NULL,
    previous_price  DECIMAL(10,2),
    last_checked_at TIMESTAMPTZ,
    created_at      TIMESTAMPTZ   NOT NULL DEFAULT NOW(),

    CONSTRAINT pk_tracked_products PRIMARY KEY (id),
    CONSTRAINT fk_tracked_products_user
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT uq_tracked_products_user_url UNIQUE (user_id, url),
    CONSTRAINT chk_tracked_products_current_price CHECK (current_price >= 0),
    CONSTRAINT chk_tracked_products_previous_price CHECK (previous_price IS NULL OR previous_price >= 0)
);
-- url is TEXT (not VARCHAR) — retailer URLs can exceed 500 chars with tracking params
```

#### Table: `notifications`

```sql
CREATE TABLE notifications (
    id                 UUID          NOT NULL DEFAULT gen_random_uuid(),
    user_id            UUID          NOT NULL,
    tracked_product_id UUID          NOT NULL,
    old_price          DECIMAL(10,2) NOT NULL,
    new_price          DECIMAL(10,2) NOT NULL,
    created_at         TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    read_at            TIMESTAMPTZ,

    CONSTRAINT pk_notifications PRIMARY KEY (id),
    CONSTRAINT fk_notifications_user
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_notifications_tracked_product
        FOREIGN KEY (tracked_product_id) REFERENCES tracked_products(id) ON DELETE CASCADE,
    CONSTRAINT chk_notifications_price_drop CHECK (new_price < old_price),
    CONSTRAINT chk_notifications_old_price CHECK (old_price > 0),
    CONSTRAINT chk_notifications_new_price CHECK (new_price >= 0)
);
-- old_price/new_price are snapshots: tracked_products.current_price is mutable;
-- these capture the exact values at drop time and are never updated after insert.
```

#### Table: `price_check_log`

```sql
CREATE TABLE price_check_log (
    id                 UUID      NOT NULL DEFAULT gen_random_uuid(),
    tracked_product_id UUID      NOT NULL,
    checked_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    result             VARCHAR(10) NOT NULL,
    retry_count        SMALLINT  NOT NULL DEFAULT 0,
    error_message      TEXT,

    CONSTRAINT pk_price_check_log PRIMARY KEY (id),
    CONSTRAINT fk_price_check_log_tracked_product
        FOREIGN KEY (tracked_product_id) REFERENCES tracked_products(id) ON DELETE CASCADE,
    CONSTRAINT chk_price_check_log_result CHECK (result IN ('success', 'failure')),
    CONSTRAINT chk_price_check_log_retry_count CHECK (retry_count >= 0 AND retry_count <= 10),
    CONSTRAINT chk_price_check_log_error_message CHECK (
        (result = 'success' AND error_message IS NULL) OR
        (result = 'failure' AND error_message IS NOT NULL)
    )
);
-- Append-only. No UPDATE operations. VARCHAR(10) + CHECK preferred over ENUM (easier to migrate).
```

### 2.3 Index Strategy

```sql
-- users
CREATE UNIQUE INDEX idx_users_google_sub ON users (google_sub);
-- (NULLs are naturally distinct in PostgreSQL UNIQUE indexes — no partial needed)

-- password_reset_tokens
CREATE INDEX idx_password_reset_tokens_token_hash ON password_reset_tokens (token_hash);
CREATE INDEX idx_password_reset_tokens_user_id ON password_reset_tokens (user_id);

-- tracked_products
CREATE INDEX idx_tracked_products_user_id_created_at ON tracked_products (user_id, created_at DESC);
-- uq_tracked_products_user_url auto-creates composite index on (user_id, url)

-- notifications
CREATE INDEX idx_notifications_user_id_unread_created_at
    ON notifications (user_id, created_at DESC)
    WHERE read_at IS NULL;
-- Partial index: only unread rows — index shrinks as notifications are dismissed
CREATE INDEX idx_notifications_user_id ON notifications (user_id);
CREATE INDEX idx_notifications_tracked_product_id ON notifications (tracked_product_id);

-- price_check_log
CREATE INDEX idx_price_check_log_tracked_product_id ON price_check_log (tracked_product_id);
CREATE INDEX idx_price_check_log_result_checked_at ON price_check_log (result, checked_at DESC);
```

### 2.4 SQLAlchemy ORM (key mappings)

All ORM classes use SQLAlchemy 2.x declarative style with `Mapped` + `mapped_column`. UUIDs generated by `uuid.uuid4()` at Python layer. Session type: `AsyncSession`.

```python
# services/webapp/webapp/domains/identity/models/persistence/user_record.py
class UserRecord(Base):
    __tablename__ = "users"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    google_sub: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default="NOW()")
    updated_at: Mapped[datetime] = mapped_column(nullable=False, server_default="NOW()")

# services/webapp/webapp/domains/tracker/models/persistence/tracked_product_record.py
class TrackedProductRecord(Base):
    __tablename__ = "tracked_products"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    product_name: Mapped[str] = mapped_column(String(500), nullable=False)
    current_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    previous_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    last_checked_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default="NOW()")

# services/webapp/webapp/domains/notifier/models/persistence/notification_record.py
class NotificationRecord(Base):
    __tablename__ = "notifications"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    tracked_product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tracked_products.id", ondelete="CASCADE"), nullable=False, index=True)
    old_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    new_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default="NOW()")
    read_at: Mapped[datetime | None] = mapped_column(nullable=True)

# services/monitor_lambda/monitor_lambda/domains/monitor/models/persistence/price_check_log_record.py
class PriceCheckLogRecord(Base):  # uses monitor_lambda's own Base
    __tablename__ = "price_check_log"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tracked_product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tracked_products.id", ondelete="CASCADE"), nullable=False, index=True)
    checked_at: Mapped[datetime] = mapped_column(nullable=False, server_default="NOW()")
    result: Mapped[str] = mapped_column(String(10), nullable=False)
    retry_count: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
```

### 2.5 Migration Strategy

- **Tool:** Alembic with async engine (`asyncpg` driver)
- **Location:** `services/webapp/alembic/` — single migration owner for the shared schema
- **Monitor Lambda** does not own migrations; installs its ORM models as read-only schema consumers
- **Initial migration:** `0001_initial_schema.py` — creates all 5 tables, all constraints, all indexes
- **Evolution pattern:** expand-contract (add nullable columns first, dual-write, drop old column last)
- **CI gate:** `alembic check` fails the build if model changes exist without a corresponding migration
- **Apply:** `alembic upgrade head` before starting new app version

### 2.6 Key Data Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Primary keys | UUIDv4 | Distributed-ready; no hot partitions; no sequential enumeration |
| Money type | `DECIMAL(10,2)` | Exact representation; no floating-point rounding errors |
| `password_hash` / `google_sub` nullable | Independently nullable | Supports email-only, Google-only, and dual-auth; `chk_users_has_auth` enforces at least one |
| `previous_price` single field | Not a history table | PRD explicitly excludes time-series in MVP; snapshots `old_price`/`new_price` on Notification |
| `result` as VARCHAR + CHECK | Not PostgreSQL ENUM | ENUM changes require non-transactional DDL; VARCHAR+CHECK is migration-safe |
| Partial index on unread notifications | `WHERE read_at IS NULL` | Index stays small as rows are dismissed; avoids unbounded growth |

---

## 3. API Contracts

### 3.1 Endpoint Summary

All endpoints prefixed `/api/v1/`. Authenticated endpoints require `session` JWT cookie. `user_id` never accepted in any request body.

| Method | Path | Auth | Responsibility |
|--------|------|------|----------------|
| POST | `/api/v1/auth/register` | No | Create email/password account; issue session cookie |
| POST | `/api/v1/auth/login` | No | Authenticate; issue session cookie |
| POST | `/api/v1/auth/logout` | Yes | Expire session cookie |
| GET | `/api/v1/auth/google/login` | No | Redirect to Google consent screen |
| GET | `/api/v1/auth/google/callback` | No | Complete OIDC flow; issue cookie; redirect to dashboard |
| POST | `/api/v1/auth/password-reset` | No | Request reset email (always 200) |
| POST | `/api/v1/auth/password-reset/confirm` | No | Submit token + new password |
| PUT | `/api/v1/auth/password` | Yes | Change password for authenticated user |
| GET | `/api/v1/products` | Yes | Dashboard: products + unread notification count |
| POST | `/api/v1/products` | Yes | Add product URL to tracking list |
| DELETE | `/api/v1/products/{product_id}` | Yes | Remove tracked product |
| GET | `/api/v1/notifications` | Yes | Paginated notification history |
| PATCH | `/api/v1/notifications/{notification_id}/read` | Yes | Dismiss notification (idempotent) |

### 3.2 Pydantic Model Catalog

#### Identity Models (`services/webapp/webapp/domains/identity/models/contracts/api/`)

```python
# register.py [new]
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)

class RegisterResponse(BaseModel):
    id: UUID
    email: str
    created_at: datetime

# login.py [new]
class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1, max_length=128)

class LoginResponse(BaseModel):
    id: UUID
    email: str

# google_callback.py [new]
class GoogleCallbackParams(BaseModel):
    code: str
    state: str

# password_reset.py [new]
class PasswordResetRequest(BaseModel):
    email: EmailStr

class PasswordResetResponse(BaseModel):
    message: str = "If an account exists for this email, a password reset link has been sent."

# password_reset_confirm.py [new]
class ConfirmResetRequest(BaseModel):
    token: str = Field(..., min_length=1, max_length=256)
    new_password: str = Field(..., min_length=8, max_length=128)

class ConfirmResetResponse(BaseModel):
    message: str = "Password has been reset successfully."

# change_password.py [new]
class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=1, max_length=128)
    new_password: str = Field(..., min_length=8, max_length=128)

class ChangePasswordResponse(BaseModel):
    message: str = "Password changed successfully."
```

#### Tracker Models (`services/webapp/webapp/domains/tracker/models/contracts/api/`)

```python
# add_product.py [new]
class AddProductRequest(BaseModel):
    url: str = Field(..., min_length=1, max_length=2048)

# dashboard.py [new]
class ProductResponse(BaseModel):
    id: UUID
    url: str
    product_name: str
    current_price: str          # Decimal serialised as string — no float precision loss
    previous_price: str | None  # null if price never changed
    last_checked_at: datetime | None
    created_at: datetime

class DashboardResponse(BaseModel):
    products: list[ProductResponse]
    unread_notification_count: int = Field(..., ge=0)

# notifications.py [new]
class NotificationResponse(BaseModel):
    id: UUID
    tracked_product_id: UUID
    old_price: str      # decimal string
    new_price: str      # decimal string
    created_at: datetime
    read_at: datetime | None

class NotificationCursor(BaseModel):
    next_cursor: str | None  # base64-encoded created_at; null = last page

class NotificationListResponse(BaseModel):
    data: list[NotificationResponse]
    pagination: NotificationCursor
```

#### Shared Model (`services/webapp/webapp/models/contracts/api/errors.py`)

```python
# errors.py [new]
class ErrorResponse(BaseModel):
    detail: str   # human-readable; safe to display
    code: str     # machine-readable; e.g. "DUPLICATE_PRODUCT"
```

### 3.3 Endpoint Behavior Specs

#### POST /api/v1/auth/register
- **201**: validate → RegisterUser flow → set JWT cookie → return RegisterResponse
- **409** `EMAIL_ALREADY_REGISTERED`: email taken
- **422** `VALIDATION_ERROR`: invalid email format or password < 8 chars

#### POST /api/v1/auth/login
- **200**: validate → LoginUser flow → set JWT cookie → return LoginResponse
- **401** `INVALID_CREDENTIALS`: email not found, wrong password, or Google-only account (no enumeration)

#### POST /api/v1/auth/logout
- **204**: validate cookie → LogoutUser flow (no-op) → expire cookie (`Max-Age=0`)
- **401** `AUTHENTICATION_REQUIRED`: missing/invalid cookie

#### GET /api/v1/auth/google/login
- **302**: generate state+nonce → store in TokenStore (TTL 300s) → redirect to Google

#### GET /api/v1/auth/google/callback
- **303** → `/dashboard`: exchange code → verify id_token → find-or-create User → set cookie → redirect
- OIDC errors redirect browser to `/login?error=<code>` (no JSON — browser mid-redirect)

#### POST /api/v1/auth/password-reset
- **200** always: silent if email not found; sends reset email only if account exists; prevents enumeration

#### POST /api/v1/auth/password-reset/confirm
- **200**: load valid tokens → bcrypt-verify → mark used → update password
- **400** `INVALID_RESET_TOKEN`: not found, expired, or already used
- **422** `VALIDATION_ERROR`: new password < 8 chars

#### PUT /api/v1/auth/password
- **200**: user_id from JWT → ChangePassword flow
- **401** `INVALID_CREDENTIALS`: wrong current password
- **422** `PASSWORD_CHANGE_NOT_ALLOWED`: Google-only account

#### GET /api/v1/products (Dashboard)
- **200**: `asyncio.gather(list_products, count_unread)` → return DashboardResponse
- Prices serialised as decimal strings via `str(price.value)`

#### POST /api/v1/products
- **201**: parse ProductUrl → check limit → check duplicate → scrape → save → return ProductResponse
- **409** `DUPLICATE_PRODUCT`: same URL already tracked by user
- **422** `INVALID_PRODUCT_URL`: non-http/https, localhost, or RFC-1918
- **422** `PRODUCT_LIMIT_EXCEEDED`: user already has 5 products
- **422** `SCRAPING_FAILED`: scraper returned failure

#### DELETE /api/v1/products/{product_id}
- **204**: load product → verify ownership → delete (ownership failure = 404, no enumeration)
- **404** `PRODUCT_NOT_FOUND`: not found or wrong owner

#### GET /api/v1/notifications
- **200**: cursor-based pagination (`limit` default 20 max 50, `cursor` = base64 `created_at`)
- **400** `INVALID_CURSOR`: malformed cursor

#### PATCH /api/v1/notifications/{notification_id}/read
- **200**: load → verify ownership → idempotent if `read_at` already set → set `read_at` → return NotificationResponse
- **404** `NOTIFICATION_NOT_FOUND`: not found or wrong owner

### 3.4 Auth Strategy

**Cookie:** `session=<jwt>; HttpOnly; Secure; SameSite=Lax; Path=/; Max-Age=86400`

**JWT claims:** `sub` = user_id (UUID string), `exp` = now+86400, `iat` = now. Algorithm: HS256. Secret from AWS Secrets Manager via `config.jwt_secret`.

**`get_current_user` dependency:** reads `session` cookie → decodes + verifies JWT → loads User by `sub`. Returns 401 (`AUTHENTICATION_REQUIRED`) for any failure without distinguishing absent/expired/invalid.

### 3.5 Error Response Format

```json
{ "detail": "A product with this URL is already being tracked.", "code": "DUPLICATE_PRODUCT" }
```

All FastAPI exception handlers in `main.py` produce this shape. Pydantic `RequestValidationError` is overridden to collapse nested validation errors to the first message. Generic `Exception` handler returns `INTERNAL_ERROR` — no stack traces to clients.

---

## 4. Cross-Dimensional Alignment

### Aligned ✅

| Check | Result |
|-------|--------|
| TrackedProduct fields: code ↔ data ↔ API | `id`, `user_id`, `url`, `product_name`, `current_price`, `previous_price`, `last_checked_at`, `created_at` — identical across all three |
| Notification fields: code ↔ data ↔ API | `id`, `user_id`, `tracked_product_id`, `old_price`, `new_price`, `created_at`, `read_at` — identical |
| Error taxonomy: code ↔ API error registry | All 14 domain errors map to correct HTTP codes; API error code strings match error class names |
| Auth strategy | JWT HttpOnly cookie `session` — consistent in HLD, lld-code, lld-api |
| Dashboard: code flow ↔ API endpoint | `GetDashboard` (asyncio.gather) maps directly to `GET /api/v1/products` returning DashboardResponse |
| Price type chain | `Price (Decimal)` → `DECIMAL(10,2)` DB → serialised as `str` in API responses — consistent |
| `user_id` never in request body | Confirmed across all three documents |
| Notification dismiss idempotency | `DismissNotification` flow idempotent (lld-code) ↔ `PATCH /notifications/{id}/read` idempotent (lld-api) |

### Minor Documentation Inconsistencies (non-functional)

| Inconsistency | Resolution |
|---------------|------------|
| `google_sub` uniqueness: lld-code mentioned partial UNIQUE index (`WHERE google_sub IS NOT NULL`); lld-data uses full UNIQUE constraint | PostgreSQL naturally treats NULLs as distinct in UNIQUE indexes — both achieve identical behaviour. **Use full UNIQUE constraint** as specified in lld-data. |
| Index name: lld-code used `idx_tracked_products_user_id`; lld-data uses `idx_tracked_products_user_id_created_at` | lld-data is authoritative for all index definitions. Use `idx_tracked_products_user_id_created_at`. |

---

## 5. Design Traceability

| LLD Component | HLD Section | HLD Decision |
|---------------|-------------|--------------|
| Three deployment units (webapp, monitor_lambda, scraper_lambda) | §4 System Architecture | FastAPI monolith + two Lambdas |
| `scraper_client` as ACL in webapp | §5 Bounded Contexts | "Scraper Client" context = ACL for boto3 invoke |
| `asyncio.Semaphore(20)` in PriceCheckCycleFlow | §7 Resilience | Bounded concurrency on Lambda invocations |
| Retry with exponential backoff (3× max) | §7 Resilience | Scraping retry strategy |
| JWT HttpOnly Secure cookie | §9 Security | Session management strategy |
| `DECIMAL(10,2)` for all prices | §6 Data Architecture | "price fields use DECIMAL(10,2)" |
| UUIDv4 PKs | §6 Data Architecture | "globally unique identifiers" |
| `users.previous_price` single field (no history) | §6 Data Architecture | "no historical price data in MVP" |
| Alembic migrations in `services/webapp/` | §6 Data Architecture | Single migration owner |
| `GET /api/v1/products` returns dashboard (products + unread count) | §14 Planned Endpoints | "dashboard endpoint" |
| `POST /api/v1/auth/password-reset` always returns 200 | §8 Auth Design | Prevents account enumeration |
| Monitor Lambda reads `tracked_products` as cross-context read | §5 Bounded Contexts | Sanctioned read-only cross-context access |
| Structured JSON logs, no PII, `url_hash` as identifier | §12 Observability | Logging strategy |

---

## 6. Implementation Order

1. Domain models, value objects, error hierarchies (all contexts) — pure, no I/O
2. Port protocols (all contexts) — contracts before implementations
3. Scraper Lambda flow + handler — standalone, testable in isolation
4. `scraper_client` ACL adapter — needed by both webapp and monitor_lambda
5. SQLAlchemy ORM models + Alembic initial migration
6. Identity flows + SQLAlchemy adapters — foundation for all authenticated ops
7. Tracker flows + SQLAlchemy adapters
8. Notifier write adapter
9. Monitor Lambda flow + handler
10. FastAPI routes (all contexts) + app factory + DI wiring

---

## 7. Open Questions

| # | Question | Impact | Owner |
|---|----------|--------|-------|
| 1 | Frontend origin URL for CORS `allow_origins` | CORS middleware config | Product |
| 2 | Google callback error redirect path: `/login?error=<code>` correct? | OIDC error UX | Product |
| 3 | Notification list scope: all vs unread only in `GET /notifications` | API behaviour | Product |
| 4 | Price check log retention: 90 days sufficient for incident post-mortems? | Data retention job | Ops |
| 5 | `product_name` never refreshed after add — MVP tolerance for stale names? | Dashboard UX | Product |
| 6 | `TokenStore` MVP implementation: in-memory dict or Redis? | Stateless constraint for multi-instance ECS | Infra |