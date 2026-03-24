# SDLC Log — Price Drop Tracker

## [2026-03-11 00:00] — /discover-feature — Discovery

- **Task:** N/A
- **Agents dispatched:** None (inception handled directly)
- **Skills invoked:** discover-feature
- **Artifacts produced:** README.md
- **Outcome:** Feature inception complete for Price Drop Tracker with 5 goals and 7 non-goals defined. Feature directory created at docs/designs/2026/001-price-drop-tracker/.
- **Findings:** 4 open questions identified — scraping strategy for anti-bot sites, polling frequency, price definition for variant products, and rate limiting/abuse controls. These should be resolved during discovery or triaged as spikes.

## [2026-03-11 00:01] — /discover-requirements — Discovery

- **Task:** N/A
- **Agents dispatched:** None (requirements handled directly)
- **Skills invoked:** discover-requirements
- **Artifacts produced:** prd.md
- **Outcome:** Requirements structured into 12 FRs (auth, product tracking, price monitoring, notifications) and 9 NFRs covering performance, availability, security, observability, scalability, and fault tolerance. 5 open questions identified with blocking analysis.
- **Findings:** Q1 (scraping strategy) and Q3 (price variant handling) must be resolved before design can begin — both block core data model and infrastructure decisions. Recommend a scraping spike before /design-system.

## [2026-03-11 00:02] — /design-system — Design (HLD)

- **Task:** N/A
- **Agents dispatched:** None (HLD produced directly)
- **Skills invoked:** design-system
- **Artifacts produced:** hld.md
- **Outcome:** High-level architecture defined. Modular Monolith (FastAPI) + AWS Lambda scraper. PostgreSQL on RDS. Google OIDC via Authlib. Email via SES. APScheduler for MVP price-check scheduling. ECS Fargate deployment.
- **ADRs:** (1) Modular monolith over microservices — single developer MVP; (2) APScheduler over EventBridge for MVP — zero infra, clear migration path; (3) Direct Google OAuth2 over Cognito — simpler, no extra cost; (4) Lambda as isolated scraper — fault isolation without distributed systems complexity.
- **Open questions resolved:** Q1 (scraping strategy) → `httpx` + `BeautifulSoup4` on Lambda, Playwright layer available as upgrade; Q3 (variant handling) → track URL as-is, price extracted from URL without variant pinning (MVP).
- **Next steps:** /design-api (tracker + auth endpoints), /design-data (schema + migrations), /design-code (monitor + scraper modules), /design-web (frontend).

## [2026-03-13 00:00] — /design-lld — Low-Level Design

- **Task:** N/A
- **Agents dispatched:** python-architect (Wave 1), data-architect (Wave 1), api-architect (Wave 2)
- **Skills invoked:** design-code, design-api, design-data
- **Artifacts produced:** lld.md
- **Waves executed:** 2 waves (Wave 1: domain model + data schema in parallel; Wave 2: API contracts)
- **Alignment check:** Passed — 2 minor documentation inconsistencies resolved (google_sub UNIQUE strategy, composite index naming); no functional misalignments
- **Outcome:** Complete low-level design across 5 bounded contexts (Identity, Tracker, Notifier, Monitor, Scraper), 3 deployment units, 13 REST endpoints, 5 database tables, 17 Pydantic models, full port/adapter structure, Alembic migration strategy, and 6 open questions for product/ops stakeholders.
- **Findings:** TokenStore implementation (in-memory vs Redis) deferred to implementation — interface is defined; swap is non-breaking. CORS origin and Google callback redirect paths need product confirmation before implementation begins.

## [2026-03-17 00:04] — /implement — Implementation

- **Task:** T-11 — Monitor Lambda
- **Agents dispatched:** Inline implementation (no agents — single tightly-coupled domain)
- **Skills invoked:** implement
- **Artifacts produced:** `scraper_result.py` (added `retry_count` to `ScraperFailure`), `scraper_lambda_client.py` (populates `retry_count` on exhausted retries), `tracked_product_repository.py` (renamed to `list_all_active`, replaced `update_price` with `update_prices` + `update_last_checked_at`), `adapters/sqlalchemy_tracked_product_repository.py` (new), `adapters/sqlalchemy_price_check_log_repository.py` (new), `adapters/ses_email_sender.py` (new), `flows/price_check_cycle_flow.py` (new), `infrastructure/settings.py` (new), `jobs/handler.py` (fully implemented)
- **Outcome:** Task T-11 implemented and verified. `PriceCheckCycleFlow` correctly detects price drops, writes notifications, sends SES emails, writes logs, and isolates per-product failures. Both verification scenarios pass.
- **Findings:** `_MAX_CONCURRENCY` set to 10 (plan description said 20, implementation uses 10 as conservative default). `NotificationRecord` ORM model lacks `product_name`/`product_url` columns — `Notification` domain model has them but they are not persisted (by design, can be fetched from `tracked_products` join).

## [2026-03-13 00:01] — /tasks-breakdown — Breakdown

- **Task:** N/A
- **Agents dispatched:** None (decomposition performed directly)
- **Skills invoked:** tasks-breakdown
- **Artifacts produced:** tasks-breakdown.md, tasks/001-project-scaffolding.md through tasks/015-frontend-notifications-settings.md (16 files total)
- **Outcome:** Feature decomposed into 15 tasks across 7 parallelization tiers. Critical path: T-1 → T-2 → T-3 → T-7 → T-8 → T-12 → T-13 → T-14 (8 steps). Complexity: 3S + 9M + 2L. Max concurrent tasks: 4 (Tier 3).
- **Findings:** 5 risks noted — (1) Scraper extraction reliability on JS-rendered pages is the highest technical risk; run a scraping spike against representative retailer URLs before T-5. (2) `TokenStore` MVP is in-memory — breaks with multiple ECS instances; decide Redis or ElastiCache before T-12. (3) SES sandbox access requires AWS approval; request production access early. (4) Monitor Lambda VPC cold start — provisioned concurrency = 1 recommended before production. (5) Frontend tasks (T-13–T-15) lack a frontend design doc; run `/design-web` first or accept added implementation uncertainty.
