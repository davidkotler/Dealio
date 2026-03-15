# FastAPI Performance Patterns

> Reference for pagination, filtering, caching, and streaming in FastAPI endpoints.

---

## 1. Pagination

### Must / Never

**MUST:**







- Include `total`, `page`/`cursor`, `has_more` metadata in paginated responses

- Set a maximum page size limit (e.g., `le=100`) to prevent resource exhaustion

- Use indexed columns for cursor fields (`id`, `created_at`)

- Return consistent sort order — add secondary sort on unique field (e.g., `ORDER BY created_at, id`)

- Use `Annotated[T, Query()]` with `Field()` constraints for pagination params



**NEVER:**

- Use offset pagination for datasets > 100k rows — O(n) skip degrades performance
- Expose raw database primary keys as cursors — encode/obfuscate them
- Allow unbounded queries — always enforce `limit` with a default
- Return total count on cursor-paginated endpoints — it requires full table scan
- Mix pagination strategies in the same endpoint

---

### When → Then

| When | Then |
|------|------|
| Dataset < 10k rows, need page jumping | Use offset pagination (`skip`/`limit`) |
| Dataset > 100k rows or real-time data | Use cursor pagination (`after`/`before`) |
| Need total count display | Use offset with `SELECT COUNT(*)` (cache if expensive) |
| Infinite scroll UI | Use cursor pagination with `has_more` flag |
| Consistent results during pagination | Use cursor on immutable field (`id`, `created_at`) |
| Bidirectional navigation needed | Return both `next_cursor` and `prev_cursor` |

---

### Patterns

#### ✅ Offset Pagination (Small Datasets)

```python
from typing import Annotated
from fastapi import APIRouter, Query, Depends
from pydantic import BaseModel, Field

class PaginationParams(BaseModel):
    """Reusable pagination parameters."""
    model_config = {"extra": "forbid"}

    skip: int = Field(0, ge=0, description="Records to skip")
    limit: int = Field(20, ge=1, le=100, description="Records per page")

PaginationDep = Annotated[PaginationParams, Query()]

@router.get("/users", response_model=PaginatedResponse[UserResponse])
async def list_users(
    *,
    pagination: PaginationDep,
    service: UserServiceDep,
) -> PaginatedResponse[UserResponse]:
    users, total = await service.list(skip=pagination.skip, limit=pagination.limit)
    return PaginatedResponse(
        items=users,
        total=total,
        skip=pagination.skip,
        limit=pagination.limit,
        has_more=(pagination.skip + len(users)) < total,
    )
```

#### ✅ Cursor Pagination (Large Datasets)

```python
from typing import Annotated
from pydantic import BaseModel, Field
from fastapi import Query
import base64

class CursorParams(BaseModel):
    """Cursor-based pagination parameters."""
    cursor: str | None = Field(None, description="Opaque cursor from previous response")
    limit: int = Field(20, ge=1, le=100)

CursorDep = Annotated[CursorParams, Query()]

def encode_cursor(id: int, created_at: datetime) -> str:
    """Encode cursor as opaque string."""
    return base64.urlsafe_b64encode(f"{id}:{created_at.isoformat()}".encode()).decode()

def decode_cursor(cursor: str) -> tuple[int, datetime]:
    """Decode cursor to id and timestamp."""
    decoded = base64.urlsafe_b64decode(cursor.encode()).decode()
    id_str, ts_str = decoded.split(":", 1)
    return int(id_str), datetime.fromisoformat(ts_str)

@router.get("/events", response_model=CursorPage[EventResponse])
async def list_events(*, params: CursorDep, db: SessionDep) -> CursorPage[EventResponse]:
    query = select(Event).order_by(Event.created_at.desc(), Event.id.desc())

    if params.cursor:
        last_id, last_ts = decode_cursor(params.cursor)
        query = query.where(
            or_(
                Event.created_at < last_ts,
                and_(Event.created_at == last_ts, Event.id < last_id),
            )
        )

    # Fetch limit + 1 to detect has_more
    results = (await db.execute(query.limit(params.limit + 1))).scalars().all()
    has_more = len(results) > params.limit
    items = results[: params.limit]

    next_cursor = None
    if has_more and items:
        last = items[-1]
        next_cursor = encode_cursor(last.id, last.created_at)

    return CursorPage(items=items, next_cursor=next_cursor, has_more=has_more)
```

