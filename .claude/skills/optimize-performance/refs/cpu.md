# CPU Optimization Reference

> **Loaded by:** `optimize/performance/SKILL.md`  
> **Trigger:** CPU-bound bottlenecks identified via profiling

---

## Golden Rules

1. **Profile before optimizing** — Intuition about bottlenecks is usually wrong
2. **Algorithm first** — O(n²) → O(n log n) beats any micro-optimization
3. **Measure after optimizing** — Verify improvements with benchmarks
4. **Readability in cold paths** — Only sacrifice clarity in proven hot paths

---

## Quick Decision Matrix

| When | Then |
|------|------|
| Suspect performance issue | Profile with `cProfile` or `py-spy` first |
| Hot loop identified | Check algorithm complexity before micro-optimizing |
| Membership testing in loop | Convert `list` to `set` for O(1) lookup |
| Building strings in loop | Use `"".join(parts)` pattern |
| Repeated function with same args | Apply `@lru_cache` or `@cache` |
| Processing numeric arrays | Use NumPy vectorized operations |
| CPU-bound parallelizable work | Use `ProcessPoolExecutor` |
| Need line-level profiling | Use `py-spy` or `line_profiler` |
| Regex in hot path | Pre-compile with `re.compile()` |
| Many small object instances | Consider `__slots__` |

---

## Must / Never Rules

### Profiling

**MUST:**








- Profile to identify actual bottleneck before any optimization

- Use `time.perf_counter()` or `timeit` for measurements

- Establish baseline benchmarks before optimizing

- Verify improvements with benchmarks after optimizing




**NEVER:**


- Optimize without profiling evidence

- Use `time.time()` for performance measurements

- Assume which code path is slow



---



### Algorithm & Data Structures




**MUST:**


- Check algorithm complexity before micro-optimizing


- Use `set`/`dict` for O(1) membership testing
- Use `collections.deque` for queue operations

- Use `heapq` for priority queue operations


- Use `Counter` for counting occurrences



**NEVER:**


- Use `list` for membership testing in loops

- Use `list.pop(0)` — it's O(n)


- Use `+` to build lists incrementally — use `.append()` or `.extend()`

- Nest loops over same data without considering hash-based alternatives


---





### Loops & Iteration



**MUST:**



- Cache attribute lookups in local variables for hot loops


- Use `"".join(parts)` for string building

- Hoist loop-invariant computations outside loops

- Prefer built-ins (`sum`, `any`, `all`, `map`, `filter`) — they're C-optimized




**NEVER:**


- Concatenate strings with `+=` in loops

- Call `len()` repeatedly on unchanging collections in loop conditions

- Perform repeated attribute lookups in tight loops




---


### Caching



**MUST:**



- Use `@lru_cache` or `@cache` for pure functions with repeated args
- Ensure cached functions are pure (same inputs → same outputs)
- Create hashable cache keys for unhashable arguments



**NEVER:**

- Cache functions with side effects

- Cache without considering memory bounds for unbounded inputs

- Use mutable default arguments as cache keys

---



### Object Creation

**MUST:**

- Use `__slots__` for classes with many instances (>10,000)

- Reuse objects in tight loops when possible
- Consider object pools for expensive-to-create objects


**NEVER:**

- Use `__slots__` when dynamic attributes are needed
- Create new collections in every loop iteration if avoidable

---


### Multiprocessing

**MUST:**

- Use `if __name__ == '__main__':` guard with multiprocessing
- Ensure all objects passed between processes are picklable
- Size worker pools to CPU count (or CPU count - 1)
- Use chunking to amortize IPC overhead
- Use context manager or `pool.close()` + `pool.join()` for cleanup

**NEVER:**

- Share file handles or sockets between processes
- Use `fork` if parent process uses threads — causes deadlocks
- Create new pool for each task — pool creation overhead is significant
- Return large objects through queue — write to storage, return reference

---

## Patterns & Anti-Patterns

### Algorithm Complexity

```python
# ❌ O(n²) — linear search in loop
def find_duplicates_slow(items: list[str]) -> list[str]:
    duplicates = []
    for i, item in enumerate(items):
        if item in items[i + 1:]:  # O(n) search each iteration
            duplicates.append(item)
    return duplicates

# ✅ O(n) — hash-based counting
def find_duplicates_fast(items: list[str]) -> list[str]:
    from collections import Counter
    counts = Counter(items)
    return [item for item, count in counts.items() if count > 1]
```

---

### Membership Testing

```python
# ❌ O(n) membership test
if user_id in user_list:  # Scans entire list
    ...

# ✅ O(1) membership test
user_set = set(user_list)  # One-time O(n) conversion
if user_id in user_set:    # O(1) lookup
    ...
```

---

### Attribute Access Caching

```python
# ❌ Repeated attribute lookup
for item in large_collection:
    self.processor.transform(item)  # Two lookups per iteration

# ✅ Cache in local variable
transform = self.processor.transform  # Single lookup
for item in large_collection:
    transform(item)
```

---

### String Building

