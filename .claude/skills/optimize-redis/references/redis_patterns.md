# Redis Patterns Reference

Comprehensive reference for Redis optimization. Organized by domain for targeted lookup.

## Table of Contents

1. [Key Naming](#1-key-naming)
2. [Data Structure Selection](#2-data-structure-selection)
3. [Memory Optimization](#3-memory-optimization)
4. [Performance](#4-performance)
5. [Connection Management](#5-connection-management)
6. [Persistence](#6-persistence)
7. [Caching Patterns](#7-caching-patterns)
8. [Lua Scripting and Programmability](#8-lua-scripting-and-programmability)
9. [Streams and Message Processing](#9-streams-and-message-processing)
10. [Distributed Locking](#10-distributed-locking)
11. [Rate Limiting](#11-rate-limiting)
12. [Security](#12-security)
13. [Monitoring](#13-monitoring)
14. [Scaling Architecture](#14-scaling-architecture)
15. [OS and Infrastructure Tuning](#15-os-and-infrastructure-tuning)
16. [Client Library Configuration](#16-client-library-configuration)
17. [Redis 8 Integrated Modules](#17-redis-8-integrated-modules)

---

## 1. Key Naming

### Standard Format

Use colon (`:`) as hierarchical separator — universally adopted, recognized by tools like RedisInsight:

```
{service}:{entity}:{id}[:{sub-entity}]
```

```
prod:user:1001:profile          # User profile hash
cache:api:users:list            # Cached API response
lock:order:ORD-456              # Distributed lock
rate:api:user:1001              # Rate limiter
session:abc123                  # Session data
```

### Naming Rules

- Lowercase letters, numbers, colons, and underscores only
- Singular nouns for entities (`user:1001` not `users:1001`)
- Numeric IDs over user-generated strings (predictable, injection-resistant)
- Prefix ephemeral data: `cache:`, `temp:` for short-lived keys
- Version keys when structure changes: `v2:user:1001:profile`
- Keep keys under ~128 bytes (1M keys: 6-char names = ~96MB vs 12-char names = ~111MB)

### Namespace Prefixes

Always prefix to prevent collisions:

```
# Environment isolation
prod:user:1001:profile
staging:user:1001:profile

# Service isolation
auth:session:abc123
billing:invoice:7890

# Multi-tenant isolation
tenant:acme:user:1001:profile
```

### KeyBuilder Pattern

Enforce consistency in application code:

```python
class KeyBuilder:
    def __init__(self, service: str, env: str = "prod"):
        self.prefix = f"{env}:{service}"

    def user_profile(self, user_id: int) -> str:
        return f"{self.prefix}:user:{user_id}:profile"

    def cache_key(self, entity: str, identifier: str) -> str:
        return f"{self.prefix}:cache:{entity}:{identifier}"
```

### Schema Documentation

Store key schema alongside code or in Redis itself:

```
_schema:user:{id}          -> hash: name, email, created_at
_schema:session:{sid}      -> hash: user_id, created_at, ip (TTL: 86400)
_schema:cache:*            -> string (always has TTL)
```

---

## 2. Data Structure Selection

### Strings

Atomic values, counters, flags. Redis optimizes numeric strings as integers internally.

```
SET user:1001:login_count 0
INCR user:1001:login_count
SET cache:token:abc123 "session_data" EX 3600
```

Keep values under 100KB to avoid network/serialization overhead.

### Hashes

Objects with multiple fields. Dramatically more memory-efficient than separate string keys.

```
# Anti-pattern: separate keys per field (~50 bytes overhead EACH)
SET user:1001:name "Alice"
SET user:1001:email "alice@example.com"
SET user:1001:age "30"

# Correct: single hash (one key overhead, compact encoding)
HSET user:1001 name "Alice" email "alice@example.com" age "30"
```

Under listpack thresholds (default: 128 entries, 64-byte values), Hashes use 50-70% less memory.
Redis 7.4+ supports per-field TTLs with `HEXPIRE`.

### Lists

Ordered collections, queues, stacks. O(1) push/pop at both ends.

```
LPUSH queue:emails '{"to":"alice@example.com","subject":"Welcome"}'
RPOP queue:emails
LTRIM queue:emails 0 9999    # Cap at 10,000 elements
```

Always use `LTRIM` to prevent unbounded growth. Consider Streams for robust queue semantics.

### Sets

Unordered unique collections, membership testing, set operations.

```
SADD user:1001:roles "admin" "editor"
SISMEMBER user:1001:roles "admin"
SINTER user:1001:roles user:1002:roles
```

Integer-only sets use intset encoding (very compact).

### Sorted Sets

Ranked data, leaderboards, time-series indices, priority queues, sliding-window rate limiters.

```
ZADD leaderboard 9500 "player:42"
ZRANGE leaderboard 0 9 REV WITHSCORES
ZRANGEBYSCORE events 1700000000 +inf LIMIT 0 100
```

### Streams

Persistent, consumer-group-based message processing. Preferred over Lists for queues.

```
XADD events * type "order_placed" order_id "5001"
XREADGROUP GROUP processors worker1 COUNT 10 BLOCK 5000 STREAMS events >
XACK events processors 1234567890-0
```

### Specialized Structures

- **Bitmaps** — Boolean states across large populations. 100M users = ~12.5MB.
  `SETBIT feature:dark_mode 1001 1` / `GETBIT feature:dark_mode 1001`

- **HyperLogLog** — Probabilistic cardinality estimation. 12KB per counter, 0.81% standard error.
  `PFADD visitors:2024-01 "user:1001"` / `PFCOUNT visitors:2024-01`

- **Geospatial** — Coordinates and radius queries.
  `GEOADD locations -122.4194 37.7749 "san_francisco"` / `GEOSEARCH locations FROMMEMBER "san_francisco" BYRADIUS 50 km`

### Selection Decision Matrix

| Need | Structure | Key Decision Factor |
|---|---|---|
| "Is this the same X?" (identity) | String with unique key | Simple existence check |
| "What are all properties of X?" | Hash | Field-level access, compact encoding |
| "What happened in order?" | List (simple) / Stream (robust) | Need consumer groups? → Stream |
| "Does X belong to group Y?" | Set | O(1) membership, set operations |
| "What are the top N?" | Sorted Set | Score-based ordering |
| "How many unique?" | HyperLogLog | Approximate is OK, fixed 12KB |
| "Is feature on for user?" | Bitmap | Boolean per user, minimal memory |
| "Where is X near Y?" | Geo | Radius/box queries |
| "Nested/variable schema?" | RedisJSON (8+) | JSONPath queries, partial updates |
| "Full-text search needed?" | RediSearch (8+) | Stemming, scoring, fuzzy matching |
| "Approximate membership?" | Bloom filter (8+) | Zero false negatives, configurable FP rate |

---

## 3. Memory Optimization

### Compact Encoding Thresholds

Redis uses memory-efficient encodings for small collections. Exceeding **either** threshold triggers
an **irreversible** conversion to standard encoding — often 4-5x memory increase.

```conf
# Hashes: listpack for small hashes
hash-max-listpack-entries 128     # Max fields (can increase to 512)
hash-max-listpack-value 64        # Max field/value bytes

# Sorted Sets: listpack for small sorted sets
zset-max-listpack-entries 128
zset-max-listpack-value 64

# Sets: intset for integer-only sets
set-max-intset-entries 512
set-max-listpack-entries 128

# Lists: control node size
list-max-listpack-size -2         # -2 = 8KB per quicklist node
list-compress-depth 1             # Compress all but head/tail
```

Verify encodings: `OBJECT ENCODING key`
Audit memory: `MEMORY USAGE key`

Increasing thresholds trades CPU for memory. Profile your workload to find the balance.

### Hash Bucketing (Instagram Pattern)

For millions of simple key-value pairs, group into hash buckets. Each hash stays within listpack
thresholds, exploiting compact encoding.

```python
def store_value(redis_client, object_id: int, data: str) -> None:
    bucket = object_id // 1000
    field = object_id % 1000
    redis_client.hset(f"media:{bucket}", str(field), data)

def get_value(redis_client, object_id: int) -> str | None:
    bucket = object_id // 1000
    field = object_id % 1000
    return redis_client.hget(f"media:{bucket}", str(field))
```

Result: ~70 bytes/entry → ~16 bytes/entry (4x reduction). Instagram saved tens of gigabytes.

Choose bucket size to keep each hash under `hash-max-listpack-entries`. With default 128,
use divisor of 100. With increased threshold of 512, use divisor of 500.

### Value Serialization and Compression

```python
import zlib

def store_compressed(redis_client, key: str, data: str, ttl: int = 3600) -> None:
    compressed = zlib.compress(data.encode(), level=6)
    redis_client.setex(key, ttl, compressed)

def get_compressed(redis_client, key: str) -> str | None:
    compressed = redis_client.get(key)
    return zlib.decompress(compressed).decode() if compressed else None
```

Reserve compression for medium-to-low frequency access. Hot keys should avoid CPU overhead.
MessagePack/Protocol Buffers reduce serialized size 30-50% vs JSON without compression overhead.

### Eviction Policies

| Policy | Use Case |
|---|---|
| `noeviction` | Primary data store — return errors when full |
| `allkeys-lru` | General-purpose cache — evict least recently used |
| `allkeys-lfu` | Cache with frequency bias — evict least frequently used (recommended) |
| `volatile-lru` | Evict only keys with TTL set (LRU) — some keys must persist |
| `volatile-ttl` | Evict keys closest to expiration |

Set `maxmemory-samples 10` (default 5) for near-perfect eviction accuracy.

### Fragmentation Management

Monitor `mem_fragmentation_ratio` (RSS / used_memory):
- 1.0–1.5: Healthy
- 1.5–2.0: Enable active defragmentation
- >2.0: Requires intervention
- <1.0: Swapping to disk (emergency — increase memory immediately)

```conf
activedefrag yes
active-defrag-ignore-bytes 100mb
active-defrag-threshold-lower 10      # Start at 10% fragmentation
active-defrag-cycle-min 5             # Minimum CPU %
active-defrag-cycle-max 75            # Maximum CPU %
```

---

## 4. Performance

### Pipelining

Send multiple commands without waiting for individual responses. Eliminates per-command network
round-trip overhead. Up to 10x throughput improvement.

```python
# Without pipelining: 10,000 round trips
for i in range(10000):
    r.set(f"key:{i}", f"value:{i}")

# With pipelining: 1 round trip
pipe = r.pipeline(transaction=False)  # No MULTI/EXEC overhead
for i in range(10000):
    pipe.set(f"key:{i}", f"value:{i}")
pipe.execute()
```

Optimal batch: 1,000–10,000 commands. Larger batches increase server memory from queued replies.
Use `transaction=False` for maximum throughput when atomicity isn't needed.

### O(N) Command Alternatives

| Dangerous Command | Risk | Safe Alternative |
|---|---|---|
| `KEYS *` | Scans entire keyspace, blocks all | `SCAN` with cursor |
| `SMEMBERS` on large set | Returns all members at once | `SSCAN` |
| `HGETALL` on large hash | Returns all fields | `HSCAN` or `HMGET` specific fields |
| `LRANGE 0 -1` on large list | Returns entire list | Paginate with bounded ranges |
| `SORT` on large collections | CPU-intensive sort | Pre-compute sorted results |
| `DEL` on large key | Blocks while freeing memory | `UNLINK` (async deletion) |

### Lazy Freeing Configuration

Move deletion to background threads:

```conf
lazyfree-lazy-eviction yes
lazyfree-lazy-expire yes
lazyfree-lazy-server-del yes
lazyfree-lazy-user-del yes       # Makes DEL behave like UNLINK
```

### Client-Side Caching (Redis 6+)

Redis tracks which keys each client reads and pushes invalidation messages when those keys change.
Sub-microsecond reads from local memory for hot keys.

Ideal for: configuration data, feature flags, frequently-read reference data.

---

## 5. Connection Management

### Connection Pooling

```python
import redis

pool = redis.ConnectionPool(
    host='redis.internal',
    port=6379,
    password='strong_password',
    max_connections=50,
    socket_timeout=5,
    socket_connect_timeout=2,
    retry_on_timeout=True,
    health_check_interval=30
)
client = redis.Redis(connection_pool=pool)
```

### Server-Side Settings

```conf
maxclients 10000              # Default 10000
timeout 300                   # Close idle connections after 5 minutes
tcp-keepalive 60              # Detect dead peers every 60 seconds
```

### Reconnection Strategy

Implement exponential backoff with jitter:

```python
import random
import time

def connect_with_backoff(max_retries: int = 10) -> redis.Redis:
    for attempt in range(max_retries):
        try:
            client = redis.Redis(host='redis.internal', port=6379)
            client.ping()
            return client
        except redis.ConnectionError:
            delay = min(2 ** attempt, 30) + random.uniform(0, 1)
            time.sleep(delay)
    raise RuntimeError("Failed to connect to Redis")
```

Jitter prevents thundering herd when many clients reconnect simultaneously after an outage.

### Connection Proxies

For large-scale deployments (hundreds of app instances):
- Reduces total connections to Redis
- Absorbs reconnection storms
- Can provide transparent failover and read/write splitting
- Options: Envoy, HAProxy, Twemproxy

---

## 6. Persistence

### Mode Comparison

| Mode | Data Loss Risk | Performance Impact | Best For |
|---|---|---|---|
| RDB only | Minutes of data | Low (background fork) | Backups, warm restart |
| AOF `everysec` | ~1 second | Moderate | Session stores, mixed workloads |
| AOF `always` | None | ~10x throughput drop | Financial transactions |
| Hybrid (RDB+AOF) | ~1 second | Moderate | Recommended default |

### Recommended Hybrid Configuration

```conf
appendonly yes
aof-use-rdb-preamble yes           # RDB preamble + AOF incremental (Redis 7+ default)
appendfsync everysec               # ~1 second data loss risk

auto-aof-rewrite-percentage 100
auto-aof-rewrite-min-size 64mb

save 3600 1                        # RDB backup every hour if >=1 change
save 300 100                       # Every 5 min if >=100 changes
save 60 10000                      # Every minute if >=10K changes

stop-writes-on-bgsave-error yes    # Halt writes if backup fails
```

### Memory Overhead

Fork-based persistence uses copy-on-write. Under heavy writes, most pages get copied, potentially
**doubling memory usage**. Provision at least 2x dataset size in RAM when persistence is enabled.

### Backup Strategy

- Trigger `BGSAVE` and wait for completion before copying RDB files
- Ship RDB to remote storage (S3, GCS) on schedule
- Test restores regularly — an untested backup is not a backup
- When both RDB and AOF exist at startup, Redis loads AOF (more complete)

---

## 7. Caching Patterns

### Cache-Aside (Lazy Loading)

```python
def get_user(user_id: int) -> User:
    cached = redis_client.get(f"cache:user:{user_id}")
    if cached:
        return deserialize(cached)

    user = database.query_user(user_id)
    redis_client.setex(f"cache:user:{user_id}", 3600, serialize(user))
    return user
```

On writes, **delete** the cache key — never update it (avoids race conditions):

```python
def update_user(user_id: int, data: dict) -> None:
    database.update_user(user_id, data)
    redis_client.delete(f"cache:user:{user_id}")  # Delete, don't update
```

### TTL Discipline

**Every cached key must have a TTL. No exceptions.**

Critical trap: `SET key value` without `EX`/`PX` **removes any existing TTL**. Always include expiry.

```python
# WRONG — removes TTL if key existed with one
redis_client.set("cache:user:1001", data)

# CORRECT — always set TTL
redis_client.setex("cache:user:1001", 3600, data)
# or
redis_client.set("cache:user:1001", data, ex=3600)
```

### TTL Jitter

Prevent synchronized mass expiration (thundering herd):

```python
import random

base_ttl = 3600
jitter = random.randint(0, 300)  # 0-5 minutes of jitter
redis_client.setex(key, base_ttl + jitter, value)
```

### Stampede Prevention

When a hot key expires, hundreds of requests simultaneously miss and flood the backend.

**Mutex lock pattern:**

```python
def get_with_lock(key: str) -> str | None:
    cached = redis_client.get(key)
    if cached:
        return cached

    lock_key = f"lock:{key}"
    if redis_client.set(lock_key, "1", nx=True, ex=10):
        try:
            value = compute_expensive_value()
            redis_client.setex(key, 3600, value)
            return value
        finally:
            redis_client.delete(lock_key)
    else:
        # Another request is computing — wait and retry
        time.sleep(0.1)
        return redis_client.get(key)
```

**Probabilistic early expiration:**

Refresh before TTL expires with increasing probability as expiration approaches.

### Write-Through

```python
def update_user(user_id: int, data: dict) -> None:
    database.update_user(user_id, data)
    redis_client.setex(f"cache:user:{user_id}", 3600, serialize(data))
```

Cache always fresh after writes, but may cache unused data and adds write latency.

---

## 8. Lua Scripting and Programmability

### When to Use Lua

- Atomic multi-step operations impossible with `MULTI`/`EXEC`
- Conditional logic: read-then-decide-then-write patterns
- Reducing round-trips for compute-near-data patterns

### Best Practices

- Pre-load with `SCRIPT LOAD`, invoke with `EVALSHA` — avoid transmitting script body every call
- Keep scripts short — blocks all clients for entire duration
- Always declare keys with `KEYS[]` — required for Cluster compatibility
- Never perform unbounded loops inside scripts
- Default `lua-time-limit` is 5 seconds

### Lock Release Pattern

```lua
-- Release lock only if we own it
if redis.call('get', KEYS[1]) == ARGV[1] then
    return redis.call('del', KEYS[1])
else
    return 0
end
```

### Redis Functions (7+)

Preferred over ad-hoc `EVAL` — named, versioned, persisted, and replicated:

```
FUNCTION LOAD "#!lua name=mylib\nredis.register_function('myfunc', function(keys, args) ... end)"
FCALL myfunc 1 key1 arg1
```

---

## 9. Streams and Message Processing

### Consumer Group Setup

```
XGROUP CREATE events processors $ MKSTREAM
```

### Two-Phase Startup Recovery

Critical pattern: on consumer startup, first drain pending messages, then read new ones.

```python
# Phase 1: Recover pending messages (delivered but not acknowledged)
while True:
    messages = redis_client.xreadgroup(
        groupname="processors", consumername="worker1",
        streams={"events": "0"},  # "0" = pending messages
        count=10
    )
    if not messages or not messages[0][1]:
        break
    for stream, entries in messages:
        for msg_id, fields in entries:
            process(fields)
            redis_client.xack("events", "processors", msg_id)

# Phase 2: Read new messages
while True:
    messages = redis_client.xreadgroup(
        groupname="processors", consumername="worker1",
        streams={"events": ">"},  # ">" = new messages only
        count=10, block=5000
    )
    if messages:
        for stream, entries in messages:
            for msg_id, fields in entries:
                process(fields)
                redis_client.xack("events", "processors", msg_id)
```

### Dead-Letter Queue

Check `times_delivered` in `XPENDING` and move poison pills to DLQ after threshold:

```python
pending = redis_client.xpending_range("events", "processors", "-", "+", 100)
for entry in pending:
    if entry["times_delivered"] > 3:
        # Move to dead-letter queue
        msg = redis_client.xrange("events", entry["message_id"], entry["message_id"])
        if msg:
            redis_client.xadd("events:dlq", msg[0][1])
            redis_client.xack("events", "processors", entry["message_id"])
```

### Stream Memory Management

```
XTRIM mystream MAXLEN ~ 100000    # Approximate trim (efficient)
```

Never use `XDEL` for cleanup — it creates fragmentation. The `~` flag allows Redis to trim
efficiently by removing entire macro-nodes rather than exact element count.

---

## 10. Distributed Locking

### Single-Instance Lock (Efficiency Lock)

Prevents duplicate work. Single point of failure.

```python
import uuid

lock_value = str(uuid.uuid4())

# Acquire
acquired = redis_client.set(
    "lock:order:ORD-456",
    lock_value,
    nx=True,    # Only if not exists
    px=30000    # 30-second TTL
)

if acquired:
    try:
        process_order("ORD-456")
    finally:
        # Release via Lua (atomic check-and-delete)
        release_script = """
        if redis.call('get', KEYS[1]) == ARGV[1] then
            return redis.call('del', KEYS[1])
        else
            return 0
        end
        """
        redis_client.eval(release_script, 1, "lock:order:ORD-456", lock_value)
```

### Redlock (Medium-Criticality)

Extends across 5 independent Redis masters, requiring majority (3/5) to acquire.

Community consensus (Kleppmann critique): unsafe for correctness-critical locks because it lacks
fencing tokens and depends on clock synchronization. Use ZooKeeper/etcd for safety-critical locking.

### Lock Selection Guide

| Criticality | Lock Type | Example |
|---|---|---|
| Efficiency (prevent duplicate work) | Single-instance | Cache refresh, batch job dedup |
| Medium (important but not financial) | Redlock | Order processing, resource allocation |
| Correctness-critical | ZooKeeper/etcd | Financial transactions, inventory |

---

## 11. Rate Limiting

### Sliding Window Counter (Cloudflare Pattern)

Best accuracy-to-memory ratio. ~0.003% error rate across 400M requests.

Maintain two counters per window, weight previous window's count by overlap:

```python
import time

def is_rate_limited(user_id: str, limit: int, window: int = 60) -> bool:
    now = time.time()
    current_window = int(now // window)
    previous_window = current_window - 1
    elapsed = now % window

    pipe = redis_client.pipeline()
    pipe.get(f"rate:{user_id}:{current_window}")
    pipe.get(f"rate:{user_id}:{previous_window}")
    current_count, previous_count = pipe.execute()

    current_count = int(current_count or 0)
    previous_count = int(previous_count or 0)

    # Weight previous window by overlap
    weighted = previous_count * ((window - elapsed) / window) + current_count

    if weighted >= limit:
        return True

    pipe = redis_client.pipeline()
    pipe.incr(f"rate:{user_id}:{current_window}")
    pipe.expire(f"rate:{user_id}:{current_window}", window * 2)
    pipe.execute()
    return False
```

### Token Bucket (Stripe Pattern)

Compact Lua script tracking remaining tokens and last-refill timestamp. Allows burst up to bucket capacity.

### Sorted Set (Exact Counting)

Precise but memory-intensive at scale:

```python
def check_rate(user_id: str, limit: int, window: int = 60) -> bool:
    now = time.time()
    key = f"rate:{user_id}"
    pipe = redis_client.pipeline()
    pipe.zremrangebyscore(key, 0, now - window)  # Remove old entries
    pipe.zadd(key, {str(now): now})               # Add current request
    pipe.zcard(key)                                # Count in window
    pipe.expire(key, window)                       # TTL safety net
    _, _, count, _ = pipe.execute()
    return count > limit
```

---

## 12. Security

### ACLs (Redis 6+)

```
# Application user — restricted to app keys, no dangerous commands
ACL SETUSER app-service on >strong_password ~app:* +@all -@dangerous -@admin

# Read-only analytics user
ACL SETUSER analytics on >analytics_pass ~orders:* ~customers:* +@read -@write

# Admin user — full access
ACL SETUSER admin on >admin_password allkeys allcommands
```

The `@dangerous` category: `FLUSHALL`, `FLUSHDB`, `KEYS`, `DEBUG`, `CONFIG`, `SHUTDOWN`.
Remove from all non-admin users.

### TLS Encryption (Redis 6+)

```conf
port 0                             # Disable unencrypted port
tls-port 6379
tls-cert-file /path/to/redis.crt
tls-key-file /path/to/redis.key
tls-ca-cert-file /path/to/ca.crt
tls-protocols "TLSv1.2 TLSv1.3"
tls-replication yes                # Encrypt replica connections
tls-cluster yes                    # Encrypt cluster bus
```

### Network Security

- Never expose Redis to the public internet
- Bind to specific interfaces (`bind 10.0.1.1 127.0.0.1`)
- Deploy within private VPC
- Firewall: allow 6379 from trusted hosts only, 26379 (Sentinel) between Redis/Sentinel nodes,
  client_port + 10000 (Cluster bus) between cluster nodes

### Command Restriction (Legacy)

```conf
rename-command FLUSHALL ""
rename-command FLUSHDB ""
rename-command DEBUG ""
rename-command CONFIG ""
rename-command KEYS ""
```

Prefer ACLs (Redis 6+) over rename-command.

---

## 13. Monitoring

### Essential Diagnostic Commands

```bash
redis-cli INFO memory              # Memory statistics
redis-cli INFO stats               # Hit/miss ratio, ops/sec
redis-cli INFO replication         # Replica health
redis-cli INFO clients             # Connected clients

redis-cli --stat                   # Live stats: keys, memory, ops/sec
redis-cli --bigkeys                # Scan for largest keys per type
redis-cli --hotkeys                # Find hottest keys (requires LFU policy)
redis-cli --latency                # Continuous latency sampling
redis-cli --intrinsic-latency 5    # Measure baseline OS/hardware latency

redis-cli MEMORY USAGE key         # Memory for specific key
redis-cli MEMORY DOCTOR            # Automated analysis
redis-cli OBJECT ENCODING key      # Current encoding (listpack/hashtable/etc.)

redis-cli SLOWLOG GET 10           # Recent slow commands
redis-cli SLOWLOG LEN              # Count of slow commands logged

redis-cli LATENCY LATEST           # Latest latency events
redis-cli LATENCY DOCTOR           # Human-readable latency diagnostics
```

### SLOWLOG Configuration

```conf
slowlog-log-slower-than 10000      # Log commands > 10ms (production)
slowlog-max-len 128                # Keep last 128 entries
```

In development: lower threshold to 1ms (1000 microseconds).

### Latency Monitoring

```
CONFIG SET latency-monitor-threshold 10    # Track events > 10ms
LATENCY LATEST                             # See latest events
LATENCY DOCTOR                             # Diagnostic advice
```

### Production Monitoring Stack

Deploy Prometheus redis_exporter (oliver006/redis_exporter) — exports ~190 metrics.
Import Grafana dashboard ID 14091 for comprehensive visualization.

### Alert Thresholds

| Metric | Warning | Critical |
|---|---|---|
| Memory usage (`used_memory / maxmemory`) | >80% | >95% |
| Fragmentation ratio | >1.5 | >2.0 (or <1.0) |
| Cache hit ratio | <95% | <90% |
| Connected clients / maxclients | >80% | >95% |
| Rejected connections | >0 | -- |
| Evicted keys (non-cache workload) | >0 | -- |
| Replication link status | down | -- |
| BGSAVE status | error | -- |
| Replication lag | >configured max-lag | -- |
| SLOWLOG growth rate | rapid increase | -- |

---

## 14. Scaling Architecture

### Sentinel (HA for Single-Node Datasets)

```conf
sentinel monitor mymaster 192.168.1.10 6379 2
sentinel down-after-milliseconds mymaster 5000
sentinel parallel-syncs mymaster 1
sentinel failover-timeout mymaster 60000
```

- Minimum 3 Sentinels on separate machines/AZs
- Quorum (typically 2 of 3) determines master-down detection
- Majority required for actual failover
- Docker/NAT: use `sentinel announce-ip` and `sentinel announce-port`

### Cluster (Horizontal Scaling)

- 16,384 hash slots: `CRC16(key) % 16384`
- Minimum 6 nodes (3 masters + 3 replicas)
- Multi-key operations: same slot only (use hash tags `{tag}`)
- Cluster bus: binary gossip on `client_port + 10000`

**Hash tags for co-located keys:**

```
SET {user:1001}:profile "..."
SET {user:1001}:settings "..."
MGET {user:1001}:profile {user:1001}:settings    # Same slot, works
```

### Replication Safety

```conf
min-replicas-to-write 1           # Refuse writes if no replicas
min-replicas-max-lag 10           # ...with lag under 10 seconds
repl-backlog-size 256mb           # Default 1MB is too small
```

Backlog size: `write_throughput_bytes_per_sec * max_expected_disconnect_seconds`.
Insufficient backlog forces full resync (expensive RDB dump + transfer).

### Scaling Decisions

- Scale reads: add replicas, direct read traffic to them
- Scale writes: add primary nodes (Cluster), rebalance slots
- Shard when data exceeds 25GB or ops exceed 25,000/sec per instance

---

## 15. OS and Infrastructure Tuning

### Linux Kernel Parameters

```bash
# Prevent fork() failures during BGSAVE
echo 'vm.overcommit_memory = 1' >> /etc/sysctl.conf

# Disable Transparent Huge Pages (causes latency spikes during fork COW)
echo never > /sys/kernel/mm/transparent_hugepage/enabled

# Match tcp-backlog setting
echo 'net.core.somaxconn = 65535' >> /etc/sysctl.conf

# Minimize swapping
echo 'vm.swappiness = 1' >> /etc/sysctl.conf

# File descriptors: >= maxclients + 32
# In systemd service: LimitNOFILE=65536
```

### Redis Configuration Essentials

```conf
tcp-backlog 65536              # Default 511; match with kernel somaxconn
timeout 300                    # Close idle connections after 5 minutes
maxclients 65536               # Requires matching file descriptor limits
tcp-keepalive 300              # Detect dead peers
hz 10                          # Event loop frequency (100 for low-latency)
dynamic-hz yes                 # Auto-adjust based on load
```

### Kubernetes Deployment

- **StatefulSets** (not Deployments) for stable network identity and persistent storage
- Container memory limits **~20% above** Redis `maxmemory` (overhead, COW, client buffers)
- SSD-backed PersistentVolumeClaims
- `readinessProbe` and `livenessProbe` with `redis-cli ping`
- `PodDisruptionBudget` for availability during upgrades
- `vm.overcommit_memory` and THP settings at **host node level** (DaemonSet or node config)
- Anti-affinity rules to spread primary/replica across nodes/AZs

---

## 16. Client Library Configuration

### Python (redis-py)

Use `hiredis` parser for ~10% speedup:

```python
import redis

pool = redis.ConnectionPool(
    host='redis.internal',
    port=6379,
    password='strong_password',
    max_connections=50,
    socket_timeout=5,
    socket_connect_timeout=2,
    retry_on_timeout=True,
    health_check_interval=30
)
client = redis.Redis(connection_pool=pool)
```

Install: `pip install redis[hiredis]`

### Java

- **Jedis** — simpler, up to 2x faster in benchmarks. Good for synchronous patterns.
- **Lettuce** — suits async/reactive applications. Non-blocking I/O.

### Node.js

Official `node-redis` is now recommended over ioredis.

### Universal Configuration Principles

- Always set connection and socket timeouts (2 seconds)
- Use bounded connection pools sized to peak concurrency
- Implement exponential backoff with jitter on reconnection
- Enable health checks (`health_check_interval=30`)

---

## 17. Redis 8 Integrated Modules

As of Redis 8 (GA 2025), all previously separate modules are built into Redis Open Source (AGPL v3).

### RedisJSON

Store nested JSON with partial-path updates and JSONPath queries:

```
JSON.SET user:1001 $ '{"name":"Alice","address":{"city":"NYC"}}'
JSON.GET user:1001 $.address.city
JSON.NUMINCRBY user:1001 $.login_count 1
```

Use instead of Hashes when: data has nested structures or variable schemas.
Hashes remain more efficient for flat objects where performance/memory are critical.

### RediSearch

Full-text search with stemming, scoring, fuzzy matching + secondary indexing:

```
FT.CREATE idx:users ON HASH PREFIX 1 user: SCHEMA
    name TEXT SORTABLE
    email TAG
    age NUMERIC SORTABLE
    location GEO

FT.SEARCH idx:users "@name:Alice @age:[25 35]"
FT.AGGREGATE idx:users "@location:[-122.4 37.7 50 km]" GROUPBY 1 @city REDUCE COUNT 0 AS count
```

Auto-indexes new keys matching prefix. Supports TEXT, NUMERIC, TAG, GEO, and VECTOR field types.

### RedisBloom

- **Bloom filters** — set membership in ~10 bits/item, configurable false positive rate,
  zero false negatives: `BF.ADD`, `BF.EXISTS`
- **Cuckoo filters** — add deletion support: `CF.ADD`, `CF.DEL`, `CF.EXISTS`
- **Count-Min Sketch** — estimate item frequency in sub-linear memory: `CMS.INCRBY`, `CMS.QUERY`
- **Top-K** — track K most frequent items with fixed memory: `TOPK.ADD`, `TOPK.LIST`

---

## Production Configuration Template

```conf
# --- Network ---
bind 10.0.1.1 127.0.0.1
port 6379
protected-mode yes
tcp-backlog 511
tcp-keepalive 60
timeout 300

# --- Security ---
requirepass YOUR_STRONG_PASSWORD
# ACL file for fine-grained access (Redis 6+)
# aclfile /etc/redis/users.acl

# --- Memory ---
maxmemory 4gb
maxmemory-policy allkeys-lfu
maxmemory-samples 10
lazyfree-lazy-eviction yes
lazyfree-lazy-expire yes
lazyfree-lazy-server-del yes
lazyfree-lazy-user-del yes

# --- Persistence (Hybrid) ---
appendonly yes
appendfsync everysec
aof-use-rdb-preamble yes
save 3600 1
save 300 100
save 60 10000
stop-writes-on-bgsave-error yes

# --- Encoding Thresholds ---
hash-max-listpack-entries 128
hash-max-listpack-value 64
zset-max-listpack-entries 128
zset-max-listpack-value 64
set-max-intset-entries 512
list-max-listpack-size -2
list-compress-depth 1

# --- Performance ---
slowlog-log-slower-than 10000
slowlog-max-len 128
latency-monitor-threshold 100
activedefrag yes
hz 10
dynamic-hz yes

# --- Replication ---
# replicaof <master-ip> <master-port>
# masterauth YOUR_STRONG_PASSWORD
min-replicas-to-write 1
min-replicas-max-lag 10
repl-backlog-size 256mb
```
