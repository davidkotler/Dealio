# Agent Routing — Domain-Specific Context

> How to enrich optimizer agent prompts with domain-specific conventions, context, and Definition of Done items.
>
> When dispatching agents in Step 6, match the agent's domain (from its filename prefix and description)
> to the sections below. Include the matching section in that agent's prompt.

---

## Application Performance Domain

**Agents:** `performance-optimizer` (and future agents like `memory-optimizer`, `cache-optimizer`)

### Codebase Conventions

- Follow `.claude/rules/principles.md`:
  - Section 1.8: Scale-Ready Design — design for 100x load
  - Section 2.11: Performance Awareness — generators, timeouts, O(n^2) avoidance
  - Section 1.4: Resilience Patterns — circuit breakers, timeouts, bulkheads
  - Section 1.7: Async-First — parallelize independent operations
- Use `lib-resilience` for external dependency calls: `http_call_policy`, `aws_call_policy`
- Use `lib-observability` for metrics: `get_meter` for performance metrics
- Keep optimizations targeted — don't refactor business logic under the guise of optimization

### Additional DoD Items

- Complexity analysis documented for algorithm changes (e.g., O(n^2) -> O(n log n))
- Generators used for large sequence processing (no materializing unbounded collections)
- Async operations parallelized where independent (`asyncio.gather()`, `TaskGroup`)
- Connection pooling verified for external calls

---

## SQL OLTP Domain

**Agents:** `sql-oltp-optimizer` (and future OLTP-focused agents)

### Codebase Conventions

- Follow `.claude/rules/principles.md`:
  - Section 3.6: Data Model Design — enumerate access patterns, correct types, constraints
  - Section 3.7: Aggregate Boundaries — one aggregate = one transaction
  - Section 3.8: Explicit Scaling Seams — repository interfaces for all data access
  - Section 3.4: Idempotent Operations — safely repeatable data operations
- Use `lib-database` for connection pools and instrumentation
- Repository pattern: SQL lives in adapter layer (`adapters/`), not in flows or routes
- PostgreSQL is the primary OLTP database (infer from codebase if not specified)

### Domain-Specific Context to Include in Prompt

- **Database platform and version** (if known from service settings or infra)
- **SQL file locations**: `**/adapters/**/*.py`, `**/repositories/**/*.py`, `**/migrations/**/*.sql`
- **ORM usage**: Check for SQLAlchemy, asyncpg, or raw SQL patterns
- **Pain point**: Slow queries, deadlocks, lock contention, or general schema review

### Additional DoD Items

- SARGability verified for all WHERE/JOIN/ON predicates (no functions on indexed columns)
- Index recommendations include exact CREATE INDEX DDL with ESR column ordering
- Transaction design follows defensive template (proper error handling, bounded duration)
- Concurrency patterns verified (no NOLOCK in production, RCSI recommended where appropriate)
- All findings include concrete SQL rewrites with before/after execution plan analysis, not vague advice

---

## SQL OLAP Domain

**Agents:** `sql-olap-optimizer` (and future analytics-focused agents)

### Codebase Conventions

- Follow `.claude/rules/principles.md`:
  - Section 3.6: Data Model Design — correct types, constraints
  - Section 2.11: Performance Awareness — pagination, bounded queries
- Analytical queries may live in: `**/queries/**`, `**/analytics/**`, `**/reports/**`, `**/*.sql`
- dbt models follow CTE pipeline architecture: import -> filter -> enrich -> aggregate -> output

### Domain-Specific Context to Include in Prompt

- **Target platform**: Snowflake, BigQuery, Redshift, PostgreSQL, ClickHouse, DuckDB
- **Query purpose**: Dashboard (latency-sensitive), ETL/dbt model (batch), ad-hoc analysis
- **Data scale**: Fact table row counts, partition strategy
- **Schema design**: Star schema, snowflake schema, or flat tables

### Additional DoD Items

- No `SELECT *` on columnar tables — explicit column projection only
- Partition pruning verified (no functions on partition columns in WHERE)
- Platform-specific optimizations applied (clustering keys, distribution keys, result caching)
- CTE pipeline architecture used for complex queries
- Window functions use named WINDOW clause when frames are shared
- Schema-level recommendations (materialized views, clustering) separated from query rewrites
- Cost impact estimated qualitatively for cloud warehouse queries

---

## PostgreSQL Domain

**Agents:** `postgresql-optimizer` (and future PostgreSQL-focused agents)

### Codebase Conventions

- Follow `.claude/rules/principles.md`:
  - Section 3.6: Data Model Design — enumerate access patterns, correct types, constraints
  - Section 3.7: Aggregate Boundaries — one aggregate = one transaction
  - Section 3.8: Explicit Scaling Seams — repository interfaces, connection pool abstraction
  - Section 1.10: Observability — structured logging, health probes
- Use `lib-database` for PostgreSQL connection pools, health checks, and instrumentation
- PostgreSQL-specific configuration lives in service `settings.py` and infrastructure code
- Database infrastructure in `infra/` directories

### Domain-Specific Context to Include in Prompt

- **PostgreSQL version** (from service config, docker-compose, or infra/cloud definitions)
- **Deployment model**: Self-managed, RDS, Aurora, Cloud SQL
- **Hardware profile**: RAM, CPU cores, storage type (if known from infra code)
- **Schema and migration files**: `**/migrations/**/*.sql`, `**/persistence/**/*.py`
- **Configuration files**: docker-compose.yml, Pulumi/Terraform PostgreSQL resources
- **Pain point**: Bloat, autovacuum, slow queries, high connections, partitioning, or general PG review

