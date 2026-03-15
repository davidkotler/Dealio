---
name: review-coherence
version: 1.0.0

description: |
  Review code for coherence with existing codebase patterns, terminology, and structure.
  Evaluates terminological consistency, structural uniformity, behavioral alignment, and pattern adherence.
  Use when reviewing new implementations, validating pattern compliance, or assessing codebase consistency.
  Relevant for any code changes, new modules, refactoring, or cross-team contributions.
chains:
  invoked-by:
    - skill: implement/python
      context: "Post-implementation coherence validation"
    - skill: implement/api
      context: "API pattern consistency check"
    - skill: implement/react
      context: "Component pattern alignment"
    - skill: review/style
      context: "Style coherence complement"
  invokes:
    - skill: implement/python
      when: "Critical or major coherence violations detected"
    - skill: review/modularity
      when: "Structural incoherence suggests boundary issues"
---

# Coherence Review

> Validate that new code reads as if written by the same mind that wrote the existing codebase.

## Quick Reference

| Aspect | Details |
|--------|---------|
| **Dimension** | Coherence (Conceptual Unity) |
| **Scope** | Terminology, structure, patterns, abstractions, interfaces |
| **Invoked By** | `implement/*`, `/review` command |
| **Invokes** | `implement/*` (on failure), `review/modularity` |
| **Verdict Options** | `PASS` · `PASS_WITH_SUGGESTIONS` · `NEEDS_WORK` · `FAIL` |

---

## Review Objective

Ensure every code change maintains conceptual unity—consistent terminology, uniform patterns, predictable structure, and aligned abstractions—making the system learnable, navigable, and evolvable.

### This Review Answers

1. Does this code use the same terminology as the existing codebase?
2. Does the structure mirror peer modules and components?
3. Are similar problems solved using established patterns?
4. Is the abstraction level uniform within components?

### Out of Scope

- Functional correctness (see `review/functionality`)
- Performance optimization (see `review/performance`)
- Security vulnerabilities (see `review/security`)

---

## Core Workflow

```
┌─────────────────────────────────────────────────────────────┐
│                  COHERENCE REVIEW WORKFLOW                  │
├─────────────────────────────────────────────────────────────┤
│  1. SCOPE    →  Identify changed/new files                  │
│  2. CONTEXT  →  Find peer modules and established patterns  │
│  3. ANALYZE  →  Compare against coherence dimensions        │
│  4. CLASSIFY →  Assign severity to each deviation           │
│  5. VERDICT  →  Determine pass/fail based on findings       │
│  6. REPORT   →  Output structured review results            │
│  7. CHAIN    →  Invoke implementation skills if needed      │
└─────────────────────────────────────────────────────────────┘
```

### Step 1: Scope Definition

Identify review targets:

```bash
# Find changed files in current work
git diff --name-only HEAD~1
# Or for new modules
find src/ -type f -name "*.py" -newer .git/ORIG_HEAD
```

### Step 2: Context Loading

Before analysis, discover existing patterns:

```bash
# Find peer modules for structural comparison
ls -la $(dirname $TARGET_FILE)/
# Find similar named files across codebase
find src/ -name "*service*.py" -o -name "*repository*.py"
# Grep for terminology patterns
grep -r "class.*Service" src/ --include="*.py" | head -20
```

**Load these references:**







- **Principles:** `rules/principles.md` → DRY, naming conventions, patterns
- **Coherence Guide:** `skills/design/code/refs/coherence.md` → Coherence dimensions
- **Domain Glossary:** `docs/glossary.md` → Ubiquitous language terms

### Step 3: Systematic Analysis

Evaluate against criteria in priority order:

| Priority | Criterion Category | Weight |
|----------|-------------------|--------|
| P0 | Terminological Coherence | Blocker |
| P1 | Structural Coherence | Critical |
| P2 | Behavioral Coherence | Major |
| P3 | Interface Coherence | Minor |

### Step 4: Severity Classification

