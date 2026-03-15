---
name: implement-kubernetes
version: 1.0.0
description: |
  Implement production-ready Kubernetes manifests, Helm charts, ArgoCD Applications, and EKS configurations.
  Use when creating, modifying, or generating: Deployments, StatefulSets, DaemonSets, Jobs, CronJobs,
  Services, Ingress, Gateway API routes, NetworkPolicies, RBAC roles, PodDisruptionBudgets, HPAs,
  Helm charts, ArgoCD Applications/ApplicationSets, Karpenter NodePools, Kustomize overlays,
  ExternalSecrets, SealedSecrets, Kyverno policies, or any YAML manifest for Kubernetes.
  Triggers on "implement k8s", "create deployment", "write helm chart", "generate manifests",
  "configure argocd", "setup eks", "create service", "add network policy", "write kustomization",
  or when producing .yaml files for container orchestration.
  Also triggers when editing existing Kubernetes YAML, fixing manifest errors, or migrating
  from Ingress to Gateway API. Relevant for Kubernetes, EKS, Helm, ArgoCD, FluxCD, Kustomize.
---

# Kubernetes Implementation

> Generate validated, production-grade Kubernetes manifests from design decisions or direct requirements.

## Quick Reference

| Aspect | Details |
|--------|---------|
| **Invoked By** | `design-kubernetes` (via DDR handoff) |
| **Chains To** | `review/infra`, `implement/helm`, `test/integration` |
| **Validates With** | `kubectl --dry-run=client`, `helm template`, `helm lint` |

## Core Workflow

1. **Gather Context** — Accept DDR from `design-kubernetes` or extract requirements from user request
2. **Load References** — Read only the refs needed for this task (see Reference Selection below)
3. **Generate Manifests** — Produce YAML following patterns from refs, applying all mandatory rules
4. **Validate** — Dry-run every manifest; lint every Helm chart
5. **Organize** — Place files in correct directory structure (Kustomize base/overlays or Helm chart)
6. **Chain** — Hand off to review if requested, or report completion

## Reference Selection

Load refs on-demand based on task. **Do not load all refs.**

| Task | Load |
|------|------|
| Deployment, StatefulSet, DaemonSet, Job, CronJob, probes, resources, topology | [refs/workloads.md](refs/workloads.md) |
| PSS, RBAC, NetworkPolicy, secrets, Kyverno, image security | [refs/security.md](refs/security.md) |
| Services, Gateway API, Ingress, CNI, service mesh, DNS, traffic mgmt | [refs/networking.md](refs/networking.md) |
| Helm chart creation, values design, templates, hooks, testing | [refs/helm.md](refs/helm.md) |
| EKS Pod Identity, IRSA, Karpenter, VPC CNI, ALB controller, cost | [refs/eks.md](refs/eks.md) |
| ArgoCD, FluxCD, ApplicationSets, progressive delivery, repo structure | [refs/gitops.md](refs/gitops.md) |

**Multiple refs often required.** Example: creating a Helm chart for an EKS deployment needs `refs/helm.md` + `refs/eks.md` + `refs/workloads.md`.

## Mandatory Rules (Every Manifest)

These apply to ALL generated Kubernetes YAML. Never omit.

### Labels







```yaml
metadata:
  labels:
    app.kubernetes.io/name: <app>

    app.kubernetes.io/instance: <release>

    app.kubernetes.io/version: <version>

    app.kubernetes.io/managed-by: <helm|kustomize|manual>

```



### Security Context (All Pods)

```yaml
securityContext:
  runAsNonRoot: true
  runAsUser: 1000
  runAsGroup: 3000

  fsGroup: 2000
  seccompProfile:

    type: RuntimeDefault
containers:

- securityContext:
    allowPrivilegeEscalation: false

    readOnlyRootFilesystem: true
    capabilities:


      drop: ["ALL"]
```




### Resources (All Containers)




```yaml
resources:



  requests:
    cpu: <value>       # Always set
    memory: <value>    # Always set




  limits:
    memory: <value>    # Always set
    # cpu: omit for latency-sensitive workloads




```


### Probes (All Long-Running Containers)




Readiness probe is always required. Add startup probe for slow-starting apps. Liveness probe with care — never couple to external dependencies.


### Image Tags




Never use `:latest`. Always pin to a specific version tag or SHA digest.


## Decision Trees



### Workload Type

