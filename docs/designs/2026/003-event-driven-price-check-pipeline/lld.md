# LLD — Event-Driven Price Check Pipeline

**Feature:** 003-event-driven-price-check-pipeline
**Date:** 2026-03-30
**Status:** Approved
**Sources:** lld-code.md, lld-data.md, lld-event.md, lld-pulumi.md (consolidated)

---

## 0. Service & Domain Structure

The pipeline replaces the monolithic `monitor_lambda` with four independent Lambda functions. All code lives in the new `services/pipeline/` uv workspace member. No existing services are modified.

### 0.1 Bounded Context → Service/Domain Mapping

| HLD Bounded Context | Service | Domain | Status | Responsibility |
|---|---|---|---|---|
| Monitor (fan-out) | `services/pipeline/` | `domains/monitor/` | [new] | Schedule-triggered; reads all tracked products + user emails; publishes one EventBridge event per product |
| Scraper (per-product) | `services/pipeline/` | `domains/scraper/` | [new] | Triggered by EventBridge; runs scrape flow; publishes SNS on price drop; writes failure log |
| DB-Update (persistence) | `services/pipeline/` | `domains/db_update/` | [new] | SQS-triggered; conditional price update + Notification + PriceCheckLog in one transaction |
| Email (delivery) | `services/pipeline/` | `domains/email/` | [new] | SQS-triggered; no DB; sends SES alert email |
| Scraper Engine (shared) | `services/pipeline/` | `shared/scraper_domain/` | [new — copy] | Verbatim copy of `monitor_lambda` scraper logic; anti-corruption layer boundary |

### 0.2 Package Layout

```
services/pipeline/
├── pyproject.toml
├── main_monitor.py           # Lambda bootstrap: monitor
├── main_scraper.py           # Lambda bootstrap: scraper
├── main_db_update.py         # Lambda bootstrap: db_update
├── main_email.py             # Lambda bootstrap: email
└── pipeline/
    ├── __init__.py
    ├── domains/
    │   ├── monitor/
    │   │   ├── adapters/
    │   │   │   ├── sqlalchemy_tracked_product_read_adapter.py
    │   │   │   └── eventbridge_publish_adapter.py
    │   │   ├── flows/fan_out_flow.py
    │   │   ├── jobs/handler.py
    │   │   ├── models/
    │   │   │   ├── domain/product_fan_out_payload.py
    │   │   │   └── contracts/events/product_price_check_requested.py
    │   │   ├── ports/
    │   │   │   ├── tracked_product_read_port.py
    │   │   │   └── eventbridge_publish_port.py
    │   │   └── exceptions.py
    │   ├── scraper/
    │   │   ├── adapters/
    │   │   │   ├── sns_publish_adapter.py
    │   │   │   └── sqlalchemy_failure_log_adapter.py
    │   │   ├── flows/scrape_dispatch_flow.py
    │   │   ├── jobs/handler.py
    │   │   ├── models/
    │   │   │   ├── domain/
    │   │   │   │   ├── scraper_event_payload.py
    │   │   │   │   └── price_drop_message.py
    │   │   │   └── contracts/events/price_drop_sns_message.py
    │   │   ├── ports/
    │   │   │   ├── sns_publish_port.py
    │   │   │   └── price_check_log_write_port.py
    │   │   └── exceptions.py
    │   ├── db_update/
    │   │   ├── adapters/sqlalchemy_price_drop_persistence_adapter.py
    │   │   ├── flows/persist_price_drop_flow.py
    │   │   ├── jobs/handler.py
    │   │   ├── models/domain/price_drop_sqs_message.py
    │   │   ├── ports/
    │   │   │   ├── tracked_product_write_port.py
    │   │   │   ├── notification_write_port.py
    │   │   │   └── price_check_log_write_port.py
    │   │   └── exceptions.py
    │   └── email/
    │       ├── adapters/ses_email_sender.py
    │       ├── flows/send_alert_flow.py
    │       ├── jobs/handler.py
    │       ├── models/domain/email_alert_payload.py
    │       ├── ports/email_sender_port.py
    │       └── exceptions.py
    └── shared/
        ├── scraper_domain/           # verbatim copy from monitor_lambda
        │   └── (all scraper sub-modules)
        ├── orm/
        │   ├── base.py
        │   ├── user_record.py
        │   ├── tracked_product_record.py
        │   ├── notification_record.py
        │   └── price_check_log_record.py
        └── infrastructure/
            ├── database.py
            ├── settings.py
            └── logger.py
```

### 0.3 Infrastructure Layout

```
infra/pipeline/
├── __main__.py               # Pulumi entry point
├── Pulumi.yaml
├── Pulumi.dev.yaml
├── Pulumi.staging.yaml
├── Pulumi.prod.yaml
└── components/
    ├── iam.py
    ├── messaging.py
    └── lambdas.py
```

---

## 1. Data Layer

### 1.1 Scope

The pipeline accesses the shared PostgreSQL schema (owned by `services/webapp/alembic/`). It introduces **no new migrations**. All pipeline ORM records live in `pipeline/shared/orm/` with their own `PipelineBase` — no cross-package imports from `webapp` or `monitor_lambda`.

### 1.2 Physical Schema (existing tables accessed)

