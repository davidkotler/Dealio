# SQL Best Practices, Standards, Conventions & Advanced Techniques for OLTP and Transactional Queries

> A comprehensive technical reference for building high-performance, maintainable, and reliable transactional SQL
> systems.

---

## 1. Foundational Principles of OLTP Systems

Online Transaction Processing (OLTP) systems are designed to manage and execute large volumes of real-time transactions
from many concurrent users. Every architectural and query design decision must be measured against the ACID guarantees
that underpin transactional integrity.

**ACID Properties Recap:**

- **Atomicity** — A transaction completes in full or not at all. If any step fails, the entire transaction is rolled
  back, leaving the database unchanged.
- **Consistency** — Every committed transaction transitions the database from one valid state to another, respecting all
  constraints, triggers, and rules.
- **Isolation** — Concurrent transactions execute as though they are the only operation on the database, preventing
  interference and data corruption.
- **Durability** — Once committed, changes persist permanently even through system failures, guaranteed by the
  transaction log and write-ahead logging.

OLTP workloads are characterized by short, fast queries that touch small numbers of rows, high concurrency from many
simultaneous users, a mix of reads and writes (with writes being frequent), and the need for sub-second response times.
The guidance in this document is oriented around these characteristics.

---

## 2. Naming Conventions and Standards

Consistent naming is the foundation of maintainable SQL. A team that agrees on naming conventions eliminates ambiguity,
accelerates onboarding, and reduces errors in queries, migrations, and automation.

### 2.1 General Rules

- **Use lowercase with underscores** (`snake_case`) for all identifiers: table names, column names, indexes,
  constraints. This avoids case-sensitivity issues across platforms and eliminates the need for quoted identifiers.
- **Never use SQL reserved words** as object names (`order`, `user`, `table`, `index`, `key`, `status`, `date`, `name`).
  If unavoidable, always qualify with the schema name or choose a more descriptive alternative.
- **Avoid spaces, special characters, and leading numerals** in all identifiers. Stick to `[A-Za-z0-9_]`.
- **Be descriptive but concise.** `order_date` is better than `od` or `the_specific_date_on_which_the_order_was_placed`.
  Abbreviations should be widely known and documented in a team glossary.
- **Use one natural language consistently** (e.g., English) for all objects.

### 2.2 Table Naming

- Use **singular nouns** that describe a single row: `customer`, `order_header`, `product`. A row in the `customer`
  table represents one customer.
- Avoid prefixes like `tbl_` or `t_`. The object type is always available from system metadata, and prefixes add noise
  without value.
- For junction/association tables in many-to-many relationships, combine both entity names: `student_course`,
  `order_product`.
- Always **schema-qualify** object references in code: `dbo.customer`, `sales.order_header`. Never hard-code server or
  database names in application SQL.

### 2.3 Column Naming

- Primary key columns: `<table_name>_id` (e.g., `customer_id`, `order_id`) or simply `id` if your ORM convention
  requires it, but the qualified form is preferred for unambiguous joins.
- Foreign key columns: match the name of the referenced primary key exactly (`customer_id` in the `order_header` table
  references `customer.customer_id`).
- Boolean/flag columns: use `is_` or `has_` prefixes (`is_active`, `has_discount`).
- Date/time columns: use `_at` for timestamps (`created_at`, `updated_at`) and `_on` or `_date` for date-only values (
  `birth_date`, `shipped_on`).
- Monetary columns: suffix with `_amount` (`total_amount`, `discount_amount`).
- Count columns: suffix with `_count` (`line_item_count`).

### 2.4 Constraint and Index Naming

- **Primary keys:** `pk_<table>` — e.g., `pk_customer`.
- **Foreign keys:** `fk_<child_table>_<parent_table>` — e.g., `fk_order_header_customer`.
- **Unique constraints:** `uq_<table>_<columns>` — e.g., `uq_customer_email`.
- **Check constraints:** `ck_<table>_<column_or_rule>` — e.g., `ck_order_header_total_positive`.
- **Default constraints:** `df_<table>_<column>` — e.g., `df_order_header_created_at`.
- **Indexes:** `ix_<table>_<columns>` — e.g., `ix_order_header_customer_id_order_date`.
- **Filtered indexes:** `ix_<table>_<columns>_<filter>` — e.g., `ix_order_header_status_active`.

### 2.5 Stored Procedure, Function, and View Naming

- **Stored procedures:** use a verb-noun pattern: `usp_create_order`, `usp_get_customer_by_id`. Avoid the `sp_` prefix
  in SQL Server, as it triggers a master database search first, degrading performance.
- **Functions:** `fn_calculate_tax`, `fn_get_fiscal_year`.
- **Views:** `vw_active_customer`, `vw_order_summary`.
- **Triggers:** `tr_<action>_<table>` — e.g., `tr_after_insert_order_header`.

---

## 3. SQL Coding Style and Formatting

