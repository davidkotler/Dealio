# Cache Patterns Reference

Comprehensive reference for cache optimization. Organized by domain for targeted lookup.
Technology-agnostic — patterns apply to Redis, Memcached, Caffeine, CDN, HTTP, or any caching layer.

## Table of Contents

1. [Cache Strategies](#1-cache-strategies)
2. [Invalidation Patterns](#2-invalidation-patterns)
3. [Stampede Prevention](#3-stampede-prevention)
4. [Eviction Policies](#4-eviction-policies)
5. [Cache Key Design](#5-cache-key-design)
6. [Multi-Layer Architecture](#6-multi-layer-architecture)
7. [Failure Modes](#7-failure-modes)
8. [HTTP Caching](#8-http-caching)
9. [Serialization](#9-serialization)
10. [Observability](#10-observability)
11. [Cache Warming](#11-cache-warming)
12. [Code-Level Conventions](#12-code-level-conventions)
13. [Real-World Patterns](#13-real-world-patterns)

---

## 1. Cache Strategies

### Cache-Aside (Lazy Loading) — The Default

Application checks cache → on miss, queries data source → populates cache → returns result.

```python
async def get_user(self, user_id: str) -> User:
    cached = await self.cache.get(f"user:{user_id}")
    if cached is not None:
        return cached

    user = await self.repository.find_by_id(user_id)
    await self.cache.set(f"user:{user_id}", user, ttl=300)
    return user
```

**Strengths:** Simple, resilient to cache failure (falls back to DB), only caches requested data.
**Weaknesses:** First request always misses (cold start), risk of thundering herd on popular key expiry.
**Best for:** Read-heavy workloads, user profiles, product catalogs, configuration data.

**Critical pattern — delete-on-write, not update-on-write:**

On write, **delete** the cache key rather than updating it. Updating creates a race condition:
1. Thread A reads from DB (gets old value)
2. Thread B writes new value to DB + cache
3. Thread A writes old value to cache (stale!)

Deleting avoids this — the next read simply misses and fetches fresh data.

```python
async def update_user(self, user_id: str, data: UpdateUserData) -> User:
    user = await self.repository.update(user_id, data)
    await self.cache.delete(f"user:{user_id}")  # DELETE, not SET
    return user
```

### Read-Through

Cache itself loads data on miss. Application only talks to cache.

**Strengths:** Simplifies application code, cache manages population logic, naturally serializes
loads per key (prevents stampede).
**Weaknesses:** Tighter coupling, cache library must support the pattern, harder to customize.
**Best for:** ORM-level caching (Hibernate L2), uniform data access layers.

### Write-Through

Every write goes to both cache and data source synchronously.

```python
async def save_user(self, user_id: str, data: dict) -> User:
    user = await self.repository.update(user_id, data)
    await self.cache.set(f"user:{user_id}", user, ttl=300)
    return user
```

**Strengths:** Cache always fresh after writes, strong read-after-write consistency.
**Weaknesses:** Higher write latency (two writes), caches data that may never be read.
**Best for:** Systems requiring immediate consistency — leaderboards, dashboards, aggregated data.

### Write-Behind (Write-Back)

Write to cache first, asynchronously flush to data source.

**Strengths:** Very fast write performance, reduces DB load via write coalescing (10 updates
before flush = 1 DB write).
**Weaknesses:** Data loss risk if cache fails before flush. Requires durable cache or WAL.
**Best for:** High-write-throughput with eventual consistency — analytics, activity streams, sessions.

### Refresh-Ahead

Cache proactively refreshes entries before expiration using background threads.

**Strengths:** Users never experience cache miss for hot data, eliminates miss latency.
**Weaknesses:** Wastes resources refreshing cold entries. Only valuable for known hot data.
**Best for:** Homepage data, trending feeds, CDN-cached popular content.

### Write-Around

Writes go directly to data source, bypassing cache. Cache populated on subsequent reads.

**Strengths:** Prevents cache pollution with data that may never be read.
**Weaknesses:** First read after write always misses.
**Best for:** Log entries, audit records, bulk data ingestion.

---

## 2. Invalidation Patterns

### TTL-Based Invalidation

Every entry gets a Time-To-Live. The simplest and most universal approach.

**TTL guidelines by data type:**

| Data Type | TTL Range | Rationale |
|---|---|---|
| Static reference (countries, currencies, config) | 1–24 hours | Rarely changes, safe to cache long |
| Semi-static (user profiles, product details) | 5–60 minutes | Changes occasionally, staleness noticeable |
| Rapidly changing (feeds, leaderboards, comments) | 5–30 seconds | Freshness critical, short cache still helps |
| Session/token data | Match session/token expiry | Security alignment |
| "Not found" results (negative cache) | 30–60 seconds | Prevents penetration without long stale risk |

**Critical rule:** Always set a TTL. TTL is your safety net even when you have event-driven invalidation.
An entry without TTL can survive indefinitely serving stale data if invalidation events are lost.

### Event-Driven Invalidation

Invalidate or update cache in response to data change events. More responsive than TTL alone.

**Application-level invalidation:**
The same code path that writes to DB also invalidates cache. Simple but brittle — every write
path must remember to invalidate.

**Change Data Capture (CDC):**
Tools like Debezium monitor the database transaction log and publish change events.

```
Source DB → WAL/binlog → Debezium → Kafka → Consumer → Cache invalidation
```

CDC eliminates consistency bugs from forgotten invalidation in application code. Provides
near-real-time invalidation (milliseconds) with minimal impact on the source database.

**Pub/Sub invalidation:**
On write, publish invalidation message that all cache nodes subscribe to. Solves the multi-node
L1 cache consistency problem — when one instance invalidates a key, all instances hear about it.

Typical propagation within ~100ms. For larger systems, Kafka provides durability, ordering, and replay.

### Version-Based Invalidation

Include version in cache key. Old keys stop being referenced, eventually evicted.

```python
CACHE_VERSION = "v3"

def cache_key(self, user_id: str) -> str:
    return f"user:{user_id}:{CACHE_VERSION}"
```

Useful during schema migrations and rolling deployments. Old-version keys naturally expire while
new-version keys populate. O(1) invalidation — just increment version counter.

### Tag-Based Invalidation

Associate cache entries with tags. Invalidating a tag purges all associated entries.

Useful when a single data change affects many cached results (e.g., price change invalidates
all product listing caches). Varnish's `xkey` and Fastly's Surrogate-Key can purge globally
in ~150ms.

### Hybrid Invalidation — Production Recommendation

The most robust approach combines strategies:

1. **TTL as safety net** — ensures no entry survives indefinitely, even if events fail
2. **Event-driven for freshness** — responds to known data changes quickly
3. **Version-based for schema changes** — simplifies deployment invalidation

---

## 3. Stampede Prevention

When a popular key expires, concurrent requests simultaneously miss and overwhelm the data source.
A key accessed 10,000 times/second can generate thousands of DB queries at expiration.

### TTL Jitter — Always Apply

Add ±10-20% randomness to all TTLs:

```python
import random

def jittered_ttl(base_ttl: int, jitter_fraction: float = 0.1) -> int:
    """Add random jitter to TTL to prevent synchronized expiration."""
    jitter = base_ttl * jitter_fraction
    return int(base_ttl + random.uniform(-jitter, jitter))

# Usage: every cache.set() call
await cache.set(key, value, ttl=jittered_ttl(300))
```

For 10,000 RPS across 1,000 instances with 300s TTL, jitter transforms a 10,000-request spike
into ~166 QPS over 60 seconds — a **60x reduction** in peak origin load. There is no reason
not to add jitter to every TTL in your system.

### Probabilistic Early Expiration (XFetch)

Proposed by Vattani, Chierichetti, and Lowenstein (2015 VLDB). Proven optimal.

```python
import math
import random
import time

def should_refresh_early(
    cached_at: float, ttl: float, delta: float, beta: float = 1.5
) -> bool:
    """XFetch: probabilistically decide to refresh before TTL expires.

    Args:
        cached_at: timestamp when entry was cached
        ttl: total TTL in seconds
        delta: time cost of recomputation in seconds
        beta: tuning parameter (1.0-2.0, default 1.5)
    """
    expiry = cached_at + ttl
    remaining = expiry - time.time()
    threshold = delta * beta * -math.log(random.random())
    return remaining < threshold
```

Each request independently decides whether to refresh based on proximity to expiration. Exactly
one request refreshes before expiry — no coordination needed. β=1.5 with 10-20% TTL jitter
provides good balance.

### Request Coalescing (Singleflight)

Only one in-flight fetch per key. Other requests wait and share the result.

```python
import asyncio
from collections import defaultdict

class SingleFlight:
    """Ensure only one in-flight fetch per key."""

    def __init__(self) -> None:
        self._flights: dict[str, asyncio.Future] = {}
        self._lock = asyncio.Lock()

    async def do(self, key: str, fetch_fn):
        async with self._lock:
            if key in self._flights:
                return await self._flights[key]

            future = asyncio.get_event_loop().create_future()
            self._flights[key] = future

        try:
            result = await fetch_fn()
            future.set_result(result)
            return result
        except Exception as exc:
            future.set_exception(exc)
            raise
        finally:
            async with self._lock:
                self._flights.pop(key, None)
```

200 concurrent requests for the same expired key → 1 database call. The single most effective
defense against thundering herds.

### Stale-While-Revalidate

Serve stale value immediately, refresh asynchronously. Three states:
- **Fresh** (within TTL): serve directly
- **Stale** (past soft TTL, within hard TTL): serve immediately + background refresh
- **Rotten** (past hard TTL): fetch from origin

```python
async def get_with_swr(
    self, key: str, fetch_fn, soft_ttl: int = 300, hard_ttl: int = 600
) -> Any:
    entry = await self.cache.get_with_metadata(key)

    if entry is None:
        # Rotten or absent — must fetch
        value = await fetch_fn()
        await self.cache.set(key, value, ttl=hard_ttl, metadata={"cached_at": time.time()})
        return value

    age = time.time() - entry.metadata["cached_at"]
    if age < soft_ttl:
        return entry.value  # Fresh

    # Stale — serve and refresh in background
    asyncio.create_task(self._background_refresh(key, fetch_fn, hard_ttl))
    return entry.value
```

### Distributed Locking

For expensive recomputation, use a lock so only one process refreshes:

```python
async def get_with_lock(self, key: str, fetch_fn, ttl: int = 300) -> Any:
    value = await self.cache.get(key)
    if value is not None:
        return value

    lock_key = f"lock:{key}"
    acquired = await self.cache.set(lock_key, "1", nx=True, ex=10)

    if acquired:
        try:
            value = await fetch_fn()
            await self.cache.set(key, value, ttl=jittered_ttl(ttl))
            return value
        finally:
            await self.cache.delete(lock_key)
    else:
        # Wait briefly, then try cache again or fetch
        await asyncio.sleep(0.1)
        return await self.cache.get(key) or await fetch_fn()
```

### Recommended Layered Defense

Apply in order (each layer catches what the previous missed):

1. **TTL jitter** — always, everywhere, zero cost
2. **Probabilistic early expiration (XFetch)** — for hot keys with predictable access
3. **Singleflight per-process** — coalesces concurrent misses within one instance
4. **Distributed locking** — last resort for expensive cross-instance coordination

---

## 4. Eviction Policies

### LRU (Least Recently Used)

Evicts the entry not accessed for the longest time. O(1) via doubly-linked list + hash map.
Redis uses approximated LRU (samples N keys, default 5, evicts least recent). Good for temporal
locality but vulnerable to scan pollution — a single sequential scan can evict all hot data.

### LFU (Least Frequently Used)

Evicts the entry with the fewest accesses. Outperforms LRU for skewed/Zipfian distributions.
Redis LFU uses probabilistic Morris counter with time-based decay — few bits per key.
Weakness: historical inertia — previously popular items linger after becoming cold.

### W-TinyLFU — State of the Art

Used by Caffeine (Java's highest-performance cache). Combines:
- 1% admission window (LRU)
- TinyLFU frequency filter (4-bit CountMinSketch, 8 bytes per entry)
- 99% main cache (segmented LRU: 80% protected, 20% probationary)

In benchmarks: **39.6% hit rate vs 40.3% optimal** — all other policies scored ≤20%.
O(1) time complexity, scan resistance, minimal space overhead. Best general-purpose policy.

### ARC (Adaptive Replacement Cache)

IBM Research (2003). Self-tunes recency vs frequency using four lists. 10-20% better than LRU.
Patented by IBM (US Patent 6996676) — limited adoption (PostgreSQL removed its ARC in v8.0).

### Selection Guide

| Scenario | Recommended Policy |
|---|---|
| General-purpose distributed cache (Redis) | `allkeys-lru` |
| Skewed workload with stable hot set (Redis) | `allkeys-lfu` |
| Mixed persistent + cache keys (Redis) | `volatile-lru` or `volatile-lfu` |
| In-process JVM cache | W-TinyLFU (Caffeine) |
| In-process Python cache | `functools.lru_cache` or `cachetools.LRUCache` |
| Data loss unacceptable (Redis) | `noeviction` |

Always pair eviction policy with TTL. Eviction handles memory pressure; TTL handles freshness.

---

## 5. Cache Key Design

### Standard Format

```
{service}:{entity}:{identifier}:{qualifier}
```

**Examples:**
```
user-service:user:12345:profile
product-service:product:SKU-001:pricing
api:search:q=redis&page=2
cache:v2:products:category:5
lock:user:1001:checkout
```

### Key Design Rules

1. **Deterministic** — same inputs → same key. Sort query parameters, normalize casing,
   canonicalize inputs.

2. **Version indicator** — `user:12345:v3` when serialization format changes. Prevents
   deserialization errors during rolling deployments.

3. **Namespace prefixes** — prevent collisions between services sharing a cache. Enable
   bulk invalidation by prefix.

4. **Short but readable** — under 200 characters. Hash very long inputs (full SQL queries)
   into a digest.

5. **No sensitive data** — keys appear in logs, monitoring, and error messages.

6. **Include variant parameters** — locale, currency, user role — to prevent one user from
   receiving another's cached data.

### Centralized Key Generation

Never construct keys with inline string formatting. Use a centralized function:

```python
class CacheKeys:
    """Single source of truth for all cache key patterns."""

    VERSION = "v2"

    @staticmethod
    def user_profile(user_id: str) -> str:
        return f"user:{user_id}:{CacheKeys.VERSION}:profile"

    @staticmethod
    def product_pricing(product_id: str, currency: str) -> str:
        return f"product:{product_id}:{CacheKeys.VERSION}:pricing:{currency}"

    @staticmethod
    def search_results(query: str, page: int) -> str:
        normalized = query.lower().strip()
        query_hash = hashlib.md5(normalized.encode()).hexdigest()[:12]
        return f"search:{query_hash}:page:{page}"
```

---

## 6. Multi-Layer Architecture

### L1 (In-Process) + L2 (Distributed)

```
Request → L1 (local, ~100ns) → L2 (Redis, ~1ms) → Database (~10-50ms)
```

**L1 configuration (typical):**
- Max items: 100–10,000
- TTL: 1–60 seconds (must be shorter than L2)
- Memory limit: ~100MB
- Eviction: LRU or W-TinyLFU (Caffeine)

**L2 configuration (Redis, typical):**
- Connection pool: 20 connections
- Operation timeout: 100ms
- TTL: 5–60 minutes (longer than L1)

**Consistency between layers:**
- L1 TTL < L2 TTL — L1 entries expire first, falling through to L2
- Pub/sub invalidation — when a node writes to L2, publish invalidation so other nodes
  evict from their L1
- Write-through to both layers simultaneously

Salesforce's AIMS system: L1/L2 caching reduced metadata retrieval from **400ms P90 to sub-ms**,
improved e2e latency by **27%**, maintained **65% availability during complete backend outages**.

### CDN / Edge Layer

For HTTP responses, add CDN as outermost cache:

```
Browser → CDN Edge (~5ms) → L1 + L2 → Origin → Database
```

Use hashed asset URLs (`main.7a9c1f.js`) with long `max-age` + `immutable`.
Use `stale-while-revalidate` for HTML/API responses.
Prefer versioned URLs over explicit purging for static assets.

---

## 7. Failure Modes

### Cache Penetration

Requests for data that doesn't exist — bypasses cache, hits DB every time.
Attackers can exploit by flooding requests for invalid IDs.

**Fixes:**
- **Negative caching:** Cache "not found" with short TTL (30-60s)
- **Bloom filter:** 1 billion keys at 1% false positive = ~1.2 GB memory. O(1) rejection.
- **Input validation:** Reject obviously invalid IDs before cache lookup.

### Cache Avalanche

Mass simultaneous expiration (e.g., after bulk warm-up with identical TTLs).

**Fixes:**
- Jittered TTLs (always)
- Staggered cache warming (spread writes over time, not all at once)
- Multi-tier caching (miss on L1 doesn't necessarily reach DB)
- Circuit breakers to protect DB during mass-miss events

### Hot Key Problem

Single key receives disproportionate traffic, overwhelming the cache node for that key.

**Fixes:**
- **Local caching of hot keys** — replicate into each instance's L1 with very short TTL
- **Key replication** — `hot_key:1`, `hot_key:2`, ... across N shards, load-balance reads
- **Real-time detection** — monitor per-key access counts, trigger mitigation dynamically

### Cache Failure

The cache is an optimization, not a guarantee.

```python
async def get_user_safe(self, user_id: str) -> User:
    try:
        cached = await self.cache.get(f"user:{user_id}")
        if cached is not None:
            return cached
    except CacheError:
        logger.warning("cache_read_failed", user_id=user_id, exc_info=True)
        # Fall through to DB — never propagate cache errors to users

    return await self.repository.find_by_id(user_id)
```

**Circuit breaker pattern:**
- Closed (normal): route through cache
- Open (cache down): skip cache, go direct to DB with rate limiting
- Half-Open (testing recovery): send limited requests to cache

Typical: 5 failures in 60s trips circuit, 30s recovery timeout, 3 test requests in half-open.

---

## 8. HTTP Caching

### RFC 9111 — Key Directives

| Directive | Meaning |
|---|---|
| `max-age=N` | Fresh for N seconds |
| `s-maxage=N` | Override max-age for shared caches (CDN) |
| `no-cache` | Always validate before serving (NOT "don't cache") |
| `no-store` | Never cache at all |
| `private` | Only browser can cache (not CDN) |
| `public` | Any cache can store |
| `immutable` | Never revalidate on reload |
| `stale-while-revalidate=N` | Serve stale for N seconds while refreshing in background |
| `stale-if-error=N` | Serve stale for N seconds if origin is down |

### Recommended Patterns

**Immutable assets** (JS/CSS bundles with content hash in filename):
```
Cache-Control: public, max-age=31536000, immutable
```

**API responses with conditional caching:**
```
Cache-Control: private, no-cache
ETag: "abc123"
```

**Semi-static pages with stale fallback:**
```
Cache-Control: public, max-age=60, stale-while-revalidate=300, stale-if-error=86400
```

**Personalized/sensitive data:**
```
Cache-Control: private, no-store
```

### Conditional Requests

`ETag` + `If-None-Match` — server returns 304 Not Modified if content unchanged. More precise
than `Last-Modified`. Use for API responses where body is expensive to generate.

`Vary` header — specifies which request headers affect the cached response. Critical for content
negotiation: `Vary: Accept-Encoding, Accept-Language`.

---

## 9. Serialization

| Format | Speed | Size | Schema | Debuggability |
|---|---|---|---|---|
| Protocol Buffers | Fastest (2-6x JSON) | Smallest (32-68% less) | Required | Poor |
| MessagePack | Fast | Small | Not required | Moderate |
| JSON | Baseline | Baseline | Not required | Excellent |

**Recommendations:**
- High-throughput production systems → Protocol Buffers or MessagePack
- Development/debugging → JSON
- Compress large values (>1KB) with LZ4 (fast) or gzip (smaller)
- Cache the DTO, not the raw entity — 3 fields is cheaper to serialize than 50

**Version your serialization schema.** When you change a cached object's structure, old entries
fail to deserialize. Options:
- Bump the key version (`user:12345:v3` → `user:12345:v4`) — old keys expire naturally
- Handle deserialization failures gracefully — treat as cache miss, log warning

---

## 10. Observability

### Essential Metrics

| Metric | Healthy | Warning | Critical | Action |
|---|---|---|---|---|
| Hit ratio | >90% | <90% | <80% | Review TTLs, patterns, key design |
| Miss rate | Stable | Spike | Sustained spike | Check stampede, cold cache, penetration |
| Latency p50 | <1ms (local), <5ms (dist) | — | p99 >10ms | Network, big values, serialization |
| Eviction rate | Zero/stable | Increasing | Sustained | Cache undersized, review what's cached |
| Memory usage | <80% | >85% | >95% | Scale up, review caching scope |
| Connection count | — | >80% max | >95% max | Connection pool sizing |
| Error rate | Zero | Any | Sustained | Connection failures, timeouts |

### Operational Practices

- **Segment by key prefix** — identify which data categories underperform
- **Track hit ratio over time** — gradual decline signals changed access patterns
- **Alert on error rates** — connection failures, serialization errors, timeouts
- **Log cache misses with context** — key prefix, origin for debugging and tuning
- **Review TTL distributions** — keys expiring too frequently (wasted refreshes) or too
  infrequently (stale risk)
- **Monitor sawtooth patterns** — DB query rate spikes aligned with TTL cycles indicate
  need for jitter or stampede protection

---

## 11. Cache Warming

Prevents the cold-start problem where a freshly deployed cache forces all traffic to the database.

**Strategies:**
- **Rolling deployments** — avoid all nodes cold simultaneously
- **Warm from existing replicas** — Netflix EVCache dumps keys from existing nodes to S3,
  populates new instances (380 nodes, 2.2GB/15M items per instance warms in ~15 minutes)
- **Predictive warming** — pre-populate cache with known hot keys based on access patterns
- **Lazy warming with stampede protection** — start cold but with singleflight + jitter
  so the DB isn't overwhelmed

**Cache warming should never block deployments.** If warming fails, the system should function
(slowly) with cold cache plus stampede protection.

---

## 12. Code-Level Conventions

### Abstract the Cache Interface

Never scatter raw cache client calls throughout business logic:

```python
from abc import ABC, abstractmethod
from typing import Any

class CachePort(ABC):
    """Cache abstraction — implementations can be Redis, local, or no-op for testing."""

    @abstractmethod
    async def get(self, key: str) -> Any | None: ...

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: int = 300) -> None: ...

    @abstractmethod
    async def delete(self, key: str) -> None: ...

    @abstractmethod
    async def exists(self, key: str) -> bool: ...
```

Benefits:
- Swap implementations (local ↔ distributed ↔ no-op) without changing business logic
- No-op implementation for tests where caching is irrelevant
- In-memory implementation for unit tests that verify cache behavior

### Declarative Caching

Separate caching concerns from business logic using decorators:

```python
from functools import wraps

def cached(ttl: int = 300, prefix: str = ""):
    def decorator(fn):
        @wraps(fn)
        async def wrapper(self, *args, **kwargs):
            key = f"{prefix}:{fn.__name__}:{args}:{sorted(kwargs.items())}"
            result = await self.cache.get(key)
            if result is not None:
                return result
            result = await fn(self, *args, **kwargs)
            await self.cache.set(key, result, ttl=jittered_ttl(ttl))
            return result
        return wrapper
    return decorator
```

### Testing with Cache

- **Unit tests** — bypass or mock cache (test business logic independently)
- **Integration tests** — validate cache behavior (correct keys, TTLs, invalidation)
- **Chaos tests** — simulate cache failure (verify graceful degradation)
- **No-op cache** — for test environments where caching is irrelevant

---

## 13. Real-World Patterns

### Meta — TAO

Graph-aware distributed cache: **1 billion+ reads/second**, **96.4% hit rate**. Two-tier
architecture: leader tier for writes, follower tiers for reads. Consistency improved from 6
nines to **10 nines (99.99999999%)**. Serves **>1 quadrillion queries/day**.

Innovations: leases (tokens preventing thundering herds), gutter pools (dedicated failover
machines at ~1% cluster capacity), UDP for reads/TCP for writes.

### Netflix — EVCache

**400 million+ cache ops/second**. Built on memcached with Ketama consistent hashing.
Replicates across AZ (2-9 copies per cluster). SSD-backed warm data. Cross-region via
Kafka with batch compression (NLB bandwidth from ~45 GB/s to <100 MB/s).

Hollow: compressed in-memory object store eliminating cache-invalidation headaches.

### Twitter — Hybrid Fan-Out

Fan-out-on-write for typical users (tweet IDs pushed to each follower's Redis timeline).
Fan-in-on-read for celebrities (>10K followers — avoids 30M write ops per tweet).
Each timeline stored **3 times** across Redis clusters. ~300 tweets cached per timeline.

### LinkedIn — Couchbase

**10+ million queries/second** across 300+ clusters. **99%+ hit rate**, **<4ms avg latency**
for 2.5+ billion items. CDC via Brooklin with System Change Numbers for reconciliation.

### Amazon DAX

Write-through caching for DynamoDB. Up to **10x performance improvement**. Reduces response
times from milliseconds to microseconds while maintaining consistency.

### Key Takeaways from Scale

1. Cache-aside with delete-on-write is the dominant pattern
2. Multi-layer (L1 local + L2 distributed) provides best latency-consistency balance
3. Stampede prevention is non-negotiable at scale
4. CDC-based invalidation for critical data, TTL for everything else
5. Every cache entry must have a TTL, every cache must have a size limit
6. 90%+ hit ratios are achievable and expected in well-tuned systems
7. Cache failure handling (circuit breakers, fallbacks) prevents cascading outages