### Additional DoD Items

- Configuration recommendations include exact postgresql.conf parameter values
- Index type selection justified (B-tree vs GIN vs GiST vs BRING) with PostgreSQL engine rationale
- VACUUM/autovacuum health checked (dead tuples, last vacuum times, wraparound risk)
- Per-table autovacuum overrides provided for hot tables
- Connection pooling verified (PgBouncer or equivalent)
- All index DDL uses `CREATE INDEX CONCURRENTLY`
- PostgreSQL version-appropriate features recommended
- Verification queries provided for each recommendation

---

## Redis Domain

**Agents:** `redis-optimizer` (and future Redis-focused agents)

### Codebase Conventions

- Follow `.claude/rules/principles.md`:
  - Section 1.4: Resilience Patterns — circuit breakers, timeouts for Redis calls
  - Section 1.8: Scale-Ready Design — design for 100x load, minimize coordination points
  - Section 2.11: Performance Awareness — generators, timeouts, O(n^2) avoidance
  - Section 3.4: Idempotent Operations — safely repeatable Redis operations
  - Section 3.8: Explicit Scaling Seams — abstract cache access behind interfaces
- Redis is used as message broker (FastStream) and cache (see `local-env/compose.yaml`)
- Use `lib-resilience` for Redis call wrapping
- Use `lib-observability` for cache hit/miss metrics
- Redis client configuration lives in service `settings.py` and infrastructure code

### Domain-Specific Context to Include in Prompt

- **Redis version** (from docker-compose, infra/cloud definitions, or service config)
- **Deployment topology**: Standalone, Sentinel, Cluster, ElastiCache, Azure Cache
- **Workload type**: Cache, session store, message broker (Streams/Pub-Sub), rate limiter, mixed
- **Client library**: redis-py, ioredis, Jedis, Lettuce, node-redis
- **Redis usage files**: `**/adapters/**/*.py`, `**/infra/**/*.py`, `**/clients/**/*.py`
- **Configuration files**: docker-compose.yml, redis.conf, Pulumi/Helm Redis resources
- **Pain point**: High memory, latency spikes, connection issues, cache stampedes, data loss, hot keys

### Additional DoD Items

- Data structure selection justified with memory impact (`OBJECT ENCODING`, `MEMORY USAGE`)
- Compact encoding thresholds verified (listpack/intset not exceeded unintentionally)
- Key naming follows consistent `service:entity:id[:sub-entity]` convention
- Every cache key has explicit TTL (`SET ... EX`, never bare `SET` that strips existing TTL)
- O(N) commands eliminated from hot paths (`KEYS *` → `SCAN`, `DEL` → `UNLINK`, `HGETALL` → `HMGET`)
- Connection pooling configured with timeouts, health checks, and bounded pool size
- Pipelining used for batch operations (1,000-10,000 commands per pipeline)
- Lazy freeing enabled (all four `lazyfree-lazy-*` options)
- Persistence mode appropriate for workload (cache vs session store vs primary data)
- Configuration recommendations include exact redis.conf parameter values
- Verification commands provided (`SLOWLOG`, `MEMORY USAGE`, `OBJECT ENCODING`, hit ratio)

---

## Routing Review Findings to Agents

When review findings exist from Step 4, route them to the appropriate agent based on content:

| Finding Keywords | Route To |
|-----------------|----------|
| CPU, memory, I/O, async, generator, timeout, connection pool, algorithm, O(n) | Application performance agent |
| N+1 query, index, SARGability, transaction, deadlock, lock, isolation, stored procedure, OLTP | SQL OLTP agent |
| Partition pruning, warehouse, aggregation, window function, OLAP, analytical, scan cost, dbt | SQL OLAP agent |
| VACUUM, autovacuum, bloat, shared_buffers, work_mem, PgBouncer, GIN, GiST, BRING, pg_repack, pg_stat_statements, PostgreSQL config, partitioning, JSONB indexing, connection pooling, replication slot, wraparound | PostgreSQL agent |
| Redis, cache, TTL, eviction, pipelining, KEYS command, big key, HGETALL, UNLINK, Lua script, Streams, consumer group, rate limit, stampede, redis-py, connection pool (Redis context), maxmemory, listpack, hash bucketing, Sorted Set, Sentinel, Cluster (Redis context), SLOWLOG, cache hit ratio, hot key | Redis agent |
| General "slow query" or "inefficient" | Route by context: OLTP if transactional tables, OLAP if analytical/fact tables, PostgreSQL if PG-specific config/infrastructure, Redis if cache/in-memory data store |

A single review finding may be relevant to multiple agents. Include it in all relevant agent prompts.

---

## Adding New Optimization Domains

When a new `*-optimizer.md` agent appears in `.claude/agents/`:

1. The orchestrator automatically discovers it via the dynamic scan in Step 5
2. Read the new agent's `description` to understand its domain
3. Match it to code patterns found in the implementation files
4. Add a domain section to this file with: Codebase Conventions, Domain Context, Additional DoD Items
5. Add routing keywords to the "Routing Review Findings" table

The naming convention pairs agents to skills:
- Agent: `.claude/agents/{domain}-optimizer.md`
- Skill: `.claude/skills/optimize-{domain}/SKILL.md`

This keeps the orchestrator evolvable without modifying the main SKILL.md.
