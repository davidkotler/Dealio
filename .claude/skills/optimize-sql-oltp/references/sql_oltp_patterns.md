# The definitive guide to SQL best practices for OLTP systems

**Every OLTP system lives or dies by how well its SQL is written, its transactions managed, and its indexes designed.** This guide synthesizes recommendations from Microsoft's official documentation, PostgreSQL docs, Oracle guidance, and leading experts—Brent Ozar, Kimberly Tripp (SQLskills), Erland Sommarskog, Aaron Bertrand, Joe Celko, and Bill Karwin—into a single authoritative reference. It covers naming conventions, query patterns, transaction isolation, indexing, schema design, stored procedures, advanced techniques, performance tuning, anti-patterns, and cross-platform differences. The principles here apply across SQL Server, PostgreSQL, MySQL, and Oracle, with platform-specific guidance noted throughout.

---

## 1. SQL coding standards and naming conventions

### Table and column naming

The singular-vs-plural debate has two authoritative camps: the ISO 11179 standard and most SQL Server DBAs prefer **singular** (`Customer`, `Order`), reasoning that each row represents one entity. Joe Celko advocates **plural** (`Customers`, `Orders`), arguing tables represent sets. The critical rule is consistency—pick one convention and enforce it database-wide.

Avoid Hungarian notation prefixes like `tbl_` or `vw_`. Phil Factor (Red Gate) notes: "This 'reverse-Hungarian' notation has never been a standard for SQL. The type of every object is already available in `sys.objects`." Use schemas for organization instead:

```sql
-- Use schemas, not prefixes
CREATE TABLE sales.Customer (...);
CREATE TABLE hr.Employee (...);
CREATE TABLE inventory.Product (...);
```

Column names should be descriptive and consistent. Use suffixes like `_id` for keys, `_at` for timestamps, `_count` for tallies, and `is_`/`has_` prefixes for booleans. Foreign key columns should reference the parent table: `customer_id` references `Customer(customer_id)`. Avoid ambiguous names like `id` (becomes confusing in JOINs) or cryptic abbreviations like `CrtDt`.

### Case conventions by platform

| Platform | Convention | Example |
|---|---|---|
| **SQL Server** | PascalCase | `CustomerOrder`, `OrderDate` |
| **PostgreSQL** | snake_case | `customer_order`, `order_date` |
| **MySQL** | snake_case | `customer_order` (case-sensitive on Linux) |
| **Oracle** | UPPER_SNAKE | Stores unquoted identifiers as uppercase |

**Never use double-quoted mixed-case identifiers in PostgreSQL**—`"CustomerOrder"` forces perpetual quoting in every query. PostgreSQL folds unquoted identifiers to lowercase.

### Index, constraint, and object naming

Consistent prefixes make indexes and constraints immediately identifiable:

```sql
-- Primary Key: PK_{Table}
CONSTRAINT PK_Customer PRIMARY KEY CLUSTERED (customer_id)

-- Foreign Key: FK_{Child}_{Parent}
CONSTRAINT FK_OrderItem_Order FOREIGN KEY (order_id) REFERENCES Order(order_id)

-- Non-Clustered Index: IX_{Table}_{Column(s)}
CREATE NONCLUSTERED INDEX IX_Order_CustomerID ON Order (customer_id);

-- Unique: UQ_{Table}_{Column}
CREATE UNIQUE INDEX UQ_Customer_Email ON Customer (email_address);

-- Check: CK_{Table}_{Rule}; Default: DF_{Table}_{Column}
CONSTRAINT CK_OrderItem_Quantity CHECK (quantity > 0)
```

### The sp_ prefix trap in SQL Server

Never prefix stored procedures with `sp_` in SQL Server. The `sp_` prefix designates system procedures, and **SQL Server always checks the master database first** for any `sp_`-prefixed procedure—even with database qualification. This causes `SP:CacheMiss` events and measurable performance degradation. If a user procedure name collides with a system procedure, the system procedure always wins. Use `usp_` or schema-qualified names instead: `sales.GetCustomerOrders`.

### Reserved word avoidance and schema organization

Common traps include `User`, `Order`, `Date`, `Time`, `Index`, `Name`, `Status`, `Type`, `Key`, and `Value`. Qualify with descriptors: `user_name` not `name`, `order_status` not `status`. Schemas provide natural security boundaries with schema-level permission grants, eliminating table-by-table security management:

```sql
GRANT SELECT ON SCHEMA::reporting TO [ReportingUsers];
GRANT EXECUTE ON SCHEMA::sales TO [SalesAppRole];
DENY SELECT ON SCHEMA::hr TO [SalesAppRole];
```

### Code formatting conventions

Use **uppercase keywords**, one column per line in SELECT, explicit `AS` for aliases, explicit JOIN syntax (never comma joins), and meaningful aliases (`c` for Customer, not `t1`). Indent JOIN conditions consistently.

---

## 2. Query writing best practices for OLTP

### Why SELECT * destroys OLTP performance

Always specify explicit column lists. SELECT * causes **network overhead** from unnecessary data transfer, **invalidates covering indexes** by forcing key lookups, **breaks schema-bound views** when columns change, and inflates memory grants for sorting and hashing. In OLTP systems where queries execute millions of times daily, these costs compound dramatically.

### SARGable predicates are non-negotiable

**SARGable** (Search ARGument Able) predicates allow index seeks. Non-SARGable predicates force full scans—the single most common cause of slow OLTP queries.

```sql
-- ❌ NON-SARGABLE: Function wrapping column prevents index use
WHERE YEAR(OrderDate) = 2024
WHERE DATEADD(day, 30, OrderDate) > GETDATE()
WHERE LEFT(DisplayName, 4) = 'Mary'

-- ✅ SARGABLE: Clean column enables index seek
WHERE OrderDate >= '2024-01-01' AND OrderDate < '2025-01-01'
WHERE OrderDate > DATEADD(day, -30, GETDATE())
WHERE DisplayName LIKE 'Mary%'
```

SARGable operators include `=`, `>`, `>=`, `<`, `<=`, `BETWEEN`, `IN`, and `LIKE 'prefix%'`. Any function wrapping a column—`YEAR()`, `MONTH()`, `CONVERT()`, `ISNULL()`, `COALESCE()`—renders the predicate non-SARGable. Arithmetic on columns (`salary * 1.1 > 50000`) should be rewritten to isolate the column (`salary > 50000 / 1.1`).

### Implicit conversions: the silent performance killer

When data types mismatch in WHERE or JOIN conditions, SQL Server silently converts the lower-precedence type. If that's the *column*, **every row** must be converted, turning seeks into scans. ADO.NET sends .NET strings as NVARCHAR by default—if the column is VARCHAR, the entire index is scanned:

```sql
-- ❌ VARCHAR column compared to NVARCHAR literal → full scan
SELECT * FROM Products WHERE ProductCode = N'ABC123';

-- ✅ Matching types → index seek
SELECT * FROM Products WHERE ProductCode = 'ABC123';
```

One customer went from **70% CPU to under 5%** by fixing implicit conversions. Execution plans show a yellow warning triangle with `CONVERT_IMPLICIT`. Detect them by querying the plan cache for plans containing `CONVERT_IMPLICIT`.

### EXISTS vs IN vs JOIN

For **existence checks**, `EXISTS` short-circuits on the first match and is generally preferred. For **anti-joins** (finding non-matches), always use `NOT EXISTS`—`NOT IN` returns zero rows when the subquery contains NULLs (because `x NOT IN (1, NULL)` evaluates to UNKNOWN). For queries **needing columns from both tables**, use JOIN. Modern optimizers often generate identical plans for IN and EXISTS on NOT NULL columns, but NOT EXISTS is always safer for anti-patterns.

### CTEs vs subqueries vs temp tables

CTEs in SQL Server are **syntactic sugar—not materialized**. The optimizer inlines them, meaning a CTE referenced multiple times executes multiple times. When cardinality estimation errors propagate through nested CTEs, performance degrades exponentially. Brent Ozar's guidance: "Start with CTEs because they're easy to write. If you hit a performance wall, try ripping out a CTE and writing it to a temp table." Temp tables create **optimization fences** that reset the optimizer's estimates, have full statistics and indexes, and can be queried repeatedly without re-execution.

### Efficient DML for OLTP

**Updates** should include a change-detection predicate to avoid unnecessary log writes and index maintenance: `UPDATE Customers SET Email = @NewEmail WHERE CustomerID = @ID AND (Email <> @NewEmail OR Email IS NULL)`.

**Batch deletes** prevent lock escalation, log bloat, and blocking. Never delete millions of rows in a single transaction:

```sql
DECLARE @BatchSize INT = 5000;
WHILE (1=1)
BEGIN
    DELETE TOP (@BatchSize) FROM BigTable WHERE CreatedDate < '2024-01-01';
    IF @@ROWCOUNT < @BatchSize BREAK;
    WAITFOR DELAY '00:00:01'; -- Allow other transactions through
END;
```

**Parameterized queries** via `sp_executesql` prevent SQL injection, enable plan caching, and reduce compilation overhead. Never concatenate user input into dynamic SQL strings.

---

## 3. Transaction management best practices

### Isolation levels shape OLTP behavior

The choice of isolation level is the most impactful decision for OLTP concurrency. Each level trades consistency guarantees against throughput:

| Isolation Level | Dirty Read | Non-Repeatable Read | Phantom Read | Implementation |
|---|---|---|---|---|
| READ UNCOMMITTED | Possible | Possible | Possible | No shared locks |
| READ COMMITTED | Prevented | Possible | Possible | Lock-based (SQL Server) or MVCC (PostgreSQL) |
| REPEATABLE READ | Prevented | Prevented | Possible* | Shared locks held to EOT (SQL Server) |
| SNAPSHOT | Prevented | Prevented | Prevented | Row versioning; update conflict detection |
| SERIALIZABLE | Prevented | Prevented | Prevented | Key-range locks (SQL Server) or SSI (PostgreSQL) |

*PostgreSQL's REPEATABLE READ is actually Snapshot Isolation, which also prevents phantoms.

The most important practical recommendation: **enable Read Committed Snapshot Isolation (RCSI)** in SQL Server (`ALTER DATABASE MyDB SET READ_COMMITTED_SNAPSHOT ON`). This converts READ COMMITTED from lock-based to MVCC-based, so **readers never block writers and writers never block readers**—the same behavior PostgreSQL provides by default. RCSI is the default in Azure SQL Database for good reason.

### Deadlock prevention strategies

Deadlocks occur when two transactions hold locks that the other needs. Prevention follows four principles: **access objects in a consistent order** across all transactions, **keep transactions short** (no user interaction, no external API calls), use the **UPDLOCK hint** in SQL Server to prevent S→X conversion deadlocks, and set **lock timeouts** to prevent indefinite waits.

Monitor deadlocks via Extended Events in SQL Server (`sqlserver.xml_deadlock_report`) or `pg_locks` and `log_lock_waits = on` in PostgreSQL. When a deadlock occurs, the victim should retry with **exponential backoff** (delay = 2^attempt + random jitter) for a maximum of 3–5 attempts:

```sql
-- SQL Server retry pattern
DECLARE @retries INT = 0;
WHILE @retries < 3
BEGIN
    BEGIN TRY
        BEGIN TRANSACTION;
            -- business logic here
        COMMIT TRANSACTION;
        BREAK;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
        IF ERROR_NUMBER() = 1205 -- Deadlock
        BEGIN
            SET @retries += 1;
            IF @retries >= 3 THROW;
            WAITFOR DELAY '00:00:00.100';
        END
        ELSE THROW;
    END CATCH;
END;
```

### Lock escalation management

SQL Server escalates row locks to table locks at approximately **5,000 locks** per index/heap per statement, or when lock memory exceeds 40% of allocated lock memory. For high-concurrency OLTP tables, control this with `ALTER TABLE SET (LOCK_ESCALATION = DISABLE)` or use trace flag **1224** (disables count-based escalation, preserves memory-pressure escalation). PostgreSQL does not have lock escalation—it maintains row-level locks regardless of count.

### Optimistic vs pessimistic concurrency

Use **pessimistic locking** (`SELECT FOR UPDATE` in PostgreSQL, `WITH (UPDLOCK, ROWLOCK)` in SQL Server) when contention is high and conflicts are expensive. Use **optimistic locking** (rowversion columns, conditional updates) when reads dominate and conflicts are rare. Most production systems use a hybrid: RCSI for read concurrency plus targeted UPDLOCK for critical write paths.

```sql
-- Optimistic: rowversion-based conflict detection (SQL Server)
UPDATE Products SET Price = @NewPrice
WHERE ProductID = @ID AND RowVer = @OriginalRowVer;
IF @@ROWCOUNT = 0
    RAISERROR('Concurrency conflict', 16, 1);
```

### Savepoints and nested transaction gotchas

SQL Server has **no true nested transactions**. Each `BEGIN TRAN` increments `@@TRANCOUNT`, but `ROLLBACK` (without a savepoint name) always resets `@@TRANCOUNT` to 0 and rolls back everything—inner `COMMIT` only decrements the counter. Use `SAVE TRANSACTION` for partial rollback capability. PostgreSQL's EXCEPTION blocks implicitly create savepoints, but each block with DML consumes a transaction ID even on rollback—avoid in tight loops.

### The essential error handling template

```sql
CREATE PROCEDURE dbo.TransferFunds
    @FromAccount INT, @ToAccount INT, @Amount DECIMAL(18,2)
AS
SET XACT_ABORT, NOCOUNT ON;
BEGIN TRY
    BEGIN TRANSACTION;
        UPDATE Accounts SET Balance = Balance - @Amount WHERE AccountID = @FromAccount;
        UPDATE Accounts SET Balance = Balance + @Amount WHERE AccountID = @ToAccount;
    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    INSERT INTO ErrorLog (ErrorNumber, ErrorMessage, ErrorTime)
    VALUES (ERROR_NUMBER(), ERROR_MESSAGE(), SYSUTCDATETIME());
    THROW;
END CATCH;
```

**`SET XACT_ABORT ON` is non-negotiable.** Without it, some errors fail only the statement, leaving the transaction open with partial changes. With XACT_ABORT, virtually all runtime errors doom the transaction. Always check `XACT_STATE()` before rollback: a value of `-1` means the transaction is already doomed.

---

## 4. Indexing strategies that make or break OLTP

### Clustered index design follows the NUSE rule

In SQL Server, the clustered index **is** the table—its leaf level contains the actual data rows. Per Kimberly Tripp (SQLskills), the ideal clustered key is **Narrow, Unique, Static, and Ever-increasing** (NUSE). INT IDENTITY is ideal. Every non-clustered index stores the clustering key as its row locator, so a wide clustering key bloats *all* indexes. PostgreSQL always uses a heap with separate B-tree indexes—there is no clustered index equivalent, though the `CLUSTER` command can physically reorder rows once.

### Covering indexes eliminate key lookups

A **covering index** contains all columns a query needs, eliminating expensive bookmark lookups to the base table. The `INCLUDE` clause stores non-key columns at the leaf level only, without bloating B-tree intermediate pages:

```sql
-- Query needs Email (for seeking) plus FirstName, LastName (for output)
CREATE NONCLUSTERED INDEX IX_Cust_Email
ON Customers (Email) INCLUDE (FirstName, LastName);
```

In real-world testing (Red Gate Simple Talk), adding a single INCLUDE column made a query **184x faster** by eliminating key lookups. Only columns used in WHERE/ORDER BY/JOIN should be key columns; columns only in SELECT belong in INCLUDE.

### Composite index column ordering: the ESR rule

For composite indexes, place **Equality** predicates first, **Sort** columns next, and **Range** predicates last. This rule (Equality, Sort, Range) maximizes the index's utility:

```sql
-- Query: WHERE customer_id = 123 AND order_date > '2024-01-01' ORDER BY amount DESC
CREATE INDEX IX_Orders_ESR ON Orders (customer_id, amount DESC, order_date);
--                                    ^Equality    ^Sort         ^Range
```

The "most selective column first" myth is debunked by Markus Winand (Use The Index Luke): "It was never a sensible rule of thumb." Equality predicates narrow the B-tree range; sort columns avoid in-memory sorts; range predicates filter without breaking sort order.

### Index maintenance: modern perspective

Brent Ozar's research concludes that **on modern SSDs and SANs, fragmentation matters far less than commonly believed**. Shared storage makes all I/O effectively random anyway. The real benefit of REBUILD is often the **statistics update and plan recompilation**, not physical defragmentation. Recommended approach: use Ola Hallengren's IndexOptimize scripts with high thresholds (50% for reorganize, 80–90% for rebuild), and always run statistics updates separately.

### Filtered indexes for common OLTP patterns

Filtered (partial) indexes index only a subset of rows, making them perfect for soft-delete patterns or status columns where queries target a small subset:

```sql
-- SQL Server: index only active orders
CREATE INDEX IX_Orders_Active ON Orders (OrderDate DESC)
INCLUDE (CustomerID) WHERE is_deleted = 0;

-- PostgreSQL: partial index
CREATE INDEX idx_orders_active ON orders (order_date DESC)
WHERE is_deleted = false;
```

**Caveat**: parameterized SQL won't match the filter predicate unless `OPTION(RECOMPILE)` is used. Filtered indexes also require `QUOTED_IDENTIFIER ON` and `ANSI_NULLS ON`.

### Detecting unused and missing indexes

```sql
-- SQL Server: find indexes with high writes but zero reads
SELECT OBJECT_NAME(i.object_id) AS TableName, i.name AS IndexName,
    ius.user_seeks, ius.user_scans, ius.user_updates
FROM sys.dm_db_index_usage_stats ius
JOIN sys.indexes i ON ius.object_id = i.object_id AND ius.index_id = i.index_id
WHERE (ius.user_seeks + ius.user_scans + ius.user_lookups) = 0
  AND ius.user_updates > 0
ORDER BY ius.user_updates DESC;
```

Monitor over a **full business cycle** before dropping indexes—an index may appear unused but be critical for a monthly report. Unique indexes may show zero reads but enforce constraints.

---

## 5. Schema design patterns for transactional databases

### Normalize to 3NF, then denormalize with evidence

OLTP databases should start at **Third Normal Form (3NF)**: eliminate repeating groups (1NF), remove partial dependencies on composite keys (2NF), and remove transitive dependencies (3NF). Higher normal forms (BCNF, 4NF, 5NF) address rare edge cases involving multiple candidate keys and multi-valued dependencies.

Denormalize only with **measured evidence** of performance problems. Common justified denormalizations include cached calculated aggregates (`order_total` maintained by triggers), read-heavy lookup denormalization where join cost exceeds storage cost, and materialized views for complex reporting queries.

### Surrogate keys win for OLTP performance

**INT IDENTITY** or SEQUENCE columns are ideal clustered keys: 4 bytes, ever-increasing, minimal fragmentation. Random GUIDs (`NEWID()`) as clustered keys cause **83%+ fragmentation** and over 300 page splits per second with 1M rows. GUIDs are 16 bytes—4x wider than INT—rippling through every non-clustered index. One practitioner reported **88% read performance improvement** after removing GUID primary keys from a 2-billion-row table.

If GUIDs are needed for distributed uniqueness, separate the clustered key from the logical key:

```sql
CREATE TABLE Customer (
    row_id       INT IDENTITY(1,1) NOT NULL,          -- Clustered key
    customer_uid UNIQUEIDENTIFIER DEFAULT NEWID(),     -- Logical PK
    CONSTRAINT PK_Customer PRIMARY KEY CLUSTERED (row_id),
    CONSTRAINT UQ_Customer_UID UNIQUE NONCLUSTERED (customer_uid)
);
```

### Soft delete patterns and their pitfalls

Use `deleted_at DATETIME2 NULL` (timestamp) over a boolean `is_deleted` flag—it captures when deletion occurred. Always create **filtered indexes** on active records (`WHERE deleted_at IS NULL`). Unique constraints break with soft deletes: a deleted user's email blocks re-registration. Fix with partial unique indexes. Every query needs filtering, creating a high risk of forgotten filters—mitigate with views or ORM default scopes.

**Recommended two-stage approach**: soft-delete first (30-day grace period for undo), then a nightly job permanently removes records past retention, balancing recoverability with GDPR compliance.

### Temporal tables for automatic history

SQL Server 2016+ provides system-versioned temporal tables that automatically maintain history with zero application changes:

```sql
CREATE TABLE hr.Employee (
    employee_id INT PRIMARY KEY,
    name NVARCHAR(100), salary DECIMAL(10,2),
    valid_from DATETIME2 GENERATED ALWAYS AS ROW START HIDDEN NOT NULL,
    valid_to   DATETIME2 GENERATED ALWAYS AS ROW END HIDDEN NOT NULL,
    PERIOD FOR SYSTEM_TIME (valid_from, valid_to)
) WITH (SYSTEM_VERSIONING = ON (HISTORY_TABLE = hr.Employee_History));

-- Point-in-time query
SELECT * FROM hr.Employee FOR SYSTEM_TIME AS OF '2025-06-15' WHERE employee_id = 1000;
```

Temporal tables add **5–20% write overhead**. For very high-write tables, history tables grow quickly—use retention policies and partitioning.

### Avoid EAV in OLTP systems

The Entity-Attribute-Value pattern stores all attributes as rows (`entity_id, attribute_name, value VARCHAR`). Joe Celko calls it "common enough to have a name—like 'cancer.'" It destroys **type safety** (everything is a string), prevents **referential integrity**, requires **N self-joins** to query N attributes, and multiplies write overhead by the number of attributes per entity. Better alternatives: **JSONB columns** with GIN indexes (PostgreSQL), **sparse columns** (SQL Server), or proper **table-per-type decomposition**.

### Polymorphic associations done right

The anti-pattern stores `commentable_type VARCHAR` and `commentable_id INT` in a single column—making foreign key enforcement impossible. Bill Karwin's recommended solution is **Class Table Inheritance** with a shared super-type table:

```sql
CREATE TABLE content (content_id INT IDENTITY PRIMARY KEY, content_type VARCHAR(20));
CREATE TABLE article (content_id INT PRIMARY KEY REFERENCES content, title VARCHAR(255));
CREATE TABLE video  (content_id INT PRIMARY KEY REFERENCES content, url VARCHAR(500));
CREATE TABLE comment (comment_id INT PRIMARY KEY,
    content_id INT REFERENCES content, body TEXT); -- Real FK!
```

GitLab's engineering guidance explicitly states: "Always use separate tables instead of polymorphic associations."

---

## 6. Stored procedure and function best practices

### SET NOCOUNT ON and XACT_ABORT ON are mandatory

`SET NOCOUNT ON` suppresses "N rows affected" messages that applications like .NET, pyodbc, and Tableau can misinterpret as result sets. `SET XACT_ABORT ON` ensures all runtime errors doom the transaction and abort the batch—without it, some errors leave transactions open with partial changes and held locks.

### Parameter sniffing: diagnosis and solutions

SQL Server compiles and caches execution plans based on the **first execution's parameter values**. With skewed data (99% of rows matching one value, <1% matching another), the cached plan may be catastrophically wrong for subsequent executions. Erik Darling demonstrates this with VoteTypeId columns where value distribution spans 5 orders of magnitude.

Solutions ranked by preference: **OPTION(RECOMPILE)** forces a fresh plan (costs CPU but guarantees optimal plan), **OPTIMIZE FOR UNKNOWN** uses average statistics, **dynamic SQL with conditional RECOMPILE** targets known problematic values, and **plan guides** apply hints without code modification. PostgreSQL handles this differently—after 5 executions, it chooses between generic and custom plans automatically.

### Dynamic SQL: sp_executesql is the only safe option

`sp_executesql` provides **strongly-typed parameters** (preventing injection), **plan caching** (like stored procedures), and **plan reuse** across executions. `EXEC()` concatenates strings with no parameterization, no plan reuse, and full SQL injection vulnerability. Always use `QUOTENAME()` for dynamic table/column names.

For **kitchen-sink queries** (dynamic search conditions), build the SQL string conditionally and always append `OPTION(RECOMPILE)`:

```sql
DECLARE @sql NVARCHAR(MAX) = N'SELECT * FROM Orders WHERE 1=1';
IF @OrderDate IS NOT NULL SET @sql += N' AND OrderDate = @OrderDate';
IF @CustomerID IS NOT NULL SET @sql += N' AND CustomerID = @CustomerID';
SET @sql += N' OPTION(RECOMPILE)';
EXEC sp_executesql @sql, N'@OrderDate DATE, @CustomerID INT', @OrderDate, @CustomerID;
```

### Scalar UDFs are a performance disaster (pre-2019)

Scalar user-defined functions in SQL Server execute **once per row** (RBAR—Row By Agonizing Row), force serial execution, and hide their cost from the optimizer. Per SQL Shack, **75% of query time** can be consumed invoking the scalar function. SQL Server 2019+ introduced **Scalar UDF Inlining**, which transforms eligible UDFs into subqueries folded into the execution plan. Inline TVFs (table-valued functions) remain the best-performing option—they're treated as parameterized views by the optimizer.

PostgreSQL's function **volatility categories** (IMMUTABLE, STABLE, VOLATILE) control optimization. IMMUTABLE functions can be pre-evaluated at plan time with constant arguments. Mislabeling a VOLATILE function as IMMUTABLE causes stale cached results.

---

## 7. Advanced OLTP patterns and techniques

### MERGE has a long history of bugs

SQL Server's MERGE statement suffers from **race conditions without HOLDLOCK** (concurrent sessions cause PK violations), numerous documented bugs (Aaron Bertrand compiled a comprehensive list), and **severe blocking** when HOLDLOCK is applied (range locks in high-concurrency scenarios). PostgreSQL's `INSERT ... ON CONFLICT` and MySQL's `INSERT ... ON DUPLICATE KEY UPDATE` are cleaner, atomic alternatives:

```sql
-- PostgreSQL: atomic upsert
INSERT INTO products (product_id, price) VALUES (123, 29.99)
ON CONFLICT (product_id) DO UPDATE SET price = EXCLUDED.price;

-- SQL Server safe alternative: UPDATE then INSERT with explicit locking
BEGIN TRAN;
UPDATE Products WITH (UPDLOCK, SERIALIZABLE) SET Price = @Price WHERE ProductID = @ID;
IF @@ROWCOUNT = 0
    INSERT INTO Products (ProductID, Price) VALUES (@ID, @Price);
COMMIT;
```

### Queue-based processing with SKIP LOCKED

PostgreSQL's `FOR UPDATE SKIP LOCKED` (9.5+, also MySQL 8+) enables zero-contention queue processing. Each worker locks and dequeues one job; other workers automatically skip locked rows. If a worker crashes, the transaction rolls back and the job returns to the queue. SQL Server achieves similar behavior with `READPAST`:

```sql
-- PostgreSQL queue dequeue
BEGIN;
WITH next_job AS (
    SELECT id FROM job_queue WHERE status = 'pending'
    ORDER BY created_at LIMIT 1 FOR UPDATE SKIP LOCKED
)
UPDATE job_queue SET status = 'in_progress'
FROM next_job WHERE job_queue.id = next_job.id
RETURNING job_queue.*;
COMMIT;
```

### Idempotent operations are essential for reliability

Every operation that might be retried (deadlocks, timeouts, network failures) must be **idempotent**. Use idempotency keys: `INSERT INTO processed_events (event_id) VALUES (@key) ON CONFLICT DO NOTHING`—if the insert succeeds, proceed; if it conflicts, the operation was already applied. Conditional updates with version columns (`WHERE version = @expected`) are naturally idempotent.

### Sequence objects vs IDENTITY

SEQUENCE objects (SQL Server 2012+, PostgreSQL, Oracle) offer cross-table usage, preallocated ranges, cycling, and independence from table operations. IDENTITY is simpler for single-table auto-increment. **Gaps in both are normal** and expected—from rollbacks, cached values, and server restarts. Never rely on sequential, gapless numbers from either mechanism.

### Partitioning rarely improves OLTP query performance

Microsoft's own documentation states: "Partitioning rarely improves performance in OLTP systems where queries perform single-row seeks." Partitioning excels at **data lifecycle management** (archiving via SWITCH is a metadata-only, near-instant operation) and **maintenance** (rebuild one partition instead of the entire table). If queries don't filter on the partition key, all partitions are scanned—worse than no partitioning.

### In-memory OLTP for extreme throughput

SQL Server's memory-optimized tables (Hekaton) use **lock-free, latch-free** MVCC for potential 10–100x throughput improvement on write-heavy workloads. Hash indexes provide O(1) equality lookups. Natively compiled stored procedures eliminate SQL interpretation overhead. Limitations include reduced DML trigger support, maximum index counts, and the requirement that tables fit in memory. PostgreSQL's **UNLOGGED tables** provide a lighter-weight alternative (no WAL writes), but data is lost on crash.

---

## 8. Performance optimization techniques

### Reading execution plans

Plans flow **right to left** (data flow). Key indicators: **fat arrows** reveal excessive data flow, **index scans** on large tables suggest missing indexes or non-SARGable predicates, **key lookups** indicate the need for covering indexes (INCLUDE columns), **sort operators** suggest missing index order, and **spills** (yellow warning triangles) mean memory grants were too small due to bad cardinality estimates. When estimated rows differ from actual rows by more than 10x, statistics are likely stale.

### Statistics drive plan quality

Statistics are what the optimizer uses to estimate row counts. Auto-update triggers after approximately **20% of rows change**—for large tables, this threshold is too high. Supplement with scheduled `UPDATE STATISTICS`. The **ascending key problem** affects sequentially increasing values (dates, identities): new values exceed histogram boundaries, causing the optimizer to underestimate rows. Use trace flag 2371 for dynamic update thresholds.

### Temp tables vs table variables

| Feature | Temp Table (#t) | Table Variable (@t) |
|---|---|---|
| Statistics | Full column statistics | None |
| Cardinality estimate | Accurate | Fixed at 1 row (pre-2019) |
| Indexes | Full CREATE INDEX support | Only via constraints |
| Parallelism (INSERT) | Parallel | Serial only |
| Transaction rollback | Affected by ROLLBACK | Not affected |

Use **temp tables** for more than ~100 rows or when joining with large tables. The lack of statistics on table variables leads to catastrophically bad plans when the optimizer assumes 1 row and chooses nested loops over hash joins. Adding `OPTION(RECOMPILE)` to queries referencing table variables allows the optimizer to see actual row counts.

### Set-based thinking eliminates cursors

A cursor over 200 million rows ran for **30 hours and completed only 0.5%** (estimated 8+ months). The set-based rewrite completed in 17 hours total. Replace cursors with window functions (`SUM() OVER()`), CROSS APPLY, recursive CTEs, and batch UPDATE/DELETE patterns. If looping is truly unavoidable, use `FAST_FORWARD READ_ONLY` cursors.

### Query Store for regression detection

Query Store (SQL Server 2016+, enabled by default in 2022+) persists multiple execution plans per query across restarts—unlike DMVs which reset. It tracks CPU, duration, logical reads, and memory grants per plan. **Plan forcing** locks a known-good plan for a regressed query. **Automatic tuning** (`FORCE_LAST_GOOD_PLAN = ON`) automatically reverts plan regressions. Query Store hints (2022+) apply hints like `OPTION(RECOMPILE)` to specific queries without code changes.

---

## 9. Anti-patterns that cripple OLTP systems

### NOLOCK is not a free performance boost

The `NOLOCK` hint (READ UNCOMMITTED) does not just risk reading uncommitted data. It enables **duplicate rows** (allocation order scans return the same row twice during page splits), **skipped rows** (page splits cause rows to be missed entirely), and **torn pages** (partial reads of large rows). Erik Darling emphasizes: even after enabling RCSI, existing NOLOCK hints still cause dirty reads instead of using the version store—"The NOLOCK hints gotta go." Legitimate uses are limited to quick-and-dirty monitoring queries where accuracy is irrelevant.

### The N+1 query problem and ORM defaults

ORMs with lazy loading fire 1 query for N parent records, then N additional queries for children—total N+1 round trips. Solutions include **eager loading** (`.Include()` in Entity Framework, `select_related()` in Django, `JOIN FETCH` in JPA), **batch fetching** (`selectinload` in SQLAlchemy fires 2 queries total), and the **DataLoader pattern** for GraphQL.

### Other critical anti-patterns

- **God tables** with 50–200 columns representing multiple entities cause excessive NULLs, wide rows, and poor cache efficiency
- **One True Lookup Table** (OTLT) consolidates all reference data into one table, destroying foreign key enforcement and type safety
- **Excessive triggers** hide business logic, create recursive chains, and compound write latency
- **Kitchen sink queries** where one procedure serves all search patterns cause catastrophic parameter sniffing—use dynamic SQL with OPTION(RECOMPILE) instead
- **GUID clustering keys** cause massive page splits and 4x index bloat compared to INT
- **Excessive DISTINCT** to hide JOIN bugs masks incorrect cardinality in join logic

---

## 10. Cross-platform differences that matter

### How each RDBMS handles concurrency differently

SQL Server defaults to **lock-based** READ COMMITTED (readers block writers), requiring RCSI to be explicitly enabled for MVCC behavior. PostgreSQL uses **MVCC natively**—readers never block writers by default, but requires VACUUM to reclaim dead tuples. MySQL/InnoDB uses **undo logs** for MVCC but its default REPEATABLE READ with gap locks can cause unexpected blocking. Oracle modifies rows in-place and uses **undo segments** for reconstruction, with no VACUUM needed.

### Platform-specific features worth adopting

| Feature | Platform | Value for OLTP |
|---|---|---|
| Query Store | SQL Server 2016+ | Plan regression detection, automatic tuning |
| RCSI | SQL Server | Eliminates reader/writer blocking |
| Partial indexes | PostgreSQL | Smaller, faster indexes for filtered queries |
| Advisory locks | PostgreSQL | Application coordination without table bloat |
| JSONB + GIN indexes | PostgreSQL | Semi-structured data within OLTP |
| Buffer pool sizing | MySQL InnoDB | Single most important tuning parameter |
| Bind variables | Oracle | Prevents library cache contention (critical) |
| In-Memory OLTP | SQL Server 2014+ | Extreme throughput for hot tables |
| AWR/ASH | Oracle | Comprehensive built-in performance monitoring |

### Key syntax differences

Row limiting uses `TOP` (SQL Server), `LIMIT` (PostgreSQL/MySQL), or `FETCH FIRST` (ANSI SQL:2008, supported in SQL Server 2012+, PostgreSQL 8.4+, Oracle 12c+). Upsert syntax diverges significantly: `MERGE` (SQL Server/Oracle), `INSERT ON CONFLICT` (PostgreSQL 9.5+), `INSERT ON DUPLICATE KEY` (MySQL). Auto-increment uses `IDENTITY` (SQL Server), `GENERATED ALWAYS AS IDENTITY` (PostgreSQL/Oracle 12c+), or `AUTO_INCREMENT` (MySQL).

Writing purely portable ANSI SQL sacrifices platform-specific optimizations. The pragmatic approach: abstract platform-specific code behind stored procedures, use ANSI SQL for general data access, and adopt platform-specific features (RCSI, advisory locks, Query Store, AWR) where they provide substantial value.

---

## Conclusion

Three principles underpin everything in this guide. First, **measure before optimizing**: start with 3NF schema design, basic indexing, and standard isolation levels, then change only what measurements prove is a bottleneck. Second, **the optimizer is usually right**: query hints, forced plans, and join hints should be last resorts—fix the underlying data types, statistics, and indexes instead. Third, **concurrency design is not optional**: choosing between lock-based and MVCC isolation, between optimistic and pessimistic concurrency, and between short batched transactions and long monolithic ones determines whether an OLTP system handles 100 or 100,000 concurrent users.

The most impactful changes for most OLTP systems are enabling RCSI (SQL Server), fixing implicit conversions and non-SARGable predicates, adding covering indexes with INCLUDE columns, following the ESR rule for composite indexes, using `SET XACT_ABORT ON` with proper TRY...CATCH, and batching large data modifications. These six changes alone typically resolve 80% of OLTP performance and reliability problems.
