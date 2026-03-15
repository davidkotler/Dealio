---
name: review-data
version: 1.0.0

description: |
  Review data layer implementations for correctness, performance, and maintainability.
  Evaluates schemas, repositories, queries, and domain models against data engineering principles.
  Use when reviewing database schemas, data access code, repository implementations,
  Pydantic models, SQL queries, NoSQL SDK queries, migrations, or after any data layer changes.
  Relevant for SQL/NoSQL, data access layers, ORM/ODM/data manipulation libraries code.

---

# Data Layer Review

> Validate data implementations are correct by construction—schemas enforce constraints, queries match access patterns, repositories return domain models.

## Quick Reference

| Aspect | Details |
|--------|---------|
| **Dimension** | Data Layer Quality |
| **Scope** | Schemas, repositories, queries, domain models, migrations |
| **Invoked By** | `implement/data`, `implement/python`, `/review` command |
| **Invokes** | `implement/data` (on failure) |
| **Verdict Options** | `PASS` · `PASS_WITH_SUGGESTIONS` · `NEEDS_WORK` · `FAIL` |

---

## Review Objective

Ensure data layer code enforces correctness at the database level, follows repository patterns, uses type-safe domain models, and implements efficient access patterns.

### This Review Answers

1. Do schemas enforce constraints (FK, NOT NULL, CHECK) at the database level?
2. Do queries match documented access patterns with proper indexes?
3. Do repositories return domain models, not raw dicts or ORM objects?
4. Are all list queries paginated with explicit limits?

### Out of Scope

- Business logic correctness (see `review/functionality`)
- API contract validation (see `review/api`)

---

## Core Workflow

1. **SCOPE** — Find: `**/migrations/**/*.py`, `**/*_repository.py`, `**/models/**/*.py`
2. **CONTEXT** — Load design artifacts (access patterns) and `rules/principles.md` §3.1–3.8
3. **ANALYZE** — Apply criteria by priority: P0 Schema → P1 Query → P2 Repository → P3 Types
4. **CLASSIFY** — Assign severity per finding
5. **VERDICT** — Determine pass/fail based on severity counts
6. **CHAIN** — Invoke `implement/data` if FAIL or NEEDS_WORK

### Severity Levels

| Severity | Definition | Action |
|----------|------------|--------|
| **🔴 BLOCKER** | Data corruption, security vulnerability | Must fix |
| **🟠 CRITICAL** | Performance degradation, constraint violation | Must fix |
| **🟡 MAJOR** | Pattern violation, maintainability issue | Should fix |
| **🔵 MINOR** | Style inconsistency, enhancement | Consider |

### Verdict Logic

```
BLOCKER present? → FAIL | CRITICAL present? → NEEDS_WORK |
Multiple MAJOR? → NEEDS_WORK | else → PASS or PASS_WITH_SUGGESTIONS
```

---

## Evaluation Criteria

### Schema Integrity (SI)

| ID | Criterion | Severity | Check |
|----|-----------|----------|-------|
| SI.1 | FK constraints at database level | 🔴 BLOCKER | `REFERENCES` clause present |
| SI.2 | NOT NULL on required fields | 🔴 BLOCKER | No implicit NULLs |
| SI.3 | CHECK constraints for enums | 🟠 CRITICAL | `CHECK (status IN (...))` |
| SI.4 | Index on every FK column | 🟠 CRITICAL | `CREATE INDEX` exists |
| SI.5 | DECIMAL for monetary values | 🔴 BLOCKER | Never FLOAT/REAL |
| SI.6 | Audit columns present | 🟡 MAJOR | `created_at`, `updated_at` |
| SI.7 | Explicit ON DELETE behavior | 🟡 MAJOR | `ON DELETE RESTRICT/CASCADE` |
| SI.8 | No reserved word identifiers | 🟡 MAJOR | Avoid `user`, `order`, `table` |

### Query Safety (QS)

| ID | Criterion | Severity | Check |
|----|-----------|----------|-------|
| QS.1 | Parameterized queries only | 🔴 BLOCKER | No string concatenation |
| QS.2 | All list queries have LIMIT | 🔴 BLOCKER | No unbounded results |
| QS.3 | Explicit column lists | 🟠 CRITICAL | No `SELECT *` |
| QS.4 | Cursor-based pagination | 🟡 MAJOR | No OFFSET >1000 |
| QS.5 | Index-compatible WHERE | 🟡 MAJOR | No functions on indexed cols |
| QS.6 | Batch fetches for N items | 🟠 CRITICAL | `WHERE id = ANY($1)` |