#### ❌ Anti-Pattern: Large Offset

```python
# WRONG: O(n) performance — DB scans and discards skip rows
@router.get("/logs")

async def list_logs(skip: int = 0, limit: int = 100, db: SessionDep):
    # At skip=1_000_000, this scans 1M rows before returning 100

    return await db.execute(select(Log).offset(skip).limit(limit))
```



---



## 2. Filtering



### Must / Never



**MUST:**

- Validate filter field names against allowlist — prevent SQL injection via dynamic columns

- Use Pydantic models with `model_config = {"extra": "forbid"}` for filter params
- Index frequently filtered columns in the database
- Use `Literal` types to constrain allowed sort/filter fields

- Combine filters with pagination in a single dependency

**NEVER:**

- Build SQL with string interpolation from user input
- Allow arbitrary field filtering without allowlist validation
- Apply filters after fetching all data — filter in the query
- Expose internal field names — map to public API names
- Allow filtering on unindexed columns for large tables

---

### When → Then

| When | Then |
|------|------|
| Simple equality filters | Use query parameters with type hints |
| Multiple filter operators needed | Use Pydantic model with `Query()` |
| Complex filter expressions | Consider `fastapi-filter` or custom DSL |
| Full-text search | Use database FTS (PostgreSQL `tsvector`) or search service |
| Filter + sort + paginate | Combine in single Pydantic model dependency |
| Range queries (dates, prices) | Use explicit `_min`/`_max` suffixed params |

---

### Patterns

#### ✅ Type-Safe Filter Model

```python
from typing import Annotated, Literal
from pydantic import BaseModel, Field
from fastapi import Query
from datetime import date

class UserFilters(BaseModel):
    """User list filters with validation."""
    model_config = {"extra": "forbid"}

    status: Literal["active", "inactive", "pending"] | None = None
    role: Literal["admin", "user", "guest"] | None = None
    created_after: date | None = Field(None, description="Filter by creation date")
    created_before: date | None = None
    search: str | None = Field(None, max_length=100, description="Search name/email")
    order_by: Literal["created_at", "name", "email"] = "created_at"
    order_dir: Literal["asc", "desc"] = "desc"

FiltersDep = Annotated[UserFilters, Query()]

@router.get("/users")
async def list_users(*, filters: FiltersDep, pagination: PaginationDep, db: SessionDep):
    query = select(User)

    if filters.status:
        query = query.where(User.status == filters.status)
    if filters.role:
        query = query.where(User.role == filters.role)
    if filters.created_after:
        query = query.where(User.created_at >= filters.created_after)
    if filters.created_before:
        query = query.where(User.created_at <= filters.created_before)
    if filters.search:
        pattern = f"%{filters.search}%"
        query = query.where(or_(User.name.ilike(pattern), User.email.ilike(pattern)))

    # Apply ordering
    order_col = getattr(User, filters.order_by)
    order_expr = order_col.desc() if filters.order_dir == "desc" else order_col.asc()
    query = query.order_by(order_expr)

    return await paginate_query(db, query, pagination)
```

#### ✅ Reusable Filter Dependency

