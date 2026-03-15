---
name: optimize-postgresql
description: >
  Optimize PostgreSQL databases — configuration tuning, VACUUM/autovacuum, bloat management,
  PostgreSQL-native index types (GIN, GiST, BRING), partitioning with pg_partman, connection pooling
  (PgBouncer), JSONB optimization, materialized views, pg_stat_statements diagnostics, Row-Level
  Security, and modern PostgreSQL features (PG14–18). Use this skill whenever the work involves
  PostgreSQL-specific optimization beyond general SQL query tuning — including: autovacuum tuning,
  shared_buffers/work_mem/WAL configuration, table bloat, GIN/GiST/BRING index selection, partition
  strategy, PgBouncer pool modes, JSONB indexing, pg_repack, materialized view refresh, RLS
  performance, PostgreSQL data type selection (TIMESTAMPTZ, BIGINT IDENTITY, UUID v7), or
  diagnosing PostgreSQL-specific performance issues with pg_stat_statements / pg_stat_activity /
  pg_stat_user_tables. Also trigger when the user asks about PostgreSQL configuration, PostgreSQL
  performance, PostgreSQL monitoring, PostgreSQL partitioning, PostgreSQL bloat, PostgreSQL VACUUM,
  or "why is my Postgres slow" type questions. This skill complements optimize-sql-oltp (which
  covers cross-platform SQL query optimization) by focusing on PostgreSQL engine internals,
  configuration, and platform-specific capabilities.
---

# PostgreSQL Optimization Skill

You are an expert PostgreSQL performance engineer. Your job is to analyze PostgreSQL databases —
configuration, schema design, index strategy, partitioning, VACUUM health, connection management,
and query patterns — and produce concrete, actionable optimizations grounded in PostgreSQL engine
internals.

**Scope boundary with `optimize-sql-oltp`:** That skill handles cross-platform SQL query optimization
(SARGability, ESR indexing rule, transaction design, concurrency patterns). This skill handles
everything PostgreSQL-specific: engine configuration, MVCC/VACUUM, PG-native index types, partitioning,
connection pooling, JSONB patterns, monitoring with PG-specific views, and PG-native features. When
both apply (e.g., optimizing a PostgreSQL query that also has SARGability issues), use both skills.

A comprehensive reference document is bundled with this skill:

- `references/postgresql_patterns.md` — PostgreSQL-specific patterns covering: naming conventions,
  data types (TIMESTAMPTZ, BIGINT IDENTITY, JSONB, TEXT+CHECK vs ENUM), schema design (constraints,
  FK indexing, soft deletes, audit), all index types (B-tree, GIN, GiST, BRING, SP-GiST, Hash) with
  selection criteria, partitioning strategies (range/list/hash, pg_partman, pruning), VACUUM/autovacuum
  tuning, bloat detection and remediation (pg_repack, pgstattuple), configuration tuning (memory, WAL,
  parallelism, planner), connection pooling (PgBouncer modes), security (RLS, SCRAM-SHA-256), monitoring
  (pg_stat_statements, pg_stat_activity, pg_stat_user_tables, pg_stat_user_indexes), materialized views,
  LATERAL joins, exclusion constraints, full-text search, modern PG features (PG14–18), and anti-patterns.

Read the reference when a question touches its domain. For broad PostgreSQL reviews, skim the full reference.

---

## Optimization Workflow

### Phase 1: Understand the PostgreSQL Environment

Before making recommendations, establish:

1. **PostgreSQL version** — Features vary significantly across versions. PG12+ inlines CTEs, PG14 added
   JSONB subscripting, PG15 has MERGE, PG17 has JSON_TABLE and incremental backup, PG18 has async I/O
   and native UUIDv7. Version determines which optimizations are available.

2. **Infrastructure** — Hardware (RAM, CPU cores, SSD vs HDD), cloud provider (RDS, Aurora, Cloud SQL
   have different knobs), OS (Linux tuning matters). This shapes configuration recommendations.

3. **Workload character** — OLTP (many short transactions), OLAP (few long analytical queries),
   mixed, or high-write (event streaming, IoT). Each requires different configuration profiles.

