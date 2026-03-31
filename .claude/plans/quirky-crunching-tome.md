# Plan: Task 1 — Pipeline Foundation

## Context

This implements the foundational scaffold for the new `services/pipeline/` uv workspace member as defined in `docs/designs/2026/003-event-driven-price-check-pipeline/tasks/001-foundation.md`. The pipeline package will house four Lambda stages (monitor, scraper, db_update, email) in a single uv package. This task creates the package structure, shared infrastructure (Settings, DB engine, logger), ORM models, and a verbatim copy of the scraper domain. Nothing else in the pipeline can be built until this exists.

---

## Critical Files

| File | Action | Notes |
|------|--------|-------|
| `pyproject.toml` (root) | Modify | Add `"services/pipeline"` to `[tool.uv.workspace].members` |
| `services/pipeline/pyproject.toml` | Create | New workspace member |
| `services/pipeline/pipeline/shared/infrastructure/settings.py` | Create | 8-field frozen dataclass with `os.environ.get` |
| `services/pipeline/pipeline/shared/infrastructure/database.py` | Create | `make_engine` / `make_session` |
| `services/pipeline/pipeline/shared/infrastructure/logger.py` | Create | `configure_logger()` with structlog JSON renderer |
| `services/pipeline/pipeline/shared/orm/base.py` | Create | `PipelineBase(DeclarativeBase)` |
| `services/pipeline/pipeline/shared/orm/*.py` | Create | 4 ORM model files mirroring physical schema |
| `services/pipeline/pipeline/shared/scraper_domain/` | Create | Full copy of `monitor_lambda/monitor_lambda/domains/scraper/` with updated imports |
| `services/pipeline/main_*.py` | Create | 4 bootstrap scripts |

---

## Reuse / Patterns to Mirror

- **Settings pattern:** Mirror `services/monitor_lambda/monitor_lambda/infrastructure/settings.py` but use `field(default_factory=lambda: os.environ.get("VAR", "default"))` for all 8 fields (task spec requirement; env var overrides needed for Lambda deployment).
- **DeclarativeBase pattern:** Mirror `MonitorBase` in `services/monitor_lambda/monitor_lambda/infrastructure/database/base.py` — just `class PipelineBase(DeclarativeBase): pass`.
- **ORM model patterns:** Mirror the existing persistence records in `monitor_lambda` and `webapp` exactly — same column types, constraints, field names. Key models to mirror:
  - `UserRecord` → from `webapp/domains/identity/models/persistence/user_record.py`
  - `TrackedProductRecord` → from `webapp/domains/tracker/models/persistence/tracked_product_record.py`
  - `NotificationRecord` → from `monitor_lambda/domains/monitor/models/persistence/notification_record.py`
  - `PriceCheckLogRecord` → from `monitor_lambda/domains/monitor/models/persistence/price_check_log_record.py`
- **structlog pattern:** Monitor lambda uses `structlog.get_logger(__name__)` with `dot.namespaced` event keys. `configure_logger()` should configure the same JSON renderer pattern.

---

## Implementation Steps

### 1. Root pyproject.toml — add pipeline to workspace members

In `pyproject.toml` (root), change:
```toml
[tool.uv.workspace]
members = [
    "services/monitor_lambda",
    "services/webapp",
]
```
to:
```toml
[tool.uv.workspace]
members = [
    "services/monitor_lambda",
    "services/webapp",
    "services/pipeline",
]
```

### 2. Create `services/pipeline/pyproject.toml`

```toml
[project]
name = "pipeline"
version = "0.1.0"
description = "Event-driven price check pipeline Lambdas"
readme = "README.md"
requires-python = ">=3.13"
dependencies = [
    "sqlalchemy[asyncio]>=2.0",
    "asyncpg>=0.29",
    "pydantic>=2.0",
    "structlog>=24.0",
    "boto3>=1.34",
    "google-generativeai>=0.8",
    "openai>=1.0",
    "httpx>=0.27",
    "beautifulsoup4>=4.12",
    "lxml>=5.0",
]
```