| Severity | Definition | Action Required |
|----------|------------|-----------------|
| **🔴 BLOCKER** | Introduces conflicting terminology or fundamentally different patterns | Must fix before merge |
| **🟠 CRITICAL** | Creates structural inconsistency or new approach to solved problem | Must fix, may defer |
| **🟡 MAJOR** | Deviates from established conventions without documented reason | Should fix |
| **🔵 MINOR** | Small stylistic inconsistencies or naming variations | Consider fixing |
| **⚪ SUGGESTION** | Opportunity to improve coherence proactively | Optional improvement |
| **🟢 COMMENDATION** | Exemplary pattern adherence or coherence improvement | Positive reinforcement |

### Step 5: Verdict Determination

```
Findings Analysis
       │
       ├─► Any BLOCKER? ──────────────► FAIL
       │   (conflicting terms, third pattern)
       │
       ├─► Any CRITICAL? ─────────────► NEEDS_WORK
       │   (structural deviation, new convention)
       │
       ├─► Multiple MAJOR? ───────────► NEEDS_WORK
       │   (>2 pattern deviations)
       │
       ├─► Few MAJOR or MINOR only? ──► PASS_WITH_SUGGESTIONS
       │
       └─► SUGGESTION/COMMENDATION ───► PASS
```

---

## Evaluation Criteria

### TC: Terminological Coherence

| ID | Criterion | Severity | Check |
|----|-----------|----------|-------|
| TC.1 | Domain terms match glossary exactly | BLOCKER | No synonyms for established concepts |
| TC.2 | Class/function names use codebase conventions | CRITICAL | Same concept = same name everywhere |
| TC.3 | Variable naming follows local patterns | MAJOR | Consistent abbreviations and styles |

**Detection commands:**
```bash
# Find terminology variations
grep -rn "customer\|client\|user\|buyer" src/ --include="*.py" | sort | uniq -c
# Check for synonym usage
grep -rn "order\|purchase\|transaction" src/ --include="*.py"
```

### SC: Structural Coherence

| ID | Criterion | Severity | Check |
|----|-----------|----------|-------|
| SC.1 | Module structure mirrors peer modules | CRITICAL | Same files, same organization |
| SC.2 | Directory hierarchy follows conventions | MAJOR | Predictable location for each artifact |
| SC.3 | File naming matches established patterns | MAJOR | `service.py` not `svc.py` or `services.py` |

**Detection commands:**
```bash
# Compare module structure
diff <(ls -1 src/orders/) <(ls -1 src/shipments/)
# Find structural outliers
find src/ -type d -exec sh -c 'ls -1 "{}" | sort' \; | sort | uniq -c | sort -rn
```

### BC: Behavioral Coherence

| ID | Criterion | Severity | Check |
|----|-----------|----------|-------|
| BC.1 | Similar problems use identical solutions | BLOCKER | No third pattern when two exist |
| BC.2 | Error handling follows established strategy | CRITICAL | Exceptions vs Result types consistent |
| BC.3 | Async/sync patterns match peer code | MAJOR | All I/O async if codebase is async |

**Detection commands:**
```bash
# Find error handling patterns
grep -rn "raise\|return None\|Result\[" src/ --include="*.py" | head -30
# Check async consistency
grep -rn "async def\|def " src/ --include="*.py" | grep -v "test"
```

### IC: Interface Coherence

| ID | Criterion | Severity | Check |
|----|-----------|----------|-------|
| IC.1 | Method signatures match peer interfaces | MAJOR | Same parameter order, types, return style |
| IC.2 | Constructor patterns align | MAJOR | Same dependency injection style |
| IC.3 | Return types follow conventions | MINOR | `Result[T, E]` if others use it |

---

## Patterns & Anti-Patterns

### ✅ Indicators of Coherence

```python
# Existing pattern in codebase:
class OrderService:
    def __init__(self, repo: OrderRepository, events: EventPublisher):
        self._repo = repo
        self._events = events

# ✅ New code follows the pattern exactly
class ShipmentService:
    def __init__(self, repo: ShipmentRepository, events: EventPublisher):
        self._repo = repo
        self._events = events
```

**Why this works:** Same naming (`Service`), same dependencies style, same attribute naming (`_repo`, `_events`). The codebase reads as one cohesive system.

### ❌ Red Flags (Incoherence Indicators)