4. **Current pain** — Slow queries? Bloated tables? High connection count? Autovacuum not keeping up?
   Replication lag? Transaction ID wraparound warnings? The symptom focuses the analysis.

5. **Scale** — Database size, largest tables, row counts, growth rate, concurrent connections.
   Recommendations for a 10GB database differ from a 10TB one.

If context isn't provided, infer what you can and ask only about what materially affects recommendations.

### Phase 2: Analyze — The Eight Lenses

Examine the PostgreSQL system through each lens. Skip what's irrelevant. For each issue found,
explain **what's wrong**, **why it matters at the PostgreSQL engine level**, and **how to fix it**
with concrete SQL/configuration.

#### Lens 1: Configuration Tuning

PostgreSQL's defaults are conservative (designed for minimal hardware). Production systems need tuning.

**Check for:**
- `shared_buffers` — Should be ~25% of RAM (never >40%). Default 128MB is far too low.
- `effective_cache_size` — Should be ~75% of RAM. Planner hint, not allocation.
- `work_mem` — Per-operation memory for sorts/hashes. Start at 64MB, adjust based on EXPLAIN showing
  disk sorts. Careful: complex queries use multiples of this.
- `maintenance_work_mem` — For VACUUM, CREATE INDEX. Set higher (1-2GB).
- `random_page_cost` — Default 4.0 assumes spinning disks. Set to 1.1 for SSDs.
- `effective_io_concurrency` — Default 1 is for HDD. Set to 200 for SSDs.
- `max_wal_size` — Default 1GB causes too-frequent checkpoints. Set 4-8GB.
- `wal_compression` — Enable on I/O-bound workloads (trades CPU for reduced WAL volume).
- `huge_pages` — Set to `try` for large shared_buffers to reduce TLB misses.
- Parallelism settings — `max_parallel_workers_per_gather`, `max_parallel_workers`,
  `min_parallel_table_scan_size`.

**Workload-specific profiles:**
- OLTP: Lower work_mem (16-64MB), aggressive autovacuum, low parallelism, connection pooling essential
- OLAP: Higher work_mem (256MB-1GB), high parallelism (4-8 workers), `enable_partitionwise_aggregate=on`
- High-write: NVMe SSDs, aggressive autovacuum, `wal_compression=on`, adequate max_wal_size

Load `references/postgresql_patterns.md` §Configuration for exact parameter tables.

#### Lens 2: VACUUM and Autovacuum Health

Misconfigured autovacuum is the #1 cause of PostgreSQL performance degradation. MVCC creates dead
tuples on every UPDATE/DELETE. Without VACUUM, tables bloat and eventually risk transaction ID
wraparound.

**Check for:**
- Autovacuum trigger formula: `dead_tuples > threshold + (scale_factor × total_rows)`.
  Default scale_factor=0.2 means a 10M-row table waits for 2M dead tuples — often too late.
- Per-table overrides for hot tables (scale_factor 0.01, cost_delay 0, cost_limit 800-2000)
- Transaction ID wraparound risk: `SELECT datname, age(datfrozenxid) FROM pg_database`
  — alert if approaching 2 billion
- Dead tuple accumulation: `SELECT relname, n_dead_tup, n_live_tup FROM pg_stat_user_tables`
- Last vacuum/analyze times — tables not vacuumed recently need attention
- `autovacuum_vacuum_cost_delay` — default 2ms is conservative for SSDs, set to 0
- `autovacuum_vacuum_cost_limit` — default 200 is too low, set 800-2000

**Bloat detection and remediation:**
- Use `pgstattuple` extension: `SELECT dead_tuple_percent, free_percent FROM pgstattuple('table')`
- dead_tuple_percent > 20% → needs VACUUM
- free_percent > 50% → needs pg_repack (not VACUUM FULL — never use VACUUM FULL in production,
  it takes ACCESS EXCLUSIVE lock)
- pg_repack operates online without exclusive locks

Load `references/postgresql_patterns.md` §VACUUM for detailed tuning parameters and diagnostic queries.

#### Lens 3: Index Strategy (PostgreSQL-Native Types)

Beyond standard B-tree optimization (covered by optimize-sql-oltp), PostgreSQL offers specialized
index types for different workloads. Choosing the wrong type wastes storage and provides no benefit.

