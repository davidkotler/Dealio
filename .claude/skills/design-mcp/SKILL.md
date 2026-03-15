---
name: design-mcp
version: 1.0.0
description: |
  Design MCP (Model Context Protocol) servers, tools, resources, and prompts before implementation.
  Use when creating new MCP servers, designing tool interfaces for AI agents, planning resource
  endpoints, defining prompt templates, architecting MCP transport and deployment strategy,
  or before implementing any FastMCP/low-level Server code.
  Relevant for MCP, FastMCP, Model Context Protocol, AI tool design, agent tooling,
  JSON-RPC, stdio transport, Streamable HTTP, tool schemas, resource URIs, prompt templates.
---

# MCP Server Design

> Design production-ready MCP servers — tools, resources, prompts, transport, and lifecycle — before writing implementation code.

## Quick Reference

| Aspect | Details |
|--------|---------|
| **Invokes** | `implement/mcp`, `implement/pydantic`, `design/api`, `design/event` |
| **Invoked By** | `design/code`, `design/lld` |
| **Key Artifacts** | Server blueprint, tool schemas, resource URI map, prompt catalog, lifespan design |

---

## Core Workflow

1. **Scope** — Determine what the MCP server exposes: which domain, what capabilities
2. **Classify Primitives** — Categorize every capability as Tool, Resource, or Prompt
3. **Design Tools** — Define schemas, names, descriptions, annotations, structured output
4. **Design Resources** — Define URI patterns, static vs templates, MIME types
5. **Design Prompts** — Define reusable interaction templates with arguments
6. **Design Lifecycle** — Lifespan context, shared dependencies, initialization order
7. **Choose Transport** — stdio vs Streamable HTTP, stateful vs stateless
8. **Design Security** — Auth strategy, input validation, trust boundaries
9. **Validate** — Check against MCP design principles before implementation

---

## Primitive Classification

The first design decision is classifying each capability into the correct MCP primitive. Getting this wrong causes agents to misuse your server.

### Decision Tree

```
Capability Request
    │
    ├─► Does it perform actions or have side effects?
    │       └─► Yes ──► TOOL (model-controlled, executable)
    │
    ├─► Does it provide read-only data for context?
    │       └─► Yes ──► RESOURCE (application-controlled, passive)
    │
    └─► Does it structure how the LLM should interact?
            └─► Yes ──► PROMPT (user-controlled, reusable template)
```

### Classification Rules

| If the capability... | Then it's a... | Because... |
|----------------------|----------------|------------|
| Creates, updates, or deletes data | **Tool** | Side effects require model decision |
| Calls external APIs | **Tool** | Network calls are actions |
| Performs computation and returns results | **Tool** | Computation is an action |
| Loads configuration or static data | **Resource** | Read-only context injection |
| Reads a document, file, or record by URI | **Resource** | Passive data retrieval |
| Provides a database record by ID | **Resource** | URI-addressable data |
| Guides the LLM through a workflow | **Prompt** | Structured interaction pattern |
| Provides domain-expert interaction templates | **Prompt** | Reusable interaction scaffolding |

---

## Tool Design

### Must / Never

**MUST:**

- Use `verb_noun` naming: `search_documents`, `create_user`, `get_weather`
- Namespace tools with clear prefixes for multi-domain servers: `orders_search`, `orders_cancel`
- Write docstrings as onboarding docs — what it does, when to use it, what context matters
- Use Pydantic models or `Field()` constraints for all parameters
- Use `Literal` types for enumerations, not free-form strings
- Return structured data via Pydantic models (generates `outputSchema`)
- Set `ToolAnnotations` (`readOnlyHint`, `destructiveHint`, `openWorldHint`)
- Make error messages actionable: what happened, why, valid format, example
- Design one tool per action — single responsibility

**NEVER:**

- Create multi-action tools with an `action` parameter (LLMs struggle with these)
- Use generic names: ~~`handle_request`~~, ~~`process_data`~~, ~~`do_action`~~
- Return raw stack traces or error codes — answer: what happened, why, how to fix
- Expose internal implementation in tool names: ~~`kafka_publish_order`~~, ~~`sql_query`~~
- Exceed 10-30 tools per server — split into focused servers if more needed
- Return more than 25K tokens per response — offer `response_format` with concise/detailed modes
- Use deeply nested schemas (>3 levels) — flatten where possible

### When → Then

