# Access Patterns Reference

> Comprehensive guidance on designing, validating, and optimizing data access patterns before implementation.

---

## Quick Reference

| Pattern Type | Use When | Key Consideration |
|--------------|----------|-------------------|
| **Point Lookup** | Fetching single entity by ID | Must use indexed key |
| **Range Scan** | Time-series, ordered lists | Requires sort key strategy |
| **Cursor Pagination** | Large datasets, infinite scroll | Stable sort order required |
| **Offset Pagination** | Small datasets, page numbers | Degrades at scale |
| **Batch Write** | Bulk imports, ETL | Idempotency keys essential |
| **Upsert** | Sync operations, idempotent writes | Define conflict resolution |
| **Read-Your-Writes** | User-facing after mutation | Route to leader or cache |
| **Eventual Consistency** | Analytics, feeds, search | Define staleness SLA |

---

## Must Rules

### Query Design

- **MUST** enumerate every access pattern before schema design
- **MUST** define latency targets (p50, p99) for each pattern
- **MUST** ensure every query can use an index (no full table scans)
- **MUST** paginate all list queries—no unbounded result sets
- **MUST** specify expected cardinality (1, 0..1, 0..N, 1..N)
- **MUST** document query frequency (requests/sec or daily volume)
- **MUST** validate access patterns against partition strategy

### Index Strategy

- **MUST** define indexes to support access patterns, not vice versa
- **MUST** consider write amplification when adding indexes
- **MUST** use composite indexes with correct column order (high→low selectivity)
- **MUST** measure index size impact on memory and storage
- **MUST** plan index maintenance windows for large tables

### Consistency

- **MUST** define consistency requirement per access pattern explicitly
- **MUST** document acceptable staleness (seconds, minutes, eventual)
- **MUST** implement read-your-writes for user-mutated data
- **MUST** use transactions for multi-entity mutations requiring atomicity

### Pagination

- **MUST** use cursor-based pagination for datasets > 10K rows
- **MUST** include total count only when explicitly required (expensive)
- **MUST** enforce maximum page size (never let clients request unlimited)
- **MUST** use stable sort keys that guarantee deterministic ordering

---

## Never Rules

### Query Design

- **NEVER** design schema before knowing query patterns
- **NEVER** return unbounded results (always LIMIT)
- **NEVER** use SELECT * in production code
- **NEVER** execute queries without WHERE clause on large tables
- **NEVER** filter in application when database can filter
- **NEVER** assume query patterns won't change

### Index Strategy

- **NEVER** create indexes speculatively—measure need first
- **NEVER** index columns with low cardinality alone (boolean, enum)
- **NEVER** ignore index bloat on frequently updated columns
- **NEVER** use function calls on indexed columns in WHERE (kills index)
- **NEVER** over-index—each index costs write performance

### Consistency

- **NEVER** assume strong consistency without explicit configuration
- **NEVER** use eventual consistency for financial or inventory data
- **NEVER** ignore read-after-write race conditions
- **NEVER** mix consistency requirements in single transaction

### Pagination

- **NEVER** use OFFSET for deep pagination (performance degrades linearly)
- **NEVER** paginate without ORDER BY (non-deterministic results)
- **NEVER** expose internal IDs as cursors (security risk)
- **NEVER** cache paginated results without invalidation strategy

---

## When → Then Decisions

### Query Type Selection

| When | Then |
|------|------|
| Fetching entity by unique identifier | Point lookup with primary key |
| Fetching entity by non-unique attribute | Secondary index + LIMIT 1 |
| Listing entities in time order | Range scan on timestamp index |
| Searching text content | Full-text search index (not LIKE '%x%') |
| Aggregating metrics | Pre-computed aggregates or OLAP store |
| Complex filtering + sorting | Composite index matching query shape |

### Pagination Strategy

| When | Then |
|------|------|
| Dataset < 1K rows, rare access | Offset pagination acceptable |
| Dataset > 10K rows | Cursor-based pagination required |
| Need "jump to page N" | Offset with strict max page limit |
| Infinite scroll / "load more" | Cursor with opaque encoded token |
| Real-time feed with new items | Cursor + polling or streaming |
| Sort order may change | Re-fetch from beginning on sort change |

### Consistency Selection

| When | Then |
|------|------|
| User views own recent mutation | Read-your-writes (session affinity or cache) |
| Financial transaction | Strong consistency (accept latency) |
| Social feed or recommendations | Eventual consistency (sub-second staleness OK) |
| Search results | Eventual consistency (index lag acceptable) |
| Inventory/stock levels | Strong consistency for decrement; eventual for display |
| Leader election / distributed lock | Linearizable consistency required |
| Analytics dashboard | Eventual consistency with defined refresh interval |