### 3.1 Keyword Casing and Syntax

- **Uppercase all SQL keywords**: `SELECT`, `FROM`, `WHERE`, `JOIN`, `INSERT`, `UPDATE`, `DELETE`, `BEGIN`, `COMMIT`,
  `ROLLBACK`.
- **Lowercase all identifiers** (table names, column names, aliases).
- **Prefer ANSI-standard syntax** over vendor-specific alternatives when possible: `CAST` over `CONVERT`, `COALESCE`
  over `ISNULL`, `ANSI JOIN` syntax over comma-separated `FROM` clauses.
- **Terminate every statement with a semicolon.** This is ANSI standard, and Microsoft has deprecated non-semicolon
  terminators since SQL Server 2008.

### 3.2 Formatting Guidelines

```sql
-- Well-formatted query example
SELECT
    oh.order_id,
    oh.order_date,
    c.customer_name,
    SUM(od.line_total) AS order_total
FROM sales.order_header AS oh
INNER JOIN sales.customer AS c
    ON c.customer_id = oh.customer_id
INNER JOIN sales.order_detail AS od
    ON od.order_id = oh.order_id
WHERE oh.order_date >= '2025-01-01'
  AND oh.status = 'shipped'
GROUP BY
    oh.order_id,
    oh.order_date,
    c.customer_name
HAVING SUM(od.line_total) > 1000.00
ORDER BY oh.order_date DESC;
```

Key style points:

- Place each major clause (`SELECT`, `FROM`, `WHERE`, `GROUP BY`, `ORDER BY`) on its own line.
- Indent columns, join conditions, and filter predicates consistently.
- Use meaningful short aliases (`oh` for `order_header`, `c` for `customer`) and always use the `AS` keyword for
  clarity.
- Align `AND`/`OR` conditions vertically for readability.

### 3.3 Avoiding SELECT *

Never use `SELECT *` in production code. Always list explicit column names. This practice prevents unexpected breakage
when columns are added or reordered, reduces network I/O by transferring only needed data, enables the query optimizer
to use covering indexes, and makes the intent of the query clear to reviewers.

---

## 4. Schema Design for OLTP

### 4.1 Normalization

OLTP schemas should be normalized to at least Third Normal Form (3NF). Normalization reduces data redundancy, enforces
data integrity through foreign keys, minimizes update anomalies (a change to a customer address happens in exactly one
row), and keeps individual rows narrow, improving cache efficiency and I/O.

Selective, controlled denormalization may be justified when a specific read pattern requires it and the write cost is
acceptable, but this should be treated as an exception backed by measurement rather than a default.

### 4.2 Primary Key Design

Choose primary keys that are narrow (4–8 bytes), ever-increasing, immutable, and not derived from business data. Integer
identity columns and sequential GUIDs (`NEWSEQUENTIALID()` in SQL Server) are ideal. Avoid random GUIDs (`NEWID()`) as
clustered keys because they scatter inserts across pages, causing excessive page splits and `PAGELATCH_EX` contention
under high concurrency.

Natural keys (email, SSN, product code) are valuable as unique constraints but poor as clustered primary keys because
they are often wide, sometimes mutable, and may collide with business rule changes.

### 4.3 Data Types

- **Use the smallest appropriate data type.** `TINYINT` (0–255) instead of `INT` when the range suffices. `DATE` instead
  of `DATETIME` when you do not need time precision.
- **Use exact numeric types** (`DECIMAL`/`NUMERIC`) for monetary and financial values. Never use `FLOAT` or `REAL` for
  money.
- **Avoid `NVARCHAR(MAX)` and `VARCHAR(MAX)`** unless truly storing large text. These types cannot participate in index
  keys and force different storage behaviors.
- **Match parameter data types to column data types** exactly in queries and stored procedures. Mismatches cause
  implicit conversions that prevent index seeks (see Section 7.3 on SARGability).

### 4.4 Constraints as Business Logic Enforcers

Constraints are the first line of defense for data integrity and should be used aggressively:

- `NOT NULL` on every column that must have a value.
- `CHECK` constraints for domain validation (`CHECK (quantity > 0)`,
  `CHECK (status IN ('pending', 'active', 'closed'))`).
- `FOREIGN KEY` constraints to enforce referential integrity. Create indexes on foreign key columns to avoid table scans
  during join and delete operations.
- `UNIQUE` constraints for natural business keys.
- `DEFAULT` constraints for columns with sensible defaults (`created_at DEFAULT GETUTCDATE()`).

---

## 5. Transaction Management

### 5.1 Core Principles

- **Keep transactions as short as possible.** The longer a transaction holds locks, the more it blocks other sessions.
  Never include user interaction, network calls, or file I/O inside a transaction boundary.
- **Do only what is necessary inside the transaction.** Move read-only operations that do not require transactional
  consistency outside the `BEGIN TRAN` / `COMMIT` boundary.
