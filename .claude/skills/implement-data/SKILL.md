---
name: implement-data
version: 1.0.0
description: |
  Implement data models, repositories, and queries from design specifications.
  Use when writing database schemas, creating Pydantic models, building repositories,
  implementing CRUD operations, writing SQL queries, or creating migrations.
  Relevant for SQLAlchemy, asyncpg, Pydantic, PostgreSQL, data access layers.
---

# Data Implementation

> Transform data designs into production-ready, type-safe data access code.

## Quick Reference

| Aspect | Details |
|--------|---------|
| **Invokes** | `test/unit`, `test/integration`, `review/data` |
| **Invoked By** | `design/data`, `implement/python`, `implement/api` |
| **Outputs** | Models, repositories, migrations, queries |

---

## Core Workflow

1. **Verify Design** — Confirm access patterns documented in `design/data` output
2. **Generate Schema** — Create DDL with constraints, indexes, FKs
3. **Define Models** — Build Pydantic models with domain types
4. **Build Repository** — Implement data access with async patterns
5. **Write Queries** — Follow documented access patterns exactly
6. **Create Migration** — Version schema changes
7. **Validate** — Run type checker and tests

---

## Must Rules

### Schema Implementation







- **MUST** create FK constraints at database level, not just application
- **MUST** add index on every foreign key column

- **MUST** use `DECIMAL`/`NUMERIC` for monetary values (never float)

- **MUST** include audit columns: `created_at`, `updated_at`, `created_by`

- **MUST** define `ON DELETE` behavior explicitly for every FK


- **MUST** use `CHECK` constraints for enum-like columns





### Domain Models



- **MUST** define typed identifiers: `OrderId = NewType("OrderId", str)`

- **MUST** use Pydantic `BaseModel` with `frozen=True` for entities

- **MUST** validate at model boundaries with Pydantic validators


- **MUST** separate write models (commands) from read models (queries)




### Repository Pattern

- **MUST** inject database connection as dependency



- **MUST** use async for all I/O operations
- **MUST** return domain models, not raw dicts or ORM objects
- **MUST** define repository interface (Protocol) before implementation




- **MUST** handle `None` explicitly—never return ambiguous results

### Query Implementation





- **MUST** use parameterized queries (never string concatenation)
- **MUST** paginate all list queries with cursor-based pagination
- **MUST** specify explicit column lists (never `SELECT *`)



- **MUST** match query to documented access pattern


- **MUST** use `LIMIT` on every query returning multiple rows

### Transactions



- **MUST** define transaction boundaries at use-case level



- **MUST** use context managers for transaction scope
- **MUST** implement idempotency keys for write operations


---






## Never Rules

### Schema

- **NEVER** use `SERIAL`/auto-increment for external-facing IDs

- **NEVER** store multiple values in single column (CSV, JSON arrays)





- **NEVER** use reserved words as identifiers (`user`, `order`, `table`)
- **NEVER** create circular foreign key dependencies
- **NEVER** skip NOT NULL when field is required

### Queries

- **NEVER** use `SELECT *` in production code






- **NEVER** execute queries without `WHERE` on large tables
- **NEVER** use `OFFSET` for deep pagination (>1000 rows)
- **NEVER** apply functions on indexed columns in `WHERE` clause
- **NEVER** use `LIKE '%term%'` on unindexed columns
- **NEVER** return unbounded result sets

### Repository






- **NEVER** expose ORM models outside repository
- **NEVER** mix business logic with data access
- **NEVER** catch and swallow database exceptions silently
- **NEVER** hardcode connection strings
- **NEVER** use sync I/O inside async functions

### Anti-Patterns


- **NEVER** write N+1 queries (query in a loop)



- **NEVER** use primitive types for domain identifiers
- **NEVER** skip type hints on repository methods
- **NEVER** implement "god repository" with 20+ methods

---

## When → Then Decisions


### Model Design



| When | Then |
|------|------|
| Entity has identity | Create typed ID: `UserId = NewType("UserId", str)` |
| Data crosses API boundary | Use Pydantic model with validation |
| Read model differs from write | Separate `CreateUserRequest` from `UserResponse` |
| Entity is immutable after creation | Use `frozen=True` in model config |
| Field has business constraints | Add Pydantic `field_validator` |


### Query Strategy