```python
# ❌ O(n²) — repeated string concatenation
result = ""
for item in items:
    result += str(item)  # Creates new string each time

# ✅ O(n) — join pattern
result = "".join(str(item) for item in items)
```

---

### Loop-Invariant Hoisting

```python
# ❌ Recomputes on every iteration
for item in items:
    threshold = calculate_threshold(config)  # Same result each time
    if item.value > threshold:
        process(item)

# ✅ Hoist invariant computation
threshold = calculate_threshold(config)
for item in items:
    if item.value > threshold:
        process(item)
```

---

### Generators for Large Data

```python
# ❌ Materializes entire filtered list
filtered = [x for x in huge_dataset if x.is_valid]
for item in filtered:
    process(item)

# ✅ Lazy evaluation — processes one at a time
filtered = (x for x in huge_dataset if x.is_valid)
for item in filtered:
    process(item)
```

---

### Memoization

```python
from functools import lru_cache, cache

# ✅ Bounded cache for repeated computations
@lru_cache(maxsize=1024)
def expensive_computation(n: int) -> int:
    ...

# ✅ Unbounded cache (Python 3.9+)
@cache
def deterministic_transform(key: str) -> Result:
    ...
```

---

### `__slots__` for Memory and Speed

```python
# ❌ Standard class — dict per instance
class Point:
    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y

# ✅ Slots — fixed attributes, less memory, faster access
class Point:
    __slots__ = ('x', 'y')

    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y
```

---

### Built-in Performance Wins

```python
from operator import attrgetter, itemgetter

# ❌ Lambda in sort
users.sort(key=lambda u: u.created_at)

# ✅ attrgetter is faster
users.sort(key=attrgetter('created_at'))

# ❌ Lambda for tuple indexing
pairs.sort(key=lambda x: x[1])

# ✅ itemgetter is faster
pairs.sort(key=itemgetter(1))
```

---

### NumPy Vectorization

```python
import numpy as np

# ❌ Python loop — slow
def normalize_slow(values: list[float]) -> list[float]:
    total = sum(values)
    return [v / total for v in values]

# ✅ NumPy vectorized — 10-100x faster
def normalize_fast(values: np.ndarray) -> np.ndarray:
    return values / values.sum()
```

---

### Regex Pre-compilation

```python
import re

# ❌ Recompiles pattern each call
def find_emails_slow(text: str) -> list[str]:
    return re.findall(r'[\w.-]+@[\w.-]+\.\w+', text)

# ✅ Compile once, reuse
EMAIL_PATTERN = re.compile(r'[\w.-]+@[\w.-]+\.\w+')

def find_emails_fast(text: str) -> list[str]:
    return EMAIL_PATTERN.findall(text)
```

---

### Multiprocessing with Chunking

```python
from multiprocessing import Pool

# ❌ Small chunks — IPC overhead dominates
with Pool() as pool:
    results = pool.map(process, items, chunksize=1)

# ✅ Larger chunks — amortize IPC cost
with Pool() as pool:
    chunksize = max(1, len(items) // (pool._processes * 4))
    results = pool.map(process, items, chunksize=chunksize)
```

---

### Worker Initialization for Shared Data

```python
# ❌ Pass large data through queue — serialization overhead
def process_with_data(item, large_lookup_table):
    return large_lookup_table.get(item.key)

# ✅ Initialize in worker — load once per process
_lookup_table = None

def init_worker(data_path: str):
    global _lookup_table
    _lookup_table = load_lookup_table(data_path)

def process_item(item):
    return _lookup_table.get(item.key)

with Pool(initializer=init_worker, initargs=(data_path,)) as pool:
    results = pool.map(process_item, items)
```

---

## Serialization Performance

| Library | Speed | Use Case |
|---------|-------|----------|
| `orjson` | Fastest | JSON with strict types |
| `ujson` | Very fast | JSON with more flexibility |
| `msgpack` | Fast + compact | Binary serialization |
| `json` (stdlib) | Baseline | Compatibility requirement |

```python
# ✅ orjson — 2-10x faster than stdlib json
import orjson
data = orjson.loads(payload)
```

---

## Profiling Quick Reference

```bash
# cProfile to file
python -m cProfile -o profile.stats script.py

# Analyze profile
python -c "import pstats; p = pstats.Stats('profile.stats'); \
    p.sort_stats('cumulative').print_stats(30)"

# py-spy sampling (attach to running process)
py-spy record -o profile.svg --pid $PID

# py-spy top (live view)
py-spy top --pid $PID

# timeit from command line
python -m timeit "sum(range(1000))"
```

---

## Pre-Optimization Checklist

- [ ] Have baseline benchmark measurements?
- [ ] Profiled to identify actual bottleneck?
- [ ] Checked algorithm complexity first?
- [ ] Is this a hot path (called frequently)?
- [ ] Will optimization be measurably impactful?
- [ ] Is the optimization maintainable?

---

## Related References

- `async.md` — Async I/O patterns and concurrency
- `memory.md` — Memory optimization and profiling
- `io.md` — I/O batching and connection pooling
