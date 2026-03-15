# Claude Code SKILL Generator/Optimizer

> Use this prompt to generate new SKILLs or optimize existing ones for Claude Code v2.0+ architecture.

---

## Context

You are a **Claude Code SKILL Architect**. Your task is to generate or optimize a SKILL that follows the progressive disclosure pattern, maximizes discoverability, and integrates cleanly into multi-skill workflows.

A SKILL is a **model-invoked** unit of portable expertise. Unlike Commands (user-invoked via `/`), SKILLs activate automatically when Claude determines they're relevant based on the description matching the user's request.

---

## Input Requirements

Before generating/optimizing a SKILL, gather:

1. **Domain**: What expertise does this SKILL encode? (e.g., "PDF form filling", "Python FastAPI development", "Git commit message generation")
2. **Trigger Scenarios**: When should Claude auto-invoke this SKILL? List 3-5 concrete user requests that should activate it.
3. **Upstream Skills**: Which existing SKILLs might chain INTO this one?
4. **Downstream Skills**: Which SKILLs should this one invoke for sub-tasks?
5. **Tool Requirements**: Which tools does this SKILL need? (Read, Write, Edit, Bash, Grep, Glob, WebFetch, etc.)
6. **Dependencies**: External packages or binaries required (e.g., `pypdf`, `ffmpeg`)
7. **Existing Assets**: Templates, scripts, or reference docs to bundle

---

## Output Structure

Generate a complete SKILL directory with this structure:

```
.claude/skills/<skill-name>/
├── SKILL.md              # Core instructions (REQUIRED, <300 lines)
├── refs/                 # Reference documentation (loaded on-demand)
│   ├── patterns.md       # Common patterns and examples
│   ├── troubleshooting.md
│   └── api-reference.md
├── scripts/              # Executable automation
│   └── validate.sh
├── assets/               # Templates and static files
│   └── template.json
└── examples/             # Concrete examples for few-shot learning
    ├── input-1.md
    └── output-1.md
```

---

## SKILL.md Template

```yaml
---
# ══════════════════════════════════════════════════════════════
# METADATA (Always loaded - keep under ~100 tokens)
# ══════════════════════════════════════════════════════════════
name: <kebab-case-identifier>
version: 1.0.0

# ┌─────────────────────────────────────────────────────────────┐
# │ DESCRIPTION: THE MOST CRITICAL FIELD                        │
# │                                                             │
# │ Claude uses this to determine relevance. Include:           │
# │ • Primary capability (what it does)                         │
# │ • Trigger phrases (when to use)                             │
# │ • File types/domains (context signals)                      │
# │                                                             │
# │ Pattern: "<Capability>. Use when <trigger conditions>."     │
# └─────────────────────────────────────────────────────────────┘
description: |
  <One-line capability statement>.
  Use when <trigger condition 1>, <trigger condition 2>, or <trigger condition 3>.
  Relevant for <file-types/domains>.

# Tool permissions (principle of least privilege)
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash(npm run lint:*)
  - Bash(pytest:*)

# External dependencies
dependencies:
  - <package-name>

# Lifecycle hooks (deterministic automation)
hooks:
  PostToolUse:
    - matcher: "Write|Edit"
      command: "./scripts/validate.sh $FILEPATH"
---

# <Skill Name>

> <One-sentence value proposition>

## Quick Reference

| Aspect | Details |
|--------|---------|
| **Invokes** | `<downstream-skill-1>`, `<downstream-skill-2>` |
| **Invoked By** | `<upstream-skill-1>`, `<upstream-skill-2>` |
| **Key Tools** | `<tool-1>`, `<tool-2>` |

---

## Core Workflow

<Step-by-step process, numbered, imperative voice>

1. **Analyze**: <What to examine first>
2. **Plan**: <Decision framework>
3. **Execute**: <Primary actions>
4. **Validate**: <Quality checks>
5. **Chain**: <When to invoke downstream skills>

---

## Decision Tree

```
User Request
    │
    ├─► Condition A? ──► Action A
    │
    ├─► Condition B? ──► Action B
    │                      └──► Invoke: <sub-skill>
    │
    └─► Condition C? ──► Action C
                           └──► Invoke: <different-sub-skill>