- **Always explicitly handle errors and rollbacks.** Use structured error handling (`TRY...CATCH` in SQL Server,
  `BEGIN...EXCEPTION` in PostgreSQL/Oracle) to ensure that failed transactions are properly rolled back.

### 5.2 Defensive Transaction Pattern (SQL Server)

```sql
SET XACT_ABORT ON;  -- Auto-rollback on any error
SET NOCOUNT ON;     -- Suppress row count messages

BEGIN TRY
    BEGIN TRANSACTION;

    -- Debit source account
    UPDATE finance.account
    SET balance = balance - @transfer_amount
    WHERE account_id = @source_account_id;

    -- Credit destination account
    UPDATE finance.account
    SET balance = balance + @transfer_amount
    WHERE account_id = @destination_account_id;

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0
        ROLLBACK TRANSACTION;

    -- Log or re-throw
    THROW;
END CATCH;
```

Key practices:

- **`SET XACT_ABORT ON`** ensures that any runtime error automatically rolls back the entire transaction. Without it,
  certain errors leave the transaction open, leading to orphaned locks.
- **`SET NOCOUNT ON`** prevents the engine from sending `DONE_IN_PROC` messages for every statement, reducing network
  overhead in high-throughput scenarios.
- **Always check `@@TRANCOUNT`** before rolling back in the `CATCH` block to avoid errors from rolling back a
  transaction that was already rolled back.

### 5.3 Batch Processing Large Operations

Never insert, update, or delete millions of rows in a single transaction. Large transactions hold locks for extended
periods, bloat the transaction log, and may cause lock escalation to table-level locks, blocking all other activity.

Instead, batch the operation:

```sql
DECLARE @batch_size INT = 5000;
DECLARE @rows_affected INT = 1;

WHILE @rows_affected > 0
BEGIN
    DELETE TOP (@batch_size)
    FROM log.audit_entry
    WHERE created_at < DATEADD(YEAR, -2, GETUTCDATE());

    SET @rows_affected = @@ROWCOUNT;

    -- Allow other transactions to proceed between batches
    WAITFOR DELAY '00:00:00.100';
END;
```

This approach keeps each transaction small, allows checkpoint operations between batches, reduces lock contention, and
provides natural progress monitoring through the loop.

---

## 6. Isolation Levels and Concurrency Control

Choosing the right isolation level is one of the most impactful decisions in OLTP system design. The tradeoff is always
between consistency (correctness) and concurrency (throughput).

### 6.1 Isolation Level Reference

| Isolation Level                | Dirty Reads | Non-Repeatable Reads | Phantom Reads | Locking Behavior                        |
|--------------------------------|-------------|----------------------|---------------|-----------------------------------------|
| READ UNCOMMITTED               | Yes         | Yes                  | Yes           | No shared locks acquired                |
| READ COMMITTED (default)       | No          | Yes                  | Yes           | Shared locks held per statement         |
| READ COMMITTED SNAPSHOT (RCSI) | No          | Yes                  | Yes           | Row versioning, no shared locks         |
| REPEATABLE READ                | No          | No                   | Yes           | Shared locks held to end of transaction |
| SNAPSHOT                       | No          | No                   | No            | Row versioning, conflict detection      |
| SERIALIZABLE                   | No          | No                   | No            | Range locks, highest blocking           |

### 6.2 Recommendations

**READ COMMITTED SNAPSHOT ISOLATION (RCSI)** is the recommended default for most OLTP workloads. It eliminates
reader-writer blocking (readers do not block writers and vice versa), requires no application code changes from standard
`READ COMMITTED`, avoids many common deadlock patterns, and is the default in Azure SQL Database and PostgreSQL.

The cost of RCSI is additional tempdb usage (SQL Server) or vacuum overhead (PostgreSQL) for maintaining row versions.
Monitor tempdb space and version store size after enabling RCSI.

```sql
-- Enable RCSI in SQL Server (requires exclusive access)
ALTER DATABASE [YourDatabase]
SET READ_COMMITTED_SNAPSHOT ON;
```

**SNAPSHOT isolation** is appropriate when a transaction needs a consistent point-in-time view across multiple
statements (e.g., generating a report within a transaction that also writes). Unlike RCSI, SNAPSHOT detects write-write
conflicts and raises errors that the application must handle with retry logic.

**SERIALIZABLE** should be reserved for narrow, specific scenarios where phantom protection is essential (e.g.,
enforcing a business rule like "no more than 3 active subscriptions per customer" where a gap in isolation could allow a
violation). Prefer application-level checks or constraints over SERIALIZABLE where possible.

**READ UNCOMMITTED / NOLOCK** should only be used for ad-hoc diagnostic queries where correctness is irrelevant. Never
use it in production application code.

### 6.3 Optimistic vs. Pessimistic Concurrency

**Pessimistic locking** (the default in locking-based isolation levels) acquires locks preemptively to prevent
conflicts. It is appropriate when conflicts are frequent and the cost of rolling back is high.

