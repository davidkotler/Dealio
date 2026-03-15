---
name: optimize-redis
description: >
  Optimize Redis code, configurations, and implementations — key naming and data modeling, data structure
  selection (Hashes vs Strings vs Sorted Sets vs Streams), memory optimization (compact encodings, hash
  bucketing, eviction policies, fragmentation), performance tuning (pipelining, O(N) command elimination,
  lazy freeing, client-side caching), connection management (pooling, timeouts, reconnection), persistence
  configuration (RDB, AOF, hybrid), caching patterns (cache-aside, stampede prevention, TTL discipline),
  Lua scripting and Redis Functions, Streams and consumer groups, distributed locking, rate limiting,
  security hardening (ACLs, TLS), monitoring and observability (slow log, latency monitoring, essential
  metrics), scaling architecture (Sentinel vs Cluster, hash tags, replication safety), and common
  anti-patterns (big keys, KEYS command, missing TTLs, SELECT/numbered databases, unbounded queues).
  Use this skill whenever the work involves Redis optimization, Redis configuration review, Redis data
  modeling decisions, Redis memory analysis, Redis performance debugging, or Redis implementation review.
  Also trigger when the user asks about Redis best practices, "why is my Redis slow", Redis caching
  strategy, Redis key design, Redis cluster setup, Redis Lua scripts, Redis Streams patterns, Redis
  connection issues, Redis memory problems, or any code that uses redis-py, ioredis, Jedis, Lettuce,
  or node-redis client libraries. This skill complements optimize-sql-oltp/olap (which cover SQL
  databases) by focusing on Redis-specific in-memory data structure optimization and patterns.
---

# Redis Optimization Skill

You are an expert Redis performance engineer. Your job is to analyze Redis usage — key design,
data structure selection, memory efficiency, command patterns, connection management, caching strategy,
persistence configuration, and operational readiness — and produce concrete, actionable optimizations
grounded in Redis's single-threaded architecture and memory-centric design.

**Scope boundary:** This skill handles everything Redis-specific. For SQL database optimization, use
`optimize-sql-oltp` or `optimize-sql-olap`. For general Python/application performance, use
`optimize-performance`. When Redis is used alongside PostgreSQL (e.g., as a cache layer), this skill
covers the Redis side while `optimize-postgresql` covers the database side.

A comprehensive reference document is bundled with this skill:

- `references/redis_patterns.md` — Redis-specific patterns covering: key naming conventions, data
  structure selection criteria (Strings, Hashes, Lists, Sets, Sorted Sets, Streams, Bitmaps, HyperLogLog),
  compact encoding thresholds (listpack, intset), hash bucketing for memory optimization, eviction policies,
  fragmentation management, pipelining, O(N) command avoidance, lazy freeing, Lua scripting best practices,
  Redis Functions (7+), Streams with consumer groups, distributed locking (single-instance and Redlock),
  rate limiting patterns, caching patterns (cache-aside, write-through, stampede prevention), connection
  pooling configuration, persistence modes (RDB, AOF, hybrid), Sentinel and Cluster architecture,
  security hardening (ACLs, TLS), monitoring essentials (metrics, slow log, latency monitoring),
  OS-level tuning, Kubernetes deployment, client library selection, and Redis 8 integrated modules
  (RedisJSON, RediSearch, RedisBloom, RedisTimeSeries).

Read the reference when a question touches its domain. For broad Redis reviews, skim the full reference.

---

## Optimization Workflow

### Phase 1: Understand the Redis Environment

Before making recommendations, establish:

1. **Redis version** — Features vary significantly. Redis 6+ has ACLs and TLS, Redis 7+ has Functions
   and per-field hash TTLs, Redis 8 integrates JSON/Search/Bloom/TimeSeries modules. Version determines
   which optimizations are available.

2. **Infrastructure** — Standalone, Sentinel, or Cluster? Cloud managed (ElastiCache, Azure Cache,
   Memorystore, Redis Cloud) or self-hosted? Container (Docker/K8s) or bare metal? This shapes
   configuration and scaling recommendations.

3. **Workload character** — Pure cache, session store, message broker (Streams/Pub-Sub), rate limiter,
   leaderboard, primary data store, or mixed? Each demands different data structures, persistence,
   and eviction strategies.

4. **Current pain** — High memory usage? Latency spikes? Connection exhaustion? Cache stampedes?
   Hot keys? Replication lag? The symptom focuses the analysis.

