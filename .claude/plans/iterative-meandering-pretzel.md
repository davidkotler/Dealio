# Plan: Task 6 — scraper_client ACL Adapter

## Context

T-6 implements the Anti-Corruption Layer adapter (`ScraperLambdaClient`) that invokes the Scraper Lambda via boto3 and translates the raw dict response into `ScraperResult` domain types with retry logic. This adapter is needed by both `webapp` (when a product URL is added, FR-5) and `monitor_lambda` (during price check cycles, FR-8). The adapter is intentionally duplicated — services are independently deployable with no shared lib.

**Critical prerequisite discovered:** The existing `scraper_result.py` models in both `webapp` and `monitor_lambda` are misaligned with the actual Lambda response format. They define `ScraperSuccess(url, price, currency)` and `ScraperErrorType` values like `NETWORK_ERROR`/`RATE_LIMITED` — but the Lambda returns `price`+`product_name` and uses `timeout`/`http_error`/`parse_error`/`blocked`. These models are unreferenced outside their own `__init__.py` files (zero downstream impact), so they must be corrected first.

---

## Design Target

| Service | Domain | Status | Layers Affected |
|---------|--------|--------|-----------------|
| webapp | scraper_client | existing | models/domain (update), adapters (new file) |
| monitor_lambda | monitor | existing | models/domain (update), adapters (new file) |

Sub-task 6.4 (add `ScraperPort` to webapp ports) is **already complete** — `scraper_port.py` exists and is correct.

---

## Implementation Steps

### Step 1 — Align webapp domain model
**File:** `services/webapp/webapp/domains/scraper_client/models/domain/scraper_result.py`

Replace current misaligned model with:
```python
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum


class ScraperErrorType(Enum):
    TIMEOUT = "timeout"
    HTTP_ERROR = "http_error"
    PARSE_ERROR = "parse_error"
    BLOCKED = "blocked"


@dataclass(frozen=True)
class ScraperSuccess:
    price: Decimal
    product_name: str


@dataclass(frozen=True)
class ScraperFailure:
    error_type: ScraperErrorType
    message: str
    status_code: int | None


ScraperResult = ScraperSuccess | ScraperFailure
```

### Step 2 — Align monitor_lambda domain model
**File:** `services/monitor_lambda/monitor_lambda/domains/monitor/models/domain/scraper_result.py`

Same content as Step 1, with comment `# Mirror of scraper_lambda's ScraperResult — no shared lib at MVP` preserved (add it back at top).

### Step 3 — Create webapp adapter
**File:** `services/webapp/webapp/domains/scraper_client/adapters/scraper_lambda_client.py`

```python
from __future__ import annotations

import asyncio
import json
from decimal import Decimal

import boto3

from webapp.domains.scraper_client.models.domain import (
    ScraperErrorType,
    ScraperFailure,
    ScraperResult,
    ScraperSuccess,
)

_RETRYABLE = {ScraperErrorType.TIMEOUT, ScraperErrorType.HTTP_ERROR}


class ScraperLambdaClient:
    def __init__(self, lambda_name: str, max_retries: int = 3) -> None:
        self._lambda_name = lambda_name
        self._max_retries = max_retries
        self._client = boto3.client("lambda")

    async def scrape(self, url: str) -> ScraperResult:
        attempt = 0
        last_result: ScraperFailure | None = None
        while attempt < self._max_retries:
            result = await self._invoke(url)
            if isinstance(result, ScraperSuccess):
                return result
            if result.error_type not in _RETRYABLE:
                return result
            last_result = result
            attempt += 1
            if attempt < self._max_retries:
                await asyncio.sleep(2 ** (attempt - 1))  # 1s, 2s
        return last_result  # type: ignore[return-value]

    async def _invoke(self, url: str) -> ScraperResult:
        try:
            response = await asyncio.to_thread(
                self._client.invoke,
                FunctionName=self._lambda_name,
                InvocationType="RequestResponse",
                Payload=json.dumps({"url": url}).encode(),
            )
            payload = json.loads(response["Payload"].read())
        except Exception as e:
            return ScraperFailure(
                error_type=ScraperErrorType.HTTP_ERROR,
                message=str(e),
                status_code=None,
            )
        if payload.get("status") == "success":
            return ScraperSuccess(
                price=Decimal(payload["price"]),
                product_name=payload["product_name"],
            )
        return ScraperFailure(
            error_type=ScraperErrorType(payload.get("error_type", "parse_error")),
            message=payload.get("message", "Unknown error"),
            status_code=payload.get("status_code"),
        )
```

