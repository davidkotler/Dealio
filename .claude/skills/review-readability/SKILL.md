---
name: review-readability
version: 1.0.0

description: |
  Review code for readability and comprehension quality. Evaluates naming clarity, structural simplicity, cognitive load, and documentation effectiveness.
  Use when reviewing code changes, validating implementations, assessing code clarity, or checking naming conventions.
  Relevant for Python, TypeScript, JavaScript, and all source code files.

chains:
  invoked-by:
    - skill: implement/python
      context: "Post-implementation quality gate"
    - skill: implement/api
      context: "Post-implementation quality gate"
    - skill: implement/react
      context: "Post-implementation quality gate"
    - skill: review/functionality
      context: "After functional correctness verified"
  invokes:
    - skill: refactor/simplify
      when: "Critical or major findings detected"
    - skill: review/modularity
      when: "Structural issues indicate deeper design problems"
---

# Readability Review

> Validate that code is written for humans to read, machines merely to execute.

## Quick Reference

| Aspect | Details |
|--------|---------|
| **Dimension** | Readability |
| **Scope** | Functions, classes, modules, naming, comments, structure |
| **Invoked By** | `implement/*`, `/review` command |
| **Invokes** | `refactor/simplify` (on failure) |
| **Verdict Options** | `PASS` · `PASS_WITH_SUGGESTIONS` · `NEEDS_WORK` · `FAIL` |

---

## Review Objective

Ensure code can be understood quickly by any competent developer without requiring mental gymnastics, external context, or author explanation.

### This Review Answers

1. Can a developer understand this code in a single read-through?
2. Do names reveal intent without requiring surrounding context?
3. Is complexity managed through clear structure rather than dense expressions?
4. Do comments add value by explaining "why", not restating "what"?

### Out of Scope

- Functional correctness (see `review/functionality`)
- Performance optimization (see `review/performance`)
- Type safety (see `review/types`)
- Architectural alignment (see `review/design`)

---

## Core Workflow

```
┌─────────────────────────────────────────────────────────────┐
│                    REVIEW WORKFLOW                          │
├─────────────────────────────────────────────────────────────┤
│  1. SCOPE    →  Identify code artifacts to review           │
│  2. CONTEXT  →  Load principles (§2.1 Readability First)    │
│  3. ANALYZE  →  Apply criteria: NC → SC → CL → DQ           │
│  4. CLASSIFY →  Assign severity to each finding             │
│  5. VERDICT  →  Determine pass/fail from severity profile   │
│  6. REPORT   →  Output structured findings                  │
│  7. CHAIN    →  Invoke refactor/simplify if needed          │
└─────────────────────────────────────────────────────────────┘
```

### Step 1: Scope Definition

Identify review targets:

```bash
# Source files (exclude tests, configs, generated)
**/*.py
**/*.ts
**/*.tsx
**/*.js
**/*.jsx

# Exclude patterns
!**/__pycache__/**
!**/node_modules/**
!**/*.generated.*
!**/migrations/**
```

### Step 2: Context Loading

Before analysis, internalize:







- **Principles:** `rules/principles.md` → Section 2.1 (Readability First)
- **Conventions:** `rules/python.md` or `rules/react.md` → Naming standards
- **Red Flags:** `rules/principles.md` → Red Flags Checklist

### Step 3: Systematic Analysis

Evaluate against criteria in order of impact:

| Priority | Criterion Category | Weight |
|----------|-------------------|--------|
| P0 | Naming Clarity (NC) | Blocker/Critical |
| P1 | Structural Clarity (SC) | Critical/Major |
| P2 | Cognitive Load (CL) | Major |
| P3 | Documentation Quality (DQ) | Minor |

### Step 4: Severity Classification

| Severity | Definition | Action Required |
|----------|------------|-----------------|
| **🔴 BLOCKER** | Code is incomprehensible; requires author to explain | Must fix before merge |
| **🟠 CRITICAL** | Significant mental effort required to understand | Must fix, may defer |
| **🟡 MAJOR** | Noticeable friction in comprehension | Should fix |
| **🔵 MINOR** | Small improvements possible | Consider fixing |
| **⚪ SUGGESTION** | Style preference or micro-optimization | Optional |
| **🟢 COMMENDATION** | Exemplary clarity worth highlighting | Positive reinforcement |

### Step 5: Verdict Determination

```
Findings Analysis
       │
       ├─► Any BLOCKER? ──────────────► FAIL
       │
       ├─► Any CRITICAL? ─────────────► NEEDS_WORK
       │
       ├─► 3+ MAJOR findings? ────────► NEEDS_WORK
       │
       ├─► Few MAJOR or MINOR only? ──► PASS_WITH_SUGGESTIONS
       │
       └─► SUGGESTION/COMMENDATION ───► PASS
```

---

## Evaluation Criteria

