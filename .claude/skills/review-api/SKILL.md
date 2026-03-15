---
name: review-api
version: 1.0.0

description: |
  Review FastAPI route handlers for correctness, patterns, and production-readiness.
  Evaluates async usage, dependency injection, response models, error handling, and HTTP semantics.
  Use when reviewing API routes, validating endpoint implementations, assessing REST handlers,
  or after implementing/modifying FastAPI endpoints.
  Relevant for FastAPI, Starlette, Python async APIs, REST endpoint validation.
chains:
  invoked-by:
    - skill: implement/api
      context: "Post-implementation quality gate"
    - skill: implement/python
      context: "When FastAPI routes are detected"
  invokes:
    - skill: implement/api
      when: "Critical or major findings detected"
    - skill: review/performance
      when: "Performance concerns identified"
---

# API Review

> Validate FastAPI endpoints meet production standards through systematic pattern analysis.

## Quick Reference

| Aspect | Details |
|--------|---------|
| **Dimension** | API Implementation Quality |
| **Scope** | Route handlers, dependencies, schemas, error handling |
| **Invoked By** | `implement/api`, `implement/python`, `/review` command |
| **Invokes** | `implement/api` (on failure), `review/performance` |
| **Verdict Options** | `PASS` · `PASS_WITH_SUGGESTIONS` · `NEEDS_WORK` · `FAIL` |

---

## Review Objective

Ensure FastAPI route implementations are type-safe, correctly structured, follow HTTP semantics, and are ready for production deployment.

### This Review Answers

1. Are route handlers properly async with correct I/O patterns?
2. Do endpoints use proper HTTP methods and status codes?
3. Are dependencies injected correctly with proper lifecycle management?
4. Do response models protect against data leakage?

### Out of Scope

- Business logic correctness (see `review/functionality`)
- Database query optimization (see `review/data`)
- Authentication/authorization logic (see `review/security`)

---

## Core Workflow

```
1. SCOPE    →  Identify route files (**/routes/**/*.py, **/api/**/*.py)
2. CONTEXT  →  Load implement/api patterns, design/api contracts
3. ANALYZE  →  Evaluate against criteria (handlers → deps → schemas → errors)
4. CLASSIFY →  Assign severity per finding
5. VERDICT  →  Determine pass/fail
6. REPORT   →  Output structured results
7. CHAIN    →  Invoke implement/api if fixes needed
```

---

## Evaluation Criteria

### Route Handlers (RH)

| ID | Criterion | Severity | Check |
|----|-----------|----------|-------|
| RH.1 | `async def` for all I/O operations | CRITICAL | No sync I/O in async handlers |
| RH.2 | Explicit `response_model` on every endpoint | MAJOR | Decorator includes response_model |
| RH.3 | Correct status codes (201 POST, 204 DELETE) | MAJOR | Status matches operation semantics |
| RH.4 | `Annotated[T, Depends()]` syntax | MINOR | Modern FastAPI 0.95+ pattern |
| RH.5 | Handlers ≤10 lines, delegate to service | MAJOR | No business logic in handlers |
| RH.6 | Keyword-only args with `*,` for 2+ params | MINOR | Prevents positional arg errors |

### Dependencies (DP)

| ID | Criterion | Severity | Check |
|----|-----------|----------|-------|
| DP.1 | `yield` pattern for resources needing cleanup | CRITICAL | DB sessions, HTTP clients use yield |
| DP.2 | Re-raise exceptions after cleanup | BLOCKER | No swallowed exceptions in yield deps |
| DP.3 | Typed return annotations on all deps | MAJOR | Explicit types, no implicit Any |
| DP.4 | No circular dependency chains | CRITICAL | Verify dep graph is acyclic |
| DP.5 | `@lru_cache` on `get_settings()` | MINOR | Config parsed once |

### Schemas (SC)