| Table | Columns used | Access mode |
|---|---|---|
| `users` | `id`, `email` | Monitor: read-only JOIN |
| `tracked_products` | `id`, `user_id`, `url`, `product_name`, `current_price`, `previous_price`, `last_checked_at`, `created_at` | Monitor: full read; DB-Update: conditional write |
| `notifications` | `id`, `user_id`, `tracked_product_id`, `old_price`, `new_price`, `created_at`, `read_at` | DB-Update: INSERT only |
| `price_check_log` | `id`, `tracked_product_id`, `checked_at`, `result`, `retry_count`, `error_message` | Scraper: INSERT failure; DB-Update: INSERT success |

> **Schema note:** `prd.md` FR-1 references `status = active` filter, but `tracked_products` has no `status` column. The HLD acknowledges this: all rows are fetched. Confirm with product owner before adding a `status` column.

### 1.3 ORM Models

#### `PipelineBase`
```python
# pipeline/shared/orm/base.py
from sqlalchemy.orm import DeclarativeBase

class PipelineBase(DeclarativeBase):
    """Independent base — pipeline never imports ORM from other workspace members."""
    pass
```

#### `TrackedProductRecord`
```python
# pipeline/shared/orm/tracked_product_record.py
class TrackedProductRecord(PipelineBase):
    __tablename__ = "tracked_products"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    product_name: Mapped[str] = mapped_column(String(500), nullable=False)
    current_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    previous_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
```

#### `NotificationRecord`
```python
# pipeline/shared/orm/notification_record.py
class NotificationRecord(PipelineBase):
    __tablename__ = "notifications"
    # CheckConstraint: new_price < old_price, old_price > 0, new_price >= 0

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    tracked_product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    old_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    new_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default="NOW()")
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
```

#### `PriceCheckLogRecord`
```python
# pipeline/shared/orm/price_check_log_record.py
class PriceCheckLogRecord(PipelineBase):
    __tablename__ = "price_check_log"
    # CheckConstraint: result IN ('success', 'failure')
    # CheckConstraint: success→error_message IS NULL; failure→error_message IS NOT NULL

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tracked_product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default="NOW()")
    result: Mapped[str] = mapped_column(String(10), nullable=False)    # 'success' | 'failure'
    retry_count: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
```

### 1.4 Access Patterns

#### Monitor — Fan-Out Read

```sql
SELECT tp.id, tp.user_id, u.email AS user_email, tp.url, tp.product_name, tp.current_price
FROM tracked_products tp
JOIN users u ON u.id = tp.user_id
ORDER BY tp.id
```
Full scan (all rows needed). No `WHERE` clause — no `status` column. Up to 5,000 rows per cycle.

#### Scraper — Failure Log INSERT

```sql
INSERT INTO price_check_log (id, tracked_product_id, checked_at, result, retry_count, error_message)
VALUES (:id, :tracked_product_id, NOW(), 'failure', 0, :error_message)
```
Autocommit single-row INSERT. Not idempotent — duplicate failure logs on Lambda retry are acceptable (audit records).

#### DB-Update — Atomic Price-Drop Transaction (3 writes in one `BEGIN`/`COMMIT`)

**Write 1 — Idempotency guard (conditional UPDATE):**
```sql
UPDATE tracked_products
SET current_price = :new_price, previous_price = :old_price, last_checked_at = NOW()
WHERE id = :tracked_product_id AND current_price = :old_price
```
`rowcount == 1` → proceed. `rowcount == 0` → duplicate, abort, acknowledge SQS message.

**Write 2 — Notification INSERT** (only if Write 1 rowcount == 1):
```sql
INSERT INTO notifications (id, user_id, tracked_product_id, old_price, new_price, created_at)
VALUES (:id, :user_id, :tracked_product_id, :old_price, :new_price, NOW())
```

**Write 3 — PriceCheckLog success INSERT** (only if Write 1 rowcount == 1):
```sql
INSERT INTO price_check_log (id, tracked_product_id, checked_at, result, retry_count, error_message)
VALUES (:id, :tracked_product_id, NOW(), 'success', 0, NULL)
```

If Write 2 or 3 fails, the transaction rolls back (Write 1 included). SQS redelivers; next delivery retries the full transaction cleanly (price is still `old_price`).

#### Email — No DB Access

All required data is carried in the SQS message payload.

### 1.5 Session Management

| Stage | Session scope | Commit strategy |
|---|---|---|
| Monitor | One per invocation, read-only | No commit (read-only) |
| Scraper | One per invocation, write on failure path | `session.commit()` after single INSERT |
| DB-Update | One per SQS record, write path | Explicit `await session.commit()` after flow completes |
| Email | None | N/A |

---

## 2. Code Architecture

### 2.1 Design Constraints

- `from __future__ import annotations` on every file
- `@dataclass` for flows and adapters (injected ports as dataclass fields)
- `Protocol` + `@runtime_checkable` for ports
- All flows are `async def`; handlers wrap with `asyncio.run()`
- `structlog.get_logger(__name__)` — JSON logging, `snake_case.dot.namespaced` event keys
- `Decimal` for prices in domain models; `str` for prices in event payloads (Decimal-safe serialisation)
- Full absolute imports: `from pipeline.domains.monitor.ports...`
- `match/case` for `ScraperResult` union dispatch in `scrape_dispatch_flow`
- No I/O inside flows — all I/O through injected port interfaces

### 2.2 Shared Infrastructure

