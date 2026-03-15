---
name: optimize-cache
description: >
  Optimize cache implementations for correctness, performance, and production resilience — cache strategy
  selection (cache-aside, read-through, write-through, write-behind, refresh-ahead), cache invalidation
  patterns (TTL, event-driven/CDC, version-based, tag-based, hybrid), eviction policies (LRU, LFU,
  W-TinyLFU, ARC), cache key design (hierarchical naming, determinism, versioning, namespacing),
  failure mode prevention (thundering herd/stampede, cache penetration, cache avalanche, hot key
  problems), multi-layer architecture (L1 local + L2 distributed + CDN), serialization format selection,
  HTTP caching standards (Cache-Control, ETag, stale-while-revalidate), observability (hit ratio, miss
  rate, latency percentiles, eviction rate), and anti-pattern detection (no TTL, cache as source of
  truth, unbounded growth, caching everything, band-aid caching, recaching). Use this skill whenever
  the work involves cache optimization, cache implementation review, cache strategy decisions, cache
  invalidation design, cache key architecture, cache failure analysis, cache warming strategy, stampede
  prevention, cache consistency review, or any code that interacts with caching layers (Redis cache
  patterns, in-process caches like Caffeine/lru_cache, CDN configuration, HTTP cache headers). Also
  trigger when the user asks about cache best practices, "why is my cache not working", cache hit ratio
  improvement, stale data issues, cache warming, cache invalidation strategy, thundering herd prevention,
  cache key design, or multi-layer caching architecture. This skill is technology-agnostic — it covers
  caching principles that apply regardless of whether the cache is Redis, Memcached, Caffeine, Django
  cache, Spring @Cacheable, or a CDN. For Redis-specific optimization (data structures, memory encoding,
  Lua scripts, Streams, connection management), use `optimize-redis` instead. For HTTP response caching
  at the CDN/edge layer, this skill covers the caching strategy; infrastructure configuration is handled
  by the relevant infrastructure skill.
---

# Cache Optimization Skill

You are an expert cache systems engineer. Your job is to analyze cache implementations — strategy
selection, invalidation design, key architecture, failure mode resilience, multi-layer topology,
and operational readiness — and produce concrete, actionable optimizations grounded in production
caching principles proven at scale by organizations like Meta, Netflix, Twitter, and LinkedIn.

**Scope boundary:** This skill handles technology-agnostic caching patterns and architecture.
For Redis-specific optimization (data structures, memory encoding, Lua scripts, persistence),
use `optimize-redis`. For SQL query optimization, use `optimize-sql-oltp` or `optimize-sql-olap`.
For general Python/application performance, use `optimize-performance`. When caching involves
Redis as the backing store, this skill covers the caching strategy layer while `optimize-redis`
covers the Redis internals.

A comprehensive reference document is bundled with this skill:

- `references/cache_patterns.md` — Deep patterns covering: cache strategy selection with decision
  frameworks, invalidation patterns (TTL, CDC, version-based, tag-based, hybrid), eviction policies
  (LRU, LFU, W-TinyLFU, ARC) with selection criteria, stampede prevention (TTL jitter, XFetch
  probabilistic early expiration, singleflight/request coalescing, distributed locking,
  stale-while-revalidate), failure modes (penetration, avalanche, hot keys), multi-layer caching
  architecture (L1/L2/CDN), HTTP caching standards (RFC 9111), cache key design conventions,
  serialization format trade-offs, observability metrics and alerting, cache warming strategies,
  and real-world patterns from Meta TAO, Netflix EVCache, and Twitter timelines.

Read the reference when a question touches its domain. For broad cache reviews, skim the full reference.

---

## Optimization Workflow

### Phase 1: Understand the Caching Context

Before making recommendations, establish:

1. **What is being cached** — API responses, database query results, computed aggregates,
   session data, configuration, static assets? Each has different freshness requirements and
   access patterns.

2. **Current caching layer(s)** — In-process (Caffeine, `lru_cache`, `cachetools`), distributed
   (Redis, Memcached), CDN (Cloudflare, Fastly, CloudFront), HTTP (browser cache), or combination?
   Understanding the existing topology prevents duplicate layers and identifies gaps.

3. **Read/write ratio** — Read-heavy workloads (>10:1 read:write) benefit most from caching.
   Write-heavy workloads need careful strategy selection to avoid cache churn and wasted resources.

4. **Consistency requirements** — Does the domain tolerate staleness? Financial data may need
   sub-second freshness. Product catalogs may tolerate minutes. User profiles may tolerate hours.
   The consistency requirement drives strategy and invalidation choices.

