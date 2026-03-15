# Performance Design Reference

> Design for performance from the start. Optimization is easier than redesign.

---

## 1. Core Principles

### MUST

- Establish performance budgets before implementation
- Define SLIs/SLOs for latency, throughput, and resource usage
- Consider data volume growth in all design decisions
- Profile assumptions with realistic data sizes
- Design hot paths for minimal allocations

### NEVER

- Assume "we'll optimize later" for critical paths
- Design without understanding expected load patterns
- Ignore memory allocation in tight loops
- Choose data structures without considering access patterns
- Block the event loop with synchronous operations

---

## 2. Data Structure Selection

### WHEN selecting collections THEN match structure to access pattern

| Access Pattern | Choose | Avoid |
|----------------|--------|-------|
| Frequent lookup by key | `dict` / HashMap | `list` linear scan |
| Ordered iteration | `list` | `dict` (pre-3.7) |
| Membership testing | `set` / `frozenset` | `list` |
| Priority access | `heapq` | sorted `list` |
| FIFO/LIFO | `deque` | `list.pop(0)` |
| Immutable sharing | `frozenset`, `tuple` | mutable copies |

```python
# ✅ Pattern: Right structure for lookup
users_by_id: dict[UserId, User] = {u.id: u for u in users}
user = users_by_id.get(target_id)  # O(1)

# ❌ Anti-pattern: Linear scan
user = next((u for u in users if u.id == target_id), None)  # O(n)
```

### WHEN data is read-heavy THEN prefer immutable structures

```python
# ✅ Pattern: Frozen for sharing across threads
from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class CacheEntry:
    key: str
    value: bytes
    expires_at: float
```

---

## 3. Algorithm Complexity

### MUST

- Document time/space complexity for public methods
- Prefer O(n log n) or better for hot paths
- Use iterators over materialized collections when possible
- Consider amortized complexity for batch operations

### NEVER

- Use O(n²) algorithms on unbounded inputs
- Nest loops over large collections without analysis
- Materialize large sequences when streaming suffices

### WHEN processing large datasets THEN stream

```python
# ✅ Pattern: Generator pipeline (O(1) memory)
def process_records(records: Iterable[Record]) -> Iterator[Result]:
    for record in records:
        if is_valid(record):
            yield transform(record)

# ❌ Anti-pattern: Materialized list (O(n) memory)
def process_records(records: list[Record]) -> list[Result]:
    return [transform(r) for r in records if is_valid(r)]
```

### WHEN combining collections THEN watch complexity

```python
# ✅ Pattern: Set intersection O(min(n,m))
common = set_a & set_b

# ❌ Anti-pattern: Nested loop O(n*m)
common = [a for a in list_a if a in list_b]
```

---

## 4. I/O & Async Patterns

### MUST

- Use async for all I/O: network, disk, database
- Batch I/O operations where possible
- Set explicit timeouts on all external calls
- Design for concurrent execution of independent operations

### NEVER

- Use `requests` (sync) in async code
- Perform I/O inside loops without batching
- Await in sequence when parallelism is possible
- Create unbounded concurrent tasks

### WHEN multiple independent I/O calls THEN parallelize

```python
# ✅ Pattern: Concurrent execution
async def fetch_all(ids: list[str]) -> list[Data]:
    tasks = [fetch_one(id) for id in ids]
    return await asyncio.gather(*tasks)

# ❌ Anti-pattern: Sequential execution
async def fetch_all(ids: list[str]) -> list[Data]:
    results = []
    for id in ids:
        results.append(await fetch_one(id))  # Serialized!
    return results
```

### WHEN batching I/O THEN use bounded concurrency

```python
# ✅ Pattern: Semaphore for backpressure
async def fetch_with_limit(ids: list[str], max_concurrent: int = 10) -> list[Data]:
    sem = asyncio.Semaphore(max_concurrent)

    async def fetch_bounded(id: str) -> Data:
        async with sem:
            return await fetch_one(id)

    return await asyncio.gather(*[fetch_bounded(id) for id in ids])
```