#### `Settings`
```python
# pipeline/shared/infrastructure/settings.py
@dataclass(frozen=True)
class Settings:
    database_url: str = field(default_factory=lambda: os.environ.get("DATABASE_URL", ...))
    aws_region: str = field(default_factory=lambda: os.environ.get("AWS_REGION", "us-east-1"))
    eventbridge_bus_name: str = field(default_factory=lambda: os.environ.get("EVENTBRIDGE_BUS_NAME", "dealio-pipeline"))
    sns_price_drop_topic_arn: str = field(default_factory=lambda: os.environ.get("SNS_PRICE_DROP_TOPIC_ARN", ""))
    ses_from_address: str = field(default_factory=lambda: os.environ.get("SES_FROM_ADDRESS", ""))
    llm_provider: str = field(default_factory=lambda: os.environ.get("LLM_PROVIDER", "gemini"))
    llm_api_key: str = field(default_factory=lambda: os.environ.get("LLM_API_KEY", ""))
    llm_model: str = field(default_factory=lambda: os.environ.get("LLM_MODEL", "gemini-2.5-flash"))
```

#### `database.py`
```python
def make_engine(database_url: str) -> AsyncEngine: ...
def make_session(engine: AsyncEngine) -> AsyncSession: ...
```

#### `logger.py`
```python
def configure_logger() -> None:
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        ...
    )
```
Call once at Lambda cold start in each bootstrap script.

#### `shared/scraper_domain/`

Verbatim copy of `monitor_lambda/monitor_lambda/domains/scraper/`. No changes to scraper logic. Integration boundary:

```python
from pipeline.shared.scraper_domain.flows.scrape_flow import scrape_flow
from pipeline.shared.scraper_domain.models.domain.scraper_result import ScraperResult, ScraperSuccess, ScraperFailure

async def scrape_flow(url: str, *, llm_client: LLMClient) -> ScraperResult: ...
```

### 2.3 Monitor Domain

**Domain model:** `ProductFanOutPayload` — one per tracked product, stamped with `correlation_id`.

**Ports:**
- `TrackedProductReadPort.list_all_for_fan_out() -> list[ProductFanOutPayload]`
- `EventBridgePublishPort.publish_batch(payloads: list[ProductFanOutPayload]) -> None`

**Flow — `fan_out_flow`:**
```python
async def fan_out_flow(*, product_read_port, eventbridge_port) -> None:
    products = await product_read_port.list_all_for_fan_out()
    if not products:
        log.info("monitor.fan_out.no_products")
        return
    log.info("monitor.fan_out.started", product_count=len(products))
    await eventbridge_port.publish_batch(products)
    log.info("monitor.fan_out.complete", product_count=len(products))
```

**Adapters:**
- `SQLAlchemyTrackedProductReadAdapter` — generates `correlation_id = uuid.uuid4()` for the cycle, executes fan-out SQL, returns `list[ProductFanOutPayload]`
- `EventBridgePublishAdapter` — batches into groups of 10 (`_BATCH_SIZE = 10`), calls `asyncio.gather()` over all chunks, uses `asyncio.to_thread()` for boto3 sync call

**Handler:** `pipeline/domains/monitor/jobs/handler.py` — `def handler(event, context) -> {"status": "ok"}`

### 2.4 Scraper Domain

**Domain models:**
- `ScraperEventPayload` — parsed inbound EventBridge `detail` field
- `PriceDropMessage` — outbound SNS message domain type (contains `old_price`, `new_price` as `Decimal`)

**Ports:**
- `SNSPublishPort.publish_price_drop(message: PriceDropMessage) -> None`
- `PriceCheckLogWritePort.write_failure(*, tracked_product_id, failure, checked_at, correlation_id) -> None`

**Flow — `scrape_dispatch_flow`:**
```python
async def scrape_dispatch_flow(*, event, llm_client, sns_port, log_port) -> None:
    result = await scrape_flow(event.url, llm_client=llm_client)
    match result:
        case ScraperFailure() as failure:
            log.warning("scraper.scrape.failure", error_type=failure.error_type.value)
            await log_port.write_failure(...)

        case ScraperSuccess() as success if success.price < event.current_price:
            log.info("scraper.price_drop.detected", user_id=str(event.user_id))
            await sns_port.publish_price_drop(PriceDropMessage(...))

        case ScraperSuccess():
            log.info("scraper.scrape.no_price_drop")
```

**Adapters:**
- `SNSPublishAdapter` — `asyncio.to_thread(client.publish, ...)` with `Message=PriceDropSNSMessage.from_domain(message).model_dump_json()`
- `SQLAlchemyFailureLogAdapter` — single-row INSERT, `session.commit()`

**Handler:** Parses `raw_event["detail"]` into `ScraperEventPayload`; instantiates LLM client based on `settings.llm_provider`; wires flow.

### 2.5 DB-Update Domain

**Domain model:** `PriceDropSQSMessage` — parsed inbound SQS/SNS payload (prices as `Decimal`).

**Ports (3 separate protocols):**
- `TrackedProductWritePort.conditional_update_price(...) -> bool`
- `NotificationWritePort.create_notification(...) -> None`
- `PriceCheckLogWritePort.write_success(...) -> None`

