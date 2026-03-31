# Requirements: Event-Driven Price Check Pipeline

**Date:** 2026-03-27
**Status:** Approved
**Author:** Claude Code (discover-requirements)
**Stakeholders:** Product Owner, Backend Developer

---

## 1. Overview

Replace the monolithic monitor Lambda — which currently fetches products, scrapes prices, persists results, and sends
emails in a single execution — with a four-stage event-driven pipeline. The monitor Lambda fans out one EventBridge
event per active product; a dedicated scraper Lambda handles each product in isolation; on a price drop it publishes
to an SNS topic that fans out to an SQS-backed DB-update Lambda and an SQS-backed email Lambda. Every stage is
independently deployable, scalable, and observable via a shared `correlation_id`.

---

## 2. Functional Requirements

### FR-1: Scheduled Fan-Out (Monitor Lambda)

**As a** system operator, **I want** a scheduled Lambda to fan out one event per active tracked product, **so that**
each product is checked independently without coupling scrape latency or failures together.

**Acceptance Criteria:**
- **Given** an EventBridge scheduled rule fires, **when** the monitor Lambda runs, **then** it queries the database
  for all tracked products where `status = active`.
- **Given** the active product list is fetched, **when** publishing to EventBridge, **then** exactly one event is
  published per product, carrying: `tracked_product_id`, `url`, `current_price` (Decimal, serialised as string),
  `user_id`, `user_email`, `product_name`, and `correlation_id` (UUID generated once per fan-out cycle).
- **Given** there are zero active products, **when** the monitor Lambda runs, **then** it logs
  `fan_out.no_products` and exits successfully without publishing any events.
- **Given** the monitor Lambda runs, **when** it executes, **then** it performs **no scraping** — its only
  responsibilities are DB read and EventBridge publish.
- **Given** the schedule is configurable, **when** the EventBridge rule is deployed, **then** the schedule
  expression is an environment parameter (not hardcoded) — the concrete interval is resolved in Q1 (see OQ-1).

---

### FR-2: Isolated Per-Product Scraping (Scraper Lambda)

**As a** system, **I want** each product to be scraped by its own Lambda invocation, **so that** a slow or failing
scrape cannot block or delay any other product.

**Acceptance Criteria:**
- **Given** the scraper Lambda receives an EventBridge event for a product, **when** it executes, **then** it
  runs the existing scrape flow (`fetch_page → classify_response → preprocess_html → LLM extraction → fallback`).
- **Given** a scrape completes and the returned price is strictly less than `current_price` in the event payload,
  **when** the scraper Lambda evaluates the result, **then** it publishes a price-drop message to the SNS topic.
- **Given** a scrape completes and the returned price is greater than or equal to `current_price`, **when**
  the scraper Lambda evaluates the result, **then** it logs `scrape.no_price_drop` and exits successfully —
  no SNS publish, no DB write.
- **Given** all sub-operations (fetch, classify, extract) fail for a product, **when** the scraper Lambda
  handles the failure, **then** it writes a `PriceCheckLog` failure record to the database (with
  `tracked_product_id`, `error_type`, `checked_at`) and terminates — no SNS publish, price unchanged.
- **Given** the scraper Lambda runs, **when** it executes, **then** it propagates the `correlation_id` from
  the incoming event payload into all log entries, the outbound SNS message, and any DB writes.

---

### FR-3: Price-Drop SNS Fan-Out

**As a** system, **I want** a price-drop detection to fan out to independent downstream consumers via SNS→SQS,
**so that** DB persistence and email delivery are decoupled and each can fail and retry independently.

**Acceptance Criteria:**
- **Given** a price drop is detected, **when** the scraper Lambda publishes to SNS, **then** the SNS message
  carries: `tracked_product_id`, `user_id`, `user_email`, `product_name`, `product_url`, `old_price`,
  `new_price`, `correlation_id`.
- **Given** the SNS topic is configured, **when** a message is published, **then** it is delivered to exactly
  two SQS queues: one for the DB-update Lambda and one for the email Lambda.
- **Given** a downstream SQS queue has a DLQ attached, **when** a Lambda consumer exhausts retries, **then**
  the message lands in the DLQ and is not silently dropped (retry count and DLQ configuration are environment
  parameters).

---

### FR-4: DB-Update Lambda

**As a** system, **I want** a dedicated Lambda to persist price-drop results to the database, **so that** DB
failures do not affect email delivery and vice versa.

