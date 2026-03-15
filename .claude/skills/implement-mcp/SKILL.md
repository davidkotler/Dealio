---
name: implement-mcp
version: 1.0.0
description: |
  Implement production-ready MCP servers using FastMCP with typed tools, resources, prompts,
  lifespan management, and proper transport configuration from design specifications.
  Use when building MCP servers, implementing FastMCP tools, creating resource handlers,
  writing prompt templates, configuring stdio or Streamable HTTP transport, adding OAuth 2.1,
  mounting MCP on ASGI apps, or wiring up server dependencies.
  Relevant for MCP, FastMCP, Model Context Protocol, AI tool servers, JSON-RPC, mcp SDK,
  tool implementation, resource endpoints, prompt templates, agent tooling.
  Prerequisite: design/mcp should be completed (server blueprint exists).
---

# MCP Server Implementation

> Transform MCP server designs into production-ready FastMCP code with typed tools, validated inputs, structured outputs, and deterministic tests.

## Quick Reference

| Aspect | Details |
|--------|---------|
| **Prerequisite** | `design/mcp` completed — server blueprint should exist |
| **Invokes** | `review/mcp`, `implement/pydantic`, `test/unit`, `observe/logs`, `observe/traces` |
| **Invoked By** | `design/mcp`, `implement/python`, `design/lld` |
| **Key Artifacts** | FastMCP server module, tool handlers, resource handlers, prompt definitions, lifespan context, tests |

---

## Core Workflow

1. **Verify Design**: Confirm server blueprint from `design/mcp` exists with tool catalog, resource map, prompt catalog
2. **Setup Server**: Create FastMCP instance with name, instructions, transport config
3. **Implement Lifespan**: Build `AppContext` dataclass and async context manager for shared dependencies
4. **Implement Tools**: Write tool functions with Pydantic input/output models, docstrings, annotations
5. **Implement Resources**: Write resource handlers with URI patterns, static and template variants
6. **Implement Prompts**: Write prompt functions returning structured message lists
7. **Wire Security**: Add OAuth 2.1 token verifier (for remote servers) and input validation
8. **Configure Transport**: Set up stdio or Streamable HTTP with stateful/stateless mode
9. **Write Tests**: Create in-memory client tests — never vibe-test with LLM chat
10. **Validate**: Run `ruff check`, `ty check`, `pytest`

---

## Must / Never

### Server Setup

**MUST:**

- Pass descriptive `name` and `instructions` to `FastMCP()` — instructions guide LLM clients
- Use `lifespan` parameter for all shared dependencies (DB, HTTP clients, caches)
- Set `json_response=True` for Streamable HTTP transport
- Set `stateless_http=True` when horizontal scaling without session affinity is needed
- Pin SDK dependency: `mcp>=1.25,<2`

**NEVER:**

- Create bare `FastMCP()` without `name` or `instructions`
- Initialize expensive resources outside the lifespan (per-request connections waste resources)
- Use module-level mutable state as an alternative to lifespan
- Mix transport configuration — pick one and document why

### Tools

**MUST:**

- Use `async def` for all tools with I/O operations
- Accept `ctx: Context` parameter for logging, progress, resource reading, and lifespan access
- Use Pydantic `BaseModel` with `Field()` constraints for complex inputs
- Use `Literal` types for enumerated parameters — not free-form `str`
- Return Pydantic models for structured output (generates `outputSchema`)
- Set `ToolAnnotations` on every tool: `readOnlyHint`, `destructiveHint`, `openWorldHint`
- Write docstrings that explain what, when, and context — treat as onboarding docs
- Keep each tool single-purpose — one action per tool

**NEVER:**

- Create multi-action tools with an `action: str` dispatch parameter
- Return raw `dict` or untyped data — always use typed models
- Return more than 25K tokens — add `response_format` parameter if output varies
- Put business logic inline — delegate to service layer
- Write to `stdout` in stdio transport (corrupts JSON-RPC) — use `ctx.info()` or `sys.stderr`
- Expose internal implementation in tool names (`sql_query`, `kafka_publish`)

### Resources

**MUST:**

- Use scheme-prefixed URIs: `config://`, `docs://`, `db://`
- Use `{param}` template syntax for dynamic resources
- Return appropriate content types
- Keep resources strictly read-only — zero side effects