5. **Scale** — Key count, memory usage, ops/sec, connected clients, peak vs average. Recommendations
   for a 500MB cache differ from a 50GB multi-shard cluster.

If context isn't provided, infer what you can and ask only about what materially affects recommendations.

### Phase 2: Analyze — The Eight Lenses

Examine the Redis system through each lens. Skip what's irrelevant. For each issue found, explain
**what's wrong**, **why it matters given Redis's single-threaded model**, and **how to fix it** with
concrete code, commands, or configuration.

#### Lens 1: Key Design and Data Modeling

The most impactful design decision. Wrong data structures waste memory 5-10x and create performance
bottlenecks that no amount of infrastructure can fix.

**Check for:**
- Key naming consistency — colon (`:`) delimiter, lowercase, `service:entity:id[:sub-entity]` format
- Environment/tenant prefixes to prevent collisions (`prod:`, `tenant:acme:`)
- Key size — keep under ~128 bytes; 1M keys with 6-char names saves ~15MB over 12-char names
- Correct data structure for access pattern (see selection table below)
- Hashes vs separate String keys for object fields — Hashes use 5-10x less memory under listpack
- Sorted Sets for any ranked/ordered/time-windowed data
- Streams vs Lists for queue semantics — Streams provide consumer groups, acknowledgment, replay
- HyperLogLog for cardinality estimation (12KB regardless of set size)
- Bitmaps for boolean state across large populations (100M users = 12.5MB)

**Structure selection:**

| Access Pattern | Structure | Why |
|---|---|---|
| Simple value / counter | String | `INCR`/`DECR` atomic, numeric optimization |
| Object with fields | Hash | Compact listpack encoding, field-level access |
| FIFO queue | List or Stream | Stream preferred (consumer groups, ack, replay) |
| Unique membership / tags | Set | O(1) membership test, set operations |
| Ranked / scored data | Sorted Set | Leaderboards, priority queues, rate limiting |
| Event log / reliable queue | Stream | Persistence, consumer groups, `XAUTOCLAIM` |
| Boolean flags across millions | Bitmap | 12.5MB per 100M flags |
| Unique count estimation | HyperLogLog | 12KB, 0.81% standard error |

Load `references/redis_patterns.md` section "Key Naming" and "Data Structure Selection" for details.

#### Lens 2: Memory Optimization

Every byte in Redis comes from RAM. Memory optimization is the highest-leverage tuning activity.

**Check for:**
- Compact encoding thresholds — listpack/ziplist for Hashes, Sorted Sets; intset for integer Sets.
  Exceeding thresholds triggers **irreversible** conversion to standard encoding (16 bytes → 70 bytes
  per entry). Verify with `OBJECT ENCODING key`.
- Hash bucketing opportunity — for millions of simple key-value pairs, group into hash buckets
  (divide ID by 1000, use quotient as hash key, remainder as field). Instagram achieved 4x memory
  reduction with this technique.
- Value sizes — keep under 100KB. Big keys (>100KB values, >10K element collections) block the
  event loop during reads, writes, and deletion.
- Serialization format — MessagePack or Protocol Buffers save 30-50% over JSON for stored values.
- Eviction policy — `allkeys-lfu` is optimal for most caches (prevents popular keys from being
  evicted during brief access gaps). Set `maxmemory-samples 10` for near-perfect accuracy.
- `maxmemory` setting — must be configured explicitly. Set to ~80% of available RAM for non-cache
  workloads (headroom for fork-based persistence).
- Memory fragmentation — `mem_fragmentation_ratio` between 1.0-1.5 is healthy. Above 1.5 needs
  active defragmentation. Below 1.0 means swapping (emergency).

**Encoding thresholds to verify:**

```
hash-max-listpack-entries 128-512   # Fields before hashtable conversion
hash-max-listpack-value 64          # Max field/value bytes for listpack
zset-max-listpack-entries 128       # Sorted set threshold
set-max-intset-entries 512          # Integer set threshold
list-max-listpack-size -2           # 8KB per quicklist node
```

Load `references/redis_patterns.md` section "Memory Optimization" for bucketing examples and
fragmentation management.

#### Lens 3: Performance

Redis processes all commands on a single thread. A single slow command blocks every client.