```

---

## Skill Chaining

### Invoke Downstream Skills When:

| Condition | Invoke | Rationale |
|-----------|--------|-----------|
| <trigger-condition> | `.claude/skills/<skill-name>/` | <why> |
| <trigger-condition> | `.claude/skills/<skill-name>/` | <why> |

### Chaining Syntax

When chaining is needed, output:

```markdown
**Invoking Sub-Skill:** `<skill-name>`
**Reason:** <brief justification>
**Handoff Context:** <key information the sub-skill needs>
```

---

## Patterns & Anti-Patterns

### ✅ Do

- <Best practice 1>
- <Best practice 2>
- <Best practice 3>

### ❌ Don't

- <Anti-pattern 1>
- <Anti-pattern 2>
- <Anti-pattern 3>

---

## Examples

### Example 1: <Scenario Name>

**Input:**
```
<user request>
```

**Output:**
```
<expected response/action>
```

---

## Deep References

For detailed guidance, load these refs as needed:

- **[patterns.md](refs/patterns.md)**: Extended patterns and edge cases
- **[troubleshooting.md](refs/troubleshooting.md)**: Common issues and solutions
- **[api-reference.md](refs/api-reference.md)**: API specifications

---

## Quality Gates

Before completing any task using this skill:

- [ ] <Validation check 1>
- [ ] <Validation check 2>
- [ ] <Validation check 3>




```

---

## Generation Rules

### Rule 1: Description-First Design

The `description` field determines discoverability. Apply this formula:

```
description = <capability> + <trigger_phrases> + <context_signals>
```

**Bad:**
```yaml
description: Helps with Python code
```

**Good:**
```yaml
description: |
  Generate type-safe FastAPI route handlers with Pydantic models.
  Use when creating REST endpoints, API routes, or HTTP handlers.
  Relevant for Python backend development, OpenAPI specs.
```

### Rule 2: Context Economy (<300 Lines)

SKILL.md is loaded when relevant—every token counts.

| Section | Target Length | Purpose |
|---------|---------------|---------|
| Frontmatter | <100 tokens | Always loaded for matching |
| Quick Reference | <50 tokens | Orientation |
| Core Workflow | <150 tokens | Primary instructions |
| Decision Tree | <100 tokens | Branching logic |
| Skill Chaining | <100 tokens | Composition rules |
| Patterns | <150 tokens | Guardrails |
| Examples | <200 tokens | Few-shot grounding |

**Total SKILL.md: <850 tokens (~250-300 lines)**

Offload everything else to `refs/`.

### Rule 3: Explicit Chaining Contracts

Skills must declare their integration points:

```yaml
# In SKILL.md frontmatter or body
chains:
  invokes:
    - skill: implement/database
      when: "Query construction, schema changes"
    - skill: test/unit
      when: "After implementation complete"
  invoked-by:
    - skill: implement/python
      context: "When FastAPI routes are detected"
```

### Rule 4: Tool Minimalism

Request only necessary tools with specific patterns:

```yaml
# ❌ Over-permissioned
allowed-tools:
  - Bash

# ✅ Scoped permissions
allowed-tools:
  - Bash(npm run:*)
  - Bash(pytest:*)
  - Bash(git diff:*)
```

### Rule 5: Deterministic Hooks Over Instructions

For critical validations, use hooks instead of instructions:

```yaml
# ❌ Relying on LLM compliance
# "Always run linting after editing files"

# ✅ Deterministic enforcement
hooks:
  PostToolUse:
    - matcher: "Write|Edit"
      command: "npm run lint --fix $FILEPATH"
```

### Rule 6: Progressive Disclosure Structure

```
SKILL.md (Always loaded when relevant)
    │
    ├── Quick decisions, core workflow
    │
    └── refs/ (Loaded on-demand)
            │
            ├── patterns.md      → "For advanced patterns, see refs/patterns.md"
            ├── edge-cases.md    → "For edge cases, see refs/edge-cases.md"
            └── api-reference.md → "For API details, see refs/api-reference.md"
```

### Rule 7: Composability Over Completeness

A skill should do ONE thing well and chain to others:

```
# ❌ Monolithic skill trying to do everything
skills/full-stack-development/
    └── SKILL.md (2000 lines, covers everything)

# ✅ Composable skill network
skills/
├── implement/
│   ├── python/      → chains to: api, database, pydantic
│   ├── api/         → chains to: validation, auth
│   └── database/    → chains to: migration
├── test/
│   ├── unit/
│   └── integration/
└── review/
    └── security/
```

---

## Optimization Checklist


When reviewing/optimizing an existing SKILL:



### Discovery & Activation


- [ ] Description includes 3+ trigger phrases


- [ ] Description mentions relevant file types/domains
- [ ] Name is kebab-case and intuitive




### Context Efficiency



- [ ] SKILL.md is under 300 lines
- [ ] No inline reference material (moved to refs/)

- [ ] Examples are minimal but representative



### Composability

- [ ] Downstream skills are explicitly declared


- [ ] Handoff context is specified for each chain
- [ ] No duplicated logic from other skills

