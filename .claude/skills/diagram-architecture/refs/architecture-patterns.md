# Architecture Pattern Templates

Ready-to-adapt Mermaid templates for common architecture patterns. Copy, modify node names
and labels to match your system. Each pattern includes structural and behavioral views.

## Table of Contents

1. [Microservices Topology](#microservices-topology)
2. [Event-Driven / CQRS](#event-driven--cqrs)
3. [Hexagonal / Ports & Adapters](#hexagonal--ports--adapters)
4. [Layered Architecture](#layered-architecture)
5. [DDD Bounded Contexts](#ddd-bounded-contexts)
6. [Data Flow Pipeline](#data-flow-pipeline)
7. [API Gateway Pattern](#api-gateway-pattern)
8. [Saga Pattern](#saga-pattern)
9. [Cloud Infrastructure](#cloud-infrastructure)
10. [CI/CD Pipeline](#cicd-pipeline)

---

## Microservices Topology

Subgraph layers separate client, gateway, services, messaging, and data tiers.
Use `LR` direction for left-to-right data flow. Label edges with protocols.

### Structural View (Flowchart)

```
flowchart LR
    subgraph Clients["Client Layer"]
        web([Web App])
        mobile([Mobile App])
    end

    subgraph Gateway["API Layer"]
        gw[API Gateway]
    end

    subgraph Services["Service Layer"]
        auth[Auth Service]
        orders[Order Service]
        payments[Payment Service]
        notifications[Notification Service]
    end

    subgraph Messaging["Messaging"]
        bus[(Event Bus)]
    end

    subgraph Data["Data Layer"]
        authDB[(Auth DB)]
        orderDB[(Order DB)]
        paymentDB[(Payment DB)]
        cache[(Redis Cache)]
    end

    web -->|REST/HTTPS| gw
    mobile -->|REST/HTTPS| gw
    gw -->|JWT validation| auth
    gw -->|REST| orders
    gw -->|REST| payments
    orders -->|publishes OrderCreated| bus
    bus -->|subscribes| payments
    bus -->|subscribes| notifications
    auth --> authDB
    orders --> orderDB
    payments --> paymentDB
    gw --> cache

    classDef client fill:#E3F2FD,stroke:#1565C0,color:#333
    classDef gateway fill:#FFF3E0,stroke:#EF6C00,color:#333
    classDef service fill:#4A90D9,stroke:#2E5C8A,color:#fff
    classDef messaging fill:#F5A623,stroke:#C68A1A,color:#fff
    classDef data fill:#2E86C1,stroke:#1B4F72,color:#fff

    class web,mobile client
    class gw gateway
    class auth,orders,payments,notifications service
    class bus messaging
    class authDB,orderDB,paymentDB,cache data
```

### Behavioral View (Sequence)

```
sequenceDiagram
    autonumber
    participant C as Client
    participant GW as API Gateway
    participant OS as Order Service
    participant PS as Payment Service
    participant EB as Event Bus
    participant NS as Notification Service

    C->>+GW: POST /orders
    GW->>+OS: CreateOrder()
    OS->>OS: Validate & persist order
    OS-->>-GW: Order created (pending)
    GW-->>-C: 201 Created

    OS-)EB: OrderCreated event
    par Payment Processing
        EB-)PS: OrderCreated
        PS->>PS: Process payment
        PS-)EB: PaymentCompleted
    and Notification
        EB-)NS: OrderCreated
        NS->>NS: Send confirmation email
    end
```

---

## Event-Driven / CQRS

Separate command (write) and query (read) paths connected by an event bus.
Show structural separation in flowchart, temporal flow in sequence diagram.

### Structural View

```
flowchart TB
    subgraph CommandSide["Command Side (Write)"]
        cmdAPI[Command API]
        cmdHandler[Command Handlers]
        domain[Domain Model]
        writeDB[(Write Store)]
    end

    subgraph EventInfra["Event Infrastructure"]
        eventBus[(Event Bus)]
    end

    subgraph QuerySide["Query Side (Read)"]
        projector[Event Projector]
        readDB[(Read Store)]
        queryAPI[Query API]
    end

    cmdAPI -->|"validates & routes"| cmdHandler
    cmdHandler -->|"executes business logic"| domain
    domain -->|"persists aggregates"| writeDB
    domain -->|"publishes domain events"| eventBus

    eventBus -->|"projects events"| projector
    projector -->|"updates read model"| readDB
    readDB -->|"serves queries"| queryAPI

    classDef command fill:#E8F5E9,stroke:#2E7D32,color:#333
    classDef event fill:#FFF3E0,stroke:#EF6C00,color:#333
    classDef query fill:#E3F2FD,stroke:#1565C0,color:#333

    class cmdAPI,cmdHandler,domain,writeDB command
    class eventBus event
    class projector,readDB,queryAPI query
```

### Behavioral View

```
sequenceDiagram
    participant Client
    participant CmdAPI as Command API
    participant Domain
    participant WriteDB as Write Store
    participant EventBus as Event Bus
    participant Projector
    participant ReadDB as Read Store
    participant QueryAPI as Query API

    Client->>+CmdAPI: POST /orders (Command)
    CmdAPI->>+Domain: Execute CreateOrder
    Domain->>WriteDB: Persist aggregate
    Domain-)EventBus: Publish OrderCreated
    Domain-->>-CmdAPI: Success
    CmdAPI-->>-Client: 202 Accepted

    Note over EventBus,ReadDB: Eventually consistent

    EventBus-)Projector: OrderCreated event
    Projector->>ReadDB: Update read model

    Client->>QueryAPI: GET /orders/{id}
    QueryAPI->>ReadDB: Query read model
    ReadDB-->>QueryAPI: Order projection
    QueryAPI-->>Client: 200 OK
```

---

## Hexagonal / Ports & Adapters

Concentric layers: driving adapters → application core → driven adapters.
Dotted arrows show adapter implementations of port interfaces.
Subroutine nodes (`[[text]]`) represent ports.

```
flowchart TB
    subgraph Driving["Driving Adapters (Inbound)"]
        rest[REST Controller]
        graphql[GraphQL Resolver]
        events[Event Handler]
    end

    subgraph Core["Application Core"]
        subgraph App["Application Layer"]
            useCase1[Create Order]
            useCase2[Cancel Order]
        end
        subgraph Domain["Domain Layer"]
            entity[Order Aggregate]
            repoPort[[Order Repository Port]]
            msgPort[[Message Publisher Port]]
            payPort[[Payment Gateway Port]]
        end
    end

    subgraph Driven["Driven Adapters (Outbound)"]
        pgAdapter[PostgreSQL Adapter]
        kafkaAdapter[Kafka Adapter]
        stripeAdapter[Stripe Adapter]
    end

    rest --> useCase1
    graphql --> useCase1
    events --> useCase2
    useCase1 --> entity
    useCase2 --> entity

    repoPort -.->|implements| pgAdapter
    msgPort -.->|implements| kafkaAdapter
    payPort -.->|implements| stripeAdapter

    classDef driving fill:#E3F2FD,stroke:#1565C0,color:#333
    classDef core fill:#FFF9C4,stroke:#F9A825,color:#333
    classDef driven fill:#F3E5F5,stroke:#7B1FA2,color:#333
    classDef port fill:#FFECB3,stroke:#FF8F00,color:#333

    class rest,graphql,events driving
    class useCase1,useCase2,entity core
    class repoPort,msgPort,payPort port
    class pgAdapter,kafkaAdapter,stripeAdapter driven
```

---

## Layered Architecture

Top-to-bottom flow with horizontal layer subgraphs. Dotted arrows between
domain and infrastructure show dependency inversion.

```
flowchart TB
    subgraph Presentation["Presentation Layer"]
        api[REST API]
        ws[WebSocket Handler]
    end

    subgraph Application["Application Layer"]
        svc1[Order Service]
        svc2[User Service]
    end

    subgraph Domain["Domain Layer"]
        entities[Domain Entities]
        ports[[Repository Ports]]
    end

    subgraph Infrastructure["Infrastructure Layer"]
        repo[Repository Impl]
        db[(Database)]
        cache[(Cache)]
        extAPI[External API Client]
    end

    api --> svc1
    ws --> svc2
    svc1 --> entities
    svc2 --> entities
    entities --> ports

    ports -.->|implements| repo
    repo --> db
    repo --> cache
    svc1 -.-> extAPI
```

---

## DDD Bounded Contexts

Each context is a subgraph with its own API, aggregate, and data store.
Cross-context communication flows through events with domain event names as labels.

```
flowchart LR
    subgraph OrderCtx["Order Context"]
        orderAPI[Order API]
        orderAgg[Order Aggregate]
        orderDB[(Order DB)]
        orderAPI --> orderAgg --> orderDB
    end

    subgraph PaymentCtx["Payment Context"]
        payAPI[Payment API]
        payAgg[Payment Aggregate]
        payDB[(Payment DB)]
        payAPI --> payAgg --> payDB
    end

    subgraph InventoryCtx["Inventory Context"]
        invAPI[Inventory API]
        invAgg[Inventory Aggregate]
        invDB[(Inventory DB)]
        invAPI --> invAgg --> invDB
    end

    subgraph SharedKernel["Integration Layer"]
        eventBus[(Event Bus)]
    end

    OrderCtx -->|"OrderPlaced"| eventBus
    eventBus -->|"OrderPlaced"| PaymentCtx
    eventBus -->|"OrderPlaced"| InventoryCtx
    PaymentCtx -->|"PaymentCompleted"| eventBus
    eventBus -->|"PaymentCompleted"| OrderCtx
```

---

## Data Flow Pipeline

Source → Processing → Storage → Consumption with semantic color coding per layer.

```
flowchart LR
    subgraph Sources["Data Sources"]
        api[REST API]
        webhook[Webhooks]
        batch[Batch Import]
    end

    subgraph Processing["Processing Layer"]
        direction TB
        validate[Validation]
        transform[Transformation]
        enrich[Enrichment]
        validate --> transform --> enrich
    end

    subgraph Storage["Storage Layer"]
        dw[(Data Warehouse)]
        lake[(Data Lake)]
        cache[(Cache)]
    end

    subgraph Consumption["Consumption Layer"]
        dashboard[Dashboards]
        ml[ML Pipeline]
        reports[Reports]
    end

    api & webhook & batch --> validate
    enrich --> dw & lake
    enrich --> cache
    dw --> dashboard & reports
    lake --> ml

    classDef source fill:#E3F2FD,stroke:#1565C0,color:#333
    classDef process fill:#FFF3E0,stroke:#EF6C00,color:#333
    classDef store fill:#E8F5E9,stroke:#2E7D32,color:#333
    classDef consume fill:#F3E5F5,stroke:#7B1FA2,color:#333

    class api,webhook,batch source
    class validate,transform,enrich process
    class dw,lake,cache store
    class dashboard,ml,reports consume
```

---

## API Gateway Pattern

Fan-out from gateway to backend services with protocol labels,
rate limiting, and auth as cross-cutting concerns.

```
flowchart LR
    subgraph Clients
        web([Web App])
        mobile([Mobile App])
        partner([Partner API])
    end

    subgraph Edge["Edge Layer"]
        waf[WAF]
        lb[Load Balancer]
        gw[API Gateway]
    end

    subgraph CrossCutting["Cross-Cutting"]
        auth[Auth / JWT]
        rateLimit[Rate Limiter]
        circuit[Circuit Breaker]
    end

    subgraph Backend["Backend Services"]
        svcA[Service A]
        svcB[Service B]
        svcC[Service C]
    end

    web & mobile & partner -->|HTTPS| waf --> lb --> gw
    gw --> auth & rateLimit
    gw -->|REST| svcA
    gw -->|gRPC| svcB
    gw -->|GraphQL| svcC
    gw --> circuit
```

---

## Saga Pattern

Orchestrated saga with compensation flows shown via `alt` blocks.

```
sequenceDiagram
    autonumber
    participant O as Saga Orchestrator
    participant Pay as Payment Service
    participant Inv as Inventory Service
    participant Ship as Shipping Service

    O->>+Pay: ChargeCustomer
    Pay-->>-O: PaymentConfirmed

    O->>+Inv: ReserveItems
    Inv-->>-O: ItemsReserved

    O->>+Ship: CreateShipment

    alt Shipping Fails
        Ship-->>-O: ShipmentFailed
        rect rgb(255,230,230)
            Note over O,Pay: Compensation Flow
            O->>Inv: ReleaseReservation
            O->>Pay: RefundPayment
        end
    else Shipping Succeeds
        Ship-->>-O: ShipmentCreated
        O->>O: Saga Complete
    end
```

---

## Cloud Infrastructure

### Using architecture-beta

```
architecture-beta
    group cloud(cloud)[AWS Cloud]
    group vpc(cloud)[VPC 10.0.0.0/16] in cloud
    group publicSubnet(cloud)[Public Subnet] in vpc
    group privateSubnet(cloud)[Private Subnet] in vpc
    group dataSubnet(cloud)[Data Subnet] in vpc

    service inet(internet)[Internet] in cloud
    service alb(server)[ALB] in publicSubnet
    service api(server)[API Server] in privateSubnet
    service worker(server)[Worker] in privateSubnet
    service rds(database)[RDS PostgreSQL] in dataSubnet
    service redis(database)[ElastiCache Redis] in dataSubnet
    service sqs(disk)[SQS Queue] in privateSubnet

    inet:R --> L:alb
    alb:R --> L:api
    api:B --> T:rds
    api:R --> L:redis
    api:B --> T:sqs
    sqs:R --> L:worker
    worker:B --> T:rds
```

### Using C4 Deployment

```
C4Deployment
    title Production Deployment — AWS

    Deployment_Node(aws, "AWS", "Cloud Provider") {
        Deployment_Node(vpc, "VPC", "10.0.0.0/16") {
            Deployment_Node(ecs, "ECS Cluster", "Fargate") {
                Container(api, "API Server", "Python/FastAPI")
                Container(worker, "Worker", "Python/FastStream")
            }
            Deployment_Node(rds, "RDS", "Multi-AZ") {
                ContainerDb(db, "PostgreSQL", "db.r6g.xlarge")
            }
            Deployment_Node(cache, "ElastiCache", "Cluster Mode") {
                ContainerDb(redis, "Redis", "cache.r6g.large")
            }
        }
    }

    Rel(api, db, "SQL", "Port 5432")
    Rel(api, redis, "Redis Protocol", "Port 6379")
    Rel(worker, db, "SQL", "Port 5432")
```

---

## CI/CD Pipeline

Left-to-right flowchart with diamond nodes for approval gates.

```
flowchart LR
    subgraph Trigger["Trigger"]
        push([Git Push])
    end

    subgraph Build["Build Stage"]
        lint[Lint & Format]
        typeCheck[Type Check]
        unitTest[Unit Tests]
        build[Build Artifacts]
    end

    subgraph Test["Test Stage"]
        intTest[Integration Tests]
        contractTest[Contract Tests]
        scan[Security Scan]
    end

    subgraph Deploy["Deployment"]
        staging{Deploy to Staging?}
        stagingDeploy[Staging Deploy]
        e2e[E2E Tests]
        prod{Deploy to Prod?}
        prodDeploy[Prod Deploy]
        smoke[Smoke Tests]
    end

    push --> lint --> typeCheck --> unitTest --> build
    build --> intTest & contractTest & scan
    intTest & contractTest & scan --> staging
    staging -->|Approved| stagingDeploy --> e2e --> prod
    staging -->|Rejected| push
    prod -->|Approved| prodDeploy --> smoke
    prod -->|Rejected| push

    classDef gate fill:#FFF3E0,stroke:#EF6C00,color:#333
    class staging,prod gate
```