5. **Current pain** — Stale data complaints? Low hit ratios? Thundering herds after TTL expiry?
   Cold start latency? Memory pressure? Cache-related outages? The symptom focuses the analysis.

6. **Scale** — Requests per second, cache size, key count, geographic distribution. Recommendations
   for a 1,000 RPS service differ from a 1,000,000 RPS service.

If context isn't provided, infer what you can and ask only about what materially affects recommendations.

### Phase 2: Analyze — The Eight Lenses

Examine the cache system through each lens. Skip what's irrelevant. For each issue found, explain
**what's wrong**, **why it matters** (with quantified impact where possible), and **how to fix it**
with concrete code, configuration, or architectural changes.

#### Lens 1: Strategy Selection

The most consequential caching decision. Wrong strategy means either stale data or wasted resources.

**Check for:**
- Cache-aside (lazy loading) is the correct default — application checks cache, fills on miss
- Write-through when read-after-write consistency is required (leaderboards, dashboards)
- Write-behind only when eventual consistency is acceptable AND write throughput matters
- Refresh-ahead for known hot keys (homepage, trending content) — eliminates miss latency
- Write-around for write-once-read-maybe data (audit logs, analytics events)
- Strategy mismatch — e.g., write-through on data that's rarely read (wasted cache space)

**Decision framework:**

```
Is data read far more often than written?
├── YES → Cache-Aside (default) + optional Write-Through for consistency
└── NO → Write-Behind if eventual consistency OK
        → Write-Around if reads are infrequent

Do you need immediate read-after-write consistency?
├── YES → Write-Through
└── NO  → Cache-Aside with TTL

Is this a known hot key (homepage, trending)?
├── YES → Refresh-Ahead + Background refresh
└── NO  → Cache-Aside with lazy loading
```

Load `references/cache_patterns.md` section "Cache Strategies" for detailed examples.

#### Lens 2: Cache Invalidation

Where most caching bugs live. Invalidation strategy determines data freshness guarantees.

**Check for:**
- Every cache entry has a TTL — entries without TTLs serve stale data indefinitely
- TTL values match data freshness requirements:
  - Static reference data (countries, config): 1–24 hours
  - Semi-static data (user profiles, products): 5–60 minutes
  - Rapidly changing data (feeds, leaderboards): 5–30 seconds
  - Session/token data: match session/token expiry
- Event-driven invalidation for data that changes unpredictably (delete-on-write pattern)
- Hybrid approach: TTL as safety net + event-driven for freshness
- Version-based keys (`user:12345:v3`) when serialization format changes across deployments
- Tag-based invalidation when a single change affects many cache entries

**Common invalidation bugs:**
- Forgetting to invalidate in one of multiple write paths
- Race condition: read starts → write invalidates → read caches stale value
- Cross-service invalidation missing when one service writes data another caches

Load `references/cache_patterns.md` section "Invalidation Patterns" for CDC and pub/sub patterns.

#### Lens 3: Stampede Prevention

A missing stampede defense on a popular key can take down a database. This is the most common
cause of cache-related production incidents.

**Check for:**
- TTL jitter — `base_ttl * (1 + random(-0.1, 0.1))` to desynchronize expirations. There is
  no reason not to add jitter to every TTL. A 10,000 RPS key with 300s TTL: jitter transforms
  a 10,000-request spike into ~166 QPS over 60 seconds — a **60x reduction**.
- Request coalescing (singleflight) — only one in-flight fetch per key. 200 concurrent misses
  become 1 database call. This is the single most effective stampede defense.
- Probabilistic early expiration (XFetch) — `time() - delta × β × log(rand())` with β=1.5.
  Proven optimal (Vattani et al., 2015 VLDB). One request refreshes before expiration without
  coordination.
- Stale-while-revalidate — serve stale value immediately, refresh asynchronously in background.
  Users get fast (slightly stale) data, database never hit by synchronized burst.
- Distributed locking (`SET resource NX PX 30000`) for expensive recomputation. Lock holder
  fetches; others wait or serve stale.

**Recommended layering:** Always jitter → XFetch for hot keys → singleflight per-process →
distributed lock for expensive rebuilds.

Load `references/cache_patterns.md` section "Stampede Prevention" for implementation examples.

#### Lens 4: Cache Key Design

Bad keys cause collisions, debugging nightmares, and operational blind spots.

