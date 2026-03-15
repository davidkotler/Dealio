---
name: design-data
version: 1.0.0
description: |
  Design data models, schemas, and access patterns before implementation.
  Use when creating database schemas, defining entities, modeling relationships,
  planning data storage, designing tables, or before any data read/write code.
  Relevant for SQL, NoSQL, data modeling, schema design, access patterns.
---

# Data Model & Schema Design

> Design data structures that are correct by construction—validate access patterns before writing any code.

## Quick Reference

| Aspect | Details |
|--------|---------|
| **Invokes** | `implement/data`, `implement/database`, `design/api` |
| **Invoked By** | `design/code`, `implement/python`, `implement/api` |
| **Output** | Schema definitions, access pattern docs, entity diagrams |

---

## Core Workflow

1. **Enumerate Access Patterns** — List every query BEFORE designing schema
2. **Define Entities** — Identify entities by identity, not attributes
3. **Model Relationships** — Specify cardinality (1:1, 1:N, M:N) and optionality
4. **Design Keys** — Choose surrogate vs natural; plan for immutability
5. **Normalize First** — Start 3NF; denormalize only with measured evidence
6. **Plan Evolution** — Define how schema will change (expand-contract)
7. **Validate** — Every query must use an index; no unbounded results

---

## Must Rules

### Schema Design

- **MUST** define primary key for every entity
- **MUST** document the grain of each table (what does one row represent?)
- **MUST** enforce constraints at data layer (NOT NULL, UNIQUE, FK, CHECK)
- **MUST** version schemas in source control with migrations
- **MUST** plan schema evolution before first deployment
- **MUST** separate operational (OLTP) from analytical (OLAP) workloads
- **MUST** define retention policy for every table

### Access Patterns

- **MUST** enumerate all access patterns before modeling
- **MUST** identify partition/shard key early—often irreversible
- **MUST** ensure every query can use an index
- **MUST** define consistency requirements per operation
- **MUST** paginate all list queries (no unbounded results)

### Keys

- **MUST** keep primary keys immutable—if they might change, use surrogate
- **MUST** use DECIMAL/NUMERIC for money (never floating-point)
- **MUST** store dates as dates, numbers as numbers (no string encoding)

---

## Never Rules

### Schema Design

- **NEVER** use reserved words as identifiers (`user`, `order`, `group`, `table`)
- **NEVER** store multiple values in single column (no CSV, no JSON arrays in relational)
- **NEVER** use floating-point for money—use integer cents or DECIMAL
- **NEVER** rely on implicit type coercion
- **NEVER** create circular foreign key dependencies
- **NEVER** ignore NULL semantics (NULL ≠ empty string ≠ zero)
- **NEVER** design assuming schema won't change

### Access Patterns

- **NEVER** design storage without knowing the queries
- **NEVER** assume all reads need strong consistency
- **NEVER** create indexes for every possible query (measure first)
- **NEVER** ignore write amplification from denormalization

### Keys

- **NEVER** use natural keys that might change (email, username)
- **NEVER** expose sequential IDs externally (security + enumeration risk)

---

## When → Then Decisions

### Key Design

| When | Then |
|------|------|
| Natural key might change | Use surrogate key (UUID or auto-increment) |
| Entity referenced from many places | Use immutable surrogate key |
| Ordering matters for range queries | Use sortable keys (timestamp prefix, ULID) |
| Distributing across shards | Use high-cardinality, uniform keys (UUID) |
| Debugging needs human-readable IDs | Encode type in prefix (`user_`, `order_`) |

### Normalization

| When | Then |
|------|------|
| Read/write ratio > 10:1 AND data stable | Consider denormalization |
| High update frequency on shared data | Normalize to single source of truth |
| Queries always need combined data | Denormalize or use materialized view |
| Storage cost > query complexity cost | Normalize aggressively |

### Consistency

| When | Then |
|------|------|
| User must see their own writes | Route to same replica or read-your-writes |
| Financial transaction or inventory | Strong consistency (accept latency) |
| Social feed or catalog display | Eventual consistency acceptable |
| Distributed lock / leader election | Linearizable consistency required |

### Partitioning

| When | Then |
|------|------|
| Single node can't handle write volume | Partition by high-cardinality attribute |
| Queries always filter by attribute X | Partition by X for pruning |
| Data has natural time ordering | Time-based partitioning with retention |
| Access is skewed (hot keys) | Add random suffix or bucket |

---

## Patterns

### ✅ Structural Patterns