**Optimistic concurrency control** assumes conflicts are rare and detects them at commit time. The standard pattern uses
a version column:

```sql
-- Add a version column to the table
ALTER TABLE sales.customer
ADD row_version ROWVERSION;  -- SQL Server auto-increments on every update

-- Read the customer (outside the transaction if possible)
SELECT customer_id, customer_name, email, row_version
FROM sales.customer
WHERE customer_id = @customer_id;

-- Update with optimistic concurrency check
UPDATE sales.customer
SET email = @new_email
WHERE customer_id = @customer_id
  AND row_version = @original_row_version;

-- Check if the update succeeded
IF @@ROWCOUNT = 0
BEGIN
    -- Another session modified the row; handle the conflict
    THROW 50001, 'Concurrency conflict: the record was modified by another user.', 1;
END;
```

Optimistic locking improves throughput in low-contention scenarios, reduces deadlock likelihood, and is the standard
pattern for web applications with "read-think-write" user interactions.

---

## 7. Query Optimization for OLTP

### 7.1 Indexing Strategy

Indexing is the single most impactful performance lever in OLTP systems. The goal is a minimal set of highly targeted
indexes that support the most critical query patterns.

**Clustered Index:**
Every table should have a clustered index (avoid heaps). The clustered key should be narrow (ideally 4 bytes), unique,
ever-increasing, and static (never updated). The ideal clustered key is an `INT IDENTITY` or `BIGINT IDENTITY` column.

**Nonclustered Indexes — Design Principles:**

- **Index foreign key columns.** Every foreign key column should have a nonclustered index to support join performance
  and to avoid table scans during cascading deletes/updates.
- **Index columns in `WHERE`, `JOIN`, `ORDER BY`, and `GROUP BY` clauses** of your most frequent queries.
- **Follow the "ESQ" rule for composite indexes:** Equality predicates first, then Sort columns, then range (inequality)
  predicates. This ordering maximizes the number of seek predicates.
- **Use `INCLUDE` columns for covering indexes.** Including the columns from the `SELECT` list in the index eliminates
  the need for a key lookup back to the clustered index.

```sql
-- Covering index for: SELECT order_id, total_amount
--                      FROM sales.order_header
--                      WHERE customer_id = @id AND status = 'active'
--                      ORDER BY order_date DESC
CREATE NONCLUSTERED INDEX ix_order_header_customer_status_date
ON sales.order_header (customer_id, status, order_date DESC)
INCLUDE (order_id, total_amount);
```

**Filtered Indexes (SQL Server) / Partial Indexes (PostgreSQL):**

When queries consistently filter on a fixed condition, a filtered index is smaller and faster:

```sql
-- Only index active orders (most queries filter for active)
CREATE NONCLUSTERED INDEX ix_order_header_active
ON sales.order_header (customer_id, order_date)
INCLUDE (order_id, total_amount)
WHERE status = 'active';
```

**Index Maintenance:**

- Monitor index usage via `sys.dm_db_index_usage_stats` (SQL Server) or `pg_stat_user_indexes` (PostgreSQL). Drop
  indexes that are never used for seeks or scans but are constantly updated.
- Rebuild or reorganize fragmented indexes on a schedule. For OLTP, a reorganize (online, non-blocking) at 10–30%
  fragmentation and a rebuild above 30% is a common guideline.
- Keep statistics up to date. Stale statistics cause the optimizer to generate suboptimal execution plans.

### 7.2 SARGability (Search ARGument Ability)

A predicate is SARGable when the query optimizer can use an index seek to evaluate it. Non-SARGable predicates force
index scans or table scans, destroying performance.

**Common SARGability Killers:**

```sql
-- ❌ NON-SARGABLE: Function on the indexed column
WHERE YEAR(order_date) = 2025
WHERE UPPER(customer_name) = 'SMITH'
WHERE ISNULL(discount_code, 'NONE') = 'NONE'

-- ✅ SARGABLE REWRITES:
WHERE order_date >= '2025-01-01' AND order_date < '2026-01-01'
WHERE customer_name = 'SMITH'  -- Use a case-insensitive collation or computed column
WHERE (discount_code = 'NONE' OR discount_code IS NULL)
```

```sql
-- ❌ NON-SARGABLE: Leading wildcard
WHERE product_name LIKE '%widget%'

-- ✅ SARGABLE: Trailing wildcard only
WHERE product_name LIKE 'widget%'
-- For full-text search needs, use a Full-Text Index instead.
```

```sql
-- ❌ NON-SARGABLE: Implicit type conversion
-- Column is VARCHAR, parameter is NVARCHAR
WHERE product_code = N'ABC123'

-- ✅ SARGABLE: Match the data type exactly
WHERE product_code = 'ABC123'
```

**Rule of thumb:** Never apply a function, calculation, or type conversion to an indexed column in a `WHERE`, `JOIN`, or
`ON` clause. Transform the other side of the comparison instead.

