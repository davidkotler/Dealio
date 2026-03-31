# Plan: Task 4 — SQLAlchemy ORM Models + Alembic Migration

## Context

Task 4 of the price-drop-tracker feature implements the database layer. We need SQLAlchemy 2.x ORM models (using `Mapped` + `mapped_column`) for all 5 tables and a hand-written Alembic migration `0001_initial_schema` that creates all tables, constraints, and indexes. The migration is the single source of truth for the schema; the ORM models provide the Python interface.

Two services are involved:
- `services/webapp` — owns the migration and 4 ORM models (identity, tracker, notifier domains)
- `services/monitor_lambda` — owns only `PriceCheckLogRecord` using its own `MonitorBase`

---

## Current State

| What | Status |
|------|--------|
| `services/webapp/alembic/env.py` | Exists — `target_metadata = None`, needs import update |
| `services/webapp/alembic/versions/` | Exists — empty (only `.gitkeep`) |
| `services/webapp/webapp/infrastructure/` | Does NOT exist — must create |
| Webapp `persistence/__init__.py` files | Exist (empty) across all 3 domains |
| `monitor_lambda/infrastructure/database/base.py` | Exists — `MonitorBase(DeclarativeBase)` ready |
| `monitor_lambda/domains/monitor/models/persistence/` | Does NOT exist — must create |
| All deps (sqlalchemy, asyncpg, alembic) in webapp | ✅ Already installed |
| Alembic in monitor_lambda | Not needed — webapp owns migrations |

---

## Files to Create

### 1. Webapp Base (Sub-task 4.1)

**`services/webapp/webapp/infrastructure/__init__.py`** — empty package marker

**`services/webapp/webapp/infrastructure/database/__init__.py`** — empty package marker

**`services/webapp/webapp/infrastructure/database/base.py`**
```python
"""SQLAlchemy declarative base for webapp ORM models."""
from sqlalchemy.orm import DeclarativeBase

class WebappBase(DeclarativeBase):
    """Base class for all webapp ORM models."""
```

---

### 2. UserRecord (Sub-task 4.2)

**`services/webapp/webapp/domains/identity/models/persistence/user_record.py`**

```python
import uuid
from datetime import datetime
from sqlalchemy import CheckConstraint, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from webapp.infrastructure.database.base import WebappBase

class UserRecord(WebappBase):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("email", name="uq_users_email"),
        UniqueConstraint("google_sub", name="uq_users_google_sub"),
        CheckConstraint("password_hash IS NOT NULL OR google_sub IS NOT NULL", name="chk_users_has_auth"),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    google_sub: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default="NOW()")
    updated_at: Mapped[datetime] = mapped_column(nullable=False, server_default="NOW()")
```

**`services/webapp/webapp/domains/identity/models/persistence/password_reset_token_record.py`**

```python
import uuid
from datetime import datetime
from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from webapp.infrastructure.database.base import WebappBase

class PasswordResetTokenRecord(WebappBase):
    __tablename__ = "password_reset_tokens"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default="NOW()")
```

---

### 3. TrackedProductRecord (Sub-task 4.3)

**`services/webapp/webapp/domains/tracker/models/persistence/tracked_product_record.py`**

```python
import uuid
from datetime import datetime
from decimal import Decimal
from sqlalchemy import CheckConstraint, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from webapp.infrastructure.database.base import WebappBase

class TrackedProductRecord(WebappBase):
    __tablename__ = "tracked_products"
    __table_args__ = (
        UniqueConstraint("user_id", "url", name="uq_tracked_products_user_url"),
        CheckConstraint("current_price >= 0", name="chk_tracked_products_current_price"),
        CheckConstraint("previous_price IS NULL OR previous_price >= 0", name="chk_tracked_products_previous_price"),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    product_name: Mapped[str] = mapped_column(String(500), nullable=False)
    current_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    previous_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    last_checked_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default="NOW()")
```

---

### 4. NotificationRecord (Sub-task 4.4)

**`services/webapp/webapp/domains/notifier/models/persistence/notification_record.py`**

```python
import uuid
from datetime import datetime
from decimal import Decimal
from sqlalchemy import CheckConstraint, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from webapp.infrastructure.database.base import WebappBase

class NotificationRecord(WebappBase):
    __tablename__ = "notifications"
    __table_args__ = (
        CheckConstraint("new_price < old_price", name="chk_notifications_price_drop"),
        CheckConstraint("old_price > 0", name="chk_notifications_old_price"),
        CheckConstraint("new_price >= 0", name="chk_notifications_new_price"),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    tracked_product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tracked_products.id", ondelete="CASCADE"), nullable=False)
    old_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    new_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default="NOW()")
    read_at: Mapped[datetime | None] = mapped_column(nullable=True)
```

---

### 5. PriceCheckLogRecord (Sub-task 4.5)

`MonitorBase` already exists at `services/monitor_lambda/monitor_lambda/infrastructure/database/base.py` — no changes needed.

**`services/monitor_lambda/monitor_lambda/domains/monitor/models/persistence/__init__.py`** — empty package marker

**`services/monitor_lambda/monitor_lambda/domains/monitor/models/persistence/price_check_log_record.py`**