**Flow — `persist_price_drop_flow`:**
```python
async def persist_price_drop_flow(*, message, product_write_port, notification_port, log_port) -> None:
    updated = await product_write_port.conditional_update_price(
        tracked_product_id=message.tracked_product_id,
        old_price=message.old_price, new_price=message.new_price, checked_at=checked_at,
    )
    if not updated:
        log.info("db_update.conditional_write.skipped")
        return                      # Duplicate — acknowledge SQS without further writes
    await notification_port.create_notification(...)
    await log_port.write_success(...)
    log.info("db_update.persist.complete")
```

**Adapter — `SQLAlchemyPriceDropPersistenceAdapter`:**

Single class implementing all 3 ports, sharing one `AsyncSession`. Transaction lifecycle:
1. `conditional_update_price` — executes UPDATE, checks `rowcount == 1`
2. `create_notification` — INSERT into `notifications`
3. `write_success` — INSERT into `price_check_log`
4. Handler calls `await session.commit()` after flow returns

If any write after step 1 raises, the session context manager rolls back. SQS retries; next delivery re-enters with `current_price == old_price`.

**Handler:** Unwraps SNS-over-SQS double-JSON, loops over `Records`, commits per message.

### 2.6 Email Domain

**Domain model:** `EmailAlertPayload` — contains `to_email` (= `user_email`; **NEVER logged**), `product_name`, `product_url`, `old_price`, `new_price`, `user_id`, `correlation_id`.

**Port:** `EmailSenderPort.send_price_drop_alert(payload: EmailAlertPayload) -> None`

**Flow — `send_alert_flow`:**
```python
async def send_alert_flow(*, payload, email_sender) -> None:
    log.bind(correlation_id=..., user_id=..., stage="email").info("email.alert.sending")
    await email_sender.send_price_drop_alert(payload)
    log.info("email.alert.sent")
```

**Adapter — `SESEmailSenderAdapter`:** `asyncio.to_thread(client.send_email, ...)`. Raises `EmailDeliveryError from ClientError`.

**Handler:** No DB access. Unwraps SNS-over-SQS envelope; builds `EmailAlertPayload`; calls `send_alert_flow`. `SESEmailSenderAdapter` instantiated once, shared across all records in the batch.

### 2.7 Bootstrap Scripts

```python
# main_monitor.py
from pipeline.domains.monitor.jobs.handler import handler  # noqa: F401

# main_scraper.py
from pipeline.domains.scraper.jobs.handler import handler  # noqa: F401

# main_db_update.py
from pipeline.domains.db_update.jobs.handler import handler  # noqa: F401

# main_email.py
from pipeline.domains.email.jobs.handler import handler  # noqa: F401
```

Lambda handler string for each function: `main_<stage>.handler`.

---

## 3. Event Contracts

### 3.1 Channel 1 — EventBridge: `ProductPriceCheckRequested`

**Source:** `dealio.pipeline.monitor`
**DetailType:** `ProductPriceCheckRequested`
**Bus:** `dealio-{env}-pipeline`

#### Pydantic Model
```python
class ProductPriceCheckRequestedDetail(BaseModel):
    model_config = ConfigDict(frozen=True, extra="ignore")   # extra="ignore" for additive evolution

    tracked_product_id: str    # UUID as string
    url: str
    current_price: str         # Decimal as string — validated via field_validator
    user_id: str               # UUID as string
    user_email: str            # PII — delivery only; NEVER log
    product_name: str
    correlation_id: str        # UUID as string — one per fan-out cycle
```

**Batching:** Monitor Lambda batches 10 events per `PutEvents` call. All batches dispatched concurrently via `asyncio.gather`. For 5,000 products: 500 concurrent calls ≈ 2–5 s fan-out at p95.

**EventBridge rule filter:**
```json
{
  "source": ["dealio.pipeline.monitor"],
  "detail-type": ["ProductPriceCheckRequested"]
}
```

**Missing field behaviour:** `KeyError` propagates to Lambda runtime → invocation marked failed → EventBridge retries (default: 2 retries).

### 3.2 Channel 2 — SNS→SQS: `PriceDropMessage`

**Topic:** `dealio-{env}-price-drop`
**Consumers:** `dealio-{env}-db-update` queue (DB-Update Lambda), `dealio-{env}-email` queue (Email Lambda)

#### Pydantic Model
```python
class PriceDropSNSMessage(BaseModel):
    model_config = ConfigDict(frozen=True, extra="ignore")

    tracked_product_id: str    # UUID as string
    user_id: str               # UUID as string
    user_email: str            # PII — delivery only; NEVER log
    product_name: str
    product_url: str
    old_price: str             # Decimal as string
    new_price: str             # Decimal as string — validated: Decimal(new_price) < Decimal(old_price)
    correlation_id: str        # Forwarded unchanged from inbound EventBridge event
```

#### SQS Envelope Unwrapping

SNS subscriptions use `raw_message_delivery=False` (default). Each SQS record's `body` is a JSON-serialised SNS notification envelope. Handlers unwrap with:

```python
for record in sqs_event["Records"]:
    sns_envelope = json.loads(record["body"])           # Step 1: SQS body → SNS envelope
    body = json.loads(sns_envelope["Message"])          # Step 2: SNS envelope → payload JSON
    message = PriceDropSQSMessage(...)                  # Step 3: parse into domain type
```

### 3.3 Participants Registry

#### Monitor Lambda (Producer — `ProductPriceCheckRequested`)