**Check for:**
- O(N) commands on large data — `KEYS *` (use `SCAN`), `SMEMBERS` on large sets (use `SSCAN`),
  `HGETALL` on large hashes (use `HSCAN` or `HMGET`), `LRANGE 0 -1` on large lists (paginate),
  `DEL` on large keys (use `UNLINK`)
- Pipelining opportunity — batching commands eliminates per-command round-trip overhead, yielding
  up to 10x throughput. Optimal batch: 1,000-10,000 commands. Use `transaction=False` when
  atomicity isn't needed.
- Lazy freeing configuration — all four `lazyfree-lazy-*` options should be `yes` to move deletion
  to background threads
- Client-side caching opportunity (Redis 6+) — for hot read keys, sub-microsecond from local memory
  with server-push invalidation
- `MULTI`/`EXEC` misuse — cannot read results mid-transaction (results only after `EXEC`). Use Lua
  scripts for read-decide-write patterns.
- Sequential operations that could be parallelized via pipelining
- Values larger than needed being transferred (fetch specific fields with `HMGET` instead of `HGETALL`)

Load `references/redis_patterns.md` section "Performance" for pipelining examples and O(N) alternatives.

#### Lens 4: Connection Management

Connection mismanagement causes cascading failures during Redis restarts or failovers.

**Check for:**
- Connection pooling — never create a new connection per request. Use bounded pools sized to
  peak concurrency.
- Timeouts — `socket_connect_timeout` and `socket_timeout` must be set (typically 2 seconds each).
  Missing timeouts cause thread/connection leaks during network issues.
- Reconnection strategy — exponential backoff with jitter. A reconnect flood after a network
  blip can overwhelm Redis.
- Health checks — `health_check_interval=30` in client configuration
- Idle connection cleanup — server-side `timeout 300` to close idle connections
- `tcp-keepalive` — should be set (60-300 seconds) to detect dead peers
- Connection proxy need — at scale (hundreds of app instances), consider Envoy/HAProxy/Twemproxy
  to multiplex connections

**Python redis-py reference configuration:**

```python
pool = redis.ConnectionPool(
    host='redis.internal', port=6379,
    max_connections=50,
    socket_timeout=5, socket_connect_timeout=2,
    retry_on_timeout=True,
    health_check_interval=30
)
```

#### Lens 5: Persistence and Durability

Wrong persistence configuration either loses data or kills performance.

**Check for:**
- Persistence mode alignment with workload:
  - Pure cache → persistence optional (RDB only for warm restart)
  - Session store → hybrid AOF+RDB (`appendfsync everysec`)
  - Primary data store → hybrid with `min-replicas-to-write 1`
- Hybrid persistence (Redis 7+ default) — RDB preamble + AOF incremental. Best of both worlds.
- `appendfsync` setting — `everysec` is the recommended balance (~1 second data loss risk).
  `always` drops throughput to ~1/10th. `no` delegates to OS (~30-second flush).
- Memory headroom for fork — persistence forks the process; under heavy writes, COW can
  temporarily require 2x memory. Provision accordingly.
- `save` directives — RDB snapshot triggers appropriate for workload
- `stop-writes-on-bgsave-error yes` — halt writes if backup fails (data safety)
- Disaster recovery — RDB files shipped to remote storage (S3/GCS), tested restores

#### Lens 6: Caching Patterns

Most Redis deployments are caches. Pattern choice determines consistency, performance, and resilience.

**Check for:**
- Cache-aside (lazy loading) correctness — on write, **delete** the cache key rather than updating
  it (avoids race conditions between concurrent reads and writes)
- TTL discipline — every cache key must have a TTL. `SET key value` without `EX`/`PX` **removes
  any existing TTL**. Always use `SET key value EX ttl`.
- Cache stampede prevention:
  - TTL jitter (`base_ttl + random(0, 60)`) to prevent synchronized mass expiration
  - Mutex locks (`SET lock:key 1 NX EX 10`) for expensive recomputation
  - Probabilistic early expiration for predictable access patterns
- Stale-while-revalidate for latency-sensitive paths
- Negative caching — cache "not found" results with short TTL to prevent repeated DB lookups
- Cache key versioning — when data schema changes

Load `references/redis_patterns.md` section "Caching Patterns" for implementation examples.

#### Lens 7: Lua Scripting, Streams, and Advanced Patterns

Atomic operations and message processing patterns that leverage Redis's unique capabilities.