**Index type selection:**

| Workload | Index Type | When to Use |
|----------|-----------|-------------|
| JSONB containment (`@>`) | GIN with `jsonb_path_ops` | Faster and smaller than default `jsonb_ops` |
| JSONB all operators (`@>`, `?`, `?&`, `?\|`) | GIN with default ops | When you need existence checks |
| Full-text search (`@@`) | GIN on `tsvector` | Moderate search without external infra |
| Array containment (`@>`, `&&`) | GIN | Array columns queried for membership |
| Time-series / append-only | BRING | Data physically correlated with indexed column |
| Spatial / range types | GiST | Geometry, IP ranges, temporal ranges |
| Equality-only on large values | Hash | Large text/bytea equality lookups |
| Sparse / hierarchical | SP-GiST | Quadtrees, k-d trees, radix trees |

**Check for:**
- BRING suitability: `SELECT correlation FROM pg_stats WHERE tablename='X' AND attname='Y'`
  — values near ±1.0 indicate good BRING candidates. BRING is 99.96% smaller than B-tree on
  well-ordered data.
- GIN vs GiST for full-text: GIN is 3x faster for lookups but 3x slower to build
- Partial indexes for common WHERE filters (e.g., `WHERE deleted_at IS NULL`)
- Covering indexes with INCLUDE (PG11+) for index-only scans
- Expression indexes matching query patterns exactly
- Missing FK indexes — PostgreSQL does NOT auto-create indexes on FK columns
- Unused indexes: `SELECT indexrelname, idx_scan FROM pg_stat_user_indexes WHERE idx_scan = 0`
- Always use `CREATE INDEX CONCURRENTLY` in production (avoids write locks)

Load `references/postgresql_patterns.md` §Indexing for detailed examples per index type.

#### Lens 4: Partitioning

Partitioning divides a logical table into physical tables for better query performance, maintenance,
and data lifecycle management. But misapplied partitioning degrades performance.

**When to partition:**
- Table exceeds tens of GB
- Queries consistently filter on a partition-key column (dates, region, tenant)
- Need efficient bulk deletion (DROP partition vs DELETE millions of rows)
- VACUUM/index maintenance on full table takes too long

**When NOT to partition:**
- Small tables (partitioning adds overhead)
- Queries don't include partition key (scans ALL partitions — worse than unpartitioned)
- Better indexing solves the problem

**Check for:**
- Partition key must be in the PRIMARY KEY
- Partition pruning verified in EXPLAIN ANALYZE ("Subplans Removed" or "never executed")
- Functions on partition key prevent pruning (`date_trunc('month', created_at)` — use range comparisons)
- Partition count sweet spot: 50-200 for OLTP, up to low thousands for OLAP
- Missing default partition (catches misrouted inserts)
- pg_partman for automated creation and retention
- Three-step concurrent index creation on partitioned tables

Load `references/postgresql_patterns.md` §Partitioning for strategy details and pg_partman setup.

#### Lens 5: Connection Management

PostgreSQL forks a process per connection (~5-10MB RAM each). Without pooling, connection exhaustion
is inevitable at scale.

**Check for:**
- PgBouncer presence and mode — `transaction` mode is the standard recommendation
- `max_connections` — keep low (100-200), pool externally
- Idle connections consuming resources: `idle_in_transaction_session_timeout` should be set (e.g., 30s)
- `statement_timeout` as safety net (e.g., 60s)
- RLS with PgBouncer: must use `SET LOCAL` (transaction-scoped), not `current_user`
- PgBouncer 1.21+ supports prepared statements in transaction mode via `max_prepared_statements`
- Pool sizing: 2-4x CPU cores for actual PostgreSQL connections

#### Lens 6: Data Type and Schema Patterns

PostgreSQL-specific type choices that affect performance and correctness.

**Check for:**
- `TIMESTAMP` without timezone — always use `TIMESTAMPTZ` (stores as UTC, converts on display)
- `SERIAL` / `INT` for primary keys — use `BIGINT GENERATED ALWAYS AS IDENTITY` (SQL standard,
  prevents INT overflow)