**Surrogate Key with Type Prefix**
```sql
-- Readable, immutable, no enumeration risk
id VARCHAR(26) PRIMARY KEY  -- e.g., 'user_01HX3QWERTY'
```

**Audit Columns**
```sql
created_at TIMESTAMP NOT NULL DEFAULT NOW(),
updated_at TIMESTAMP,
created_by VARCHAR(26) NOT NULL,
updated_by VARCHAR(26)
```

**Soft Delete**
```sql
deleted_at TIMESTAMP,  -- NULL = active, non-NULL = deleted
-- All queries: WHERE deleted_at IS NULL
```

**Bridge Table for M:N**
```sql
CREATE TABLE user_roles (
    user_id VARCHAR(26) REFERENCES users(id),
    role_id VARCHAR(26) REFERENCES roles(id),
    granted_at TIMESTAMP NOT NULL,
    granted_by VARCHAR(26) NOT NULL,
    PRIMARY KEY (user_id, role_id)
);
```

### ✅ Access Patterns

**Idempotent Processing**
```python
async def process_event(event: Event) -> None:
    if await processed.exists(event.idempotency_key):
        return  # Already handled
    async with transaction():
        await handle(event)
        await processed.record(event.idempotency_key)
```

**Paginated Query**
```sql
-- Cursor-based (scalable)
SELECT * FROM orders
WHERE created_at < :cursor
ORDER BY created_at DESC
LIMIT 20;
```

---

## Anti-Patterns

### ❌ Schema Anti-Patterns

**Entity-Attribute-Value (EAV)**
```sql
-- WRONG: No type safety, no constraints, slow queries
CREATE TABLE attributes (
    entity_id INT,
    attr_name VARCHAR(50),
    attr_value TEXT
);
```

**Comma-Separated Values**
```sql
-- WRONG: Can't query, can't index, can't enforce FK
tags VARCHAR(500)  -- 'red,blue,green'
```

**Primitive Obsession**
```python
# WRONG: order_id and customer_id easily swapped
def create_order(order_id: str, customer_id: str): ...
```
```python
# RIGHT: Type-safe domain identifiers
OrderId = NewType("OrderId", str)
CustomerId = NewType("CustomerId", str)
def create_order(order_id: OrderId, customer_id: CustomerId): ...
```

### ❌ Access Anti-Patterns

**N+1 Query**
```python
# WRONG: N+1 database calls
orders = db.query("SELECT * FROM orders")
for order in orders:
    items = db.query(f"SELECT * FROM items WHERE order_id = {order.id}")
```
```python
# RIGHT: Single query with join
orders = db.query("""
    SELECT o.*, i.* FROM orders o
    LEFT JOIN items i ON i.order_id = o.id
""")
```

**Unbounded Query**
```sql
-- WRONG: Could return millions of rows
SELECT * FROM events WHERE type = 'click';
```
```sql
-- RIGHT: Always paginate
SELECT * FROM events WHERE type = 'click' LIMIT 100;
```

**Hot Partition**
```sql
-- WRONG: All today's data hits one partition
PARTITION BY (DATE(created_at))  -- "today" is always hot
```
```sql
-- RIGHT: Distribute with hash
PARTITION BY HASH(user_id)
```

---

## Skill Chaining

| Condition | Invoke | Handoff |
|-----------|--------|---------|
| Schema ready for implementation | `implement/data` | DDL statements, constraints |
| API contracts needed | `design/api` | Entity shapes, response models |
| Need database-specific syntax | `implement/database` | Target database type |

---

## Quality Gates

Before completing data design:

- [ ] Every access pattern documented with frequency and latency target
- [ ] Every table has defined grain (what is one row?)
- [ ] Primary keys are immutable
- [ ] All queries can use an index (no full scans)
- [ ] No unbounded queries (all paginated)
- [ ] Constraints enforced at data layer
- [ ] Schema evolution strategy defined
- [ ] Retention policy documented

---

## Access Pattern Template

```markdown
**Pattern**: [Name]
**Frequency**: [req/sec or daily count]
**Query**: [pseudo-SQL]
**Latency**: [p50, p99 targets]
**Consistency**: [strong | eventual | read-your-writes]
**Volume**: [rows returned, bytes]
**Index**: [columns used]
```

---

## Deep References

For extended guidance, see:







- `refs/normalization.md` — Detailed normal forms and denormalization criteria
- `refs/access-patterns.md` — Comprehensive guidance on designing, validating, and optimizing data access
- `refs/relationships.md` — Guidance on modeling entity relationships: cardinality, optionality, foreign keys, and join strategies.