| When | Then |
|------|------|
| Tool only reads data | Set `readOnlyHint=True` in annotations |
| Tool deletes or modifies irreversibly | Set `destructiveHint=True` |
| Tool calls external systems | Set `openWorldHint=True` |
| Parameter has fixed options | Use `Literal["opt1", "opt2"]`, not `str` |
| Complex input with multiple fields | Use Pydantic `BaseModel` as parameter |
| Tool returns structured data | Return Pydantic model (auto-generates `outputSchema`) |
| Tool may produce large output | Add `response_format: Literal["concise", "detailed"]` parameter |
| Tool description exceeds 2 sentences | Good — treat it as onboarding documentation |
| Existing REST API available | Don't wrap 1:1 — design composite tools matching agent workflows |
| Multiple related tools exist | Group with common prefix: `users_search`, `users_create` |

### Tool Schema Template

```python
from pydantic import BaseModel, Field
from typing import Literal
from mcp.types import ToolAnnotations
from mcp.server.fastmcp import Context


class SearchParams(BaseModel):
    """Validated input for document search."""
    query: str = Field(description="Search terms", min_length=1, max_length=500)
    max_results: int = Field(default=10, ge=1, le=100)
    file_type: Literal["pdf", "docx", "csv", "all"] = Field(default="all")


class SearchResult(BaseModel):
    """Structured search output."""
    document_id: str = Field(description="Unique document identifier")
    title: str
    relevance_score: float = Field(ge=0.0, le=1.0)
    snippet: str = Field(description="Relevant excerpt from document")


@mcp.tool(annotations=ToolAnnotations(
    readOnlyHint=True,
    openWorldHint=False,
))
async def search_documents(params: SearchParams, ctx: Context) -> list[SearchResult]:
    """Search the document repository for files matching a query.

    Use this tool when the user wants to find specific documents,
    reports, or data files. Supports full-text search across all
    indexed documents.

    Args:
        params: Search parameters including query, max results, and file type filter.
    """
    await ctx.info(f"Searching for: {params.query}")
    # Implementation here
```

---

## Resource Design

### Must / Never

**MUST:**

- Use scheme prefixes that reveal data domain: `config://`, `file://`, `db://`, `docs://`
- Use URI hierarchy that mirrors the data model: `products://{category}/{product_id}`
- Keep resources read-only — no side effects
- Return appropriate MIME types
- Use parameterized templates (`{param}`) for dynamic resources
- Make static resources (no parameters) for configuration and metadata

**NEVER:**

- Perform writes or mutations in resource handlers
- Use resources when the LLM needs to decide when to fetch — that's a tool
- Create resources with unbounded result sets — paginate or limit
- Expose internal paths or credentials in resource URIs

### When → Then

| When | Then |
|------|------|
| Data is always the same | Static resource (no parameters): `config://settings` |
| Data varies by identifier | Resource template: `users://{user_id}/profile` |
| Data changes and clients should know | Notify via `send_resource_list_changed()` |
| Large dataset | Paginate or expose as tool with pagination parameters |
| Binary/large payload | Return reference URI, not inline content |

### Resource URI Map Template

```
Resource URI Map
├── config://
│   ├── config://app/settings          (static)  — Application configuration
│   └── config://app/feature-flags     (static)  — Feature toggle states
├── docs://
│   ├── docs://{category}              (template) — List docs in category
│   └── docs://{category}/{doc_id}     (template) — Single document content
├── db://
│   └── db://schemas/{table_name}      (template) — Table schema definition
```

---

## Prompt Design

### Must / Never

**MUST:**

- Design prompts for reusable interaction patterns — not one-off queries
- Include a `title` for display in client UIs
- Accept arguments for customization via typed parameters
- Return structured message lists: `UserMessage`, `AssistantMessage`
- Write prompts that encode domain expertise the LLM wouldn't have alone

**NEVER:**

- Use prompts for data retrieval — that's a resource
- Use prompts for actions — that's a tool
- Hardcode values that should be arguments
- Create prompts without clear use-case documentation

### Prompt Catalog Template

```python
from mcp.server.fastmcp.prompts.base import UserMessage, AssistantMessage


@mcp.prompt(title="Debug Assistant")
def debug_error(error_message: str, context: str = "") -> list:
    """Guide the LLM through systematic error debugging.

    Use when the user encounters an error and needs structured
    investigation steps.
    """
    messages = [
        UserMessage(f"I'm seeing this error:\n\n```\n{error_message}\n```"),
    ]
    if context:
        messages.append(UserMessage(f"Additional context:\n{context}"))
    messages.append(AssistantMessage(
        "I'll help debug this. Let me analyze the error systematically."
    ))
    return messages
```

---

## Lifecycle Design

