# Plan: LLM-Based Price Extraction for scraper_lambda

## Context

The current `extract_price.py` uses a 3-level regex/CSS cascade (JSON-LD → meta tags → CSS selectors) which fails on sites with non-standard markup. The user wants to replace this with an LLM-based approach: fetch the page HTML, preprocess it, send to an LLM (OpenAI or Gemini), and parse structured JSON output for price + product name. The LLM provider must be swappable via environment config.

**Flow:** URL → fetch HTML → preprocess → LLM extract (price + name) → if LLM fails → cascade fallback → ScraperResult

---

## Design Summary

**Complexity:** Medium
**Design Depth:** Standard

### Design Target

| Service | Domain | Status | Layers Affected |
|---------|--------|--------|-----------------|
| scraper_lambda | scraper | existing | ports (new), adapters (new), flows (modified), infrastructure (new), jobs (modified) |

---

## File Changes

### New Files

```
services/scraper_lambda/scraper_lambda/
├── infrastructure/
│   ├── __init__.py
│   └── settings.py                          # Dataclass config (LLM_PROVIDER, LLM_API_KEY, LLM_MODEL)
└── domains/scraper/
    ├── ports/
    │   ├── __init__.py
    │   └── llm_client.py                    # LLMClient Protocol
    ├── adapters/
    │   ├── __init__.py
    │   ├── openai_llm_client.py             # OpenAI adapter
    │   └── gemini_llm_client.py             # Gemini adapter
    ├── flows/
    │   └── preprocess_html.py               # Pure fn: strip noise, truncate to 32k chars
    └── models/domain/
        └── llm_extraction_result.py         # Frozen dataclass: price: Decimal|None, product_name: str|None
```

### Modified Files

| File | Change |
|------|--------|
| `domains/scraper/flows/scrape_flow.py` | Inject `LLMClient`, add preprocess + LLM steps, cascade as fallback |
| `domains/scraper/jobs/handler.py` | Build `Settings()`, call `_build_llm_client()`, pass to `scrape_flow` |
| `domains/scraper/exceptions.py` | Add `LLMExtractionError` |
| `pyproject.toml` | Add `openai>=1.0`, `google-generativeai>=0.8`, `pydantic>=2.0` |

---

## Key Interfaces

### LLMClient Protocol (`ports/llm_client.py`)

```python
@runtime_checkable
class LLMClient(Protocol):
    async def extract_product_data(self, cleaned_html: str) -> LLMExtractionResult: ...
```

### LLMExtractionResult (`models/domain/llm_extraction_result.py`)

```python
@dataclass(frozen=True)
class LLMExtractionResult:
    price: Decimal | None
    product_name: str | None
```

### Settings (`infrastructure/settings.py`)

```python
@dataclass(frozen=True)
class Settings:
    llm_provider: str = field(default_factory=lambda: os.environ["LLM_PROVIDER"])
    llm_api_key: str  = field(default_factory=lambda: os.environ["LLM_API_KEY"])
    llm_model: str    = field(default_factory=lambda: os.environ.get("LLM_MODEL", ""))
```

- `LLM_PROVIDER`: `"openai"` or `"gemini"`
- `LLM_API_KEY`: required, never logged
- `LLM_MODEL`: optional — if empty, each adapter uses its own default (`gpt-4o-mini` / `gemini-2.0-flash`)

---

## Adapters

### OpenAI (`adapters/openai_llm_client.py`)

```python
@dataclass
class OpenAILLMClient:
    _api_key: str
    _model: str = "gpt-4o-mini"

    async def extract_product_data(self, cleaned_html: str) -> LLMExtractionResult: ...
```

- Uses `openai` SDK (`AsyncOpenAI`) — async-native, no `asyncio.to_thread` needed
- `temperature=0` for deterministic extraction
- 30s timeout
- Parses response JSON via a Pydantic model `_LLMResponse(price: str|None, product_name: str|None)`
- Converts `price` string → `Decimal`; non-numeric → `None`

### Gemini (`adapters/gemini_llm_client.py`)

```python
@dataclass
class GeminiLLMClient:
    _api_key: str
    _model: str = "gemini-2.0-flash"

    async def extract_product_data(self, cleaned_html: str) -> LLMExtractionResult: ...
```

