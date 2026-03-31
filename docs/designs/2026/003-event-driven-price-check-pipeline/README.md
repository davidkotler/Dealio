# Event-Driven Price Check Pipeline

> Replace the monolithic monitor lambda with a distributed, event-driven pipeline using EventBridge, SNS, SQS, and discrete Lambda functions.

## Vision

Price checking becomes a fully decoupled, parallelised pipeline where each stage is an independent Lambda function communicating through managed AWS messaging primitives. EventBridge schedules the fan-out; the monitor Lambda publishes one scrape event per active product (including current price) via EventBridge; dedicated scraper Lambdas run concurrently per product; when a price drop is detected the scraper publishes to an SNS topic which fans out to two independent SQS queues — one consumed by a DB-update Lambda, one by an email Lambda — giving the system horizontal scalability, fault isolation, and independent deployability per stage.

## Goals

- **Scheduled fan-out**: EventBridge triggers the monitor Lambda on a configurable schedule; the monitor fetches all active products from the DB and publishes one EventBridge event per product (carrying `tracked_product_id`, `url`, `current_price`, `user_id`, `user_email`, `product_name`) without performing any scraping itself.
- **Isolated scraping**: A dedicated scraper Lambda handles each product independently, triggered by EventBridge; one slow or failing scrape cannot block others.
- **Silent failure on scrape error**: If all sub-scraping operations fail for a product, the pipeline logs the failure and terminates for that product — no DB update, no event published, price remains unchanged until the next scheduled run.
- **SNS fan-out on price drop**: When a price drop is detected, the scraper Lambda publishes to an SNS topic; SNS delivers the message to two independent SQS queues — one for the DB-update Lambda, one for the email Lambda — so each consumer operates and fails independently.
- **Rate-limit ready architecture**: Email delivery is isolated behind its own SQS queue and Lambda; per-user rate limiting can be added to that Lambda without touching any other pipeline stage.
- **Flexible concurrency**: Each user may track up to 5 product URLs; the system is designed to scale to an unbounded number of users by treating Lambda concurrency and SQS throughput as configuration parameters, not hardcoded limits.
- **Observable pipeline**: Each stage emits structured logs with a shared `correlation_id` (set at the monitor Lambda and propagated through every event payload) so the full journey of a single product check is traceable end-to-end.

## Rationale

The current implementation attempts to do everything inside a single Lambda execution: fetch all products, scrape each one, persist results, and send emails. This couples all failure modes together, exhausts Lambda concurrency on slow scrapes, and makes each stage impossible to scale or redeploy independently. The architecture cannot grow beyond a small product catalogue without hitting timeout and concurrency ceilings. Decomposing into discrete, message-connected Lambdas is the natural scaling seam this system needs.

## Value Proposition

| Stakeholder | Value |
|-------------|-------|
| End user | Price-drop emails arrive reliably; individual scrape failures do not delay or suppress other products |
| Developer | Each Lambda stage can be deployed, tested, and debugged in isolation |
| Operations | Failed scrapes are logged with structured context; DLQs on both downstream SQS queues capture any DB or email failures |
| System | Concurrent per-product scraping (one Lambda invocation per product) reduces wall-clock time for the full catalogue check |
| Future | Email rate limiting can be added to the email Lambda without touching the rest of the pipeline |

## Non-Goals

- Real-time scraping triggered by user actions (this pipeline remains scheduled, not on-demand)
- Replacing the existing webapp or frontend — only the backend processing pipeline changes
- Multi-region deployment or cross-region failover
- Per-user email rate limiting (architecture is designed to accommodate this; implementation is deferred)
- Changing the scraping strategy or LLM extraction logic — only the orchestration changes
- Retrying failed scrapes within the same pipeline run — a failed product waits for the next scheduled cycle

## Architecture Decisions

| Decision | Resolution |
|----------|------------|
| Downstream fan-out topology | SNS topic → two independent SQS queues (one per consumer Lambda); each Lambda fails and retries independently |
| Scrape failure handling | Log and terminate for that product; no DB update, no SNS publish; price unchanged until next scheduled run |
| Price comparison data source | Monitor Lambda embeds `current_price` and all product context in the EventBridge event payload; scraper Lambda requires no DB access |
| Concurrency model | One Lambda invocation per product; Lambda reserved concurrency and SQS batch size are environment configuration parameters, not hardcoded |
| Email rate limiting | Not implemented now; the email Lambda's SQS queue is the natural insertion point — add a per-user deduplication/rate-limit layer there when required |
| Max products per user | 5 URLs per user at launch; pipeline scales horizontally, no architectural change needed to raise this limit |

## Open Questions

- What is the desired EventBridge schedule interval? (e.g., every 30 min, every hour) — confirm with product owner before infrastructure design

## Status

| Phase | State |
|-------|-------|
| **Inception** | ✅ Complete |
| **Discovery** | ✅ Complete |
| **Design** | 🔄 HLD Complete — LLD Not Started |
| **Breakdown** | ⬜ Not Started |
| **Implementation** | ⬜ Not Started |
| **Ship** | ⬜ Not Started |