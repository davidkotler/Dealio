# Quality Attributes Reference

> Framework for analyzing, prioritizing, and designing for non-functional requirements (NFRs).

---

## Quality Attribute Framework

### The "-ilities" Taxonomy

| Category | Attributes | Architectural Impact |
|----------|------------|---------------------|
| **Runtime** | Performance, Scalability, Availability | Infrastructure, data architecture |
| **Evolution** | Modifiability, Extensibility, Portability | Module boundaries, abstractions |
| **Security** | Confidentiality, Integrity, Authenticity | Encryption, access control, audit |
| **Operations** | Observability, Deployability, Testability | Instrumentation, CI/CD, isolation |
| **Business** | Cost, Time-to-Market, Compliance | Technology choices, scope |

---

## 1. Availability

### Measuring Availability

| Level | Uptime | Downtime/Year | Downtime/Month |
|-------|--------|---------------|----------------|
| 99% | "Two nines" | 3.65 days | 7.31 hours |
| 99.9% | "Three nines" | 8.77 hours | 43.83 minutes |
| 99.95% | | 4.38 hours | 21.92 minutes |
| 99.99% | "Four nines" | 52.60 minutes | 4.38 minutes |
| 99.999% | "Five nines" | 5.26 minutes | 26.30 seconds |

### Availability Patterns

**Redundancy:**
```
                    ┌─────────────┐
                    │Load Balancer│
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
              ▼            ▼            ▼
         ┌────────┐   ┌────────┐   ┌────────┐
         │Instance│   │Instance│   │Instance│
         │   1    │   │   2    │   │   3    │
         └────────┘   └────────┘   └────────┘
```

**Failover:**









- **Active-Passive**: Standby takes over on failure

- **Active-Active**: All instances handle traffic

- **Multi-Region**: Geographic redundancy



**Design Checklist:**

- [ ] No single points of failure identified
- [ ] Health checks implemented (liveness + readiness)
- [ ] Graceful degradation for non-critical features
- [ ] Failure detection time defined (MTTD)
- [ ] Recovery time defined (MTTR)

---

## 2. Scalability

### Scaling Dimensions

| Dimension | Description | Strategies |
|-----------|-------------|------------|
| **Load** | More requests/second | Horizontal scaling, caching |
| **Data** | More storage volume | Partitioning, archival |
| **Complexity** | More features/domains | Modularization, microservices |
| **Geographic** | More regions | Multi-region, CDN |

### Scaling Patterns

**Horizontal Scaling (Scale Out):**
```
Before:     ┌────────┐
            │Instance│
            └────────┘

After:      ┌────────┐  ┌────────┐  ┌────────┐
            │Instance│  │Instance│  │Instance│
            └────────┘  └────────┘  └────────┘
```

**Vertical Scaling (Scale Up):**
```
Before:     ┌────────┐
            │ 4 CPU  │
            │ 8 GB   │
            └────────┘

After:      ┌────────┐
            │ 16 CPU │
            │ 64 GB  │
            └────────┘

```


**Database Scaling:**


| Pattern | Use When | Trade-off |
|---------|----------|-----------|

| **Read Replicas** | Read-heavy workloads | Replication lag |
| **Sharding** | Data exceeds single node | Query complexity |

| **Caching** | Hot data, read-heavy | Cache invalidation |
| **CQRS** | Read/write divergence | Eventual consistency |


**Design Checklist:**

- [ ] Stateless services (no local state)
- [ ] Horizontal scaling possible without code changes
- [ ] Database scaling strategy defined
- [ ] Caching strategy defined
- [ ] Load testing targets established

---

## 3. Performance

### Latency Targets

| Tier | p50 | p95 | p99 | Use Case |
|------|-----|-----|-----|----------|
| **Interactive** | <100ms | <200ms | <500ms | User-facing API |
| **Background** | <1s | <5s | <30s | Async processing |
| **Batch** | N/A | N/A | <hours | Nightly jobs |


### Performance Patterns


**Caching Strategy:**

```
┌────────┐     ┌─────────┐     ┌──────────┐     ┌────────┐

│ Client │────▶│   CDN   │────▶│ App Cache│────▶│Database│

└────────┘     └─────────┘     └──────────┘     └────────┘
                  (Static)      (Dynamic)         (Source)

```


| Cache Type | What to Cache | TTL Strategy |

|------------|---------------|--------------|

| **CDN** | Static assets, API responses | Long (hours/days) |
| **Application** | Computed values, session data | Medium (minutes) |

| **Database** | Query results | Short (seconds) |


**Async Processing:**

- Move non-blocking work off the critical path

- Use message queues for eventual consistency
- Implement fire-and-forget for notifications

**Design Checklist:**

- [ ] Latency targets defined per endpoint tier
- [ ] Critical path identified and optimized
- [ ] Caching strategy documented
- [ ] Database query patterns analyzed
- [ ] Async opportunities identified

---

## 4. Reliability

### Failure Modes

| Failure Type | Example | Mitigation |
|--------------|---------|------------|
| **Crash** | Process dies | Restart policies, redundancy |
| **Hang** | Infinite loop, deadlock | Timeouts, health checks |
| **Byzantine** | Corrupt data, wrong results | Checksums, validation |
| **Cascade** | One failure causes others | Circuit breakers, bulkheads |

### Resilience Patterns

**Circuit Breaker:**
```

         ┌──────────────────────────────────────┐
         │          CIRCUIT BREAKER             │
         │                                      │
         │   CLOSED ──(failures)──▶ OPEN       │
         │      ▲                      │        │

         │      │                      │        │
         │   (success)              (timeout)   │
         │      │                      │        │
         │      └────── HALF-OPEN ◀────┘        │
         └──────────────────────────────────────┘

```

