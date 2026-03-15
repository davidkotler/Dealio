# Data Model Design Reference

> Layered data architecture for domain-driven systems — declare once, inherit everywhere, map automatically.

---

## Table of Contents

1. [Core Philosophy](#core-philosophy)
2. [Layer Architecture](#layer-architecture)
3. [Layer 0 — Common (Primitives & Mixins)](#layer-0--common-primitives--mixins)
4. [Layer 1 — Domain Models](#layer-1--domain-models)
5. [Layer 2 — Contract Models (API & Event)](#layer-2--contract-models-api--event)
6. [Layer 3 — Persistence Models](#layer-3--persistence-models)
7. [Dependency Rules](#dependency-rules)
8. [Composition via Mixins](#composition-via-mixins)
9. [Model-Owned Mapping](#model-owned-mapping)
10. [Shared vs Service-Local Placement](#shared-vs-service-local-placement)
11. [Field Naming Conventions](#field-naming-conventions)
12. [Anti-Patterns](#anti-patterns)
13. [Decision Guide](#decision-guide)
14. [Quality Gates](#quality-gates)

---

## Core Philosophy

Three principles govern how data models are structured across a system:

**1. Ubiquitous Language — Declare Once**
Every field is declared in exactly one place and reused across all layers. A `recipient_id` in the domain model is `recipient_id` in the API response, the event payload, and the database row. No synonyms, no translations, no re-declarations.

**2. Information Hiding**
Each service owns its persistence model. Other services interact only through contracts (API responses and event payloads). A service can change how it stores data without breaking any consumer.

**3. Layered Separation**
Data flows through four distinct layers, each with a clear responsibility. Models compose upward from primitives. Each layer adds only what it needs — it never duplicates what lower layers already define.

---

## Layer Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Consumers                            │
│         (UI, other services, external clients)          │
└───────────────────────┬─────────────────────────────────┘
                        │ Contracts (API / Event)
┌───────────────────────▼─────────────────────────────────┐
│               Layer 2 — Contracts                       │
│     API request/response models, Event payloads         │
│     "How we communicate the domain"                     │
└───────────────────────┬─────────────────────────────────┘
                        │ inherits from
┌───────────────────────▼─────────────────────────────────┐
│               Layer 1 — Domain Models                   │
│     Entities, Value Objects, Aggregates                  │
│     "What the domain IS"                                │
└───────────────────────┬─────────────────────────────────┘
                        │ composes from
┌───────────────────────▼─────────────────────────────────┐
│            Layer 0 — Common (Primitives & Mixins)       │
│     IDs, Enums, Audit, Value Objects                    │
│     "Shared building blocks"                            │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│               Layer 3 — Persistence                     │
│     Storage-specific models                             │
│     "How we store domain data"                          │
│     Inherits from Domain, always service-local          │
└─────────────────────────────────────────────────────────┘
```

| Layer | Responsibility | Depends On |
|-------|----------------|------------|
| **0 — Common** | Primitives, mixins, value objects, enums | Nothing |
| **1 — Domain** | Entities, aggregates, domain value objects | Common |
| **2 — Contracts** | API req/res, event payloads | Common, Domain |
| **3 — Persistence** | Storage models, DB-specific fields | Common, Domain |

---

## Layer 0 — Common (Primitives & Mixins)

Common holds the atomic building blocks that every other layer composes from. Nothing in this layer depends on domain, contracts, or persistence.

### What belongs here

| Category | Purpose | Examples |
|----------|---------|----------|
| IDs | Typed ID wrappers and generators | `EntityId`, `new_entity_id()`, prefixed IDs (`usr_`, `ord_`) |
| Enums | Cross-boundary enumerations | `SortDirection`, `Environment`, `Currency` |
| Values | Immutable value objects shared across boundaries | `Money`, `DateRange`, `EmailAddress` |
| Mixins | Composable cross-cutting concern mixins | `AuditMixin`, `TenantMixin`, `CreatedByMixin` |

### MUST

- Declare each field exactly once — if `created_at` exists in `AuditMixin`, no other layer redefines it
- Make all mixins frozen, immutable model classes designed for multiple-inheritance composition
- Use annotated fields with explicit validation, documentation, and constraints
- Keep mixins single-purpose — one cross-cutting concern per mixin

### NEVER

- Import from domain, contracts, or persistence layers
- Put business logic in common types — they are pure data definitions
- Create "kitchen sink" mixins that combine unrelated concerns

### Example

```python
from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from typing import Annotated

class AuditMixin(BaseModel):
    """Tracks creation and modification timestamps."""
    model_config = ConfigDict(frozen=True)

    created_at: Annotated[datetime, Field(description="When this record was created (UTC)")]
    updated_at: Annotated[datetime | None, Field(description="When last modified (UTC)")] = None

class TenantMixin(BaseModel):
    """Multi-tenant isolation — every tenant-scoped record carries organization_id."""
    model_config = ConfigDict(frozen=True)

    organization_id: Annotated[str, Field(min_length=1, description="Owning organization/tenant ID")]

class SoftDeleteMixin(BaseModel):
    """Soft-delete support — composed at the persistence layer only, never on domain."""
    model_config = ConfigDict(frozen=True)

    deleted_at: Annotated[datetime | None, Field(description="Soft-delete timestamp")] = None
    deleted_by: Annotated[str | None, Field(description="Actor who deleted this record")] = None

class VersionedMixin(BaseModel):
    """Optimistic concurrency — composed at the persistence layer only."""
    model_config = ConfigDict(frozen=True)

    version: Annotated[int, Field(description="Row version for optimistic locking")] = 1
```

> **Note:** `SoftDeleteMixin` and `VersionedMixin` are defined in common for reuse, but composed only at the persistence layer — never on domain models.

---

## Layer 1 — Domain Models

Domain models express the business language. They compose common mixins and add domain-specific fields. A domain model is the **single source of truth** for what a concept IS.

### MUST

- Declare one model per concept — each entity is defined exactly once
- Compose mixins to assemble cross-cutting concerns without duplication
- Keep models framework-agnostic — no ORM decorators, no API-specific fields, no storage details
- Use domain terminology — if the business says "recipient", the field is `recipient_id`, not `user_id`
- Make all models frozen and immutable

### NEVER

- Put business logic or side effects in models — models are data, logic lives in flows/services
- Include storage-specific concerns — domain models represent what a concept IS, not how it's stored
- Include API-specific concerns (HATEOAS links, pagination metadata)
- Use generic names (`Handler`, `Processor`) when domain terms exist

### WHEN → THEN

| When | Then |
|------|------|
| An entity is tracked by identity over time | Model as Entity with a typed ID field |
| A concept is defined solely by its attributes | Model as Value Object (in common layer) |
| Multiple entities must be atomically consistent | Group into same Aggregate |
| A significant state change occurs | Emit a Domain Event |
| Another service consumes this model via API/event | Place in shared schemas package |
| Model is only used in-process within one service | Place in service-local models |

### Example

```python
class Order(TenantMixin, AuditMixin):
    """A customer order — the domain's single source of truth for this concept."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    order_id: Annotated[EntityId, Field(description="Unique order identifier")]
    customer_id: Annotated[EntityId, Field(description="Customer who placed this order")]
    status: Annotated[OrderStatus, Field(description="Current order lifecycle status")]
    total_cents: Annotated[int, Field(ge=0, description="Order total in cents")]
    currency: Annotated[str, Field(min_length=3, max_length=3, description="ISO 4217 currency code")]
```

Notice: `organization_id`, `created_at`, `updated_at` come from mixins. Storage-specific concerns (soft-delete, partition keys, row versioning, denormalized fields) are NOT here — those belong on persistence models.

---

## Layer 2 — Contract Models (API & Event)

Contracts define how the domain is communicated to consumers. They **inherit from domain models** so that domain fields ("hard" fields) are declared once and never duplicated.

### Two sub-types

| Type | Purpose |
|------|---------|
| **API contracts** | HTTP request/response shapes — what consumers see over the wire |
| **Event contracts** | Async event payloads — what consumers receive from the message broker |

### MUST

- **Inherit API response models from the domain model** — all domain fields come for free
- Exclude internal fields from serialization using `Field(exclude=True)` when consumers should not see them
- Use the same field names as the domain model — ubiquitous language is non-negotiable
- Version contracts and maintain backward compatibility
- Wrap responses in standard envelopes (`ApiResponse[T]`, `EventEnvelope[T]`)

### NEVER

- Redeclare fields that the domain model already defines — inherit instead
- Expose persistence details (table names, column aliases, DB-specific types) in contracts
- Expose internal domain fields that consumers don't need (e.g., `organization_id` to external clients)
- Break existing consumers without a deprecation period

### API contract example

```python
class OrderResponse(Order):
    """API response — inherits all domain fields, hides internal ones.

    Gets for free: order_id, customer_id, status, total_cents, currency,
    created_at, updated_at (from Order + mixins).
    Excludes: organization_id (internal tenant concern).
    """
    model_config = ConfigDict(frozen=True, extra="forbid")

    # Hide internal fields from API serialization
    organization_id: Annotated[str, Field(exclude=True)] = ""
```

Zero field duplication. `OrderResponse` gets `order_id`, `customer_id`, `status`, `total_cents`, `currency`, `created_at`, `updated_at` automatically via inheritance.

### Summary/projection models

For list endpoints where a smaller shape is needed, create a standalone projection model:

```python
class OrderSummary(BaseModel):
    """Compact projection for list endpoints — fewer fields, lower bandwidth."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    order_id: Annotated[EntityId, Field(description="Unique order identifier")]
    status: Annotated[OrderStatus, Field(description="Current order lifecycle status")]
    total_cents: Annotated[int, Field(ge=0, description="Order total in cents")]
    created_at: Annotated[datetime, Field(description="When the order was placed")]
```

Summary models are projections, not full domain models — standalone declaration is acceptable.

### Event contract example

```python
class OrderPlaced(DomainEvent):
    """Published when a new order is placed."""
    __event_type__: ClassVar[str] = "order.placed"
    __event_version__: ClassVar[int] = 1

    model_config = ConfigDict(frozen=True, extra="forbid")

    order_id: Annotated[EntityId, Field(description="Unique order identifier")]
    customer_id: Annotated[EntityId, Field(description="Customer who placed this order")]
    total_cents: Annotated[int, Field(ge=0, description="Order total in cents")]
    currency: Annotated[str, Field(description="ISO 4217 currency code")]
```

Events use the same field names as the domain model because they speak the same ubiquitous language.

---

## Layer 3 — Persistence Models

Persistence models define how domain data is stored. They **inherit from the domain model** (same as contracts) and add only persistence-specific fields.

Persistence models are **always service-local** — storage is an implementation detail hidden behind the service boundary.

### MUST

- Make persistence models inherit from the domain model — all domain fields come for free
- Use the same Pydantic `BaseModel` foundation as domain and contract models
- Add only storage-specific fields — persistence models diverge from domain only where storage requires it
- Provide `from_domain()` / `to_domain()` methods using `model_dump()` for automatic mapping
- Keep all persistence models inside the owning service — never shared

### NEVER

- Import persistence models from another service — use contracts instead
- Use explicit field-by-field mapping — use `model_dump()` to spread fields automatically
- Let storage concerns leak into domain models — domain models represent what a concept IS, not how it's stored
- Expose persistence models through API responses or event payloads

### What are storage-specific concerns?

Domain models represent business concepts. Persistence models can diverge from domain in many ways — any concern that exists solely because of how data is stored belongs on the persistence model, not the domain.

| Concern | What it adds | Example |
|---------|-------------|---------|
| **Soft-delete** | Logical deletion tracking | `deleted_at`, `deleted_by` |
| **Row versioning** | Optimistic concurrency control | `version: int`, `etag: str` |
| **Partition / shard keys** | Data distribution for scalability | `partition_key`, `shard_id` |
| **Denormalized fields** | Redundant data to avoid joins | `customer_name` copied from customer table |
| **Flattened relationships** | Two domain objects stored as one row | Embedding address fields directly in an order row |
| **Storage-specific types** | DB-optimized representations | JSONB columns, binary serialization, compressed fields |
| **Indexing metadata** | Fields that exist solely for query performance | `search_vector`, computed sort keys |

### Example

```python
class OrderRecord(Order):
    """Persistence model — inherits all domain fields, adds storage concerns.

    Inherits: order_id, customer_id, status, total_cents, currency,
    organization_id, created_at, updated_at (from Order + mixins).
    Adds: storage-specific fields for deletion tracking and data distribution.
    """
    model_config = ConfigDict(frozen=True, extra="forbid")

    deleted_at: Annotated[datetime | None, Field(description="Soft-delete timestamp")] = None
    deleted_by: Annotated[str | None, Field(description="Actor who deleted")] = None
    partition_key: Annotated[str | None, Field(description="Data distribution key")] = None

    @classmethod
    def from_domain(cls, domain: Order) -> "OrderRecord":
        """Domain → Record. Spreads all domain fields automatically."""
        return cls(**domain.model_dump())

    def to_domain(self) -> Order:
        """Record → Domain. Drops storage-specific fields automatically."""
        return Order(**self.model_dump(exclude={"deleted_at", "deleted_by", "partition_key"}))
```

### Why storage concerns belong here, not on the domain

The domain model represents what a concept IS. Storage concerns — soft-delete, row versioning, partition keys, denormalized fields — exist because of how and where data is stored. These are implementation details of the service's data layer. If a consumer needs to know about a storage concern (e.g., when something was deleted), create a dedicated contract model that explicitly includes that information — don't pollute the domain.

### Extra persistence fields at construction

When `from_domain()` needs storage-specific values that have no default, accept them as explicit parameters:

```python
@classmethod
def from_domain(cls, domain: Order, partition_key: str) -> "OrderRecord":
    return cls(partition_key=partition_key, **domain.model_dump())
```

---

## Dependency Rules

These rules ensure layers remain decoupled and changes don't cascade:

```
Layer 0 (Common)     →  depends on nothing
Layer 1 (Domain)     →  depends on Common only
Layer 2 (Contracts)  →  depends on Common and Domain
Layer 3 (Persistence)→  depends on Common and Domain

Contracts NEVER depend on Persistence.
Persistence NEVER depends on Contracts.
Services NEVER import another service's Persistence models.
Services MAY import another service's Domain models and Contracts via shared packages.
```

Visualized:

```
                  ┌─────────────┐
                  │   Common    │  ← no dependencies
                  └──────┬──────┘
                         │
                  ┌──────▼──────┐
                  │   Domain    │  ← depends on Common
                  └──┬───────┬──┘
                     │       │
          ┌──────────▼──┐ ┌──▼──────────┐
          │  Contracts  │ │ Persistence │  ← both depend on Common + Domain
          └─────────────┘ └─────────────┘
                 ✗ no dependency between Contracts and Persistence
```

If you find a contract importing a persistence model (or vice versa), the layering is broken. Fix it immediately.

---

## Composition via Mixins

Mixins are the mechanism for building domain language without duplication. Each mixin captures a single cross-cutting concern.

### Classifying mixins by layer

| Mixin | Composed at | Rationale |
|-------|-------------|-----------|
| `AuditMixin` (`created_at`, `updated_at`) | Domain | Temporal data is part of what the entity IS |
| `CreatedByMixin` (`created_by`, `updated_by`) | Domain | Actor tracking is a domain concept |
| `TenantMixin` (`organization_id`) | Domain | Multi-tenancy is a domain boundary |
| `SoftDeleteMixin` (`deleted_at`, `deleted_by`) | **Persistence** | Only the DB cares about logical deletion |
| Row versioning (`version`, `etag`) | **Persistence** | Optimistic concurrency is a storage concern |
| Partition/shard key (`partition_key`) | **Persistence** | Data distribution is a storage concern |

### Composition pattern

```python
# Domain model — compose only domain-relevant mixins
class Invoice(TenantMixin, AuditMixin, CreatedByMixin):
    """Multi-tenant, auditable invoice with actor tracking."""
    invoice_id: ...
    amount_cents: ...
    ...

# Contract model — inherits everything from domain
class InvoiceResponse(Invoice):
    """API response — inherits all domain fields."""
    organization_id: Annotated[str, Field(exclude=True)] = ""

# Persistence model — adds storage-specific concerns
class InvoiceRecord(Invoice):
    """Storage model — adds storage concerns to domain fields."""
    deleted_at: Annotated[datetime | None, Field(...)] = None
    version: Annotated[int, Field(...)] = 1
    ...
```

### MRO (Method Resolution Order)

When composing multiple mixins, put the most specific class first (leftmost):

```python
class MyEntity(TenantMixin, AuditMixin, CreatedByMixin):
    ...  # gets organization_id, created_at, updated_at, created_by, updated_by

class MyEntityRecord(SoftDeleteMixin, MyEntity):
    ...  # gets everything above + deleted_at, deleted_by
```

All mixin fields appear on the composed model with no duplication.

---

## Model-Owned Mapping

Models own their own conversion between layers. Mapping lives on the model, not in repositories or services. This ensures adding or removing a field requires **zero changes** to mapping code.

### The pattern

```python
class OrderRecord(Order):

    @classmethod
    def from_domain(cls, domain: Order) -> "OrderRecord":
        """Domain → Record. model_dump() spreads all domain fields."""
        return cls(**domain.model_dump())

    def to_domain(self) -> Order:
        """Record → Domain. Excludes storage-specific fields."""
        return Order(**self.model_dump(exclude={"deleted_at", "deleted_by", "partition_key"}))
```

### Why this works

- **No field-by-field mapping.** `model_dump()` spreads all domain fields automatically. Adding a new field to `Order` makes it flow through `from_domain()` and `to_domain()` with zero code changes.
- **Single place.** Mapping logic lives on the persistence model. Even if multiple repositories need conversion, they all call `OrderRecord.from_domain(domain)`.
- **Thin repositories.** The repository just calls model methods:

```python
class OrderRepository:
    async def save(self, order: Order) -> None:
        record = OrderRecord.from_domain(order)
        await self._session.merge(record)

    async def get_by_id(self, order_id: EntityId) -> Order:
        record = await self._session.get(OrderRecord, order_id)
        return record.to_domain()
```

### NEVER

- Write field-by-field mapping in repositories — every field change requires updating every mapper
- Scatter mapping logic across multiple adapters — centralize it on the model
- Use `__dict__` or manual attribute copying — use `model_dump()` for validated, type-safe conversion

---

## Shared vs Service-Local Placement

### The rule

If another service needs to import a domain model or contract — to call an API or consume an event — put it in a shared schemas package. If it's only used in-process inside a single service, keep it in the service.

### Decision criteria

| Question | If yes → | If no → |
|----------|----------|---------|
| Does another service request or consume this via API or event? | Shared schemas package | Service-local |
| Is this an API/event envelope or infrastructure contract? | Shared schemas package | — |
| Is this used only in-process within one service? | Service-local | — |
| Is this a storage concern? | **Always** service-local | — |

### Why shared?

When Service A returns an `OrderResponse` from its API and Service B calls that API, Service B needs the `OrderResponse` type to deserialize the response. If the type lives inside Service A's codebase, Service B would have to:

1. **Duplicate the model** — violating "declare once"
2. **Import from Service A's package** — creating deployment coupling

Neither is acceptable. A shared schemas package gives every service access through a common dependency.

### Structure

```
shared-schemas/
├── common/           ← Layer 0: primitives and mixins
├── domain/           ← Layer 1: cross-service domain models
│   ├── orders/
│   └── users/
├── contracts/        ← Layer 2: cross-service contracts
│   ├── api/
│   │   ├── orders/
│   │   └── users/
│   └── events/
│       ├── orders/
│       └── users/
└── persistence/      ← Layer 3: shared patterns (rare)

services/<name>/
├── models/
│   ├── domain/       ← Internal-only domain models
│   ├── contracts/    ← Internal-only contracts
│   └── persistence/  ← Always service-local
```

---

## Field Naming Conventions

Consistent naming is how ubiquitous language is enforced across layers.

| Convention | Pattern | Examples |
|------------|---------|----------|
| IDs | `<entity>_id` | `order_id`, `customer_id`, `organization_id` |
| Timestamps | `<action>_at` | `created_at`, `updated_at`, `sent_at`, `deleted_at` |
| Actors | `<action>_by` | `created_by`, `updated_by`, `deleted_by` |
| Domain terms | Use business language | `recipient_id` not `target_user_fk` |
| Casing | `snake_case` everywhere | All layers, all fields |
| Cross-layer | Same name in every layer | If domain says `channel`, API says `channel`, event says `channel`, DB column is `channel` |

---

## Anti-Patterns

### ❌ Redeclaring fields instead of inheriting

```python
# WRONG — duplicates every domain field
class OrderResponse(BaseModel):
    order_id: EntityId      # already on Order
    customer_id: EntityId   # already on Order
    status: OrderStatus     # already on Order
    total_cents: int        # already on Order
    created_at: datetime    # already on AuditMixin
```

```python
# RIGHT — inherit, get everything for free
class OrderResponse(Order):
    model_config = ConfigDict(frozen=True, extra="forbid")
```

### ❌ Explicit field-by-field mapping

```python
# WRONG — every new field requires updating this mapping
def to_domain(record: OrderRecord) -> Order:
    return Order(
        order_id=record.order_id,
        customer_id=record.customer_id,
        status=record.status,
        total_cents=record.total_cents,
        # forgot currency — silent bug
    )
```

```python
# RIGHT — model_dump() handles all fields automatically
def to_domain(self) -> Order:
    return Order(**self.model_dump(exclude={"deleted_at", "deleted_by"}))
```

### ❌ Storage concerns on domain models

```python
# WRONG — persistence concerns on domain model
class Order(TenantMixin, AuditMixin):
    deleted_at: datetime | None = None   # soft-delete is storage
    version: int = 1                     # row versioning is storage
    partition_key: str | None = None     # sharding is storage
    ...
```

```python
# RIGHT — storage concerns added only at persistence layer
class Order(TenantMixin, AuditMixin):
    ...  # only domain fields

class OrderRecord(Order):
    deleted_at: datetime | None = None
    version: int = 1
    partition_key: str | None = None
    ...
```

### ❌ Leaking storage concerns into contracts

```python
# WRONG — exposes storage internals to API consumers
class OrderResponse(BaseModel):
    row_version: int          # optimistic locking — storage concern
    partition_key: str        # sharding — storage concern
    deleted_at: datetime      # soft-delete — storage concern
    search_vector: str        # full-text index — storage concern
```

### ❌ Importing persistence across services

```python
# WRONG — breaks information hiding, creates deployment coupling
from order_service.models.persistence.order_record import OrderRecord
```

```python
# RIGHT — use shared contracts
from shared_schemas.contracts.api.orders import OrderResponse
```

### ❌ Skipping the domain layer

```python
# WRONG — persistence leaks directly to API
async def get_order(order_id: str):
    record = await db.get(OrderRecord, order_id)
    return record.__dict__  # persistence shape in API response
```

```python
# RIGHT — domain model is the intermediary
async def get_order(order_id: str):
    order = await repo.get_by_id(order_id)  # returns domain model
    return ApiResponse(data=order)           # contract inherits from domain
```

### ❌ Business logic in models

```python
# WRONG — models are data, not behavior
class Order(BaseModel):
    async def charge_customer(self): ...     # side effect
    def calculate_total(self): ...           # business logic
```

Logic belongs in flows (application layer) and domain services, not in data models.

---

## Decision Guide

Use this when deciding where to put a new model or field:

```
Is this a primitive type or cross-cutting concern
(ID, timestamp, tenant, audit)?
  └─ YES → Layer 0: common (mixin or value type)

Is this a core business concept with identity?
  └─ YES → Layer 1: domain (entity or aggregate)
  └─ Does it only have attributes, no identity?
       └─ YES → Layer 0: common/values (value object)

Does this define how we communicate to consumers (HTTP or event)?
  └─ YES → Layer 2: contracts
  └─ HTTP request/response? → contracts/api/<domain>/
  └─ Event payload?         → contracts/events/<domain>/

Does this define how we store data?
  └─ YES → Layer 3: persistence (always service-local)

Is this a storage concern (soft-delete, row version, partition key, denormalized fields, etc.)?
  └─ YES → Add only at persistence layer, never on domain
  └─ If a consumer needs it → create a dedicated contract model

Does another service consume this via API or event?
  └─ YES → shared schemas (domain + contracts)
  └─ NO  → service-local models (internal only)
```

---

## Quality Gates

Before completing data model design, verify:

- [ ] Every field is declared in exactly one place (no re-declarations across layers)
- [ ] Contract models inherit from domain models (no field duplication)
- [ ] Persistence models inherit from domain models with `from_domain()` / `to_domain()` using `model_dump()`
- [ ] Storage concerns (soft-delete, row versioning, partition keys, denormalized fields, etc.) live only on persistence models
- [ ] No contract imports any persistence model (and vice versa)
- [ ] No service imports another service's persistence models
- [ ] Cross-service domain models and contracts live in shared schemas
- [ ] All field names use domain terminology consistently across layers
- [ ] All models are frozen and immutable
- [ ] Mixins are single-purpose (one concern per mixin)
