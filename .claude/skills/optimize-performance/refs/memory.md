# Memory Optimization Reference

> **Core Principle:** Don't materialize what you don't need. Stream, generate, profile.

---

## MUST / NEVER

### Data Materialization

| MUST | NEVER |
|------|-------|
| Use generators for large datasets | Materialize millions of records into lists |
| Stream data through pipelines | Load entire files into memory |
| Use generator expressions `(x for x in data)` | Use list comprehensions for unbounded data |
| Specify `chunksize` for pandas reads | Call `.read()` on large files without chunking |

### Object Memory

| MUST | NEVER |
|------|-------|
| Use `__slots__` for high-volume classes (>10k instances) | Use regular classes for millions of data objects |
| Prefer `tuple` over `list` for immutable sequences | Use `dict` when `namedtuple` suffices |
| Use `dataclass(slots=True)` for data containers | Create dynamic attributes on hot objects |

### Computation Patterns

| MUST | NEVER |
|------|-------|
| Use NumPy vectorization for numeric arrays | Write Python loops over numeric data |
| Use built-ins (`sum`, `min`, `max`, `any`, `all`) | Reimplement aggregations manually |
| Cache pure functions with `@cache` or `@lru_cache` | Recompute deterministic results |
| Localize attribute lookups in hot loops | Access `self.x.y.z` repeatedly in tight loops |

### Profiling

| MUST | NEVER |
|------|-------|
| Profile before optimizing | Guess at bottlenecks |
| Use `tracemalloc` for allocation tracking | Optimize without measurement |
| Verify improvements with re-profiling | Assume optimizations worked |

---

## WHEN / THEN

### Generators

**WHEN** processing data that:







- May exceed available memory
- Comes from I/O (files, network, database)
- Is processed once sequentially

**THEN** use generators:

```python
# ✅ THEN: Generator function
def read_large_file(path: Path) -> Iterator[Record]:
    with open(path) as f:
        for line in f:
    **     **ield parse_record(line)
****
# ✅ **EN: G**erator expression

tran**ormed** (process(item) for item in source)

```***

****

### **slots**



**WHEN** a class:

- Will have >10,000 instances
- Has fixed attributes known at definition
- Is stored in large collections

**THEN** define `__slots__`:

```python
# ✅ THEN: slots class
class Point:
    __slots__ = ("x", "y")
    def __init__(self, x: float, y: float):

        self.x, self.y = x, y


# ✅ THEN: dataclass with slots
@dataclass(slots=True)

class Coordinate:
    lat: float

    lon: float
```


### Caching


**WHEN** a function:

- Is pure (same inputs → same outputs)
- Is called repeatedly with same arguments
- Has expensive computation


**THEN** apply memoization:


```python
# ✅ THEN: Unbounded cache for pure functions
@cache

def compute_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# ✅ THEN: Bounded cache for memory-sensitive contexts
@lru_cache(maxsize=256)
def fetch_config(key: str) -> Config:

    return load_from_disk(key)

```


### Vectorization


**WHEN** performing:

- Element-wise numeric operations

- Aggregations over arrays
- Matrix/array transformations

**THEN** use NumPy operations:



```python
# ✅ THEN: Vectorized computation
result = data * 2 + 1  # Single operation, C-speed



# ✅ THEN: Vectorized conditionals
filtered = data[data > threshold]
```



### Hot Path Optimization

**WHEN** profiling reveals:

- A loop consuming >10% of execution time

- Repeated attribute/global lookups in tight loops

**THEN** localize lookups:

```python

# ✅ THEN: Localize before loop
transform = self.processor.transform  # One lookup
append = results.append               # One lookup
for item in huge_list:
    append(transform(item))

```

### Chunk Processing

**WHEN** handling:

- Files larger than available RAM
- Database result sets with millions of rows
- Network streams of unknown size

**THEN** process in chunks:

```python
# ✅ THEN: Chunked file processing
for chunk in pd.read_csv(path, chunksize=10_000):
    process_chunk(chunk)

# ✅ THEN: Batched iteration
from itertools import batched  # Python 3.13+
for batch in batched(huge_dataset, 1000):
    process_batch(batch)
```

---

## Patterns

### Stream Processing Pipeline

```python
def pipeline(source: Iterable[Raw]) -> Iterator[Result]:
    """Memory-efficient transformation pipeline."""
    validated = (validate(item) for item in source)
    filtered = (item for item in validated if item.is_valid)
    transformed = (transform(item) for item in filtered)
    return transformed

# Usage: never materializes full dataset
for result in pipeline(read_source()):
    write_output(result)
```

### Lazy Property with Caching

```python
from functools import cached_property

class ExpensiveResource:
    @cached_property
    def computed_data(self) -> Data:
        """Computed once on first access, cached thereafter."""
        return expensive_computation()
```

### Memory-Efficient Data Container

```python
from dataclasses import dataclass

@dataclass(slots=True, frozen=True)
class Event:
    """Immutable, memory-efficient event record."""
    event_id: str
    timestamp: datetime
    payload: bytes
```

