# Resilience Patterns Reference

> Patterns for building systems that withstand failure, degrade gracefully, and recover automatically.

---

## Resilience Principles

### The Reality of Distributed Systems

1. **Networks are unreliable**: Packets get lost, connections drop
2. **Latency is variable**: What was 10ms might become 10s
3. **Services fail**: Dependencies will be unavailable
4. **Failures cascade**: One failure triggers others

### Design Philosophy

```
┌─────────────────────────────────────────────────────────────┐
│                   RESILIENCE MINDSET                        │
│                                                             │
│   "Everything fails, all the time."                         │
│                        — Werner Vogels                      │
│                                                             │
│   Design for failure, not success.                          │
│   Expect the unexpected.                                    │
│   Make failure visible, not hidden.                         │
│   Prefer degradation over complete failure.                 │
└─────────────────────────────────────────────────────────────┘
```

---

## 1. Circuit Breaker

### Purpose

Prevent cascading failures by failing fast when a dependency is unhealthy.

### State Machine

```
                         ┌─────────────────────────────────────┐
                         │          CIRCUIT BREAKER            │
                         │                                     │
  ┌───────────────────────────────────────────────────────────────────────┐
  │                                                                       │
  │    ┌──────────┐     failures > threshold     ┌──────────┐            │
  │    │          │ ──────────────────────────▶  │          │            │
  │    │  CLOSED  │                              │   OPEN   │            │
  │    │          │ ◀──────────────────────────  │          │            │
  │    └────┬─────┘     probe succeeds           └────┬─────┘            │
  │         │                  ▲                      │                   │
  │    (requests             │                   (fail fast)            │
  │     allowed)              │                      │                   │
  │         │                 │                      │                   │
  │         │            success                 timeout                 │
  │         │                 │                      │                   │
  │         │           ┌─────┴─────┐                │                   │
  │         └──────────▶│ HALF-OPEN │◀───────────────┘                   │
  │                     │           │                                     │
  │                     │(1 probe   │                                     │
  │                     │ allowed)  │                                     │
  │                     └───────────┘                                     │
  │                           │                                           │
  │                      probe fails                                      │
  │                           │                                           │
  │                           ▼                                           │
  │                     back to OPEN                                      │
  │                                                                       │
  └───────────────────────────────────────────────────────────────────────┘
```

### Configuration

| Parameter | Description | Typical Value |
|-----------|-------------|---------------|
| `failure_threshold` | Failures before opening | 5 |
| `success_threshold` | Successes to close | 3 |
| `timeout` | Time before half-open | 30 seconds |
| `failure_rate` | % failures to trigger | 50% |
| `slow_call_threshold` | Latency considered slow | 2 seconds |

### Implementation Pattern

```python
from circuitbreaker import circuit

@circuit(
    failure_threshold=5,
    recovery_timeout=30,
    expected_exception=ServiceUnavailableError
)
async def call_payment_service(payment: Payment) -> PaymentResult:
    async with httpx.AsyncClient(timeout=5.0) as client:
        response = await client.post(
            f"{PAYMENT_SERVICE_URL}/process",
            json=payment.model_dump()
        )
        response.raise_for_status()
        return PaymentResult.model_validate(response.json())
```

---

## 2. Retry with Backoff

### Purpose

Automatically retry transient failures with increasing delays.

### Backoff Strategies

```
┌─────────────────────────────────────────────────────────────┐
│                    RETRY STRATEGIES                         │
│                                                             │
│  Constant:     ─────┼─────┼─────┼─────┼                    │
│                     1s    1s    1s    1s                   │
│                                                             │
│  Linear:       ─┼───┼─────┼───────┼                        │
│                 1s  2s    3s      4s                       │
│                                                             │
│  Exponential:  ┼─┼───┼───────┼───────────────┼             │
│                1s 2s  4s       8s            16s           │
│                                                             │
│  Exp + Jitter: ┼──┼────┼─────────┼─────────────────┼       │
│                1.1 2.3  4.7       9.2              17.8    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Formula

```python
# Exponential backoff with full jitter
delay = min(
    base_delay * (2 ** attempt) * random.uniform(0.5, 1.5),
    max_delay
)
```

### Retry Decision Tree

```
Is the error retryable?
    │
    ├─► 4xx (client error) ──► NO, don't retry
    │
    ├─► 5xx (server error) ──► YES, retry with backoff
    │
    ├─► Timeout ──► YES, retry with backoff
    │
    ├─► Connection error ──► YES, retry with backoff
    │
    └─► Unknown ──► NO, fail and investigate
```

### Implementation

```python
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential_jitter,
    retry_if_exception_type
)