- Uses `google-generativeai` SDK (sync) wrapped in `asyncio.to_thread()` — mirrors boto3 pattern in existing adapters
- `response_mime_type="application/json"` — native JSON mode, no markdown fence risk
- Same Pydantic parse + Decimal conversion

### Error mapping (both adapters)

| Error | Action |
|-------|--------|
| Auth / quota / network | `raise LLMExtractionError("...") from exc` |
| Invalid JSON response | return `LLMExtractionResult(None, None)` |
| Pydantic validation fail | return `LLMExtractionResult(None, None)` |
| Non-numeric price string | set `price=None` in result |

---

## LLM Prompt

**System:** Extract product price and name from HTML. Return ONLY valid JSON:
```json
{"price": "29.99 or null", "product_name": "string or null"}
```
Rules: primary current price only, no currency symbols, null if not found.

**User:** `{cleaned_html}`

---

## HTML Preprocessing (`flows/preprocess_html.py`)

Pure function, no I/O:
1. Parse with BeautifulSoup (lxml → html.parser fallback)
2. Decompose: `script`, `style`, `svg`, `canvas`, `header`, `footer`, `nav`, `aside`, HTML comments
3. Collapse whitespace
4. Truncate at `max_chars=32_000` (scan back to nearest `<` to avoid mid-tag cut)

---

## Updated scrape_flow.py

```
fetch_page(url)
  → ScraperFailure?  return
classify_response(response)
  → blocked/http_error?  return
preprocess_html(response.text)
  → cleaned: str
llm_client.extract_product_data(cleaned)
  → LLMExtractionResult with price + name?  return ScraperSuccess
  → LLMExtractionError or None fields?  fall back to cascade:
      extract_price(response.text) + extract_name(response.text)
        → both found?  return ScraperSuccess
        → missing?  return ScraperFailure(PARSE_ERROR)
```

**Signature change:**
```python
async def scrape_flow(url: str, *, llm_client: LLMClient) -> ScraperResult:
```

`extract_price.py` and `extract_name.py` remain untouched — used as fallback.

---

## Provider Factory (`jobs/handler.py`)

```python
def _build_llm_client(settings: Settings) -> LLMClient:
    model = settings.llm_model
    if settings.llm_provider == "openai":
        from ...adapters.openai_llm_client import OpenAILLMClient
        return OpenAILLMClient(_api_key=settings.llm_api_key, _model=model or "gpt-4o-mini")
    if settings.llm_provider == "gemini":
        from ...adapters.gemini_llm_client import GeminiLLMClient
        return GeminiLLMClient(_api_key=settings.llm_api_key, _model=model or "gemini-2.0-flash")
    raise ValueError(f"Unsupported LLM_PROVIDER: {settings.llm_provider!r}")
```

Deferred imports: unused provider SDK is never loaded (cold start benefit).
Adding a new provider (Anthropic) = new `if` branch + new adapter file only.

---

## Implementation Order

1. `infrastructure/settings.py` + `__init__.py`
2. `models/domain/llm_extraction_result.py`
3. `exceptions.py` — add `LLMExtractionError`
4. `ports/llm_client.py` + `ports/__init__.py`
5. `flows/preprocess_html.py`
6. `adapters/openai_llm_client.py`
7. `adapters/gemini_llm_client.py` + `adapters/__init__.py`
8. `flows/scrape_flow.py` — inject LLMClient, add LLM path + cascade fallback
9. `jobs/handler.py` — add Settings + factory + pass to flow
10. `pyproject.toml` — add openai, google-generativeai, pydantic

---

## Verification

1. Set env vars: `LLM_PROVIDER=openai`, `LLM_API_KEY=<key>`, optionally `LLM_MODEL=gpt-4o-mini`
2. Invoke the Lambda handler locally with a product URL
3. Verify `ScraperSuccess` returned with valid price (Decimal) and product_name
4. Test Gemini: swap `LLM_PROVIDER=gemini`, `LLM_API_KEY=<gemini_key>`
5. Test fallback: pass invalid `LLM_API_KEY` → should fall back to cascade and still extract price from a standard page (e.g. books.toscrape.com)
6. Test total failure: invalid key + page with no structured data → `ScraperFailure(PARSE_ERROR)`
