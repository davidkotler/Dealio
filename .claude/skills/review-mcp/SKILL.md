---
name: review-mcp
version: 1.0.0

description: |
  Review MCP (Model Context Protocol) server implementations for correctness, production-readiness,
  and adherence to MCP best practices. Evaluates FastMCP server setup, tool design, resource handlers,
  prompt definitions, lifespan management, transport configuration, security, error handling, and testing.
  Use when reviewing MCP server code, validating FastMCP implementations, assessing tool/resource/prompt
  quality, checking transport and auth configuration, or after implementing/modifying MCP servers.
  Relevant for MCP, FastMCP, Model Context Protocol, AI tool servers, JSON-RPC, mcp SDK,
  tool handlers, resource endpoints, prompt templates, agent tooling, stdio, Streamable HTTP.

chains:
  invoked-by:
    - skill: implement/mcp
      context: "Post-implementation quality gate"
    - skill: implement/python
      context: "When MCP server code detected in changes"
  invokes:
    - skill: implement/mcp
      when: "Critical or major findings detected"
    - skill: review/performance
      when: "Performance concerns identified"
    - skill: review/observability
      when: "Observability gaps identified"
---

# MCP Server Review

> Validate MCP server implementations meet production standards through systematic evaluation of tools, resources, prompts, lifecycle, transport, security, and testing.

## Quick Reference

| Aspect | Details |
|--------|---------|
| **Dimension** | MCP Server Implementation Quality |
| **Scope** | Server setup, tools, resources, prompts, lifespan, transport, auth, errors, tests |
| **Invoked By** | `implement/mcp`, `implement/python`, `/review` command |
| **Invokes** | `implement/mcp` (on failure), `review/performance`, `review/observability` |
| **Verdict Options** | `PASS` · `PASS_WITH_SUGGESTIONS` · `NEEDS_WORK` · `FAIL` |

---

## Review Objective

Ensure MCP server implementations are correctly structured, type-safe, well-documented for LLM clients, properly managing lifecycle resources, and ready for production deployment.

### This Review Answers

1. Is the server properly initialized with name, instructions, and lifespan?
2. Do tools follow single-responsibility with typed I/O, annotations, and LLM-friendly docstrings?
3. Are resources read-only with scheme-prefixed URIs and appropriate content types?
4. Is the lifespan pattern correctly managing all shared dependencies?
5. Is the transport correctly configured with appropriate stateful/stateless mode?
6. Are error messages actionable — enabling LLM self-correction?
7. Are tests deterministic and in-memory — not vibe-tests?

### Out of Scope

- Business logic correctness (see `review/functionality`)
- Python style and typing (see `review/style`, `review/types`)
- Database query optimization (see `review/data`)
- General API design (see `review/api` — for REST, not MCP)

---

## Core Workflow

```
1. SCOPE    →  Identify MCP server files (server.py, *_tools.py, *_resources.py, *_prompts.py, auth.py)
2. CONTEXT  →  Load design/mcp blueprint, implement/mcp patterns, rules/principles.md
3. ANALYZE  →  Evaluate against criteria: Server → Tools → Resources → Prompts → Lifecycle → Transport → Security → Errors → Tests
4. CLASSIFY →  Assign severity per finding
5. VERDICT  →  Determine pass/fail based on severity counts
6. REPORT   →  Output structured results
7. CHAIN    →  Invoke implement/mcp if fixes needed
```

---

## Evaluation Criteria

### Server Setup (SS)

| ID | Criterion | Severity | Check |
|----|-----------|----------|-------|
| SS.1 | `FastMCP` created with descriptive `name` | CRITICAL | Not empty or generic |
| SS.2 | `instructions` parameter provided | MAJOR | Guides LLM clients on tool usage |
| SS.3 | `lifespan` parameter set when shared deps exist | BLOCKER | No per-request connections |
| SS.4 | `from __future__ import annotations` present | MINOR | Modern type annotation support |
| SS.5 | SDK pinned `mcp>=1.25,<2` in dependencies | MAJOR | Prevent breaking on major version |
| SS.6 | No module-level mutable state as lifespan alternative | BLOCKER | State must be in lifespan context |

### Tool Implementation (TI)

