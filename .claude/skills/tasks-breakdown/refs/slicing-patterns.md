# Slicing Patterns

> Extended guidance for identifying vertical slices and knowing when horizontal extraction is justified.

---

## The Vertical Slice Principle

A vertical slice cuts through **every architectural layer** needed to deliver one thin, user-facing (or system-facing) capability. After completing one vertical slice, the system can do something it couldn't do before — even if that something is narrow.

### Anatomy of a Vertical Slice

```
┌─────────────────────────────────────────────────────┐
│  UI          │  Component: CreateProductForm         │
├──────────────┼──────────────────────────────────────┤
│  API         │  POST /v1/products                   │
├──────────────┼──────────────────────────────────────┤
│  Logic       │  CreateProduct flow + Product entity  │
├──────────────┼──────────────────────────────────────┤
│  Data        │  products table + migration           │
├──────────────┼──────────────────────────────────────┤
│  Events      │  product.created event (if needed)    │
├──────────────┼──────────────────────────────────────┤
│  Observability│ create_product span + metrics        │
├──────────────┼──────────────────────────────────────┤
│  Tests       │  Unit + Integration + Contract        │
└──────────────┴──────────────────────────────────────┘
```

Each layer is thin — just enough to support the one capability. The product table might have 15 columns, but the first slice only needs the 5 required for creation. The API might eventually have 10 endpoints, but the first slice delivers one.

---

## Slicing Strategies

### Strategy 1: Slice by User-Facing Operation (CRUD)

The most common and safest strategy. Each CRUD operation is a separate slice.

```
Feature: Product Management
├── Slice 1: Create Product (POST + form + persist + event)
├── Slice 2: Read Product (GET + detail page + query)
├── Slice 3: List Products (GET /products + list page + pagination)
├── Slice 4: Update Product (PUT + edit form + validation)
└── Slice 5: Delete Product (DELETE + confirmation + soft delete)
```

**When to use:** Domain entities with clear lifecycle operations. Most features start here.

### Strategy 2: Slice by Business Rule Variant

When the same operation has meaningfully different behavior based on inputs or context.

```
Feature: Payment Processing
├── Slice 1: Pay with credit card (basic path)
├── Slice 2: Pay with stored payment method
├── Slice 3: Pay with split payments
└── Slice 4: Pay with promotional credit
```

**When to use:** Complex business logic where each variant has different validation, different side effects, or different error handling.

### Strategy 3: Slice by Integration Point

When a feature connects to multiple external systems and each connection is independently valuable.

```
Feature: Order Fulfillment
├── Slice 1: Accept order + persist (no integrations)
├── Slice 2: Notify warehouse via event
├── Slice 3: Send confirmation email
└── Slice 4: Update inventory service
```

**When to use:** Features with multiple downstream integrations. The first slice delivers the core capability; subsequent slices add integrations one at a time.

### Strategy 4: Slice by Domain Boundary

When a feature spans multiple bounded contexts.

```
Feature: Subscription Upgrade
├── Slice 1: Billing domain — upgrade plan + prorate charge
├── Slice 2: Access domain — update entitlements + permissions
├── Slice 3: Notification domain — send upgrade confirmation
└── Slice 4: Analytics domain — track upgrade event
```

**When to use:** Cross-domain features. Each domain boundary is a natural slice point. Anti-corruption layers live within each slice.

### Strategy 5: Slice by Data Complexity

When the data model is complex, start with a minimal model and enrich.

```
Feature: User Profile
├── Slice 1: Core fields (name, email, avatar) — full CRUD
├── Slice 2: Add preferences (notifications, timezone, language)
├── Slice 3: Add social connections (linked accounts, followers)
└── Slice 4: Add activity history (read-only feed)
```

**When to use:** Entities with many fields where different field groups serve different use cases.

---

## When Horizontal Extraction Is Justified

Horizontal slicing is generally wrong, but there are **three legitimate cases** where extracting a horizontal layer as its own task is correct:

### Case 1: Shared Infrastructure That Doesn't Exist Yet

If the feature requires infrastructure that no prior feature has established — database connection pooling, message broker setup, authentication middleware — and this infrastructure serves multiple vertical slices, extract it.

```
Task 0 (horizontal, justified): Set up PostgreSQL connection + migration framework
Task 1 (vertical): Create Product (uses DB from Task 0)
Task 2 (vertical): List Products (uses DB from Task 0)
```

**Rule:** The horizontal task must be a hard dependency of 2+ vertical slices AND the infrastructure doesn't exist in the codebase yet.

### Case 2: Shared Domain Types Referenced Across Slices

If multiple vertical slices reference the same domain types (entities, value objects, enums) and those types need to exist before any slice can begin.

```
Task 0 (horizontal, justified): Define Product aggregate + value objects + enums
Task 1 (vertical): Create Product (uses types from Task 0)
Task 2 (vertical): Search Products (uses types from Task 0)
```

**Rule:** Only extract if the types are genuinely shared. If only one slice uses a type, define it within that slice.

### Case 3: Migration or Schema Change With Blast Radius

If a database migration affects existing tables or data and needs careful review independent of the feature code.

```
Task 0 (horizontal, justified): Migration — add columns to orders table + backfill
Task 1 (vertical): Use new columns in order update flow
```

**Rule:** Only extract migrations that touch existing production data. New tables go inside their vertical slice.

---

## Splitting Heuristics

### "Too Big" Signals — Split Further

- Task description uses "and" more than twice ("create **and** validate **and** persist **and** notify")
- Definition of Done lists more than 8 files
- Estimated complexity exceeds L (2–3 sessions)
- Task touches more than 2 bounded contexts
- You can't describe the acceptance criteria in 2–3 sentences

### "Too Small" Signals — Combine

- Task creates a single model file with no behavior
- Task only adds a type alias or enum with no consumer
- Estimated complexity is trivially S (< 30 minutes)
- Task has no independent acceptance criteria — it only makes sense as part of a larger change

### The "Could You Demo It?" Test

After completing a vertical slice, could you demo something working? If yes, the slice is correctly sized. If the answer is "well, you can see the database has data but nothing visible happens" — the slice is too thin or too horizontal.

---

## Ordering Slices

### Start With the Walking Skeleton

The first 1–2 slices should establish the **walking skeleton** — a minimal end-to-end path through the system that proves the architecture works. Subsequent slices add capabilities onto the working foundation.

```
Slice 1 (skeleton): Create Product — simplest happy path through all layers
Slice 2 (flesh):    List Products — proves read path works
Slice 3 (flesh):    Update Product — proves mutation path works
Slice 4 (muscle):   Product Search — adds query complexity
Slice 5 (muscle):   Product Categories — adds relationships
```

### Risk-First Ordering

If there's a technically uncertain slice (new integration, unfamiliar technology, complex algorithm), schedule it early. Discovering that something is harder than expected is cheaper when there's time to adjust.

### Dependency-Respecting Order

Topologically sort: no task starts before its hard dependencies complete. Within a tier (tasks with no mutual dependencies), prioritize by risk, then by value.