### Naming Clarity (NC)

| ID | Criterion | Severity | Check |
|----|-----------|----------|-------|
| NC.1 | Names reveal intent without external context | CRITICAL | Can you understand purpose from name alone? |
| NC.2 | No unexplained abbreviations | MAJOR | Are all abbreviations domain-standard or spelled out? |
| NC.3 | Naming is consistent within module | MAJOR | Same concept = same terminology throughout? |
| NC.4 | Boolean names indicate true/false meaning | MINOR | `is_`, `has_`, `can_`, `should_` prefixes used? |
| NC.5 | Function names describe action and result | MAJOR | Verb + noun pattern reveals behavior? |
| NC.6 | No single-letter names outside tiny scopes | MAJOR | `i` only in short loops; no `x`, `d`, `t` for domain objects? |

### Structural Clarity (SC)

| ID | Criterion | Severity | Check |
|----|-----------|----------|-------|
| SC.1 | Functions ≤ 30 lines (prefer ≤ 20) | CRITICAL | `wc -l` on function body |
| SC.2 | Nesting depth ≤ 3 levels | MAJOR | No pyramid of doom? |
| SC.3 | Single level of abstraction per function | MAJOR | Not mixing high-level flow with low-level details? |
| SC.4 | Related code grouped logically | MINOR | Declarations, logic, returns in clear sections? |
| SC.5 | Early returns reduce nesting | MINOR | Guard clauses at top instead of nested else? |
| SC.6 | No god functions (> 5 responsibilities) | BLOCKER | Function does ONE thing? |

### Cognitive Load (CL)

| ID | Criterion | Severity | Check |
|----|-----------|----------|-------|
| CL.1 | No dense one-liners sacrificing clarity | MAJOR | Would multi-line be clearer? |
| CL.2 | Complex expressions broken into named parts | MAJOR | Intermediate variables explain steps? |
| CL.3 | No "clever" code requiring mental unpacking | CRITICAL | Obvious solution preferred over elegant-but-obscure? |
| CL.4 | Conditionals read like natural language | MINOR | `if user.is_active` not `if user.status == 1`? |
| CL.5 | No magic numbers or strings | MAJOR | Constants with meaningful names? |
| CL.6 | Control flow is linear and predictable | MAJOR | No spaghetti jumps or exception-based flow control? |

### Documentation Quality (DQ)

| ID | Criterion | Severity | Check |
|----|-----------|----------|-------|
| DQ.1 | Comments explain "why", not "what" | MAJOR | No `# increment counter` for `count += 1`? |
| DQ.2 | No redundant or obvious comments | MINOR | Comments add information code doesn't convey? |
| DQ.3 | Complex algorithms have explanatory comments | MAJOR | Non-obvious logic is annotated? |
| DQ.4 | Public APIs have docstrings | MINOR | Functions/classes document parameters, returns, raises? |
| DQ.5 | No commented-out code | MINOR | Dead code removed, not commented? |
| DQ.6 | TODOs have context and ownership | MINOR | `# TODO(username): reason` format? |

---

## Patterns & Anti-Patterns

### ✅ Indicators of Quality

```python
def calculate_order_total_with_discounts(
    line_items: list[LineItem],
    customer_tier: CustomerTier,
    promotional_codes: list[str],
) -> Money:
    """Calculate final order total after applying all applicable discounts."""
    subtotal = sum(item.price * item.quantity for item in line_items)

    tier_discount = get_tier_discount(customer_tier, subtotal)

    promo_discount = apply_promotional_codes(promotional_codes, subtotal)

    return subtotal - tier_discount - promo_discount

```



**Why this works:**

- Function name reveals exact purpose: calculates total WITH discounts
- Parameter names are self-documenting
- Intermediate variables (`tier_discount`, `promo_discount`) explain steps

- Each line does one thing at one level of abstraction
- Total length is ~10 lines, well under threshold


### ❌ Red Flags


```python

def calc(items, t, codes):
    s = sum(i.p * i.q for i in items)

    return s - get_d(t, s) - apply_c(codes, s)
```


**Why this fails:**

- `calc` reveals nothing about what's calculated
- Single-letter parameters (`t`, `codes` is okay but inconsistent)
- `i.p`, `i.q` require knowledge of item structure
- `get_d`, `apply_c` are cryptic abbreviations
- No way to understand this without reading the implementation

### ✅ Clear Conditional Logic

```python
def can_user_access_resource(user: User, resource: Resource) -> bool:
    if not user.is_active:
        return False

    if user.is_admin:
        return True

    if resource.is_public:
        return True

    return user.id in resource.allowed_user_ids
```

**Why this works:** Guard clauses read top-to-bottom as English sentences.

### ❌ Nested Conditional Pyramid