**Notes:**
- `_RETRYABLE` uses `ScraperErrorType.TIMEOUT` / `ScraperErrorType.HTTP_ERROR` (enum members, not string values)
- `asyncio.to_thread` wraps the synchronous boto3 call to avoid blocking the event loop
- All exceptions caught → `ScraperFailure(HTTP_ERROR)` — never raises
- Retry delays: attempt 1→2: `2^0 = 1s`; attempt 2→3: `2^1 = 2s`

### Step 4 — Create monitor_lambda adapter
**File:** `services/monitor_lambda/monitor_lambda/domains/monitor/adapters/scraper_lambda_client.py`

Identical logic to Step 3, but imports from `monitor_lambda.domains.monitor.models.domain`.

```python
from __future__ import annotations

import asyncio
import json
from decimal import Decimal

import boto3

from monitor_lambda.domains.monitor.models.domain import (
    ScraperErrorType,
    ScraperFailure,
    ScraperResult,
    ScraperSuccess,
)

_RETRYABLE = {ScraperErrorType.TIMEOUT, ScraperErrorType.HTTP_ERROR}


class ScraperLambdaClient:
    # (identical body to webapp version)
    ...
```

The `lambda_name` comes from an environment variable (e.g., `os.environ["SCRAPER_LAMBDA_NAME"]`) injected at construction time — no `config.py` equivalent in monitor_lambda.

---

## Files to Modify / Create

| Action | File |
|--------|------|
| **Update** | `services/webapp/webapp/domains/scraper_client/models/domain/scraper_result.py` |
| **Update** | `services/monitor_lambda/monitor_lambda/domains/monitor/models/domain/scraper_result.py` |
| **Create** | `services/webapp/webapp/domains/scraper_client/adapters/scraper_lambda_client.py` |
| **Create** | `services/monitor_lambda/monitor_lambda/domains/monitor/adapters/scraper_lambda_client.py` |
| No change | `services/webapp/webapp/domains/scraper_client/ports/scraper_port.py` (already correct) |
| No change | `services/monitor_lambda/monitor_lambda/domains/monitor/ports/scraper_port.py` (already correct) |

---

## Quality Considerations

- **Testability:** boto3 client is stored as `self._client`; tests can `patch.object(client._client, "invoke", ...)` — matches task verification scripts
- **Robustness:** All exceptions caught in `_invoke`; `scrape()` never raises; retries bounded by `max_retries`
- **Async correctness:** `asyncio.to_thread` for boto3 (sync → async boundary); `asyncio.sleep` for backoff
- **No shared lib:** Duplication across services is intentional per architecture decision; models are isolated bounded contexts
- **Enum usage:** `_RETRYABLE` compares enum members (not string values) for type safety

---

## Verification

```bash
# From services/webapp:
cd services/webapp

# Happy path — success response
uv run python -c "
import asyncio, json
from unittest.mock import patch, MagicMock
from webapp.domains.scraper_client.adapters.scraper_lambda_client import ScraperLambdaClient
from webapp.domains.scraper_client.models.domain import ScraperSuccess

client = ScraperLambdaClient(lambda_name='test-scraper')
mock_response = {'Payload': MagicMock(read=lambda: json.dumps({'status': 'success', 'price': '99.99', 'product_name': 'Test Widget'}).encode())}

with patch.object(client._client, 'invoke', return_value=mock_response):
    result = asyncio.run(client.scrape('https://example.com/product'))

print(type(result).__name__, result.price, result.product_name)
# Expected: ScraperSuccess 99.99 Test Widget
"

# parse_error should NOT retry (only 1 invoke call)
uv run python -c "
import asyncio, json
from unittest.mock import patch, MagicMock
from webapp.domains.scraper_client.adapters.scraper_lambda_client import ScraperLambdaClient

client = ScraperLambdaClient(lambda_name='test-scraper', max_retries=3)
failure_payload = {'status': 'failure', 'error_type': 'parse_error', 'message': 'No price found', 'status_code': None}
mock_response = {'Payload': MagicMock(read=lambda: json.dumps(failure_payload).encode())}

with patch.object(client._client, 'invoke', return_value=mock_response) as mock_invoke:
    result = asyncio.run(client.scrape('https://example.com/product'))
    print('Invoke calls:', mock_invoke.call_count)  # Expected: 1
print(type(result).__name__, result.error_type)
# Expected: ScraperFailure ScraperErrorType.PARSE_ERROR
"
```