**Acceptance Criteria:**
- **Given** the DB-update Lambda receives an SQS message for a price drop, **when** it processes it, **then**
  it performs all three writes atomically in a single database transaction:
  1. `tracked_products.current_price ← new_price`, `previous_price ← old_price`,
     `last_checked_at ← now(UTC)`.
  2. A new `Notification` record for the user.
  3. A `PriceCheckLog` record with `result = success`.
- **Given** the DB-update Lambda processes a message successfully, **when** it completes, **then** it deletes
  the SQS message (standard SQS visibility / ack behaviour).
- **Given** the DB-update Lambda throws an unhandled exception, **when** the SQS visibility timeout expires,
  **then** the message is retried up to the configured maximum before being sent to the DLQ.
- **Given** a scrape failure occurs, **when** it is handled by the scraper Lambda, **then** the scraper Lambda
  writes the `PriceCheckLog` failure record directly — the DB-update Lambda is not involved in failure recording.

---

### FR-5: Email Lambda

**As a** user, **I want** a price-drop email to arrive via SES when a tracked product's price falls, **so that**
I am notified without needing to check the dashboard.

**Acceptance Criteria:**
- **Given** the email Lambda receives an SQS message for a price drop, **when** it processes it, **then** it
  sends a price-drop alert email via SES to `user_email` with `product_name`, `product_url`, `old_price`,
  `new_price`.
- **Given** SES rejects the send (e.g. bounce, throttle), **when** the Lambda raises an exception, **then**
  SQS retries delivery up to the configured maximum; the message lands in the DLQ on final failure.
- **Given** the email Lambda processes a message, **when** it logs, **then** it includes `correlation_id`,
  `user_id` (hashed or masked — no PII in log values), `tracked_product_id`.

---

### FR-6: End-to-End Correlation

**As a** developer/operator, **I want** a single `correlation_id` to appear in every log entry and event payload
from fan-out through email, **so that** the full journey of any product check is traceable end-to-end.

**Acceptance Criteria:**
- **Given** the monitor Lambda starts a fan-out cycle, **when** it generates a `correlation_id`, **then** it is
  a UUID v4, created once per cycle and included in every EventBridge event published in that cycle.
- **Given** any Lambda stage emits a structured log, **when** it logs, **then** the `correlation_id` field is
  present in every log entry for that invocation.
- **Given** the scraper Lambda publishes to SNS, **when** the SNS message is formed, **then** the
  `correlation_id` from the incoming EventBridge event is forwarded unchanged.
- **Given** the DB-update or email Lambda processes an SQS message, **when** it logs, **then** the
  `correlation_id` from the SQS message body is present in all log entries.

---

### FR-7: Infrastructure as Code

**As a** developer, **I want** all AWS resources (EventBridge rule, Lambda functions, SNS topic, SQS queues, DLQs,
IAM roles) defined in Pulumi, **so that** the pipeline is reproducible and environment-promotable.

**Acceptance Criteria:**
- **Given** a Pulumi stack is deployed, **when** it completes, **then** all four Lambda functions, the
  EventBridge rule, the SNS topic, both SQS queues, and both DLQs exist with correct IAM permissions.
- **Given** environment-specific parameters (schedule expression, Lambda memory/timeout, SQS visibility timeout,
  DLQ max-receive-count, LLM provider/model, SES from-address), **when** the stack is configured, **then**
  each parameter is injected via Pulumi config — no hardcoded values.

---

## 3. Non-Functional Requirements

### NFR-1: Performance — Fan-Out Latency

- **Target:** Monitor Lambda completes fan-out (DB query + all EventBridge publishes) within **30 seconds** for
  up to 5,000 active tracked products (5 URLs × 1,000 users).
- **Rationale:** Fan-out is the critical path gate; slow fan-out delays the entire cycle.
- **Validation:** Load test with synthetic product records; measure p95 fan-out duration in CloudWatch.

### NFR-2: Performance — Per-Product Scrape Timeout

- **Target:** Each scraper Lambda invocation has a hard timeout of **60 seconds** (configurable via environment).
- **Rationale:** LLM extraction can be slow; a timeout cap prevents indefinite Lambda billing and backlog
  accumulation.
- **Validation:** Verify Lambda function timeout setting in Pulumi stack; integration test with a mock that
  delays 61 s confirms timeout fires.

### NFR-3: Availability — Scrape Failure Isolation

- **Target:** A failure rate of up to **50%** of product scrapes in a single cycle must not prevent the
  remaining products from completing their full pipeline journey (DB update + email).
- **Rationale:** Scrape failures are expected (bot detection, timeouts, LLM errors); they must not cascade.
- **Validation:** Unit tests on scraper Lambda confirm silent termination on `ScraperFailure`; no SNS publish
  observable.

