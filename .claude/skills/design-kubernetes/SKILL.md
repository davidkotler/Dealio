---
name: design-kubernetes
version: 1.0.0
description: |
  Architect Kubernetes, Helm, ArgoCD, and EKS configurations before implementation.
  Use when creating or modifying: Deployments, StatefulSets, Services, Ingress, Gateway API,
  NetworkPolicies, RBAC, Helm charts, ArgoCD Applications, Karpenter NodePools, or any YAML
  manifest. Triggers on "design k8s", "plan kubernetes", "architect deployment", "how should
  we structure", "before implementing", or when user mentions EKS, Helm, ArgoCD, Kustomize.
  Activates in plan mode. Produces design artifacts that gate downstream implementation.
  Relevant for cloud-native infrastructure, container orchestration, GitOps workflows.
---

# Kubernetes Design

> Architect production-ready Kubernetes configurations with security, scalability, and operability built-in from the start.

## Quick Reference

| Aspect | Details |
|--------|---------|
| **Invokes** | `implement/kubernetes`, `implement/helm`, `review/infra` |
| **Invoked By** | `design/system`, `design/pulumi` |
| **Key Outputs** | Design Decision Record, Resource Specifications, Security Posture |

---

## Core Workflow

1. **Classify** → Identify workload type and requirements
2. **Scope** → Define namespace, RBAC, and network boundaries  
3. **Specify** → Determine resources, probes, and availability
4. **Secure** → Select PSS level, secrets strategy, policies
5. **Observe** → Plan metrics, logging, and alerting approach
6. **Document** → Produce Design Decision Record (DDR)

## Decision Framework

### Step 1: Workload Classification

```
What are you deploying?
    │
    ├─► Stateless service ──────────► Deployment
    │
    ├─► Stateful (needs identity/storage) ──► StatefulSet
    │                                           └─► Consider: database operators
    │
    ├─► Node-level agent ───────────► DaemonSet
    │
    ├─► One-time task ──────────────► Job
    │
    └─► Scheduled task ─────────────► CronJob
```

### Step 2: Namespace Strategy

```
Recommended: team + environment pattern
    │
    └─► Format: {team}-{environment}
        Examples: backend-prod, frontend-staging, data-dev
```

**Required namespace resources:**







- ResourceQuota (CPU, memory, pod limits)
- LimitRange (default container limits)
- NetworkPolicy (default deny)

### Step 3: Resource Specification

| QoS Target | Memory | CPU | Use Case |
|------------|--------|-----|----------|
| Guaranteed | requests == limits | requests == limits | Databases, critical services |
| Burstable | requests < limits | requests only (no limits) | Most applications |
| BestEffort | none | none | Never for production |

**Rule:** Set memory limits always. Omit CPU limits for latency-sensitive apps.

### Step 4: Security Posture

```
PSS Level Selection:
    │
    ├─► restricted ──► Production workloads (default choice)
    │       └─► runAsNonRoot, readOnlyRootFilesystem, drop ALL
    │
    ├─► baseline ────► Legacy apps requiring privilege
    │
    └─► privileged ──► System components only (CNI, CSI)
```

### Step 5: Availability Design

| Replicas | PDB minAvailable | Topology Spread |
|----------|------------------|-----------------|
| 2 | 1 | Single zone OK |
| 3+ | 2 or 50% | Spread across zones |
| Critical | N-1 | Require multi-zone |

---

## Design Decision Record Template

```markdown
## Kubernetes Design: {Component Name}

### Context
- Purpose: {what this deploys}
- Traffic: {expected RPS/load}
- Data: {stateless/stateful, persistence needs}

### Decisions

#### Workload
- Type: {Deployment|StatefulSet|DaemonSet|Job|CronJob}
- Replicas: {count} | Rationale: {why}

#### Resources
- Requests: CPU={}, Memory={}
- Limits: CPU={none|value}, Memory={}
- QoS Class: {Guaranteed|Burstable}

#### Security
- PSS Level: {restricted|baseline|privileged}
- Service Account: {name, RBAC scope}
- Network Policy: {default-deny + allowlist}
- Secrets: {k8s-native|external-secrets|sealed-secrets}

#### Availability
- PDB: minAvailable={} | maxUnavailable={}
- Topology: {zone spread requirement}
- Probes: liveness={}, readiness={}, startup={}

#### Networking
- Service Type: {ClusterIP|LoadBalancer|Headless}
- Ingress: {Gateway API|ALB Ingress|none}
- DNS: {internal|external}

#### Observability
- Metrics: {prometheus annotations|ServiceMonitor}
- Logging: {stdout format}
- Tracing: {OTEL instrumentation}

### Open Questions
- [ ] {unresolved decisions}
```

---

## Skill Chaining

### Invoke Downstream When