| Attribute | Value |
|---|---|
| Trigger | EventBridge Scheduler rule (configurable rate, default `rate(1 hour)`) |
| Idempotency | Not required — scraping is read-only; duplicate invocations produce duplicate scrapes (acceptable) |
| Failure strategy | PutEvents batch failure → Lambda invocation fails → Scheduler does not retry scheduled invocations |

#### Scraper Lambda (Consumer — `ProductPriceCheckRequested` / Producer — `PriceDropMessage`)

| Attribute | Value |
|---|---|
| Trigger | EventBridge rule on `dealio-{env}-pipeline` bus |
| Timeout | 60 s (NFR-2) |
| Idempotency | Not required — scraping is read-only; duplicate SNS publishes are gated by DB-Update conditional write |
| Failure strategy | ScraperFailure → write PriceCheckLog failure, exit success. Unhandled exception → EventBridge retries (2×) |

#### DB-Update Lambda (Consumer — `PriceDropMessage`)

| Attribute | Value |
|---|---|
| Trigger | SQS event source mapping, `dealio-{env}-db-update` queue, `batch_size=1` |
| Timeout | 30 s |
| Idempotency | `UPDATE ... WHERE current_price = old_price` — duplicate message is a no-op (rowcount=0) |
| Failure strategy | Unhandled exception → SQS visibility timeout expires → message requeued. After `maxReceiveCount` (default 3) retries → `dealio-{env}-db-update-dlq` |
| SLA | Must complete within SQS visibility timeout (default 90 s; Lambda timeout 30 s) |

#### Email Lambda (Consumer — `PriceDropMessage`)

| Attribute | Value |
|---|---|
| Trigger | SQS event source mapping, `dealio-{env}-email` queue, `batch_size=1` |
| Timeout | 30 s |
| Idempotency | Not guaranteed — duplicate SQS delivery may produce duplicate email. Accepted at MVP. |
| Failure strategy | SES error → Lambda raises → SQS retry. After `maxReceiveCount` retries → `dealio-{env}-email-dlq`. DB-Update is unaffected (separate queue). |

### 3.4 `correlation_id` Propagation

| Stage | Generated / Source | Forwarded to |
|---|---|---|
| Monitor | `uuid.uuid4()` in `SQLAlchemyTrackedProductReadAdapter` | Every `ProductPriceCheckRequestedDetail.correlation_id` |
| Scraper | `raw_event["detail"]["correlation_id"]` → `ScraperEventPayload.correlation_id` | `PriceDropSNSMessage.correlation_id`; failure log; all log entries |
| DB-Update | `body["correlation_id"]` → `PriceDropSQSMessage.correlation_id` | All log entries; `write_success` |
| Email | `body["correlation_id"]` → `EmailAlertPayload.correlation_id` | All log entries |

Bind at handler entry:
```python
bound_log = log.bind(
    correlation_id=str(event.correlation_id),
    tracked_product_id=str(event.tracked_product_id),
    stage="scraper",  # one of: monitor | scraper | db_update | email
)
```

CloudWatch Logs Insights cross-stage query:
```
filter correlation_id = "..."
| fields @timestamp, stage, @message
| sort @timestamp asc
```

### 3.5 Structured Log Event Key Catalogue

All log events use `structlog` JSON renderer. Convention: `snake_case.dot.namespaced`.

| Stage | Event Key | Level | Required Bound Fields |
|---|---|---|---|
| Monitor | `monitor.fan_out.no_products` | INFO | `correlation_id`, `stage` |
| Monitor | `monitor.fan_out.started` | INFO | `correlation_id`, `stage`, `product_count` |
| Monitor | `monitor.fan_out.complete` | INFO | `correlation_id`, `stage`, `product_count` |
| Scraper | `scraper.scrape.started` | INFO | `correlation_id`, `tracked_product_id`, `stage` |
| Scraper | `scraper.scrape.failure` | WARNING | `correlation_id`, `tracked_product_id`, `stage`, `error_type` |
| Scraper | `scraper.price_drop.detected` | INFO | `correlation_id`, `tracked_product_id`, `stage`, `user_id` |
| Scraper | `scraper.scrape.no_price_drop` | INFO | `correlation_id`, `tracked_product_id`, `stage` |
| DB-Update | `db_update.persist.started` | INFO | `correlation_id`, `tracked_product_id`, `stage` |
| DB-Update | `db_update.conditional_write.skipped` | INFO | `correlation_id`, `tracked_product_id`, `stage` |
| DB-Update | `db_update.persist.complete` | INFO | `correlation_id`, `tracked_product_id`, `stage` |
| Email | `email.alert.sending` | INFO | `correlation_id`, `user_id`, `stage` |
| Email | `email.alert.sent` | INFO | `correlation_id`, `user_id`, `stage` |

### 3.6 PII Policy

`user_email` is present in all event payloads (required for delivery). It is **forbidden** in any log field value.

| `user_email` IS permitted | `user_email` FORBIDDEN |
|---|---|
| EventBridge event payload | Any `structlog` log call field |
| SNS message body | CloudWatch metric dimensions |
| SQS message body | DLQ message attributes |
| `EmailAlertPayload.to_email` (in-memory) | Exception messages / error strings |
| SES API `Destination.ToAddresses` | |

Enforcement: CI grep for `user_email` in `log.info`, `log.warning`, `log.error`, `log.debug` calls.

### 3.7 Schema Versioning