| ID | Criterion | Severity | Check |
|----|-----------|----------|-------|
| SC.1 | Separate models: `*Create`, `*Update`, `*Response` | MAJOR | No single model for all ops |
| SC.2 | No sensitive fields in response models | BLOCKER | No password, token, api_key exposed |
| SC.3 | `model_config = {"from_attributes": True}` for ORM | MAJOR | Pydantic v2 ORM conversion |
| SC.4 | `exclude_unset=True` for PATCH operations | MAJOR | Partial updates work correctly |
| SC.5 | `Field(description=...)` on all fields | MINOR | OpenAPI documentation complete |

### Error Handling (EH)

| ID | Criterion | Severity | Check |
|----|-----------|----------|-------|
| EH.1 | Never return 200 for errors | CRITICAL | Proper 4xx/5xx codes |
| EH.2 | Global exception handler for domain errors | MAJOR | Consistent error response schema |
| EH.3 | No internal details in error responses | MAJOR | No stack traces, internal IDs |
| EH.4 | 404 for missing resources, 422 for validation | MAJOR | Semantic error codes |

### HTTP Semantics (HS)

| ID | Criterion | Severity | Check |
|----|-----------|----------|-------|
| HS.1 | GET is safe and idempotent (no side effects) | CRITICAL | Read-only operations |
| HS.2 | PUT/DELETE are idempotent | MAJOR | Same result on repeat calls |
| HS.3 | Resource paths use plural nouns | MINOR | `/users` not `/user` |
| HS.4 | No verbs in URL paths | MINOR | `/users/{id}` not `/getUser/{id}` |

---

## Severity Definitions

| Severity | Definition | Action |
|----------|------------|--------|
| **🔴 BLOCKER** | Security risk, data leakage, swallowed errors | Must fix before merge |
| **🟠 CRITICAL** | Breaks async, wrong HTTP semantics, circular deps | Must fix, may defer |
| **🟡 MAJOR** | Missing response_model, business logic in handler | Should fix |
| **🔵 MINOR** | Style issues, missing descriptions | Consider fixing |
| **⚪ SUGGESTION** | Improvements beyond requirements | Optional |
| **🟢 COMMENDATION** | Excellent patterns observed | Positive reinforcement |

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

### ✅ Correct Pattern

```python
@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(*, data: UserCreate, service: UserServiceDep) -> User:
    """Create a new user account."""
    return await service.create(data)
```

**Why:** Explicit response_model, correct 201 status, async handler, thin delegation.

### ❌ Anti-Pattern

```python
@router.post("/")
async def create_user(data: dict, db: Session):
    user = User(**data)
    db.add(user)
    db.commit()
    return {"status": "ok", "user": user.__dict__}
```

**Why:** No response_model, dict input, ORM leak, business logic, wrong return.

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
```

---

## Summary Format

```markdown
# API Review Summary

## Verdict: {{EMOJI}} {{VERDICT}}

| Metric | Count |
|--------|-------|
| Files Reviewed | N |
| Blockers | N |
| Critical | N |
| Major | N |

## Key Findings
1. {{FINDING_1}}
2. {{FINDING_2}}

## Chain Decision
{{CHAIN_EXPLANATION}}
```

---

## Skill Chaining

| Verdict | Action | Target |
|---------|--------|--------|
| `FAIL` | Mandatory fixes | `implement/api` |
| `NEEDS_WORK` | Targeted fixes | `implement/api` |
| `PASS` | Continue | Next review dimension |

### Handoff Protocol

```markdown
**Chain Target:** `implement/api`
**Priority Findings:** {{BLOCKER_AND_CRITICAL_IDS}}
**Constraint:** Preserve existing tests and contracts
```

---

## Quality Gates

Before finalizing review:

- [ ] All route files in scope analyzed
- [ ] Each finding has location + criterion + severity
- [ ] Verdict matches severity distribution
- [ ] Actionable suggestions for non-PASS verdicts
- [ ] Chain decision explicit and justified
