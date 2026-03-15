# I/O Optimization Reference

> **Core Principle:** Batch calls. Every I/O is a scaling question.

Network and disk operations dominate latency. Minimize round trips, pool connections, design for horizontal scale.

---

## Must / Never

### Batching

| MUST | NEVER |
|------|-------|
| Batch database reads into single queries | Execute queries in loops (N+1) |
| Use bulk insert/update operations | Insert records one at a time |
| Fetch related data with JOINs or IN clauses | Fetch parent, then loop for children |
| Bound concurrent operations with semaphores | Fire unbounded parallel requests |

### Connections

| MUST | NEVER |
|------|-------|
| Pool database connections at module/app level | Create connections per request |
| Reuse HTTP clients with keep-alive | Instantiate new client per call |
| Configure pool min/max sizes explicitly | Use unbounded connection pools |
| Set `max_inactive_connection_lifetime` | Let idle connections accumulate |

### Scale Design

| MUST | NEVER |
|------|-------|
| Design stateless request handlers | Store request state in memory |
| Make all operations idempotent | Assume exactly-once execution |
| Paginate all collection endpoints | Return unbounded lists |
| Handle backpressure with bounded queues | Let producers overwhelm consumers |

### Resilience

| MUST | NEVER |
|------|-------|
| Set explicit timeouts on all I/O | Use default/infinite timeouts |
| Implement retry with exponential backoff | Retry immediately in tight loops |
| Add circuit breakers for external services | Let failing dependencies cascade |
| Use jitter in retry delays | Use fixed retry intervals |

---

## When / Then

### Query Patterns

| WHEN | THEN |
|------|------|
| Fetching multiple records by ID | Use `WHERE id IN (...)` or `ANY($1)` |
| Loading entity with relations | JOIN in single query or batch lookup |
| Building complex object graphs | Use DataLoader pattern |
| Inserting multiple records | Use `INSERT ... VALUES` bulk or `insert_many()` |

### Pagination

| WHEN | THEN |
|------|------|
| API endpoint returns collections | Implement cursor-based pagination |
| Dataset is small (<1000) and stable | Offset pagination acceptable |
| Results must be consistent during iteration | Use cursor (keyset) pagination |
| Building admin/internal UIs | Offset pagination acceptable |

### Caching

| WHEN | THEN |
|------|------|
| Data is read-heavy, rarely changes | Implement read-through cache |
| Computation is expensive | Use cache-aside with appropriate TTL |
| Data is updated | Invalidate cache immediately after write |
| Cache key depends on parameters | Hash parameters into cache key |

### Async Patterns

| WHEN | THEN |
|------|------|
| Calling external HTTP services | Use `async/await` with shared client |
| Multiple independent I/O operations | Execute concurrently with `TaskGroup` |
| Blocking library in async context | Wrap with `asyncio.to_thread()` |
| Processing message queues | Use async consumers with bounded concurrency |

---

## Patterns

### Batch Database Reads

```python
# Single query for multiple IDs
users = await db.fetch_all(
    "SELECT * FROM users WHERE id = ANY($1)",
    list(user_ids)
)
user_map = {u.id: u for u in users}
```

### Connection Pool Setup

```python
# Database pool (module-level)
pool = await asyncpg.create_pool(
    dsn,
    min_size=5,
    max_size=20,
    max_inactive_connection_lifetime=300,
)

# HTTP client (module-level)
client = httpx.AsyncClient(
    limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
    timeout=httpx.Timeout(30.0),
)
```

### N+1 Prevention with JOIN

```python
# Single query with JOIN
posts_with_authors = await db.fetch_all("""
    SELECT p.*, u.name as author_name
    FROM posts p
    JOIN users u ON p.author_id = u.id
    WHERE p.created_at > $1
""", cutoff_date)
```

### Cursor Pagination

```python
async def fetch_page(
    cursor: str | None = None,
    limit: int = 100,
) -> tuple[list[Item], str | None]:
    query = "SELECT * FROM items"
    if cursor:
        query += " WHERE id > $1 ORDER BY id LIMIT $2"
        items = await db.fetch_all(query, cursor, limit + 1)
    else:
        query += " ORDER BY id LIMIT $1"
        items = await db.fetch_all(query, limit + 1)

    has_next = len(items) > limit
    next_cursor = items[-1].id if has_next else None
    return items[:limit], next_cursor
```

### Read-Through Cache

```python
async def get_user(user_id: int) -> User:
    cache_key = f"user:{user_id}"
    if cached := await cache.get(cache_key):
        return User.model_validate_json(cached)

    user = await db.fetch_user(user_id)
    await cache.set(cache_key, user.model_dump_json(), ex=300)
    return user
```

### Concurrent HTTP with Bounded Concurrency

```python
semaphore = asyncio.Semaphore(10)

async def fetch_with_limit(url: str) -> Response:
    async with semaphore:
        return await client.get(url)

async with asyncio.TaskGroup() as tg:
    tasks = [tg.create_task(fetch_with_limit(url)) for url in urls]
results = [t.result() for t in tasks]
```

### Retry with Exponential Backoff