No formal schema registry at MVP. Version is implicit in `DetailType` string.

- **Additive changes:** backward compatible; add with `default=None`; use `extra="ignore"` on Pydantic models (see §5.1)
- **Breaking changes:** new `DetailType` (e.g., `"ProductPriceCheckRequestedV2"`); Monitor publishes both versions in parallel during migration window

---

## 4. Infrastructure

### 4.1 Architecture Decision Records

| ADR | Decision | Status |
|---|---|---|
| ADR-001 | Single Pulumi stack (`pipeline`) for all 4 Lambdas | Accepted |
| ADR-002 | EventBridge Custom Bus for fan-out (not SQS direct trigger or Step Functions) | Accepted |
| ADR-003 | SNS Topic → 2× SQS fan-out for price-drop; each consumer has its own queue and DLQ | Accepted |
| ADR-004 | CloudWatch alarms: Lambda `Errors` metric math + DLQ depth on both DLQs | Accepted |
| ADR-005 | Resource naming: `dealio-{env}-{suffix}` where `env` = Pulumi stack name | Accepted |
| ADR-006 | Lambda package: Docker image vs zip — deferred; compatible with either | Decision Deferred |

### 4.2 Component Inventory (34 resources)

| # | Resource | Pulumi Type | AWS Name |
|---|---|---|---|
| 1-2 | Monitor IAM Role + Policy | `aws.iam.Role` + `aws.iam.RolePolicy` | `dealio-{env}-monitor-role` |
| 3-4 | Scraper IAM Role + Policy | `aws.iam.Role` + `aws.iam.RolePolicy` | `dealio-{env}-scraper-role` |
| 5-6 | DB-Update IAM Role + Policy | `aws.iam.Role` + `aws.iam.RolePolicy` | `dealio-{env}-db-update-role` |
| 7-8 | Email IAM Role + Policy | `aws.iam.Role` + `aws.iam.RolePolicy` | `dealio-{env}-email-role` |
| 9-10 | Scheduler IAM Role + Policy | `aws.iam.Role` + `aws.iam.RolePolicy` | `dealio-{env}-scheduler-role` |
| 11 | EventBridge Custom Bus | `aws.cloudwatch.EventBus` | `dealio-{env}-pipeline` |
| 12 | EventBridge Scheduler Rule | `aws.scheduler.Schedule` | `dealio-{env}-monitor-schedule` |
| 13 | EventBridge Rule (bus) | `aws.cloudwatch.EventRule` | `dealio-{env}-scraper-rule` |
| 14 | EventBridge Rule Target | `aws.cloudwatch.EventTarget` | — |
| 15 | Lambda Permission (EB→Scraper) | `aws.lambda_.Permission` | — |
| 16 | Lambda Permission (Scheduler→Monitor) | `aws.lambda_.Permission` | — |
| 17 | SNS Topic | `aws.sns.Topic` | `dealio-{env}-price-drop` |
| 18 | SQS DLQ (db-update) | `aws.sqs.Queue` | `dealio-{env}-db-update-dlq` |
| 19 | SQS DLQ (email) | `aws.sqs.Queue` | `dealio-{env}-email-dlq` |
| 20 | SQS Queue (db-update) | `aws.sqs.Queue` | `dealio-{env}-db-update` |
| 21 | SQS Queue (email) | `aws.sqs.Queue` | `dealio-{env}-email` |
| 22-23 | SQS Queue Policies | `aws.sqs.QueuePolicy` | — |
| 24-25 | SNS Subscriptions (raw_message_delivery=False) | `aws.sns.TopicSubscription` | — |
| 26 | Lambda: Monitor | `aws.lambda_.Function` | `dealio-{env}-monitor` |
| 27 | Lambda: Scraper | `aws.lambda_.Function` | `dealio-{env}-scraper` |
| 28 | Lambda: DB-Update | `aws.lambda_.Function` | `dealio-{env}-db-update` |
| 29 | Lambda: Email | `aws.lambda_.Function` | `dealio-{env}-email` |
| 30 | SQS ESM (db-update) | `aws.lambda_.EventSourceMapping` | — |
| 31 | SQS ESM (email) | `aws.lambda_.EventSourceMapping` | — |
| 32 | CW Alarm: Scraper Error Rate | `aws.cloudwatch.MetricAlarm` | `dealio-{env}-scraper-errors` |
| 33 | CW Alarm: DB-Update DLQ Depth | `aws.cloudwatch.MetricAlarm` | `dealio-{env}-db-update-dlq-depth` |
| 34 | CW Alarm: Email DLQ Depth | `aws.cloudwatch.MetricAlarm` | `dealio-{env}-email-dlq-depth` |

### 4.3 Lambda Configuration

| Lambda | Memory (default) | Timeout (default) | Handler String |
|---|---|---|---|
| Monitor | 256 MB | 300 s | `main_monitor.handler` |
| Scraper | 512 MB | **60 s** (NFR-2) | `main_scraper.handler` |
| DB-Update | 256 MB | 30 s | `main_db_update.handler` |
| Email | 256 MB | 30 s | `main_email.handler` |

SQS queues: `visibility_timeout_seconds` must be ≥ Lambda timeout. DB-Update default: 90 s. Email default: 60 s.

### 4.4 IAM Policies

All Lambda roles trust `lambda.amazonaws.com` + `AWSLambdaBasicExecutionRole` managed policy.