| When | Then |
|------|------|
| Fetching by unique ID | Point lookup with primary key |
| Listing with pagination | Cursor-based with `(sort_key, id)` |
| Multiple entities by IDs | Batch with `WHERE id = ANY($1)` |
| Complex filtering | Composite index matching query shape |
| Full-text search needed | Use `tsvector`/`tsquery`, not `LIKE` |
| Aggregations needed | Pre-compute or use materialized view |


### Transaction Boundaries

| When | Then |
|------|------|
| Single entity mutation | Transaction in repository method |
| Multi-entity mutation | Transaction at use-case level |
| Read after own write | Use same connection or cache |
| Eventual consistency OK | Separate read replica |
| Idempotency required | Check idempotency key before write |

### Database Selection

| When | Then |
|------|------|
| PostgreSQL project | Load `refs/postgresql.md` |
| SQLite for testing | Load `refs/sqlite.md` |
| MySQL/MariaDB project | Load `refs/mysql.md` |
| Document store needed | Load `refs/mongodb.md` |

---

## Patterns

### ✅ Typed Domain Identifiers

```python
from typing import NewType
from pydantic import BaseModel, ConfigDict

# Type-safe identifiers prevent swapping arguments
OrderId = NewType("OrderId", str)
CustomerId = NewType("CustomerId", str)
Money = NewType("Money", Decimal)

class Order(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: OrderId
    customer_id: CustomerId
    total: Money
```

### ✅ Repository with Protocol

```python
from typing import Protocol

class OrderRepository(Protocol):
    async def get(self, order_id: OrderId) -> Order | None: ...
    async def save(self, order: Order) -> None: ...
    async def list_by_customer(
        self, customer_id: CustomerId, cursor: str | None, limit: int
    ) -> CursorPage[Order]: ...

class PostgresOrderRepository:
    def __init__(self, pool: asyncpg.Pool):
        self._pool = pool

    async def get(self, order_id: OrderId) -> Order | None:
        row = await self._pool.fetchrow(
            "SELECT id, customer_id, total FROM orders WHERE id = $1",
            order_id
        )
        return Order.model_validate(dict(row)) if row else None
```

### ✅ Cursor-Based Pagination

```python
async def list_by_customer(
    self,
    customer_id: CustomerId,
    cursor: str | None,
    limit: int = 20
) -> CursorPage[Order]:
    limit = min(limit, 100)  # Enforce max

    if cursor:
        created_at, last_id = decode_cursor(cursor)
        rows = await self._pool.fetch(
            """
            SELECT id, customer_id, total, created_at
            FROM orders
            WHERE customer_id = $1
              AND (created_at, id) < ($2, $3)
            ORDER BY created_at DESC, id DESC
            LIMIT $4
            """,
            customer_id, created_at, last_id, limit + 1
        )
    else:
        rows = await self._pool.fetch(
            """
            SELECT id, customer_id, total, created_at
            FROM orders
            WHERE customer_id = $1
            ORDER BY created_at DESC, id DESC
            LIMIT $2
            """,
            customer_id, limit + 1
        )

    has_more = len(rows) > limit
    items = [Order.model_validate(dict(r)) for r in rows[:limit]]
    next_cursor = encode_cursor(items[-1]) if has_more and items else None

    return CursorPage(items=items, next_cursor=next_cursor, has_more=has_more)
```

### ✅ Idempotent Write

```python
async def process_payment(self, event: PaymentEvent) -> None:
    async with self._pool.acquire() as conn:
        async with conn.transaction():
            # Check idempotency first
            exists = await conn.fetchval(
                "SELECT 1 FROM processed_events WHERE key = $1",
                event.idempotency_key
            )
            if exists:
                return

            # Execute business logic
            await self._execute_payment(conn, event)

            # Record idempotency key
            await conn.execute(
                "INSERT INTO processed_events (key, processed_at) VALUES ($1, $2)",
                event.idempotency_key, utc_now()
            )
```

### ✅ Batch Fetch (Avoid N+1)

```python
async def get_orders_with_items(
    self, order_ids: list[OrderId]
) -> list[OrderWithItems]:
    # Single query with JOIN
    rows = await self._pool.fetch(
        """
        SELECT
            o.id, o.customer_id, o.total,
            COALESCE(
                json_agg(json_build_object(
                    'product_id', oi.product_id,
                    'quantity', oi.quantity,
                    'unit_price', oi.unit_price
                )) FILTER (WHERE oi.id IS NOT NULL),
                '[]'
            ) as items
        FROM orders o
        LEFT JOIN order_items oi ON oi.order_id = o.id
        WHERE o.id = ANY($1)
        GROUP BY o.id
        """,
        order_ids
    )
    return [OrderWithItems.model_validate(dict(r)) for r in rows]
```

