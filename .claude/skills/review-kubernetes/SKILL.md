---
name: review-kubernetes
version: 1.0.0
description: |
  Review Kubernetes manifests, Helm charts, ArgoCD Applications, and EKS configurations
  for production-readiness. Evaluates security hardening, operational resilience,
  networking correctness, and GitOps quality.
  Use when reviewing Deployments, StatefulSets, DaemonSets, Jobs, Services, Gateway API
  routes, NetworkPolicies, RBAC roles, PDBs, HPAs, Helm charts, ArgoCD Applications,
  Kustomize overlays, ExternalSecrets, SealedSecrets, or Kyverno policies.
  Also use when validating manifest changes, assessing cluster security posture,
  or gate-checking Kubernetes implementations before merge.
  Relevant for Kubernetes, EKS, Helm, ArgoCD, FluxCD, Kustomize, YAML manifests.

chains:
  invoked-by:
    - skill: implement/kubernetes
      context: "Post-implementation quality gate"
    - skill: implement/helm
      context: "After Helm chart generation"
  invokes:
    - skill: implement/kubernetes
      when: "Critical or blocker findings detected"
    - skill: review/security
      when: "RBAC or policy findings need deeper audit"
---

# Kubernetes Infrastructure Review

> Validate production-readiness of Kubernetes manifests through systematic security, resilience, and operational analysis.

## Quick Reference

| Aspect         | Details                                                              |
| -------------- | -------------------------------------------------------------------- |
| **Dimension**  | Kubernetes Infrastructure                                            |
| **Scope**      | All K8s YAML manifests, Helm charts, ArgoCD/Flux configs, Kustomize |
| **Invoked By** | `implement/kubernetes`, `implement/helm`, `/review` command          |
| **Invokes**    | `implement/kubernetes` (on failure)                                  |
| **Verdict**    | `PASS` · `PASS_WITH_SUGGESTIONS` · `NEEDS_WORK` · `FAIL`           |

---

## Review Objective

Ensure every Kubernetes artifact meets production-grade standards for security, resilience, observability, and operational correctness before deployment.

### This Review Answers

1. Do all manifests satisfy Pod Security Standards (restricted) and security hardening rules?
2. Are workloads configured for operational resilience — probes, resources, PDBs, topology?
3. Is networking correctly configured — service exposure, Gateway API, network policies?
4. Do Helm charts and GitOps configs follow structural and quality best practices?

### Out of Scope

- Application-level business logic correctness
- Cloud provider billing or cost optimization beyond resource sizing

---

## Core Workflow

```
SCOPE → CONTEXT → ANALYZE → CLASSIFY → VERDICT → REPORT → CHAIN
```

### Step 1: Scope Definition

Identify review targets:

```bash
# K8s manifests, Helm charts, GitOps configs, Kustomize
**/*.yaml **/*.yml **/Chart.yaml **/templates/**/*.yaml **/values*.yaml
**/kustomization.yaml **/clusters/**/*.yaml **/apps/**/*.yaml
```

### Step 2: Context Loading

Before analysis, load refs on-demand based on artifacts found:

| Artifacts Found                          | Load Reference                                     |
| ---------------------------------------- | -------------------------------------------------- |
| Deployment, StatefulSet, DaemonSet, Job  | `refs/workloads.md` — probes, resources, topology   |
| SecurityContext, RBAC, NetworkPolicy      | `refs/security.md` — PSS, RBAC, policies, secrets   |
| Service, Gateway, HTTPRoute, Ingress     | `refs/networking.md` — exposure, CNI, mesh, DNS      |
| Chart.yaml, templates/, values.yaml      | `refs/helm.md` — chart structure, templates, testing |
| Application, Kustomization, HelmRelease  | `refs/gitops.md` — ArgoCD, Flux, repo structure      |

**Multiple refs are often required.** A Helm-deployed workload needs `workloads` + `security` + `helm`.

### Step 3: Systematic Analysis

Evaluate each artifact against criteria in priority order:

| Priority | Criterion Category       | Weight  |
| -------- | ------------------------ | ------- |
| P0       | Security Hardening       | Blocker |
| P1       | Operational Resilience   | Critical|
| P2       | Networking & Exposure    | Major   |
| P3       | Helm & GitOps Quality    | Minor   |

### Step 4: Severity Classification

| Severity              | Definition                                                        | Action Required          |
| --------------------- | ----------------------------------------------------------------- | ------------------------ |
| **🔴 BLOCKER**        | Security violation or missing control that exposes the cluster    | Must fix before merge    |
| **🟠 CRITICAL**       | Resilience gap causing outage risk under normal operations        | Must fix, may defer      |
| **🟡 MAJOR**          | Deviation from networking or structural standards                 | Should fix               |
| **🔵 MINOR**          | Helm/GitOps quality issue or missing optional best practice       | Consider fixing          |
| **⚪ SUGGESTION**     | Improvement that increases operational maturity                   | Optional                 |
| **🟢 COMMENDATION**   | Exemplary pattern worth reinforcing                               | Positive reinforcement   |

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

