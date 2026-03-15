# GitOps Design Patterns

> ArgoCD, FluxCD, and repository structure for continuous delivery.

---

## GitOps Principles

1. **Declarative** - Desired state in Git, not imperative scripts
2. **Versioned** - Git history = change history = rollback capability
3. **Immutable** - Changes via PR, not direct cluster modification
4. **Continuously reconciled** - Agents ensure state matches Git

---

## Tool Selection

| Feature | Argo CD | Flux CD |
|---------|---------|---------|
| UI | Rich web dashboard | None (CLI only) |
| Learning curve | Lower | Higher |
| Resource usage | Higher (~500MB) | Lower (~100MB) |
| Multi-tenancy | Application-level RBAC | Kubernetes RBAC |
| Helm support | Yes (native) | Yes (via controller) |
| Kustomize | Yes | Yes (native) |
| Best for | Developer experience | Platform engineering |

**Recommendation:** Argo CD for most teams; Flux for platform teams or resource-constrained environments

---

## Repository Structure

### Monorepo (Recommended for <50 services)

```
infrastructure-repo/
├── apps/
│   ├── base/
│   │   ├── api/
│   │   │   ├── deployment.yaml
│   │   │   ├── service.yaml
│   │   │   ├── hpa.yaml
│   │   │   └── kustomization.yaml
│   │   └── worker/
│   │       └── ...
│   ├── staging/
│   │   ├── api/
│   │   │   ├── kustomization.yaml      # Patches base
│   │   │   └── replica-patch.yaml
│   │   └── kustomization.yaml
│   └── production/
│       ├── api/
│       │   ├── kustomization.yaml
│       │   └── replica-patch.yaml
│       └── kustomization.yaml
├── infrastructure/
│   ├── base/
│   │   ├── cert-manager/
│   │   ├── external-secrets/
│   │   └── prometheus/
│   ├── staging/
│   └── production/
├── clusters/
│   ├── staging/
│   │   ├── apps.yaml           # ArgoCD Application
│   │   └── infrastructure.yaml
│   └── production/
│       ├── apps.yaml
│       └── infrastructure.yaml
└── README.md
```

### Multi-repo (For large organizations)

```
org/
├── infra-base/          # Shared infrastructure charts
├── infra-staging/       # Staging cluster config
├── infra-production/    # Production cluster config
├── app-api/             # API service repo
└── app-worker/          # Worker service repo
```

---

## Argo CD Configuration

### Installation

```bash
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# Get initial admin password
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d
```

### Application Definition

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: api-production
  namespace: argocd
  finalizers:
  - resources-finalizer.argocd.argoproj.io
spec:
  project: backend
  source:
    repoURL: https://github.com/org/infrastructure.git
    targetRevision: main
    path: apps/production/api
  destination:
    server: https://kubernetes.default.svc
    namespace: backend-prod
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
      allowEmpty: false
    syncOptions:
    - CreateNamespace=true
    - PrunePropagationPolicy=foreground
    - PruneLast=true
    retry:
      limit: 5
      backoff:
        duration: 5s
        factor: 2
        maxDuration: 3m
  ignoreDifferences:
  - group: apps
    kind: Deployment
    jsonPointers:
    - /spec/replicas  # Ignore HPA-managed field
```

### ApplicationSet (Multi-environment)

```yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: api
  namespace: argocd
spec:
  generators:
  - list:
      elements:
      - env: staging
        cluster: https://staging.k8s.example.com
        namespace: backend-staging
      - env: production
        cluster: https://prod.k8s.example.com
        namespace: backend-prod
  template:
    metadata:
      name: 'api-{{env}}'
    spec:
      project: backend
      source:
        repoURL: https://github.com/org/infrastructure.git
        targetRevision: main
        path: 'apps/{{env}}/api'
      destination:
        server: '{{cluster}}'
        namespace: '{{namespace}}'
      syncPolicy:
        automated:
          prune: true
          selfHeal: true
