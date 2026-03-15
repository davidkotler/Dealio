# Technology Selection Reference

> Decision frameworks for choosing databases, messaging / streaming systems, data processing systems, cloud services, and infrastructure.

---

## Selection Principles

### The "Boring Technology" Philosophy

1. **Innovation Tokens**: Each new technology costs a token. You have ~3 tokens.
2. **Team Expertise**: Weight heavily toward what the team knows
3. **Operational Cost**: Consider maintenance, monitoring, debugging burden
4. **Escape Hatches**: Prefer technologies with migration paths
5. **Community/Support**: Active community, good documentation, vendor support

### Decision Framework

```
┌─────────────────────────────────────────────────────────────┐
│                  TECHNOLOGY DECISION                        │
└─────────────────────────────────────────────────────────────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
              ▼            ▼            ▼
        ┌──────────┐ ┌──────────┐ ┌──────────┐
        │ REQUIRED │ │ OPTIONAL │ │ NICE TO  │
        │CAPABILITY│ │ FEATURES │ │   HAVE   │
        └────┬─────┘ └────┬─────┘ └────┬─────┘
             │            │            │
             └────────────┼────────────┘
                          │
                          ▼
                  ┌───────────────┐
                  │   CANDIDATE   │
                  │   ANALYSIS    │
                  └───────┬───────┘
                          │
         ┌────────────────┼────────────────┐
         │                │                │
         ▼                ▼                ▼
    ┌─────────┐     ┌─────────┐     ┌─────────┐
    │  Team   │     │  Ops    │     │ Future  │
    │Expertise│     │  Cost   │     │  Proof  │
    └─────────┘     └─────────┘     └─────────┘
```

---

## 1. Database Selection

### Decision Matrix

| Requirement | SQL (PostgreSQL) | Document (MongoDB) | Key-Value (Redis) | Wide-Column (Cassandra) |
|-------------|------------------|-------------------|-------------------|-------------------------|
| ACID Transactions | ✅ Strong | ⚠️ Document-level | ❌ No | ⚠️ Lightweight |
| Complex Queries | ✅ Excellent | ⚠️ Limited joins | ❌ Key-only | ❌ Limited |
| Schema Flexibility | ⚠️ Migrations | ✅ Schemaless | ✅ Schemaless | ⚠️ Column families |
| Horizontal Scale | ⚠️ Read replicas | ✅ Sharding | ✅ Clustering | ✅ Designed for it |
| Write Performance | ⚠️ Good | ✅ Fast | ✅ Very fast | ✅ Very fast |
| Operational Ease | ✅ Mature | ⚠️ Moderate | ✅ Simple | ❌ Complex |

### When to Choose What

**PostgreSQL (Default Choice):**







- Complex relationships and joins
- ACID transactions required

- Rich query requirements

- Structured data with schema

- Team knows SQL

- Up to ~10TB, ~50K queries/sec





**MongoDB:**


- Document-centric data model


- Rapid schema evolution
- Hierarchical/nested data


- Geographic distribution
- Flexible schema exploration phase



**Redis:**


- Caching layer
- Session storage

- Rate limiting
- Real-time leaderboards
- Pub/sub messaging

- <100ms latency required

**Cassandra/ScyllaDB:**

- Massive write throughput
- Time-series data
- No complex queries
- Multi-datacenter replication
- Eventual consistency acceptable

### Cloud-Managed Options

| Need | AWS | GCP | Azure |
|------|-----|-----|-------|

| Managed PostgreSQL | RDS, Aurora | Cloud SQL | Azure Database |
| Managed MongoDB | DocumentDB | MongoDB Atlas | Cosmos DB |
| Managed Redis | ElastiCache | Memorystore | Azure Cache |
| Serverless SQL | Aurora Serverless | Cloud SQL | Azure SQL Serverless |

| Global Distribution | DynamoDB Global Tables | Spanner | Cosmos DB |

---



## 2. Messaging & Streaming