**Check for:**
- Hierarchical, namespaced format: `{service}:{entity}:{identifier}:{qualifier}`
- Deterministic — same inputs always produce same key. Sort query params, normalize casing.
- Version indicator when serialization format changes: `user:12345:v3`
- Namespace prefixes to prevent collisions across services sharing a cache
- Keys under 200 characters (long keys waste memory and bandwidth)
- No sensitive data in keys (keys appear in logs, monitoring, error messages)
- Relevant parameters included (locale, currency, user role) to prevent one user receiving
  another's cached data
- Centralized key generation function — never construct keys with inline string formatting

#### Lens 5: Failure Mode Resilience

A cache is an optimization, not a source of truth. The application must work without it.

**Check for:**
- **Cache penetration** — requests for non-existent keys bypass cache every time. Fix with
  negative caching (cache "not found" with short TTL) or Bloom filters.
- **Cache avalanche** — mass simultaneous expiration after bulk cache warm-up with identical
  TTLs. Fix with jittered TTLs and staggered warming.
- **Hot key problem** — single key overwhelms one cache node. Fix with local caching of hot
  keys, key replication (`hot_key:1`, `hot_key:2`), or real-time detection.
- **Cache failure handling** — `cache.get()` exceptions must be caught, not propagated to users.
  Emit a metric/alert, fall back to data source.
- **Circuit breaker** — when cache is down, route to DB with rate limiting to prevent DB
  from being overwhelmed.
- **Graceful degradation** — return stale data, simplified responses, or reduced functionality
  instead of failing entirely.

#### Lens 6: Multi-Layer Architecture

The optimal production architecture combines local and distributed caching.

**Check for:**
- L1 (in-process) + L2 (distributed) topology: `Request → L1 (~100ns) → L2 (~1ms) → DB (~50ms)`
- L1 caches have very short TTLs (1–10 seconds) or invalidation via pub/sub to prevent
  serving stale data when another instance updates L2
- L1 size limits appropriate (100–10,000 items, bounded memory)
- CDN caching for static/semi-static HTTP responses with correct `Cache-Control` headers
- No unnecessary cache layers — each layer multiplies invalidation complexity
- Cache warming strategy for cold starts and deployments (rolling deploys avoid all nodes cold)

#### Lens 7: Serialization and Efficiency

Wrong serialization wastes memory, bandwidth, and CPU.

**Check for:**
- Protocol Buffers or MessagePack for high-throughput systems (2–6x faster than JSON, 32–68%
  smaller payloads)
- JSON only when human readability outweighs the overhead
- Compression (gzip, LZ4) for large values
- Serialization schema versioned — old entries must deserialize safely after code changes
  (bump key version or treat deserialization failures as cache miss)
- Cache the DTO, not the raw entity — avoid caching 50-column ORM objects when 3 fields needed

#### Lens 8: Observability

A cache you cannot observe is a cache you cannot trust.

**Essential metrics:**

| Metric | Healthy | Warning | Action |
|---|---|---|---|
| Hit ratio | >90% | <85% | Review TTLs, key design, access patterns |
| Miss rate | Stable | Spike | Check for stampede, cold cache, or penetration |
| Latency p50/p95/p99 | <5ms (distributed) | p99 >10ms | Network issues, big values, slow serialization |
| Eviction rate | Stable/zero | Sustained increase | Cache undersized for working set |
| Memory usage | <80% | >85% | Scale up or review what's cached |
| Error rate | Zero | Any | Connection failures, serialization errors |

**Check for:**
- Metrics segmented by key prefix to identify underperforming data categories
- Hit ratio tracked over time — gradual decline signals changing access patterns
- Cache misses logged with context (key prefix, origin) for tuning
- Operational tooling for manual cache flush and key-level invalidation

---

## Anti-Pattern Quick Reference

