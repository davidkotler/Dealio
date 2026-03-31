# SDLC Log: Event-Driven Price Check Pipeline

---

## [2026-03-27 00:00] — /discover-requirements — Discovery

- **Task:** N/A
- **Agents dispatched:** None (requirements handled directly)
- **Skills invoked:** discover-requirements
- **Artifacts produced:** prd.md
- **Outcome:** Requirements structured into 7 FRs and 10 NFRs with acceptance criteria. 5 open questions raised and resolved in the same session. Status: Approved.
- **Findings:** OQ-2 — scraper Lambda owns PriceCheckLog failure writes (has DB access); OQ-3 — conditional write idempotency (`current_price = old_price` guard); OQ-4 — any decrease; OQ-5 — single shared `services/pipeline/` package; OQ-1 — schedule interval deferred to product owner.

---

## [2026-03-27 00:01] — /design-system — High-Level Design

- **Task:** N/A
- **Agents dispatched:** Explore (codebase analysis)
- **Skills invoked:** design-system
- **Artifacts produced:** hld.md
- **Outcome:** Full HLD produced. Architecture style: event-driven pipeline on AWS serverless. 4 bounded contexts (monitor, scraper, db-update, email) in a single `services/pipeline/` package. Key decisions: EventBridge custom bus for fan-out, SNS → 2× SQS for downstream decoupling, conditional write for idempotency.
- **Findings:** `tracked_products` schema is missing a `status` column — a new Alembic migration is required before pipeline can be deployed. ORM models are currently duplicated across webapp, monitor_lambda, and the planned pipeline package; consolidation deferred to implementation. DB connection exhaustion risk at 5,000 concurrent scraper invocations — PgBouncer/RDS Proxy recommended before production scale.

---

## [2026-03-31] — /design-lld — Low-Level Design

- **Task:** 003-event-driven-price-check-pipeline
- **Agents dispatched:** python-architect (wave 1), data-architect (wave 1), event-architect (wave 2), pulumi-architect (wave 3) — all outputs written inline due to agent file-write permission constraints
- **Skills invoked:** design-code, design-data, design-event, design-pulumi
- **Artifacts produced:** `lld.md` (consolidated from lld-code.md, lld-data.md, lld-event.md, lld-pulumi.md)
- **Outcome:** Full LLD produced and consolidated. All 4 bounded contexts designed end-to-end: domain models, ports, flows, adapters, handlers, ORM models, event contracts, Pulumi infrastructure (34 resources, 6 ADRs). Two design inconsistencies identified and resolved in §5 of lld.md: (1) `correlation_id` generation location — resolved to generate in `fan_out_flow`, pass to adapter; (2) Pydantic `extra` config — resolved to `extra="ignore"` on all contract models before first production deployment.
- **Findings:** Schema discrepancy: `prd.md` FR-1 references `status = active` filter but `tracked_products` has no `status` column — confirmed with HLD, all rows are fetched at MVP, product owner confirmation required before adding column. ORM duplication now spans 3 packages (webapp, monitor_lambda, pipeline) — extract to `libs/lib-schemas/` when a 4th consumer appears. ADR-006 (Lambda zip vs Docker image) deferred — compatible with either approach.

---

## [2026-03-31] — /tasks-breakdown — Task Decomposition

- **Task:** 003-event-driven-price-check-pipeline
- **Artifacts produced:** `tasks-breakdown.md` + 6 per-task detail files (`tasks/001-foundation.md` through `tasks/006-pulumi-infrastructure.md`)
- **Outcome:** Feature decomposed into 6 vertical slices across 2 tiers. Critical path: T-1 (Foundation) → T-6 (Pulumi). Tier 1: T-1 alone (M). Tier 2: T-2 through T-6 in parallel (4M + 1S + 1L). Each task file is self-contained with verbatim acceptance criteria, domain model/port/flow/adapter/handler design references, SQL statements, verification commands, expected behaviors, boundary conditions, and invariants.
- **Findings:** `correlation_id` generation location and Pydantic `extra` config resolutions from LLD §5 are reflected in T-2 and T-3 task files respectively. Scraper domain copy maintenance risk (manual mirror of monitor_lambda changes) documented in T-1 and tasks-breakdown.md risk notes. ORM duplication accepted as technical debt — extraction to `libs/lib-schemas/` deferred to when a 4th consumer appears.

---

## [2026-03-31 00:00] — /implement — Implementation

- **Task:** T-2 — Monitor Lambda — Fan-out flow + EventBridge adapter + handler
- **Agents dispatched:** python-implementer (general-purpose)
- **Skills invoked:** implement-python, implement-pydantic, implement-event, implement-data
- **Artifacts produced:** `pipeline/domains/monitor/models/domain/product_fan_out_payload.py`, `pipeline/domains/monitor/models/contracts/events/product_price_check_requested.py`, `pipeline/domains/monitor/ports/tracked_product_read_port.py`, `pipeline/domains/monitor/ports/eventbridge_publish_port.py`, `pipeline/domains/monitor/flows/fan_out_flow.py`, `pipeline/domains/monitor/adapters/sqlalchemy_tracked_product_read_adapter.py`, `pipeline/domains/monitor/adapters/eventbridge_publish_adapter.py`, `pipeline/domains/monitor/exceptions.py`, `pipeline/domains/monitor/jobs/handler.py` (replaced stub), plus all `__init__.py` stubs
- **Outcome:** Task T-2 implemented and marked complete. Handler returns `{"status": "ok"}`; `fan_out_flow` generates one `correlation_id` per cycle; `EventBridgePublishAdapter` chunks into 10s with `asyncio.gather` + `asyncio.to_thread`; `user_email` never logged. Both smoke-import and payload shape verifications pass.
- **Findings:** None — implementation matched design spec exactly with no deviations.