### 7.3 Parameter Sniffing

Parameter sniffing occurs when SQL Server compiles an execution plan based on the parameter values from the first
execution, then reuses that plan for all subsequent executions regardless of the parameter values passed. When data
distribution is highly skewed, a plan optimized for a "small" parameter may be catastrophic for a "large" one.

**Mitigation Strategies (in order of preference):**

1. **Proper indexing and SARGable queries** — When the optimizer has good indexes and accurate statistics, the impact of
   plan reuse is minimized because the plan works well for most parameter ranges.

2. **Update statistics regularly** — Stale statistics amplify sniffing problems. Use `AUTO_UPDATE_STATISTICS` and
   consider `AUTO_UPDATE_STATISTICS_ASYNC` for OLTP workloads to avoid synchronous stalls.

3. **`OPTION (RECOMPILE)`** — Forces a fresh plan on every execution. Best for infrequently called queries with highly
   variable parameters. Avoid on queries executing thousands of times per second due to compilation CPU cost.

4. **`OPTIMIZE FOR UNKNOWN`** — Uses average statistics density instead of sniffed values, producing a "middle of the
   road" plan.

5. **Parameter Sensitive Plan Optimization (SQL Server 2022+)** — Automatically generates multiple cached plans for
   different parameter ranges. Enabled by default at compatibility level 160.

6. **Dynamic SQL with `sp_executesql`** — Generates separate plans per distinct parameter pattern. Useful for complex
   search procedures with many optional filters.

### 7.4 Execution Plan Analysis

Always verify your query's behavior by reading its execution plan. Key things to look for:

- **Index Seeks vs. Index Scans/Table Scans:** Seeks are targeted; scans read entire indexes or tables. OLTP queries
  should seek, not scan.
- **Estimated vs. Actual Row Counts:** Large discrepancies indicate stale statistics or parameter sniffing issues.
- **Key Lookups (Bookmark Lookups):** These indicate that a nonclustered index found the rows but had to return to the
  clustered index for additional columns. Resolve by adding `INCLUDE` columns to create a covering index.
- **Sort and Hash operations with spills to tempdb:** These indicate insufficient memory grants, often caused by bad
  cardinality estimates.
- **Implicit Conversions:** Shown as `CONVERT_IMPLICIT` in the plan and `TypeConvertPreventingSeek` in SQL Server 2022+
  extended events. Fix by matching data types.

---

## 8. Deadlock Prevention and Resolution

Deadlocks occur when two or more transactions form a circular wait for resources held by each other. While the database
engine will detect and resolve deadlocks by killing one transaction (the "victim"), deadlocks degrade performance and
reliability.

### 8.1 Prevention Strategies

**Access objects in a consistent order.** If all transactions that touch both `customer` and `order_header` always
modify `customer` first, circular waits become impossible.

```sql
-- ❌ Transaction A: UPDATE customer → UPDATE order_header
-- ❌ Transaction B: UPDATE order_header → UPDATE customer
-- This creates a deadlock opportunity.

-- ✅ Both transactions: UPDATE customer → UPDATE order_header
-- Consistent ordering eliminates the cycle.
```

**Keep transactions short.** Minimize the time between `BEGIN TRAN` and `COMMIT`. Never wait for user input or external
service calls inside a transaction.

**Create proper indexes.** Without an index on the filter columns, a query may scan the entire table, acquiring locks on
every row and page. With a targeted index, the query touches only the necessary rows.

**Index foreign key columns.** When a parent row is deleted or updated, the engine must check the child table. Without
an index on the foreign key, this check scans the child table under a lock.

**Enable RCSI.** Read Committed Snapshot Isolation eliminates the most common class of deadlocks: the reader-writer
deadlock where a `SELECT` and an `UPDATE` block each other.

**Use `UPDLOCK` for read-then-update patterns.** When you must read a row and then update it within a transaction,
taking an update lock on the read prevents the classic shared-to-exclusive lock conversion deadlock:

```sql
BEGIN TRANSACTION;

SELECT @current_balance = balance
FROM finance.account WITH (UPDLOCK, ROWLOCK)
WHERE account_id = @account_id;

-- Perform business logic with @current_balance

UPDATE finance.account
SET balance = @new_balance
WHERE account_id = @account_id;

COMMIT TRANSACTION;
```

### 8.2 Queue Processing Pattern

Database-backed queues are a common source of deadlocks when multiple workers scan for the next available item. The
`READPAST` hint is essential:

```sql
-- Atomically claim the next work item, skipping locked rows
WITH cte AS (
    SELECT TOP (1) *
    FROM dbo.work_queue WITH (UPDLOCK, READPAST, ROWLOCK)
    WHERE status = 'pending'
    ORDER BY created_at
)
UPDATE cte
SET status = 'processing',
    claimed_at = GETUTCDATE(),
    claimed_by = @worker_id
OUTPUT inserted.*;
```

