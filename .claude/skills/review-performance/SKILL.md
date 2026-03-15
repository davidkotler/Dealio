---
name: review-performance
version: 1.0.0

description: |
  Review code for performance quality. Evaluates CPU efficiency, memory usage, I/O patterns, and async correctness.
  Use when reviewing Python implementations, validating optimization changes, or assessing scalability.
  Relevant for Python backend services, data pipelines, async applications, database-heavy code.

chains:
  invoked-by:
    - skill: implement/python
      context: "Post-implementation performance validation"
    - skill: implement/api
      context: "API handler efficiency check"
    - skill: implement/data
      context: "Data pipeline scalability review"
  invokes:
    - skill: optimize/performance
      when: "Critical or major findings detected"
    - skill: test/unit
      when: "Optimization changes behavior"
---

# Performance Review

> Validate code efficiency and scalability through systematic resource utilization analysis.

## Quick Reference

| Aspect | Details |
|--------|---------|
| **Scope** | Functions, classes, modules, async handlers, data pipelines |
| **Invoked By** | `implement/python`, `implement/api`, `implement/data`, `/review` |
| **Invokes** | `optimize/performance` (on failure), `test/unit` (after fix) |
| **Verdicts** | `PASS` · `PASS_WITH_SUGGESTIONS` · `NEEDS_WORK` · `FAIL` |

---

## Review Objective

Ensure code meets production performance requirements by identifying bottlenecks, anti-patterns, and scalability risks before they reach production.

**Key Questions:**







1. Will this code scale under expected load without resource exhaustion?
2. Are I/O operations batched and connections pooled appropriately?
3. Is async code non-blocking with bounded concurrency?
4. Are algorithms and data structures appropriate for the data size?

**Out of Scope:** Micro-optimizations in non-hot paths; third-party library performance.

---

## Core Workflow

```
SCOPE → CONTEXT → ANALYZE → CLASSIFY → VERDICT → REPORT → CHAIN
```

1. **Scope:** Target `**/*.py` excluding test files
2. **Context:** Load `rules/principles.md` + `optimize/performance/refs/*.md`
3. **Analyze:** Apply criteria by priority (P0→P3)
4. **Classify:** Assign severity per finding
5. **Verdict:** Aggregate findings into decision
6. **Report:** Output structured results
7. **Chain:** Invoke `optimize/performance` if needed

### Priority Matrix

| Priority | Category | Weight |
|----------|----------|--------|
| P0 | Resource Exhaustion (ASYNC) | Blocker |
| P1 | I/O Anti-Patterns (IO) | Critical |
| P2 | Algorithm Complexity (CPU) | Major |
| P3 | Memory Patterns (MEM) | Minor |

### Severity Guide

| Severity | Definition | Action |
|----------|------------|--------|
| 🔴 BLOCKER | OOM, deadlock, resource exhaustion | Must fix |
| 🟠 CRITICAL | Severe degradation (N+1, blocking) | Must fix |
| 🟡 MAJOR | Noticeable impact (O(n²), no timeout) | Should fix |
| 🔵 MINOR | Suboptimal but functional | Consider |
| ⚪ SUGGESTION | Potential improvement | Optional |
| 🟢 COMMENDATION | Excellent practice | Reinforce |

### Verdict Logic

```
BLOCKER found? ────────► FAIL
CRITICAL found? ───────► NEEDS_WORK
Multiple MAJOR? ───────► NEEDS_WORK
Few MAJOR/MINOR? ──────► PASS_WITH_SUGGESTIONS
Otherwise ─────────────► PASS
```

---

## Evaluation Criteria

### CPU Efficiency (CPU)

| ID | Criterion | Sev | Check |
|----|-----------|-----|-------|
| CPU.1 | Algorithm complexity appropriate | MAJOR | No O(n²)+ on unbounded data |
| CPU.2 | Pure functions cached | MINOR | `@cache`/`@lru_cache` applied |
| CPU.3 | Hot loops optimized | MINOR | Localized attribute lookups |

### Memory Efficiency (MEM)

| ID | Criterion | Sev | Check |
|----|-----------|-----|-------|
| MEM.1 | Large data uses generators | CRITICAL | No `[x for x in huge_data]` |
| MEM.2 | High-volume classes use slots | MINOR | >10k instances → `__slots__` |
| MEM.3 | Caches are bounded | MAJOR | `maxsize=N` on lru_cache |

### I/O Patterns (IO)

| ID | Criterion | Sev | Check |
|----|-----------|-----|-------|
| IO.1 | No N+1 query patterns | CRITICAL | No queries in loops |
| IO.2 | Connections pooled | MAJOR | Module-level pools |
| IO.3 | Explicit timeouts on I/O | MAJOR | `timeout=` on external calls |