**Monitor:** `events:PutEvents` on `dealio-{env}-pipeline` bus + `secretsmanager:GetSecretValue` for DB URL.

**Scraper:** `sns:Publish` on `dealio-{env}-price-drop` topic + `secretsmanager:GetSecretValue` for DB URL + LLM API key.

**DB-Update:** `sqs:ReceiveMessage`, `sqs:DeleteMessage`, `sqs:GetQueueAttributes` on `dealio-{env}-db-update` + DB URL secret.

**Email:** `sqs:ReceiveMessage`, `sqs:DeleteMessage`, `sqs:GetQueueAttributes` on `dealio-{env}-email` + `ses:SendEmail` (Resource: `*`).

**Scheduler:** Trusts `scheduler.amazonaws.com` + `lambda:InvokeFunction` on `dealio-{env}-monitor`.

### 4.5 Lambda Environment Variables

| Lambda | Env Var | Source |
|---|---|---|
| Monitor | `DATABASE_URL` | `pipeline:database_url` (secret) |
| Monitor | `EVENTBRIDGE_BUS_NAME` | Output of `pipeline-bus.name` (resource output, not config) |
| Monitor | `AWS_REGION` | `pipeline:aws_region` |
| Scraper | `DATABASE_URL` | `pipeline:database_url` (secret) |
| Scraper | `SNS_PRICE_DROP_TOPIC_ARN` | Output of `price-drop-topic.arn` |
| Scraper | `LLM_PROVIDER`, `LLM_API_KEY`, `LLM_MODEL` | `pipeline:llm_*` config |
| Scraper | `AWS_REGION` | `pipeline:aws_region` |
| DB-Update | `DATABASE_URL` | `pipeline:database_url` (secret) |
| DB-Update | `AWS_REGION` | `pipeline:aws_region` |
| Email | `SES_FROM_ADDRESS` | `pipeline:ses_from_address` |
| Email | `AWS_REGION` | `pipeline:aws_region` |

Email Lambda: **no `DATABASE_URL`** — no DB access.

### 4.6 Configuration Schema

**Required (no defaults):**

| Key | Type |
|---|---|
| `pipeline:database_url` | string (secret) |
| `pipeline:llm_api_key` | string (secret) |
| `pipeline:ses_from_address` | string |
| `pipeline:aws_account_id` | string |
| `pipeline:aws_region` | string |

**Optional (with defaults):** `schedule_expression` (`"rate(1 hour)"`), `llm_provider` (`"gemini"`), `llm_model` (`"gemini-2.5-flash"`), Lambda memory/timeout per function, SQS visibility timeout/maxReceiveCount, `sqs_batch_size` (`1`), `scraper_error_rate_threshold` (`0.2`), `message_retention_seconds` (`1209600`).

### 4.7 CloudWatch Alarms

1. **Scraper error rate** — MetricMath: `Errors / Invocations > 0.2` on `dealio-{env}-scraper`. Evaluation: 1 period × 5 minutes.
2. **DB-Update DLQ depth** — `ApproximateNumberOfMessagesVisible > 0` on `dealio-{env}-db-update-dlq`.
3. **Email DLQ depth** — `ApproximateNumberOfMessagesVisible > 0` on `dealio-{env}-email-dlq`.

---

## 5. Cross-Cutting Design Decisions

### 5.1 Pydantic `extra` Config — Resolution Required

**Issue:** `lld-event.md` specifies `extra="forbid"` on Pydantic contract models; `lld-code.md` omits `extra`. These are inconsistent.

**Resolution:** Set `extra="ignore"` on **all** Pydantic contract models (`ProductPriceCheckRequestedDetail`, `PriceDropSNSMessage`) before first production deployment. This allows additive schema evolution (new optional fields) without breaking consumers. `extra="forbid"` is appropriate only in test environments where strict contract enforcement is desired.

### 5.2 `correlation_id` Generation Location — Resolution Required

**Issue:** `lld-code.md` §3.5 shows `correlation_id` generated inside the adapter (`SQLAlchemyTrackedProductReadAdapter`). The notes in §3.4 say the preferred approach is to generate in `fan_out_flow` and pass to the adapter. These are inconsistent.

**Resolution:** Generate `correlation_id` **in `fan_out_flow`**, pass it to `publish_batch`. This keeps adapters stateless and makes `fan_out_flow` the single source of truth for the cycle-scoped UUID. The adapter's `list_all_for_fan_out` signature does **not** generate a UUID — the flow passes it through.

Updated flow signature:
```python
async def fan_out_flow(*, product_read_port, eventbridge_port) -> None:
    correlation_id = uuid.uuid4()
    products = await product_read_port.list_all_for_fan_out(correlation_id=correlation_id)
    ...
```

Updated port signature:
```python
class TrackedProductReadPort(Protocol):
    async def list_all_for_fan_out(self, correlation_id: uuid.UUID) -> list[ProductFanOutPayload]: ...
```

### 5.3 DB-Update Transaction Rollback Guarantee

If `create_notification` or `write_success` raises after `conditional_update_price` returns `True`, the `AsyncSession` context manager rolls back. The handler **must not** call `session.commit()` in an except block. SQS redelivers the message; the next delivery re-enters with `current_price == old_price`, retrying the full transaction cleanly.

### 5.4 ORM Duplication

