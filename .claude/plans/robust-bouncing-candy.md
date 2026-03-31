# Implementation Plan — T-1: Project Scaffolding

## Context

This is the first implementation task for the **Price Drop Tracker** feature (`001-price-drop-tracker`).
The `services/` directory does not yet exist — this is a greenfield scaffolding task.
Goal: produce three importable Python packages (webapp, monitor_lambda, scraper_lambda) with correct
structure, dependency manifests, stubs, and Alembic configuration so that subsequent tasks (T-2+)
have foundations to build on.

**Feature directory:** `docs/designs/2026/001-price-drop-tracker/`
**Task file:** `docs/designs/2026/001-price-drop-tracker/tasks/001-project-scaffolding.md`
**Task complexity:** S (small) — no dependencies, parallelizable with nothing

---

## Phase Gate

- `tasks-breakdown.md` exists ✅
- T-1 has no hard dependencies ✅

---

## Skills to Invoke

| Skill | Reason |
|-------|--------|
| `implement-python` | All code is Python 3.13+; enforces `src` layout, uv packaging, strict typing |
| `implement-pydantic` | `config.py` uses `pydantic-settings` (`BaseSettings`) with field constraints |

---

## Agent Team

**Single agent** — T-1 is S-complexity. The three services are independent, but the work in each
is trivial (a few files per service). Multi-instance dispatch overhead is not justified here.

| Agent | Type | Scoped Action |
|-------|------|---------------|
| `python-implementer` | `python-implementer` | Create all three service directory trees, write pyproject.toml for each, write webapp stubs (config.py, main.py, dependencies.py), initialize and configure Alembic for webapp, write Lambda handler stubs, write monitor_lambda DB base |

---

## Files to Create

### `services/webapp/`

```
services/webapp/
  webapp/
    __init__.py
    config.py          ← Settings(BaseSettings) with all required fields
    main.py            ← bare FastAPI() app instance
    dependencies.py    ← empty module (placeholder)
    domains/
      identity/
        __init__.py
        exceptions.py
        routes/v1/__init__.py
        flows/__init__.py
        ports/__init__.py
        adapters/__init__.py
        models/
          __init__.py
          domain/__init__.py
          contracts/api/__init__.py
          persistence/__init__.py
      tracker/
        __init__.py
        exceptions.py
        routes/v1/__init__.py
        flows/__init__.py
        ports/__init__.py
        adapters/__init__.py
        models/
          __init__.py
          domain/__init__.py
          contracts/api/__init__.py
          persistence/__init__.py
      notifier/
        __init__.py
        ports/__init__.py
        adapters/__init__.py
        models/
          __init__.py
          domain/__init__.py
          persistence/__init__.py
      scraper_client/
        __init__.py
        ports/__init__.py
        adapters/__init__.py
        models/
          __init__.py
          domain/__init__.py
    models/
      __init__.py
      contracts/
        __init__.py
        api/
          __init__.py
          errors.py    ← placeholder error response model
  alembic/
    env.py             ← async engine configured with asyncpg + Settings.database_url
    versions/          ← empty dir (0001_initial_schema.py written in T-4)
  alembic.ini          ← script_location = alembic, database_url read from Settings
  pyproject.toml       ← name=webapp, deps: fastapi, uvicorn, sqlalchemy[asyncio], asyncpg,
                         alembic, pydantic[email], pydantic-settings, authlib,
                         python-jose[cryptography], passlib[bcrypt], httpx, boto3, structlog
```

### `services/monitor_lambda/`

```
services/monitor_lambda/
  monitor_lambda/
    __init__.py
    domains/
      monitor/
        __init__.py
        exceptions.py
        jobs/
          __init__.py
          handler.py   ← def handler(event, context): pass
        flows/__init__.py
        ports/__init__.py
        adapters/__init__.py
        models/
          __init__.py
          domain/__init__.py
    infrastructure/
      __init__.py
      database/
        __init__.py
        base.py        ← DeclarativeBase subclass (MonitorBase)
  pyproject.toml       ← name=monitor_lambda, deps: sqlalchemy[asyncio], asyncpg, boto3, structlog
```

### `services/scraper_lambda/`

```
services/scraper_lambda/
  scraper_lambda/
    __init__.py
    domains/
      scraper/
        __init__.py
        exceptions.py
        jobs/
          __init__.py
          handler.py   ← def handler(event, context): pass
        flows/__init__.py
        models/
          __init__.py
          domain/__init__.py
  pyproject.toml       ← name=scraper_lambda, deps: httpx, beautifulsoup4, lxml, structlog
```

---

## Key Implementation Notes

### pyproject.toml pattern (PEP 621, uv)
```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "{service-name}"
version = "0.1.0"
requires-python = ">=3.13"
dependencies = [...]

[tool.hatch.build.targets.wheel]
packages = ["{service-name}"]
```

### config.py pattern
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    jwt_secret: str
    aws_region: str = "us-east-1"
    scraper_lambda_name: str
    ses_from_address: str
    google_client_id: str
    google_client_secret: str
    google_redirect_uri: str

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

def get_settings() -> Settings:
    return Settings()
```

### alembic/env.py pattern (async asyncpg)
Configure with `run_migrations_offline()` and `run_migrations_online()` using
`AsyncEngine` from sqlalchemy.ext.asyncio. Read `database_url` from `Settings`.

### monitor_lambda/infrastructure/database/base.py
```python
from sqlalchemy.orm import DeclarativeBase

class MonitorBase(DeclarativeBase):
    pass
```

---

## Verification

After implementation, run the following to verify success:

```bash
# Verify webapp is importable
cd services/webapp && uv run python -c "import webapp; print('ok')"

# Verify scraper_lambda is importable
cd services/scraper_lambda && uv run python -c "import scraper_lambda; print('ok')"

# Verify monitor_lambda is importable
cd services/monitor_lambda && uv run python -c "import monitor_lambda; print('ok')"

# Verify Alembic is configured (should print current = None or empty)
cd services/webapp && uv run alembic current
```

All four commands must complete without errors.

---

## Definition of Done

- [ ] All three `pyproject.toml` files exist with correct names and dependencies
- [ ] All `__init__.py` files in every package directory
- [ ] `services/webapp/webapp/config.py` — `Settings(BaseSettings)` with all required fields
- [ ] `services/webapp/webapp/main.py` — bare `FastAPI()` instance
- [ ] `services/webapp/webapp/dependencies.py` — empty module
- [ ] `services/webapp/alembic/env.py` — async engine + asyncpg configured
- [ ] `services/webapp/alembic.ini` — points to `alembic/` dir, reads db url from Settings
- [ ] `services/monitor_lambda/monitor_lambda/domains/monitor/jobs/handler.py` — stub
- [ ] `services/scraper_lambda/scraper_lambda/domains/scraper/jobs/handler.py` — stub
- [ ] `services/monitor_lambda/monitor_lambda/infrastructure/database/base.py` — `MonitorBase`
- [ ] All four verification commands pass
