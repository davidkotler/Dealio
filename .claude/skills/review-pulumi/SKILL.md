---
name: review-pulumi
version: 1.0.0
description: |
  Review Pulumi Python infrastructure code for correctness, security, and production-readiness.
  Evaluates component patterns, naming conventions, IAM policies, stack references, and
  configuration management against organizational standards.
  Use when reviewing Pulumi programs, validating infrastructure changes, assessing IaC quality,
  or after implementing stacks, components, or cloud resources.
  Relevant for Pulumi Python, AWS, infrastructure-as-code, ComponentResource, stack config.

chains:
  invoked-by:
    - skill: implement/pulumi
      context: "Post-implementation quality gate"
    - skill: design/pulumi
      context: "Validate implementation matches design artifacts"
  invokes:
    - skill: implement/pulumi
      when: "Critical or major findings detected"
    - skill: review/security
      when: "IAM or network findings require deeper security analysis"
---

# Pulumi Infrastructure Review

> Validate that Pulumi code is production-ready, secure, and aligned with design artifacts through systematic evaluation.

## Quick Reference

| Aspect          | Details                                                          |
|-----------------|------------------------------------------------------------------|
| **Dimension**   | Pulumi Infrastructure Quality                                    |
| **Scope**       | `__main__.py`, `components/*.py`, `Pulumi.yaml`, `Pulumi.*.yaml`|
| **Invoked By**  | `implement/pulumi`, `design/pulumi`, `/review` command           |
| **Invokes**     | `implement/pulumi` (on failure)                                  |
| **Verdict Options** | `PASS` · `PASS_WITH_SUGGESTIONS` · `NEEDS_WORK` · `FAIL`    |

---

## Review Objective

Ensure Pulumi infrastructure code is correct, secure, maintainable, and aligned with design artifacts before deployment.

### This Review Answers

1. Do all ComponentResources follow the mandatory anatomy (parent, type string, outputs)?
2. Are naming conventions consistent (kebab-case logical, auto-naming default)?
3. Does the security posture meet production standards (IAM, encryption, network isolation)?
4. Are stack references parameterized and outputs structured by domain?

### Out of Scope

- Application-level business logic review
- Cloud cost optimization analysis

---

## Core Workflow

```
┌──────────────────────────────────────────────────────────────┐
│                      REVIEW WORKFLOW                         │
├──────────────────────────────────────────────────────────────┤
│  1. SCOPE    → Identify Pulumi artifacts to review           │
│  2. CONTEXT  → Load design artifacts and reference patterns  │
│  3. ANALYZE  → Apply evaluation criteria systematically      │
│  4. CLASSIFY → Assign severity to each finding               │
│  5. VERDICT  → Determine pass/fail based on findings         │
│  6. REPORT   → Output structured review results              │
│  7. CHAIN    → Invoke downstream skills if needed            │
└──────────────────────────────────────────────────────────────┘
```

### Step 1: Scope Definition

Identify review targets:

```bash
# Pulumi project and stack configuration
Glob: Pulumi.yaml, Pulumi.*.yaml

# Implementation and component files
Glob: __main__.py, components/**/*.py, utils/**/*.py
```

### Step 2: Context Loading

Before analysis, internalize:







- **Design Artifacts:** ADR, Stack Map, Component Inventory — confirm existence and code alignment
- **Component Patterns:** `refs/component-patterns.md` → anatomy, type strings, output registration
- **Naming:** `refs/naming-conventions.md` → kebab-case, auto-naming, explicit naming risks
- **Security:** `refs/security-checklist.md` → OIDC, IAM, encryption, network isolation
- **Stack Refs:** `refs/stack-references.md` → parameterized references, structured exports

### Step 3: Systematic Analysis

For each artifact, evaluate against criteria in order of severity:

| Priority | Criterion Category         | Weight  |
|----------|----------------------------|---------|
| P0       | Component Structure        | Blocker |
| P1       | Security Posture           | Critical|
| P2       | Naming & Configuration     | Major   |
| P3       | Stack References & Exports | Minor   |

### Step 4: Severity Classification

| Severity             | Definition                                       | Action Required       |
|----------------------|--------------------------------------------------|-----------------------|
| **🔴 BLOCKER**       | Broken resource tree, preview failure, data loss risk | Must fix before merge |
| **🟠 CRITICAL**      | Security vulnerability, missing encryption, IAM `*/*` | Must fix, may defer   |
| **🟡 MAJOR**         | Missing output registration, wrong naming, hardcoded refs | Should fix            |
| **🔵 MINOR**         | Suboptimal patterns, missing tags, style inconsistency | Consider fixing       |
| **⚪ SUGGESTION**    | Alternative approach, optimization opportunity   | Optional improvement  |
| **🟢 COMMENDATION** | Exemplary pattern usage, proactive security      | Positive reinforcement|