| ID | Criterion | Severity | Check |
|----|-----------|----------|-------|
| TI.1 | `async def` for all tools with I/O | CRITICAL | No sync I/O in async tools |
| TI.2 | `ctx: Context` parameter present | MAJOR | Enables logging, progress, lifespan access |
| TI.3 | Pydantic `BaseModel` with `Field()` for complex inputs | MAJOR | Constrained, documented parameters |
| TI.4 | `Literal` types for enumerated params | MAJOR | Not free-form `str` for fixed options |
| TI.5 | Returns Pydantic model (structured output) | CRITICAL | Generates `outputSchema`, not raw dict |
| TI.6 | `ToolAnnotations` set on every tool | MAJOR | `readOnlyHint`, `destructiveHint`, `openWorldHint` |
| TI.7 | Docstring explains what, when, and context | MAJOR | LLM onboarding documentation |
| TI.8 | Single responsibility — one action per tool | CRITICAL | No `action: str` dispatch parameter |
| TI.9 | No `print()` to stdout | BLOCKER | Corrupts JSON-RPC in stdio transport |
| TI.10 | Tool count per server ≤ 30 | MAJOR | Split if exceeding |
| TI.11 | Output ≤ 25K tokens or offers `response_format` | MAJOR | Concise/detailed modes for large output |
| TI.12 | `verb_noun` naming convention | MAJOR | `search_docs`, not `docSearch` or `handle` |
| TI.13 | Domain namespace prefix for multi-domain | MINOR | `orders_search`, `users_create` |
| TI.14 | No internal impl in tool names | MINOR | Not `sql_query`, `kafka_publish` |

### Resource Implementation (RI)

| ID | Criterion | Severity | Check |
|----|-----------|----------|-------|
| RI.1 | Scheme-prefixed URIs | MAJOR | `config://`, `docs://`, `db://` |
| RI.2 | URI hierarchy mirrors data model | MINOR | `products://{category}/{id}` |
| RI.3 | Strictly read-only — no side effects | BLOCKER | No writes or mutations |
| RI.4 | `{param}` template syntax for dynamic resources | MAJOR | Parameterized, not hardcoded |
| RI.5 | No unbounded result sets | CRITICAL | Paginate or limit |
| RI.6 | No file paths or credentials in URIs | BLOCKER | Security violation |
| RI.7 | Appropriate MIME type returned | MINOR | Matches content format |

### Prompt Implementation (PI)

| ID | Criterion | Severity | Check |
|----|-----------|----------|-------|
| PI.1 | `title` parameter for client UI display | MAJOR | Required for UX |
| PI.2 | Typed arguments for customization | MAJOR | Not untyped kwargs |
| PI.3 | Returns `UserMessage`/`AssistantMessage` list | CRITICAL | Structured MCP message format |
| PI.4 | Encodes domain expertise | MINOR | Not generic boilerplate |
| PI.5 | No data retrieval or actions in prompts | CRITICAL | Prompts are templates, not tools/resources |

### Lifecycle Management (LM)

| ID | Criterion | Severity | Check |
|----|-----------|----------|-------|
| LM.1 | `@dataclass` AppContext for lifespan deps | MAJOR | Type-safe, IDE-friendly |
| LM.2 | `@asynccontextmanager` wraps lifespan | CRITICAL | Proper async resource management |
| LM.3 | All shared deps initialized in lifespan, not per-request | BLOCKER | Connection pools, HTTP clients, caches |
| LM.4 | Cleanup in `finally` block | BLOCKER | Prevent resource leaks on shutdown |
| LM.5 | Reverse cleanup order (LIFO) | MAJOR | Last opened, first closed |
| LM.6 | Lifespan context accessed via `ctx.request_context.lifespan_context` | MAJOR | Standard access pattern |
| LM.7 | No per-request connection creation in tool handlers | BLOCKER | Resource waste, connection exhaustion |

### Transport Configuration (TC)

| ID | Criterion | Severity | Check |
|----|-----------|----------|-------|
| TC.1 | Transport choice documented with rationale | MAJOR | stdio vs streamable-http justification |
| TC.2 | `json_response=True` for Streamable HTTP | MAJOR | Proper response format |
| TC.3 | `stateless_http=True` when horizontal scaling needed | MAJOR | Avoid session affinity requirement |
| TC.4 | Session affinity configured for stateful mode | CRITICAL | Progress/notifications break without it |
| TC.5 | ASGI mount path correct when co-hosted | CRITICAL | `streamable_http_path="/"` with `app.mount()` |
| TC.6 | Health endpoint excluded from auth middleware | MAJOR | Kubernetes probes need unauthenticated access |