### Security Hardening

| ID   | Criterion                                   | Severity    | Check                                                                             |
| ---- | ------------------------------------------- | ----------- | --------------------------------------------------------------------------------- |
| SH.1 | PSS restricted: `runAsNonRoot: true`        | 🔴 BLOCKER  | Pod `securityContext.runAsNonRoot` is `true`                                       |
| SH.2 | PSS restricted: `allowPrivilegeEscalation: false` | 🔴 BLOCKER | Every container sets `allowPrivilegeEscalation: false`                            |
| SH.3 | PSS restricted: `capabilities.drop: ["ALL"]`| 🔴 BLOCKER  | Every container drops ALL capabilities                                            |
| SH.4 | PSS restricted: `readOnlyRootFilesystem: true` | 🔴 BLOCKER | Every container uses read-only root; writable paths use `emptyDir`              |
| SH.5 | No `:latest` or untagged images             | 🔴 BLOCKER  | Every `image:` field has a pinned version tag or SHA digest                        |
| SH.6 | No wildcard RBAC                            | 🔴 BLOCKER  | No `"*"` in `apiGroups`, `resources`, or `verbs`                                  |
| SH.7 | Default-deny NetworkPolicy per namespace    | 🟠 CRITICAL | Namespace has a `podSelector: {}` deny-all policy for Ingress and Egress          |
| SH.8 | `automountServiceAccountToken: false`       | 🟠 CRITICAL | ServiceAccounts disable token mount unless explicitly needed                       |
| SH.9 | RBAC uses `resourceNames` for secrets       | 🟡 MAJOR    | Secrets access specifies `resourceNames`, not blanket access                       |
| SH.10| `seccompProfile.type: RuntimeDefault`       | 🟡 MAJOR    | Pod securityContext includes seccomp profile                                       |

### Operational Resilience

| ID   | Criterion                                   | Severity    | Check                                                                             |
| ---- | ------------------------------------------- | ----------- | --------------------------------------------------------------------------------- |
| OR.1 | Memory requests and limits on all containers| 🟠 CRITICAL | `resources.requests.memory` and `resources.limits.memory` are set                  |
| OR.2 | CPU requests on all containers              | 🟠 CRITICAL | `resources.requests.cpu` is set (limits omitted for latency-sensitive is OK)       |
| OR.3 | Readiness probe on all long-running pods    | 🟠 CRITICAL | Every Deployment/StatefulSet/DaemonSet container has `readinessProbe`               |
| OR.4 | Liveness probe does not hit external deps   | 🔴 BLOCKER  | Liveness probe checks internal state only — never DB, cache, or downstream         |
| OR.5 | Startup probe for apps with >10s init       | 🟡 MAJOR    | Apps needing warm-up have `startupProbe` with adequate `failureThreshold`           |
| OR.6 | PDB exists for replicas >= 2                | 🟠 CRITICAL | `PodDisruptionBudget` present; never `minAvailable: 100%`                          |
| OR.7 | Topology spread for replicas >= 3           | 🟠 CRITICAL | `topologySpreadConstraints` with zone key and `maxSkew: 1`                         |
| OR.8 | Rolling update: `maxUnavailable: 0` for prod| 🟡 MAJOR    | Production Deployments use zero-downtime strategy                                  |
| OR.9 | `terminationGracePeriodSeconds` for StatefulSets | 🟡 MAJOR | StatefulSets set adequate grace period (≥30s for databases)                       |

### Networking & Exposure

| ID   | Criterion                                   | Severity    | Check                                                                             |
| ---- | ------------------------------------------- | ----------- | --------------------------------------------------------------------------------- |
| NE.1 | Gateway API over legacy Ingress             | 🟡 MAJOR    | New deployments use `HTTPRoute` + `Gateway`, not `Ingress`                         |
| NE.2 | Correct service type for use case           | 🟡 MAJOR    | ClusterIP for internal, Headless for StatefulSet, LoadBalancer only when needed     |
| NE.3 | NetworkPolicy allows DNS egress             | 🟠 CRITICAL | Allow policies include UDP/53 egress to `kube-dns`                                 |
| NE.4 | IMDS blocked on EKS                         | 🟠 CRITICAL | Egress NetworkPolicy excludes `169.254.169.254/32` unless Pod Identity is used     |
| NE.5 | TLS termination configured                  | 🟡 MAJOR    | Gateway listeners or Ingress annotations reference TLS certificates                |
| NE.6 | Headless service for StatefulSets           | 🟡 MAJOR    | StatefulSet has a corresponding `clusterIP: None` service                          |

### Helm & GitOps Quality