### NFR-4: Availability — Downstream Consumer Independence

- **Target:** A complete outage of the email Lambda (DLQ full, all retries exhausted) must not affect the
  DB-update Lambda — price persistence and notification records continue to be written.
- **Rationale:** Email is lower-priority than data persistence; failure isolation is a primary design goal.
- **Validation:** Integration test: email Lambda SQS queue is made unavailable; DB-update Lambda continues
  processing its queue independently.

### NFR-5: Observability — Structured Logs

- **Target:** 100% of log entries across all four Lambda stages are structured (JSON), carry `correlation_id`
  and `tracked_product_id`, and use `snake_case` dot-namespaced event keys (e.g. `scraper.price_drop_detected`).
- **Rationale:** Traceability requirement from README; aligns with existing structlog patterns in codebase.
- **Validation:** CloudWatch Logs Insights query: `filter correlation_id != null` returns all log entries for a
  given cycle.

### NFR-6: Observability — Alerting on High Failure Rate

- **Target:** A CloudWatch alarm fires when the scrape failure rate across a single fan-out cycle exceeds
  **20%** (configurable threshold).
- **Rationale:** Mirrors the existing `_FAILURE_RATE_THRESHOLD` logic in `price_check_cycle_flow.py`; moves
  it to infrastructure so it doesn't require Lambda to aggregate results.
- **Validation:** Alarm definition in Pulumi; tested via synthetic metric injection.

### NFR-7: Scalability — Concurrency Model

- **Target:** The pipeline must handle up to **5,000 concurrent scraper Lambda invocations** (1,000 users × 5
  products) within a single fan-out cycle without architectural change.
- **Rationale:** "Flexible concurrency" goal from README — Lambda reserved concurrency and SQS batch size are
  config, not code.
- **Validation:** Reserved concurrency limit set via Pulumi config; SQS batch size is environment parameter.

### NFR-8: Security — Least Privilege IAM

- **Target:** Each Lambda function's IAM execution role grants only the permissions it requires:
  - Monitor Lambda: `rds-data:*` / DB read, `events:PutEvents`.
  - Scraper Lambda: `events:PutEvents` (input) is IAM-managed by EventBridge; `sns:Publish` to its one topic.
  - DB-update Lambda: `sqs:ReceiveMessage`, `sqs:DeleteMessage`; DB write.
  - Email Lambda: `sqs:ReceiveMessage`, `sqs:DeleteMessage`; `ses:SendEmail`.
- **Rationale:** Principle of least privilege per engineering principles §1.11.
- **Validation:** IAM policy simulator validates no cross-role permission bleed; reviewed in Pulumi code review.

### NFR-9: Security — No PII in Log Values

- **Target:** `user_email` must never appear as a raw value in any structured log field. Use `user_id`
  (UUID) as the identity key; hash or omit email.
- **Rationale:** Engineering principles §1.11: never log PII.
- **Validation:** Log search across all Lambda stages in staging: `filter @message like /user_email/` returns
  zero results.

### NFR-10: Idempotency — DB-Update Lambda

- **Target:** Replaying the same SQS message must not create duplicate `Notification` records or corrupt
  `current_price`. Strategy: **conditional write** — the DB-update Lambda only applies the price update if
  `tracked_products.current_price = old_price` (the value from the message). A duplicate message where
  `current_price` has already been updated to `new_price` becomes a no-op and is acknowledged.
- **Rationale:** SQS at-least-once delivery guarantees duplicate messages; engineering principles §3.4.
  Conditional write requires no deduplication table and adds no extra state — `old_price` is already in the
  message payload.
- **Caveat:** If the same product drops to the same price in two successive cycles, the second message's
  `old_price` will equal the already-stored `current_price`, so the write proceeds normally. Only an exact
  replay (same `old_price` and `new_price`) is a no-op.
- **Validation:** Integration test: same message delivered twice; assert exactly one `Notification` record,
  one `PriceCheckLog` record, and `current_price = new_price` in the DB.

---

## 4. Constraints

### Technical Constraints

- **Existing scraper domain must not be rewritten.** The scraper Lambda re-uses the existing
  `fetch_page → classify_response → preprocess_html → LLM extraction → fallback` flow from
  `monitor_lambda/domains/scraper/`. Scraping logic is out of scope (per README non-goals).
- **Python 3.13 / uv workspace, shared package.** All four Lambda handlers live in a single new
  `services/pipeline/` package added to the uv workspace. Each Lambda stage is a sub-module within that
  package; they share domain code, ORM models, and infrastructure utilities without duplication.
