# Architecture Styles Reference

> Detailed guidance on selecting and implementing architecture styles based on system requirements.

---

## Decision Matrix

| Style | Best When | Avoid When | Team Size | Complexity |
|-------|-----------|------------|-----------|------------|
| **Modular Monolith** | Starting out, unclear boundaries | Needing independent scaling | 1-3 teams | Low-Medium |
| **Microservices** | Clear domains, independent scaling | Small team, tight deadlines | 3+ teams | High |
| **Event-Driven** | Loose coupling, async workflows | Strong consistency required | 2+ teams | Medium-High |
| **CQRS** | Read/write divergence | Simple CRUD domains | 2+ teams | High |
| **Serverless** | Variable load, event processing | Consistent latency needs | Any | Medium |

---

## 1. Modular Monolith

### Structure

```
┌─────────────────────────────────────────────────────────────┐
│                     MODULAR MONOLITH                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │   Orders    │  │  Payments   │  │  Inventory  │         │
│  │   Module    │  │   Module    │  │   Module    │         │
│  │             │  │             │  │             │         │
│  │ ┌─────────┐ │  │ ┌─────────┐ │  │ ┌─────────┐ │         │
│  │ │ Domain  │ │  │ │ Domain  │ │  │ │ Domain  │ │         │
│  │ ├─────────┤ │  │ ├─────────┤ │  │ ├─────────┤ │         │
│  │ │  App    │ │  │ │  App    │ │  │ │  App    │ │         │
│  │ ├─────────┤ │  │ ├─────────┤ │  │ ├─────────┤ │         │
│  │ │ Infra   │ │  │ │ Infra   │ │  │ │ Infra   │ │         │
│  │ └─────────┘ │  │ └─────────┘ │  │ └─────────┘ │         │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘         │
│         │                │                │                 │
│         └────────────────┼────────────────┘                 │
│                          │                                  │
│              ┌───────────┴───────────┐                      │
│              │    Shared Kernel      │                      │
│              │  (Events, Contracts)  │                      │
│              └───────────────────────┘                      │
└─────────────────────────────────────────────────────────────┘
```

### Module Boundaries

**MUST:**








- Each module has its own domain, application, and infrastructure layers

- Modules communicate through explicit public interfaces (events, APIs)

- Database tables are owned by exactly one module

- No direct imports across module boundaries





**NEVER:**



- Share ORM models across modules

- Use foreign keys across module boundaries

- Call internal module methods from other modules



### When to Choose



✅ **Choose when:**

- Team is small (< 15 engineers)

- Domain boundaries are not yet clear
- Need fast iteration speed
- Deployment simplicity is valued

- Starting a new project

❌ **Avoid when:**

- Need independent scaling per domain
- Teams need autonomous deployment
- Different tech stacks per domain required

### Migration Path

```
Monolith → Modular Monolith → Extract Services
    │              │                  │
    │              │                  └── When: Clear boundary, scaling need
    │              └── When: Growth, clearer domains
    └── Starting point
```

---

## 2. Microservices Architecture

### Structure

```
┌─────────────────────────────────────────────────────────────────────┐

│                          API GATEWAY                                │
└─────────────────────────────────────────────────────────────────────┘
           │                    │                    │
           ▼                    ▼                    ▼

    ┌─────────────┐      ┌─────────────┐      ┌─────────────┐
    │   Orders    │      │  Payments   │      │  Inventory  │

    │   Service   │      │   Service   │      │   Service   │
    │             │      │             │      │             │

    │   ┌─────┐   │      │   ┌─────┐   │      │   ┌─────┐   │
    │   │ DB  │   │      │   │ DB  │   │      │   │ DB  │   │

    │   └─────┘   │      │   └─────┘   │      │   └─────┘   │
    └──────┬──────┘      └──────┬──────┘      └──────┬──────┘

           │                    │                    │
           └────────────────────┼────────────────────┘

                               │
                    ┌──────────┴──────────┐

                    │    Message Broker    │
                    │   (Events/Commands)  │


                    └─────────────────────┘
```