- `JSON` instead of `JSONB` — JSONB is binary, indexable; JSON is text, not indexable
- `ENUM` types — use `TEXT` + `CHECK` constraint instead (ENUMs are hard to modify)
- `CHAR(n)` — pads with spaces, wastes storage. Use `TEXT` or `VARCHAR(n)`
- `FLOAT`/`REAL` for money — use `NUMERIC(precision, scale)`
- `VARCHAR(36)` for UUIDs — use native `UUID` type
- Missing `NOT NULL` on columns that should never be empty
- Missing `CHECK` constraints for business rules
- JSONB for data that should be relational columns (filter/sort/aggregate/JOIN targets)

#### Lens 7: PostgreSQL-Specific Query Patterns

Patterns that leverage PostgreSQL's unique capabilities or avoid its specific pitfalls.

**Check for:**
- CTE materialization control (PG12+): `AS MATERIALIZED` / `AS NOT MATERIALIZED`
- LATERAL joins for top-N-per-group instead of correlated subqueries
- `ON CONFLICT` (UPSERT) for insert-or-update patterns
- Materialized views for expensive computations — `REFRESH CONCURRENTLY` requires unique index
- Exclusion constraints for scheduling/reservation problems
- Full-text search with `tsvector`/`tsquery` + GIN vs external search engine
- `COPY` for bulk loading (4-10x faster than INSERT)
- Batch inserts with `unnest()` arrays (2x faster than multi-row VALUES at batch size 1000)
- Mislabeled function volatility (IMMUTABLE on a VOLATILE function → stale results)
- Double-quoted mixed-case identifiers (forces perpetual quoting)

#### Lens 8: Monitoring and Diagnostics

PostgreSQL provides rich internal views for performance analysis.

**Essential diagnostic checks:**

```sql
-- Cache hit ratio (should be > 99%)
SELECT sum(blks_hit) * 100.0 / sum(blks_hit + blks_read) AS cache_hit_ratio
FROM pg_stat_database WHERE datname = current_database();

-- Top queries by total time (pg_stat_statements)
SELECT query, calls, round(total_exec_time::numeric, 2) AS total_ms,
       round(mean_exec_time::numeric, 2) AS mean_ms
FROM pg_stat_statements ORDER BY total_exec_time DESC LIMIT 10;

-- Tables most in need of vacuuming
SELECT relname, n_dead_tup, last_autovacuum, last_vacuum
FROM pg_stat_user_tables WHERE n_dead_tup > 10000 ORDER BY n_dead_tup DESC;

-- Unused indexes (wasting write overhead)
SELECT indexrelname, idx_scan, pg_size_pretty(pg_relation_size(indexrelid)) AS size
FROM pg_stat_user_indexes WHERE idx_scan = 0 ORDER BY pg_relation_size(indexrelid) DESC;

-- Transaction ID wraparound risk
SELECT datname, age(datfrozenxid) AS xid_age FROM pg_database ORDER BY xid_age DESC;
```

**Check for:**
- pg_stat_statements enabled (`shared_preload_libraries`)
- `log_min_duration_statement` set (e.g., 500ms) to log slow queries
- auto_explain enabled for automatic EXPLAIN on slow queries
- Inactive replication slots (cause unbounded WAL accumulation, fill disks)
- Cache hit ratio below 99% (insufficient shared_buffers or working set too large)
- `track_io_timing = on` for I/O-aware analysis

### Phase 3: Deliver Recommendations

Structure your response as:

1. **Summary** — One paragraph: the PostgreSQL environment, key issues, and expected impact.

2. **Findings** — Ordered by impact (highest first). For each:
   - What's wrong (with the specific PostgreSQL internals explanation)
   - Why it matters (quantified impact where possible)
   - The fix (concrete SQL, configuration, or DDL — never vague advice)

3. **Configuration Changes** — Exact `postgresql.conf` parameters with values and rationale.
   Group by: memory, WAL, planner, autovacuum, logging.

4. **DDL Changes** — Index creation (with CONCURRENTLY), partitioning setup, constraint additions.
   Always include exact statements.

5. **Monitoring Setup** — Which pg_stat views to watch, what thresholds to alert on,
   recommended extensions (pg_stat_statements, pgstattuple, auto_explain).