### Safety & Determinism


- [ ] Tools follow least-privilege principle
- [ ] Critical validations use hooks, not instructions
- [ ] Dangerous operations are gated or prohibited

### Maintainability

- [ ] Version field is present
- [ ] Examples cover happy path + 1 edge case
- [ ] Quality gates are testable

---

## Skill Chaining Patterns

### Pattern 1: Sequential Pipeline

```
implement/python
    └──► implement/api (when: route handlers detected)
            └──► implement/database (when: queries needed)
                    └──► test/unit (when: implementation complete)
```

### Pattern 2: Conditional Branch

```
implement/python
    ├──► implement/api      (when: HTTP routes)
    ├──► implement/cli      (when: CLI commands)
    └──► implement/worker   (when: background jobs)
```

### Pattern 3: Validation Loop

```
implement/* ──► review/types ──► [PASS] ──► optimize/*
                    │
                    └──► [FAIL] ──► implement/* (fix types)
```

### Pattern 4: Subagent Delegation

For parallel or isolated execution, delegate to a subagent with preloaded skills:

```yaml
# In .claude/agents/code-reviewer.md
---
name: code-reviewer
skills:
  - review/security
  - review/performance
  - review/types
---
```

Then invoke from main conversation: "Spawn the code-reviewer agent to analyze these changes."

---

## Example: Complete SKILL Generation

**Input Request:**
> Generate a SKILL for Python FastAPI development

**Generated Output:**

```yaml
---
name: implement-fastapi
version: 1.0.0
description: |
  Generate type-safe FastAPI route handlers with Pydantic models and dependency injection.
  Use when creating REST endpoints, API routes, HTTP handlers, or OpenAPI-documented services.
  Relevant for Python backend development, async APIs, Pydantic schemas.
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash(pytest:*)
  - Bash(uvicorn:*)
dependencies:
  - fastapi
  - pydantic
  - uvicorn
hooks:
  PostToolUse:
    - matcher: "Write|Edit"
      paths: ["**/routes/**/*.py", "**/api/**/*.py"]
      command: "ruff check --fix $FILEPATH && ruff format $FILEPATH"
---

# FastAPI Implementation

> Generate production-ready FastAPI endpoints with type safety and OpenAPI docs.

## Quick Reference

| Aspect | Details |
|--------|---------|
| **Invokes** | `implement/pydantic`, `implement/database`, `test/unit` |
| **Invoked By** | `implement/python` |
| **Key Tools** | Write, Edit, Bash(pytest) |

---

## Core Workflow

1. **Analyze**: Examine existing route structure in `src/api/` or `app/routes/`
2. **Model**: Define Pydantic request/response models first
3. **Route**: Implement async route handler with type hints
4. **Inject**: Add dependencies (auth, db session) via `Depends()`
5. **Validate**: Run `pytest` on new endpoint
6. **Chain**: Invoke `test/unit` for comprehensive coverage

---

## Skill Chaining

| Condition | Invoke | Handoff Context |
|-----------|--------|-----------------|
| Complex request/response shapes | `implement/pydantic` | Model field requirements |
| Database queries needed | `implement/database` | Table names, query type |
| Implementation complete | `test/unit` | Route path, expected responses |

---

## Patterns

### ✅ Do

- Use `async def` for all route handlers
- Define explicit `response_model` on decorators
- Group related routes in `APIRouter`

### ❌ Don't

- Mix business logic in route handlers
- Use `Any` type annotations
- Skip Pydantic validation for request bodies

---

## Example

**Input:** "Create an endpoint to fetch user by ID"

**Output:**
```python
from fastapi import APIRouter, Depends, HTTPException
from app.models.user import UserResponse

from app.services.user import UserService

router = APIRouter(prefix="/users", tags=["users"])

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: int, service: UserService = Depends()):

    user = await service.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
```


---

## Deep References


- **[patterns.md](refs/patterns.md)**: Auth patterns, pagination, error handling
- **[testing.md](refs/testing.md)**: TestClient usage, fixture patterns

```

---

## Final Validation

After generating a SKILL, verify:

1. **Discoverability Test**: "Would Claude invoke this for the intended triggers?"
2. **Token Budget Test**: "Is SKILL.md under 300 lines?"
3. **Chaining Test**: "Are all integration points declared?"
4. **Safety Test**: "Are dangerous operations gated?"
5. **Duplication Test**: "Does this duplicate any existing skill?"


# Task



## Notes
- Think for very long and use as many resources as possible.
- Optimize the review SKILL markdown document for Claude Code
- Review and improve the document before submitting.
- Write another document that explains the document and gives a reason for every point
every point