```
Requirement → Controller

├─ Stateless HTTP/gRPC service → Deployment
├─ Stable identity + persistent storage → StatefulSet


├─ Every-node agent (logs, monitoring) → DaemonSet
├─ One-time batch processing → Job
└─ Scheduled recurring task → CronJob

```


### Service Exposure


```
Traffic Source → Service Type + Ingress
├─ Cluster-internal only → ClusterIP

├─ StatefulSet direct pod access → Headless (clusterIP: None)

├─ External HTTP/HTTPS → ClusterIP + Gateway API HTTPRoute (preferred)
│                         └─ or ClusterIP + ALB Ingress (legacy)

├─ External TCP/UDP → LoadBalancer (NLB)
└─ Development/testing → NodePort
```


### Secrets Strategy

```
Environment → Strategy

├─ Production → External Secrets Operator + cloud provider (AWS SM, Vault)
├─ GitOps required → Sealed Secrets (encrypted in Git)
└─ Development only → Kubernetes native Secrets (not for prod)
```


## Output Organization

### Kustomize Layout


```
apps/
├── base/
│   └── <app>/

│       ├── deployment.yaml
│       ├── service.yaml
│       ├── hpa.yaml
│       ├── pdb.yaml
│       ├── networkpolicy.yaml

│       └── kustomization.yaml
└── overlays/
    ├── staging/
    │   └── <app>/

    │       ├── kustomization.yaml
    │       └── patches/
    └── production/
        └── <app>/
            ├── kustomization.yaml

            └── patches/
```

### Helm Chart Layout

```
charts/<app>/
├── Chart.yaml
├── values.yaml
├── values.schema.json

├── templates/
│   ├── _helpers.tpl
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── hpa.yaml
│   ├── pdb.yaml
│   ├── serviceaccount.yaml
│   ├── networkpolicy.yaml
│   ├── NOTES.txt
│   └── tests/

│       └── test-connection.yaml
└── ci/
    ├── values-staging.yaml
    └── values-production.yaml
```

## Validation Checklist

Run after generating every set of manifests:


```bash
# Validate YAML syntax and K8s schema
kubectl apply --dry-run=client -f <manifest>.yaml

# Helm specific
helm lint ./charts/<app>/
helm template <release> ./charts/<app>/ -f values-production.yaml | kubectl apply --dry-run=client -f -
```

### Must-Pass Checks

- [ ] No `image: *:latest` anywhere
- [ ] All containers have `resources.requests.memory` and `resources.limits.memory`
- [ ] All long-running pods have `readinessProbe`
- [ ] `securityContext.runAsNonRoot: true` on every pod
- [ ] `allowPrivilegeEscalation: false` on every container
- [ ] `readOnlyRootFilesystem: true` with emptyDir mounts for writable paths
- [ ] `capabilities.drop: ["ALL"]` on every container
- [ ] Namespace has `default-deny` NetworkPolicy
- [ ] No wildcard (`*`) RBAC verbs or resources
- [ ] `app.kubernetes.io/name` label on every resource
- [ ] PDB exists for replicas >= 2
- [ ] `topologySpreadConstraints` for replicas >= 3
- [ ] Gateway API used over legacy Ingress for new deployments

## Anti-Patterns (Never Generate)

```yaml
# ❌ God-mode RBAC
rules:
- apiGroups: ["*"]
  resources: ["*"]
  verbs: ["*"]

# ❌ Readiness probe hitting external DB
readinessProbe:
  exec:
    command: ["psql", "-c", "SELECT 1"]

# ❌ PDB blocking all updates
spec:
  minAvailable: 100%

# ❌ Missing emptyDir for read-only filesystem
readOnlyRootFilesystem: true
# without corresponding emptyDir mounts for /tmp, cache dirs

# ❌ Hardcoded env-specific values in base manifests
# Use Kustomize overlays or Helm values instead
```

## Chaining

| Condition | Action |
|-----------|--------|
| DDR received from `design-kubernetes` | Implement all decisions from DDR |
| Helm chart required | Load `refs/helm.md`, generate chart |
| ArgoCD Application needed | Load `refs/gitops.md`, generate Application |
| EKS-specific (Pod Identity, Karpenter) | Load `refs/eks.md` |
| Implementation complete, review requested | Hand off to `review/infra` with manifest paths |
| Design unclear or missing | Ask user to clarify, or invoke `design-kubernetes` first