### Async Correctness (ASYNC)

| ID | Criterion | Sev | Check |
|----|-----------|-----|-------|
| ASYNC.1 | No blocking I/O in async | BLOCKER | No `requests`, `open()`, `Path.read_text()` |
| ASYNC.2 | Bounded concurrency | BLOCKER | Semaphore on `gather()`/`TaskGroup` |
| ASYNC.3 | CancelledError re-raised | CRITICAL | Not caught without re-raise |

---

## Patterns

### ✅ Quality Indicator

```python
MAX_CONCURRENT = 50
semaphore = asyncio.Semaphore(MAX_CONCURRENT)

async def fetch_all(urls: list[str]) -> list[Response]:
    async def fetch_one(url: str) -> Response:
        async with semaphore:
            async with httpx.AsyncClient(timeout=10.0) as client:
                return await client.get(url)
    async with asyncio.TaskGroup() as tg:
        tasks = [tg.create_task(fetch_one(url)) for url in urls]
    return [t.result() for t in tasks]
```
**Why:** Bounded concurrency, explicit timeout, TaskGroup for exception propagation.

### ❌ Red Flag

```python
async def fetch_all(urls: list[str]) -> list[Response]:
    return await asyncio.gather(*[
        asyncio.to_thread(requests.get, url) for url in urls
    ])
```
**Why:** Unbounded gather creates unlimited threads; uses sync `requests` in async.

---

## Finding Format

```markdown
### [🟠 CRITICAL] {{TITLE}}

**Location:** `{{FILE}}:{{LINE}}`  
**Criterion:** {{ID}} - {{NAME}}

**Issue:** {{DESCRIPTION}}

**Evidence:**
\`\`\`python
{{CODE}}
\`\`\`

**Suggestion:** {{FIX}}

**Rationale:** {{WHY}}
```

---

## Skill Chaining

| Verdict | Action | Target |
|---------|--------|--------|
| `FAIL` | Mandatory | `optimize/performance` |
| `NEEDS_WORK` | Targeted | `optimize/performance` |
| `PASS_WITH_SUGGESTIONS` | Optional | None |
| `PASS` | Continue | Next phase |

**Handoff Context:**
```markdown
**Target:** `optimize/performance`
**Findings:** {{BLOCKER_AND_CRITICAL_IDS}}
**Bottleneck:** {{CPU|Memory|I/O|Async}}
**Constraint:** Preserve behavior; run tests after
```

**Re-Review:** Max 3 iterations, scope limited to modified files.

---

## Example: N+1 Detection

**Input:**
```python
async def get_orders_with_items(order_ids: list[int]) -> list[Order]:
    orders = []
    for order_id in order_ids:
        order = await db.fetch_one("SELECT * FROM orders WHERE id = $1", order_id)
        items = await db.fetch_all("SELECT * FROM items WHERE order_id = $1", order_id)
        orders.append(Order(**order, items=items))
    return orders
```

**Finding:**
```markdown
### [🟠 CRITICAL] N+1 Query Pattern in Order Fetching

**Location:** `services/order_service.py:15`  
**Criterion:** IO.1 - No N+1 query patterns

**Issue:** Each order triggers 2 queries in loop. 100 orders = 200 queries vs 2.

**Suggestion:** Batch with `WHERE id = ANY($1)`:
\`\`\`python
orders = await db.fetch_all("SELECT * FROM orders WHERE id = ANY($1)", order_ids)
items = await db.fetch_all("SELECT * FROM items WHERE order_id = ANY($1)", order_ids)
\`\`\`

**Rationale:** N+1 is #1 cause of API latency. Batching: O(n) → O(1) round trips.
```

**Verdict:** `NEEDS_WORK` → Chain to `optimize/performance` (I/O focus)

---

## Deep References

| Reference | When | Path |
|-----------|------|------|
| CPU | Algorithm/caching | `optimize/performance/refs/cpu.md` |
| Memory | Generators/slots | `optimize/performance/refs/memory.md` |
| I/O | Batching/pooling | `optimize/performance/refs/io.md` |
| Async | Concurrency/blocking | `optimize/performance/refs/async.md` |

---

## Quality Gates

- [ ] All Python files in scope analyzed
- [ ] Each finding: location + criterion + severity
- [ ] Verdict aligns with severity distribution
- [ ] Actionable suggestions for non-PASS
- [ ] Chain decision explicit with bottleneck type
- [ ] No false positives on intentional patterns