**NEVER:**

- Perform writes or mutations in resource handlers
- Return unbounded result sets — paginate or limit
- Expose file paths or credentials in URIs

### Prompts

**MUST:**

- Include `title` parameter for client UI display
- Accept typed arguments for customization
- Return structured message lists using `UserMessage`, `AssistantMessage`
- Encode domain expertise that the LLM wouldn't have alone

**NEVER:**

- Use prompts for data retrieval (that's a resource) or actions (that's a tool)
- Hardcode values that should be arguments

### Testing

**MUST:**

- Test with in-memory client connections — bypass transport overhead
- Use `await mcp.call_tool("name", {...})` for direct tool testing
- Test validation errors return actionable messages
- Test lifespan initialization and cleanup
- Mock external dependencies via lifespan context injection

**NEVER:**

- Validate server behavior by chatting with an LLM ("vibe-testing")
- Skip error path testing
- Test transport layer when testing tool logic

---

## When → Then

| When | Then |
|------|------|
| No server blueprint exists | Invoke `design/mcp` first |
| Server has shared dependencies | Implement lifespan with `@dataclass` AppContext |
| Tool reads data, no side effects | Set `readOnlyHint=True` in annotations |
| Tool deletes or modifies irreversibly | Set `destructiveHint=True` |
| Tool calls external APIs | Set `openWorldHint=True`, wrap with timeout |
| Parameter has fixed options | Use `Literal["opt1", "opt2"]` |
| Complex input (3+ fields) | Create Pydantic `BaseModel` → invoke `implement/pydantic` |
| Tool returns structured data | Return Pydantic model (auto-generates `outputSchema`) |
| Tool output may be large | Add `response_format: Literal["concise", "detailed"]` param |
| Local IDE integration | `transport="stdio"` |
| Remote/cloud/multi-client | `transport="streamable-http"` |
| Serverless (Lambda, Cloud Run) | `stateless_http=True, json_response=True` |
| Mounting alongside FastAPI | `app.mount("/mcp", mcp.streamable_http_app())` |
| Server exceeds 30 tools | Split into domain-specific servers |
| Ready to test | Write in-memory client tests |

---

## Decision Trees

### Transport Selection

```
Deployment Target?
├─► Local subprocess (IDE, Claude Desktop)
│   └─► transport="stdio"
├─► Remote HTTP server
│   ├─► Need progress/notifications?
│   │   └─► Stateful (default) + session affinity
│   └─► Horizontal scaling / serverless?
│       └─► stateless_http=True, json_response=True
└─► Alongside existing web app?
    └─► ASGI mount on FastAPI/Starlette
        └─► Set streamable_http_path="/" on FastMCP
```

### Tool Implementation

```
Tool Request
├─► Has I/O (DB, HTTP, file)?
│   └─► async def with await
├─► CPU-bound computation?
│   └─► Use run_in_executor
├─► Needs shared resources?
│   └─► Access via ctx.request_context.lifespan_context
├─► Needs to log progress?
│   └─► Use ctx.info(), ctx.report_progress()
└─► Needs LLM inference?
    └─► Use ctx.session.create_message() (sampling)
```

### Error Strategy

```
Error Scenario?
├─► Invalid input (validation) → Pydantic raises automatically
├─► Business rule violated → McpError(INVALID_PARAMS, actionable message)
├─► External service down → McpError(INTERNAL_ERROR, retry guidance)
├─► Resource not found → McpError(INVALID_PARAMS, "X not found. Valid: [...]")
└─► Unexpected error → McpError(INTERNAL_ERROR, generic safe message)

Actionable message format:
"Error: {what happened}. {why}. Valid: {format/options}."
```

---

## Skill Chaining

| Condition | Invoke | Handoff Context |
|-----------|--------|-----------------|
| No server blueprint | `design/mcp` | Domain, capabilities needed |
| Complex Pydantic models | `implement/pydantic` | Input/output field definitions |
| Tool calls external APIs | `implement/python` | HTTP client, resilience patterns |
| Tools need DB access | `implement/data` | Repository, query patterns |
| After implementation | `review/mcp` | Server files, tool catalog, test coverage |
| After implementation | `test/unit` | Tool names, schemas, expected responses |
| Adding structured logs | `observe/logs` | Log schema, tool call context |
| Distributed tracing | `observe/traces` | Span naming, context propagation |