### Bounded Processing with itertools

```python
from itertools import islice, chain

# Take first N without materializing
sample = list(islice(generator, 100))

# Flatten without copying
flat = chain.from_iterable(nested_iterables)
```

---

## Anti-Patterns

### ❌ Materializing Large Data

```python
# ❌ ANTI-PATTERN: OOM risk
def get_all_users() -> list[User]:
    return [User.from_row(r) for r in db.fetch_all_users()]

# ✅ FIX: Stream results
def get_all_users() -> Iterator[User]:
    for row in db.fetch_all_users():
        yield User.from_row(row)
```

### ❌ Unbounded Collection Growth

```python
# ❌ ANTI-PATTERN: Memory leak potential
cache = {}
def process(key: str) -> Result:
    if key not in cache:
        cache[key] = expensive_compute(key)  # Grows forever
    return cache[key]

# ✅ FIX: Bounded cache
@lru_cache(maxsize=1000)
def process(key: str) -> Result:
    return expensive_compute(key)
```

### ❌ Repeated Attribute Lookup in Loops

```python
# ❌ ANTI-PATTERN: 3 lookups per iteration
for item in items:
    self.stats.counter.increment(item.value)

# ✅ FIX: Localize
increment = self.stats.counter.increment
for item in items:
    increment(item.value)
```

### ❌ List Where Tuple Suffices


```python
# ❌ ANTI-PATTERN: Mutable container for immutable data
def get_coordinates() -> list[list[float]]:
    return [[lat, lon] for lat, lon in source]

# ✅ FIX: Tuples for immutable pairs

def get_coordinates() -> list[tuple[float, float]]:
    return [(lat, lon) for lat, lon in source]
```

### ❌ Manual Aggregation


```python
# ❌ ANTI-PATTERN: Slow Python loop
total = 0
for x in values:
    total += x


# ✅ FIX: C-optimized built-in
total = sum(values)
```

---


## Data Structure Memory Costs

| Structure | Base Overhead | Per-Item Cost | Best For |
|-----------|---------------|---------------|----------|
| `list` | 56 bytes | 8 bytes | Dynamic, ordered sequences |
| `tuple` | 40 bytes | 8 bytes | Immutable, small sequences |

| `dict` | 232 bytes | 24 bytes | Key-value lookup |
| `set` | 216 bytes | 8 bytes | Membership testing |
| Regular class | ~100+ bytes | — | Stateful objects |
| `__slots__` class | ~40 bytes | — | High-volume data objects |

**Decision Guide:**

- Few instances → Use regular classes for flexibility
- Many instances (>10k) → Use `__slots__` or `dataclass(slots=True)`
- Immutable data → Prefer `tuple`, `frozenset`, `frozen=True`
- Lookup-heavy → Use `dict` or `set`

---

## Profiling Commands

### Memory Allocation Tracking

```python
import tracemalloc

tracemalloc.start()
# ... code to profile ...
snapshot = tracemalloc.take_snapshot()
for stat in snapshot.statistics("lineno")[:10]:
    print(stat)
```

### Line-by-Line Memory

```python
# Requires: pip install memory_profiler
from memory_profiler import profile


@profile
def memory_intensive():
    data = [x**2 for x in range(1_000_000)]
    return sum(data)

```

### Quick Size Check



```python
import sys
obj = create_object()

print(f"Size: {sys.getsizeof(obj)} bytes")
```



---

## itertools Quick Reference


| Function | Purpose | Memory Benefit |
|----------|---------|----------------|
| `chain.from_iterable()` | Flatten nested iterables | No intermediate list |


| `islice(iterable, n)` | Take first N items | No full materialization |
| `batched(iterable, n)` | Chunk into batches | Controlled memory |
| `compress(data, selectors)` | Filter by boolean mask | Lazy evaluation |
| `filterfalse(pred, iterable)` | Inverse filter | Lazy evaluation |


---



## Cache Selection Guide

| Scenario | Decorator | Reason |
|----------|-----------|--------|

| Pure function, unlimited calls | `@cache` | Unbounded, simple |
| Memory-sensitive, many keys | `@lru_cache(maxsize=N)` | Evicts oldest |
| Expensive property, computed once | `@cached_property` | Per-instance cache |


| Needs manual invalidation | `@lru_cache` + `.cache_clear()` | Control lifecycle |

---


## Chain Triggers

**Invoke `optimize/performance/cpu`** when:


- Algorithmic complexity needs improvement
- CPU profiling shows hot spots

**Invoke `observe/metrics`** when:

- Adding memory metrics for production monitoring

**Invoke `test/unit`** when:

- Verifying optimization doesn't break behavior

---

## Quality Gates

Before completing memory optimization:

- [ ] Profiled before optimization (baseline established)
- [ ] No unbounded caches introduced
- [ ] Generators used for large data pipelines
- [ ] `__slots__` considered for high-volume classes
- [ ] Profiled after optimization (improvement verified)