`tracked_products`, `notifications`, `price_check_log` ORM records are defined in three places:
- `services/webapp/webapp/...` (WebappBase)
- `services/monitor_lambda/monitor_lambda/...` (MonitorBase)
- `services/pipeline/pipeline/shared/orm/` (PipelineBase — this design)

This is accepted technical debt. When a fourth consumer appears, extract to `libs/lib-schemas/` and migrate all three consumers.

### 5.5 `pyproject.toml` — uv Workspace Registration

Add to root `pyproject.toml` `[tool.uv.workspace]`:
```toml
[tool.uv.workspace]
members = [
    "services/webapp",
    "services/monitor_lambda",
    "services/pipeline",   # ADD
]
```

---

## 6. Full Structural Mapping

All files are `[new]` — no existing files are modified.

| Component | Path |
|---|---|
| `Settings` | `pipeline/shared/infrastructure/settings.py` |
| `make_engine`, `make_session` | `pipeline/shared/infrastructure/database.py` |
| `configure_logger` | `pipeline/shared/infrastructure/logger.py` |
| `scraper_domain/` (copy) | `pipeline/shared/scraper_domain/` |
| `PipelineBase` | `pipeline/shared/orm/base.py` |
| `UserRecord` | `pipeline/shared/orm/user_record.py` |
| `TrackedProductRecord` | `pipeline/shared/orm/tracked_product_record.py` |
| `NotificationRecord` | `pipeline/shared/orm/notification_record.py` |
| `PriceCheckLogRecord` | `pipeline/shared/orm/price_check_log_record.py` |
| `ProductFanOutPayload` | `pipeline/domains/monitor/models/domain/product_fan_out_payload.py` |
| `ProductPriceCheckRequestedDetail` | `pipeline/domains/monitor/models/contracts/events/product_price_check_requested.py` |
| `TrackedProductReadPort` | `pipeline/domains/monitor/ports/tracked_product_read_port.py` |
| `EventBridgePublishPort` | `pipeline/domains/monitor/ports/eventbridge_publish_port.py` |
| `fan_out_flow` | `pipeline/domains/monitor/flows/fan_out_flow.py` |
| `SQLAlchemyTrackedProductReadAdapter` | `pipeline/domains/monitor/adapters/sqlalchemy_tracked_product_read_adapter.py` |
| `EventBridgePublishAdapter` | `pipeline/domains/monitor/adapters/eventbridge_publish_adapter.py` |
| Monitor handler | `pipeline/domains/monitor/jobs/handler.py` |
| `ScraperEventPayload` | `pipeline/domains/scraper/models/domain/scraper_event_payload.py` |
| `PriceDropMessage` | `pipeline/domains/scraper/models/domain/price_drop_message.py` |
| `PriceDropSNSMessage` | `pipeline/domains/scraper/models/contracts/events/price_drop_sns_message.py` |
| `SNSPublishPort` | `pipeline/domains/scraper/ports/sns_publish_port.py` |
| Scraper `PriceCheckLogWritePort` | `pipeline/domains/scraper/ports/price_check_log_write_port.py` |
| `scrape_dispatch_flow` | `pipeline/domains/scraper/flows/scrape_dispatch_flow.py` |
| `SNSPublishAdapter` | `pipeline/domains/scraper/adapters/sns_publish_adapter.py` |
| `SQLAlchemyFailureLogAdapter` | `pipeline/domains/scraper/adapters/sqlalchemy_failure_log_adapter.py` |
| Scraper handler | `pipeline/domains/scraper/jobs/handler.py` |
| `PriceDropSQSMessage` | `pipeline/domains/db_update/models/domain/price_drop_sqs_message.py` |
| `TrackedProductWritePort` | `pipeline/domains/db_update/ports/tracked_product_write_port.py` |
| `NotificationWritePort` | `pipeline/domains/db_update/ports/notification_write_port.py` |
| DB-Update `PriceCheckLogWritePort` | `pipeline/domains/db_update/ports/price_check_log_write_port.py` |
| `persist_price_drop_flow` | `pipeline/domains/db_update/flows/persist_price_drop_flow.py` |
| `SQLAlchemyPriceDropPersistenceAdapter` | `pipeline/domains/db_update/adapters/sqlalchemy_price_drop_persistence_adapter.py` |
| DB-Update handler | `pipeline/domains/db_update/jobs/handler.py` |
| `EmailAlertPayload` | `pipeline/domains/email/models/domain/email_alert_payload.py` |
| `EmailSenderPort` | `pipeline/domains/email/ports/email_sender_port.py` |
| `send_alert_flow` | `pipeline/domains/email/flows/send_alert_flow.py` |
| `SESEmailSenderAdapter` | `pipeline/domains/email/adapters/ses_email_sender.py` |
| Email handler | `pipeline/domains/email/jobs/handler.py` |
| `main_monitor.py` | `services/pipeline/main_monitor.py` |
| `main_scraper.py` | `services/pipeline/main_scraper.py` |
| `main_db_update.py` | `services/pipeline/main_db_update.py` |
| `main_email.py` | `services/pipeline/main_email.py` |
| Pulumi entry point | `infra/pipeline/__main__.py` |
| Pulumi IAM components | `infra/pipeline/components/iam.py` |
| Pulumi messaging components | `infra/pipeline/components/messaging.py` |
| Pulumi Lambda components | `infra/pipeline/components/lambdas.py` |