### Service Design Principles




**MUST:**

- Single responsibility: one service, one bounded context
- Database per service: no shared data stores



- API-first: contract defined before implementation
- Autonomous deployment: independent release cycles
- Decentralized governance: teams own their services

**NEVER:**



- Create distributed monoliths (services with tight coupling)
- Share databases or schemas across services
- Make synchronous chains longer than 2 hops
- Deploy multiple services together



### Service Size Heuristics

| Signal | Too Big | Too Small |
|--------|---------|-----------|
| **Team** | Multiple teams working on one service | One team owns 10+ services |
| **Deployment** | Changes require coordinating with others | Deploying 5+ services for one feature |


| **Data** | Service owns unrelated data | Constant cross-service queries |
| **Cohesion** | Mixed business capabilities | Split single business capability |

### When to Choose

✅ **Choose when:**


- Clear domain boundaries exist
- Independent scaling is required
- Multiple teams need autonomy
- Different tech stacks per domain
- High availability requirements

❌ **Avoid when:**

- Small team (< 10 engineers)
- Tight deadlines
- Domain boundaries unclear
- Operational maturity is low

---

## 3. Event-Driven Architecture

### Structure

```

┌─────────────┐                              ┌─────────────┐
│   Orders    │──── OrderPlaced ────────────▶│  Payments   │
│   Service   │                              │   Service   │
└─────────────┘                              └──────┬──────┘
                                                    │
                                            PaymentCompleted

                                                    │
┌─────────────┐                              ┌──────▼──────┐

│  Shipping   │◀─── OrderPaid ──────────────│   Orders    │
│   Service   │                              │   Service   │
└──────┬──────┘                              └─────────────┘
       │
  ShipmentCreated
       │

       ▼
┌─────────────┐

│Notification │
│   Service   │
└─────────────┘
```

### Event Design


**Event Types:**


| Type | Purpose | Example |
|------|---------|---------|
| **Domain Event** | Something that happened | `OrderPlaced`, `PaymentReceived` |
| **Integration Event** | Cross-boundary notification | `CustomerCreated` (published externally) |
| **Command** | Request to do something | `ProcessPayment`, `ShipOrder` |


**Event Schema Requirements:**


```json
{
  "eventId": "uuid-v7",
  "eventType": "OrderPlaced",
  "aggregateId": "order-123",

  "aggregateType": "Order",
  "timestamp": "2026-01-18T10:00:00Z",

  "version": 1,
  "correlationId": "request-456",
  "causationId": "previous-event-789",
  "payload": { ... }
}
```


**MUST:**

- Events are immutable facts (past tense naming)
- Include all context needed by consumers
- Version events for evolution
- Use correlation IDs for tracing

**NEVER:**


- Include references that require lookups
- Use events for queries (use CQRS instead)
- Assume event ordering across partitions
- Design for exactly-once (design for at-least-once + idempotency)

### Choreography vs. Orchestration


| Aspect | Choreography | Orchestration |
|--------|--------------|---------------|
| **Coupling** | Loose (services react independently) | Central coordinator |

| **Visibility** | Distributed (hard to trace) | Centralized (easy to trace) |
| **Flexibility** | Easy to add consumers | Changes require orchestrator update |
| **Complexity** | Emergent behavior | Explicit workflow |
| **Best For** | Simple flows, many consumers | Complex workflows, compensation |

**Decision**: Use choreography by default. Use orchestration (Saga) for complex, multi-step workflows requiring compensation.


---

## 4. CQRS (Command Query Responsibility Segregation)


### Structure