`READPAST` allows concurrent workers to skip rows locked by other workers, avoiding collisions. A covering index on
`(status, created_at)` is essential to prevent table scans.

### 8.3 Retry Logic

Deadlocks are a normal part of concurrent system operation. The application layer must implement retry logic:

```
-- Pseudocode
max_retries = 3
for attempt in 1..max_retries:
    try:
        execute_transaction()
        break  -- success
    catch DeadlockException:
        if attempt == max_retries:
            raise  -- give up
        wait(random_backoff(attempt))  -- exponential backoff
```

---

## 9. Advanced Query Patterns

### 9.1 Upsert (MERGE / INSERT ... ON CONFLICT)

The upsert pattern atomically inserts a row if it does not exist or updates it if it does. Each database has its
preferred syntax.

**SQL Server (MERGE):**

```sql
MERGE INTO inventory.product_stock AS target
USING (VALUES (@product_id, @warehouse_id, @quantity))
    AS source (product_id, warehouse_id, quantity)
ON target.product_id = source.product_id
   AND target.warehouse_id = source.warehouse_id
WHEN MATCHED THEN
    UPDATE SET quantity = target.quantity + source.quantity,
               updated_at = GETUTCDATE()
WHEN NOT MATCHED THEN
    INSERT (product_id, warehouse_id, quantity, created_at)
    VALUES (source.product_id, source.warehouse_id, source.quantity, GETUTCDATE());
```

**PostgreSQL (INSERT ... ON CONFLICT):**

```sql
INSERT INTO inventory.product_stock (product_id, warehouse_id, quantity, created_at)
VALUES (@product_id, @warehouse_id, @quantity, NOW())
ON CONFLICT (product_id, warehouse_id)
DO UPDATE SET
    quantity = product_stock.quantity + EXCLUDED.quantity,
    updated_at = NOW();
```

> **Caution with MERGE in SQL Server:** Always terminate `MERGE` statements with a semicolon and consider adding lock
> hints (`WITH (HOLDLOCK)`) on the target to prevent race conditions under high concurrency.

### 9.2 Pagination

**Offset-Based Pagination (simple, but degrades at deep pages):**

```sql
SELECT order_id, order_date, total_amount
FROM sales.order_header
ORDER BY order_date DESC, order_id DESC
OFFSET @page_size * (@page_number - 1) ROWS
FETCH NEXT @page_size ROWS ONLY;
```

**Keyset Pagination (consistent performance at any depth):**

```sql
SELECT TOP (@page_size)
    order_id, order_date, total_amount
FROM sales.order_header
WHERE (order_date < @last_seen_date)
   OR (order_date = @last_seen_date AND order_id < @last_seen_id)
ORDER BY order_date DESC, order_id DESC;
```

Keyset pagination is strongly preferred for OLTP APIs because it maintains constant performance regardless of page depth
and avoids the row-counting overhead of `OFFSET`.

### 9.3 Conditional Aggregation

Instead of multiple queries or self-joins for different aggregations of the same data, use conditional aggregation:

```sql
SELECT
    customer_id,
    COUNT(*) AS total_orders,
    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) AS completed_orders,
    SUM(CASE WHEN status = 'cancelled' THEN 1 ELSE 0 END) AS cancelled_orders,
    SUM(CASE WHEN order_date >= DATEADD(DAY, -30, GETUTCDATE()) THEN total_amount ELSE 0 END) AS last_30_day_revenue
FROM sales.order_header
WHERE customer_id = @customer_id
GROUP BY customer_id;
```

This executes a single scan/seek instead of four separate queries.

### 9.4 Window Functions for Running Totals and Ranking

```sql
-- Running balance for a financial ledger
SELECT
    transaction_id,
    transaction_date,
    amount,
    SUM(amount) OVER (
        PARTITION BY account_id
        ORDER BY transaction_date, transaction_id
        ROWS UNBOUNDED PRECEDING
    ) AS running_balance
FROM finance.transaction
WHERE account_id = @account_id
ORDER BY transaction_date, transaction_id;
```

Window functions avoid the need for correlated subqueries or cursors and are highly optimized in modern database
engines.

### 9.5 CTEs for Readability (Not Performance)

Common Table Expressions improve readability and maintainability but are not guaranteed to be materialized. In SQL
Server, a CTE is inlined into the main query—essentially a syntactic alias for a subquery. Do not assume a CTE executes
only once.

```sql
-- CTE for readability
WITH active_customers AS (
    SELECT customer_id, customer_name, email
    FROM sales.customer
    WHERE is_active = 1
)
SELECT
    ac.customer_name,
    COUNT(oh.order_id) AS order_count
FROM active_customers AS ac
INNER JOIN sales.order_header AS oh
    ON oh.customer_id = ac.customer_id
WHERE oh.order_date >= '2025-01-01'
GROUP BY ac.customer_name;
```