---

## 5. Caching Strategy

### MUST

- Define cache invalidation rules at design time
- Use appropriate TTLs based on data freshness requirements
- Consider cache stampede prevention
- Size caches based on working set, not total data

### NEVER

- Cache without invalidation strategy
- Use unbounded in-memory caches
- Cache mutable objects without copying
- Assume cache hits in correctness logic

### WHEN designing cache THEN specify key dimensions

| Dimension | Decision |
|-----------|----------|
| **Scope** | Request / Session / Application / Distributed |
| **Invalidation** | TTL / Event-driven / Manual |
| **Eviction** | LRU / LFU / FIFO / Size-based |
| **Consistency** | Strong / Eventual / Read-your-writes |

```python
# ✅ Pattern: Cache with clear semantics
@dataclass
class CacheConfig:
    ttl_seconds: int
    max_size: int
    eviction: Literal["lru", "lfu"] = "lru"
    invalidation: Literal["ttl", "event"] = "ttl"

@lru_cache(maxsize=1000)
def get_user_permissions(user_id: str) -> Permissions:
    return db.fetch_permissions(user_id)

# Explicit invalidation
def on_permission_change(user_id: str) -> None:
    get_user_permissions.cache_clear()  # Or targeted invalidation
```

### WHEN cache miss is expensive THEN prevent stampede

```python
# ✅ Pattern: Single-flight / lock-based loading
class Cache:
    def __init__(self):
        self._cache: dict[str, Any] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    async def get_or_load(self, key: str, loader: Callable) -> Any:
        if key in self._cache:
            return self._cache[key]

        lock = self._locks.setdefault(key, asyncio.Lock())
        async with lock:
            if key in self._cache:  # Double-check after acquiring lock
                return self._cache[key]
            value = await loader()
            self._cache[key] = value
            return value
```

---

## 6. Database Design

### MUST

- Design indexes based on query patterns
- Denormalize for read-heavy paths
- Plan partitioning strategy for large tables
- Use connection pooling with appropriate limits

### NEVER

- Design schemas without knowing query patterns
- Use `SELECT *` in application code
- Execute N+1 queries
- Hold transactions open during external calls

### WHEN designing queries THEN minimize round trips

```python
# ✅ Pattern: Single query with join
orders = await db.execute("""
    SELECT o.*, c.name as customer_name
    FROM orders o
    JOIN customers c ON o.customer_id = c.id
    WHERE o.status = :status
""", {"status": "pending"})

# ❌ Anti-pattern: N+1 queries
orders = await db.execute("SELECT * FROM orders WHERE status = :status", ...)
for order in orders:
    customer = await db.execute("SELECT * FROM customers WHERE id = :id", ...)  # N queries!
```

### WHEN reading large datasets THEN paginate

```python
# ✅ Pattern: Cursor-based pagination
async def iter_orders(batch_size: int = 100) -> AsyncIterator[Order]:
    cursor = None
    while True:
        query = "SELECT * FROM orders WHERE id > :cursor ORDER BY id LIMIT :limit"
        batch = await db.fetch_all(query, {"cursor": cursor or 0, "limit": batch_size})
        if not batch:
            break
        for row in batch:
            yield Order.from_row(row)
        cursor = batch[-1].id
```

---

## 7. API Design for Performance

### MUST

- Support pagination for list endpoints
- Enable sparse fieldsets / field selection
- Design for client-side caching (ETags, Cache-Control)
- Provide bulk endpoints for batch operations

### NEVER

- Return unbounded collections
- Require multiple round trips for common use cases
- Ignore response size in API design
- Force full resource fetch when partial suffices

### WHEN designing list endpoints THEN include limits