The lifespan pattern is the sole resource management strategy for MCP servers. Every shared dependency (DB pools, HTTP clients, caches) must be initialized here.

### Lifespan Template

```python
from contextlib import asynccontextmanager
from dataclasses import dataclass


@dataclass
class AppContext:
    """Strongly-typed application dependencies.

    All shared resources initialized once at startup,
    accessed via ctx.request_context.lifespan_context.
    """
    db: DatabasePool
    http_client: httpx.AsyncClient
    cache: CacheBackend


@asynccontextmanager
async def app_lifespan(server: FastMCP):
    db = await DatabasePool.create(dsn=settings.DATABASE_URL)
    http_client = httpx.AsyncClient(
        timeout=30.0,
        limits=httpx.Limits(max_connections=100),
    )
    cache = await CacheBackend.connect(settings.REDIS_URL)
    try:
        yield AppContext(db=db, http_client=http_client, cache=cache)
    finally:
        await cache.close()
        await http_client.aclose()
        await db.close()
```

### Lifespan Rules

- Use `@dataclass` for lifespan context — type safety + IDE autocomplete
- Initialize expensive resources once, not per-request
- Always clean up in `finally` — prevent resource leaks on shutdown
- Type `Context` generically: `Context[ServerSession, AppContext]`
- Access via `ctx.request_context.lifespan_context`
- Never use module-level mutable state as alternative

---

## Transport and Deployment Design

### Decision Matrix

| Question | stdio | Streamable HTTP |
|----------|-------|-----------------|
| Who connects? | Single local client | Multiple remote clients |
| Deployment? | Subprocess | Container/serverless |
| Latency? | Microseconds | Network overhead |
| Scaling? | Single instance | Horizontal |
| Progress reporting? | Yes | Yes (stateful) / No (stateless) |
| Server-initiated notifications? | Yes | Yes (stateful) / No (stateless) |
| Production remote? | No | Yes |

### When → Then

| When | Then |
|------|------|
| Local IDE/desktop integration | `transport="stdio"` |
| Remote, multi-client, cloud | `transport="streamable-http"` |
| Serverless (Lambda, Cloud Run) | `stateless_http=True, json_response=True` |
| Need progress reporting | Stateful mode (default) with session affinity |
| Horizontal scaling without sticky sessions | Stateless mode |
| Mounting alongside REST API | ASGI mount on FastAPI/Starlette |

### Stateless vs Stateful Design

```
Transport Decision
    │
    ├─► Need progress reporting OR server-initiated notifications?
    │       ├─► Yes ──► Stateful mode (default)
    │       │           └─► Requires session affinity for load balancing
    │       └─► No  ──► Stateless mode
    │                   └─► stateless_http=True, json_response=True
    │                   └─► Free horizontal scaling, serverless-ready
    │
    └─► Mounting with existing web app?
            └─► ASGI mount: app.mount("/mcp", mcp.streamable_http_app())
                └─► Set streamable_http_path="/" on FastMCP instance
```

---

## Security Design

### Must / Never

**MUST:**

- Implement OAuth 2.1 for any remote server handling user data
- Validate all inputs via Pydantic models with `Field()` constraints
- Use parameterized queries — never string concatenation for SQL/commands
- Exclude health endpoints from authentication middleware
- Use `print(..., file=sys.stderr)` for stdio servers — never write to stdout
- Set explicit timeouts on all external calls

**NEVER:**

- Forward client OAuth tokens to upstream APIs (token passthrough is forbidden)
- Hardcode secrets — use environment variables or secret managers
- Expose internal errors or stack traces to clients
- Trust tool descriptions from third-party servers without review (tool poisoning risk)
- Allow unrestricted network egress from MCP servers

### Auth Design Template

```python
from mcp.server.auth.provider import AccessToken, TokenVerifier
from mcp.server.auth.settings import AuthSettings


class JWTVerifier(TokenVerifier):
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
    "Protected Server",
    token_verifier=JWTVerifier(),
    auth=AuthSettings(
        issuer_url="https://auth.example.com",
        resource_server_url="https://mcp.example.com",
        required_scopes=["mcp:tools"],
    ),
)
```

---

## Server Composition

When a single server grows beyond 30 tools or spans multiple domains, split into focused servers and compose via ASGI mounting.

### When → Then

| When | Then |
|------|------|
| Server has >30 tools | Split into domain-specific servers |
| Tools span multiple bounded contexts | One server per context |
| Shared lifespan resources across servers | Manage via ASGI lifespan on the host app |
| Each server needs independent path | Mount: `app.mount("/api", api_mcp.streamable_http_app())` |

### Composition Template

