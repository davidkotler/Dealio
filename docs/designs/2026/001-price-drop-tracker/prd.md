# Requirements: Price Drop Tracker

**Date:** 2026-03-11
**Status:** Draft
**Author:** Claude Code (via /discover-requirements)
**Stakeholders:** Product Owner

---

## 1. Overview

The Price Drop Tracker enables online shoppers to paste any product URL and have the system
automatically monitor its price. When a price drops, users are notified by email and via an
in-app notification on their dashboard. The MVP targets web users who want automated deal
alerts without manual checking, limited to tracking up to 5 products per free account.

---

## 2. Functional Requirements

### FR-1: User Registration
**As a** new visitor, **I want** to create an account with my email and password, **so that**
I can start tracking products and receive personalised price drop alerts.

**Acceptance Criteria:**
- **Given** a visitor on the sign-up page, **when** they submit a valid email and password,
  **then** their account is created and they are redirected to the dashboard
- **Given** a visitor submits an email already registered, **when** they submit, **then**
  they see an error indicating the email is in use (no account enumeration beyond this context)
- **Given** a visitor submits a password shorter than 8 characters, **when** they submit,
  **then** they see a validation error and no account is created
- **Given** a visitor submits an invalid email format, **when** they submit, **then**
  they see a validation error and no account is created

---

### FR-2: User Login
**As a** registered user, **I want** to log in with my email and password, **so that**
I can access my tracked products and notifications.

**Acceptance Criteria:**
- **Given** a registered user with correct credentials, **when** they submit the login form,
  **then** they are authenticated and redirected to their dashboard
- **Given** a user with incorrect credentials, **when** they submit, **then** they see a
  generic "invalid email or password" message and are not logged in
- **Given** an authenticated user, **when** their session expires, **then** they are
  redirected to the login page on next request

---

### FR-3: Password Reset
**As a** user who has forgotten their password, **I want** to request a password reset link
via email, **so that** I can regain access to my account.

**Acceptance Criteria:**
- **Given** a user enters a registered email on the forgot-password page, **when** they
  submit, **then** a password reset email is sent and a success message is shown (regardless
  of whether email exists, to prevent enumeration)
- **Given** a user clicks a valid reset link, **when** they submit a new password, **then**
  their password is updated and the reset link is invalidated
- **Given** a user clicks an expired or already-used reset link, **when** they attempt
  to reset, **then** they see an error and are prompted to request a new link
- **Given** a reset link, **when** it has not been used within 1 hour, **then** it expires
  automatically

---

### FR-4: Change Password
**As** an authenticated user, **I want** to change my password from the settings page,
**so that** I can keep my account secure.

**Acceptance Criteria:**
- **Given** an authenticated user on the settings page, **when** they submit their current
  password and a valid new password, **then** their password is updated
- **Given** a user submits an incorrect current password, **when** they submit, **then**
  they see an error and their password is not changed
- **Given** a new password shorter than 8 characters, **when** submitted, **then** a
  validation error is shown

---

### FR-5: Add Product to Tracking
**As** an authenticated user, **I want** to add a product URL to my tracking list, **so that**
the system monitors its price and alerts me when it drops.

**Acceptance Criteria:**
- **Given** a user with fewer than 5 tracked products, **when** they submit a valid product
  URL, **then** the system scrapes the product page, extracts the current price and product
  name, and adds the product to their dashboard
- **Given** a user with 5 tracked products, **when** they attempt to add another, **then**
  they see an error stating the 5-product limit has been reached
- **Given** a URL from which the system cannot extract a price, **when** submission is
  attempted, **then** the user sees an error indicating the product could not be tracked
  (URL invalid or price not found)
- **Given** a URL the user has already added, **when** they attempt to add it again,
  **then** they see an error indicating it is already being tracked

---

### FR-6: Remove Product from Tracking
**As** an authenticated user, **I want** to remove a product from my tracking list, **so that**
I stop receiving notifications and free up a tracking slot.