```python
# ✅ Pattern: Bounded pagination
@router.get("/orders", response_model=PaginatedResponse[Order])
async def list_orders(
    limit: int = Query(default=20, le=100),
    cursor: str | None = Query(default=None),
) -> PaginatedResponse[Order]:
    orders, next_cursor = await order_repo.paginate(limit, cursor)
    return PaginatedResponse(items=orders, next_cursor=next_cursor)
```

### WHEN clients need partial data THEN support field selection

```python
# ✅ Pattern: Sparse fieldsets
@router.get("/users/{id}")
async def get_user(
    id: UserId,
    fields: set[str] = Query(default={"id", "name", "email"}),
) -> dict:
    user = await user_repo.get(id)
    return {k: getattr(user, k) for k in fields if hasattr(user, k)}
```

---

## 8. Memory & Resource Management

### MUST

- Use `__slots__` for high-volume objects
- Prefer generators over lists for large sequences
- Release resources explicitly (context managers)
- Pool expensive objects (connections, threads)

### NEVER

- Create objects in hot loops unnecessarily
- Hold references to large objects beyond their lifetime
- Use string concatenation in loops
- Ignore memory in data structure choices

### WHEN creating many instances THEN use slots

```python
# ✅ Pattern: Slots for memory efficiency
@dataclass(slots=True)
class Point:
    x: float
    y: float
    z: float

# Memory: ~48 bytes per instance vs ~152 bytes without slots
```

### WHEN building strings THEN use appropriate method

```python
# ✅ Pattern: Join for multiple strings
result = "".join(parts)  # O(n)

# ❌ Anti-pattern: Concatenation in loop
result = ""
for part in parts:
    result += part  # O(n²) - creates new string each iteration
```

---

## 9. Scalability Patterns

### MUST

- Design for horizontal scaling from the start
- Externalize state to shared stores
- Use consistent hashing for distributed caching
- Plan sharding strategy for large datasets

### NEVER

- Store request state in process memory
- Assume single-instance deployment
- Ignore partition tolerance in distributed systems
- Design for peak load only (plan for 10x)

### WHEN designing for scale THEN separate compute from state

```
# ✅ Pattern: Stateless service + external state
┌─────────────────┐     ┌─────────────────┐
│   Service A     │────▶│      Redis      │
└─────────────────┘     │   (Session)     │
┌─────────────────┐     └─────────────────┘
│   Service A     │────▶┌─────────────────┐
└─────────────────┘     │   PostgreSQL    │
        ▲               │   (Durable)     │
        │               └─────────────────┘
   Load Balancer
```

### WHEN planning capacity THEN calculate bounds

| Metric | Calculate |
|--------|-----------|
| **Memory** | (object_size × expected_count) × safety_factor |
| **Connections** | max_concurrent_requests × services_per_request |
| **Throughput** | (requests_per_second × response_size) × headroom |
| **Storage growth** | daily_ingestion × retention_days × replication |

---

## 10. Quick Reference

### Performance Decision Matrix

| Scenario | Design Choice |
|----------|---------------|
| Frequent key lookup | `dict` / HashMap |
| Large dataset processing | Streaming / generators |
| Multiple independent I/O | `asyncio.gather()` |
| Expensive computation reuse | Caching with TTL |
| N+1 query pattern | JOIN or batch fetch |
| Unbounded list endpoint | Cursor pagination |
| High-volume objects | `__slots__` + frozen |
| External service calls | Timeout + retry + circuit breaker |
| Cross-service state | External store (Redis/DB) |
| Mutable shared data | Copy-on-write / immutable |

### Red Flags in Design

- [ ] No performance requirements defined
- [ ] Unbounded collection in response
- [ ] Nested loops over large datasets
- [ ] Synchronous I/O in async context
- [ ] Cache without invalidation plan
- [ ] N+1 query pattern
- [ ] No pagination on list endpoints
- [ ] In-memory state in service layer
- [ ] No timeout on external calls
- [ ] String concatenation in loops

---

*Performance is a feature. Design it in; don't bolt it on.*