**Chaining Syntax:**

```markdown
**Invoking:** `implement/pydantic`
**Reason:** Complex tool input with nested models and cross-field validation
**Context:** SearchParams with query constraints, ForecastResult with weather fields
```

---

## Patterns

### Server Module Structure

```python
"""MCP server for {domain} operations."""
from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Literal

import httpx
from mcp.server.fastmcp import Context, FastMCP
from mcp.server.session import ServerSession
from mcp.shared.exceptions import McpError
from mcp.types import ErrorData, INTERNAL_ERROR, INVALID_PARAMS, ToolAnnotations
from pydantic import BaseModel, Field


# --- Lifespan ---

@dataclass
class AppContext:
    """Shared dependencies initialized once at startup."""
    http_client: httpx.AsyncClient


@asynccontextmanager
async def app_lifespan(server: FastMCP):
    http_client = httpx.AsyncClient(
        timeout=30.0,
        limits=httpx.Limits(max_connections=100),
    )
    try:
        yield AppContext(http_client=http_client)
    finally:
        await http_client.aclose()


# --- Server ---

mcp = FastMCP(
    "WeatherService",
    instructions="Use get_forecast for weather predictions. Use get_alerts for severe weather warnings.",
    lifespan=app_lifespan,
)
```

### Tool with Pydantic Input/Output

```python
class ForecastParams(BaseModel):
    """Validated forecast request parameters."""
    city: str = Field(description="City name or coordinates", min_length=1, max_length=200)
    days: int = Field(default=3, ge=1, le=14, description="Number of forecast days")
    units: Literal["celsius", "fahrenheit"] = Field(default="celsius")


class ForecastDay(BaseModel):
    """Single day forecast."""
    date: str
    high: float = Field(description="High temperature")
    low: float = Field(description="Low temperature")
    condition: str
    precipitation_pct: float = Field(ge=0, le=100)


class ForecastResult(BaseModel):
    """Structured forecast output."""
    city: str
    days: list[ForecastDay]
    source: str = Field(description="Data provider attribution")


@mcp.tool(annotations=ToolAnnotations(
    readOnlyHint=True,
    openWorldHint=True,
))
async def get_forecast(
    *,
    params: ForecastParams,
    ctx: Context[ServerSession, AppContext],
) -> ForecastResult:
    """Get weather forecast for a city.

    Use this tool when the user asks about upcoming weather conditions,
    temperature predictions, or wants to plan activities around weather.
    Supports forecasts up to 14 days ahead.

    Args:
        params: Forecast parameters including city, number of days, and temperature units.
    """
    await ctx.info(f"Fetching {params.days}-day forecast for {params.city}")
    app = ctx.request_context.lifespan_context

    try:
        response = await app.http_client.get(
            "https://api.weather.example.com/forecast",
            params={"city": params.city, "days": params.days},
        )
        response.raise_for_status()
        data = response.json()
    except httpx.TimeoutException:
        raise McpError(ErrorData(
            code=INTERNAL_ERROR,
            message=f"Weather API timed out for '{params.city}'. Try again or use a major city name.",
        ))
    except httpx.HTTPStatusError as e:
        raise McpError(ErrorData(
            code=INTERNAL_ERROR,
            message=f"Weather API returned HTTP {e.response.status_code}. City '{params.city}' may not exist.",
        ))

    return ForecastResult(
        city=params.city,
        days=[ForecastDay(**day) for day in data["forecast"]],
        source="weather.example.com",
    )
```

### Resource with Static and Template

```python
@mcp.resource("weather://stations")
def list_stations() -> str:
    """List all available weather monitoring stations.

    Returns JSON array of station metadata including location and capabilities.
    """
    import json
    return json.dumps([
        {"id": "us-east-1", "name": "US East", "capabilities": ["forecast", "alerts"]},
        {"id": "eu-west-1", "name": "EU West", "capabilities": ["forecast"]},
    ])


@mcp.resource("weather://stations/{station_id}")
def get_station(station_id: str) -> str:
    """Get detailed metadata for a specific weather station.

    Returns station configuration, supported data types, and current status.
    """
    station = station_registry.get(station_id)
    if not station:
        return f'{{"error": "Station {station_id} not found"}}'
    return station.model_dump_json()
```