```

### ApplicationSet with Git Generator

```yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: apps
spec:
  generators:
  - git:
      repoURL: https://github.com/org/infrastructure.git
      revision: main
      directories:
      - path: apps/production/*
  template:
    metadata:
      name: '{{path.basename}}'
    spec:
      project: default
      source:
        repoURL: https://github.com/org/infrastructure.git
        targetRevision: main
        path: '{{path}}'
      destination:
        server: https://kubernetes.default.svc
        namespace: '{{path.basename}}'
```

### Project Configuration

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AppProject
metadata:
  name: backend
  namespace: argocd
spec:
  description: Backend services project
  sourceRepos:
  - 'https://github.com/org/infrastructure.git'
  - 'https://charts.bitnami.com/bitnami'
  destinations:
  - namespace: 'backend-*'
    server: https://kubernetes.default.svc
  clusterResourceWhitelist:
  - group: ''
    kind: Namespace
  namespaceResourceWhitelist:
  - group: '*'
    kind: '*'
  roles:
  - name: backend-team
    description: Backend team access
    policies:
    - p, proj:backend:backend-team, applications, *, backend/*, allow
    groups:
    - backend-developers
```

---

## Flux CD Configuration

### Bootstrap

```bash
flux bootstrap github \
  --owner=org \
  --repository=infrastructure \
  --branch=main \
  --path=clusters/production \
  --personal
```

### GitRepository Source

```yaml
apiVersion: source.toolkit.fluxcd.io/v1
kind: GitRepository
metadata:
  name: infrastructure
  namespace: flux-system
spec:
  interval: 1m
  url: https://github.com/org/infrastructure.git
  ref:
    branch: main
  secretRef:
    name: flux-system
```

### Kustomization

```yaml
apiVersion: kustomize.toolkit.fluxcd.io/v1
kind: Kustomization
metadata:
  name: apps
  namespace: flux-system
spec:
  interval: 10m
  targetNamespace: backend-prod
  sourceRef:
    kind: GitRepository
    name: infrastructure
  path: ./apps/production
  prune: true
  healthChecks:
  - apiVersion: apps/v1
    kind: Deployment
    name: api
    namespace: backend-prod
  timeout: 5m
```

### HelmRelease

```yaml
apiVersion: helm.toolkit.fluxcd.io/v2beta2
kind: HelmRelease
metadata:
  name: api
  namespace: backend-prod
spec:
  interval: 5m
  chart:
    spec:
      chart: ./charts/api
      sourceRef:
        kind: GitRepository
        name: infrastructure
        namespace: flux-system
  values:
    replicaCount: 3
    image:
      tag: v2.1.0
  valuesFrom:
  - kind: ConfigMap
    name: api-values
    valuesKey: values.yaml
```

---

## Progressive Delivery

### Argo Rollouts (Canary)

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: api
spec:
  replicas: 5
  strategy:
    canary:
      canaryService: api-canary
      stableService: api-stable
      trafficRouting:
        alb:
          ingress: api-ingress
          servicePort: 80
      steps:
      - setWeight: 10
      - pause: {duration: 5m}
      - setWeight: 30
      - pause: {duration: 5m}
      - setWeight: 50
      - pause: {duration: 10m}
      analysis:
        templates:
        - templateName: success-rate
        startingStep: 1
        args:
        - name: service-name
          value: api-canary
```

### Analysis Template

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: success-rate
spec:
  args:
  - name: service-name
  metrics:
  - name: success-rate
    interval: 1m
    successCondition: result[0] >= 0.95
    failureLimit: 3
    provider:
      prometheus:
        address: http://prometheus:9090
        query: |
          sum(rate(http_requests_total{service="{{args.service-name}}", code=~"2.."}[5m])) /
          sum(rate(http_requests_total{service="{{args.service-name}}"}[5m]))
```

### Flagger (Flux ecosystem)

```yaml
apiVersion: flagger.app/v1beta1
kind: Canary
metadata:
  name: api
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: api
  service:
    port: 80
  analysis:
    interval: 1m
    threshold: 5
    maxWeight: 50
    stepWeight: 10
    metrics:
    - name: request-success-rate
      thresholdRange:
        min: 99
      interval: 1m
    - name: request-duration
      thresholdRange:
        max: 500
      interval: 30s
```

---

## Secrets in GitOps

### Sealed Secrets

```bash
# Install controller
helm install sealed-secrets sealed-secrets/sealed-secrets -n kube-system

# Seal secret
kubeseal --format yaml < secret.yaml > sealed-secret.yaml

# Commit sealed-secret.yaml to Git
```

### External Secrets with ArgoCD

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: external-secrets
spec:
  source:
    repoURL: https://charts.external-secrets.io
    chart: external-secrets
    targetRevision: 0.9.x
  destination:
    server: https://kubernetes.default.svc
    namespace: external-secrets
  syncPolicy:
    automated:
      prune: true
```

---

## Sync Waves and Hooks

### Sync Order with Waves

```yaml
# Wave -1: Namespace (created first)
apiVersion: v1
kind: Namespace
metadata:
  name: backend-prod
  annotations:
    argocd.argoproj.io/sync-wave: "-1"
---
# Wave 0: ConfigMaps/Secrets (default)
apiVersion: v1
kind: ConfigMap
metadata:
  annotations:
    argocd.argoproj.io/sync-wave: "0"
---
# Wave 1: Deployments
apiVersion: apps/v1
kind: Deployment
metadata:
  annotations:
    argocd.argoproj.io/sync-wave: "1"
```

### Hooks

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: db-migrate
  annotations:
    argocd.argoproj.io/hook: PreSync
    argocd.argoproj.io/hook-delete-policy: HookSucceeded
spec:
  template:
    spec:
      containers:
      - name: migrate
        image: api:v2.1.0
        command: ["python", "manage.py", "migrate"]
      restartPolicy: Never
```

---

## Notifications

### Slack Integration

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-notifications-cm
data:
  service.slack: |
    token: $slack-token
  template.app-sync-succeeded: |
    message: |
      Application {{.app.metadata.name}} sync succeeded.
      Revision: {{.app.status.sync.revision}}
  trigger.on-sync-succeeded: |
    - when: app.status.operationState.phase in ['Succeeded']
      send: [app-sync-succeeded]
```