### 3. Package skeleton — all `__init__.py` stubs

Create empty `__init__.py` files at:
- `services/pipeline/pipeline/__init__.py`
- `services/pipeline/pipeline/domains/__init__.py`
- `services/pipeline/pipeline/domains/monitor/__init__.py`
- `services/pipeline/pipeline/domains/scraper/__init__.py`
- `services/pipeline/pipeline/domains/db_update/__init__.py`
- `services/pipeline/pipeline/domains/email/__init__.py`
- `services/pipeline/pipeline/shared/__init__.py`
- `services/pipeline/pipeline/shared/orm/__init__.py`
- `services/pipeline/pipeline/shared/infrastructure/__init__.py`

All `__init__.py` files: `from __future__ import annotations` only (or empty — task says stubs).

### 4. Settings (`pipeline/shared/infrastructure/settings.py`)

```python
from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Settings:
    database_url: str = field(
        default_factory=lambda: os.environ.get(
            "DATABASE_URL",
            "postgresql+asyncpg://dealio:dealio@localhost:5433/dealio?ssl=disable",
        )
    )
    aws_region: str = field(default_factory=lambda: os.environ.get("AWS_REGION", "us-east-1"))
    eventbridge_bus_name: str = field(
        default_factory=lambda: os.environ.get("EVENTBRIDGE_BUS_NAME", "dealio-pipeline")
    )
    sns_price_drop_topic_arn: str = field(
        default_factory=lambda: os.environ.get("SNS_PRICE_DROP_TOPIC_ARN", "")
    )
    ses_from_address: str = field(default_factory=lambda: os.environ.get("SES_FROM_ADDRESS", ""))
    llm_provider: str = field(default_factory=lambda: os.environ.get("LLM_PROVIDER", "gemini"))
    llm_api_key: str = field(default_factory=lambda: os.environ.get("LLM_API_KEY", ""))
    llm_model: str = field(default_factory=lambda: os.environ.get("LLM_MODEL", "gemini-2.5-flash"))
```

### 5. Database (`pipeline/shared/infrastructure/database.py`)

```python
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine


def make_engine(database_url: str) -> AsyncEngine:
    return create_async_engine(database_url, pool_pre_ping=True)


def make_session(engine: AsyncEngine) -> AsyncSession:
    return AsyncSession(engine, expire_on_commit=False)
```

### 6. Logger (`pipeline/shared/infrastructure/logger.py`)

```python
from __future__ import annotations

import structlog


def configure_logger() -> None:
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.BoundLogger,
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
    )
```

### 7. ORM base (`pipeline/shared/orm/base.py`)

```python
from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class PipelineBase(DeclarativeBase):
    """Declarative base for all pipeline ORM models."""
```

### 8. ORM models

All 4 files in `pipeline/shared/orm/`. Mirror exactly from source tables — same column types, same constraints, same field names. Import base from `pipeline.shared.orm.base`.

**`user_record.py`** — maps `users` table (same as `WebappBase` version but using `PipelineBase`; include id, email, password_hash, google_sub, created_at, updated_at)

**`tracked_product_record.py`** — maps `tracked_products` (id, user_id FK, url, product_name, current_price, previous_price, last_checked_at, created_at)

**`notification_record.py`** — maps `notifications` (id, user_id FK, tracked_product_id FK, old_price, new_price, created_at, read_at). `default=uuid.uuid4` on PK.

**`price_check_log_record.py`** — maps `price_check_log` (id, tracked_product_id FK, checked_at, result String(10), retry_count SmallInteger, error_message). `default=uuid.uuid4` on PK.

Note: No `__table_args__` constraints needed on PipelineBase models (read-only access pattern; constraints owned by alembic/webapp).

### 9. Scraper domain copy

Copy all files from `services/monitor_lambda/monitor_lambda/domains/scraper/` → `services/pipeline/pipeline/shared/scraper_domain/`.