**Acceptance Criteria:**
- **Given** a tracked product on the dashboard, **when** the user clicks "Remove", **then**
  the product is removed from their list and no further price checks or notifications occur
  for that product
- **Given** a product is removed, **when** the user views the dashboard, **then** the product
  is no longer shown and the user's tracked count decreases by one

---

### FR-7: Dashboard — View Tracked Products
**As** an authenticated user, **I want** to see all my tracked products on a dashboard,
**so that** I can review current prices, price changes, and when each was last checked.

**Acceptance Criteria:**
- **Given** an authenticated user, **when** they navigate to the dashboard, **then** they
  see a list of their tracked products, each showing: product name, current price, previous
  price, and last-checked timestamp
- **Given** a user with no tracked products, **when** they view the dashboard, **then**
  they see an empty state with a prompt to add their first product
- **Given** a product whose price has never changed, **when** displayed, **then** the
  previous price field is shown as "—" or equivalent empty indicator

---

### FR-8: Periodic Price Monitoring
**As** the system, **I want** to periodically check every tracked product's current price,
**so that** price drops can be detected and users notified.

**Acceptance Criteria:**
- **Given** products are being tracked, **when** a scheduled price-check cycle runs,
  **then** all active tracked products across all users are checked within the cycle window
- **Given** a price check succeeds, **when** the fetched price differs from the stored
  current price, **then** the current price is updated, the previous price is stored, and
  the last-checked timestamp is updated
- **Given** a price check fails for a product (network error, scraping failure), **when**
  the failure occurs, **then** that product's check is retried up to 3 times with exponential
  backoff, and the failure is logged; other products' checks are not affected
- **Given** a product check fails all retries, **when** logging occurs, **then** the
  last-checked timestamp is not updated and the user is not notified (silent failure, monitored
  via system observability)

---

### FR-9: Price Drop Detection and Notification Trigger
**As** the system, **I want** to detect when a product's new price is lower than its previous
price, **so that** users can be notified.

**Acceptance Criteria:**
- **Given** a price check returns a price strictly lower than the stored current price,
  **when** the update is processed, **then** a price-drop notification event is emitted for
  that user and product
- **Given** a price check returns the same or a higher price, **when** processed,
  **then** no notification event is emitted

---

### FR-10: Email Notification on Price Drop
**As** a user with a tracked product, **I want** to receive an email when its price drops,
**so that** I can take action on the deal without visiting the site.

**Acceptance Criteria:**
- **Given** a price-drop event for a product, **when** the notification is processed, **then**
  the user receives an email to their registered address containing: product name, previous
  price, new (lower) price, and a link to the product
- **Given** the email service is unavailable, **when** sending is attempted, **then** the
  notification is queued for retry; the user eventually receives the email when the service
  recovers
- **Given** a single price-check cycle detects a drop, **when** notifications are sent,
  **then** exactly one email is sent per price-drop event (no duplicates)

---

### FR-11: In-App Notification on Price Drop
**As** a user with a tracked product, **I want** to see in-app notifications of price drops
on my dashboard, **so that** I am informed even if I do not check my email.

**Acceptance Criteria:**
- **Given** a price-drop event, **when** the user next views their dashboard, **then**
  a notification indicator is visible (e.g., badge, banner, or notification list entry)
  showing which product dropped and by how much
- **Given** a user views and dismisses a notification, **when** they reload the dashboard,
  **then** the dismissed notification is no longer shown as unread

---

### FR-12: Support Contact from Settings
**As** an authenticated user, **I want** to contact support from the settings page, **so that**
I can report issues or get help without leaving the app.

**Acceptance Criteria:**
- **Given** an authenticated user on the settings page, **when** they click "Contact Support",
  **then** they are provided a support email address or a pre-filled email link to contact
  the team

---

## 3. Non-Functional Requirements