6. **Verification Steps** — How to confirm optimizations worked: EXPLAIN ANALYZE comparisons,
   pg_stat counters to check before/after, cache hit ratio monitoring.

---

## Anti-Pattern Quick Reference

| Anti-Pattern | Impact | Fix |
|---|---|---|
| Default `shared_buffers` (128MB) | Constant disk reads, low cache hit ratio | Set to 25% of RAM |
| `random_page_cost = 4.0` on SSD | Planner avoids index scans that would be fast | Set to 1.1 |
| Autovacuum scale_factor = 0.2 on large tables | 2M dead tuples before vacuum on 10M-row table | Per-table override: 0.01 |
| `VACUUM FULL` in production | ACCESS EXCLUSIVE lock blocks all reads/writes | Use pg_repack |
| `TIMESTAMP` without timezone | Silent timezone bugs in distributed systems | Always `TIMESTAMPTZ` |
| `SERIAL` for primary keys | INT overflow at ~2.1 billion rows | `BIGINT GENERATED ALWAYS AS IDENTITY` |
| `ENUM` types | Cannot remove values, hard to modify | `TEXT` + `CHECK` constraint |
| `JSON` instead of `JSONB` | Cannot index, cannot use containment operators | Always use `JSONB` |
| Missing FK indexes | Full table scans on DELETE/UPDATE of referenced row | Index every FK column |
| Random UUID v4 clustered | B-tree page splits, WAL amplification | UUID v7 (time-ordered) or BIGINT |
| GIN default ops when only `@>` needed | Larger, slower index | Use `jsonb_path_ops` operator class |
| BRING on randomly-ordered data | Index provides no selectivity | Check `correlation` in pg_stats first |
| Partitioning without partition key in queries | Scans all partitions — worse than no partitioning | Ensure queries filter on partition key |
| `max_connections = 1000` | Each connection costs ~10MB, resource exhaustion | Keep 100-200, use PgBouncer |
| Direct connections at scale | Fork-per-connection model doesn't scale | PgBouncer in transaction mode |
| Disabled autovacuum | Table bloat, eventual transaction ID wraparound shutdown | Never disable in production |
| Functions on partition key in WHERE | Prevents partition pruning | Use direct range comparisons |
| `trust` authentication in production | No password required, security breach | Use `scram-sha-256` |
| Superuser for application connections | Bypasses RLS, unnecessary privilege | Create app role with minimal grants |
| Inactive replication slots | Unbounded WAL accumulation, fills disk | Monitor and drop inactive slots |

---

## Modern PostgreSQL Features Worth Recommending

When optimizing, recommend version-appropriate features:

| Version | Feature | Optimization Opportunity |
|---------|---------|-------------------------|
| PG12+ | CTE inlining by default | Remove manual CTE-to-subquery rewrites |
| PG13+ | B-tree deduplication | Smaller indexes for repeated values (automatic) |
| PG14 | JSONB subscripting (`data['key']`) | Cleaner JSONB access syntax |
| PG14 | `SEARCH`/`CYCLE` for recursive CTEs | Built-in cycle detection |
| PG15 | MERGE command | SQL-standard upsert/delete in one statement |
| PG15 | `wal_compression = zstd` | Better compression than lz4/pglz |
| PG16 | pg_stat_io | Granular I/O monitoring by backend type |
| PG16 | `VACUUM (BUFFER_USAGE_LIMIT)` | Memory-controlled vacuuming |
| PG17 | Native incremental backup | Dramatically faster recovery (78min → 4min) |
| PG17 | JSON_TABLE | SQL-standard JSON-to-relational conversion |
| PG17 | TidStore for VACUUM | 20x VACUUM memory reduction |
| PG18 | Async I/O (`io_method = 'io_uring'`) | Up to 3x read performance |
| PG18 | Native `uuidv7()` | Time-ordered UUIDs without extensions |
| PG18 | Virtual generated columns | Computed on read, no storage cost |
| PG18 | B-tree skip scan | Multi-column indexes without leading column |
| PG18 | `OLD`/`NEW` in RETURNING | See before/after values from UPDATE |