```python
# ❌ BLOCKER: Introduces conflicting terminology
class ShippingManager:  # "Manager" vs "Service", "Shipping" vs "Shipment"
    def __init__(self, db: Database):  # Different dependency style
        self.database = db  # Different attribute naming (_repo vs database)
```

**Why this fails:** Creates a "snowflake" implementation. Future developers won't know which pattern to follow. Codebase now has two conventions.

### ❌ The Third Pattern Anti-Pattern

```python
# Discovery: Two date formatting approaches exist
# Approach A (3 usages): datetime.strftime("%Y-%m-%d")
# Approach B (12 usages): date.isoformat()

# ❌ BLOCKER: Adding a third approach
formatted = f"{date.year}-{date.month:02d}-{date.day:02d}"

# ✅ Correct: Use the dominant pattern (B) and create migration ticket
```

### ❌ The Historical Layers Anti-Pattern

```python
# ❌ Codebase shows geological strata of different eras
# 2019 layer: raw SQL, no types
def get_user(user_id):
    return db.execute(f"SELECT * FROM users WHERE id = {user_id}")

# 2024 layer: async, repository pattern  
async def get_user(user_id: UserId) -> User | None:
    return await user_repository.find_by_id(user_id)

# New code MUST use 2024 pattern OR include migration plan
```

---

## Finding Output Format

```markdown
### [{{SEVERITY_EMOJI}} {{SEVERITY}}] {{FINDING_TITLE}}

**Location:** `{{FILE_PATH}}:{{LINE_NUMBER}}`
**Criterion:** {{CRITERION_ID}} - {{CRITERION_NAME}}
**Peer Reference:** `{{PEER_FILE_PATH}}` (established pattern)

**Issue:**
{{DESCRIPTION_OF_DEVIATION}}

**Evidence:**
\`\`\`python
# Your code:
{{INCOHERENT_CODE}}

# Established pattern (from {{PEER_FILE}}):
{{COHERENT_PATTERN}}
\`\`\`

**Suggestion:**
{{SPECIFIC_REMEDIATION}}

**Rationale:**
{{WHY_COHERENCE_MATTERS_HERE}}
```

---

## Review Summary Format

```markdown
# Coherence Review Summary

## Verdict: {{VERDICT_EMOJI}} {{VERDICT}}

| Metric | Count |
|--------|-------|
| Files Reviewed | {{COUNT}} |
| Peer Modules Compared | {{COUNT}} |
| Blockers | {{COUNT}} |
| Critical | {{COUNT}} |
| Major | {{COUNT}} |
| Minor | {{COUNT}} |
| Commendations | {{COUNT}} |

## Coherence Dimensions

| Dimension | Status | Issues |
|-----------|--------|--------|
| Terminological | {{✅/❌}} | {{COUNT}} |
| Structural | {{✅/❌}} | {{COUNT}} |
| Behavioral | {{✅/❌}} | {{COUNT}} |
| Interface | {{✅/❌}} | {{COUNT}} |

## Key Findings

{{TOP_3_FINDINGS_SUMMARY}}

## Migration Notes

{{IF_NEW_PATTERN_PROPOSED_DOCUMENT_MIGRATION_PLAN}}

## Skill Chain Decision

{{CHAIN_DECISION_EXPLANATION}}
```

---

## Skill Chaining

### Chain Triggers

| Verdict | Chain Action | Target Skill |
|---------|--------------|--------------|
| `FAIL` | Mandatory implementation fixes | `implement/{language}` |
| `NEEDS_WORK` | Targeted pattern alignment | `implement/{language}` |
| `PASS_WITH_SUGGESTIONS` | Optional improvements | None (suggestions only) |
| `PASS` | Continue pipeline | `review/modularity` or next review |

### Handoff Protocol

When chaining to implement:

```markdown
**Chain Target:** `implement/python`
**Priority Findings:** TC.1, SC.1, BC.1
**Context:** Review identified {{COUNT}} coherence violations requiring alignment
**Constraint:** Match patterns from `{{PEER_MODULE_PATH}}`

**Reference Files:** {{LIST_OF_PEER_FILES_TO_MIRROR}}

```



### Re-Review Loop



After implement completes:

- Scope limited to modified files
- Focus on previously-failed criteria
- Maximum 2 iterations before escalation to architect

---

## Integration Points