```python
def check_access(u, r):
    if u.active:
        if u.admin:
            return True
        else:
            if r.public:
                return True
            else:
                if u.id in r.users:
                    return True
    return False
```

**Why this fails:** Mental stack required; must trace all paths to understand.

---

## Finding Output Format

Structure each finding as:

```markdown
### [🟠 CRITICAL] Cryptic function name reveals no intent

**Location:** `src/services/order.py:45`
**Criterion:** NC.1 - Names reveal intent without external context

**Issue:**
Function `proc_ord` provides no indication of what processing occurs or what the expected outcome is.

**Evidence:**
```python
def proc_ord(o, u):
    # 30 lines of processing
    return result
```

**Suggestion:**
Rename to describe the action and result:
```python
def process_order_for_fulfillment(order: Order, user: User) -> FulfillmentResult:
```

**Rationale:**
Names are read 10x more than written. Investment in clear naming pays compound returns in maintainability.
```

---

## Review Summary Format

```markdown
# Readability Review Summary

## Verdict: 🟡 NEEDS_WORK

| Metric | Count |
|--------|-------|
| Files Reviewed | 5 |
| Blockers | 0 |
| Critical | 2 |
| Major | 4 |
| Minor | 3 |
| Suggestions | 1 |
| Commendations | 1 |

## Key Findings

1. **[CRITICAL] NC.1** - `proc_ord` and `calc_inv` reveal no intent
2. **[CRITICAL] SC.1** - `OrderService.create` is 67 lines
3. **[MAJOR] CL.3** - Complex list comprehension with nested conditions

## Recommended Actions

1. Rename functions to reveal intent (NC.1 findings)
2. Extract `OrderService.create` into smaller methods
3. Break complex comprehension into intermediate steps

## Skill Chain Decision

→ **Invoking:** `refactor/simplify`
→ **Reason:** 2 CRITICAL findings require structural changes
→ **Priority:** NC.1 (naming), SC.1 (function length)
```

---

## Skill Chaining

### Chain Triggers

| Verdict | Chain Action | Target Skill |
|---------|--------------|--------------|
| `FAIL` | Mandatory refactor | `refactor/simplify` |

| `NEEDS_WORK` | Targeted fixes | `refactor/simplify` |
| `PASS_WITH_SUGGESTIONS` | Optional | None (suggestions only) |
| `PASS` | Continue pipeline | `review/modularity` or next phase |


### Handoff Protocol


When chaining to refactor:

```markdown

**Chain Target:** `refactor/simplify`
**Priority Findings:** NC.1, SC.1, CL.3
**Context:** Readability review identified 2 critical and 4 major issues

**Constraint:** Preserve all existing functionality and test coverage
```


### Re-Review Loop

After refactor completes:

- Scope limited to modified files
- Focus on previously-failed criteria
- Maximum 3 iterations before escalation to human review

---

## Integration Points

### Upstream Integration

| Source | Trigger | Context Provided |
|--------|---------|------------------|
| `implement/python` | Post-implementation | Changed files, function signatures |
| `implement/api` | Post-implementation | Route handlers, request/response models |
| `implement/react` | Post-implementation | Component files, hooks |
| `/review` command | Explicit invocation | User-specified scope |

### Downstream Integration

| Target | Condition | Handoff |
|--------|-----------|---------|
| `refactor/simplify` | Verdict ≠ PASS | Findings + priority order |
| `review/modularity` | Structural issues found | Current verdict + SC findings |
| `review/coherence` | Naming inconsistencies | NC findings for deeper analysis |

---

## Quick Checks

Use these bash commands for rapid assessment:

```bash
# Functions over 30 lines (Python)
grep -n "def " file.py | while read line; do
  # Check function length heuristically
done

# Nesting depth indicator (count leading whitespace)
grep -E "^\s{16,}" file.py  # 4+ levels of 4-space indent

# Single-letter variables (excluding loop counters)
grep -E "\b[a-z]\s*=" file.py | grep -v "for [a-z] in"

# Commented-out code
grep -E "^\s*#.*\b(def|class|if|for|return)\b" file.py
```

---

## Deep References

Load on-demand for complex reviews:

| Reference | When to Load | Path |
|-----------|--------------|------|
| Naming conventions | Multi-language codebase | `rules/python.md`, `rules/react.md` |
| Readability principles | Philosophical questions | `rules/principles.md` § 2.1 |
| Cognitive complexity metrics | Quantitative analysis needed | `refs/complexity-metrics.md` |

---

## Quality Gates

Before finalizing review output:

- [ ] All source files in scope were analyzed
- [ ] Each finding has location + criterion ID + severity
- [ ] Verdict aligns with severity distribution
- [ ] Actionable suggestions provided for MAJOR+ findings
- [ ] Good examples (🟢) highlighted when found
- [ ] Chain decision is explicit and justified
- [ ] Output follows structured format