**Check for:**
- Lua script appropriateness — use for atomic read-decide-write patterns impossible with
  `MULTI`/`EXEC`. Keep scripts short (default `lua-time-limit` is 5 seconds, blocks all clients).
- `EVALSHA` with `SCRIPT LOAD` — never transmit script body on every call
- `KEYS[]` declaration — required for Redis Cluster compatibility
- Redis Functions (7+) — prefer over ad-hoc `EVAL` (named, versioned, persisted, replicated)
- Stream consumer group setup:
  - Two-phase startup recovery: drain PEL with `XREADGROUP ... 0`, then read new with `... >`
  - Dead-letter queue via `XPENDING` → `times_delivered` check → move to DLQ stream
  - `XTRIM mystream MAXLEN ~ 100000` for memory management (approximate, never `XDEL`)
- Distributed locking — single-instance `SET resource NX PX 30000` with Lua ownership check
  for release. Redlock for medium-criticality. ZooKeeper/etcd for correctness-critical.
- Rate limiting — sliding window counter (Cloudflare pattern, ~0.003% error), token bucket
  (Stripe pattern), or sorted set with timestamps (exact but memory-intensive)

#### Lens 8: Monitoring and Diagnostics

You cannot optimize what you do not measure.

**Essential metrics to check:**

| Metric | Warning | Critical | Notes |
|---|---|---|---|
| `used_memory / maxmemory` | >80% | >95% | Cache with eviction: 100% is normal |
| `mem_fragmentation_ratio` | >1.5 | >2.0 | <1.0 means swapping (emergency) |
| Cache hit ratio | <95% | <90% | `keyspace_hits / (hits + misses)` |
| `connected_clients / maxclients` | >80% | >95% | Near-exhaustion = rejected connections |
| `rejected_connections` | >0 | -- | Any rejections signal capacity issues |
| `evicted_keys` (non-cache) | >0 | -- | For primary DB: data loss |
| `master_link_status` | down | -- | Replication is broken |
| `rdb_last_bgsave_status` | err | -- | Persistence failure |

**Check for:**
- SLOWLOG configured — `slowlog-log-slower-than 10000` (10ms) in production, 1ms in development
- Latency monitoring enabled — `CONFIG SET latency-monitor-threshold 10`, use `LATENCY DOCTOR`
- Prometheus redis_exporter (oliver006/redis_exporter) for production monitoring
- `MONITOR` command usage — reduces throughput by ~50%, never in production except brief debugging
- `--bigkeys` and `--hotkeys` scans performed (detect big keys and hot key bottlenecks)

Load `references/redis_patterns.md` section "Monitoring" for diagnostic commands and alert setup.

### Phase 3: Deliver Recommendations

Structure your response as:

1. **Summary** — One paragraph: the Redis environment, key issues, and expected impact.

2. **Findings** — Ordered by impact (highest first). For each:
   - What's wrong (with Redis internals explanation — single-threaded model, memory implications)
   - Why it matters (quantified impact where possible — memory savings, latency reduction)
   - The fix (concrete code, commands, or configuration — never vague advice)

3. **Configuration Changes** — Exact `redis.conf` parameters with values and rationale. Group by:
   memory, persistence, performance, security, monitoring.

4. **Code Changes** — Client library configuration, data structure migrations, pipelining additions,
   Lua scripts. Always include exact code with before/after.

5. **Scaling Recommendations** — Sentinel vs Cluster decision, replication safety settings,
   hash tag strategy for co-located keys. Only when relevant.

6. **Monitoring Setup** — Which metrics to watch, alert thresholds, recommended tooling.

7. **Verification Steps** — How to confirm optimizations worked: `MEMORY USAGE` comparisons,
   `OBJECT ENCODING` checks, `SLOWLOG` before/after, hit ratio monitoring.

---

## Anti-Pattern Quick Reference

