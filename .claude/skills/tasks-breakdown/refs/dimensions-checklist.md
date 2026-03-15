# Dimension Checklist

> Per-dimension questions to ask for each vertical slice, common artifacts, and frequently missed items.

---

## How to Use This Checklist

For **each vertical slice** (task), walk through every dimension below. For each dimension, ask the guiding questions. If the answer is "yes" to any question, that dimension needs a sub-task in the task breakdown. If the answer is "no" to all questions, consciously skip the dimension — but document that you considered it.

The goal is **completeness without bloat**: every relevant dimension is covered, nothing irrelevant is added.

---

## Dimension 1: Data

### Guiding Questions

- Does this slice introduce a new entity or aggregate?
- Does this slice add or modify columns/fields on an existing entity?
- Does this slice require a database migration?
- Does this slice need seed data or test fixtures?
- Does this slice change access patterns (new query, new index)?
- Does this slice introduce a new persistence model (separate from domain model)?

### Common Artifacts

| Artifact | Location |
|----------|----------|
| Migration file | `services/{svc}/{svc}/domains/{domain}/migrations/` or migration tool |
| Persistence model | `services/{svc}/{svc}/domains/{domain}/models/persistence/` |
| Domain entity/VO | `services/{svc}/{svc}/domains/{domain}/models/domain/` |
| Repository port | `services/{svc}/{svc}/domains/{domain}/ports/` |
| Repository adapter | `services/{svc}/{svc}/domains/{domain}/adapters/` |

### Frequently Missed

- **Index creation** — New queries without indexes cause production performance issues. Every new query pattern should have a corresponding index.
- **Backfill strategy** — Adding a non-nullable column to an existing table requires a backfill plan.
- **Persistence ↔ domain mapping** — The persistence model and domain model are separate. Don't forget the mapping layer.
- **ID generation** — New entities need UUIDv7/ULID generation, not auto-increment. Define ID strategy explicitly.
- **Soft delete** — If the entity can be deleted, plan for soft delete (timestamp + filtered queries), not hard delete.

---

## Dimension 2: Code / Domain Logic

### Guiding Questions

- Does this slice introduce new business rules or validation?
- Does this slice create a new flow (use case orchestration)?
- Does this slice add domain events (internal, within the aggregate)?
- Does this slice require new value objects or domain types?
- Does this slice modify existing domain logic?
- Does this slice need an anti-corruption layer for external data?

### Common Artifacts

| Artifact | Location |
|----------|----------|
| Entity / Aggregate | `domains/{domain}/models/domain/entities.py` or `aggregates.py` |
| Value Objects | `domains/{domain}/models/domain/value_objects.py` |
| Flow (use case) | `domains/{domain}/flows/{use_case}.py` |
| Domain exceptions | `domains/{domain}/exceptions.py` |
| Ports (abstractions) | `domains/{domain}/ports/` |

### Frequently Missed

- **Validation at domain boundary** — Business rules live in the domain, not in the API layer. Don't skip domain-level validation because "Pydantic handles it."
- **Error types** — Each domain failure mode should have a typed exception. Don't raise generic `ValueError`.
- **Idempotency** — If the operation can be retried, design for idempotent execution from the start.
- **Pure logic separation** — Keep the flow as an orchestrator. Domain decisions should be pure functions on entities/VOs, side effects through ports.

---

## Dimension 3: API

### Guiding Questions

- Does this slice add a new HTTP endpoint?
- Does this slice modify an existing endpoint's request/response shape?
- Does this slice need new Pydantic request/response models?
- Does this slice require authentication or authorization changes?
- Does this slice need rate limiting, pagination, or filtering?
- Was an OpenAPI spec written for this endpoint during design?

### Common Artifacts

| Artifact | Location |
|----------|----------|
| Route handler | `domains/{domain}/routes/v1/{resource}.py` |
| Request model | `domains/{domain}/models/contracts/api/requests.py` |
| Response model | `domains/{domain}/models/contracts/api/responses.py` |
| OpenAPI spec | `specs/openapi/v1.yaml` |

### Frequently Missed

- **Response envelope** — Use the shared response envelope from `schemas/contracts/api/`, not a custom shape.
- **Error responses** — Define error response models for 4xx/5xx cases, not just happy path.
- **Pagination** — List endpoints must paginate. Use the shared pagination contract.
- **Versioning** — New endpoints go under `/v1/`. If modifying existing endpoints, consider backward compatibility.
- **Dependency injection** — Wire service dependencies via `Depends()`, not direct instantiation.

---

## Dimension 4: Events

### Guiding Questions

- Does this slice produce an event that other services/domains consume?
- Does this slice consume an event from another service/domain?
- Does this slice need an AsyncAPI spec update?
- Does this slice require outbox pattern for reliable publishing?
- Does this slice need idempotent event handling?
- Does this slice introduce a new event schema?

### Common Artifacts