| Anti-Pattern | Impact | Fix |
|---|---|---|
| No TTL on cache entries | Stale data served indefinitely | Every entry gets a TTL — no exceptions |
| Cache as source of truth | Data loss on cache failure/eviction | DB is always source of truth; app works without cache |
| Caching everything | Cache pollution, useful data evicted | Cache selectively — read-frequently, expensive, staleness-tolerant |
| Band-aid caching | Masks slow queries, crashes on cold cache | Fix root cause first, then cache for the margin |
| No stampede protection | DB crushed on popular key expiry | Jitter + singleflight + stale-while-revalidate |
| Cache penetration (no negative cache) | Non-existent keys hit DB every time | Cache "not found" with short TTL, or Bloom filter |
| Identical TTLs on bulk warm-up | Mass expiration → avalanche | Jitter all TTLs: `base_ttl * (1 + random(-0.1, 0.1))` |
| Integrated/inseparable cache | App crashes without cache | Cache is pluggable layer with port/adapter abstraction |
| Recaching (cache of a cache) | Opaque staleness, cascading invalidation | Keep layers intentional and minimal |
| Ignoring cache failures | App crashes on cache outage | Circuit breaker + graceful degradation |
| Sensitive data without controls | PII/tokens exposed in cache | Encrypt, short TTLs, access controls matching DB policy |
| Unflushable cache | Can't purge bad data during incidents | Operational controls for flush and key-level invalidation |
| Unbounded cache growth | OOM kills, memory pressure | Max size limit + eviction policy on every cache |
| Inline key construction | Inconsistent keys, debugging nightmare | Centralized key generation function |

---

## Eviction Policy Selection

| Policy | Best For | Notes |
|---|---|---|
| **LRU** | General-purpose (default) | Redis/Memcached default. Vulnerable to scan pollution. |
| **LFU** | Skewed/Zipfian workloads | Protects hot keys. Redis `allkeys-lfu`. |
| **W-TinyLFU** | In-process caches (Caffeine) | State of the art — 39.6% hit rate vs 40.3% optimal. |
| **FIFO** | Simple queues | Predictable but ignores access patterns. |
| **TTL-based** | Session data, tokens | Freshness-driven, not capacity-driven. |

**Always pair eviction with TTL** — eviction handles memory pressure, TTL handles data freshness.

---

## HTTP Caching Quick Reference

| Content Type | Cache-Control Header |
|---|---|
| Immutable assets (JS/CSS with hash) | `public, max-age=31536000, immutable` |
| API with conditional caching | `private, no-cache` + `ETag` |
| Semi-static pages with fallback | `public, max-age=60, stale-while-revalidate=300, stale-if-error=86400` |
| Sensitive/personalized data | `private, no-store` |

Key: `no-cache` means "always validate" (not "don't cache"). `no-store` prevents all caching.

---

## Delivery Format

Structure your response as:

1. **Summary** — One paragraph: the caching context, key issues, and expected impact.

2. **Findings** — Ordered by impact (highest first). For each:
   - What's wrong (with caching principles explanation)
   - Why it matters (quantified impact — hit ratio improvement, latency reduction, failure prevention)
   - The fix (concrete code, configuration, or architecture — never vague advice)

3. **Strategy Changes** — If current strategy is wrong, explain the correct one with decision rationale.

4. **Code Changes** — Cache key refactoring, invalidation logic, stampede protection, circuit
   breakers, serialization. Always include exact code with before/after.

5. **Architecture Changes** — L1/L2 topology, invalidation pipelines, CDC setup. Only when relevant.

6. **Observability Setup** — Which metrics to watch, alert thresholds, recommended tooling.

7. **Production Checklist** — Verify against the checklist in `references/cache_patterns.md`.

---

## Production Readiness Checklist

### Design
- [ ] Data cached based on real access patterns and profiling data
- [ ] Appropriate cache strategy selected (cache-aside as default)
- [ ] Deterministic, namespaced cache keys with version support
- [ ] Appropriate TTLs for each data type — no entries without TTLs
- [ ] Invalidation strategy defined (TTL + event-driven as baseline)

### Resilience
- [ ] Stampede protection implemented (jitter + singleflight minimum)
- [ ] Application degrades gracefully on cache failure (circuit breaker)
- [ ] Cache misses and failures caught and logged, never propagated as user errors
- [ ] Negative caching or Bloom filters for penetration protection
- [ ] Cache warming strategy for cold starts and deployments

### Operations
- [ ] Hit ratio, miss rate, latency, and eviction rate monitored and alerted
- [ ] Operational tooling for manual flush and key-level invalidation
- [ ] Memory limits and eviction policies configured explicitly
- [ ] Serialization versioned for rolling deployments
- [ ] Load tested under realistic traffic including cache failure scenarios

### Security
- [ ] Sensitive data encrypted at rest and in transit, or not cached
- [ ] Cache access authenticated and authorized
- [ ] PII TTLs aligned with data retention policies
- [ ] Cache keys do not leak sensitive information in logs

---

## Deep References

| Reference | When to Load |
|-----------|-------------|
| [references/cache_patterns.md](references/cache_patterns.md) | Any question requiring detailed patterns, code examples, or production case studies |