### Prompt with Typed Arguments

```python
from mcp.server.fastmcp.prompts.base import AssistantMessage, UserMessage


@mcp.prompt(title="Travel Weather Briefing")
def travel_weather(
    *,
    destination: str,
    departure_date: str,
    return_date: str,
) -> list:
    """Generate a structured weather briefing for travel planning.

    Use when the user is planning a trip and needs weather-informed
    packing and activity recommendations.
    """
    return [
        UserMessage(
            f"I'm traveling to {destination} from {departure_date} to {return_date}. "
            "Give me a weather briefing with packing recommendations and activity suggestions."
        ),
        AssistantMessage(
            "I'll prepare a comprehensive weather briefing for your trip. "
            "Let me check the forecast and provide tailored recommendations."
        ),
    ]
```

### Lifespan with Multiple Dependencies

```python
@dataclass
class AppContext:
    """Strongly-typed shared dependencies."""
    db: DatabasePool
    http_client: httpx.AsyncClient
    cache: CacheBackend
    search_index: SearchClient


@asynccontextmanager
async def app_lifespan(server: FastMCP):
    db = await DatabasePool.create(dsn=settings.DATABASE_URL)
    http_client = httpx.AsyncClient(
        timeout=30.0,
        limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
    )
    cache = await CacheBackend.connect(settings.REDIS_URL)
    search = SearchClient(settings.SEARCH_URL)
    try:
        yield AppContext(
            db=db,
            http_client=http_client,
            cache=cache,
            search_index=search,
        )
    finally:
        await search.close()
        await cache.close()
        await http_client.aclose()
        await db.close()
```

### ASGI Mount with FastAPI

```python
import contextlib

from fastapi import FastAPI
from starlette.responses import JSONResponse


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    async with contextlib.AsyncExitStack() as stack:
        await stack.enter_async_context(mcp.session_manager.run())
        yield


app = FastAPI(lifespan=lifespan)


@app.get("/health")
async def health():
    return JSONResponse({"status": "healthy"})


# Set streamable_http_path="/" on FastMCP so mount path controls final URL
app.mount("/mcp", mcp.streamable_http_app())
```

### OAuth 2.1 Token Verifier

```python
from mcp.server.auth.provider import AccessToken, TokenVerifier
from mcp.server.auth.settings import AuthSettings


class JWTVerifier(TokenVerifier):
    """Validate JWT tokens against the auth provider."""

    async def verify_token(self, token: str) -> AccessToken | None:
        payload = await verify_jwt(token)
        if not payload:
            return None
        return AccessToken(
            token=token,
            client_id=payload.get("client_id"),
            scopes=payload.get("scope", "").split(),
            expires_at=payload.get("exp"),
        )


mcp = FastMCP(
    "ProtectedServer",
    token_verifier=JWTVerifier(),
    auth=AuthSettings(
        issuer_url="https://auth.example.com",
        resource_server_url="https://mcp.example.com",
        required_scopes=["mcp:tools"],
    ),
    lifespan=app_lifespan,
)
```

### Progress Reporting for Long Operations

```python
@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
async def process_dataset(
    *,
    dataset_id: str,
    ctx: Context[ServerSession, AppContext],
) -> ProcessingResult:
    """Process a dataset with progress reporting.

    Use for large dataset operations where the user should see incremental progress.
    Requires stateful transport mode.
    """
    app = ctx.request_context.lifespan_context
    records = await app.db.fetch_records(dataset_id)

    processed = 0
    for i, record in enumerate(records):
        await process_record(record)
        processed += 1
        if (i + 1) % 100 == 0:
            await ctx.report_progress(
                progress=i + 1,
                total=len(records),
                message=f"Processed {i + 1}/{len(records)} records",
            )

    return ProcessingResult(total_processed=processed, dataset_id=dataset_id)
```

### Dynamic Tool Registration