@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential_jitter(initial=1, max=60, jitter=5),
    retry=retry_if_exception_type((ConnectionError, TimeoutError))
)
async def fetch_with_retry(url: str) -> dict:
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.json()
```

---

## 3. Bulkhead

### Purpose

Isolate failures to prevent resource exhaustion from affecting entire system.

### Types

**Thread Pool Bulkhead:**
```
┌─────────────────────────────────────────────────────────────┐
│                    THREAD POOL BULKHEAD                     │
│                                                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐ │
│  │  Critical APIs  │  │  Normal APIs    │  │ Batch Jobs  │ │
│  │   Pool: 50      │  │   Pool: 100     │  │  Pool: 20   │ │
│  │   Queue: 25     │  │   Queue: 50     │  │  Queue: 10  │ │
│  └─────────────────┘  └─────────────────┘  └─────────────┘ │
│                                                             │
│  Failure in "Normal" doesn't exhaust "Critical" threads    │
└─────────────────────────────────────────────────────────────┘
```

**Semaphore Bulkhead:**
```
┌─────────────────────────────────────────────────────────────┐
│                   SEMAPHORE BULKHEAD                        │
│                                                             │
│  ┌───────────────────────┐   ┌───────────────────────┐     │
│  │ Payment Service       │   │ Notification Service  │     │
│  │ Max concurrent: 10    │   │ Max concurrent: 50    │     │
│  │ Wait timeout: 500ms   │   │ Wait timeout: 100ms   │     │
│  └───────────────────────┘   └───────────────────────┘     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Implementation

```python
from asyncio import Semaphore, wait_for, TimeoutError

class BulkheadedClient:
    def __init__(self, max_concurrent: int = 10, timeout: float = 5.0):
        self._semaphore = Semaphore(max_concurrent)
        self._timeout = timeout

    async def call(self, operation: Callable) -> Any:
        try:
            async with wait_for(self._semaphore.acquire(), timeout=1.0):
                return await wait_for(operation(), timeout=self._timeout)
        except TimeoutError:
            raise BulkheadRejectedException("Bulkhead at capacity")
```

---

## 4. Timeout

### Purpose

Prevent resources from being held indefinitely by slow operations.

### Timeout Layers

```
┌─────────────────────────────────────────────────────────────┐
│                      TIMEOUT LAYERS                         │
│                                                             │
│  Client ──► Gateway ──► Service A ──► Service B ──► DB     │
│                                                             │
│  Overall:   10s                                             │
│  Gateway:         8s                                        │
│  Service A:            6s                                   │
│  Service B:                 4s                              │
│  DB:                              2s                        │
│                                                             │
│  Each layer must timeout BEFORE its caller                  │
└─────────────────────────────────────────────────────────────┘
```

### Timeout Budget Pattern

```
Total Budget: 10 seconds
    │
    ├── Service A call: 4s max
    │       └── Database query: 2s max
    │       └── Cache lookup: 500ms max
    │
    ├── Service B call: 3s max
    │       └── External API: 2s max
    │
    └── Reserve for processing: 3s
```

### Implementation

```python
async def process_order(order: Order) -> OrderResult:
    # Start timeout budget
    deadline = asyncio.get_event_loop().time() + 10.0

    # Service A with remaining budget
    remaining = deadline - asyncio.get_event_loop().time()
    inventory = await asyncio.wait_for(
        check_inventory(order),
        timeout=min(4.0, remaining)
    )

    # Service B with remaining budget
    remaining = deadline - asyncio.get_event_loop().time()
    payment = await asyncio.wait_for(
        process_payment(order),
        timeout=min(3.0, remaining)
    )

    return OrderResult(inventory=inventory, payment=payment)
```

---

## 5. Fallback

### Purpose

Provide alternative behavior when primary operation fails.

### Fallback Strategies

| Strategy | Description | Example |
|----------|-------------|---------|
| **Cached** | Return stale cached data | Product catalog |
| **Default** | Return sensible default | Feature flags |
| **Degraded** | Reduced functionality | Basic search vs. ML-ranked |
| **Fail-silent** | Swallow error, continue | Analytics, telemetry |
| **Fail-fast** | Immediate error to user | Payment processing |

### Decision Tree

```
Primary operation failed
    │
    ├─► Is cached data available?
    │       │
    │       ├─► YES, staleness < threshold ──► Return cached
    │       │
    │       └─► NO or too stale
    │               │
    │               ├─► Is default acceptable?
    │               │       │
    │               │       ├─► YES ──► Return default
    │               │       │
    │               │       └─► NO ──► Fail to user
    │               │
    │               └─► Is degraded mode possible?
    │                       │
    │                       ├─► YES ──► Return degraded
    │                       │
    │                       └─► NO ──► Fail to user
```

### Implementation

```python
async def get_product_recommendations(user_id: str) -> list[Product]:
    try:
        # Primary: ML-powered recommendations
        return await recommendation_service.get_personalized(user_id)
    except ServiceUnavailableError:
        try:
            # Fallback 1: Cached recommendations
            cached = await cache.get(f"recs:{user_id}")
            if cached:
                return cached
        except CacheError:
            pass

        # Fallback 2: Popular products (always available)
        return await product_service.get_popular(limit=10)
```