### Upstream Integration

| Source | Trigger | Context Provided |
|--------|---------|------------------|
| `implement/python` | Post-implementation | Changed files, module context |
| `implement/api` | New endpoint created | Route patterns, schema |
| `/review` command | Explicit invocation | User-specified scope |

### Downstream Integration

| Target | Condition | Handoff |
|--------|-----------|---------|
| `implement/{lang}` | Verdict ≠ PASS | Findings + peer references |
| `review/modularity` | Structural issues suggest boundaries | Module structure analysis |

---

## Examples

### Example 1: Terminology Violation

**Input:** Review new `src/shipping/manager.py`

**Analysis:**
```bash
# Find existing service patterns
grep -rn "class.*Service" src/ --include="*.py"
# Result: 12 files use "Service" suffix

# Find terminology
grep -rn "Shipping\|Shipment" src/ --include="*.py"  
# Result: docs/glossary.md defines "Shipment", not "Shipping"
```

**Output:**
```markdown
### [🔴 BLOCKER] Terminology Deviation: "Shipping" vs "Shipment"

**Location:** `src/shipping/manager.py:1`
**Criterion:** TC.1 - Domain terms match glossary
**Peer Reference:** `docs/glossary.md`, `src/orders/service.py`

**Issue:**
Module uses "Shipping" but glossary defines "Shipment" as the domain term.
Additionally, "Manager" suffix deviates from established "Service" pattern.

**Evidence:**
\`\`\`python
# Your code:
class ShippingManager:

# Established pattern:
class ShipmentService:  # From glossary + service convention
\`\`\`

**Suggestion:**
Rename to `ShipmentService` to align with domain language and naming conventions.

**Rationale:**
Terminological coherence is foundational—mixed terms cause confusion and make
the codebase harder to search, discuss, and maintain.
```

**Verdict:** `FAIL` → Chain to `implement/python` with peer reference

### Example 2: Structural Deviation

**Input:** Review new `src/payments/` module

**Analysis:**
```bash
# Compare with peer module
diff <(ls -1 src/orders/) <(ls -1 src/payments/)
# orders/: __init__.py, models.py, service.py, repository.py, events.py, exceptions.py
# payments/: __init__.py, payment.py, db.py, handlers/
```

**Output:**
```markdown
### [🟠 CRITICAL] Structural Deviation: Module organization

**Location:** `src/payments/`
**Criterion:** SC.1 - Module structure mirrors peers
**Peer Reference:** `src/orders/`

**Issue:**
New module uses different file organization than established pattern.

**Evidence:**
\`\`\`
# Expected (from src/orders/):     # Actual (src/payments/):
├── __init__.py                    ├── __init__.py
├── models.py                      ├── payment.py      ← different naming
├── service.py                     ├── db.py           ← different naming
├── repository.py                  ├── handlers/       ← unexpected subdir
├── events.py                      └── (missing events.py, exceptions.py)
└── exceptions.py
\`\`\`

**Suggestion:**
Restructure to match peer modules:
- Rename `payment.py` → `models.py`
- Rename `db.py` → `repository.py`
- Add `service.py`, `events.py`, `exceptions.py`
- Move handlers into `service.py` or follow established handler pattern

**Rationale:**
Structural coherence enables navigation—developers should know where to find
any artifact without searching.
```

**Verdict:** `NEEDS_WORK` → Chain to `implement/python`

---

## Deep References

Load on-demand for complex reviews:

| Reference | When to Load | Path |
|-----------|--------------|------|
| Coherence Principles | Always (baseline) | `skills/design/code/refs/coherence.md` |
| Domain Glossary | Terminology validation | `docs/glossary.md` |
| Module Templates | Structural comparison | `.claude/assets/templates/` |
| Engineering Principles | Pattern validation | `rules/principles.md` |

---

## Quality Gates

Before finalizing review output:

- [ ] At least 2 peer modules identified for comparison
- [ ] All five coherence dimensions evaluated
- [ ] Each finding includes peer reference evidence
- [ ] Terminology checked against glossary (if exists)
- [ ] Verdict aligns with severity distribution
- [ ] Migration plan noted if new pattern is superior
- [ ] Chain decision is explicit with target skill