Files to copy and update imports:
- `__init__.py` — add copy notice comment
- `exceptions.py` — no import changes needed
- `ports/llm_client.py` — change `from monitor_lambda.domains.scraper.models.domain...` → `from pipeline.shared.scraper_domain.models.domain...`
- `adapters/gemini_llm_client.py` — change `from monitor_lambda.domains.scraper.adapters.openai_llm_client import _LLMResponse` → `from pipeline.shared.scraper_domain.adapters.openai_llm_client import _LLMResponse`; change other `monitor_lambda.domains.scraper.*` imports
- `adapters/openai_llm_client.py` — change `monitor_lambda.domains.scraper.*` imports
- `models/domain/llm_extraction_result.py` — no local imports to change
- `models/domain/scraper_result.py` — no local imports to change
- `flows/scrape_flow.py` — change all `from monitor_lambda.domains.scraper.*` → `from pipeline.shared.scraper_domain.*`
- `flows/fetch_page.py` — change imports
- `flows/preprocess_html.py` — change imports
- `flows/extract_name.py` — change imports
- `flows/extract_price.py` — change imports
- `flows/classify_response.py` — change imports
- `jobs/handler.py` — change imports

Import replacement rule: `monitor_lambda.domains.scraper` → `pipeline.shared.scraper_domain`

Add to `scraper_domain/__init__.py`:
```python
# This is a verbatim copy of services/monitor_lambda/monitor_lambda/domains/scraper/.
# Any changes to monitor_lambda's scraper logic must be manually mirrored here.
# Future: extract to libs/lib-scraper when a third consumer appears.
```

### 10. Bootstrap scripts (4 files at `services/pipeline/`)

Each contains only a re-export of `handler`:
```python
# main_monitor.py
from __future__ import annotations
from pipeline.domains.monitor.jobs.handler import handler  # noqa: F401
```
(repeat pattern for scraper, db_update, email)

---

## Import Mapping for Scraper Copy

All occurrences of `monitor_lambda.domains.scraper` in copied files → `pipeline.shared.scraper_domain`

Confirmed cross-file import in gemini_llm_client.py:
- `from monitor_lambda.domains.scraper.adapters.openai_llm_client import _LLMResponse` → `from pipeline.shared.scraper_domain.adapters.openai_llm_client import _LLMResponse`

---

## Verification

```bash
cd services/pipeline

# Settings default values
uv run python -c "from pipeline.shared.infrastructure.settings import Settings; s = Settings(); print(s.aws_region)"
# Expected: us-east-1

# Database imports
uv run python -c "from pipeline.shared.infrastructure.database import make_engine, make_session; print('ok')"
# Expected: ok

# ORM model
uv run python -c "from pipeline.shared.orm.tracked_product_record import TrackedProductRecord; print(TrackedProductRecord.__tablename__)"
# Expected: tracked_products

# Scraper domain
uv run python -c "from pipeline.shared.scraper_domain.flows.scrape_flow import scrape_flow; print('ok')"
# Expected: ok

# Bootstrap
uv run python -c "from main_monitor import handler; print('ok')"
# Expected: ok (after domain stub handler is created)

# Root workspace sync
cd ../..
uv sync
# Expected: resolves without errors; pipeline listed
```

Note: `main_monitor` bootstrap verification requires a stub `handler` in `pipeline/domains/monitor/jobs/handler.py`. Create a minimal stub:
```python
from __future__ import annotations
from typing import Any
def handler(event: dict[str, Any], context: object) -> dict[str, Any]:
    return {}
```
(repeat for scraper, db_update, email domains)

---

## Invariants to Enforce

- Every `.py` file starts with `from __future__ import annotations`
- `PipelineBase` never imported by `webapp` or `monitor_lambda`
- `pipeline/shared/scraper_domain/` contains zero references to `monitor_lambda.*`
- Bootstrap scripts contain only re-export — no business logic