### Repository Pattern (RP)

| ID | Criterion | Severity | Check |
|----|-----------|----------|-------|
| RP.1 | Returns domain models | 🟠 CRITICAL | Not dicts/ORM objects |
| RP.2 | Async for all I/O | 🟠 CRITICAL | `async def` everywhere |
| RP.3 | Protocol interface defined | 🟡 MAJOR | ABC/Protocol before impl |
| RP.4 | Injected dependencies | 🟡 MAJOR | Connection via constructor |
| RP.5 | Explicit None handling | 🟡 MAJOR | `-> T | None` signatures |
| RP.6 | Transaction boundaries | 🟡 MAJOR | Context managers used |
| RP.7 | Idempotency keys for writes | 🟡 MAJOR | Check-before-write pattern |

### Type Safety (TS)

| ID | Criterion | Severity | Check |
|----|-----------|----------|-------|
| TS.1 | Typed domain identifiers | 🟡 MAJOR | `NewType("OrderId", str)` |
| TS.2 | Pydantic for boundaries | 🟡 MAJOR | External data validated |
| TS.3 | Frozen entities | 🔵 MINOR | `frozen=True` for immutable |
| TS.4 | Separate read/write models | 🔵 MINOR | Request ≠ Response types |

---

## Patterns & Anti-Patterns

### ✅ Correct Implementation

```python
# Typed identifiers prevent argument swapping
OrderId = NewType("OrderId", str)
CustomerId = NewType("CustomerId", str)

class OrderRepository(Protocol):
    async def get(self, order_id: OrderId) -> Order | None: ...

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

**Why this works:** Type-safe IDs, protocol interface, async I/O, parameterized query, explicit columns, returns domain model.

### ❌ Red Flags

```python
# Multiple violations
class OrderRepo:
    def get_orders(self, customer_id: str):  # sync, primitive ID
        return self.session.execute(
            f"SELECT * FROM orders WHERE customer_id = '{customer_id}'"
        ).fetchall()  # SQL injection, SELECT *, unbounded, returns raw
```

**Why this fails:** String interpolation (injection), `SELECT *`, no LIMIT, sync I/O, primitive ID, returns raw rows.

---

## Output Formats

### Finding Format

```markdown
### [🔴 BLOCKER] Missing FK constraint
**Location:** `migrations/001_orders.py:15` | **Criterion:** SI.1
**Issue:** customer_id has no FOREIGN KEY constraint
**Suggestion:** Add `REFERENCES customers(id) ON DELETE RESTRICT`
```

### Summary Format

```markdown
# Data Layer Review: {{VERDICT}}
| Blockers | Critical | Major | Minor | Files |
|----------|----------|-------|-------|-------|
| N        | N        | N     | N     | N     |

**Key Findings:** 1. [Sev] Issue... 2. [Sev] Issue...
**Chain Decision:** {{Invoke implement/data | Continue | None}}
```

---

## Skill Chaining

| Verdict | Chain To | Handoff |
|---------|----------|---------|
| `FAIL` | `implement/data` | Blocker IDs + constraint: preserve access patterns |
| `NEEDS_WORK` | `implement/data` | Critical/Major IDs + files to fix |
| `PASS_WITH_SUGGESTIONS` | None | Suggestions only |
| `PASS` | `test/integration` | Continue pipeline |

---

## Quality Gates

Before completing review:

- [ ] All schema files analyzed for constraints
- [ ] All repositories checked for pattern compliance
- [ ] All queries verified for parameterization and limits
- [ ] Each finding has location + criterion + severity
- [ ] Verdict aligns with severity distribution
- [ ] Chain decision is explicit

---

## Deep References

Load on-demand for complex reviews:

| Reference | When to Load |
|-----------|--------------|
| `design/data/refs/access-patterns.md` | Validating query coverage |
| `implement/data/refs/repository.md` | Repository pattern details |
| `rules/principles.md` §3.1–3.8 | Data engineering principles |