| Condition | Invoke | Handoff Context |
|-----------|--------|-----------------|
| Design approved, ready to implement | `implement/kubernetes` | DDR, resource specs |
| Helm chart needed | `implement/helm` | Values schema, chart structure |
| ArgoCD Application needed | `implement/kubernetes` | Sync policy, project config |
| Implementation complete | `review/infra` | Manifest paths, design rationale |

### Chaining Syntax

```markdown
**Invoking Sub-Skill:** `implement/kubernetes`
**Reason:** Design phase complete, proceeding to manifest generation
**Handoff Context:** DDR approved, security posture: restricted, replicas: 3
```

---

## Critical Validations

### Before Approving Any Design

- [ ] **No naked Pods** → Must use controller (Deployment, StatefulSet, etc.)
- [ ] **No `latest` tags** → Pin versions or SHA digests
- [ ] **Resources specified** → At minimum: memory requests + limits
- [ ] **Probes defined* → readiness required, liveness with startup for slow apps
- [ ] **Security context** → runAsNonRoot, readOnlyRootFilesystem, drop ALL capabilities
- [ ] **Labels applied* → app.kubernetes.io/* standard labels
- [ ] **Network policy* → Default deny exists for namespace

### EKS-Specific Checks

- [ ] **Pod Identity referred** over IRSA for new workloads
- [ ] **Karpenter NodPool** if dynamic scaling needed
- [ ] **VPC CNI** considerations for pod IP capacity
- [ ] **ALB Ingress**annotations for internet-facing

### Helm Chart Checks

- [ ] **values.schema.jsn** for input validation
- [ ] **_helpers.tpl** fr DRY template names
- [ ] **NOTES.txt** withuseful post-install info
- [ ] **Chart.yaml** with proper SemVer

### ArgoCD/GitOps Checks

- [ ] **syncPolicy.automated** with prune and selfHeal
- [ ] **Application in argocd namespace** with proper project
- [ ] **Health checks** configured for custom resources

---

## Patterns

### ✅ Do

- Design namespace + RBAC before any manifests
- Use Gateway API over legacy Ingress (NGINX retiring March 2026)
- Specify topologySpreadConstraints for ≥3 replicas
- Store secrets in external stores (Vault, AWS Secrets Manager)
- Use Karpenter over Cluster Autoscaler on EKS

### ❌ Don't

- Set PDB minAvailable to 100% (blocks all updates)
- Use ClusterRoles when namespace Roles suffice
- Hardcode environment-specific values in manifests
- Skip resource quotas on shared clusters
- Couple readiness probes to external dependencies

---

## Deep References

Load these refs for detailed guidance:

- **[workloads.md](refs/workloads.md)**: Deployment strategies, StatefulSet patterns, Job configurations
- **[security.md](refs/security.md)**: PSS implementation, RBAC patterns, network policy templates
- **[networking.md](refs/networking.md)**: Service mesh decisions, Gateway API migration, CNI selection
- **[helm.md](refs/helm.md)**: Chart structure, templating patterns, values design
- **[eks.md](refs/eks.md)**: Pod Identity setup, Karpenter configuration, cost optimization
- **[gitops.md](refs/gitops.md)**: ArgoCD ApplicationSets, Flux setup, repository structure



---



## Example



### Input

"Design a Kubernetes deployment for our user-api service. It's a FastAPI app handling 500 RPS, connects to PostgreSQL, and needs to be highly available."

### Output (abbreviated DDR)

```markdown
## Kubernetes Design: user-api

### Decisions

#### Workload
- Type: Deployment (stateless, DB connection is external)
- Replicas: 3 (HA requirement, spread across AZs)

#### Resources
- Requests: CPU=250m, Memory=512Mi (based on FastAPI baseline)
- Limits: CPU=none (avoid throttling), Memory=1Gi
- QoS Class: Burstable

#### Security
- PSS Level: restricted
- Service Account: user-api-sa (read secrets only)
- Network Policy: allow ingress from gateway, egress to postgres
- Secrets: External Secrets Operator → AWS Secrets Manager

#### Availability
- PDB: minAvailable=2
- Topology: maxSkew=1 across topology.kubernetes.io/zone
- Probes: readiness + liveness + startup configured

#### Networking
- Service: ClusterIP (internal only)
- Ingress: Gateway API HTTPRoute via AWS ALB
- DNS: user-api.backend-prod.svc.cluster.local

### Next Steps
1. Invoke implement/kubernetes with this DDR
2. Create Helm chart for multi-environment deployment
3. Configure ArgoCD Application with automated sync
```

---

## Quality Gates

Before proceeding to implementation:

- [ ] DDR completed with all sections
- [ ] Security posture explicitly chosen (not defaulted)
- [ ] Resource calculations documented (not guessed)
- [ ] Availability requirements mapped to PDB/topology
- [ ] Observability hooks identified
- [ ] No violations of Patterns ❌ Don't list