```python
from abc import ABC, abstractmethod
from sqlalchemy import Select

class BaseFilter(BaseModel, ABC):
    """Base class for filter models."""
    model_config = {"extra": "forbid"}

    @abstractmethod
    def apply(self, query: Select) -> Select:
        """Apply filters to query."""
        ...

class OrderFilter(BaseModel):
    """Reusable ordering filter."""
    order_by: str = "created_at"
    order_dir: Literal["asc", "desc"] = "desc"

    def apply(self, query: Select, model: type, allowed: set[str]) -> Select:
        if self.order_by not in allowed:
            raise ValueError(f"Invalid order_by: {self.order_by}")
        col = getattr(model, self.order_by)
        return query.order_by(col.desc() if self.order_dir == "desc" else col.asc())

```

#### ❌ Anti-Pattern: Dynamic Column Access


```python
# WRONG: SQL injection vulnerability
@router.get("/items")

async def list_items(

    filter_field: str,  # User controls column name!
    filter_value: str,
    db: SessionDep,

):

    # DANGEROUS: Arbitrary column access
    query = select(Item).where(getattr(Item, filter_field) == filter_value)
    return await db.execute(query)

```


---


## 3. Caching


### Must / Never


**MUST:**

- Use async Redis client (`redis.asyncio.Redis`) in async endpoints
- Set TTL on all cache entries — prevent unbounded memory growth
- Include cache key version prefix for invalidation (`v1:users:{id}`)

- Use `@lru_cache` on `get_settings()` — parse config once
- Implement cache-aside pattern: check cache → miss → fetch → store → return
- Add `X-Cache: HIT/MISS` header for observability

**NEVER:**

- Cache user-specific data with shared keys
- Cache responses with sensitive data (tokens, PII) without encryption
- Use `decode_responses=True` with `fastapi-cache` Redis backend
- Cache error responses or partial failures
- Rely solely on in-memory cache (`lru_cache`) in multi-process deployments
- Set infinite TTL — data staleness is inevitable

---

### When → Then

| When | Then |
|------|------|
| Single-process, pure functions | Use `@lru_cache(maxsize=N)` |
| Multi-process / distributed | Use Redis or Memcached backend |
| Expensive computation, stable data | Cache with long TTL (hours) |
| Frequently changing data | Cache with short TTL (seconds) + invalidation |
| User-specific cached data | Include user ID in cache key |
| Need conditional requests | Implement ETag + `If-None-Match` handling |
| CDN/browser caching | Set `Cache-Control` response headers |
| Cache stampede risk | Use locking or stale-while-revalidate |

---

### Patterns

#### ✅ Redis Cache-Aside Pattern

```python
from redis.asyncio import Redis
from fastapi import Depends
from typing import Annotated
import json

async def get_redis() -> AsyncGenerator[Redis, None]:
    redis = Redis.from_url("redis://localhost:6379", decode_responses=False)
    try:
        yield redis
    finally:
        await redis.aclose()

RedisDep = Annotated[Redis, Depends(get_redis)]

@router.get("/products/{product_id}", response_model=ProductResponse)
async def get_product(
    *,
    product_id: int,
    redis: RedisDep,
    service: ProductServiceDep,
    response: Response,
) -> Product:
    cache_key = f"v1:product:{product_id}"

    # Check cache
    cached = await redis.get(cache_key)
    if cached:
        response.headers["X-Cache"] = "HIT"
        return ProductResponse.model_validate_json(cached)

    # Cache miss — fetch from DB
    product = await service.get_by_id(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Store in cache with TTL
    await redis.setex(cache_key, 300, product.model_dump_json())  # 5 min TTL
    response.headers["X-Cache"] = "MISS"
    return product
```

#### ✅ HTTP Cache Headers + ETag