**Bulkhead:**
```
┌─────────────────────────────────────────────────┐

│               REQUEST POOL                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────┐ │
│  │  Critical   │  │   Normal    │  │ Batch   │ │
│  │  (20 conn)  │  │  (50 conn)  │  │(10 conn)│ │
│  └─────────────┘  └─────────────┘  └─────────┘ │

└─────────────────────────────────────────────────┘
```

**Retry Strategy:**
```python

# Exponential backoff with jitter
delay = min(base_delay * (2 ** attempt) + random_jitter, max_delay)
```

**Design Checklist:**

- [ ] All external dependencies have timeouts
- [ ] Circuit breakers for unstable dependencies
- [ ] Retry policies with backoff defined
- [ ] Bulkheads isolate failure domains
- [ ] Fallback behaviors for degraded mode

---

## 5. Security


### Security Layers

```
┌─────────────────────────────────────────────────────────────┐
│                       PERIMETER                             │

│   WAF │ DDoS Protection │ API Gateway │ Rate Limiting       │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                      APPLICATION                            │
│   Authentication │ Authorization │ Input Validation         │

└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                         DATA                                │
│   Encryption at Rest │ Encryption in Transit │ Masking      │
└─────────────────────────────────────────────────────────────┘

                              │
┌─────────────────────────────────────────────────────────────┐
│                      INFRASTRUCTURE                         │
│   Network Segmentation │ Secrets Management │ Audit Logs    │
└─────────────────────────────────────────────────────────────┘
```


### Security Patterns

| Concern | Pattern | Implementation |
|---------|---------|----------------|
| **AuthN** | OAuth2/OIDC | Identity provider (Auth0, Cognito) |

| **AuthZ** | RBAC/ABAC | Policy engine (OPA, custom) |
| **Secrets** | Vault | HashiCorp Vault, AWS Secrets Manager |
| **Encryption** | TLS, AES-256 | mTLS between services, KMS |
| **Audit** | Immutable logs | Append-only audit trail |

**Design Checklist:**

- [ ] Authentication mechanism defined
- [ ] Authorization model documented (RBAC/ABAC)
- [ ] Data classification completed

- [ ] Encryption requirements specified
- [ ] Secrets management approach defined
- [ ] Audit logging requirements captured

---

## 6. Observability


### Three Pillars

```
┌─────────────────────────────────────────────────────────────┐
│                     OBSERVABILITY                           │
│                                                             │

│   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐      │
│   │    LOGS     │   │   TRACES    │   │   METRICS   │      │
│   │             │   │             │   │             │      │
│   │ What        │   │ Request     │   │ Aggregated  │      │
│   │ happened    │   │ flow across │   │ measurements│      │
│   │ (events)    │   │ services    │   │ over time   │      │
│   └─────────────┘   └─────────────┘   └─────────────┘      │

│         │                 │                 │               │
│         └─────────────────┼─────────────────┘               │
│                           │                                 │
│              ┌────────────┴────────────┐                    │
│              │     CORRELATION ID      │                    │
│              │   (Connects all three)  │                    │
│              └─────────────────────────┘                    │

└─────────────────────────────────────────────────────────────┘
```

### SLI/SLO Framework

| Type | Example SLI | Example SLO |
|------|-------------|-------------|


| **Availability** | % of successful requests | 99.9% over 30 days |
| **Latency** | p99 response time | <500ms for 99% |
| **Throughput** | Requests per second | Handle 10,000 RPS |
| **Error Rate** | % of 5xx responses | <0.1% over 24 hours |
| **Freshness** | Age of data | <5 minutes stale |

**Design Checklist:**


- [ ] SLIs defined for each service
- [ ] SLOs established with stakeholders
- [ ] Error budgets calculated
- [ ] Alerting thresholds set
- [ ] Dashboards planned

---


## Quality Attribute Trade-offs

### Trade-off Matrix

| Optimizing For | May Sacrifice | Mitigation |
|----------------|---------------|------------|
| **Performance** | Cost, Simplicity | Targeted optimization |

| **Availability** | Cost, Consistency | Strategic redundancy |
| **Consistency** | Availability, Latency | Scope strong consistency |
| **Security** | Performance, Usability | Risk-based approach |
| **Evolvability** | Short-term velocity | Invest in boundaries |

### CAP Theorem Reminder

```

            Consistency
                 △
                /│\
               / │ \
              /  │  \
             /   │   \
            / CP │ CA \
           /─────┼─────\

          /      │      \
         /   AP  │       \
        ▽────────┴────────▽
   Availability         Partition
                       Tolerance
```

**In distributed systems, during a network partition:**

- **CP**: Sacrifice availability for consistency
- **AP**: Sacrifice consistency for availability
- **CA**: Only possible without partitions (single node)

**Default choice for most systems: AP with eventual consistency**

---

## Requirements Elicitation Template

For each quality attribute, capture:

```markdown
## [Quality Attribute]: [Name]

### Business Context
- Why is this important?
- What's the cost of failure?

### Measurable Target
- Specific: What exactly are we measuring?
- Measurable: What number constitutes success?
- Achievable: Is this realistic?
- Relevant: Does this matter to users/business?
- Time-bound: Over what period?

### Current State
- Baseline measurements (if existing system)
- Gap analysis

### Architectural Implications
- What does this require in the design?
- Trade-offs with other attributes?

### Validation Approach
- How will we test/measure this?
- When will we validate?
```