### Security (SE)

| ID | Criterion | Severity | Check |
|----|-----------|----------|-------|
| SE.1 | OAuth 2.1 for remote servers handling user data | BLOCKER | Token verification required |
| SE.2 | All inputs validated via Pydantic constraints | CRITICAL | `Field()` with bounds |
| SE.3 | Parameterized queries — no string interpolation | BLOCKER | SQL injection prevention |
| SE.4 | No hardcoded secrets | BLOCKER | Environment variables or secret manager |
| SE.5 | No internal errors exposed to clients | MAJOR | Safe error messages only |
| SE.6 | No forwarding of client OAuth tokens upstream | BLOCKER | Token passthrough forbidden |
| SE.7 | Explicit timeouts on all external calls | CRITICAL | Prevent hanging |

### Error Handling (EH)

| ID | Criterion | Severity | Check |
|----|-----------|----------|-------|
| EH.1 | Error messages are actionable | CRITICAL | What happened, why, valid format |
| EH.2 | Uses `McpError` with proper `ErrorData` codes | MAJOR | `INVALID_PARAMS`, `INTERNAL_ERROR` |
| EH.3 | Validation errors auto-raised by Pydantic | MAJOR | Not manually checked |
| EH.4 | External service errors wrapped with guidance | MAJOR | Timeout → "try again", 404 → "valid options: [...]" |
| EH.5 | No swallowed exceptions | BLOCKER | No empty `except` blocks |
| EH.6 | No stack traces in error responses | MAJOR | Security and LLM confusion risk |

### Testing (TS)

| ID | Criterion | Severity | Check |
|----|-----------|----------|-------|
| TS.1 | In-memory client tests exist | CRITICAL | `server.call_tool()` or `server.create_client()` |
| TS.2 | No vibe-testing (LLM chat validation) | BLOCKER | Deterministic assertions only |
| TS.3 | Happy path tested per tool | MAJOR | At least one positive test |
| TS.4 | Validation error paths tested | MAJOR | Invalid inputs return actionable errors |
| TS.5 | Lifespan initialization tested | MAJOR | AppContext created correctly |
| TS.6 | External deps mocked via lifespan injection | MAJOR | Deterministic, no network |
| TS.7 | Resource handlers tested | MAJOR | Static + template variants |
| TS.8 | Tool listing verified | MINOR | `list_tools()` returns expected set |

---

## Severity Definitions

| Severity | Definition | Action |
|----------|------------|--------|
| **BLOCKER** | Security risk, data leakage, resource leak, protocol corruption | Must fix before merge |
| **CRITICAL** | Breaks tool behavior, wrong transport config, missing structured output | Must fix, may defer |
| **MAJOR** | Missing annotations, weak docs, pattern violations | Should fix |
| **MINOR** | Style, naming conventions, optional enhancements | Consider fixing |
| **SUGGESTION** | Improvements beyond requirements | Optional |
| **COMMENDATION** | Excellent MCP patterns observed | Positive reinforcement |

---

## Verdict Determination

```
Findings Analysis
       │
       ├─► Any BLOCKER? ──────────────► FAIL
       ├─► Any CRITICAL? ─────────────► NEEDS_WORK
       ├─► Multiple MAJOR? ───────────► NEEDS_WORK
       ├─► Few MAJOR or MINOR only? ──► PASS_WITH_SUGGESTIONS
       └─► SUGGESTION/COMMENDATION ───► PASS
```

---

## Patterns

### Correct MCP Tool

```python
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
    """
    await ctx.info(f"Fetching forecast for {params.city}")
    app = ctx.request_context.lifespan_context
    response = await app.http_client.get(...)
    return ForecastResult(...)
```

**Why:** Pydantic I/O, annotations, rich docstring, async, lifespan access, Context logging.

### Anti-Pattern: Multi-Action Tool

```python
@mcp.tool()
async def manage_user(action: str, user_id: str, data: dict) -> dict:
    """Create, update, delete, or get a user."""
    if action == "create": ...
    elif action == "delete": ...
```

