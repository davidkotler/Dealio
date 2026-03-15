---
name: review-data-model
version: 1.0.0

description: |
  Review Pydantic data models for layered architecture compliance, field duplication, mixin composition,
  storage concern separation, and domain-driven design alignment.
  Use when reviewing Pydantic models, domain entities, API contracts, event payloads, persistence records,
  or any data model code that crosses layer boundaries. Also use when validating model inheritance chains,
  checking for field re-declarations, verifying mixin placement, or assessing model-owned mapping patterns.
  Relevant for Python Pydantic codebases with layered data architecture (Common/Domain/Contracts/Persistence).

chains:
  invoked-by:
    - skill: implement/pydantic
      context: "Post-implementation model quality gate"
    - skill: implement/data
      context: "Data model validation"
    - skill: design/data
      context: "Design artifact model review"
  invokes:
    - skill: implement/pydantic
      when: "Critical findings require model rewrite"
    - skill: review/coherence
      when: "Naming inconsistencies across layers"
---

# Data Model Architecture Review

> Validate that data models follow layered architecture — declare once, inherit everywhere, map automatically.

## Quick Reference

| Aspect | Details |
|--------|---------|
| **Scope** | Pydantic models: domain entities, API contracts, event payloads, persistence records, mixins |
| **Invoked By** | `implement/pydantic`, `implement/data`, `design/data`, `/review` command |
| **Invokes** | `implement/pydantic` (failure) |
| **Verdicts** | `PASS` . `PASS_WITH_SUGGESTIONS` . `NEEDS_WORK` . `FAIL` |

---

## Review Objective

Ensure data models enforce the four-layer architecture (Common -> Domain -> Contracts -> Persistence) with zero field duplication, proper inheritance, correct mixin placement, and clean layer separation.

### This Review Answers

1. Are fields declared exactly once and reused via inheritance across all layers?
2. Do contracts and persistence models inherit from domain models (not redeclare fields)?
3. Are storage concerns (soft-delete, row versioning, partition keys) restricted to persistence only?
4. Does model-owned mapping use `model_dump()` instead of field-by-field copying?
5. Are cross-service models in shared schemas and persistence models service-local?

### Out of Scope

- Query safety and SQL correctness (see `review/data`)
- Repository pattern compliance (see `review/data`)
- API endpoint implementation (see `review/api`)
- General design quality (see `review/design`)

---

## Core Workflow

```
1. SCOPE    ->  Locate model files (**/models/**/*.py, **/*_model*.py, **/*_schema*.py)
2. CONTEXT  ->  Load data-model.md ref, data-architecture.md, principles.md
3. MAP      ->  Classify each model into layer: Common | Domain | Contract | Persistence
4. ANALYZE  ->  Apply criteria by category
5. CLASSIFY ->  Assign severity per finding
6. VERDICT  ->  Determine pass/fail from severity distribution
7. CHAIN    ->  Route to rewrite or next review
```

### Severity Levels

| Severity | Definition | Action |
|----------|------------|--------|
| **BLOCKER** | Architecture violation, field duplication across layers, broken inheritance | Must fix |
| **CRITICAL** | Storage concern on domain model, cross-service persistence import, broken mapping | Must fix |
| **MAJOR** | Missing model-owned mapping, mixin at wrong layer, mutable model | Should fix |
| **MINOR** | Naming inconsistency, missing `extra="forbid"`, style issue | Consider |

---

## Evaluation Criteria

### Layer Compliance (LC)

The four-layer architecture creates clean separation. Each model must belong to exactly one layer, and dependencies must flow downward (Common <- Domain <- Contracts/Persistence).

| ID | Criterion | Severity |
|----|-----------|----------|
| LC.1 | Each model classifiable to exactly one layer (Common/Domain/Contract/Persistence) | BLOCKER |
| LC.2 | No contract imports any persistence model (or vice versa) | BLOCKER |
| LC.3 | No service imports another service's persistence models | BLOCKER |
| LC.4 | Domain models depend only on Common layer | CRITICAL |
| LC.5 | Cross-service domain models and contracts placed in shared schemas package | MAJOR |
| LC.6 | Persistence models always service-local | MAJOR |

### Field Declaration (FD)

Every field should be declared exactly once. Duplication means two places to update when a field changes — and one will inevitably be missed.

| ID | Criterion | Severity |
|----|-----------|----------|
| FD.1 | No field redeclared across layers (same name + type in parent and child) | BLOCKER |
| FD.2 | Contract models inherit from domain models (not standalone BaseModel) | CRITICAL |
| FD.3 | Persistence models inherit from domain models (not standalone BaseModel) | CRITICAL |
| FD.4 | Domain fields ("hard" fields) present only via inheritance in contracts/persistence | MAJOR |
| FD.5 | Ubiquitous language: same field name across all layers for same concept | MAJOR |

