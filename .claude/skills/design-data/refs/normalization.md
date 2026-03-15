# Normalization & Denormalization Reference

> Detailed guidance on normal forms, when to normalize, when to denormalize, and how to measure the trade-offs.

---

## Quick Reference

| Normal Form | Rule | Violation Example |
|-------------|------|-------------------|
| **1NF** | Atomic values only | `tags = 'red,blue'` |
| **2NF** | Full key dependency | Non-key depends on part of composite key |
| **3NF** | No transitive dependency | `zip → city` in customer table |
| **BCNF** | Every determinant is a key | Overlapping candidate keys |

---

## Normal Forms Explained

### First Normal Form (1NF)

**Rule:** Every column contains atomic (indivisible) values. No arrays, no comma-separated lists.

```sql
-- ❌ VIOLATES 1NF: Multi-valued column
CREATE TABLE orders (
    order_id INT PRIMARY KEY,
    product_ids VARCHAR(500)  -- '101,102,103'
);

-- ✅ 1NF COMPLIANT: Separate rows
CREATE TABLE order_items (
    order_id INT REFERENCES orders(id),
    product_id INT REFERENCES products(id),
    quantity INT NOT NULL,
    PRIMARY KEY (order_id, product_id)
);
```

**Why It Matters:**







- Can't index into comma-separated values
- Can't enforce foreign key constraints
- Query complexity increases (`LIKE '%value%'` doesn't scale)

---

### Second Normal Form (2NF)

**Rule:** Every non-key attribute depends on the *entire* primary key, not just part of it.

**Applies to:** Tables with composite primary keys.

```sql
-- ❌ VIOLATES 2NF: product_name depends only on product_id
CREATE TABLE order_items (
    order_id INT,
    product_id INT,
    quantity INT,
    product_name VARCHAR(100),  -- Depends only on product_id!
    PRIMARY KEY (order_id, product_id)
);

-- ✅ 2NF COMPLIANT: Remove partial dependency
CREATE TABLE order_items (
    order_id INT,
    product_id INT REFERENCES products(id),
    quantity INT,
    PRIMARY KEY (order_id, product_id)
);

CREATE TABLE products (

    id INT PRIMARY KEY,

    name VARCHAR(100)

);

```



**Why It Matters:**

- Update anomaly: Change product name → update every order_item
- Insert anomaly: Can't add product without an order
- Delete anomaly: Delete last order → lose product info

---

### Third Normal Form (3NF)

**Rule:** No transitive dependencies. Non-key attributes don't depend on other non-key attributes.

```sql
-- ❌ VIOLATES 3NF: city depends on zip_code, not customer_id
CREATE TABLE customers (
    customer_id INT PRIMARY KEY,
    name VARCHAR(100),
    zip_code VARCHAR(10),
    city VARCHAR(50),        -- zip_code → city (transitive)
    state VARCHAR(2)         -- zip_code → state (transitive)
);

-- ✅ 3NF COMPLIANT: Extract transitive dependency
CREATE TABLE customers (
    customer_id INT PRIMARY KEY,

    name VARCHAR(100),
    zip_code VARCHAR(10) REFERENCES zip_codes(code)

);


CREATE TABLE zip_codes (
    code VARCHAR(10) PRIMARY KEY,

    city VARCHAR(50) NOT NULL,
    state VARCHAR(2) NOT NULL

);
```


**Why It Matters:**

- Single source of truth for zip → city mapping
- No risk of inconsistent city names for same zip
- Smaller customer table (better cache efficiency)

---

### Boyce-Codd Normal Form (BCNF)

**Rule:** Every determinant (column that determines another) must be a candidate key.

```sql
-- ❌ VIOLATES BCNF: teacher determines subject, but teacher isn't a key
CREATE TABLE class_assignments (
    student_id INT,
    subject VARCHAR(50),
    teacher VARCHAR(50),
    PRIMARY KEY (student_id, subject)
    -- Constraint: Each teacher teaches only one subject
    -- teacher → subject, but teacher isn't a candidate key
);

-- ✅ BCNF COMPLIANT: Decompose
CREATE TABLE teachers (
    teacher_id INT PRIMARY KEY,
    name VARCHAR(50),
    subject VARCHAR(50) NOT NULL
);

CREATE TABLE enrollments (
    student_id INT,
    teacher_id INT REFERENCES teachers(id),
    PRIMARY KEY (student_id, teacher_id)
);
```

**When BCNF Matters:** Rare in practice. Apply when you have overlapping candidate keys causing update anomalies.

---

## Must Rules

- **MUST** start at 3NF for new schemas—it's the safe default
- **MUST** document every denormalization decision with measured justification
- **MUST** measure read/write ratio before denormalizing
- **MUST** define update strategy when denormalizing (sync, async, eventual)
- **MUST** add constraints even on denormalized columns where possible
- **MUST** track denormalized data lineage (source of truth location)

---

## Never Rules

- **NEVER** denormalize without measured performance evidence
- **NEVER** denormalize frequently-updated data (write amplification)
- **NEVER** denormalize without defining consistency requirements
- **NEVER** assume denormalization is "just caching"—it's schema design
- **NEVER** denormalize M:N relationships into arrays (1NF violation)
- **NEVER** skip 3NF "because NoSQL"—document stores need structure too

---

## When → Then Decisions

### Normalization Triggers

| When | Then | Rationale |
|------|------|-----------|
| Data changes frequently | Normalize | Single update location |
| Multiple entry points to data | Normalize | Consistency across paths |
| Storage costs are significant | Normalize | Reduce redundancy |
| Schema is evolving rapidly | Normalize | Easier to change |
| Audit/compliance requirements | Normalize | Clear source of truth |

### Denormalization Triggers

| When | Then | Rationale |
|------|------|-----------|
| Read/write ratio > 10:1 AND data is stable | Consider denormalization | Read cost dominates |
| Query requires 4+ JOINs | Consider materialized view | Join cost too high |
| Latency SLA < 10ms for complex query | Consider denormalization | Joins add latency |
| Reporting on historical snapshots | Denormalize at write time | Point-in-time accuracy |
| Cross-shard queries | Denormalize within shard | Avoid distributed joins |

### Denormalization Method Selection

| When | Then |
|------|------|
| Read-heavy, batch-updatable | Materialized view with scheduled refresh |
| Real-time reads, infrequent writes | Synchronous denormalization (same transaction) |
| High write volume, staleness OK | Async denormalization (event-driven) |
| Analytics/reporting | Separate read replica with different schema |
| Single entity enrichment | Computed/generated columns |

---

## Denormalization Patterns

### Pattern 1: Cached Aggregates

Store pre-computed aggregates on parent entity.

```sql
-- Normalized: Count requires query
SELECT COUNT(*) FROM order_items WHERE order_id = ?;

-- Denormalized: Count stored on parent
CREATE TABLE orders (
    id INT PRIMARY KEY,
    customer_id INT,
    item_count INT DEFAULT 0,          -- Denormalized
    total_amount DECIMAL(10,2) DEFAULT 0  -- Denormalized
);

-- Update strategy: Trigger or application code
CREATE TRIGGER update_order_totals
AFTER INSERT ON order_items
FOR EACH ROW
UPDATE orders SET
    item_count = item_count + 1,
    total_amount = total_amount + NEW.line_total
WHERE id = NEW.order_id;
```

**Trade-off:** Faster reads, but every item insert/update/delete must update order.

---

### Pattern 2: Snapshot Denormalization

Capture values at point-in-time, don't reference current values.

```sql
-- ❌ WRONG: Price changes affect historical orders
CREATE TABLE order_items (

    order_id INT,
    product_id INT REFERENCES products(id),
    quantity INT

    -- Price looked up from products table at query time
);


-- ✅ RIGHT: Capture price at order time
CREATE TABLE order_items (
    order_id INT,

    product_id INT,
    quantity INT,
    unit_price DECIMAL(10,2) NOT NULL,  -- Snapshot

    product_name VARCHAR(100) NOT NULL,  -- Snapshot
    product_sku VARCHAR(50) NOT NULL     -- Snapshot
);

```

**When Required:**

- Financial records (invoices, receipts)
- Audit trails
- Historical reporting
- Legal/compliance requirements

---

### Pattern 3: Materialized Path

Denormalize hierarchy for efficient subtree queries.

```sql
-- Normalized: Adjacency list (slow for subtree queries)
CREATE TABLE categories (
    id INT PRIMARY KEY,
    parent_id INT REFERENCES categories(id),
    name VARCHAR(100)
);
-- Finding all descendants requires recursive CTE

-- Denormalized: Materialized path
CREATE TABLE categories (
    id INT PRIMARY KEY,
    parent_id INT REFERENCES categories(id),
    name VARCHAR(100),
    path VARCHAR(500) NOT NULL,  -- '/1/5/12/45'
    depth INT NOT NULL           -- 4
);

-- All descendants of category 5:
SELECT * FROM categories WHERE path LIKE '/1/5/%';

-- All ancestors:
-- Parse path string: '/1/5/12' → [1, 5, 12]
```

**Trade-off:** O(1) subtree queries, but path must be updated on every move.

---

### Pattern 4: Closure Table

Best denormalization for complex hierarchies.

```sql
-- Closure table stores ALL ancestor-descendant pairs
CREATE TABLE category_closure (
    ancestor_id INT REFERENCES categories(id),
    descendant_id INT REFERENCES categories(id),
    depth INT NOT NULL,
    PRIMARY KEY (ancestor_id, descendant_id)
);

-- Node 5's subtree (all descendants):
SELECT c.* FROM categories c
JOIN category_closure cc ON c.id = cc.descendant_id
WHERE cc.ancestor_id = 5;

-- Node 5's ancestors:
SELECT c.* FROM categories c
JOIN category_closure cc ON c.id = cc.ancestor_id
WHERE cc.descendant_id = 5
ORDER BY cc.depth DESC;
```

**Trade-off:** O(n) rows for n nodes, but O(1) ancestor/descendant queries.

---

## Anti-Patterns

### ❌ Premature Denormalization

```sql
-- WRONG: Denormalizing "just in case"
CREATE TABLE users (
    id INT PRIMARY KEY,
    name VARCHAR(100),
    order_count INT,           -- "Might need this"
    total_spent DECIMAL(10,2), -- "Could be useful"
    last_order_date TIMESTAMP, -- "Why not"
    favorite_category VARCHAR(50) -- "Users might want"
);
-- Now every order affects users table
-- No measured evidence these fields are needed
```

**Fix:** Start normalized. Add denormalization only when query performance proves insufficient.

---

### ❌ Denormalizing Volatile Data

```sql
-- WRONG: Denormalizing frequently-changing data
CREATE TABLE order_items (
    id INT PRIMARY KEY,
    product_id INT,
    current_stock_level INT  -- Changes constantly!
);
-- Every inventory change updates every order_item
```

**Fix:** Only denormalize stable data. For volatile data, accept the join cost or use caching layer.

---

### ❌ Inconsistent Denormalization


```sql
-- WRONG: Denormalized in some places, not others
-- Table A has customer_name denormalized

-- Table B references customer_id only
-- Table C has customer_email denormalized
-- Which is the source of truth?
```


**Fix:** Document the canonical source. Denormalize consistently or not at all.

---


### ❌ Denormalization Without Update Strategy

```sql

-- WRONG: Denormalized but no plan for updates
ALTER TABLE orders ADD COLUMN customer_name VARCHAR(100);
UPDATE orders o SET customer_name = (SELECT name FROM customers WHERE id = o.customer_id);
-- What happens when customer name changes?

-- No trigger, no event handler, no sync process defined
```

**Fix:** Define update strategy BEFORE denormalizing:

- Synchronous (same transaction)
- Trigger-based
- Event-driven (async)
- Scheduled batch
- Accept staleness (document SLA)

---

## Measuring Denormalization Trade-offs

### Calculate Read/Write Ratio

```sql
-- Measure over representative time period
SELECT
    (SELECT COUNT(*) FROM query_log WHERE table_name = 'products' AND operation = 'SELECT') AS reads,
    (SELECT COUNT(*) FROM query_log WHERE table_name = 'products' AND operation IN ('INSERT','UPDATE','DELETE')) AS writes;

-- Ratio > 10:1 = candidate for denormalization
-- Ratio < 10:1 = normalization preferred
```

### Calculate Write Amplification

```
Write Amplification = (Denormalized writes) / (Normalized writes)

Example:
- Normalized: Update customer name = 1 write
- Denormalized: Update customer name = 1 + (orders with customer_name) writes

If customer has 1000 orders, WA = 1001x
```

### Calculate Join Cost

```sql
-- Measure join query performance
EXPLAIN ANALYZE
SELECT o.*, c.name, c.email, p.name as product_name
FROM orders o
JOIN customers c ON o.customer_id = c.id
JOIN order_items oi ON oi.order_id = o.id
JOIN products p ON oi.product_id = p.id
WHERE o.id = ?;

-- If join cost > latency SLA, consider denormalization
```

---

## Denormalization Checklist

Before denormalizing, verify:

- [ ] Read/write ratio measured (target: >10:1)
- [ ] Query latency measured (proves need)
- [ ] Write amplification calculated
- [ ] Update strategy defined (sync/async/batch)
- [ ] Consistency SLA defined (how stale is acceptable)
- [ ] Source of truth documented
- [ ] Rollback plan exists (can re-normalize)
- [ ] Monitoring in place (detect drift)

---

## Decision Matrix

| Scenario | Recommendation |
|----------|----------------|
| New feature, unknown query patterns | **3NF** — optimize later |
| OLTP with complex transactions | **3NF** — consistency matters |
| OLAP/reporting warehouse | **Denormalize** — read optimized |
| Event sourcing projections | **Denormalize** — derived views |
| Microservice local data | **3NF** — service owns schema |
| Cross-service read model | **Denormalize** — avoid distributed joins |
| Audit/compliance data | **3NF** — source of truth |
| User-facing dashboards | **Denormalize** — latency matters |