### Step 5: Verdict Determination

```
Findings Analysis
│
├─► Any BLOCKER? ──────────────► FAIL
│
├─► Any CRITICAL? ─────────────► NEEDS_WORK
│
├─► Multiple MAJOR? ───────────► NEEDS_WORK
│
├─► Few MAJOR or MINOR only? ──► PASS_WITH_SUGGESTIONS
│
└─► SUGGESTION/COMMENDATION ───► PASS
```

---

## Evaluation Criteria

### Component Structure (CS)

| ID   | Criterion                              | Severity | Check                                                 |
|------|----------------------------------------|----------|-------------------------------------------------------|
| CS.1 | `super().__init__` uses three-part type string `<org>:<module>:<Type>` | 🔴 BLOCKER | Type string matches `acmecorp:module:ClassName` format |
| CS.2 | All child resources have `parent=self`  | 🔴 BLOCKER | No child resource created without `ResourceOptions(parent=self)` |
| CS.3 | `register_outputs()` called with all exposed values | 🟡 MAJOR | Every ComponentResource ends with `self.register_outputs({...})` |
| CS.4 | Args use `@dataclass` with `pulumi.Input[]` types | 🟡 MAJOR | Component args class is a typed dataclass |
| CS.5 | `opts: ResourceOptions | None = None` accepted | 🔵 MINOR | Component constructor accepts and passes through opts |
| CS.6 | Child logical names use `f"{name}-suffix"` pattern | 🔵 MINOR | Children prefixed with parent name |

### Security Posture (SP)

| ID   | Criterion                              | Severity | Check                                                 |
|------|----------------------------------------|----------|-------------------------------------------------------|
| SP.1 | No IAM `Action: "*"` or `Resource: "*"` | 🟠 CRITICAL | All IAM policies use specific actions and resource ARNs |
| SP.2 | S3 buckets have encryption + public access block | 🟠 CRITICAL | Every `BucketV2` paired with encryption and `BucketPublicAccessBlock` |
| SP.3 | RDS uses `storage_encrypted=True`, `publicly_accessible=False` | 🟠 CRITICAL | Database resources have encryption and network isolation |
| SP.4 | Stateful resources have `protect=True`  | 🟡 MAJOR | RDS, S3 state buckets, DynamoDB have `ResourceOptions(protect=True)` |
| SP.5 | Security groups use specific ports and CIDRs | 🟡 MAJOR | No `0.0.0.0/0` ingress except ALB on 443 |
| SP.6 | No secrets in stack config files        | 🟠 CRITICAL | Secrets use `config.require_secret()`, not plaintext config |

### Naming & Configuration (NC)

| ID   | Criterion                              | Severity | Check                                                 |
|------|----------------------------------------|----------|-------------------------------------------------------|
| NC.1 | Logical names use kebab-case           | 🟡 MAJOR | No PascalCase, snake_case, or unseparated names |
| NC.2 | Logical names are descriptive of purpose | 🔵 MINOR | `"orders-api"` not `"api"`, `"user-uploads"` not `"bucket"` |
| NC.3 | Auto-naming used unless explicit name justified | 🟡 MAJOR | Explicit physical names only for DNS, import, or external refs |
| NC.4 | Explicit names have `delete_before_replace=True` | 🟠 CRITICAL | Every explicitly-named resource sets this option |
| NC.5 | Tags include Environment, Project, ManagedBy | 🔵 MINOR | All taggable resources have required tags or use provider `default_tags` |
| NC.6 | Config uses typed accessors (`require`, `get_int`, `require_secret`) | 🔵 MINOR | No raw `config.get()` for required values |

### Stack References & Exports (SR)

| ID   | Criterion                              | Severity | Check                                                 |
|------|----------------------------------------|----------|-------------------------------------------------------|
| SR.1 | Stack references are parameterized via config | 🟡 MAJOR | No hardcoded `"org/project/stack"` strings |
| SR.2 | Mandatory outputs use `require_output()` | 🔵 MINOR | Not `get_output()` for values that must exist |
| SR.3 | Exports are structured by domain       | 🔵 MINOR | `pulumi.export("network", {...})` not flat individual exports |
| SR.4 | No circular stack dependencies         | 🟠 CRITICAL | Dependency graph is acyclic (layered or hub-and-spoke) |
| SR.5 | Only necessary values exported         | ⚪ SUGGESTION | No full resource objects exported, only specific IDs/ARNs |
| SR.6 | No entire resource objects exported    | 🔵 MINOR | `pulumi.export("vpc", vpc)` is an anti-pattern |

---

## Patterns & Anti-Patterns

### ✅ Indicators of Quality