### Index Strategy

| When | Then |
|------|------|
| Query filters on column A | Index on A |
| Query filters A AND B | Composite index (A, B) |
| Query filters A, orders by B | Composite index (A, B) |
| Query uses A OR B | Separate indexes, let DB merge |
| Low cardinality column (status) | Composite with high-cardinality column |
| Range query on column | Column must be rightmost in composite |
| Need to avoid table lookup | Covering index (include all SELECT columns) |

### Caching Strategy

| When | Then |
|------|------|
| Read-heavy, rarely changes | Cache-aside with TTL |
| Writes must reflect immediately | Write-through cache |
| High write volume, read staleness OK | Write-behind (async) cache |
| User-specific data | Cache key includes user ID |
| Data has natural expiry | TTL matches business expiry |
| Complex invalidation logic | Event-driven invalidation |

---

## Patterns

### ✅ Point Lookup

```sql
-- Direct primary key lookup: O(1)
SELECT id, name, email, status
FROM users
WHERE id = $1;
```

```python
# Repository pattern
async def get_user(self, user_id: UserId) -> User | None:
    return await self.db.fetchone(
        "SELECT * FROM users WHERE id = $1", user_id
    )
```

---

### ✅ Cursor-Based Pagination

```sql
-- Efficient at any depth: O(log N)
SELECT id, created_at, title
FROM articles
WHERE created_at < $cursor_timestamp
  AND (created_at < $cursor_timestamp OR id < $cursor_id)
ORDER BY created_at DESC, id DESC
LIMIT 20;
```

```python
from pydantic import BaseModel
from typing import Generic, TypeVar
from base64 import b64encode, b64decode
import json

T = TypeVar("T")

class CursorPage(BaseModel, Generic[T]):
    items: list[T]
    next_cursor: str | None
    has_more: bool

def encode_cursor(created_at: datetime, id: str) -> str:
    return b64encode(json.dumps({"t": created_at.isoformat(), "id": id}).encode()).decode()

def decode_cursor(cursor: str) -> tuple[datetime, str]:
    data = json.loads(b64decode(cursor))
    return datetime.fromisoformat(data["t"]), data["id"]
```

---

### ✅ Read-Your-Writes Pattern

```python
class UserService:
    def __init__(self, db: Database, cache: Redis):
        self._db = db
        self._cache = cache

    async def update_profile(self, user_id: UserId, data: ProfileUpdate) -> User:
        user = await self._db.execute(
            "UPDATE users SET ... WHERE id = $1 RETURNING *", user_id
        )
        # Cache updated value for read-your-writes
        await self._cache.setex(
            f"user:{user_id}:profile",
            ttl=60,  # Short TTL, just for immediate reads
            value=user.model_dump_json()
        )
        return user

    async def get_profile(self, user_id: UserId) -> User:
        # Check cache first (catches recent self-updates)
        cached = await self._cache.get(f"user:{user_id}:profile")
        if cached:
            return User.model_validate_json(cached)
        # Fall back to replica (may be stale for other users' updates)
        return await self._db.replica.fetchone(
            "SELECT * FROM users WHERE id = $1", user_id
        )
```

---

### ✅ Idempotent Write with Deduplication

```python
async def process_payment(self, event: PaymentEvent) -> None:
    # Check idempotency key first
    existing = await self._db.fetchone(
        "SELECT id FROM processed_events WHERE idempotency_key = $1",
        event.idempotency_key
    )
    if existing:
        logger.info("event.duplicate", key=event.idempotency_key)
        return

    async with self._db.transaction():
        # Process the payment
        await self._execute_payment(event)
        # Record idempotency key
        await self._db.execute(
            "INSERT INTO processed_events (idempotency_key, processed_at) VALUES ($1, $2)",
            event.idempotency_key, utc_now()
        )
```

---

### ✅ Batch Read with IN Clause

```sql
-- Bounded batch: always limit IN clause size
SELECT id, name, price
FROM products
WHERE id = ANY($1::uuid[])
  AND deleted_at IS NULL;
```

```python
async def get_products_batch(
    self,
    product_ids: list[ProductId],
    batch_size: int = 100
) -> list[Product]:
    """Fetch products in batches to avoid oversized IN clauses."""
    results = []
    for chunk in chunked(product_ids, batch_size):
        rows = await self._db.fetch(
            "SELECT * FROM products WHERE id = ANY($1)",
            chunk
        )
        results.extend(Product.model_validate(row) for row in rows)
    return results
```

---

### ✅ Composite Index for Filter + Sort

```sql
-- Query pattern: filter by status, order by created_at
SELECT id, title, created_at
FROM orders
WHERE status = 'pending'
  AND created_at > $since
ORDER BY created_at ASC
LIMIT 50;

-- Optimal index: (status, created_at)
CREATE INDEX idx_orders_status_created
ON orders (status, created_at);
```