```python
import hashlib
from fastapi import Request, Response

def compute_etag(data: bytes) -> str:
    """Generate weak ETag from content hash."""
    return f'W/"{hashlib.sha1(data).hexdigest()[:16]}"'

@router.get("/catalog", response_model=CatalogResponse)
async def get_catalog(
    *,
    request: Request,
    response: Response,
    service: CatalogServiceDep,
) -> CatalogResponse:
    catalog = await service.get_catalog()
    content = catalog.model_dump_json().encode()
    etag = compute_etag(content)

    # Check conditional request
    if_none_match = request.headers.get("if-none-match")
    if if_none_match == etag:
        return Response(status_code=304)

    # Set cache headers
    response.headers["ETag"] = etag
    response.headers["Cache-Control"] = "public, max-age=60, stale-while-revalidate=300"
    return catalog
```

#### ✅ fastapi-cache Decorator

```python

from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from fastapi_cache.decorator import cache
from redis import asyncio as aioredis

@app.on_event("startup")

async def startup():

    redis = aioredis.from_url("redis://localhost:6379")
    FastAPICache.init(RedisBackend(redis), prefix="api-cache")

@router.get("/stats", response_model=StatsResponse)
@cache(expire=60)  # Cache for 60 seconds

async def get_stats(service: StatsServiceDep) -> StatsResponse:

    return await service.compute_stats()
```

#### ❌ Anti-Pattern: Unbounded In-Memory Cache


```python

# WRONG: Memory leak in production
_cache: dict[str, Any] = {}  # Grows forever!

@router.get("/data/{key}")
async def get_data(key: str):

    if key not in _cache:

        _cache[key] = await expensive_fetch(key)  # No TTL, no eviction
    return _cache[key]
```

---



## 4. Streaming

### Must / Never

**MUST:**

- Use `async def` generators with `StreamingResponse` for I/O-bound streaming

- Set appropriate `media_type` (`text/event-stream`, `application/x-ndjson`, etc.)
- Check `await request.is_disconnected()` in long-running streams to release resources
- Use chunked transfer encoding for unknown content length
- Add timeout protection with `async_timeout` for external data sources
- Set `X-Accel-Buffering: no` header when behind Nginx

**NEVER:**

- Load entire dataset into memory before streaming
- Use sync generators in async endpoints — blocks event loop
- Stream without client disconnect detection — leaks connections
- Forget to close resources (files, DB connections) in generators
- Use SSE for bidirectional communication — use WebSockets instead
- Stream sensitive data without authentication middleware

---

### When → Then

| When | Then |
|------|------|
| Large file download | Use `FileResponse` or chunked `StreamingResponse` |
| Real-time updates (server → client) | Use SSE with `EventSourceResponse` |
| Line-delimited JSON (logs, events) | Use NDJSON with `StreamingResponse` |
| LLM token streaming | Use SSE or chunked response |
| Bidirectional real-time | Use WebSockets instead of streaming |
| Export large dataset | Stream rows with cursor pagination internally |
| Video/audio streaming | Use `Range` header support with `FileResponse` |

---

### Patterns

#### ✅ Chunked File Streaming

```python
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pathlib import Path

CHUNK_SIZE = 64 * 1024  # 64KB chunks

async def stream_file(path: Path):
    """Stream file in chunks to minimize memory."""
    async with aiofiles.open(path, "rb") as f:
        while chunk := await f.read(CHUNK_SIZE):
            yield chunk

@router.get("/download/{file_id}")
async def download_file(file_id: str, service: FileServiceDep):
    file_path = await service.get_file_path(file_id)
    if not file_path.exists():
        raise HTTPException(status_code=404)

    return StreamingResponse(
        stream_file(file_path),
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{file_path.name}"'},
    )
```

#### ✅ Server-Sent Events (SSE)

```python
from sse_starlette import EventSourceResponse
from fastapi import Request
import asyncio

@router.get("/events/stream")
async def stream_events(request: Request, service: EventServiceDep):
    async def event_generator():
        try:
            async for event in service.subscribe():
                # Check if client disconnected
                if await request.is_disconnected():
                    break
                yield {
                    "event": event.type,
                    "id": str(event.id),
                    "data": event.payload.model_dump_json(),
                }
        finally:
            await service.unsubscribe()

    return EventSourceResponse(
        event_generator(),
        ping=15,  # Keep-alive ping every 15s
        headers={"X-Accel-Buffering": "no"},  # Disable Nginx buffering
    )
```

