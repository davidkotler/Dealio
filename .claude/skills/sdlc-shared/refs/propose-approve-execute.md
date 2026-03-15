# Propose-Approve-Execute

> The interaction pattern every orchestrator skill uses to present agent teams, collect user approval, and dispatch agents in parallel.

---

## Purpose

No agent runs without explicit user approval. Every orchestrator skill follows the same three-step cycle:

1. **Propose** — analyze context, discover relevant agents, present a proposal table
2. **Approve** — user reviews, modifies, and approves the agent team
3. **Execute** — dispatch all approved agents in parallel via the Task tool

This pattern ensures the user controls what runs while the orchestrator handles the complexity of agent discovery, context preparation, and parallel dispatch.

---

## Step 1: Propose

After resolving the feature directory, passing the phase gate, and discovering relevant agents (per `agent-discovery.md`), present the proposal table.

### Proposal Table Format

```markdown
## Proposed Agent Team

| # | Agent Name | Subagent Type | Task-Specific Action | Estimated Scope |
|---|------------|---------------|----------------------|-----------------|
| 1 | requirements-analyst | requirements-analyst | Elicit and structure authentication requirements from the OAuth2 brief | M |
| 2 | scope-analyst | scope-analyst | Define scope boundaries, identify risks, and estimate effort for the auth feature | S |
```

### Column Descriptions

- **#**: Sequential number — used by the user to reference agents when modifying the proposal
- **Agent Name**: Human-readable name from the agent's frontmatter
- **Subagent Type**: The value passed to `Task(subagent_type=...)` — the agent filename without `.md`
- **Task-Specific Action**: What this agent will do for *this specific task*, not its generic description
- **Estimated Scope**: S (focused, single concern), M (moderate, multiple concerns), L (broad, cross-cutting)

### Grouping (When Applicable)

Some skills group agents into logical batches. For example, `/design-system` and `/design-lld` separate HLD and LLD candidates:

```markdown
## Proposed Agent Team

### HLD Architects (High-Level Design)
| # | Agent Name | Subagent Type | Task-Specific Action | Estimated Scope |
|---|------------|---------------|----------------------|-----------------|
| 1 | system-architect | system-architect | Define service boundaries and integration patterns for the payments domain | L |

### LLD Architects (Low-Level Design)
| # | Agent Name | Subagent Type | Task-Specific Action | Estimated Scope |
|---|------------|---------------|----------------------|-----------------|
| 2 | api-architect | api-architect | Design REST API contracts for payment endpoints | M |
| 3 | data-architect | data-architect | Design payment data model and persistence strategy | M |
| 4 | event-architect | event-architect | Design payment event schemas and async flows | M |
```

---

## Step 2: Approve

After presenting the proposal, wait for user response. The user can:

### Approve As-Is

User says "approve", "go", "looks good", "yes", or similar → proceed to execution with the full proposed team.

### Remove Agents

User says "remove 3" or "drop the event-architect" → remove the specified agents and confirm the updated list before executing.

```
User: "Remove 3 and 4"
→ Updated team: agents 1 and 2 only. Proceed?
```

### Add Agents

User says "also add the kubernetes-architect" → add the specified agent to the proposal, generate a task-specific action for it, and confirm.

```
User: "Add kubernetes-architect"
→ Added: kubernetes-architect — Design K8s deployment manifests for the payment service (M)
→ Updated team: agents 1, 2, 3, 4, 5. Proceed?
```

### Modify Actions or Scope

User says "change agent 2's action to focus on GraphQL instead of REST" → update the action and confirm.

### Replace the Entire Proposal

User provides a fundamentally different direction → rebuild the proposal based on their feedback.

### Key Rule

**Never execute without explicit approval.** If the user's response is ambiguous, ask for clarification. Silence is not consent.

---

## Step 3: Execute

### Dispatching Agents

Dispatch all approved agents via the Task tool in a **single message** with multiple tool calls. This enables parallel execution — all agents work simultaneously.

```
Message with N tool calls:
├── Task(subagent_type="requirements-analyst", prompt="...", description="Elicit requirements")
├── Task(subagent_type="scope-analyst", prompt="...", description="Define scope")
└── Task(subagent_type="api-architect", prompt="...", description="Design API contracts")
```

### Agent Prompt Template

Each dispatched agent receives a structured prompt:

```markdown
## Context

**Feature:** {feature-name}
**Feature Directory:** {feature-dir-path}
**Phase:** {current SDLC phase}
**Task:** {task name, if applicable}

## Your Assignment

{Task-specific action from the approved proposal table}

## Artifacts to Read

{List of relevant files the agent should read for context — e.g., prd.md, lld.md sections, README.md}

## Artifacts to Produce

{What the agent should write and where — e.g., "Write your findings to {feature-dir}/reviews/{task-name}/api-reviewer.md"}

## Design Constraints

{Relevant design decisions, constraints, or scope boundaries from the feature artifacts}

## Definition of Done

{Specific completion criteria for this agent's work}
```

### Batching Rule (>6 Agents)

If more than 6 agents are approved, batch them into groups of 6:

1. Dispatch the first batch (agents 1-6) in a single message
2. Wait for all agents in the batch to complete
3. Present a brief summary of batch 1 results
4. Dispatch the next batch (agents 7-12) in a single message
5. Repeat until all batches are dispatched

The cap of 6 agents per batch prevents context window pressure from accumulated agent outputs. This number can be tuned based on experience.

### Sequential Groups (When Required)

Some skills require sequential execution of groups — for example, `/design-system` runs HLD agents first, then `/design-lld` runs LLD agents (so LLD agents can reference the HLD output):

1. Dispatch HLD group → wait for completion
2. Dispatch LLD group (with HLD output as additional context) → wait for completion

The skill specifies when sequential ordering between groups is needed. Within each group, agents always run in parallel.

---

## After Execution: Result Collection

### Summary Presentation

After all agents complete, present a summary to the user:

```markdown
## Execution Summary

| Agent | Status | Artifacts Produced | Key Outcomes |
|-------|--------|-------------------|--------------|
| requirements-analyst | ✅ Complete | prd.md | 6 FRs, 4 NFRs defined |
| scope-analyst | ✅ Complete | prd.md (scope section) | 3 risks identified, M effort |
```

### Handling Failures

If an agent fails or produces incomplete output:

1. Report the failure clearly in the summary
2. Include any partial output or error details
3. Ask the user whether to: retry the agent, skip it, or adjust and re-dispatch

Do not silently drop failed agents from the summary.

---

## Interaction Flow Diagram

```
Orchestrator Skill Starts
        │
        ▼
  Resolve Feature Directory (refs/feature-resolution.md)
        │
        ▼
  Phase Gate Check (refs/phase-gating.md)
        │
        ├─► Gate fails → Block with message → END
        │
        ▼
  Discover Agents (refs/agent-discovery.md)
        │
        ▼
  Build Proposal Table
        │
        ▼
  Present to User ◄──────────────────┐
        │                            │
        ▼                            │
  User Responds                      │
        │                            │
        ├─► Approve → Execute        │
        ├─► Modify → Update table ───┘
        └─► Reject → END

  Execute
        │
        ├─► Dispatch agents (parallel, batched if >6)
        │
        ▼
  Collect Results
        │
        ▼
  Present Summary
        │
        ▼
  Append SDLC Log Entry (refs/sdlc-log-format.md)
        │
        ▼
  END
```