**Why:** LLMs struggle with dispatch. No structured I/O, no annotations, `dict` types.

### Anti-Pattern: Missing Lifespan

```python
@mcp.tool()
async def query(sql: str) -> str:
    db = await Database.connect()  # Per-request connection!
    result = await db.execute(sql)
    await db.disconnect()
    return str(result)
```

**Why:** New connection every call exhausts pool. Use `ctx.request_context.lifespan_context.db`.

### Anti-Pattern: Vibe-Testing

```python
# "Hey Claude, can you search for documents?" → "Looks good!"
# ← NOT a test. No assertions, not deterministic, not repeatable.
```

**Why:** In-memory `server.call_tool()` with assertions catches regressions; chat doesn't.

---

## Finding Format

```markdown
### [{{SEVERITY_EMOJI}} {{SEVERITY}}] {{TITLE}}

**Location:** `{{FILE}}:{{LINE}}`
**Criterion:** {{ID}} - {{NAME}}

**Issue:** {{DESCRIPTION}}

**Evidence:**
\`\`\`python
{{CODE}}
\`\`\`

**Suggestion:** {{FIX}}
**Rationale:** {{WHY_IT_MATTERS}}
```

---

## Summary Format

```markdown
# MCP Server Review Summary

## Verdict: {{EMOJI}} {{VERDICT}}

| Metric | Count |
|--------|-------|
| Files Reviewed | N |
| Blockers | N |
| Critical | N |
| Major | N |
| Minor | N |

## Key Findings
1. {{FINDING_1}}
2. {{FINDING_2}}

## MCP-Specific Assessment
- **Tool Quality:** {{tools have typed I/O, annotations, rich docs / issues found}}
- **Resource Safety:** {{read-only, URI patterns correct / issues found}}
- **Lifecycle:** {{lifespan manages all deps / resource leaks detected}}
- **Transport:** {{correctly configured / misconfigured}}
- **Security:** {{OAuth + validation / gaps detected}}
- **Testing:** {{deterministic in-memory tests / vibe-testing detected}}

## Chain Decision
{{CHAIN_EXPLANATION}}
```

---

## Skill Chaining

| Verdict | Action | Target |
|---------|--------|--------|
| `FAIL` | Mandatory fixes | `implement/mcp` |
| `NEEDS_WORK` | Targeted fixes | `implement/mcp` |
| `PASS_WITH_SUGGESTIONS` | Optional improvements | None |
| `PASS` | Continue | Next review dimension or `test/unit` |

### Handoff Protocol

```markdown
**Chain Target:** `implement/mcp`
**Priority Findings:** {{BLOCKER_AND_CRITICAL_IDS}}
**Constraint:** Preserve existing tool schemas and tests
```

---

## Quality Gates

Before finalizing review:

- [ ] All server files in scope analyzed (server.py, tools/, resources/, prompts/, auth.py)
- [ ] Every tool checked for: Pydantic I/O, annotations, docstring quality, single-responsibility
- [ ] Every resource checked for: read-only, URI scheme, bounded results
- [ ] Lifespan verified: all shared deps managed, cleanup in finally, no per-request connections
- [ ] Transport configuration validated against deployment target
- [ ] Security assessed: OAuth for remote, Pydantic validation, no hardcoded secrets
- [ ] Error messages verified as actionable (what, why, valid format)
- [ ] Test coverage verified: in-memory client, no vibe-testing, error paths covered
- [ ] Each finding has location + criterion + severity
- [ ] Verdict matches severity distribution
- [ ] Actionable suggestions for non-PASS verdicts
- [ ] Chain decision explicit and justified

---

## Deep References

Load on-demand for complex reviews:

| Reference | When to Load |
|-----------|--------------|
| `design/mcp` SKILL.md | Validating tool/resource/prompt design decisions |
| `implement/mcp` SKILL.md | Checking implementation patterns |
| `rules/principles.md` §1.1, §1.4, §1.10, §1.11, §2.9 | API-first, resilience, observability, security, testability |
| MCP SDK `mcp.server.fastmcp` | FastMCP API surface verification |
| MCP transport spec (2025-03-26) | Streamable HTTP configuration details |