### Decision Matrix




| Requirement | Kafka | RabbitMQ | SQS/SNS | Redis Streams |
|-------------|-------|----------|---------|---------------|
| Throughput | ✅ Millions/sec | ⚠️ Thousands/sec | ⚠️ Region-limited | ⚠️ Instance-limited |

| Message Ordering | ✅ Partition-level | ⚠️ Queue-level | ⚠️ FIFO queues | ✅ Stream-level |



| Replay/Retention | ✅ Days/weeks | ❌ No | ❌ No | ⚠️ Limited |
| Consumer Groups | ✅ Native | ⚠️ Competing consumers | ⚠️ Manual | ✅ Native |
| Operational Ease | ❌ Complex | ⚠️ Moderate | ✅ Managed | ✅ Simple |

| Message Routing | ⚠️ Topic-based | ✅ Rich routing | ✅ SNS filtering | ❌ No |




### When to Choose What


**Apache Kafka / AWS MSK / Confluent:**



- High throughput event streaming
- Event sourcing / CQRS
- Log aggregation

- Real-time analytics pipelines


- Message replay required
- Multiple consumer groups

**RabbitMQ:**

- Complex routing requirements



- Request-reply patterns
- Priority queues
- Lower throughput, richer features
- Team familiar with AMQP

**AWS SQS/SNS:**




- Serverless architectures
- Simple pub/sub
- No operational overhead desired
- AWS-native ecosystem
- Dead letter queue requirements

**Redis Streams:**



- Already using Redis
- Simple streaming needs
- Low latency required
- Moderate throughput

### Event Schema Management


| Approach | Tool | When |

|----------|------|------|
| Schema Registry | Confluent, AWS Glue | Kafka ecosystem |
| AsyncAPI | AsyncAPI Spec | Documentation-first |
| Protocol Buffers | protobuf | Cross-language, compact |
| JSON Schema | JSON Schema | Flexibility, readability |

---



## 3. API Gateway & Service Mesh

### API Gateway Options

| Feature | Kong | AWS API Gateway | Traefik | Envoy |
|---------|------|-----------------|---------|-------|
| Rate Limiting | ✅ | ✅ | ✅ | ✅ |

| Authentication | ✅ | ✅ | ⚠️ | ⚠️ |

| Transformations | ✅ | ✅ | ⚠️ | ⚠️ |
| Analytics | ✅ | ✅ | ⚠️ | ⚠️ |
| Self-Hosted | ✅ | ❌ | ✅ | ✅ |
| Operational Ease | ⚠️ | ✅ | ✅ | ❌ |

### Service Mesh Decision


**When to use a service mesh:**

- 10+ services
- Complex traffic management
- mTLS between services
- Advanced observability
- Canary deployments

**Options:**

| Mesh | Complexity | Features | Best For |
|------|------------|----------|----------|
| Istio | High | Full-featured | Large deployments |
| Linkerd | Medium | Lightweight | Kubernetes-native |
| Consul Connect | Medium | Multi-platform | HashiCorp ecosystem |
| AWS App Mesh | Low | AWS-integrated | AWS-native |

---

## 4. Compute & Runtime

### Compute Options

| Pattern | Best For | Limitations |
|---------|----------|-------------|
| **Containers (ECS/EKS/GKE)** | Long-running services, consistent workloads | Operational overhead |
| **Serverless (Lambda/Cloud Functions)** | Event-driven, variable load, low traffic | Cold starts, time limits |
| **VMs (EC2/Compute Engine)** | Legacy apps, special requirements | Management overhead |
| **Edge (CloudFlare Workers)** | Low latency, globally distributed | Limited runtime |

### Container Orchestration

| Requirement | ECS | EKS/GKE | Nomad |
|-------------|-----|---------|-------|
| Simplicity | ✅ | ❌ | ⚠️ |
| Kubernetes Ecosystem | ❌ | ✅ | ❌ |
| Multi-Cloud | ❌ | ⚠️ | ✅ |
| Operational Cost | ✅ Low | ❌ High | ⚠️ Medium |