```python
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type((ConnectionError, TimeoutError)),
)
async def fetch_with_retry(url: str) -> Response:
    return await client.get(url, timeout=5.0)
```

### Circuit Breaker

```python
from circuitbreaker import circuit

@circuit(failure_threshold=5, recovery_timeout=30)
async def call_external_service(data: dict) -> Response:
    return await external_client.post("/api", json=data, timeout=5.0)
```

---

## Anti-Patterns

### N+1 Queries

```python
# ❌ WRONG: N+1 pattern
for user_id in user_ids:
    user = await db.fetch_one("SELECT * FROM users WHERE id = $1", user_id)
    results.append(user)

# ✅ FIX: Batch query
users = await db.fetch_all("SELECT * FROM users WHERE id = ANY($1)", list(user_ids))
```

### Connection Per Request

```python
# ❌ WRONG: New connection each request
async def get_data():
    conn = await asyncpg.connect(dsn)  # Expensive!
    try:
        return await conn.fetch("SELECT ...")
    finally:
        await conn.close()

# ✅ FIX: Use shared pool
async def get_data():
    async with pool.acquire() as conn:
        return await conn.fetch("SELECT ...")
```

### Unbounded Lists

```python
# ❌ WRONG: Returns all records
@app.get("/users")
async def list_users():
    return await db.fetch_all("SELECT * FROM users")  # Could be millions!

# ✅ FIX: Paginate
@app.get("/users")
async def list_users(cursor: str | None = None, limit: int = 100):
    users, next_cursor = await fetch_page(cursor, min(limit, 100))
    return {"users": users, "next_cursor": next_cursor}
```

### Blocking I/O in Async

```python
# ❌ WRONG: Blocks event loop
async def fetch_data():
    response = requests.get(url)  # Sync library!
    return response.json()

# ✅ FIX: Use async client or thread
async def fetch_data():
    return await client.get(url)  # httpx async
# OR
async def fetch_data():
    return await asyncio.to_thread(requests.get, url)
```

### Sequential External Calls

```python
# ❌ WRONG: Sequential, slow
results = []
for url in urls:
    response = await client.get(url)
    results.append(response)

# ✅ FIX: Concurrent with semaphore
async with asyncio.TaskGroup() as tg:
    tasks = [tg.create_task(fetch_with_semaphore(url)) for url in urls]
results = [t.result() for t in tasks]
```

### No Retry Logic

```python
# ❌ WRONG: Single attempt, fails on transient error
response = await client.post(url, json=data)

# ✅ FIX: Retry with backoff
@retry(stop=stop_after_attempt(3), wait=wait_exponential())
async def post_with_retry(url: str, data: dict):
    return await client.post(url, json=data, timeout=5.0)
```

### Cache Without Invalidation

```python
# ❌ WRONG: Stale data after update
async def update_user(user_id: int, data: dict):
    await db.update_user(user_id, data)
    # Cache still has old data!

# ✅ FIX: Invalidate on write
async def update_user(user_id: int, data: dict):
    user = await db.update_user(user_id, data)
    await cache.delete(f"user:{user_id}")
    return user
```

---

## Scale Checklist

Before shipping, verify:

- [ ] **Stateless** — No instance-local state? Horizontally scalable?
- [ ] **Idempotent** — Safe to retry? No duplicate side effects?
- [ ] **Paginated** — All collections use cursor/offset? No unbounded lists?
- [ ] **Pooled** — DB and HTTP connections reused from pools?
- [ ] **Backpressure** — Queues bounded? Producers throttled when needed?
- [ ] **Timeouts** — All I/O operations have explicit timeouts?
- [ ] **Retries** — Transient failures handled with backoff?
- [ ] **Monitored** — Slow queries logged? Latency metrics exposed?

---

## Quick Reference

| Operation | Pattern | Example |
|-----------|---------|---------|
| Multiple DB reads | `WHERE id = ANY($1)` | `fetch_all(..., list(ids))` |
| Bulk insert | `insert_many()` | `db.insert_many(records)` |
| HTTP calls | Shared client + semaphore | `TaskGroup` + `Semaphore(10)` |
| Pagination | Cursor-based | `WHERE id > $cursor ORDER BY id LIMIT $n` |
| Caching | Read-through + invalidate | Get→miss→fetch→set; delete on write |
| Retries | Exponential backoff | `tenacity` with `wait_exponential()` |
| Resilience | Circuit breaker | `@circuit(failure_threshold=5)` |

---

## Profiling

### Log Slow Queries

```python
async def timed_query(query: str, *args):
    start = time.perf_counter()
    result = await db.fetch_all(query, *args)
    elapsed = time.perf_counter() - start
    if elapsed > 0.1:
        logger.warning("slow_query", duration_ms=elapsed*1000, query=query[:100])
    return result
```

### Trace I/O Operations

```python
from opentelemetry import trace
tracer = trace.get_tracer(__name__)

async def fetch_data(resource_id: int):
    with tracer.start_as_current_span("fetch_data") as span:
        span.set_attribute("resource_id", resource_id)
        with tracer.start_as_current_span("db_query"):
            return await db.fetch(resource_id)
```