### Mixin Composition (MC)

Mixins are the mechanism for declaring cross-cutting concerns once. Each mixin must be single-purpose and composed at the correct layer.

| ID | Criterion | Severity |
|----|-----------|----------|
| MC.1 | Storage concerns (soft-delete, row versioning, partition keys) not on domain models | CRITICAL |
| MC.2 | Domain-relevant mixins (Audit, Tenant, CreatedBy) composed at domain layer | MAJOR |
| MC.3 | Each mixin is single-purpose (one cross-cutting concern) | MAJOR |
| MC.4 | Mixins are frozen, immutable BaseModel subclasses | MINOR |
| MC.5 | No "kitchen sink" mixins combining unrelated concerns | MAJOR |

### Model Quality (MQ)

Pydantic models should be immutable, validated, and framework-agnostic at the domain layer.

| ID | Criterion | Severity |
|----|-----------|----------|
| MQ.1 | All models use `frozen=True` | MAJOR |
| MQ.2 | All models use `extra="forbid"` | MINOR |
| MQ.3 | Domain models are framework-agnostic (no ORM decorators, no API-specific fields) | CRITICAL |
| MQ.4 | Annotated fields with explicit validation and constraints | MINOR |
| MQ.5 | No business logic or side effects in model classes | MAJOR |
| MQ.6 | Typed domain identifiers (NewType or prefixed IDs) | MINOR |

### Mapping Pattern (MP)

Models own their own conversion between layers. Mapping uses `model_dump()` for zero-maintenance field propagation.

| ID | Criterion | Severity |
|----|-----------|----------|
| MP.1 | No field-by-field mapping in repositories or services | CRITICAL |
| MP.2 | Persistence models provide `from_domain()` / `to_domain()` using `model_dump()` | MAJOR |
| MP.3 | `to_domain()` excludes storage-specific fields via `exclude=` set | MAJOR |
| MP.4 | `from_domain()` accepts extra persistence-only values as explicit parameters | MINOR |
| MP.5 | Contract models use `Field(exclude=True)` to hide internal fields from serialization | MAJOR |

### Contract Design (CD)

Contracts define how the domain is communicated to consumers. They inherit domain fields and add only communication-specific concerns.

| ID | Criterion | Severity |
|----|-----------|----------|
| CD.1 | API response models inherit from domain models (all domain fields come for free) | CRITICAL |
| CD.2 | Internal fields hidden via `Field(exclude=True)` not field deletion | MAJOR |
| CD.3 | Event payloads use same field names as domain (ubiquitous language) | MAJOR |
| CD.4 | No persistence details in contracts (table names, column aliases, DB types) | CRITICAL |
| CD.5 | Summary/projection models for list endpoints are documented as intentional standalone | MINOR |

---

## Verdict Logic

```
Any BLOCKER?           -> FAIL (architecture violation, must redesign)
Any CRITICAL?          -> NEEDS_WORK (targeted fixes required)
Multiple (>=3) MAJOR?  -> NEEDS_WORK (quality debt)
Few MAJOR/MINOR?       -> PASS_WITH_SUGGESTIONS
MINOR/SUGGESTION only? -> PASS
```

---

## Patterns

### Layer Classification Quick-Check

When reviewing a model, classify it by asking:

```
Is this reusable across many models? (ID type, audit timestamps, tenant)
  -> Layer 0: Common (mixin or value type)

Is this the single source of truth for a business concept?
  -> Layer 1: Domain (entity or aggregate)

Does this define how we communicate to consumers (HTTP or event)?
  -> Layer 2: Contract (API response, event payload)

Does this define how we store data?
  -> Layer 3: Persistence (always service-local)
```

### Good: Proper Inheritance Chain

```python
# Layer 0 — Common
class AuditMixin(BaseModel):
    model_config = ConfigDict(frozen=True)
    created_at: Annotated[datetime, Field(...)]
    updated_at: Annotated[datetime | None, Field(...)] = None

# Layer 1 — Domain (composes from Common)
class Order(TenantMixin, AuditMixin):
    model_config = ConfigDict(frozen=True, extra="forbid")
    order_id: Annotated[EntityId, Field(...)]
    status: Annotated[OrderStatus, Field(...)]

# Layer 2 — Contract (inherits from Domain)
class OrderResponse(Order):
    model_config = ConfigDict(frozen=True, extra="forbid")
    organization_id: Annotated[str, Field(exclude=True)] = ""

# Layer 3 — Persistence (inherits from Domain, adds storage concerns)
class OrderRecord(Order):
    model_config = ConfigDict(frozen=True, extra="forbid")
    deleted_at: Annotated[datetime | None, Field(...)] = None
    partition_key: Annotated[str | None, Field(...)] = None

    @classmethod
    def from_domain(cls, domain: Order) -> "OrderRecord":
        return cls(**domain.model_dump())

    def to_domain(self) -> Order:
        return Order(**self.model_dump(exclude={"deleted_at", "partition_key"}))
```