---

### ✅ Covering Index to Avoid Table Lookup

```sql
-- Query only needs these columns
SELECT user_id, email, last_login
FROM users
WHERE status = 'active'
ORDER BY last_login DESC
LIMIT 100;

-- Covering index includes all needed columns
CREATE INDEX idx_users_active_login
ON users (status, last_login DESC)
INCLUDE (user_id, email);
```

---

### ✅ Conditional/Partial Index

```sql
-- Only 5% of orders are 'pending', but queried frequently
CREATE INDEX idx_orders_pending
ON orders (created_at)
WHERE status = 'pending';

-- Much smaller than full index, faster to maintain
```

---

### ✅ Time-Series Range Query with Partitioning

```sql
-- Partition by month for time-series data
CREATE TABLE events (
    id UUID PRIMARY KEY,
    event_type VARCHAR(50),
    payload JSONB,
    created_at TIMESTAMP NOT NULL
) PARTITION BY RANGE (created_at);

CREATE TABLE events_2024_01 PARTITION OF events
    FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');

-- Query automatically prunes to relevant partitions
SELECT * FROM events
WHERE created_at >= '2024-01-15'
  AND created_at < '2024-01-16'
ORDER BY created_at;
```

---

### ✅ Optimistic Locking

```python
async def update_order(
    self,
    order_id: OrderId,
    updates: OrderUpdate,
    expected_version: int
) -> Order:
    result = await self._db.execute(
        """
        UPDATE orders
        SET status = $2, version = version + 1, updated_at = NOW()
        WHERE id = $1 AND version = $3
        RETURNING *
        """,
        order_id, updates.status, expected_version
    )
    if not result:
        raise ConcurrentModificationError(
            f"Order {order_id} was modified (expected version {expected_version})"
        )
    return Order.model_validate(result)
```

---

## Anti-Patterns

### ❌ N+1 Query Problem

```python
# WRONG: N+1 queries
orders = await db.fetch("SELECT * FROM orders WHERE user_id = $1", user_id)
for order in orders:
    # This executes N additional queries!
    items = await db.fetch("SELECT * FROM order_items WHERE order_id = $1", order.id)
    order.items = items
```

```python
# RIGHT: Single query with JOIN or batch fetch
orders = await db.fetch("""
    SELECT o.*,
           COALESCE(json_agg(oi.*) FILTER (WHERE oi.id IS NOT NULL), '[]') as items
    FROM orders o
    LEFT JOIN order_items oi ON oi.order_id = o.id
    WHERE o.user_id = $1
    GROUP BY o.id
""", user_id)
```

---

### ❌ Unbounded Query

```sql
-- WRONG: Could return millions of rows
SELECT * FROM events WHERE type = 'page_view';
```

```sql
-- RIGHT: Always paginate
SELECT * FROM events
WHERE type = 'page_view'
  AND created_at > $cursor
ORDER BY created_at
LIMIT 100;
```

---

### ❌ Offset Pagination at Scale

```sql
-- WRONG: O(offset) performance - scans and discards rows
SELECT * FROM articles ORDER BY created_at DESC LIMIT 20 OFFSET 100000;
-- Database must scan 100,020 rows to return 20
```

```sql
-- RIGHT: Cursor pagination - O(log N) constant time
SELECT * FROM articles
WHERE created_at < $cursor_timestamp
ORDER BY created_at DESC
LIMIT 20;
```

---

### ❌ Function on Indexed Column

```sql
-- WRONG: Index on created_at is NOT used
SELECT * FROM orders
WHERE DATE(created_at) = '2024-01-15';
```

```sql
-- RIGHT: Range query uses index
SELECT * FROM orders
WHERE created_at >= '2024-01-15 00:00:00'
  AND created_at < '2024-01-16 00:00:00';
```

---

### ❌ SELECT * in Production

```python
# WRONG: Fetches all columns including large TEXT/BLOB
users = await db.fetch("SELECT * FROM users WHERE status = 'active'")
```

```python
# RIGHT: Explicit column list
users = await db.fetch("""
    SELECT id, email, name, status, created_at
    FROM users
    WHERE status = 'active'
""")
```

---

### ❌ LIKE with Leading Wildcard

```sql
-- WRONG: Cannot use index, full table scan
SELECT * FROM products WHERE name LIKE '%widget%';
```

```sql
-- RIGHT: Use full-text search
SELECT * FROM products
WHERE to_tsvector('english', name) @@ to_tsquery('english', 'widget');

-- Or trigram index for partial matching
CREATE INDEX idx_products_name_trgm ON products USING gin (name gin_trgm_ops);
SELECT * FROM products WHERE name ILIKE '%widget%';  -- Now uses index
```