### NFR-1: Performance — Dashboard Load Time
- **Target:** Dashboard page renders within p95 < 2 s under normal load (< 100 concurrent users)
- **Rationale:** Users expect near-instant access to their tracked products
- **Validation:** Synthetic monitoring on the dashboard route; load test at 100 concurrent users
- **Priority:** Must Have

---

### NFR-2: Performance — Product Addition Latency
- **Target:** Product addition (scrape + save) completes or returns a processing response within
  p95 < 10 s; if asynchronous, the user sees a "checking price…" state and the product appears
  within 30 s
- **Rationale:** Scraping an external page introduces latency beyond our control; users need
  feedback that the operation is in progress
- **Validation:** Manual and automated test with representative product URLs; timeout monitoring
- **Priority:** Must Have

---

### NFR-3: Availability — Service Uptime
- **Target:** 99.5% uptime measured monthly for the web application; price monitoring may have
  scheduled maintenance windows of up to 1 hour/week without SLA violation
- **Rationale:** MVP product — high availability instils trust; brief monitoring gaps acceptable
- **Validation:** Uptime monitoring with external ping service; monthly availability report
- **Priority:** Should Have

---

### NFR-4: Security — Authentication & Password Storage
- **Target:** Passwords stored using bcrypt (cost factor ≥ 12) or equivalent adaptive hash;
  all traffic over HTTPS; session tokens are HTTP-only cookies with Secure flag; reset tokens
  expire after 1 hour
- **Rationale:** User credentials are sensitive; email-based auth makes password security
  the primary attack surface
- **Validation:** Security review of auth implementation; penetration test before public launch
- **Priority:** Must Have

---

### NFR-5: Security — Input Validation & Abuse Prevention
- **Target:** All user-submitted URLs are validated as syntactically valid HTTP/HTTPS URLs
  before scraping; rate limit URL addition to max 10 attempts per user per hour
- **Rationale:** Prevents the scraping infrastructure from being weaponised against arbitrary
  hosts; mitigates accidental or deliberate abuse
- **Validation:** Unit tests on URL validation; integration test for rate-limit enforcement
- **Priority:** Must Have

---

### NFR-6: Security — Data Privacy
- **Target:** No PII (user email, names) written to application logs or traces; user data
  scoped to the authenticated user only (no cross-user data leakage)
- **Rationale:** GDPR and general data hygiene; user emails are the only PII held
- **Validation:** Log audit during testing; code review for query-level user scoping
- **Priority:** Must Have

---

### NFR-7: Observability — Operational Visibility
- **Target:** Structured logs for: price check start/end, scraping failures (with URL and error
  type), notification delivery success/failure; health endpoint returning 200 when system is
  nominal; alerting on error rate > 5% of price checks per cycle
- **Rationale:** Scraping failures are expected and must be detected without user-reported
  incidents; notification failures are silent to users
- **Validation:** Verify log fields during integration testing; confirm alert fires in staging
- **Priority:** Must Have

---

### NFR-8: Scalability — Initial Load Target
- **Target:** System handles 1,000 registered users each tracking 5 products (5,000 tracked
  products) with a price-check cycle completing within the configured polling interval;
  architecture designed for horizontal scaling of the web layer and polling workers
- **Rationale:** MVP load is modest; design should not require re-architecture at 10× growth
- **Validation:** Load test simulating 5,000 product checks in a single cycle; confirm no
  single-instance assumptions in deployment config
- **Priority:** Should Have

---

### NFR-9: Fault Tolerance — Price Check Resilience
- **Target:** A failure on any single product's price check must not prevent checks for other
  products; failed checks retried up to 3 times with exponential backoff before recording
  failure
- **Rationale:** Scraping is inherently unreliable; one broken retailer page should not
  degrade the entire monitoring service
- **Validation:** Integration test injecting scraping failure for one product in a multi-product
  check cycle; confirm others complete successfully
- **Priority:** Must Have

---

## 4. Constraints

### Technical Constraints
- **Web only:** No mobile app for MVP; responsive web design is acceptable but native apps
  are out of scope
- **Product limit:** Free tier capped at 5 tracked products per user; enforced at application
  layer