```
                         ┌─────────────────┐
                         │    Commands     │
                         │  (Create, Update│

                         │    Delete)      │
                         └────────┬────────┘
                                  │

                                  ▼
┌─────────────┐           ┌─────────────┐           ┌─────────────┐
│   Write     │           │   Domain    │           │   Event     │
│   Model     │◀──────────│   Logic     │──────────▶│   Store     │
│(Aggregates) │           │             │           │             │
└─────────────┘           └─────────────┘           └──────┬──────┘
                                                          │

                                                   Domain Events
                                                          │
                                  ┌───────────────────────┼───────┐


                                  │                       │       │
                                  ▼                       ▼       ▼
                         ┌─────────────┐          ┌─────────────┐
                         │   Read      │          │   Read      │
                         │   Model 1   │          │   Model 2   │
                         │ (List View) │          │(Detail View)│
                         └──────┬──────┘          └──────┬──────┘

                                │                        │
                                └────────────┬───────────┘
                                             │


                                             ▼
                                  ┌─────────────────┐
                                  │     Queries     │
                                  │   (Read-Only)   │
                                  └─────────────────┘
```


### When to Apply CQRS

✅ **Apply when:**


- Read and write patterns diverge significantly
- Read models need different shapes for different consumers

- Write model is complex (DDD aggregates)
- Scaling reads and writes independently is valuable
- Event sourcing is already in use

❌ **Avoid when:**

- Simple CRUD operations suffice
- Team lacks event-driven experience
- Eventual consistency is unacceptable

- Domain is not complex enough to justify

### Consistency Considerations


| Scenario | Approach |
|----------|----------|
| User creates then immediately views | Optimistic UI, show pending state |
| Dashboard/reporting | Eventual consistency acceptable |
| Financial transactions | Strong consistency, use write model for reads |
| Search/filtering | Dedicated read store, eventual consistency |

---


## 5. Hybrid Approaches


### The Strangler Fig Pattern

For migrating from monolith to services:

```
┌─────────────────────────────────────────────────────────────┐
│                      API GATEWAY                            │
│   (Routes traffic based on feature flags / path)            │
└────────────────────────────┬────────────────────────────────┘

                             │
              ┌──────────────┼──────────────┐
              │              │              │

              ▼              ▼              ▼
       ┌───────────┐  ┌───────────┐  ┌───────────┐
       │   New     │  │   New     │  │  Legacy   │
       │  Service  │  │  Service  │  │ Monolith  │
       │ (Orders)  │  │(Payments) │  │(Remaining)│
       └───────────┘  └───────────┘  └───────────┘
```

**Steps:**

1. Identify bounded context with clearest boundaries
2. Create new service with its own database
3. Route new traffic to new service

4. Migrate data incrementally
5. Deprecate old code paths
6. Repeat for next context

### Cell-Based Architecture

For extreme scale and fault isolation:

```
┌─────────────────────────────────────────────────────────────┐
│                    GLOBAL ROUTER                            │
└─────────────────────────────────────────────────────────────┘
         │                    │                    │

         ▼                    ▼                    ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│     Cell 1      │  │     Cell 2      │  │     Cell 3      │
│   (Region A)    │  │   (Region B)    │  │   (Region C)    │
│  ┌───────────┐  │  │  ┌───────────┐  │  │  ┌───────────┐  │
│  │ All       │  │  │  │ All       │  │  │  │ All       │  │
│  │ Services  │  │  │  │ Services  │  │  │  │ Services  │  │
│  │ + Data    │  │  │  │ + Data    │  │  │  │ + Data    │  │
│  └───────────┘  │  │  └───────────┘  │  │  └───────────┘  │
└─────────────────┘  └─────────────────┘  └─────────────────┘
```

**Use when:**

- Global scale with regional data residency
- Need blast radius isolation
- Can accept eventual consistency between cells

---

## Architecture Evolution Checklist

Before finalizing architecture style:

- [ ] Team size and structure supports the choice
- [ ] Operational maturity matches complexity
- [ ] Domain boundaries are clear enough
- [ ] Consistency requirements are understood
- [ ] Migration path from current state is feasible
- [ ] Technology choices align with team expertise
