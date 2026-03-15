# PostgreSQL Optimization Patterns Reference

> Comprehensive technical reference for PostgreSQL-specific optimization. Sourced from official
> PostgreSQL documentation, leading consultancies (Citus, Timescale, pganalyze, EDB, Percona,
> Crunchy Data, Cybertec), and battle-tested community knowledge. Covers PostgreSQL 14–18.

## Table of Contents

1. [Data Types and Schema Design](#1-data-types-and-schema-design)
2. [Indexing Strategies](#2-indexing-strategies)
3. [Partitioning](#3-partitioning)
4. [VACUUM, Autovacuum, and Bloat](#4-vacuum-autovacuum-and-bloat)
5. [Configuration Tuning](#5-configuration-tuning)
6. [Connection Management](#6-connection-management)
7. [Query Patterns](#7-query-patterns)
8. [Monitoring and Diagnostics](#8-monitoring-and-diagnostics)
9. [Security](#9-security)
10. [Modern Features (PG14–18)](#10-modern-features-pg1418)
11. [Anti-Patterns](#11-anti-patterns)
12. [Diagnostic Queries](#12-diagnostic-queries)

---

## 1. Data Types and Schema Design

### 1.1 Type Selection

| Use Case | Recommended | Avoid | Why |
|----------|-------------|-------|-----|
| Primary keys | `BIGINT GENERATED ALWAYS AS IDENTITY` | `SERIAL` (legacy), `INT` (overflow at ~2.1B) | SQL-standard, prevents manual identity inserts |
| Money/currency | `NUMERIC(p, s)` | `FLOAT`, `REAL`, `DOUBLE PRECISION` | Floating-point accumulates rounding errors |
| Timestamps | `TIMESTAMPTZ` | `TIMESTAMP` without timezone | Stores as UTC, converts on display; avoids timezone bugs |
| Short strings with max | `VARCHAR(n)` | `CHAR(n)` (pads with spaces) | CHAR wastes storage, creates comparison bugs |
| Arbitrary text | `TEXT` | `VARCHAR` without limit (equivalent but less explicit) | `TEXT` is idiomatic PostgreSQL |
| Boolean flags | `BOOLEAN` | `SMALLINT`, `CHAR(1)` | Native type with proper semantics |
| JSON data | `JSONB` | `JSON` (text-based, not indexable) | JSONB is binary, supports GIN indexes and containment |
| IP addresses | `INET` or `CIDR` | `TEXT` | Native operators, range queries, indexable |
| UUIDs | `UUID` | `VARCHAR(36)` | 16 bytes vs 36+ bytes, native comparison |
| Enumerations | `TEXT` + `CHECK` | `ENUM` type | ENUMs cannot remove values, hard to modify |
| Public-facing IDs | UUID v7 (time-ordered) or hybrid | Random UUID v4 | v4 causes B-tree page splits, WAL amplification |

### 1.2 TIMESTAMPTZ Always

PostgreSQL stores `TIMESTAMPTZ` internally as UTC microseconds since epoch. On retrieval, it
converts to the session's `timezone` setting. Using plain `TIMESTAMP` discards timezone
information, causing bugs when:
- Servers move across timezones
- Daylight saving transitions occur
- Distributed systems have mixed timezone settings

```sql
SET timezone = 'UTC';  -- Application should always set this
SELECT created_at AT TIME ZONE 'America/New_York' FROM orders;
```

### 1.3 BIGINT GENERATED ALWAYS AS IDENTITY

`SERIAL` is syntactic sugar for an implicit sequence + `INT`. Problems:
- `INT` maxes at ~2.1 billion — high-traffic tables exhaust this
- `SERIAL` allows manual inserts that can collide with the sequence
- Not SQL standard

```sql
-- Modern approach
CREATE TABLE events (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    event_type TEXT NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}'
);
```

### 1.4 JSONB Patterns

Use JSONB for genuinely dynamic data — product attributes, user preferences, API response caching.
Use relational columns for anything you filter, sort, aggregate, or JOIN on.

```sql
-- Hybrid: typed columns for core fields, JSONB for flexible remainder
CREATE TABLE products (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name TEXT NOT NULL,
    price NUMERIC(10, 2) NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('draft', 'active', 'archived')),
    attributes JSONB NOT NULL DEFAULT '{}'
);

-- JSONB containment query (uses GIN index)
SELECT * FROM products WHERE attributes @> '{"color": "red"}';

-- JSONB path query
SELECT * FROM products WHERE attributes->>'brand' = 'Acme';
```

JSONB caveats:
- Updates rewrite the entire column (no partial updates)
- Query planner has limited statistics for JSONB paths
- If you write `WHERE data->>'status' = 'active'` in most queries, make it a column

### 1.5 Schema Constraints

```sql
-- Enforce at the database level, not just application
ALTER TABLE orders
    ADD CONSTRAINT ck_orders_amount_positive CHECK (amount > 0),
    ADD CONSTRAINT ck_orders_status CHECK (status IN ('pending', 'paid', 'shipped', 'cancelled'));

-- NOT NULL on every column that should never be empty
ALTER TABLE users ALTER COLUMN email SET NOT NULL;

-- FK columns MUST have indexes (PostgreSQL does NOT auto-create them)
ALTER TABLE orders ADD CONSTRAINT fk_orders_customers
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE RESTRICT;
CREATE INDEX idx_orders_customer_id ON orders(customer_id);  -- CRITICAL

-- Hybrid PK pattern: fast BIGINT internally, opaque UUID externally
CREATE TABLE orders (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    public_id UUID NOT NULL DEFAULT gen_random_uuid() UNIQUE
);
```

### 1.6 Soft Deletes vs Hard Delete + Audit

Traditional soft deletes (`deleted_at TIMESTAMPTZ`) pollute every query, bloat tables, and break
UNIQUE constraints. The better pattern:

```sql
-- Hard delete with audit log
WITH deleted AS (
    DELETE FROM users WHERE id = 123 RETURNING *
)
INSERT INTO deleted_records (table_name, record_id, data, deleted_by)
SELECT 'users', id, to_jsonb(deleted.*), current_user FROM deleted;
```

If soft deletes are required, always create a partial index:

```sql
CREATE INDEX idx_users_email_active ON users (email) WHERE deleted_at IS NULL;
-- Partial unique constraint
CREATE UNIQUE INDEX idx_unique_active_email ON users (email) WHERE deleted_at IS NULL;
```

---

## 2. Indexing Strategies

### 2.1 Index Type Selection Matrix

| Type | Best For | Key Operators | Build Speed | Lookup Speed | Size |
|------|----------|---------------|-------------|--------------|------|
| **B-tree** | Equality, range, sorting (default) | `=`, `<`, `>`, `BETWEEN`, `IN`, `IS NULL` | Fast | Fast | Medium |
| **GIN** | JSONB, arrays, full-text, multi-value | `@>`, `<@`, `?`, `?&`, `?\|`, `&&`, `@@` | 3x slower | 3x faster than GiST | Large |
| **GiST** | Spatial, ranges, nearest-neighbor, FTS | `<<`, `>>`, `&&`, `@>`, `<@`, `<->` | Moderate | Moderate | Medium |
| **BRING** | Time-series, append-only, physically sorted | `=`, `<`, `>`, `BETWEEN` | Very fast | Varies | 99.96% smaller |
| **SP-GiST** | Quadtrees, k-d trees, radix trees | Varies | Moderate | Fast for sparse | Small |
| **Hash** | Equality-only on large values | `=` only | Fast | Fast | Medium |

### 2.2 B-tree Patterns

Column order in composite indexes follows the leftmost prefix rule. An index on `(a, b, c)`
serves queries on `(a)`, `(a, b)`, or `(a, b, c)`, but not `(b)` or `(c)` alone.
PG18 adds skip scan which can use the index without the leading column.

**Equality before range:**
```sql
-- Good: equality first, range second
CREATE INDEX idx_orders_status_created ON orders (status, created_at DESC);
-- Serves: WHERE status = 'paid' AND created_at > '2025-01-01'
```

**Covering indexes (INCLUDE, PG11+):**
```sql
-- Enables index-only scan (no heap fetch)
CREATE INDEX idx_orders_lookup ON orders (customer_id)
    INCLUDE (order_date, total, status);
-- Plan shows: "Index Only Scan" with "Heap Fetches: 0"
```

**Partial indexes:**
```sql
-- Only 5% of orders are 'pending', but queried constantly
CREATE INDEX idx_orders_pending ON orders (created_at) WHERE status = 'pending';

-- Index non-null values only
CREATE INDEX idx_users_phone ON users (phone) WHERE phone IS NOT NULL;
```

**Expression indexes:**
```sql
-- Must exactly match query expression
CREATE INDEX idx_users_email_lower ON users (lower(email));
-- Works: WHERE lower(email) = 'test@example.com'
-- Fails: WHERE email ILIKE 'test@example.com' (different operator)
```

### 2.3 GIN Indexes

```sql
-- JSONB: default operator class (supports @>, ?, ?&, ?|)
CREATE INDEX idx_products_metadata ON products USING GIN (metadata);

-- JSONB: jsonb_path_ops (faster and smaller for @> only)
CREATE INDEX idx_products_metadata_path ON products USING GIN (metadata jsonb_path_ops);

-- Full-text search
CREATE INDEX idx_articles_search ON articles
    USING GIN (to_tsvector('english', title || ' ' || body));

-- Array containment
CREATE INDEX idx_posts_tags ON posts USING GIN (tags);
-- Query: SELECT * FROM posts WHERE tags @> ARRAY['postgresql'];
```

GIN write performance: builds are 3x slower than B-tree. On write-heavy tables, consider
disabling `fastupdate` and monitor the pending list.

### 2.4 BRING Indexes

BRING stores min/max summaries per block range. Only effective when physical row order correlates
with the indexed column.

```sql
-- Check suitability first
SELECT correlation FROM pg_stats WHERE tablename = 'logs' AND attname = 'created_at';
-- Values near ±1.0 = excellent BRING candidate

-- Time-series logs (data inserted chronologically)
CREATE INDEX idx_logs_created_brin ON logs USING BRING (created_at)
    WITH (pages_per_range = 64);
```

BRING is orders of magnitude smaller than B-tree. A B-tree on 1 billion rows might be 20GB;
the equivalent BRING index could be 48KB.

### 2.5 GiST Indexes

```sql
-- Range types (scheduling, reservations)
CREATE INDEX idx_events_timerange ON events USING GIST (time_range);
-- Query: WHERE time_range && '[2025-01-01, 2025-01-31]'::daterange

-- Exclusion constraints (prevent overlapping bookings)
CREATE EXTENSION btree_gist;
CREATE TABLE room_bookings (
    room_id INT NOT NULL,
    during TSTZRANGE NOT NULL,
    EXCLUDE USING GIST (room_id WITH =, during WITH &&)
);
```

### 2.6 Index Maintenance

**Find unused indexes:**
```sql
SELECT schemaname, relname AS table_name, indexrelname AS index_name,
       idx_scan AS times_used, pg_size_pretty(pg_relation_size(indexrelid)) AS index_size
FROM pg_stat_user_indexes WHERE idx_scan = 0
ORDER BY pg_relation_size(indexrelid) DESC;
```

**Concurrent creation (always in production):**
```sql
CREATE INDEX CONCURRENTLY idx_orders_customer ON orders (customer_id);
-- Cannot run inside a transaction block
-- May fail, leaving INVALID index that must be dropped and retried
```

**Reindex bloated indexes:**
```sql
REINDEX INDEX CONCURRENTLY idx_orders_customer;
```

---

## 3. Partitioning

### 3.1 Strategies

**Range (most common, time-series):**
```sql
CREATE TABLE events (
    id BIGINT GENERATED ALWAYS AS IDENTITY,
    event_type TEXT NOT NULL,
    payload JSONB,
    created_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (id, created_at)  -- partition key MUST be in PK
) PARTITION BY RANGE (created_at);

CREATE TABLE events_2025_01 PARTITION OF events
    FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');
CREATE TABLE events_default PARTITION OF events DEFAULT;
```

**List (categorical):**
```sql
CREATE TABLE orders (
    id BIGINT GENERATED ALWAYS AS IDENTITY,
    region TEXT NOT NULL,
    amount NUMERIC NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (id, region)
) PARTITION BY LIST (region);

CREATE TABLE orders_us PARTITION OF orders FOR VALUES IN ('us-east', 'us-west');
CREATE TABLE orders_eu PARTITION OF orders FOR VALUES IN ('eu-west', 'eu-central');
```

**Hash (even distribution):**
```sql
CREATE TABLE sessions (
    id UUID, user_id BIGINT NOT NULL, data JSONB,
    PRIMARY KEY (id, user_id)
) PARTITION BY HASH (user_id);

CREATE TABLE sessions_p0 PARTITION OF sessions FOR VALUES WITH (MODULUS 4, REMAINDER 0);
-- ... p1, p2, p3
```

### 3.2 Partition Pruning

The primary benefit. The planner eliminates irrelevant partitions when the partition key appears
in WHERE with constants or parameters.

**Verify pruning:**
```sql
EXPLAIN (ANALYZE, COSTS, BUFFERS)
SELECT * FROM events WHERE created_at >= '2025-03-01' AND created_at < '2025-04-01';
-- Look for: "Partitions removed: N" or only relevant partition appearing
```

**Functions on partition key prevent pruning:**
```sql
-- BAD: prevents pruning
WHERE date_trunc('month', created_at) = '2025-03-01'

-- GOOD: enables pruning
WHERE created_at >= '2025-03-01' AND created_at < '2025-04-01'
```

### 3.3 pg_partman Automation

```sql
CREATE EXTENSION pg_partman;

SELECT partman.create_parent(
    p_parent_table := 'public.events',
    p_control := 'created_at',
    p_type := 'native',
    p_interval := '1 month',
    p_premake := 4  -- Create 4 future partitions
);

-- Set retention
UPDATE partman.part_config
SET retention = '12 months', retention_keep_table = false
WHERE parent_table = 'public.events';

-- Schedule maintenance with pg_cron
SELECT cron.schedule('partman', '0 * * * *', 'CALL partman.run_maintenance_proc()');
```

### 3.4 Data Lifecycle

Dropping a partition is nearly instantaneous vs DELETE + VACUUM:

```sql
-- Instant removal of old data
ALTER TABLE events DETACH PARTITION events_2024_01;
DROP TABLE events_2024_01;
```

### 3.5 Concurrent Index Creation on Partitioned Tables

Three-step pattern:
1. Create an invalid index on the parent with `ON ONLY`
2. Create indexes `CONCURRENTLY` on each partition
3. Attach partition indexes to the parent index

---

## 4. VACUUM, Autovacuum, and Bloat

### 4.1 How VACUUM Works

PostgreSQL's MVCC never modifies rows in place. UPDATE creates a new version, DELETE marks the
old version as dead. VACUUM reclaims dead tuples.

- **VACUUM** — Reclaims space within data files. Does not return space to OS. Allows concurrent reads/writes.
- **VACUUM FULL** — Rewrites entire table, returns space to OS. Takes ACCESS EXCLUSIVE lock. **Never use in production.**
- **VACUUM ANALYZE** — VACUUM + update statistics.
- **ANALYZE** — Updates column statistics for the query planner. Does not remove dead tuples.

### 4.2 Autovacuum Trigger Formula

`dead_tuples > autovacuum_vacuum_threshold + (autovacuum_vacuum_scale_factor × table_row_count)`

With defaults (threshold=50, scale_factor=0.2), a 10M-row table doesn't vacuum until 2 million
dead tuples accumulate.

### 4.3 Production Autovacuum Settings

| Parameter | Default | Production Override | Notes |
|-----------|---------|-------------------|-------|
| `autovacuum` | `on` | `on` (never disable) | |
| `autovacuum_max_workers` | 3 | 5–8 | One worker per table |
| `autovacuum_vacuum_scale_factor` | 0.2 | 0.05–0.1 | Lower for large tables |
| `autovacuum_vacuum_threshold` | 50 | 50–1000 | Additive to scale factor |
| `autovacuum_analyze_scale_factor` | 0.1 | 0.02–0.05 | Trigger ANALYZE more often |
| `autovacuum_vacuum_cost_delay` | 2ms | 0–2ms | 0 on SSDs |
| `autovacuum_vacuum_cost_limit` | 200 | 800–2000 | Higher = faster vacuum |
| `autovacuum_freeze_max_age` | 200M | 400M–600M | Anti-wraparound threshold |
| `autovacuum_work_mem` | -1 (uses maintenance_work_mem) | 256MB–1GB | Avoids multiple index passes |

**Per-table overrides for hot tables:**
```sql
ALTER TABLE high_traffic_orders SET (
    autovacuum_vacuum_scale_factor = 0.01,
    autovacuum_vacuum_threshold = 1000,
    autovacuum_analyze_scale_factor = 0.005,
    autovacuum_vacuum_cost_delay = 0,
    autovacuum_vacuum_cost_limit = 1000
);
```

### 4.4 Transaction ID Wraparound

PostgreSQL uses 32-bit transaction IDs (~4 billion). Without VACUUM freezing old tuple XIDs,
the database will **shut down** to prevent data corruption.

```sql
-- Monitor wraparound risk
SELECT datname, age(datfrozenxid) AS xid_age,
       current_setting('autovacuum_freeze_max_age')::bigint AS freeze_max_age,
       round(age(datfrozenxid)::numeric /
           current_setting('autovacuum_freeze_max_age')::numeric * 100, 1) AS pct_towards_wraparound
FROM pg_database ORDER BY age(datfrozenxid) DESC;
```

If `age(datfrozenxid)` approaches 2 billion, take immediate action.

### 4.5 Bloat Detection and Remediation

```sql
-- Detect bloat with pgstattuple
CREATE EXTENSION pgstattuple;
SELECT dead_tuple_percent, free_percent FROM pgstattuple('my_table');
-- dead_tuple_percent > 20% → needs VACUUM
-- free_percent > 50% → needs pg_repack
```

**pg_repack (preferred for online compaction):**
Creates shadow table, copies data, replays changes via trigger, performs brief atomic swap.
No ACCESS EXCLUSIVE lock during the copy phase.

```bash
pg_repack --table orders --no-kill-backend -d mydb
```

**VACUUM FULL is an emergency tool, not maintenance.** It blocks all reads and writes for the
entire duration.

---

## 5. Configuration Tuning

### 5.1 Memory

| Parameter | Formula | Example (64GB RAM, 16 CPU) | Notes |
|-----------|---------|--------------------------|-------|
| `shared_buffers` | 25% RAM (never >40%) | 16GB | PostgreSQL page cache |
| `effective_cache_size` | 75% RAM | 48GB | Planner hint, no allocation |
| `work_mem` | Start 64MB, adjust per EXPLAIN | 64MB | Per-operation sort/hash memory |
| `maintenance_work_mem` | 1–2GB | 2GB | VACUUM, CREATE INDEX, ALTER TABLE |
| `huge_pages` | `try` | `try` | Reduces TLB misses for large shared_buffers |

**work_mem caution:** A complex query with multiple sorts can use multiples of this value.
Total memory = work_mem × operations × connections. Start low, increase based on EXPLAIN ANALYZE
showing sorts spilling to disk (`Sort Method: external merge`).

### 5.2 WAL

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| `wal_level` | `replica` (minimum for replication) or `logical` | |
| `max_wal_size` | 4–8GB | Fewer checkpoints = less I/O; default 1GB too low |
| `checkpoint_timeout` | 15min | Spread checkpoint I/O; default 5min too aggressive |
| `checkpoint_completion_target` | 0.9 | Spread I/O over 90% of checkpoint interval |
| `wal_compression` | `on` (PG15+: `zstd`) | Trades CPU for reduced WAL volume |

**Non-critical writes throughput trick:**
```sql
-- For audit logs, analytics events — risk losing last ~600ms on crash, no corruption
SET LOCAL synchronous_commit = 'off';
INSERT INTO audit_log (...) VALUES (...);
```

### 5.3 Query Planner

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| `random_page_cost` | 1.1 (SSD), 4.0 (HDD) | Tells planner random reads cost on SSDs |
| `seq_page_cost` | 1.0 | Reference point for other costs |
| `effective_io_concurrency` | 200 (SSD), 2 (HDD) | Prefetch for bitmap heap scans |

### 5.4 Parallelism

```
max_parallel_workers_per_gather = 4   -- Workers per query node
max_parallel_workers = 8              -- Total workers across all queries
max_worker_processes = 12             -- Total background worker slots
parallel_tuple_cost = 0.01            -- Lower to encourage parallel plans
min_parallel_table_scan_size = '8MB'
```

### 5.5 Logging

```
log_min_duration_statement = '500ms'   -- Log queries slower than 500ms
log_checkpoints = on
log_lock_waits = on
log_temp_files = 0                      -- Log all temp file usage (sort spills)
log_autovacuum_min_duration = '250ms'   -- Log slow autovacuum runs
```

### 5.6 OS-Level Tuning (Linux)

- `vm.swappiness = 1` — Minimize swapping without OOM killer risk
- `vm.overcommit_memory = 2` — Prevent overcommit surprises
- **Disable Transparent Huge Pages** — They cause memory fragmentation and latency spikes:
  `echo never > /sys/kernel/mm/transparent_hugepage/enabled`
- Filesystem: XFS with `noatime` mount option
- I/O scheduler: `none` for NVMe, `mq-deadline` for SATA SSDs

---

## 6. Connection Management

### 6.1 PgBouncer Configuration

```ini
[databases]
mydb = host=127.0.0.1 port=5432 dbname=mydb

[pgbouncer]
listen_port = 6432
pool_mode = transaction          # Recommended for most apps
max_client_conn = 1000
default_pool_size = 25           # Actual PG connections per database
reserve_pool_size = 5
reserve_pool_timeout = 3
server_idle_timeout = 300
```

**Pool modes:**
- `session` — Connection held for entire client session. Safest, least efficient.
- `transaction` — Connection returned after each transaction. Best balance.
- `statement` — Connection returned after each statement. Only for simple queries.

### 6.2 Connection Sizing

Optimal PostgreSQL connections ≈ 2–4× CPU cores (not hundreds). PgBouncer multiplexes
many client connections over this small pool.

```sql
-- Keep low; pool externally
-- postgresql.conf:
max_connections = 200

-- Monitor usage
SELECT count(*) AS active FROM pg_stat_activity WHERE state = 'active';
```

### 6.3 Idle Connection Management

```
idle_in_transaction_session_timeout = '30s'   -- Kill idle-in-transaction
statement_timeout = '60s'                      -- Kill runaway queries
```

### 6.4 RLS with PgBouncer

When using PgBouncer in transaction mode, `current_user` is shared across tenants.
Use `SET LOCAL` (transaction-scoped) for tenant context:

```sql
-- Application sets context per request
SET LOCAL app.tenant_id = 'a1b2c3d4-...';
-- RLS policy uses: current_setting('app.tenant_id')::uuid
```

---

## 7. Query Patterns

### 7.1 CTE Materialization (PG12+)

Before PG12, all CTEs were materialized (optimization fence). Since PG12, non-recursive CTEs
are inlined by default. Control with:

```sql
-- Force materialization (compute once, reference multiple times)
WITH expensive AS MATERIALIZED (
    SELECT id, complex_function(data) AS result FROM big_table
)
SELECT * FROM expensive WHERE result > 100;

-- Force inlining (allow predicate pushdown)
WITH simple AS NOT MATERIALIZED (
    SELECT * FROM users WHERE status = 'active'
)
SELECT * FROM simple WHERE created_at > '2025-01-01';
```

### 7.2 LATERAL Joins

Replace correlated subqueries. Essential for top-N-per-group:

```sql
-- Top 3 recent orders per customer
SELECT c.name, o.order_id, o.total
FROM customers c
LEFT JOIN LATERAL (
    SELECT order_id, total FROM orders
    WHERE customer_id = c.id ORDER BY order_date DESC LIMIT 3
) o ON true;
```

### 7.3 UPSERT (ON CONFLICT)

```sql
INSERT INTO user_settings (user_id, key, value)
VALUES (42, 'theme', 'dark')
ON CONFLICT (user_id, key)
DO UPDATE SET value = EXCLUDED.value, updated_at = now();

-- Batch upsert
INSERT INTO inventory (product_id, warehouse_id, quantity)
VALUES (1, 10, 100), (2, 10, 200), (3, 10, 50)
ON CONFLICT (product_id, warehouse_id)
DO UPDATE SET quantity = inventory.quantity + EXCLUDED.quantity, updated_at = now();
```

### 7.4 Materialized Views

```sql
CREATE MATERIALIZED VIEW mv_monthly_stats AS
SELECT date_trunc('month', created_at) AS month,
       COUNT(*) AS total_orders, SUM(amount) AS total_revenue
FROM orders WHERE status = 'paid'
GROUP BY 1 WITH DATA;

-- Unique index required for CONCURRENTLY refresh
CREATE UNIQUE INDEX idx_mv_monthly_stats_month ON mv_monthly_stats (month);

-- Refresh without blocking reads
REFRESH MATERIALIZED VIEW CONCURRENTLY mv_monthly_stats;

-- Automate with pg_cron
SELECT cron.schedule('hourly_refresh', '0 * * * *',
    'REFRESH MATERIALIZED VIEW CONCURRENTLY mv_monthly_stats');
```

### 7.5 Exclusion Constraints

Solve scheduling and reservation problems declaratively:

```sql
CREATE EXTENSION btree_gist;
CREATE TABLE room_bookings (
    room_id INT NOT NULL,
    during TSTZRANGE NOT NULL,
    EXCLUDE USING GIST (room_id WITH =, during WITH &&)
);
-- Any overlapping booking for the same room is rejected at DB level
```

### 7.6 Full-Text Search

```sql
-- Generated column for automatic tsvector maintenance
ALTER TABLE articles ADD COLUMN search_vector tsvector
    GENERATED ALWAYS AS (
        setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
        setweight(to_tsvector('english', coalesce(body, '')), 'B')
    ) STORED;

CREATE INDEX idx_articles_search ON articles USING GIN (search_vector);

-- Query
SELECT title, ts_rank(search_vector, query) AS rank
FROM articles, to_tsquery('english', 'postgresql & optimization') AS query
WHERE search_vector @@ query
ORDER BY rank DESC;
```

### 7.7 Bulk Loading

```sql
-- COPY is 4–10x faster than multi-row INSERT
COPY products FROM '/path/to/data.csv' WITH (FORMAT csv, HEADER true);

-- From application code, use unnest for batch inserts (2x faster at batch 1000)
INSERT INTO measurements (sensor_id, value, recorded_at)
SELECT * FROM unnest($1::int[], $2::float8[], $3::timestamptz[]);
```

### 7.8 Batch DML

Large UPDATE/DELETE operations should be batched to avoid long locks and WAL bloat:

```sql
DO $$
DECLARE rows_deleted INT;
BEGIN
    LOOP
        DELETE FROM logs WHERE id IN (
            SELECT id FROM logs WHERE created_at < '2024-01-01' LIMIT 10000
        );
        GET DIAGNOSTICS rows_deleted = ROW_COUNT;
        EXIT WHEN rows_deleted = 0;
        PERFORM pg_sleep(0.1);  -- Brief pause for replication
    END LOOP;
END $$;
```

### 7.9 Statistics for Correlated Columns

When EXPLAIN shows large row estimate mismatches:

```sql
-- Fix correlated column estimates (PG10+)
CREATE STATISTICS stts_city_zip (dependencies) ON city, zip FROM addresses;
ANALYZE addresses;

-- Increase statistics target for skewed columns
ALTER TABLE orders ALTER COLUMN status SET STATISTICS 500;
ANALYZE orders;
```

---

## 8. Monitoring and Diagnostics

### 8.1 pg_stat_statements

The most important monitoring extension. Enable in `postgresql.conf`:

```
shared_preload_libraries = 'pg_stat_statements'
pg_stat_statements.track = 'top'
pg_stat_statements.max = 10000
track_io_timing = on
```

```sql
CREATE EXTENSION pg_stat_statements;

-- Top 10 queries by total execution time
SELECT queryid, calls,
       round(total_exec_time::numeric, 2) AS total_ms,
       round(mean_exec_time::numeric, 2) AS mean_ms,
       rows, query
FROM pg_stat_statements
ORDER BY total_exec_time DESC LIMIT 10;
```

### 8.2 auto_explain

Automatically logs execution plans for slow queries:

```
shared_preload_libraries = 'pg_stat_statements, auto_explain'
auto_explain.log_min_duration = '1s'
auto_explain.log_analyze = on
auto_explain.log_buffers = on
```

### 8.3 Key Metrics and Thresholds

| Metric | Query/Source | Target | Action If Violated |
|--------|-------------|--------|-------------------|
| Cache hit ratio | `pg_stat_database` | > 99% | Increase shared_buffers or reduce working set |
| Dead tuples | `pg_stat_user_tables` | Trend stable | Tune autovacuum |
| XID age | `pg_database` | < 500M | VACUUM FREEZE |
| Index usage | `pg_stat_user_indexes` | > 0 scans | Drop unused indexes |
| Connections | `pg_stat_activity` | < max_connections | Add PgBouncer |
| Replication lag | `pg_stat_replication` | < 1s | Check network, increase wal_sender |
| Lock waits | `pg_locks` | Rare | Investigate contention |

### 8.4 Replication Slot Monitoring

**Critical:** Inactive replication slots cause unbounded WAL accumulation that fills disks.

```sql
-- Check for inactive slots
SELECT slot_name, active, pg_size_pretty(
    pg_wal_lsn_diff(pg_current_wal_lsn(), restart_lsn)
) AS retained_wal
FROM pg_replication_slots WHERE NOT active;
```

---

## 9. Security

### 9.1 Row-Level Security (RLS)

```sql
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE projects FORCE ROW LEVEL SECURITY;  -- Applies to table owners too

CREATE POLICY tenant_isolation ON projects
    USING (tenant_id = current_setting('app.tenant_id')::uuid)
    WITH CHECK (tenant_id = current_setting('app.tenant_id')::uuid);
```

Key advantage: if you forget to define a policy, RLS **fails closed** (denies access).
Always use a non-superuser app role (superusers bypass RLS). Index `tenant_id`.

### 9.2 Authentication

```
# pg_hba.conf — require SSL + SCRAM for all remote connections
hostssl all all 0.0.0.0/0 scram-sha-256

# postgresql.conf
password_encryption = 'scram-sha-256'
ssl = on
ssl_min_protocol_version = 'TLSv1.3'
```

MD5 is cryptographically broken. PG18 formally deprecates it.

### 9.3 Role Hierarchy

```sql
-- Never use superuser for application connections
CREATE ROLE app_readonly LOGIN PASSWORD 'strong' NOSUPERUSER NOCREATEDB;
CREATE ROLE app_readwrite LOGIN PASSWORD 'strong' NOSUPERUSER NOCREATEDB;

GRANT USAGE ON SCHEMA app TO app_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA app TO app_readonly;

GRANT USAGE ON SCHEMA app TO app_readwrite;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA app TO app_readwrite;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA app TO app_readwrite;

-- Auto-grant on future tables
ALTER DEFAULT PRIVILEGES IN SCHEMA app
    GRANT SELECT ON TABLES TO app_readonly;
```

---

## 10. Modern Features (PG14–18)

### PG14
- JSONB subscripting: `data['key']` instead of `data->'key'`
- Multirange types
- `SEARCH DEPTH FIRST`/`BREADTH FIRST` for recursive CTEs
- B-tree bottom-up deletion

### PG15
- MERGE command (SQL-standard upsert/delete in one statement)
- SECURITY INVOKER views
- `wal_compression = zstd`
- Logical replication row filters and column lists
- CREATE on public schema revoked from PUBLIC by default

### PG16
- `pg_stat_io` for I/O monitoring by backend type
- Logical replication from standbys
- `any_value()` aggregate
- `VACUUM (BUFFER_USAGE_LIMIT)` for memory-controlled vacuuming
- Regex support in pg_hba.conf

### PG17
- Native incremental backup (`pg_basebackup --incremental`)
- `JSON_TABLE` (SQL-standard JSON-to-relational)
- 20x VACUUM memory reduction via TidStore
- `MERGE ... RETURNING`
- `COPY ON_ERROR ignore` for fault-tolerant bulk loads
- 2x WAL write throughput

### PG18
- Async I/O (`io_method = 'io_uring'`) — up to 3x read performance
- Native `uuidv7()` — time-ordered UUIDs without extensions
- Virtual generated columns (computed on read, no storage)
- `OLD`/`NEW` in RETURNING clauses
- B-tree skip scan (use multi-column indexes without leading column)
- Temporal constraints (`PRIMARY KEY ... WITHOUT OVERLAPS`)
- OAuth 2.0 authentication
- Parallel GIN index builds
- Data checksums enabled by default in initdb

---

## 11. Anti-Patterns

### Schema
- **EAV tables** — Use JSONB instead. EAV creates massive row counts, prevents indexing.
- **FLOAT for money** — Use NUMERIC. Floating-point introduces rounding errors.
- **JSON as TEXT** — Use JSONB for queryable, indexable JSON.
- **Missing FK indexes** — FK constraints help the planner, but indexes on FK columns are not automatic.
- **ENUM types** — Hard to modify. Use TEXT + CHECK.
- **Over-indexing** — Every index slows writes. Monitor `pg_stat_user_indexes` for unused indexes.

### Operational
- **Disabling autovacuum** — Never. Leads to bloat and wraparound shutdown.
- **VACUUM FULL routinely** — Emergency tool, not maintenance. Use pg_repack.
- **Superuser for app connections** — Bypasses RLS, unnecessary privilege.
- **Ignoring connection pooling** — Direct connections at scale exhaust resources.
- **Not monitoring replication lag** — Stale reads from lagging replicas.
- **Ignoring inactive replication slots** — Unbounded WAL accumulation.
- **Configuration changes without benchmarking** — Establish baselines with pg_stat_statements first.

### Query
- **`NOT IN` with nullable columns** — Returns zero rows when subquery contains NULL. Use `NOT EXISTS`.
- **Functions on indexed columns** — Prevents index usage. Transform the constant side.
- **OFFSET pagination** — Use keyset pagination for consistent performance.
- **Implicit type casting** — VARCHAR vs INTEGER comparison causes full-table scans.
- **Missing LIMIT on exploratory queries** — Always paginate or limit.
- **ORDER BY without index** — Sorting millions in memory when an index could provide pre-sorted data.

---

## 12. Diagnostic Queries

```sql
-- Database sizes
SELECT datname, pg_size_pretty(pg_database_size(datname))
FROM pg_database ORDER BY pg_database_size(datname) DESC;

-- Table sizes (including indexes and toast)
SELECT relname, pg_size_pretty(pg_total_relation_size(relid)) AS total,
       pg_size_pretty(pg_relation_size(relid)) AS table_only,
       pg_size_pretty(pg_indexes_size(relid)) AS indexes
FROM pg_stat_user_tables ORDER BY pg_total_relation_size(relid) DESC LIMIT 20;

-- Long-running queries
SELECT pid, now() - query_start AS duration, state, query
FROM pg_stat_activity WHERE state != 'idle' ORDER BY duration DESC LIMIT 10;

-- Blocking locks
SELECT blocked.pid, blocked.query AS blocked_query,
       blocking.pid AS blocking_pid, blocking.query
FROM pg_stat_activity blocked
JOIN pg_locks bl ON bl.pid = blocked.pid AND NOT bl.granted
JOIN pg_locks bk ON bk.locktype = bl.locktype AND bk.relation = bl.relation
    AND bk.pid != bl.pid AND bk.granted
JOIN pg_stat_activity blocking ON bk.pid = blocking.pid;

-- Tables needing vacuum most urgently
SELECT relname, n_dead_tup, last_autovacuum, last_vacuum
FROM pg_stat_user_tables WHERE n_dead_tup > 10000 ORDER BY n_dead_tup DESC;

-- Transaction ID wraparound risk
SELECT datname, age(datfrozenxid) AS xid_age FROM pg_database ORDER BY xid_age DESC;

-- Cache hit ratio
SELECT sum(blks_hit) * 100.0 / nullif(sum(blks_hit + blks_read), 0) AS cache_hit_ratio
FROM pg_stat_database WHERE datname = current_database();

-- Index usage rates
SELECT relname, indexrelname, idx_scan, idx_tup_read, idx_tup_fetch
FROM pg_stat_user_indexes ORDER BY idx_scan DESC;

-- Table I/O statistics (seq scan vs index scan)
SELECT relname, seq_scan, idx_scan,
       n_tup_ins, n_tup_upd, n_tup_del, n_dead_tup
FROM pg_stat_user_tables ORDER BY seq_scan DESC;
```