```python
@dataclass
class SecureBucketArgs:
    bucket_name: pulumi.Input[str]
    versioning_enabled: pulumi.Input[bool] = True

class SecureBucket(pulumi.ComponentResource):
    bucket_arn: pulumi.Output[str]

    def __init__(self, name: str, args: SecureBucketArgs,
                 opts: pulumi.ResourceOptions | None = None) -> None:
        super().__init__("acmecorp:storage:SecureBucket", name, None, opts)
        child_opts = pulumi.ResourceOptions(parent=self)
        self.bucket = s3.BucketV2(f"{name}-bucket", opts=child_opts)
        # ... encryption, public access block, versioning ...
        self.bucket_arn = self.bucket.arn
        self.register_outputs({"bucket_arn": self.bucket_arn})
```

**Why this works:** Three-part type string, parent chaining, `f"{name}-suffix"` naming, dataclass args, output registration — all mandatory patterns present.

### ❌ Red Flags

```python
class BadComponent(pulumi.ComponentResource):
    def __init__(self, name, args, opts=None):
        super().__init__("BadComponent", name, None, opts)  # Missing org:module
        self.bucket = s3.BucketV2("my-bucket")              # No parent, hardcoded name
        self.bucket_arn = self.bucket.arn                    # No register_outputs
```

**Why this fails:** Invalid type string breaks Pulumi Console. Missing parent breaks resource tree. Missing output registration breaks downstream references. Hardcoded name prevents stack isolation.

---

## Finding Output Format

```markdown
### [{{SEVERITY_EMOJI}} {{SEVERITY}}] {{FINDING_TITLE}}
**Location:** `{{FILE_PATH}}:{{LINE_NUMBER}}`
**Criterion:** {{CRITERION_ID}} - {{CRITERION_NAME}}
**Issue:** {{ISSUE_DESCRIPTION}}
**Evidence:** (code snippet)
**Suggestion:** {{REMEDIATION_GUIDANCE}}
**Rationale:** {{WHY_THIS_MATTERS}}
```

---

## Review Summary Format

```markdown
# Pulumi Infrastructure Review Summary
## Verdict: {{VERDICT_EMOJI}} {{VERDICT}}
| Metric | Count |
|--------|-------|
| Files Reviewed | — |
| Blockers / Critical / Major / Minor | — / — / — / — |
| Suggestions / Commendations | — / — |
## Key Findings
(Top 3 findings summarized)
## Recommended Actions
1. (Highest-priority) 2. (Second) 3. (Third)
## Skill Chain Decision
(Chain to implement/pulumi if verdict ≠ PASS, with finding IDs)
```

---

## Skill Chaining

### Chain Triggers

| Verdict                | Chain Action          | Target Skill         |
|------------------------|-----------------------|----------------------|
| `FAIL`                 | Mandatory implement   | `implement/pulumi`   |
| `NEEDS_WORK`           | Targeted fixes        | `implement/pulumi`   |
| `PASS_WITH_SUGGESTIONS`| Optional improvements | None (suggestions only) |
| `PASS`                 | Continue pipeline     | `test/unit`          |

### Handoff Protocol

When chaining to implement:

```markdown
**Chain Target:** `implement/pulumi`
**Priority Findings:** (List BLOCKER and CRITICAL finding IDs)
**Context:** Review identified N issues requiring remediation
**Constraint:** Preserve existing stack state and resource URNs
```

### Re-Review Loop

After implement completes, re-invoke with scope limited to modified files, focus on previously-failed criteria, maximum 3 iterations before escalation.

---

## Integration Points

| Direction  | Skill               | Trigger                        |
|------------|----------------------|--------------------------------|
| Upstream   | `implement/pulumi`   | Post-implementation            |
| Upstream   | `design/pulumi`      | Post-design validation         |
| Upstream   | `/review` command    | Explicit invocation            |
| Downstream | `implement/pulumi`   | Verdict ≠ PASS → findings list |
| Downstream | `test/unit`          | Verdict = PASS → component list|

---

## Deep References

Load on-demand for complex reviews:

| Reference            | When to Load                           | Path                         |
|----------------------|----------------------------------------|------------------------------|
| Component Patterns   | Evaluating ComponentResource anatomy   | `refs/component-patterns.md` |
| Naming Conventions   | Assessing naming and auto-naming usage | `refs/naming-conventions.md` |
| Security Checklist   | Reviewing IAM, encryption, network     | `refs/security-checklist.md` |
| Stack References     | Evaluating cross-stack communication   | `refs/stack-references.md`   |

---

## Quality Gates

Before finalizing review output:

- [ ] All Pulumi artifacts in scope were analyzed
- [ ] Each finding has location + criterion + severity
- [ ] Verdict aligns with severity distribution
- [ ] Actionable suggestions provided for non-PASS verdicts
- [ ] Chain decision is explicit and justified
- [ ] Output follows structured format
- [ ] Design artifacts (ADR, Stack Map) were checked for alignment