```python
async def register_plugin_tools(mcp: FastMCP, plugins: list[Plugin]) -> None:
    """Register tools from plugins at runtime."""
    for plugin in plugins:
        for tool_def in plugin.get_tools():
            mcp.add_tool(
                tool_def.handler,
                name=f"{plugin.namespace}_{tool_def.name}",
                description=tool_def.description,
            )
    await mcp.notify_tools_changed()
```

---

## Testing Patterns

### Direct Tool Testing

```python
import pytest
from mcp.server.fastmcp import FastMCP


@pytest.fixture
def server() -> FastMCP:
    mcp = FastMCP("TestServer")

    @mcp.tool()
    def add(*, a: int, b: int) -> int:
        """Add two numbers."""
        return a + b

    return mcp


@pytest.mark.asyncio
async def test_add_tool(server: FastMCP) -> None:
    result = await server.call_tool("add", {"a": 5, "b": 3})
    assert result[0].text == "8"


@pytest.mark.asyncio
async def test_add_tool_validation_error(server: FastMCP) -> None:
    with pytest.raises(Exception):
        await server.call_tool("add", {"a": "not_a_number", "b": 3})
```

### In-Memory Client Testing

```python
from mcp import ClientSession


@pytest.fixture
async def client(server: FastMCP):
    async with server.create_client() as client:
        yield client


@pytest.mark.asyncio
async def test_list_tools(client: ClientSession) -> None:
    tools = await client.list_tools()
    tool_names = [t.name for t in tools.tools]
    assert "get_forecast" in tool_names


@pytest.mark.asyncio
async def test_call_tool(client: ClientSession) -> None:
    result = await client.call_tool("get_forecast", {
        "params": {"city": "London", "days": 3},
    })
    assert not result.isError
    assert "London" in result.content[0].text
```

### Testing with Mocked Lifespan

```python
from unittest.mock import AsyncMock


@pytest.fixture
async def server_with_mock_deps() -> FastMCP:
    """Server with mocked external dependencies."""
    mock_http = AsyncMock(spec=httpx.AsyncClient)
    mock_http.get.return_value = httpx.Response(
        200,
        json={"forecast": [{"date": "2026-03-04", "high": 15, "low": 8, "condition": "cloudy", "precipitation_pct": 30}]},
    )

    @asynccontextmanager
    async def mock_lifespan(server: FastMCP):
        yield AppContext(http_client=mock_http)

    mcp = FastMCP("TestWeather", lifespan=mock_lifespan)
    # Register tools...
    return mcp
```

### Testing Resources

```python
@pytest.mark.asyncio
async def test_static_resource(client: ClientSession) -> None:
    result = await client.read_resource("weather://stations")
    assert result.contents
    data = json.loads(result.contents[0].text)
    assert len(data) > 0


@pytest.mark.asyncio
async def test_template_resource(client: ClientSession) -> None:
    result = await client.read_resource("weather://stations/us-east-1")
    assert result.contents
    station = json.loads(result.contents[0].text)
    assert station["id"] == "us-east-1"
```

---

## Anti-Patterns

### Multi-Action Tool

```python
# WRONG — LLMs struggle with dispatch logic
@mcp.tool()
async def manage_user(*, action: str, user_id: str, data: dict) -> dict:
    """Create, update, delete, or get a user."""
    if action == "create": ...
    elif action == "delete": ...

# CORRECT — One tool per action
@mcp.tool(annotations=ToolAnnotations(destructiveHint=False))
async def create_user(*, name: str, email: str) -> UserResult: ...

@mcp.tool(annotations=ToolAnnotations(destructiveHint=True))
async def delete_user(*, user_id: str) -> DeleteResult: ...
```

### Missing Lifespan (Per-Request Connections)

```python
# WRONG — New connection every tool call
@mcp.tool()
async def query(*, sql: str) -> str:
    db = await Database.connect()
    result = await db.execute(sql)
    await db.disconnect()
    return str(result)

# CORRECT — Pool via lifespan
@mcp.tool()
async def query(*, sql: str, ctx: Context[ServerSession, AppContext]) -> str:
    db = ctx.request_context.lifespan_context.db
    return str(await db.execute(sql))
```

### Unhelpful Error Messages