- **PostgreSQL via async SQLAlchemy (asyncpg).** No new database technology; DB-update Lambda uses the
  existing ORM models and alembic schema.
- **SES for email.** Email Lambda sends via the existing `SESEmailSender` adapter or an equivalent
  using the same SES API.
- **AWS-only infrastructure.** EventBridge, SNS, SQS, Lambda — no third-party messaging services.
- **Pulumi for IaC.** Infrastructure definition follows the existing Pulumi patterns in this repository.
- **No API/frontend changes.** Webapp and React frontend are not modified (per README non-goals).

### Business Constraints

- **Per-user product limit: 5 URLs.** Maximum active tracked products per user at launch; no architectural
  enforcement required (existing DB constraint or application-layer check in webapp handles this).
- **No per-user email rate limiting at launch.** Architecture must accommodate it at the email Lambda's SQS
  queue, but implementation is deferred (per README non-goals).
- **Schedule interval TBD.** The EventBridge schedule expression is an environment parameter; the concrete
  value will be decided by the product owner before the first production deployment.

### Organizational Constraints

- **Single developer team.** No cross-team coordination required; all four Lambda services are owned by the
  same team.

---

## 5. Dependencies

| Dependency | Type | Direction | Impact if Unavailable |
|---|---|---|---|
| PostgreSQL (existing schema) | Data | Upstream (monitor), Downstream (DB-update) | Monitor can't fan out; DB-update can't persist |
| AWS EventBridge | Infrastructure | Downstream (monitor publishes), Upstream (scraper triggered) | Fan-out impossible; entire pipeline blocked |
| AWS SNS | Infrastructure | Downstream (scraper publishes) | Price-drop fan-out blocked; no DB update, no email |
| AWS SQS (2 queues + 2 DLQs) | Infrastructure | Upstream (DB-update, email) | Consumer Lambdas can't receive messages |
| AWS SES | API | Downstream (email Lambda) | Email delivery fails; messages accumulate in SQS / DLQ |
| LLM Provider (Gemini / OpenAI) | API | Upstream (scraper) | Scrape extraction fails; silent failure per FR-2 |
| Existing scraper domain code | Code | Internal | Scraper Lambda cannot be assembled |
| Existing ORM / SQLAlchemy models | Code | Internal | DB-update Lambda cannot persist |
| Pulumi stack (infra) | IaC | Deployment | Pipeline cannot be provisioned |

---

## 6. Resolved Decisions

All questions resolved — no open items blocking design.

| # | Question | Resolution |
|---|---|---|
| OQ-1 | EventBridge schedule interval | Deferred; schedule expression is an environment parameter, value set by product owner before production deployment |
| OQ-2 | Who writes `PriceCheckLog` failure records? | Scraper Lambda writes failure records directly to DB (needs DB access); DB-update Lambda handles success records only |
| OQ-3 | Idempotency strategy for DB-update Lambda | Conditional write: update only if `current_price = old_price`; duplicate messages with stale `old_price` are no-ops |
| OQ-4 | Price drop definition | Any decrease (`new_price < current_price`); minimum delta support deferred to a future iteration |
| OQ-5 | Lambda package structure | Single shared `services/pipeline/` package in the uv workspace; all four Lambda handlers are sub-modules sharing domain and infrastructure code |

---

## 7. Glossary

| Term | Definition |
|---|---|
| Fan-out | The monitor Lambda publishing one EventBridge event per active tracked product in a single execution |
| Correlation ID | A UUID v4 generated once per fan-out cycle, propagated through every event, message, and log entry in that cycle to enable end-to-end tracing |
| Price drop | A scraped price strictly less than `current_price` carried in the EventBridge event payload; any decrease qualifies (minimum delta support deferred) |
| Monitor Lambda | The first Lambda stage: scheduled, reads DB, publishes per-product EventBridge events, performs no scraping |
| Scraper Lambda | The second Lambda stage: triggered per product by EventBridge, runs the scrape flow, publishes to SNS on price drop |
| DB-update Lambda | The third Lambda stage: SQS consumer, persists price update + Notification record + PriceCheckLog to PostgreSQL |
| Email Lambda | The fourth Lambda stage: SQS consumer, sends SES price-drop alert email |
| DLQ | Dead Letter Queue — an SQS queue that receives messages a consumer Lambda fails to process after the configured maximum retry count |
| Active product | A `tracked_products` row where `status = active`; the set the monitor Lambda fans out over |
| Silent failure | When a scrape fails, the scraper Lambda logs the failure and terminates — no downstream SNS publish, no DB write, the product's price remains unchanged until the next scheduled cycle |