| Artifact | Location |
|----------|----------|
| Event handler | `domains/{domain}/handlers/v1/{event_handler}.py` |
| Event payload | `domains/{domain}/models/contracts/events/payload.py` |
| AsyncAPI spec | `specs/asyncapi/v1.yaml` |
| Event registration | `event_registry.py` |

### Frequently Missed

- **Idempotency key** — Every event consumer must handle duplicate delivery. Define the idempotency strategy.
- **Dead letter routing** — Failed events must route to a DLQ, not silently drop.
- **Schema versioning** — Event schemas need explicit versioning. New fields must be optional.
- **Correlation ID propagation** — Events must carry correlation/trace IDs for distributed tracing.
- **Outbox pattern** — If the event must be atomically consistent with a database write, use the transactional outbox.

---

## Dimension 5: Web / UI

### Guiding Questions

- Does this slice add a new page or route?
- Does this slice add or modify a component?
- Does this slice need new client-side state?
- Does this slice require data fetching (API integration)?
- Does this slice need form validation?
- Does this slice have accessibility requirements?

### Common Artifacts

| Artifact | Location |
|----------|----------|
| Page / Route | `web/src/app/{route}/page.tsx` |
| Component | `web/src/components/{domain}/{Component}.tsx` |
| API hook | `web/src/hooks/use{Resource}.ts` |
| Types | `web/src/types/{domain}.ts` |

### Frequently Missed

- **Loading and error states** — Every data-fetching component needs loading, error, and empty states.
- **Optimistic updates** — Mutations that affect the current view should update optimistically.
- **Accessibility** — ARIA labels, keyboard navigation, screen reader support. Not optional.
- **Responsive design** — Component must work across breakpoints.

---

## Dimension 6: Infrastructure

### Guiding Questions

- Does this slice need new cloud resources (queue, topic, bucket, database)?
- Does this slice need new environment variables or secrets?
- Does this slice require Kubernetes manifest changes?
- Does this slice need IAM/IRSA role updates?
- Does this slice require Pulumi stack changes?
- Does this slice modify Docker configuration?

### Common Artifacts

| Artifact | Location |
|----------|----------|
| Pulumi resource | `services/{svc}/deploy/cloud/` |
| Helm values | `services/{svc}/deploy/k8s/values.yaml` |
| Environment overlay | `services/{svc}/deploy/k8s/overlays/{env}.yaml` |
| Settings config | `services/{svc}/{svc}/settings.py` |

### Frequently Missed

- **Secrets management** — New secrets go through ExternalSecrets, not hardcoded env vars.
- **Per-environment config** — New config needs overlays for dev, staging, preprod, prod.
- **Resource limits** — New services or significant workload changes need updated CPU/memory limits.
- **Network policies** — New inter-service communication may need NetworkPolicy updates.

---

## Dimension 7: Verification

> **Note:** Observability (logs, traces, metrics) and tests (unit, integration, contract, E2E) are handled by the dedicated `/observe` and `/test` skills during the implementation loop. Do not include them as sub-tasks in the breakdown.

Instead, every task must include a **"How to Verify"** section with concrete, manual verification steps that confirm functional correctness.

### Guiding Questions

- What bash command can I run to verify the data layer works? (e.g., migration applied, row inserted)
- What curl/httpie call proves the API endpoint behaves correctly? (happy path + one error case)
- What can I do in the UI to confirm the feature works end-to-end?
- What DB query or CLI check confirms the domain logic produced the right output?
- What infrastructure command confirms resources are provisioned? (e.g., `kubectl get`, `aws s3 ls`)

### Verification by Dimension

| Dimension | Example verification |
|-----------|---------------------|
| **Data** | `psql -c "\\d products"` confirms table schema; `psql -c "SELECT count(*) FROM products"` confirms seed data |
| **Logic** | `python -c "from svc.domains.products.flows import create_product; ..."` — instantiate and call the flow |
| **API** | `curl -X POST localhost:8000/v1/products -d '{"name":"test"}' -H 'Content-Type: application/json'` — expect 201 |
| **Event** | Publish test event, check consumer logs for processing confirmation; verify DLQ is empty |
| **Web** | Open `localhost:3000/products` → click Create → fill form → submit → confirm toast + list update |
| **Infra** | `pulumi preview` shows no drift; `kubectl get pods -n ns` shows Running; `aws s3 ls s3://bucket` lists objects |

### Good Verification Characteristics

- **Runnable** — exact command, not "verify it works"
- **Observable** — describes what the expected output looks like
- **Quick** — under 2 minutes per task
- **Covers happy + error** — e.g., POST valid data (201) and POST missing field (422)

---

## Quick Reference: Dimension Matrix

Use this matrix as a fast scan. For each task, check or cross each dimension:

```
Task: ________________
  [  ] Data — migrations, models, repos, indexes
  [  ] Logic — entities, flows, validation, errors
  [  ] API — routes, request/response, auth, pagination
  [  ] Event — producers, consumers, schemas, idempotency
  [  ] Web — pages, components, state, accessibility
  [  ] Infra — cloud resources, config, secrets, k8s
  [  ] Verify — bash commands, curl calls, UI walkthrough with expected outputs
```