---

### ❌ Hot Partition

```sql
-- WRONG: All today's data hits single partition
CREATE TABLE events (...) PARTITION BY (DATE(created_at));
-- "Today" partition gets all writes, others are cold
```

```sql
-- RIGHT: Distribute writes with hash + time
CREATE TABLE events (...) PARTITION BY RANGE (created_at);
-- Use sub-partitioning or hash-based distribution within time ranges
-- Or: add random suffix to partition key for write distribution
```

---

### ❌ Missing Index on Foreign Key

```sql
-- WRONG: No index on foreign key
CREATE TABLE order_items (
    id UUID PRIMARY KEY,
    order_id UUID REFERENCES orders(id),  -- No index!
    product_id UUID,
    quantity INT
);

-- DELETE FROM orders WHERE id = $1
-- Must full-scan order_items to check FK constraint
```

```sql
-- RIGHT: Always index foreign keys
CREATE TABLE order_items (
    id UUID PRIMARY KEY,
    order_id UUID REFERENCES orders(id),
    product_id UUID,
    quantity INT
);
CREATE INDEX idx_order_items_order_id ON order_items(order_id);
```

---

### ❌ Over-Indexing

```sql
-- WRONG: Index for every possible query
CREATE INDEX idx1 ON orders(status);
CREATE INDEX idx2 ON orders(created_at);
CREATE INDEX idx3 ON orders(user_id);
CREATE INDEX idx4 ON orders(status, created_at);
CREATE INDEX idx5 ON orders(status, user_id);
CREATE INDEX idx6 ON orders(user_id, created_at);
-- 6 indexes = 6x write amplification
```

```sql
-- RIGHT: Minimal indexes covering actual patterns
-- Analyze actual query patterns first, then:
CREATE INDEX idx_orders_user_created ON orders(user_id, created_at DESC);
CREATE INDEX idx_orders_status_created ON orders(status, created_at DESC)
    WHERE status IN ('pending', 'processing');  -- Partial for hot statuses
```

---

### ❌ Inconsistent Read After Write

```python
# WRONG: Read from replica immediately after write to leader
async def update_and_fetch(self, user_id: UserId, data: dict) -> User:
    await self.db.leader.execute("UPDATE users SET ... WHERE id = $1", user_id)
    # Replica lag! May return stale data
    return await self.db.replica.fetchone("SELECT * FROM users WHERE id = $1", user_id)
```

```python
# RIGHT: Read from leader after write, or use cache
async def update_and_fetch(self, user_id: UserId, data: dict) -> User:
    # Option 1: Return from same write
    return await self.db.leader.fetchone(
        "UPDATE users SET ... WHERE id = $1 RETURNING *", user_id
    )

    # Option 2: Cache for read-your-writes
    user = await self.db.leader.execute(...)
    await self.cache.setex(f"user:{user_id}", 60, user.json())
    return user
```

---

## Access Pattern Template

Document every access pattern using this template:

```markdown
### Pattern: [Descriptive Name]

**Query:**
```sql
<exact SQL or pseudo-SQL>
```

**Frequency:** [X req/sec | Y calls/day]
**Latency Target:** p50 < Xms, p99 < Yms
**Consistency:** [strong | eventual | read-your-writes]
**Cardinality:** [1 | 0..1 | 0..N | 1..N]
**Volume:** [rows returned, bytes estimate]
**Index Required:** [column(s)]
**Partition Key:** [if applicable]
**Cache Strategy:** [none | TTL | invalidation]
```

---

## Index Selection Checklist

Before adding an index:

- [ ] Access pattern measured (not speculative)
- [ ] Column order matches query (filter → sort → select)
- [ ] Cardinality is sufficient (avoid indexing booleans alone)
- [ ] Write amplification acceptable for write volume
- [ ] Covering index considered if avoiding table lookup helps
- [ ] Partial index considered if query always filters subset
- [ ] Existing indexes checked for overlap (can one serve both?)

---

## Pagination Checklist

Before implementing pagination:

- [ ] Sort order is deterministic (includes unique tiebreaker)
- [ ] Cursor is opaque (not raw IDs or timestamps)
- [ ] Maximum page size enforced server-side
- [ ] Total count is optional (expensive on large tables)
- [ ] Cursor encodes enough state for stateless pagination
- [ ] Forward/backward navigation requirements defined

---

## Consistency Checklist

For each access pattern:

- [ ] Consistency level explicitly chosen (not defaulted)
- [ ] Staleness SLA defined for eventual consistency
- [ ] Read-your-writes handled for user-facing mutations
- [ ] Replica lag monitored and alerted
- [ ] Fallback behavior defined if consistency cannot be met