### ✅ Schema with Constraints

```sql
CREATE TABLE orders (
    id VARCHAR(26) PRIMARY KEY,  -- ULID format
    customer_id VARCHAR(26) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    total DECIMAL(12, 2) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ,
    created_by VARCHAR(26) NOT NULL,

    CONSTRAINT fk_customer FOREIGN KEY (customer_id)
        REFERENCES customers(id) ON DELETE RESTRICT,
    CONSTRAINT chk_status CHECK (
        status IN ('pending', 'confirmed', 'shipped', 'delivered', 'cancelled')
    ),
    CONSTRAINT chk_total_positive CHECK (total >= 0)
);

-- Index on FK for JOIN performance
CREATE INDEX idx_orders_customer ON orders(customer_id);

-- Composite index for customer's orders by date
CREATE INDEX idx_orders_customer_created
    ON orders(customer_id, created_at DESC, id DESC);
```

---

## Anti-Patterns

### ❌ N+1 Query

```python
# WRONG: N+1 database calls
orders = await repo.list_orders(customer_id)
for order in orders:
    order.items = await repo.get_items(order.id)  # N queries!
```

```python
# RIGHT: Single query with aggregation
orders = await repo.get_orders_with_items(customer_id)
```

### ❌ Primitive Obsession

```python
# WRONG: Easy to swap arguments
async def transfer(from_id: str, to_id: str, amount: float): ...

transfer("acc_123", "acc_456", 100.0)  # Which is from/to?
transfer("acc_456", "acc_123", 100.0)  # Oops, reversed!
```

```python
# RIGHT: Type-safe domain identifiers
AccountId = NewType("AccountId", str)
Money = NewType("Money", Decimal)

async def transfer(from_id: AccountId, to_id: AccountId, amount: Money): ...
```

### ❌ Leaky Repository

```python
# WRONG: Exposes ORM model
class OrderRepository:
    async def get(self, order_id: str) -> OrderORM:  # ORM leak!
        return await self.session.get(OrderORM, order_id)
```

```python
# RIGHT: Returns domain model
class OrderRepository:
    async def get(self, order_id: OrderId) -> Order | None:
        orm = await self.session.get(OrderORM, order_id)
        return Order.model_validate(orm.__dict__) if orm else None
```

### ❌ Unbounded Query

```sql
-- WRONG: Could return millions of rows
SELECT * FROM events WHERE type = 'page_view';
```

```sql
-- RIGHT: Always paginate
SELECT id, user_id, created_at FROM events
WHERE type = 'page_view' AND created_at < $cursor
ORDER BY created_at DESC
LIMIT 100;
```

### ❌ Function on Indexed Column

```sql
-- WRONG: Index cannot be used
SELECT * FROM orders WHERE DATE(created_at) = '2024-01-15';
```

```sql
-- RIGHT: Range query uses index
SELECT * FROM orders
WHERE created_at >= '2024-01-15 00:00:00'
  AND created_at < '2024-01-16 00:00:00';
```

### ❌ God Repository

```python
# WRONG: Too many responsibilities
class DataRepository:
    async def get_user(self, id): ...
    async def save_user(self, user): ...
    async def get_order(self, id): ...
    async def save_order(self, order): ...
    async def get_product(self, id): ...
    # 50 more methods...
```

```python
# RIGHT: Single responsibility per repository
class UserRepository: ...
class OrderRepository: ...
class ProductRepository: ...
```

---

## Skill Chaining

| Condition | Invoke | Handoff |
|-----------|--------|---------|
| No design artifacts exist | `design/data` | Request access patterns first |
| Schema ready, need DDL | `refs/{database}.md` | Database type |
| Implementation complete | `test/integration` | Repository + test database |
| Query performance issues | `optimize/performance` | Query plans, indexes |
| Review data layer quality | `review/data` | Repository code |

---

## Quality Gates

Before completing data implementation:

- [ ] Every access pattern from design has matching query
- [ ] All FKs have indexes
- [ ] All queries use parameterized inputs
- [ ] All list queries are paginated with `LIMIT`
- [ ] Domain models use typed identifiers
- [ ] Repository returns domain models, not ORM/dicts
- [ ] Transactions have explicit boundaries
- [ ] Write operations have idempotency strategy
- [ ] Migration file generated and reviewed
- [ ] Type checker passes (`ty check`)

---

## Deep References

Load or generate database-specific guidance as needed:
