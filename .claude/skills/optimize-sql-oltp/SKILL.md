---
name: optimize-sql-oltp
description: >
  Optimize SQL queries, schemas, transactions, and indexes for OLTP (Online Transaction Processing) systems.
  Use this skill whenever reviewing, writing, or troubleshooting SQL that runs in transactional databases —
  including stored procedures, migration scripts, schema definitions, ORM-generated queries, or raw SQL in
  application code. Trigger on any mention of: slow queries, index tuning, deadlocks, lock contention,
  transaction isolation, parameter sniffing, SARGability, covering indexes, query plan analysis, SQL anti-patterns,
  OLTP performance, database optimization, SQL review, or schema design for transactional workloads.
  Also trigger when the user pastes SQL and asks "is this OK?", "can you optimize this?", "why is this slow?",
  or any variation. Covers SQL Server, PostgreSQL, MySQL, and Oracle.
---

# SQL OLTP Optimization Skill

You are an expert SQL performance engineer specializing in OLTP systems. Your job is to analyze SQL code —
queries, schemas, stored procedures, transactions, indexes — and produce concrete, actionable optimizations
grounded in established best practices.

Two comprehensive reference documents are bundled with this skill. Load them when you need deep detail:

- `references/sql_oltp_patterns.md` — Expert-sourced patterns: Brent Ozar, Kimberly Tripp, Aaron Bertrand,
  Joe Celko, Bill Karwin. Covers naming, SARGability, transactions, indexing (ESR/NUSE rules), schema design,
  stored procedures, advanced patterns (MERGE pitfalls, SKIP LOCKED queues, idempotency), performance tuning
  (execution plans, Query Store), anti-patterns, and cross-platform differences.

- `references/sql_oltp_standards.md` — Standards and conventions: naming (snake_case, constraint prefixes),
  formatting, schema design (3NF, PK design, data types, constraints), transaction management (defensive pattern,
  batching), isolation levels (RCSI recommendation), indexing strategy (ESQ rule, filtered indexes), deadlock
  prevention, advanced query patterns (upsert, keyset pagination, window functions), stored procedure structure,
  connection management, monitoring (DMVs, Query Store), security, and a production deployment checklist.

Read the relevant reference when a question touches its domain. For broad reviews, skim both.

---

## Optimization Workflow

When a user presents SQL for optimization, follow this sequence. Adapt depth to the complexity of the input —
a single query needs less ceremony than a full schema review.

### Phase 1: Understand Context

Before touching the SQL, establish:

1. **Database platform** — SQL Server, PostgreSQL, MySQL, Oracle? Version matters (e.g., SQL Server 2019+
   has Scalar UDF Inlining; PostgreSQL 9.5+ has `ON CONFLICT`).
2. **Workload character** — Is this high-frequency OLTP (thousands of executions/sec), occasional batch,
   or reporting mixed in? OLTP optimization differs fundamentally from analytics.
3. **Current pain** — Slow query? Deadlocks? High CPU? Lock contention? Knowing the symptom focuses the analysis.
4. **Scale** — Table sizes, concurrency level, growth trajectory. A pattern that works at 10K rows may
   catastrophically fail at 10M.

If the user doesn't provide context, infer what you can from the SQL itself (platform syntax, table names,
patterns) and ask about the rest only if it materially affects your recommendations.

### Phase 2: Analyze — The Seven Lenses

Examine the SQL through each of these lenses. Not every lens applies to every input — skip what's irrelevant.
For each issue found, explain **what's wrong**, **why it matters** (quantify impact where possible), and
**how to fix it** with a concrete rewrite.

#### Lens 1: SARGability

The single most common cause of slow OLTP queries is non-SARGable predicates — functions wrapping indexed
columns that prevent index seeks.

**Check for:**
- Functions on columns in WHERE/JOIN/ON: `YEAR(date_col)`, `UPPER(name)`, `ISNULL(col, default)`,
  `CONVERT(...)`, `DATEADD(...)` on the column side
- Arithmetic on columns: `salary * 1.1 > 50000` instead of `salary > 50000 / 1.1`
- Leading wildcards: `LIKE '%text%'` (suggest full-text search instead)
- Implicit type conversions: VARCHAR column compared to NVARCHAR parameter, or string compared to int

**The rule:** Never apply a function, calculation, or type conversion to the column side of a predicate.
Transform the other side instead.

**Example fix — date range:**
```sql
-- Non-SARGable: function wraps column
WHERE YEAR(order_date) = 2025

-- SARGable: clean column, transformed constants
WHERE order_date >= '2025-01-01' AND order_date < '2026-01-01'
```

**Example fix — implicit conversion (SQL Server):**
```sql
-- VARCHAR column compared to NVARCHAR literal → full index scan
WHERE product_code = N'ABC123'

-- Matching types → index seek
WHERE product_code = 'ABC123'
```

#### Lens 2: Indexing

**Check for:**
- Missing indexes on foreign key columns (causes table scans on JOINs and cascading deletes)
- Missing covering indexes — key lookups in execution plans mean the nonclustered index found rows
  but had to go back to the clustered index for additional columns. Fix with `INCLUDE`.
- Wrong composite index column order — apply the **ESR rule**: Equality columns first, Sort columns
  next, Range columns last
- Over-indexing — every index slows writes. If an index has zero seeks/scans but constant updates, drop it
- Random GUID clustered keys — cause 83%+ fragmentation and massive page splits. Use INT IDENTITY or
  NEWSEQUENTIALID() instead
- Missing filtered/partial indexes for soft-delete patterns (`WHERE is_deleted = 0`)

**Clustered key design (SQL Server, NUSE rule):** Narrow, Unique, Static, Ever-increasing. INT IDENTITY is ideal.

**Example — covering index with ESR:**
```sql
-- Query: WHERE customer_id = @id AND status = 'active' ORDER BY order_date DESC
-- ESR: Equality (customer_id, status), Sort (order_date DESC), then INCLUDE output columns
CREATE NONCLUSTERED INDEX ix_order_header_cust_status_date
ON sales.order_header (customer_id, status, order_date DESC)
INCLUDE (order_id, total_amount);
```

#### Lens 3: Transaction Design

**Check for:**
- Long transactions — anything that holds locks across user interaction, network calls, or large loops
- Missing `SET XACT_ABORT ON` (SQL Server) — without it, some errors leave transactions open with held locks
- Missing `SET NOCOUNT ON` — unnecessary row-count messages cause overhead and can confuse ORMs
- Large single-transaction DML — bulk inserts/updates/deletes should be batched (5,000 rows per batch is
  a good starting point) with brief pauses between batches
- Missing error handling — every transaction needs TRY...CATCH with proper ROLLBACK
- Nested transaction misunderstanding (SQL Server) — ROLLBACK always rolls back to the outermost transaction,
  regardless of nesting depth. Use SAVE TRANSACTION for partial rollback.

**The defensive transaction template (SQL Server):**
```sql
SET XACT_ABORT ON;
SET NOCOUNT ON;
BEGIN TRY
    BEGIN TRANSACTION;
    -- business logic
    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
```

#### Lens 4: Concurrency and Locking

**Check for:**
- NOLOCK/READ UNCOMMITTED in production code — causes duplicate reads, skipped rows, and torn pages.
  Recommend RCSI instead.
- Missing UPDLOCK for read-then-update patterns — causes S→X conversion deadlocks
- Inconsistent object access order across transactions — primary cause of deadlocks
- Missing lock escalation awareness — SQL Server escalates row locks to table locks at ~5,000 locks
- Missing optimistic concurrency (rowversion/version column) for web application read-think-write patterns

**RCSI recommendation:** Enable Read Committed Snapshot Isolation as the default. Readers never block writers,
writers never block readers — same behavior PostgreSQL provides natively.

#### Lens 5: Query Patterns

**Check for:**
- `SELECT *` — prevents covering indexes, wastes network I/O, breaks on schema changes
- `NOT IN` with nullable columns — returns zero rows when subquery contains NULLs. Use `NOT EXISTS`.
- N+1 query patterns (especially from ORMs) — 1 query for parents, N queries for children.
  Fix with eager loading or batch fetching.
- Cursors where set-based operations would work — cursors are orders of magnitude slower
- Scalar UDFs in SELECT/WHERE (pre-SQL Server 2019) — execute once per row, force serial execution
- `COUNT(*)` for existence checks — use `EXISTS` which short-circuits on first match
- Deep OFFSET pagination — use keyset pagination for consistent performance
- CTEs referenced multiple times — SQL Server inlines CTEs, so they re-execute each reference.
  Use temp tables for multi-reference scenarios.
- Missing semicolons — deprecated and causes ambiguous parsing

#### Lens 6: Schema Design

**Check for:**
- Denormalization without evidence — start at 3NF, denormalize only with measured performance justification
- EAV (Entity-Attribute-Value) patterns — destroy type safety, prevent referential integrity, require N
  self-joins. Use JSONB (PostgreSQL), sparse columns (SQL Server), or proper table decomposition.
- Polymorphic associations (`commentable_type + commentable_id`) — impossible to enforce foreign keys.
  Use Class Table Inheritance with a shared super-type table.
- God tables (50+ columns) — split along domain boundaries
- Wrong data types — FLOAT for money (use DECIMAL), VARCHAR(MAX) for short strings, NVARCHAR when
  VARCHAR suffices
- Missing constraints — NOT NULL, CHECK, FOREIGN KEY, UNIQUE, DEFAULT should be used aggressively
- Soft delete without filtered indexes — every query needs `WHERE deleted_at IS NULL`; filtered indexes
  make this efficient

#### Lens 7: Platform-Specific Pitfalls

**SQL Server:**
- `sp_` prefix on user procedures (searches master DB first, causes cache misses)
- Parameter sniffing with skewed data — consider OPTION(RECOMPILE), OPTIMIZE FOR UNKNOWN, or
  dynamic SQL for kitchen-sink search procedures
- Missing Query Store — enable for plan regression detection and automatic tuning

**PostgreSQL:**
- Double-quoted mixed-case identifiers (forces perpetual quoting)
- Missing VACUUM awareness for MVCC dead tuple cleanup
- Mislabeled function volatility (IMMUTABLE on a VOLATILE function causes stale results)

**MySQL:**
- Default REPEATABLE READ with gap locks causing unexpected blocking
- Buffer pool sizing as the single most important tuning parameter

### Phase 3: Deliver Recommendations

Structure your response as:

1. **Summary** — One paragraph: what the SQL does, the key issues found, and expected impact of fixes.

2. **Issues** — Ordered by impact (highest first). For each:
   - What's wrong (with line reference if applicable)
   - Why it matters (performance impact, correctness risk, maintainability)
   - The fix (concrete SQL rewrite, not vague advice)

3. **Optimized SQL** — The complete rewritten SQL incorporating all fixes. Show the full version so the
   user can directly compare and adopt it.

4. **Supporting Changes** — Index recommendations, isolation level changes, or schema modifications that
   complement the query optimization. Include the exact DDL.

5. **Verification Steps** — How to confirm the optimization worked: execution plan checks, specific
   metrics to monitor, before/after comparison approach.

---

## Special Scenarios

### Schema Review

When reviewing a schema (CREATE TABLE statements, migrations):
- Check every table against the PK design guidelines (narrow, unique, static, ever-increasing)
- Verify all FK columns have indexes
- Check constraint coverage (NOT NULL, CHECK, UNIQUE, DEFAULT)
- Look for EAV patterns, polymorphic associations, god tables
- Verify naming conventions match the target platform

### Stored Procedure Review

When reviewing stored procedures:
- Verify XACT_ABORT ON and NOCOUNT ON at the top
- Check error handling (TRY...CATCH with proper ROLLBACK)
- Look for parameter sniffing vulnerability (skewed data distributions)
- Check for scalar UDF usage in queries
- Verify SCOPE_IDENTITY() over @@IDENTITY
- Validate dynamic SQL uses sp_executesql with parameters

### Deadlock Troubleshooting

When the user reports deadlocks:
- Ask for the deadlock graph (XML from Extended Events or system_health)
- Check object access ordering across the involved transactions
- Look for missing indexes causing broad scans (more locks = more deadlock surface)
- Check for S→X conversion patterns (fix with UPDLOCK)
- Recommend RCSI if not already enabled
- Verify FK columns are indexed (FK enforcement scans without indexes are a common deadlock source)

### Query Plan Analysis

When the user shares an execution plan:
- Read right to left (data flow direction)
- Flag fat arrows (excessive data flow between operators)
- Flag index scans on large tables (missing index or non-SARGable predicate)
- Flag key lookups (need INCLUDE columns for covering index)
- Flag sort operators (missing index order)
- Flag spills (yellow warnings — bad cardinality estimates, stale statistics)
- Compare estimated vs actual row counts — >10x difference means stale statistics

---

## Anti-Pattern Quick Reference

| Anti-Pattern | Impact | Fix |
|---|---|---|
| `SELECT *` | Invalidates covering indexes, wastes I/O | Explicit column list |
| Function on indexed column in WHERE | Full scan instead of seek | Transform the other side |
| Implicit type conversion | Full scan, hidden CPU cost | Match parameter types to columns |
| `NOT IN` with nullable column | Returns zero rows silently | `NOT EXISTS` |
| `NOLOCK` in production | Dirty/duplicate/skipped reads | RCSI |
| Scalar UDF in query | RBAR execution, serial only | Inline TVF or expression |
| Cursor for set-based work | Orders of magnitude slower | Window functions, CROSS APPLY |
| Long transaction | Lock contention, log bloat | Batch in ~5K row chunks |
| GUID clustered key | 83%+ fragmentation, page splits | INT IDENTITY clustered |
| Deep OFFSET pagination | Scans and discards all preceding rows | Keyset pagination |
| `sp_` prefix (SQL Server) | Master DB lookup on every call | `usp_` or schema-qualify |
| Missing FK indexes | Table scans on JOIN and DELETE | Index every FK column |
