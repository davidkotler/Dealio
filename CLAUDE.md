# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What is Dealio

A price drop tracker application. Users add product URLs; the system periodically scrapes prices and sends email alerts when prices drop.

## Repository Layout

```
services/
  webapp/          # FastAPI backend (Python 3.13, async SQLAlchemy, PostgreSQL)
  monitor_lambda/  # AWS Lambda that runs the price-check cycle
  frontend/        # React 19 + TypeScript + Vite + Tailwind CSS
pyproject.toml     # uv workspace root (members: webapp, monitor_lambda)
```

## Commands

### Python (uv workspace)

```bash
# Install all dependencies
uv sync

# Run the webapp (from repo root or services/webapp/)
cd services/webapp && python main.py
# or: uvicorn webapp.main:app --host localhost --port 8001 --reload

# Run the monitor lambda locally
cd services/monitor_lambda && python check_lambda.py

# Database migrations (run from services/webapp/)
cd services/webapp
alembic upgrade head          # apply all migrations
alembic revision -m "name"    # create new migration
alembic downgrade -1           # rollback one step
```

### Frontend

```bash
cd services/frontend
npm install
npm run dev      # dev server (Vite, default port 5173)
npm run build    # production build
npm run lint     # ESLint
```

## Environment Variables

**`services/webapp/.env`** (see `webapp/config.py` for all fields):
- `DATABASE_URL` — PostgreSQL async URL (`postgresql+asyncpg://...`)
- `JWT_SECRET`
- `SCRAPER_LAMBDA_NAME`
- `SES_FROM_ADDRESS`
- `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI`
- `APP_BASE_URL`
- `AWS_REGION` (default: `us-east-1`)

**`services/monitor_lambda`** — reads from `Settings` dataclass defaults or environment:
- `DATABASE_URL`, `SES_FROM_ADDRESS`, `AWS_REGION`
- `LLM_PROVIDER` (default: `gemini`), `LLM_API_KEY`, `LLM_MODEL` (default: `gemini-2.5-flash`)

**`services/frontend/.env`** (copy from `.env.example`):
- `VITE_API_BASE_URL=http://localhost:8001`

## Architecture

### Domain Layer Pattern (Hexagonal / Ports & Adapters)

Both `webapp` and `monitor_lambda` use an identical internal structure per domain:

```
domains/<domain>/
  adapters/      # Concrete implementations of ports (SQLAlchemy repos, AWS clients, etc.)
  flows/         # Use-case orchestration — pure business logic, no I/O directly
  jobs/          # Entry points (Lambda handler or route handlers that wire flows)
  models/
    domain/      # Domain entities and value objects (dataclasses / Pydantic)
    contracts/   # API request/response schemas (Pydantic, under contracts/api/)
    persistence/ # SQLAlchemy ORM records
  ports/         # Abstract interfaces (Protocols) — the boundary between domain and infra
infrastructure/  # Shared DB engine setup, base ORM class
```

### webapp Domains

- **identity** — Registration, email/password login, Google OIDC, JWT session cookies, password reset via SES email
- **tracker** — Add/remove tracked products, dashboard, list/dismiss notifications; calls `scraper_client` on add
- **notifier** — Write-side for notifications (used by monitor lambda via DB); read-side lives in `tracker`
- **scraper_client** — Anti-corruption layer wrapping the scraper Lambda invocation

### monitor_lambda Domains

- **monitor** — Price-check cycle: loads all active tracked products, scrapes each concurrently (max 10), saves `PriceCheckLog`, updates prices, creates `Notification` records, sends SES email alerts on price drop
- **scraper** — The actual scraping logic: fetch page → classify response → preprocess HTML → LLM extraction (Gemini or OpenAI) → regex/CSS fallback

### Frontend

- **Routing**: React Router v7. `PublicOnlyRoute` redirects authenticated users away from auth pages; `PrivateRoute` guards app pages.
- **State**: Zustand for auth (`useAuthStore`, persisted to localStorage). React Query v5 for all server state (products, notifications).
- **API**: Axios client (`src/api/client.ts`) with `withCredentials: true` and a 401 interceptor that clears auth state and redirects to `/login`. Base URL from `VITE_API_BASE_URL`.
- **Forms**: React Hook Form + Zod schemas (in `src/schemas/`).
- **Path alias**: `@/` maps to `src/`.

### Database

PostgreSQL via async SQLAlchemy (asyncpg driver). Schema defined in `services/webapp/alembic/versions/0001_initial_schema.py`. Tables: `users`, `password_reset_tokens`, `tracked_products`, `notifications`, `price_check_log`. The webapp's `lifespan` creates tables on startup via `metadata.create_all` in addition to Alembic for development convenience.

### Key Design Rules (from project principles)

- **Flows are pure orchestration** — no I/O inside flows; all I/O goes through injected port interfaces
- **Ports are Protocols** — adapters implement ports; domains never import concrete adapters
- **Models are layered** — domain models ≠ persistence records ≠ API contracts; always translate between layers
- **Scraper result is a union type** — `ScraperSuccess | ScraperFailure`, never exceptions for expected failures
- **Full import paths** — always use absolute imports from the package root (e.g., `from webapp.domains.tracker.ports...`)
- **Structured logging** via `structlog` with event keys in `snake_case` using dot-separated namespacing (e.g., `price_check.price_drop_detected`)