```python
import uuid
from datetime import datetime
from sqlalchemy import CheckConstraint, ForeignKey, SmallInteger, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from monitor_lambda.infrastructure.database.base import MonitorBase

class PriceCheckLogRecord(MonitorBase):
    __tablename__ = "price_check_log"
    __table_args__ = (
        CheckConstraint("result IN ('success', 'failure')", name="chk_price_check_log_result"),
        CheckConstraint("retry_count >= 0 AND retry_count <= 10", name="chk_price_check_log_retry_count"),
        CheckConstraint(
            "(result = 'success' AND error_message IS NULL) OR (result = 'failure' AND error_message IS NOT NULL)",
            name="chk_price_check_log_error_message",
        ),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tracked_product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tracked_products.id", ondelete="CASCADE"), nullable=False)
    checked_at: Mapped[datetime] = mapped_column(nullable=False, server_default="NOW()")
    result: Mapped[str] = mapped_column(String(10), nullable=False)
    retry_count: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
```

---

### 6. Alembic Migration (Sub-task 4.6)

**`services/webapp/alembic/versions/0001_initial_schema.py`**

Hand-written (not autogenerated) because `price_check_log` belongs to `MonitorBase` (different metadata) and the partial index on notifications requires explicit SQL.

Structure:
- `revision = "0001_initial_schema"`, `down_revision = None`
- `upgrade()`: creates all 5 tables in dependency order (users → password_reset_tokens + tracked_products → notifications + price_check_log), then all named indexes
- `downgrade()`: drops indexes then tables in reverse order

Tables and all constraints match `LLD §2.2` exactly (named constraints per spec).

Indexes in `upgrade()`:
```sql
CREATE UNIQUE INDEX idx_users_google_sub ON users (google_sub)
CREATE INDEX idx_password_reset_tokens_token_hash ON password_reset_tokens (token_hash)
CREATE INDEX idx_password_reset_tokens_user_id ON password_reset_tokens (user_id)
CREATE INDEX idx_tracked_products_user_id_created_at ON tracked_products (user_id, created_at DESC)
CREATE INDEX idx_notifications_user_id_unread_created_at ON notifications (user_id, created_at DESC) WHERE read_at IS NULL
CREATE INDEX idx_notifications_user_id ON notifications (user_id)
CREATE INDEX idx_notifications_tracked_product_id ON notifications (tracked_product_id)
CREATE INDEX idx_price_check_log_tracked_product_id ON price_check_log (tracked_product_id)
CREATE INDEX idx_price_check_log_result_checked_at ON price_check_log (result, checked_at DESC)
```

Use `op.execute()` for the partial index (WHERE clause), `op.create_index()` for the rest.

---

### 7. Alembic env.py Update (Sub-task 4.7)

**Modify `services/webapp/alembic/env.py`** — update `target_metadata = None` to:

```python
# Import all webapp ORM models so Alembic detects them for autogenerate
from webapp.infrastructure.database.base import WebappBase
import webapp.domains.identity.models.persistence.user_record  # noqa: F401
import webapp.domains.identity.models.persistence.password_reset_token_record  # noqa: F401
import webapp.domains.tracker.models.persistence.tracked_product_record  # noqa: F401
import webapp.domains.notifier.models.persistence.notification_record  # noqa: F401

target_metadata = WebappBase.metadata
```

Note: `PriceCheckLogRecord` uses `MonitorBase` and is not imported here. The migration is hand-written to include `price_check_log` anyway.

---

## Files to Modify Summary

| File | Change |
|------|--------|
| `services/webapp/alembic/env.py` | Change `target_metadata = None` → import models + `WebappBase.metadata` |
| `services/webapp/webapp/domains/identity/models/persistence/__init__.py` | Already exists (empty) — no changes needed |
| `services/webapp/webapp/domains/tracker/models/persistence/__init__.py` | Already exists (empty) — no changes needed |
| `services/webapp/webapp/domains/notifier/models/persistence/__init__.py` | Already exists (empty) — no changes needed |

---

## Implementation Order

1. `infrastructure/database/base.py` (webapp Base) — foundation for all webapp models
2. `user_record.py` — no upstream ORM deps
3. `password_reset_token_record.py` — depends on `users` table name
4. `tracked_product_record.py` — depends on `users` table name
5. `notification_record.py` — depends on `users` + `tracked_products` table names
6. `price_check_log_record.py` (monitor_lambda) — depends on `tracked_products` table name
7. `alembic/env.py` update — needs all 4 webapp model imports to exist
8. `0001_initial_schema.py` — hand-written, no dependencies on ORM models at import time

---

## Verification

```bash
# Start PostgreSQL
docker run --rm -d -e POSTGRES_PASSWORD=test -e POSTGRES_DB=dealio -p 5432:5432 postgres:16

cd services/webapp
DATABASE_URL=postgresql+asyncpg://postgres:test@localhost:5432/dealio \
  uv run alembic upgrade head

# Confirm 5 tables
psql postgresql://postgres:test@localhost:5432/dealio -c "\dt"

# Confirm all indexes (including partial)
psql postgresql://postgres:test@localhost:5432/dealio -c "\di"

# Confirm chk_users_has_auth fires
psql postgresql://postgres:test@localhost:5432/dealio -c \
  "INSERT INTO users (id, email) VALUES (gen_random_uuid(), 'test@test.com');" \
  2>&1 | grep "chk_users_has_auth"

# Confirm downgrade
DATABASE_URL=postgresql+asyncpg://postgres:test@localhost:5432/dealio \
  uv run alembic downgrade base
psql postgresql://postgres:test@localhost:5432/dealio -c "\dt"  # expected: no tables
```
