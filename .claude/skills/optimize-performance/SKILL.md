---
name: optimize-performance
version: 1.0.0
description: |
  Profile Python code and apply targeted optimizations for CPU, memory, I/O, and async bottlenecks.
  Use when optimizing performance, improving speed, reducing memory usage, fixing slow code,
  profiling bottlenecks, or after implementing features that handle large data or high load.
  Relevant for Python backend services, data pipelines, async applications, database-heavy code.
---

# Performance Optimization

> **Core Principle:** Profile before optimizing. Measure after optimizing. Never guess.

## Quick Reference

| Aspect | Details |
|--------|---------|
| **Invokes** | `test/unit` (verify behavior unchanged) |
| **Invoked By** | `implement/python`, `implement/api`, `implement/data` |
| **Key Tools** | Bash(cProfile), Bash(py-spy), Read, Edit |

---

## Core Workflow

1. **Profile**: Measure current performance to identify actual bottlenecks
2. **Classify**: Determine bottleneck type (CPU, Memory, I/O, Async)
3. **Reference**: Load the appropriate ref file for detailed patterns
4. **Optimize**: Apply targeted fixes from the referenced guide
5. **Verify**: Re-profile to confirm improvement; run tests to ensure correctness
6. **Chain**: Invoke `test/unit` if behavior-critical changes were made

---

## Bottleneck Classification

```
Performance Issue Detected
    │
    ├─► High CPU time in profiler?
    │       └──► Load: refs/cpu.md
    │
    ├─► Memory growing / OOM errors?
    │       └──► Load: refs/memory.md
    │
    ├─► Slow external calls / N+1 queries?
    │       └──► Load: refs/io.md
    │
    └─► Async blocking / concurrency issues?
            └──► Load: refs/async.md
```

---

## Quick Profiling Commands

### CPU Profiling







```bash
# Function-level profiling
python -m cProfile -s cumulative script.py 2>&1 | head -30

# Live sampling (attach to running process)
py-spy top --pid $PID



# Flame graph generation

py-spy record -o profile.svg -- python script.py

```




### Memory Profiling


```bash

# Track allocations
python -c "import tracemalloc; tracemalloc.start(); exec(open('script.py').read()); print(tracemalloc.take_snapshot().statistics('lineno')[:10])"


# Line-by-line memory (requires @profile decorator)

python -m memory_profiler script.py
```


### Timing

```bash
# Quick benchmark
python -m timeit -s "from module import func" "func()"
```

---


## Bottleneck Signatures


| Symptom | Likely Cause | Reference |
|---------|--------------|-----------|
| Single core at 100%, othes ile | CPU-bound algorithm | `refs/cpu.md` |


| Memory grows unbounded | Materializing large data | `refs/memory.md` |
| Low CPU, long wall-clock time | I/O blocking | `refs/io.md` |
| Queries in loops, N+1 pattern| Unbatched I/O | `refs/io.md` |


| Event loop blocked | Syn I/O in async context | `refs/async.md` |

| Resource exhaustion under load | Unbounded concurrency | `refs/async.md` |
| GC pauses, high allocatio rae | Object churn | `refs/memory.md` |




---




## Reference Selection Guide



### Load `refs/cpu.md` When


- Profiler shows hot functions consuming >10% CPU time

- Nested loops over large datasets

- Repeated computations with same inputs

- Numerical processing without NumPy
- Algorithm complexity conerns (O(n²) patterns)




### Load `refs/memory.md` When

- OOM errors or high memory warnings
- Processing files larger han available RAM


- Creating millions of object

- Unbounded caches or growing collections

- Need to optimize object memory footprint

### Load `refs/io.md` When


- Database queries in loops (+1)


- No connection pooling

- Missing pagination on large result sets
- No retry/timeout on external calls
- Sequential HTTP requests that could parallelize


### Load `refs/async.md` When


- Using `asyncio` and seeing bloced event loop

- `requests` or `open()` in async functions
- Unbounded `gather()` causing resource exhaustion
- Race conditions across await points

- Producer-consumer backpressure issues

---



## Optimization Priority Matrix

| Impact | Effort | Action |

|--------|--------|--------|
| High | Low | **Do immediately** (algorithm fix, add cache) |
| High | High | Plan for next iteration |

| Low | Low | Do if time permits

| Low | High | Skip unless critical path |


**Typical impact ranking:**

1. Algorithm complexity (O(n²) → O(n log n))
2. I/O batching (N+1 → single query)

3. Caching (eliminate redundant computation)

4. Async/concurrency (parallelizeI/O)

5. Memory streaming (generators)

6. Micro-optimizations (last resort)

---


## Anti-Pattern Quick Reference




### ❌ Never Do

- Optimize without profiling evidence


- Guess at bottlenecks
- Micro-optimize cold paths
- Sacrifice readability in non-hot code
- Skip verification after changes




### ✅ Always Do


- Profile to find actual bottlenek
- Measure before and after
- Verify behavior with tests


- Document performance-critical code
- Consider maintainability trade-offs

---




## Skill Chaining


### Invoke Downstream Skills When

| Condition | Invoke | Handoff Context |


|-----------|--------|-----------------|
| Optimization changes behavior | `test/unit` | Functions modified, expected behavior |
| Adding observability for perf | `observe/metrics` | Key operations to instrument |
| Refactoring for performance | `refactor` | Code structure changes needed |




### Chaining Syntax


When delegating to a reference:

```markdown


**Loading Reference:** `refs/cpu.md`
**Reason:** Profiler shows 45% time in `process_items()` loop
**Focus Area:** Algorithm complexity and loop optimization
```




---


## Complete Optimization Checklist

Before starting:


- [ ] Baseline metrics captured (time, memory, throughput)
- [ ] Profiler output analyzed
- [ ] Bottleneck type classified



After optimizing:

- [ ] Re-profiled to verify improvement
- [ ] Tests pass (behavior unchanged)

- [ ] No new anti-patterns introduced
- [ ] Performance-critical sections documented

---


## Common Patterns by Domain

### Data Pipeline


→ Primary: `refs/memory.md` (streaming, generators)
→ Secondary: `refs/io.md` (batching, connection pools)

### API Service

→ Primary: `refs/io.md` (N+1, connection pools, caching)
→ Secondary: `refs/async.md` (concurrency, timeouts)

### Background Worker

→ Primary: `refs/async.md` (bounded concurrency, backpressure)
→ Secondary: `refs/cpu.md` (if compute-heavy)

### Numerical/ML

→ Primary: `refs/cpu.md` (vectorization, algorithm)
→ Secondary: `refs/memory.md` (large array handling)

---

## Deep References

Load these based on bottleneck classification:

| Reference | Focus | Key Patterns |
|-----------|-------|--------------|
| [cpu.md](refs/cpu.md) | Computation | Algorithm, caching, vectorization, multiprocessing |
| [memory.md](refs/memory.md) | Allocation | Generators, `__slots__`, streaming, profiling |
| [io.md](refs/io.md) | External calls | Batching, pooling, pagination, resilience |
| [async.md](refs/async.md) | Concurrency | Semaphores, TaskGroup, blocking I/O, cancellation |

---

## Quality Gates

Before completing performance optimization:

- [ ] Profiled with appropriate tool for bottleneck type
- [ ] Root cause identified (not just symptom)
- [ ] Optimization targets hot path (>10% of time/resources)
- [ ] Applied patterns from correct reference file
- [ ] Improvement verified with re-profiling
- [ ] Behavior verified with existing tests
- [ ] Trade-offs documented if readability sacrificed