### Bad: Multiple Violations

```python
# FD.1: Redeclares fields instead of inheriting
class OrderResponse(BaseModel):
    order_id: str          # already on Order
    status: str            # already on Order
    created_at: datetime   # already on AuditMixin

# MC.1: Storage concern on domain model
class Order(TenantMixin, AuditMixin, SoftDeleteMixin):
    ...  # deleted_at doesn't belong on domain

# MP.1: Field-by-field mapping instead of model_dump()
def to_domain(record):
    return Order(
        order_id=record.order_id,
        status=record.status,
        # forgot currency — silent bug
    )

# LC.3: Importing persistence across services
from order_service.models.persistence import OrderRecord
```

---

## Finding Format

```markdown
### [CRITICAL] Field Duplication in Contract Model

**Location:** `models/contracts/api/orders.py:15`
**Criterion:** FD.1 - No field redeclared across layers

**Issue:** OrderResponse redeclares `order_id`, `status`, `total_cents` that
already exist on the domain model Order.

**Evidence:**
\`\`\`python
class OrderResponse(BaseModel):  # Should inherit from Order
    order_id: EntityId      # duplicated from Order
    status: OrderStatus     # duplicated from Order
    total_cents: int        # duplicated from Order
\`\`\`

**Suggestion:** Change to `class OrderResponse(Order)` — all domain fields
come for free via inheritance.

**Rationale:** Duplicated fields create two maintenance points. When a field
changes on the domain model, the contract silently drifts.
```

---

## Summary Format

```markdown
# Data Model Architecture Review

## Verdict: {{EMOJI}} {{VERDICT}}

| Metric | Count |
|--------|-------|
| Models Reviewed | {{N}} |
| Blockers | {{N}} |
| Critical | {{N}} |
| Major | {{N}} |
| Minor | {{N}} |

| Model | Layer | Inherits From | Status |
|-------|-------|---------------|--------|
| Order | Domain | TenantMixin, AuditMixin | OK |
| OrderResponse | Contract | Order | OK |
| OrderRecord | Persistence | Order | OK |
| InvoiceResponse | Contract | BaseModel | FD.2 - should inherit Invoice |

## Duplicate Fields Detected
| Field | Declared In | Also In | Finding |
|-------|------------|---------|---------|
| order_id | Order | OrderResponse | FD.1 |

## Key Findings
1. {{Finding 1}}
2. {{Finding 2}}
3. {{Finding 3}}

## Chain Decision
**Target:** `{{skill}}` | **Reason:** {{rationale}}
```

---

## Skill Chaining

| Verdict | Action | Target |
|---------|--------|--------|
| `FAIL` | Mandatory rewrite | `implement/pydantic` |
| `NEEDS_WORK` | Targeted fixes | `implement/pydantic` |
| `PASS_WITH_SUGGESTIONS` | Optional improvements | None -> continue |
| `PASS` | Continue pipeline | `review/coherence` or `review/data` |

**Handoff to implement/pydantic:**
```
Priority: {{BLOCKER/CRITICAL IDs}}
Constraint: Preserve domain field names (ubiquitous language)
Focus: {{failed criterion categories}}
Reference: design-code/refs/data-model.md
```

**Re-review:** Max 3 iterations on modified models before escalation.

---

## Deep References

| Reference | When to Load |
|-----------|--------------|
| `skills/design-code/refs/data-model.md` | Full layered architecture guide |
| `rules/principles.md` | Engineering principles validation |
| `skills/design-code/refs/domain-driven-design.md` | Entity/VO/Aggregate classification |

---

## Quality Gates

Before completing review:

- [ ] Every model classified into exactly one layer
- [ ] Inheritance chains traced (model -> parent -> mixins)
- [ ] Field duplication check across all layers for each concept
- [ ] Storage concerns verified absent from domain models
- [ ] Mapping patterns checked (model_dump, not field-by-field)
- [ ] Cross-service model placement verified (shared vs service-local)
- [ ] Each finding has location + criterion + severity
- [ ] Verdict aligns with severity distribution
- [ ] Chain decision explicit with handoff context