```python
from fastapi import FastAPI
import contextlib


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    async with contextlib.AsyncExitStack() as stack:
        await stack.enter_async_context(orders_mcp.session_manager.run())
        await stack.enter_async_context(users_mcp.session_manager.run())
        yield


app = FastAPI(lifespan=lifespan)
app.mount("/orders", orders_mcp.streamable_http_app())
app.mount("/users", users_mcp.streamable_http_app())
```

---

## Anti-Patterns

### Multi-Action Tool

```python
# WRONG — LLMs struggle with action dispatching
@mcp.tool()
async def manage_user(action: str, user_id: str, data: dict) -> dict:
    """Create, update, delete, or get a user."""
    ...

# CORRECT — One tool per action
@mcp.tool()
async def create_user(name: str, email: str) -> UserResult: ...

@mcp.tool()
async def get_user(user_id: str) -> UserResult: ...

@mcp.tool()
async def delete_user(user_id: str) -> DeleteResult: ...
```

### 1:1 REST Wrapping

```python
# WRONG — Maps REST endpoints, not agent workflows
@mcp.tool()
async def list_users() -> list[dict]: ...

@mcp.tool()
async def list_events() -> list[dict]: ...

@mcp.tool()
async def create_event(user_id: str, event_data: dict) -> dict: ...

# CORRECT — Composite tool matching agent workflow
@mcp.tool()
async def schedule_event(
    attendee_emails: list[str],
    title: str,
    start_time: datetime,
) -> ScheduleResult:
    """Schedule an event and invite attendees.

    Resolves attendees by email, checks availability,
    creates the event, and sends invitations in one step.
    """
    ...
```

### Anemic Error Messages

```python
# WRONG — Unhelpful for LLM self-correction
raise McpError(ErrorData(code=INTERNAL_ERROR, message="Error 404"))

# CORRECT — Enables LLM retry with correct input
raise McpError(ErrorData(
    code=INVALID_PARAMS,
    message="Column 'last_name' does not exist. Valid columns: first_name, email, created_at"
))
```

### Missing Lifespan

```python
# WRONG — Creates connection per request
@mcp.tool()
async def query(sql: str) -> str:
    db = await Database.connect()  # New connection every call!
    result = await db.execute(sql)
    await db.disconnect()
    return str(result)

# CORRECT — Shared pool via lifespan
@mcp.tool()
async def query(sql: str, ctx: Context) -> str:
    db = ctx.request_context.lifespan_context.db
    return str(await db.execute(sql))
```

### Stdout Pollution (stdio transport)

```python
# WRONG — Corrupts JSON-RPC messages
print("Debug: processing request")

# CORRECT — Use stderr or Context logging
print("Debug: processing request", file=sys.stderr)
await ctx.info("Processing request")
```

### Vibe-Testing

```python
# WRONG — Chatting with LLM to verify server works
# "Hey Claude, can you search for documents about Python?"
# "Looks good!" ← Not a test

# CORRECT — Deterministic in-memory tests
async def test_search_returns_results():
    result = await mcp.call_tool("search_documents", {
        "params": {"query": "Python", "max_results": 5}
    })
    assert len(result) > 0
    assert all(r.relevance_score > 0 for r in result)
```

---

## Design Output Template

After completing the design workflow, produce:

```markdown
## MCP Server Design: {Server Name}

### 1. Server Overview
- **Name:** {name}
- **Description:** {what this server does}
- **Instructions:** {guidance for LLM clients}
- **Transport:** stdio | streamable-http
- **Mode:** stateful | stateless
- **Domain:** {bounded context this serves}

### 2. Lifespan Dependencies
| Dependency | Type | Purpose |
|------------|------|---------|
| {name} | DB Pool / HTTP Client / Cache | {why needed} |

### 3. Tool Catalog
| Tool | Annotations | Input | Output | Description |
|------|-------------|-------|--------|-------------|
| `verb_noun` | RO/RW/Destructive | Params model | Result model | {when to use} |

### 4. Resource Map
| URI Pattern | Type | MIME | Description |
|-------------|------|------|-------------|
| `scheme://path/{param}` | static/template | application/json | {what it provides} |

### 5. Prompt Catalog
| Prompt | Title | Arguments | Description |
|--------|-------|-----------|-------------|
| {name} | {display title} | {typed args} | {when to use} |

### 6. Security
- Auth: {OAuth 2.1 / None (stdio local)}
- Validation: {Pydantic constraints summary}
- Trust boundaries: {what's trusted, what's validated}