For scenarios where you need a CTE's result set to be materialized (evaluated once and cached), use a temporary table
instead.

### 9.6 Avoiding Cursors and Row-by-Row Processing

Cursors process one row at a time and are almost always slower than set-based alternatives. Replace cursor logic with
set-based operations:

```sql
-- ❌ Cursor approach (slow)
DECLARE order_cursor CURSOR FOR
    SELECT order_id FROM sales.order_header WHERE status = 'pending';
OPEN order_cursor;
FETCH NEXT FROM order_cursor INTO @order_id;
WHILE @@FETCH_STATUS = 0
BEGIN
    EXEC usp_process_order @order_id;
    FETCH NEXT FROM order_cursor INTO @order_id;
END;
CLOSE order_cursor;
DEALLOCATE order_cursor;

-- ✅ Set-based approach (fast)
UPDATE sales.order_header
SET status = 'processing',
    processed_at = GETUTCDATE()
OUTPUT inserted.order_id, inserted.status
WHERE status = 'pending';
```

If row-by-row processing is truly unavoidable (e.g., calling an external stored procedure per row), consider batching or
using `FAST_FORWARD` read-only cursors, which are significantly faster than the default keyset cursors.

---

## 10. Stored Procedure Best Practices

### 10.1 Structure

```sql
CREATE OR ALTER PROCEDURE sales.usp_create_order
    @customer_id    INT,
    @order_date     DATE = NULL,  -- Defaults to today
    @order_id       INT OUTPUT
AS
BEGIN
    SET XACT_ABORT ON;
    SET NOCOUNT ON;

    -- Default parameter values
    SET @order_date = COALESCE(@order_date, CAST(GETUTCDATE() AS DATE));

    -- Input validation
    IF NOT EXISTS (SELECT 1 FROM sales.customer WHERE customer_id = @customer_id)
    BEGIN
        THROW 50010, 'Customer not found.', 1;
        RETURN;
    END;

    BEGIN TRY
        BEGIN TRANSACTION;

        INSERT INTO sales.order_header (customer_id, order_date, status, created_at)
        VALUES (@customer_id, @order_date, 'pending', GETUTCDATE());

        SET @order_id = SCOPE_IDENTITY();

        COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0
            ROLLBACK TRANSACTION;
        THROW;
    END CATCH;
END;
```

### 10.2 Guidelines

- **Validate inputs early** and fail fast with descriptive error messages.
- **Use `SCOPE_IDENTITY()`** (not `@@IDENTITY`) to retrieve the last inserted identity value within the current scope.
- **Avoid dynamic SQL unless necessary.** When dynamic SQL is required (e.g., dynamic search with optional filters),
  always use parameterized `sp_executesql` to prevent SQL injection and promote plan reuse.
- **Avoid scalar user-defined functions in queries.** Scalar UDFs in `SELECT`, `WHERE`, and `JOIN` clauses are executed
  once per row, creating hidden RBAR (Row-By-Agonizing-Row) processing. Use inline table-valued functions instead, which
  the optimizer can fold into the query plan.
- **Use `EXISTS` instead of `COUNT`** when checking for the presence of rows. `EXISTS` short-circuits after finding the
  first match.

```sql
-- ❌ Slow: Counts all matching rows
IF (SELECT COUNT(*) FROM sales.order_header WHERE customer_id = @id) > 0

-- ✅ Fast: Stops at first match
IF EXISTS (SELECT 1 FROM sales.order_header WHERE customer_id = @id)
```

---

## 11. Connection and Resource Management

### 11.1 Connection Pooling

Every database connection consumes memory and file descriptors. Opening and closing connections per query is
prohibitively expensive. Always use connection pooling (built into ADO.NET, JDBC, pgBouncer, etc.).

### 11.2 Timeouts

Set appropriate command timeouts at the application level. A query that should complete in 100ms should not be allowed
to run for 30 seconds holding locks. Typical OLTP command timeouts are 5–15 seconds.

### 11.3 Connection Lifetime

Close connections (return them to the pool) as soon as the unit of work is complete. Holding connections open across
user think-time exhausts the pool.

---

## 12. Monitoring and Diagnostics

### 12.1 Key Metrics to Track

- **Transaction throughput** (transactions per second).
- **Average and P99 query duration.**
- **Lock wait time and blocking chains.**
- **Deadlock frequency and patterns.**
- **Buffer cache hit ratio** (should be >99% for OLTP).
- **Page life expectancy** (indicates memory pressure).
- **Transaction log growth and checkpoint frequency.**

### 12.2 Essential DMVs (SQL Server)