---

## 6. Health Checks

### Types

| Type | Purpose | Frequency |
|------|---------|-----------|
| **Liveness** | Is process alive? | Every 10s |
| **Readiness** | Can accept traffic? | Every 5s |
| **Startup** | Has initialization completed? | Until healthy |
| **Deep** | Are dependencies healthy? | Every 30s |

### Health Check Design

```
┌─────────────────────────────────────────────────────────────┐
│                    HEALTH CHECK ENDPOINTS                   │
│                                                             │
│  /health/live                                               │
│      └── Process is running (no dependency checks)         │
│                                                             │
│  /health/ready                                              │
│      └── Can serve traffic (checks critical deps)          │
│      └── Database connection pool OK                        │
│      └── Cache connection OK                                │
│                                                             │
│  /health/startup                                            │
│      └── Initialization complete                            │
│      └── Config loaded                                      │
│      └── Migrations applied                                 │
│                                                             │
│  /health/deep                                               │
│      └── All dependencies checked (for monitoring)         │
│      └── Database query works                               │
│      └── External services reachable                        │
└─────────────────────────────────────────────────────────────┘
```

### Implementation

```python
@router.get("/health/live")
async def liveness():
    return {"status": "ok"}

@router.get("/health/ready")
async def readiness(
    db: AsyncSession = Depends(get_db),
    cache: Redis = Depends(get_cache)
):
    checks = {}

    # Database check
    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {e}"

    # Cache check
    try:
        await cache.ping()
        checks["cache"] = "ok"
    except Exception as e:
        checks["cache"] = f"error: {e}"

    all_ok = all(v == "ok" for v in checks.values())
    status_code = 200 if all_ok else 503

    return JSONResponse(
        content={"status": "ready" if all_ok else "not_ready", "checks": checks},
        status_code=status_code
    )
```

---

## 7. Rate Limiting

### Purpose

Protect services from overload by limiting request rates.

### Algorithms

| Algorithm | Description | Use Case |
|-----------|-------------|----------|
| **Token Bucket** | Burst-friendly, refills over time | API rate limiting |
| **Leaky Bucket** | Smooth output rate | Streaming |
| **Fixed Window** | Simple, reset at intervals | Basic limiting |
| **Sliding Window** | No burst at window edges | Precise limiting |

### Token Bucket

```
┌─────────────────────────────────────────────────────────────┐
│                     TOKEN BUCKET                            │
│                                                             │
│         ┌─────────────────────┐                            │
│         │  Bucket (capacity)  │  ◀── Tokens added at rate  │
│         │  ┌─────────────────┐│                            │
│         │  │ ● ● ● ● ● ● ●  ││                            │
│         │  │ ● ● ● ○ ○ ○ ○  ││  (7 tokens available)      │
│         │  └─────────────────┘│                            │
│         └──────────┬──────────┘                            │
│                    │                                        │
│                    ▼                                        │
│             Request consumes 1 token                        │
│             No token = reject (429)                         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Rate Limit Headers

```http
HTTP/1.1 200 OK
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 42
X-RateLimit-Reset: 1704067200
Retry-After: 60
```

---

## 8. Graceful Degradation

### Degradation Levels

```
┌─────────────────────────────────────────────────────────────┐
│                  DEGRADATION LEVELS                         │
│                                                             │
│  Level 0: NORMAL                                            │
│      └── All features available                             │
│                                                             │
│  Level 1: DEGRADED                                          │
│      └── Non-critical features disabled                     │
│      └── ML recommendations → Popular items                 │
│      └── Real-time analytics → Batch                        │
│                                                             │
│  Level 2: MINIMAL                                           │
│      └── Only critical path available                       │
│      └── Browse → Buy → Confirm only                        │
│      └── No search, recommendations, reviews                │
│                                                             │
│  Level 3: MAINTENANCE                                       │
│      └── Read-only or static page                           │
│      └── "We're experiencing issues" message                │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Feature Flags for Degradation

```python
class DegradationManager:
    async def should_use_ml_recommendations(self) -> bool:
        if self.degradation_level >= 1:
            return False
        if not await self.health.is_ml_service_healthy():
            return False
        return True

    async def get_recommendations(self, user_id: str) -> list[Product]:
        if await self.should_use_ml_recommendations():
            return await self.ml_service.recommend(user_id)
        else:
            return await self.product_service.get_popular()
```

---

## Resilience Checklist

Before finalizing resilience design:

- [ ] All external calls have timeouts configured
- [ ] Circuit breakers protect unstable dependencies
- [ ] Retry policies use exponential backoff with jitter
- [ ] Bulkheads isolate critical from non-critical paths
- [ ] Fallback strategies defined for each dependency
- [ ] Health checks implement liveness, readiness, startup
- [ ] Rate limiting protects against overload
- [ ] Graceful degradation levels defined
- [ ] Dead letter queues capture failed messages
- [ ] Chaos testing planned for validation
