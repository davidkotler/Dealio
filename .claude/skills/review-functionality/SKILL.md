---
name: review-functionality
version: 1.0.0

description: |
  Review code for functional correctness. Evaluates whether code produces expected outputs,
  handles edge cases, and implements business logic accurately.
  Use when reviewing implementations, validating bug fixes, or assessing feature completeness.
  Relevant for all code changes, new features, bug fixes, refactoring validation.

chains:
  invoked-by:
    - skill: implement/python
      context: "Post-implementation correctness validation"
    - skill: implement/api
      context: "API behavior verification"
    - skill: implement/react
      context: "Component logic validation"
  invokes:
    - skill: implement/python
      when: "Critical or major functional defects detected"
    - skill: review/robustness
      when: "Functionality passes, error handling review needed"
    - skill: test/unit
      when: "Missing test coverage for functional paths"
---

# Functionality Review

> Validate that code does what it's supposed to do through systematic behavioral analysis.

## Quick Reference

| Aspect | Details |
|--------|---------|
| **Dimension** | Functional Correctness |
| **Scope** | Logic, behavior, requirements alignment, edge cases |
| **Invoked By** | `implement/*`, `/review` command |
| **Invokes** | `implement/*` (on failure), `test/unit` (coverage gaps) |
| **Verdict Options** | `PASS` · `PASS_WITH_SUGGESTIONS` · `NEEDS_WORK` · `FAIL` |

---

## Review Objective

Ensure code produces correct outputs for all inputs, implements requirements completely, and handles boundary conditions appropriately.

### Key Questions








1. Does the code produce correct outputs for expected inputs?

2. Are all specified requirements implemented?

3. Are edge cases and boundary conditions handled?

4. Does the business logic align with domain rules?



### Out of Scope

- Code style/formatting → `review/style`
- Performance → `review/performance`
- Security → `review/security`

---

## Core Workflow


```

1. SCOPE    →  Identify code paths (git diff, changed files)
2. CONTEXT  →  Load requirements, specs, domain rules, existing tests


3. ANALYZE  →  Trace logic flow, verify correctness per criteria
4. CLASSIFY →  Assign severity to each finding


5. VERDICT  →  Determine pass/fail based on severity distribution
6. REPORT   →  Output structured findings


7. CHAIN    →  Invoke fix/downstream skills as needed
```



### Scope Identification


```bash
git diff --name-only HEAD~1 -- "*.py" "*.ts" "*.tsx" "*.js"

```

### Verdict Logic

```
BLOCKER present?      → FAIL
CRITICAL present?     → NEEDS_WORK
Multiple MAJOR?       → NEEDS_WORK
Few MAJOR/MINOR?      → PASS_WITH_SUGGESTIONS
SUGGESTION only?      → PASS
```

---

## Severity Definitions

| Severity | Definition | Action |
|----------|------------|--------|
| **🔴 BLOCKER** | Wrong output, crashes, data corruption | Must fix before merge |
| **🟠 CRITICAL** | Missing required feature, logic flaw | Must fix |
| **🟡 MAJOR** | Unhandled edge case, incomplete validation | Should fix |
| **🔵 MINOR** | Suboptimal logic, minor inconsistency | Consider fixing |
| **⚪ SUGGESTION** | Alternative approach | Optional |
| **🟢 COMMENDATION** | Excellent handling | Positive reinforcement |

---

## Evaluation Criteria

### Correctness (COR)

| ID | Criterion | Severity | Check |
|----|-----------|----------|-------|
| COR.1 | Output matches specification | BLOCKER | Trace inputs→outputs against spec |
| COR.2 | Calculations are accurate | BLOCKER | Verify arithmetic, aggregations |
| COR.3 | State transitions are valid | CRITICAL | State machine follows rules |

### Completeness (CMP)

| ID | Criterion | Severity | Check |
|----|-----------|----------|-------|
| CMP.1 | All requirements implemented | CRITICAL | Map code to requirements |
| CMP.2 | All code paths reachable | MAJOR | No dead code/unreachable branches |
| CMP.3 | Return values handled | MAJOR | No ignored critical returns |

### Edge Case Handling (EDG)

| ID | Criterion | Severity | Check |
|----|-----------|----------|-------|
| EDG.1 | Null/None/undefined handled | CRITICAL | Check all dereferences |
| EDG.2 | Empty collections handled | MAJOR | Empty list/dict/set behavior |
| EDG.3 | Boundary values handled | MAJOR | Min/max, zero, negative values |