| ID   | Criterion                                   | Severity    | Check                                                                             |
| ---- | ------------------------------------------- | ----------- | --------------------------------------------------------------------------------- |
| HG.1 | Standard labels on every resource           | 🟡 MAJOR    | `app.kubernetes.io/name`, `/instance`, `/version`, `/managed-by` present           |
| HG.2 | Helm: `values.schema.json` present          | 🔵 MINOR    | Chart includes JSON Schema for value validation                                    |
| HG.3 | Helm: `_helpers.tpl` uses `include` not `template` | 🔵 MINOR | Template helpers are pipeable via `include`                                    |
| HG.4 | Helm: config checksum annotation            | 🔵 MINOR    | Deployment template has `checksum/config` annotation for ConfigMap reload           |
| HG.5 | ArgoCD: `selfHeal` and `prune` enabled      | 🔵 MINOR    | Application syncPolicy sets `automated.selfHeal: true` and `prune: true`           |
| HG.6 | ArgoCD: HPA-managed replicas ignored        | 🔵 MINOR    | `ignoreDifferences` excludes `/spec/replicas` when HPA is active                   |
| HG.7 | No hardcoded env-specific values in base    | 🟡 MAJOR    | Env-specific values use Kustomize overlays or Helm values files, not base manifests |
| HG.8 | Helm: `required` for mandatory values       | 🔵 MINOR    | Critical values use `{{ required "msg" .Values.x }}` in templates                  |

---

## Patterns & Anti-Patterns

### ✅ Indicators of Quality

```yaml
spec:
  securityContext:
    runAsNonRoot: true
    runAsUser: 1000
    fsGroup: 2000
    seccompProfile: { type: RuntimeDefault }
  containers:
    - securityContext:
        allowPrivilegeEscalation: false
        readOnlyRootFilesystem: true
        capabilities: { drop: ["ALL"] }
      resources:
        requests: { cpu: 250m, memory: 256Mi }
        limits: { memory: 512Mi }
      readinessProbe:
        httpGet: { path: /health/ready, port: 8080 }
      volumeMounts:
        - { name: tmp, mountPath: /tmp }
  volumes:
    - { name: tmp, emptyDir: {} }
```

**Why this works:** Satisfies PSS restricted, sets resource boundaries, enables traffic-aware routing, and provides writable paths without compromising filesystem immutability.

### ❌ Red Flags

```yaml
spec:
  containers:
    - image: myapp:latest     # SH.5: Untagged
      resources: {}           # OR.1/OR.2: No resources
      # No readinessProbe     # OR.3: Missing probe
      # No securityContext     # SH.1-SH.4: Missing PSS
---
rules:                        # SH.6: God-mode RBAC
  - apiGroups: ["*"]
    resources: ["*"]
    verbs: ["*"]
```

**Why this fails:** Cluster-wide security exposure, uncontrolled resource consumption, no traffic routing signal, and unrestricted API access.

---

## Finding Output Format

Each finding must include: `### [SEVERITY_EMOJI SEVERITY] Title`, then **Location** (file:line), **Criterion** (ID — name), **Issue** (description), **Evidence** (code snippet), **Suggestion** (remediation), **Rationale** (why it matters).

---

## Review Summary Format

Output must include: Verdict (emoji + label), counts table (Files Reviewed, Blockers, Critical, Major, Minor, Suggestions, Commendations), Key Findings (top 3), Recommended Actions (top 3), and Skill Chain Decision with justification.

---

## Skill Chaining

### Chain Triggers

| Verdict                 | Chain Action           | Target Skill              |
| ----------------------- | ---------------------- | ------------------------- |
| `FAIL`                  | Mandatory implement    | `implement/kubernetes`    |
| `NEEDS_WORK`            | Targeted fixes         | `implement/kubernetes`    |
| `PASS_WITH_SUGGESTIONS` | Optional improvements  | None (suggestions only)   |
| `PASS`                  | Continue pipeline      | `test/integration`        |

### Handoff Protocol

When chaining to `implement/kubernetes`, provide: priority finding IDs (blockers + criticals), count of total issues, and constraint to preserve existing application logic and namespace boundaries.

After implement completes, re-invoke this review scoped to modified files with focus on previously-failed criteria. Maximum 3 iterations before escalation.

---

## Deep References

Load on-demand for complex reviews:

| Reference      | When to Load                                    | Path                |
| -------------- | ----------------------------------------------- | ------------------- |
| Workloads      | Reviewing Deployments, StatefulSets, probes     | `refs/workloads.md` |
| Security       | Reviewing PSS, RBAC, NetworkPolicy, secrets     | `refs/security.md`  |
| Networking     | Reviewing Services, Gateway API, Ingress, mesh  | `refs/networking.md`|
| Helm           | Reviewing chart structure, templates, values     | `refs/helm.md`      |
| GitOps         | Reviewing ArgoCD, FluxCD, repo structure        | `refs/gitops.md`    |

---

## Quality Gates

Before finalizing review output:

- [ ] All YAML artifacts in scope were analyzed
- [ ] Each finding has file location + criterion ID + severity
- [ ] Verdict aligns with severity distribution per the decision tree
- [ ] Actionable suggestions provided for every non-PASS finding
- [ ] Chain decision is explicit and justified
- [ ] Output follows the structured review summary format
