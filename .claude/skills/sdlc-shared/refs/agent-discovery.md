# Agent Discovery

> How orchestrator skills dynamically discover, categorize, and propose agents from `.claude/agents/`.

---

## Discovery Algorithm

### Step 1: Scan the Agents Directory

List all `.md` files in `.claude/agents/`:

```bash
ls .claude/agents/*.md
```

Each file represents one agent. The filename encodes both the domain and the role.

### Step 2: Parse Filename for Role Detection

Split the filename (without `.md`) on `-`. The **last segment** is the role. Everything before it is the domain.

```
api-architect.md        → domain: "api",              role: "architect"
python-implementer.md   → domain: "python",           role: "implementer"
unit-tests-reviewer.md  → domain: "unit-tests",       role: "reviewer"
observability-engineer.md → domain: "observability",   role: "engineer"
tasks-planner.md        → domain: "tasks",            role: "planner"
performance-optimizer.md → domain: "performance",      role: "optimizer"
```

### Step 3: Categorize by Role

Map the extracted role to an SDLC phase using this table:

| Filename suffix | Role category | Primary SDLC phases |
|----------------|---------------|---------------------|
| `*-analyst.md` | analyst | discover |
| `*-architect.md` | architect | design |
| `*-planner.md` | planner | breakdown |
| `*-implementer.md` | implementer | implement, refactor |
| `*-engineer.md` | observer | observe |
| `*-optimizer.md` | optimizer | optimize |
| `*-tester.md` | tester | test |
| `*-reviewer.md` | reviewer | review |

### Step 4: Read Agent Description

For each candidate agent, read the `description` field from the YAML frontmatter. This provides:

- **Domain expertise** — what the agent specializes in (e.g., "REST API design", "data models and repositories")
- **Capabilities** — what the agent can produce (e.g., "OpenAPI specs", "Pydantic models")
- **Trigger context** — when the agent is most useful

Use this description to match agents to the specific task context. An `api-implementer` is relevant when the task involves HTTP endpoints; a `data-implementer` is relevant when it involves persistence.

### Step 5: Handle Unrecognized Roles

If an agent filename's last segment doesn't match any known role in the table above:

1. Read the agent's `description` from frontmatter
2. Look for role keywords: "analyze", "architect", "design", "implement", "build", "test", "review", "optimize", "observe", "instrument", "plan", "break down"
3. Map the keyword to the closest role category
4. If still ambiguous, include the agent in the proposal with a note asking the user to confirm its role

This fallback ensures new agents with unconventional names still get discovered.

---

## Building the Proposal Table

After discovering and categorizing agents, present them to the user in a structured table.

### Proposal Table Format

```markdown
| # | Agent Name | Subagent Type | Task-Specific Action | Estimated Scope |
|---|------------|---------------|----------------------|-----------------|
| 1 | requirements-analyst | requirements-analyst | Elicit and structure requirements from README | M |
| 2 | scope-analyst | scope-analyst | Define scope boundaries and risk register | S |
```

### Column Definitions

| Column | Description |
|--------|-------------|
| **#** | Sequential number for easy reference during user approval |
| **Agent Name** | The agent's name from its frontmatter (human-readable) |
| **Subagent Type** | The `subagent_type` value to pass to the Task tool — matches the agent filename without `.md` |
| **Task-Specific Action** | A one-sentence description of what this agent will do for this specific task, derived from the agent's description and the current context |
| **Estimated Scope** | S (small, <30 min), M (medium, 30-60 min), L (large, 60+ min) — based on the task complexity for this agent |

### Deriving Task-Specific Actions

Don't just copy the agent's generic description. Tailor the action to the current context:

```
❌ Generic: "Elicit requirements from stakeholder input"
✅ Specific: "Structure authentication requirements from the OAuth2 integration brief"

❌ Generic: "Review Python code for quality"
✅ Specific: "Review the CreateProduct flow for modularity and error handling"
```

Read the task context (feature README, PRD sections, task details from breakdown) and combine it with the agent's domain expertise to produce a specific, actionable description.

---

## Filtering Agents by Relevance

Not every agent of a matching role is relevant to every task. Apply these filtering heuristics:

### For Implementer Proposals (`/implement`)

Match agent domains to task requirements:

| Task mentions | Propose |
|---------------|---------|
| API endpoints, routes, HTTP, REST | `api-implementer` |
| Database, models, persistence, queries, migrations | `data-implementer` |
| Events, handlers, consumers, producers, messages | `event-implementer` |
| React, components, UI, frontend | `react-implementer` |
| Kubernetes, deployments, Helm, K8s | `kubernetes-implementer` |
| Pulumi, infrastructure, IaC, cloud resources | `pulumi-implementer` |
| Python logic, domain, flows, services | `python-implementer` |

### For Reviewer Proposals (`/review`)

Analyze changed files to determine domains:

| Changed file patterns | Propose |
|-----------------------|---------|
| `routes/`, `api/` | `api-reviewer` |
| `models/`, `adapters/`, `migrations/` | `data-reviewer` |
| `handlers/`, `consumers/`, `publishers/` | `event-reviewer` |
| `.tsx`, `.ts`, `components/` | `react-reviewer` |
| `k8s/`, `deploy/`, `helm/` | `kubernetes-reviewer` |
| `pulumi/`, `__main__.py` (in deploy/) | `pulumi-reviewer` |
| Any `.py` files | `python-reviewer` (cross-cutting) |
| Any code changes | `performance-reviewer` (cross-cutting) |
| Any instrumented code | `observability-reviewer` (cross-cutting) |
| `tests/unit/` | `unit-tests-reviewer` |
| `tests/integration/` | `integration-tests-reviewer` |
| `tests/contract/` | `contract-tests-reviewer` |
| `tests/e2e/` | `e2e-tests-reviewer` |
| `tests/ui/` | `ui-tests-reviewer` |

### For Architect Proposals (`/design-system` + `/design-lld`)

Group architects into two tiers:

- **HLD candidates**: Agents with `system-` prefix (e.g., `system-architect`) — propose for high-level design
- **LLD candidates**: All other `*-architect` agents — propose for low-level design

### Always Propose

Some agents are cross-cutting and should always be proposed for their phase regardless of domain:

- `/review`: `python-reviewer`, `performance-reviewer`, `observability-reviewer`
- `/implement`: `python-implementer` (when any Python code is involved)

---

## Dispatching Agents via the Task Tool

After user approval, dispatch agents using the Task tool with these parameters:

```
Task tool call:
  subagent_type: "{agent-filename-without-md}"   # e.g., "api-implementer"
  description: "{3-5 word summary}"               # e.g., "Implement API endpoints"
  prompt: "{detailed task prompt with context}"
```

The prompt passed to each agent should include:

1. **Feature context**: Feature directory path, feature name
2. **Task context**: Selected task details, sub-tasks, definition of done
3. **Design artifacts**: Relevant sections from lld.md, hld.md, PRD
4. **Scope boundaries**: What this specific agent should produce (not overlap with other agents)
5. **Output location**: Where to write artifacts

Dispatch all approved agents in a **single message** with multiple Task tool calls to enable parallel execution. See `propose-approve-execute.md` for batching rules when >6 agents are approved.