- **Generic URL scraping:** Must work for any HTTP/HTTPS product URL without retailer-specific
  integrations; scraping strategy (headless browser, proxy, scraping API) is a technical
  decision left to the Design phase
- **Notification channels:** Email and in-app only; no SMS, push notifications, or webhooks
  in MVP
- **No price history:** Dashboard shows only current price and previous price — no time-series
  chart or trend analysis in MVP

### Business Constraints
- **No paid tiers in MVP:** Billing, subscriptions, and premium features are explicitly out
  of scope
- **No browser extension:** One-click tracking from product pages is a non-goal for MVP
- **No social features:** Wishlists, sharing, or social alerts are out of scope

### Organizational Constraints
- **Small team:** Implementation should favour simplicity and proven patterns over novel
  approaches
- **Scraping risk:** Anti-bot protections (Cloudflare, CAPTCHA) at target retailers are a
  known risk; a technical spike is required before committing to a scraping implementation

---

## 5. Dependencies

| Dependency | Type | Direction | Impact if Unavailable |
|------------|------|-----------|----------------------|
| Transactional email provider (e.g., SendGrid, AWS SES, SMTP relay) | External service | Downstream | Email notifications cannot be delivered; in-app notifications unaffected |
| Scraping infrastructure (Playwright headless browser / proxy rotation / scraping API — TBD) | Infrastructure | Upstream | Product addition and price monitoring fail entirely; core feature unavailable |
| Relational database (PostgreSQL recommended) | Infrastructure | Downstream | All persistence unavailable; system non-functional |
| Background job / task scheduler (e.g., Celery + Redis, APScheduler, cron) | Infrastructure | Internal | Periodic price checks cannot run; no price drops detected |
| Object storage or cache (optional, Redis) | Infrastructure | Internal | Session management and rate limiting affected if absent |

---

## 6. Open Questions

| # | Question | Why It Matters | Blocks |
|---|----------|----------------|--------|
| Q1 | What scraping strategy will be used for anti-bot protected sites (Playwright headless, proxy rotation, third-party scraping API)? | Determines infrastructure cost, reliability, and legal risk of the core feature | Implementation of FR-5 (Add Product) and FR-8 (Price Monitoring) |
| Q2 | What is the price-check polling frequency? (e.g., every hour, every 6 hours, daily) | Directly affects infrastructure cost, number of scraping requests, and how quickly users are notified after a price drop | NFR-8 (Scalability) and overall infrastructure sizing |
| Q3 | How is "price" defined for product pages with variants (size, colour, model)? Track the URL as-is without variant selection, or prompt the user to pin a specific variant? | Determines data model for tracked products and UX for adding products with multiple prices on one page | FR-5 (Add Product) acceptance criteria and data model design |
| Q4 | What rate-limiting and abuse controls are needed for URL addition? (e.g., per-user hourly limit, domain blocklist, known-retailer allowlist) | Prevents scraping infrastructure from being used to attack arbitrary hosts; affects security posture | NFR-5 (Input Validation & Abuse Prevention) design |
| Q5 | What is the behaviour when a tracked product URL goes dead (404, site down) or the product is discontinued? | Affects UX for stale tracked products and error communication to users | FR-7 (Dashboard) and FR-8 (Price Monitoring) edge-case handling |

---

## 7. Glossary

| Term | Definition |
|------|-----------|
| Tracked product | A product URL added by a user that the system monitors for price changes |
| Price drop | A state transition where the scraped price of a tracked product is strictly lower than the previously recorded price |
| Current price | The most recently successfully scraped price for a tracked product |
| Previous price | The price recorded immediately before the current price was updated |
| Last-checked time | The timestamp of the most recent successful price check for a tracked product |
| In-app notification | A visual indicator on the dashboard informing the user of a price drop since their last visit |
| Price check cycle | One execution of the background job that checks all active tracked products across all users |
| Scraping | The process of fetching a product page and extracting its price using automated parsing |