### 7. Observability
- Logging: {ctx.info/warning/error usage}
- Metrics: {tool call frequency, latency, error rate}
- Health: {/health endpoint for HTTP transport}

### 8. Deployment
- Transport config
- Container/scaling strategy
- ASGI mounting (if applicable)
```

---

## Quality Gates

Before proceeding to implementation:

- [ ] Every capability classified as Tool, Resource, or Prompt with clear rationale
- [ ] Tools use `verb_noun` naming with domain namespace prefixes
- [ ] Tool docstrings describe what, when, and context — not just what
- [ ] All tool parameters use Pydantic models or `Field()` constraints
- [ ] All tools return structured data (Pydantic models, not raw dicts)
- [ ] `ToolAnnotations` set for every tool (readOnly, destructive, openWorld)
- [ ] Error messages are actionable: what happened, why, valid format
- [ ] Resources use scheme-prefixed URIs mirroring the data model
- [ ] Resources are strictly read-only — no side effects
- [ ] Prompts encode domain expertise, not generic interactions
- [ ] Lifespan pattern designed for all shared dependencies
- [ ] Transport chosen with rationale (stdio vs Streamable HTTP)
- [ ] Stateful vs stateless decision documented with tradeoffs
- [ ] Auth strategy defined (OAuth 2.1 for remote, validation for all)
- [ ] No tool writes to stdout (stdio transport safety)
- [ ] Tool count per server ≤ 30 (split if exceeding)
- [ ] Test strategy uses in-memory clients, not LLM chat

---

## Skill Chaining

| Condition | Invoke | Handoff Context |
|-----------|--------|-----------------|
| Ready to implement server | `implement/mcp` | Server blueprint, tool catalog, resource map |
| Post-implementation review | `review/mcp` | Validate implementation against design |
| Complex Pydantic models | `implement/pydantic` | Input/output model definitions |
| MCP server triggers REST calls | `design/api` | Upstream API contracts |
| MCP server publishes events | `design/event` | Event schemas, async flows |
| Server needs data access | `design/data` | Entity models, access patterns |

**Chaining Syntax:**

```markdown
**Invoking:** `implement/mcp`
**Reason:** MCP server design complete, ready for FastMCP implementation
**Context:** Server blueprint with tool catalog, resource map, lifespan design
```

---

## Examples

### Example 1: Design Weather MCP Server

**Request:** "Design an MCP server for weather data"

**Output:**

```markdown
### Server: weather-service
- Transport: streamable-http (remote API)
- Mode: stateless (no progress needed, horizontal scaling)
- Instructions: "Use get_forecast for weather predictions and get_alerts for severe weather warnings."

### Tools
| Tool | Annotations | Input | Output |
|------|-------------|-------|--------|
| `get_forecast` | readOnly=True, openWorld=True | city: str, days: int (1-14) | ForecastResult |
| `get_alerts` | readOnly=True, openWorld=True | region: str, severity: Literal["all","severe","extreme"] | list[AlertResult] |

### Resources
| URI | Type | Description |
|-----|------|-------------|
| `weather://stations` | static | List of available weather stations |
| `weather://stations/{station_id}` | template | Station metadata and capabilities |

### Prompts
| Prompt | Title | Arguments | Description |
|--------|-------|-----------|-------------|
| `travel_weather` | "Travel Weather Briefing" | destination: str, dates: str | Structured weather analysis for travel planning |

### Lifespan
- httpx.AsyncClient with 30s timeout, 100 max connections
- API key from environment variable
```

### Example 2: Design Document Management MCP Server

**Request:** "Design an MCP server for internal document management"

**Output:**

```markdown
### Server: doc-manager
- Transport: streamable-http
- Mode: stateful (progress reporting for large uploads)
- Auth: OAuth 2.1 with scopes: docs:read, docs:write, docs:admin

### Tools
| Tool | Annotations | Input | Output |
|------|-------------|-------|--------|
| `docs_search` | readOnly=True | SearchParams (query, filters, max_results) | list[SearchResult] |
| `docs_upload` | destructive=False | UploadParams (title, content, category) | UploadResult |
| `docs_delete` | destructive=True | doc_id: str | DeleteResult |
| `docs_summarize` | readOnly=True | doc_id: str, max_length: int | SummaryResult |

### Resources
| URI | Type | Description |
|-----|------|-------------|
| `docs://categories` | static | Available document categories |
| `docs://{category}/{doc_id}` | template | Document content by category and ID |
| `config://retention-policy` | static | Document retention rules |

### Lifespan
- DatabasePool for document storage
- S3Client for binary content (claim-check pattern)
- SearchIndex client for full-text search
```