### Business Logic (BIZ)

| ID | Criterion | Severity | Check |
|----|-----------|----------|-------|
| BIZ.1 | Domain rules enforced | CRITICAL | Invariants maintained |
| BIZ.2 | Business constraints validated | MAJOR | Validation completeness |
| BIZ.3 | Domain terminology used | MINOR | Ubiquitous language alignment |

---

## Patterns & Anti-Patterns

### ✅ Quality Indicator

```python
async def transfer_funds(from_account: AccountId, to_account: AccountId, amount: Money) -> TransferResult:
    if amount <= Money(0):
        raise InvalidAmountError("Amount must be positive")  # EDG.3: Boundary

    source = await self._accounts.get(from_account)
    if source.balance < amount:
        return TransferResult.insufficient_funds(source.balance)  # BIZ.1: Invariant

    source.withdraw(amount)
    target = await self._accounts.get(to_account)
    target.deposit(amount)
    await self._accounts.save_all([source, target])  # COR.3: Atomic state
    return TransferResult.success(new_balance=source.balance)
```

### ❌ Red Flag

```python
def transfer(from_id, to_id, amount):
    source = db.query(f"SELECT * FROM accounts WHERE id = {from_id}")  # EDG.1: No null check
    source["balance"] -= amount  # EDG.3: No validation, BIZ.1: Negative balance possible
    db.save(source)
    db.save(target)  # COR.3: Non-atomic, partial failure possible
```

---

## Finding Format

```markdown
### [🔴 BLOCKER] {{Title}}

**Location:** `{{file}}:{{line}}`
**Criterion:** {{ID}} - {{Name}}

**Issue:** {{Description}}

**Evidence:**
\`\`\`{{language}}
{{code}}
\`\`\`

**Suggestion:** {{Fix guidance}}
**Rationale:** {{Why it matters}}
```

---

## Summary Format

```markdown
# Functionality Review Summary

## Verdict: {{EMOJI}} {{VERDICT}}

| Metric | Count |
|--------|-------|

| Files Reviewed | {{N}} |
| Blockers | {{N}} |
| Critical | {{N}} |
| Major | {{N}} |


## Key Findings
1. **[{{SEV}}]** {{Finding}} ({{Criterion}})


## Skill Chain Decision
{{Chain justification}}
```


---

## Skill Chaining


| Verdict | Action | Target |
|---------|--------|--------|
| `FAIL` | Mandatory fix | `implement/{language}` |
| `NEEDS_WORK` | Targeted fixes | `implement/{language}` |

| `PASS_WITH_SUGGESTIONS` | None | Document only |
| `PASS` | Continue pipeline | `review/robustness` |

### Handoff Format

```markdown
**Chain Target:** `implement/python`
**Priority Findings:** {{IDs}}
**Constraint:** Preserve existing API signatures
```

### Re-Review: Max 3 iterations, scope limited to modified files

---

## Common Defect Patterns

| Pattern | Manifestation |
|---------|---------------|
| **Off-by-one** | `< n` vs `<= n`, slice bounds, 0/1 indexing |
| **Null chains** | `obj.prop.nested` without guards |
| **State inconsistency** | Partial updates, missing transactions |
| **Logic inversions** | `if x` vs `if not x`, `and`/`or` confusion |

---

## Integration Points

| Direction | Source/Target | Trigger |
|-----------|---------------|---------|
| ← Upstream | `implement/*` | Post-implementation |
| ← Upstream | `/review` command | Explicit invocation |
| → Downstream | `implement/*` | Verdict ≠ PASS |
| → Downstream | `review/robustness` | PASS verdict |
| → Downstream | `test/unit` | Coverage gaps |

---

## Deep References

| Reference | Path |
|-----------|------|
| Domain patterns | `skills/design/code/refs/ddd.md` |
| Robustness criteria | `skills/review/robustness/SKILL.md` |
| Testing strategies | `skills/test/unit/SKILL.md` |

---

## Quality Gates

- [ ] All changed code paths analyzed
- [ ] Each finding: location + criterion + severity
- [ ] Verdict aligns with severity distribution
- [ ] Fix suggestions for non-PASS verdicts
- [ ] Chain decision explicit and justified