```sql
-- Top 20 queries by average duration
SELECT TOP 20
    qs.total_elapsed_time / qs.execution_count AS avg_elapsed_time_us,
    qs.execution_count,
    qs.total_logical_reads / qs.execution_count AS avg_logical_reads,
    SUBSTRING(st.text, (qs.statement_start_offset / 2) + 1,
        (CASE qs.statement_end_offset
            WHEN -1 THEN DATALENGTH(st.text)
            ELSE qs.statement_end_offset
        END - qs.statement_start_offset) / 2 + 1) AS query_text
FROM sys.dm_exec_query_stats AS qs
CROSS APPLY sys.dm_exec_sql_text(qs.sql_handle) AS st
ORDER BY avg_elapsed_time_us DESC;

-- Current blocking chains
SELECT
    blocking.session_id AS blocking_session,
    blocked.session_id AS blocked_session,
    blocked.wait_type,
    blocked.wait_time,
    st.text AS blocked_query
FROM sys.dm_exec_requests AS blocked
INNER JOIN sys.dm_exec_sessions AS blocking
    ON blocking.session_id = blocked.blocking_session_id
CROSS APPLY sys.dm_exec_sql_text(blocked.sql_handle) AS st
WHERE blocked.blocking_session_id <> 0;
```

### 12.3 Query Store

Enable Query Store (SQL Server 2016+, Azure SQL Database) to capture query plans, execution statistics, and regressions
over time. It provides the ability to force specific plans for problematic queries, identify regressed queries after
upgrades or statistics updates, track query performance trends, and apply Query Store hints when application code cannot
be modified.

```sql
ALTER DATABASE [YourDatabase]
SET QUERY_STORE = ON (
    OPERATION_MODE = READ_WRITE,
    MAX_STORAGE_SIZE_MB = 1000,
    INTERVAL_LENGTH_MINUTES = 30,
    QUERY_CAPTURE_MODE = AUTO
);
```

---

## 13. Security Practices in Transactional SQL

- **Never concatenate user input into SQL strings.** Always use parameterized queries or stored procedures.
- **Apply the principle of least privilege.** Application service accounts should have only the permissions they need (
  `EXECUTE` on procedures, `SELECT/INSERT/UPDATE/DELETE` on specific tables through schemas).
- **Use schema separation** to group related objects and apply permissions at the schema level.
- **Encrypt sensitive data** at rest (Transparent Data Encryption) and in transit (TLS).
- **Audit data access** to sensitive tables using database audit features or change data capture.

---

## 14. Anti-Patterns Reference

| Anti-Pattern                          | Problem                                               | Remedy                                          |
|---------------------------------------|-------------------------------------------------------|-------------------------------------------------|
| `SELECT *`                            | Reads unnecessary columns, breaks covering indexes    | List explicit columns                           |
| Functions on indexed columns in WHERE | Prevents index seeks (non-SARGable)                   | Rewrite predicate to keep column clean          |
| Implicit type conversions             | Prevents index seeks, hidden performance killer       | Match parameter types to column types exactly   |
| Missing semicolons                    | Deprecated syntax, ambiguous parsing                  | Terminate every statement with `;`              |
| `sp_` prefix on user procedures       | SQL Server searches master DB first                   | Use `usp_` or no prefix                         |
| Cursors for set-based problems        | Row-by-row processing, orders of magnitude slower     | Rewrite as set-based operations                 |
| Long-running transactions             | Lock contention, log growth, blocking                 | Keep transactions short, batch large operations |
| Over-indexing                         | Slows writes, wastes storage, complicates maintenance | Monitor usage, drop unused indexes              |
| `NOLOCK` in production queries        | Reads dirty, uncommitted, or partially written data   | Use RCSI instead                                |
| Scalar UDFs in queries                | Hidden RBAR execution, cannot be parallelized         | Use inline table-valued functions               |
| `OFFSET` at deep page depths          | Scans and discards rows up to offset                  | Use keyset pagination                           |
| `OR` on different columns in WHERE    | Often prevents index seeks                            | Split into `UNION ALL` of two indexed queries   |
| `NOT IN` with NULLable column         | Returns no rows if any NULL exists in subquery        | Use `NOT EXISTS` instead                        |

---

## 15. Checklist: Before Deploying to Production

1. **All queries use explicit column lists** (no `SELECT *`).
2. **All `WHERE` and `JOIN` predicates are SARGable.**
3. **Data types in parameters match column data types exactly.**
4. **Every foreign key column has an index.**
5. **Critical queries have covering indexes verified via execution plans.**
6. **Transactions are as short as possible with proper error handling.**
7. **Large data operations are batched.**
8. **RCSI or appropriate isolation level is enabled.**
9. **Application has retry logic for deadlocks and transient errors.**
10. **Query Store is enabled and monitored.**
11. **Statistics are set to auto-update.**
12. **Connection pooling is configured.**
13. **No scalar UDFs in query predicates or SELECT lists.**
14. **All procedures use `SET XACT_ABORT ON` and `SET NOCOUNT ON`.**
15. **Security: all queries are parameterized, service accounts have least privilege.**

---

*Last updated: March 2026. Covers SQL Server 2019/2022/2025, PostgreSQL 15+, and general ANSI SQL principles.*