**Recommendation**: Start with ECS for simplicity. Move to EKS/GKE when Kubernetes ecosystem benefits outweigh operational cost.

---

## 5. Caching Strategy

### Caching Layers

```
┌─────────────────────────────────────────────────────────────┐
│                      CACHING STRATEGY                       │
│                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│  │   BROWSER   │    │     CDN     │    │     APP     │     │
│  │    CACHE    │───▶│    CACHE    │───▶│    CACHE    │     │
│  │             │    │             │    │             │     │
│  │  • Static   │    │  • Static   │    │  • Session  │     │
│  │  • SW Cache │    │  • API resp │    │  • Computed │     │
│  └─────────────┘    └─────────────┘    └─────────────┘     │
│                                               │             │
│                                               ▼             │
│                                        ┌─────────────┐     │
│                                        │  DATABASE   │     │
│                                        │    CACHE    │     │
│                                        │             │     │
│                                        │  • Query    │     │
│                                        │  • Object   │     │
│                                        └─────────────┘     │
└─────────────────────────────────────────────────────────────┘
```

### Cache Invalidation Strategies

| Strategy | How | When |
|----------|-----|------|
| **TTL** | Expire after duration | Read-heavy, staleness OK |
| **Write-Through** | Update cache on write | Strong consistency needed |
| **Write-Behind** | Async cache update | High write throughput |
| **Cache-Aside** | App manages cache | Flexible, common pattern |
| **Event-Driven** | Invalidate on events | Microservices, eventual consistency |

---

## 6. Observability Stack

### Three Pillars Stack

| Pillar | Open Source | Commercial | Cloud-Native |
|--------|-------------|------------|--------------|
| **Logs** | ELK, Loki | Splunk, Datadog | CloudWatch, Stackdriver |
| **Metrics** | Prometheus, Graphite | Datadog, New Relic | CloudWatch, Cloud Monitoring |
| **Traces** | Jaeger, Zipkin | Datadog, Honeycomb | X-Ray, Cloud Trace |

### Recommended Stack by Scale

| Scale | Logs | Metrics | Traces | Dashboards |
|-------|------|---------|--------|------------|
| **Startup** | CloudWatch/Loki | CloudWatch | X-Ray | Grafana Cloud |
| **Growth** | Datadog | Datadog | Datadog | Datadog |
| **Enterprise** | Splunk/ELK | Prometheus | Jaeger | Grafana |

---

## 7. Technology Evaluation Template

```markdown
## Technology Evaluation: [Technology Name]

### Context
- **Problem**: What are we solving?
- **Constraints**: Budget, timeline, team expertise

### Candidates Evaluated
| Option | Pros | Cons |
|--------|------|------|
| Option A | | |
| Option B | | |
| Option C | | |

### Evaluation Criteria
| Criterion | Weight | Option A | Option B | Option C |
|-----------|--------|----------|----------|----------|
| Capability fit | 30% | | | |
| Team expertise | 25% | | | |
| Operational cost | 20% | | | |
| Community/support | 15% | | | |
| Future-proofing | 10% | | | |
| **Total** | 100% | | | |

### Recommendation
[Selected option with rationale]

### Migration Path
[How to move if this choice doesn't work out]

### Decision Date
[Date] - [Decision makers]
```

---

## Anti-Patterns to Avoid

| Anti-Pattern | Why It's Bad | Instead |
|--------------|--------------|---------|
| **Resume-Driven Development** | Complexity without value | Boring technology |
| **Database per Microservice** (premature) | Operational explosion | Start shared, extract later |
| **Kafka for Everything** | Over-engineering | Right tool for the job |
| **No Managed Services** | Undifferentiated heavy lifting | Use managed when sensible |
| **Multi-Cloud Day 1** | Complexity explosion | Single cloud, portable abstractions |