#### ✅ NDJSON Streaming (Large Dataset Export)

```python
from fastapi.responses import StreamingResponse
import json

async def stream_ndjson(db: AsyncSession, query: Select):
    """Stream query results as newline-delimited JSON."""
    async with db.stream(query) as result:
        async for row in result:
            yield json.dumps(row._asdict()) + "\n"

@router.get("/export/orders")
async def export_orders(
    *,
    filters: OrderFiltersDep,
    db: SessionDep,
):
    query = select(Order).where(/* apply filters */).order_by(Order.id)

    return StreamingResponse(
        stream_ndjson(db, query),
        media_type="application/x-ndjson",
        headers={
            "Content-Disposition": 'attachment; filename="orders.ndjson"',
            "X-Accel-Buffering": "no",
        },
    )
```

#### ✅ LLM Token Streaming with Timeout

```python
import async_timeout
from fastapi.responses import StreamingResponse

STREAM_TIMEOUT = 60  # seconds

async def stream_llm_response(prompt: str, client: LLMClient):
    """Stream LLM tokens with timeout protection."""
    async with async_timeout.timeout(STREAM_TIMEOUT):
        try:
            async for token in client.stream_completion(prompt):
                yield f"data: {json.dumps({'token': token})}\n\n"
            yield "data: [DONE]\n\n"
        except asyncio.TimeoutError:
            yield f"data: {json.dumps({'error': 'timeout'})}\n\n"

@router.post("/chat/stream")
async def chat_stream(body: ChatRequest, client: LLMClientDep):
    return StreamingResponse(
        stream_llm_response(body.prompt, client),
        media_type="text/event-stream",
    )
```

#### ❌ Anti-Pattern: Loading All Data Before Streaming

```python
# WRONG: Defeats purpose of streaming — loads everything into memory
@router.get("/export")
async def export_all(db: SessionDep):
    # Loads ALL rows into memory first!
    all_rows = await db.execute(select(BigTable))
    data = all_rows.scalars().all()

    async def generate():
        for row in data:  # Already in memory — not streaming!
            yield row.model_dump_json() + "\n"

    return StreamingResponse(generate(), media_type="application/x-ndjson")
```

---

## 5. Quick Decision Matrix

| Scenario | Solution |
|----------|----------|
| List endpoint, < 10k items | Offset pagination + total count |
| List endpoint, > 100k items | Cursor pagination, no total count |
| Filter by enum field | `Literal` type in Pydantic model |
| Filter by date range | `_after`/`_before` suffixed params |
| Repeated expensive query | Redis cache with TTL |
| Static/slow-changing response | ETag + Cache-Control headers |
| Settings/config | `@lru_cache` on getter function |
| Large file download | `StreamingResponse` with chunked reads |
| Real-time server push | SSE with `EventSourceResponse` |
| LLM response streaming | SSE with timeout + disconnect check |
| Export large dataset | NDJSON streaming with DB cursor |

---

## 6. Performance Checklist

Before deploying endpoints with these patterns:

- [ ] Pagination: Maximum limit enforced, default limit set
- [ ] Pagination: Cursor pagination uses indexed columns
- [ ] Filtering: All filter fields validated against allowlist
- [ ] Filtering: Filtered columns are indexed in database
- [ ] Caching: TTL set on all cache entries
- [ ] Caching: Cache keys include version prefix for invalidation
- [ ] Caching: `X-Cache` header added for debugging
- [ ] Streaming: Client disconnect checked in generators
- [ ] Streaming: Resources properly closed in `finally` blocks
- [ ] Streaming: Timeout protection for external data sources
- [ ] Headers: `X-Accel-Buffering: no` for streaming behind Nginx
