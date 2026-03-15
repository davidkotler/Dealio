# Async Operations & Concurrency Reference

> **Core Principle:** Concurrency is always bounded. Unbounded fan-out kills systems.

---

## Quick Decision Matrix

| Scenario | Solution |
|----------|----------|
| Multiple concurrent I/O calls | `TaskGroup` + `Semaphore` |
| Blocking I/O in async context | `asyncio.to_thread()` |
| CPU-bound work in async | `asyncio.to_thread()` |
| Shared mutable state | `asyncio.Lock()` |
| Waiting for condition | `asyncio.Event()` |
| Producer-consumer pattern | `asyncio.Queue(maxsize=N)` |
| Streaming large datasets | `AsyncIterator` (yield) |
| Operation must complete | `asyncio.shield()` |

---

## MUST

1. **Bound all concurrent operations** with semaphores—define `MAX_CONCURRENT` explicitly
2. **Use `TaskGroup`** for parallel coroutines—provides proper exception propagation
3. **Offload blocking I/O** to thread pool via `asyncio.to_thread()`
4. **Re-raise `CancelledError`** after cleanup—never swallow it
5. **Use `asyncio.Lock()`** for shared mutable state across await points
6. **Define timeouts** for all network operations using `asyncio.timeout()`
7. **Use bounded queues** (`maxsize=N`) for backpressure in producer-consumer
8. **Use `asyncio.run()`** as single entry point—never manage event loops manually
9. **Stream with async generators** when processing unbounded or large sequences
10. **Use `asyncio.Event()`** for signaling—not polling loops

---

## NEVER

1. **Never use unbounded `gather()`** without semaphore—causes resource exhaustion
2. **Never block the event loop** with sync I/O (`requests`, `open()`, `Path.read_text()`)
3. **Never catch `CancelledError` without re-raising**—breaks cancellation propagation
4. **Never rely on GIL** across await points—race conditions occur at yield points
5. **Never use `wait_for()`**—prefer `asyncio.timeout()` context manager (3.11+)
6. **Never poll with `sleep()` loops**—use `Event` or `Queue` instead
7. **Never call `asyncio.run()` inside async functions**—causes RuntimeError
8. **Never manage event loops manually**—`get_event_loop()` / `run_until_complete()` are legacy
9. **Never collect async iterator results into list** when streaming is possible
10. **Never create unbounded queues** for production workloads—no backpressure

---

## WHEN / THEN

### Concurrency Control

**WHEN** fetching multiple URLs **THEN** bound with semaphore:

```python
MAX_CONCURRENT = 50
semaphore = asyncio.Semaphore(MAX_CONCURRENT)

async def fetch_bounded(url: str) -> Response:
    async with semaphore:
        return await client.get(url)

async def fetch_all(urls: list[str]) -> list[Response]:
    async with asyncio.TaskGroup() as tg:
        tasks = [tg.create_task(fetch_bounded(url)) for url in urls]
    return [t.result() for t in tasks]
```

---

### Blocking Operations

**WHEN** performing file I/O in async context **THEN** offload to thread:

```python
async def read_file(path: Path) -> str:
    return await asyncio.to_thread(path.read_text)
```

**WHEN** performing CPU-bound work **THEN** offload to thread:

```python
async def compute_hash(data: bytes) -> str:
    return await asyncio.to_thread(hashlib.sha256(data).hexdigest)
```

---

### Timeouts

**WHEN** calling external services **THEN** use context manager timeout:

```python
async with asyncio.timeout(5.0):
    result = await external_service.call()
```

---

### Cancellation

**WHEN** handling cancellation **THEN** re-raise after cleanup:

```python
async def worker():
    try:
        await long_operation()
    except asyncio.CancelledError:
        logger.info("Cancelled, cleaning up")
        await cleanup()
        raise  # MUST re-raise
    except Exception:
        logger.error("Operation failed")
        raise
```

**WHEN** operation must complete despite cancellation **THEN** shield it:

```python
async def critical_save(data: Data) -> None:
    await asyncio.shield(db.commit(data))
```

---

### Synchronization

**WHEN** mutating shared state across await points **THEN** use Lock:

```python
class Counter:
    def __init__(self):
        self.value = 0
        self._lock = asyncio.Lock()

    async def increment(self):
        async with self._lock:
            self.value += 1
```

**WHEN** waiting for a condition **THEN** use Event:

```python
ready_event = asyncio.Event()

async def wait_for_ready():
    await ready_event.wait()

async def signal_ready():
    ready_event.set()
```

---

### Streaming

**WHEN** processing large/unbounded sequences **THEN** use async generators:

```python
from collections.abc import AsyncIterator

async def fetch_pages(query: str) -> AsyncIterator[Page]:
    cursor = None
    while True:
        batch, cursor = await fetch_batch(query, cursor)
        for page in batch:
            yield page
        if cursor is None:
            break
```

---

### Producer-Consumer

**WHEN** decoupling producers from consumers **THEN** use bounded queue:

```python
queue: asyncio.Queue[Task] = asyncio.Queue(maxsize=100)

async def producer(items: list[Item]):
    for item in items:
        await queue.put(item)  # Blocks when full (backpressure)

async def consumer():
    while True:
        item = await queue.get()
        await process(item)
        queue.task_done()
```

---

### Application Entry Point

**WHEN** starting async application **THEN** use single `asyncio.run()`:

```python
async def main():
    async with asyncio.TaskGroup() as tg:
        tg.create_task(service_a())
        tg.create_task(service_b())

if __name__ == "__main__":
    asyncio.run(main())
```

---

## Patterns

### ✅ Bounded Parallel Fetch

```python
async def fetch_all_bounded(urls: list[str], max_concurrent: int = 50) -> list[Response]:
    semaphore = asyncio.Semaphore(max_concurrent)

    async def fetch_one(url: str) -> Response:
        async with semaphore:
            async with httpx.AsyncClient(timeout=10.0) as client:
                return await client.get(url)

    async with asyncio.TaskGroup() as tg:
        tasks = [tg.create_task(fetch_one(url)) for url in urls]
    return [t.result() for t in tasks]
```

### ✅ Async Context Manager

```python
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

@asynccontextmanager
async def db_session() -> AsyncIterator[Session]:
    session = await create_session()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()
```

### ✅ Graceful Shutdown

```python
async def main():
    async with asyncio.TaskGroup() as tg:
        task = tg.create_task(worker())

        try:
            await shutdown_signal.wait()
        except asyncio.CancelledError:
            task.cancel()
            raise
```

---

## Anti-Patterns

### ❌ Unbounded Concurrency

```python
# WRONG: 10,000 URLs = 10,000 concurrent connections
async def fetch_all(urls: list[str]) -> list[Response]:
    return await asyncio.gather(*[fetch(url) for url in urls])
```

### ❌ Blocking Event Loop

```python
# WRONG: Blocks entire event loop
async def read_file(path: Path) -> str:
    return path.read_text()

# WRONG: Sync HTTP in async context
async def fetch_data(url: str) -> dict:
    return requests.get(url).json()
```

### ❌ Swallowing CancelledError

```python
# WRONG: Breaks cancellation propagation
async def worker():
    try:
        await operation()
    except Exception:  # Catches CancelledError!
        logger.error("Failed")
```

### ❌ Polling Loop

```python
# WRONG: Wasteful CPU cycles
async def wait_for_ready():
    while not is_ready:
        await asyncio.sleep(0.1)
```

### ❌ GIL Reliance Across Await

```python
# WRONG: Race condition at await point
async def increment(self):
    current = self.value
    await asyncio.sleep(0)  # Other coroutines can modify!
    self.value = current + 1
```

### ❌ Manual Event Loop

```python
# WRONG: Legacy pattern, error-prone
loop = asyncio.get_event_loop()
loop.run_until_complete(main())
```

---

## Debugging

Enable debug mode to detect issues:

```python
asyncio.run(main(), debug=True)
```

Or via environment:
```bash
PYTHONASYNCIODEBUG=1 python app.py
```

**Debug mode detects:**







- Coroutines never awaited
- Callbacks taking too long
- Unclosed transports/resources

---

## Summary Table

| Anti-Pattern | Fix |
|--------------|-----|
| Unbounded concurrency | `Semaphore(MAX_CONCURRENT)` |
| Blocking in async | `asyncio.to_thread()` |
| `gather()` without error handling | `TaskGroup` |
| Polling loops | `Event` / `Queue` |
| Swallowing `CancelledError` | Re-raise after cleanup |
| Manual event loop | `asyncio.run()` |
| GIL reliance across await | `asyncio.Lock()` |
| `wait_for()` | `asyncio.timeout()` |
| Collecting async iterators | `yield` streaming |
| Unbounded queues | `Queue(maxsize=N)` |