```python
# WRONG — LLM cannot self-correct
raise McpError(ErrorData(code=INTERNAL_ERROR, message="Error"))

# CORRECT — Actionable: what, why, valid options
raise McpError(ErrorData(
    code=INVALID_PARAMS,
    message="Column 'last_name' not found. Valid columns: first_name, email, created_at.",
))
```

### Stdout Pollution (stdio)

```python
# WRONG — Corrupts JSON-RPC messages
print(f"Processing {city}")

# CORRECT — Use Context logging or stderr
await ctx.info(f"Processing {city}")
# or
import sys
print(f"Debug: {city}", file=sys.stderr)
```

### Vibe-Testing

```python
# WRONG — Chatting with LLM to validate
# "Hey Claude, try searching for documents about Python"
# "Looks good!" ← Not a real test

# CORRECT — Deterministic assertions
async def test_search_returns_results(server):
    result = await server.call_tool("search_docs", {"query": "Python"})
    assert len(result) > 0
```

### Untyped Returns

```python
# WRONG — Raw dict, no schema for client
@mcp.tool()
async def get_weather(*, city: str) -> dict:
    return {"temp": 22, "condition": "sunny"}

# CORRECT — Pydantic model generates outputSchema
class WeatherResult(BaseModel):
    temperature: float = Field(description="Temperature in Celsius")
    condition: str

@mcp.tool()
async def get_weather(*, city: str) -> WeatherResult:
    return WeatherResult(temperature=22.0, condition="sunny")
```

---

## Quality Gates

Before completing MCP server implementation:

- [ ] `FastMCP` initialized with `name`, `instructions`, and `lifespan`
- [ ] All shared dependencies managed via lifespan `AppContext` dataclass
- [ ] Every tool has Pydantic input models with `Field()` constraints
- [ ] Every tool returns a Pydantic model (structured output)
- [ ] Every tool has `ToolAnnotations` (`readOnlyHint`, `destructiveHint`, `openWorldHint`)
- [ ] Tool docstrings explain what, when, and context — not just "does X"
- [ ] Error messages are actionable: what happened, why, valid format
- [ ] Resources are strictly read-only with scheme-prefixed URIs
- [ ] Prompts return structured `UserMessage`/`AssistantMessage` lists with `title`
- [ ] No `print()` to stdout — uses `ctx.info()` or `sys.stderr`
- [ ] Transport configured with documented rationale
- [ ] OAuth 2.1 implemented for remote servers handling user data
- [ ] In-memory client tests cover happy path, validation errors, error paths
- [ ] No vibe-testing — all behavior verified with deterministic assertions
- [ ] `ruff check` and `ty check` pass
- [ ] `from __future__ import annotations` present in all modules
- [ ] SDK pinned: `mcp>=1.25,<2`

---

## File Layout

```
services/<name>/<name>/
    server.py                    # FastMCP instance, lifespan, transport config
    tools/
        __init__.py
        <domain>_tools.py        # Tool handlers grouped by domain
    resources/
        __init__.py
        <domain>_resources.py    # Resource handlers
    prompts/
        __init__.py
        <domain>_prompts.py      # Prompt templates
    models/
        contracts/
            tools/               # Pydantic input/output models for tools
            resources/           # Resource response models
    auth.py                      # TokenVerifier (if OAuth 2.1)
    settings.py                  # MCP server settings
tests/
    unit/
        test_tools.py            # Direct tool tests
        test_resources.py        # Resource handler tests
    integration/
        test_server.py           # In-memory client tests
```

---

## Running the Server

```python
# stdio (local, subprocess)
if __name__ == "__main__":
    mcp.run(transport="stdio")

# Streamable HTTP (remote, production)
if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8000)

# ASGI mount (alongside FastAPI)
app = FastAPI(lifespan=combined_lifespan)
app.mount("/mcp", mcp.streamable_http_app())
# Run: uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

---

## Deep References

For extended guidance on specific patterns:
- MCP SDK docs: `mcp.server.fastmcp` module API
- Transport details: Streamable HTTP spec (version 2025-03-26)
- Auth: OAuth 2.1 Resource Server role, `/.well-known/oauth-protected-resource`
- Testing: `mcp.client.stdio`, `mcp.client.streamable_http` for integration tests