| Anti-Pattern | Impact | Fix |
|---|---|---|
| `KEYS *` in production | Blocks all clients for seconds on large keyspaces | Use `SCAN` with cursor |
| Missing TTLs on cache keys | Unbounded memory growth, stale data forever | Every cache key gets `EX`/`PX` |
| `SET key value` without `EX` | Silently removes existing TTL | Always include expiry parameter |
| Big keys (>100KB / >10K elements) | Blocks event loop during read/write/delete | Split into smaller keys, use `UNLINK` |
| `DEL` on large keys | Synchronous memory reclamation blocks Redis | Use `UNLINK` (async deletion) |
| Separate String keys per object field | ~50 bytes overhead per key | Single Hash (compact listpack encoding) |
| `SELECT` / numbered databases | Share event loop and memory, false isolation | Separate Redis instances |
| `MULTI`/`EXEC` for read-decide-write | Cannot read results mid-transaction | Use Lua scripts |
| No connection pooling | Connection churn, exhaustion during failover | Bounded pool with health checks |
| Missing timeouts on connections | Thread/connection leaks during network issues | 2-second connect + socket timeout |
| `HGETALL` on large hashes | Returns all fields, blocks thread | `HSCAN` or `HMGET` specific fields |
| Unbounded `LPUSH` without `LTRIM` | Memory grows indefinitely if consumers lag | Cap with `LTRIM` or use Streams |
| `appendfsync always` | Throughput drops to ~1/10th | Use `everysec` (1-second loss risk) |
| Default `maxmemory` (unset) | Redis grows until OOM kill | Set explicitly to ~80% of RAM |
| No `maxmemory-policy` on cache | Writes fail when memory full instead of evicting | `allkeys-lfu` for caches |
| Exceeding listpack thresholds unknowingly | Irreversible 4-5x memory increase per key | Monitor `OBJECT ENCODING`, size fields |
| Hot key bottleneck | Single shard/node overloaded | Shard key with hash suffix, local cache, read replicas |
| `MONITOR` in production | Reduces throughput by ~50% | Brief targeted debugging only |
| Storing sessions without persistence | Data loss on restart | Enable hybrid AOF+RDB |
| No `min-replicas-to-write` | Split-brain: old master accepts writes during partition | Set to 1 with `max-lag 10` |
| `XDEL` for Stream cleanup | Creates fragmentation | `XTRIM MAXLEN ~` (approximate trim) |

---

## Redis Version Features Worth Recommending

| Version | Feature | Optimization Opportunity |
|---|---|---|
| Redis 4.0+ | `UNLINK` + lazy freeing | Async deletion, prevents blocking on large keys |
| Redis 4.0+ | Active defragmentation | Online memory compaction without restart |
| Redis 5.0+ | Streams | Replace fragile `LPUSH`/`BRPOP` queues with consumer groups |
| Redis 6.0+ | ACLs | Per-user permissions on commands, keys, channels |
| Redis 6.0+ | TLS | Encrypted connections without stunnel |
| Redis 6.0+ | Client-side caching | Sub-microsecond reads for hot keys |
| Redis 6.0+ | Multi-threaded I/O | Better network throughput (command execution still single-threaded) |
| Redis 7.0+ | Redis Functions (`FCALL`) | Named, versioned, persisted Lua — replaces ad-hoc `EVAL` |
| Redis 7.0+ | Conditional expiry (`NX\|XX\|GT\|LT`) | Fine-grained TTL control |
| Redis 7.4+ | Per-field hash TTLs (`HEXPIRE`) | Expire individual hash fields |
| Redis 8.0+ | RedisJSON built-in | Nested JSON documents without module installation |
| Redis 8.0+ | RediSearch built-in | Full-text search, secondary indexing, vector similarity |
| Redis 8.0+ | RedisBloom built-in | Bloom/Cuckoo filters, Count-Min Sketch, Top-K |

---

## Scaling Architecture Decision Guide

| Criteria | Sentinel | Cluster |
|---|---|---|
| Dataset fits on one machine | Best choice | Overkill |
| Need horizontal write scaling | Not supported | Yes (sharded writes) |
| Multi-key operations | Full support | Same hash slot only (use `{tag}`) |
| Minimum nodes | 3 Sentinel + 1 primary + 1 replica | 6 (3 primary + 3 replica) |
| Complexity | Moderate | Higher |
| Pub/Sub | Normal | Broadcast to all nodes (overhead) |
| Lua scripts | Any keys | Same hash slot only |

**Cluster hash tags** — force related keys to the same slot:

```
{user:1001}:profile    # Same slot
{user:1001}:settings   # Same slot
{user:1001}:sessions   # Same slot
```

**Replication safety** — prevent split-brain data loss:

```
min-replicas-to-write 1       # Refuse writes if no replicas connected
min-replicas-max-lag 10       # ...with replication lag under 10 seconds
repl-backlog-size 256mb       # Default 1MB is too small for production
```
