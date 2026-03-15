# Workloads Reference

## Table of Contents







- Deployment Patterns
- StatefulSet Patterns
- DaemonSet Patterns
- Job and CronJob Patterns
- Probe Configuration
- Resource Calculation
- Topology and Affinity

---

## Deployment Patterns

### Rolling Update Strategies

| Scenario | maxSurge | maxUnavailable | Use When |
|----------|----------|----------------|----------|
| Zero-downtime | 25% | 0 | Production services, user-facing APIs |
| Balanced | 25% | 25% | Standard workloads |
| Fast update | 50% | 25% | Non-critical, speed matters |
| Resource-constrained | 0 | 1 | Tight node capacity |

```yaml
spec:
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 25%
      maxUnavailable: 0
```

### Blue-Green with Argo Rollouts

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: api-rollout
spec:
  replicas: 3
  strategy:
    blueGreen:
      activeService: api-active
      previewService: api-preview
      autoPromotionEnabled: false
      prePromotionAnalysis:
        templates:
        - templateName: success-rate
```

### Canary with Analysis

```yaml
spec:
  strategy:
    canary:
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
```

### Config Reload via Checksum Annotation

Force pod restart when ConfigMap changes:
```yaml
template:
  metadata:
    annotations:
      checksum/config: {{ include (print $.Template.BasePath "/configmap.yaml") . | sha256sum }}
```

---

## StatefulSet Patterns

### When to Use

| Requirement | StatefulSet? |
|-------------|-------------|
| Stable network identity (pod-0, pod-1) | Yes |
| Persistent storage per pod | Yes |
| Ordered deployment/scaling | Yes |
| Simple connection to external DB | No → Deployment |
| Stateless + shared storage | No → Deployment + PVC |

### Database Template

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres
spec:
  serviceName: postgres-headless
  replicas: 3
  podManagementPolicy: OrderedReady    # Parallel for non-ordered
  updateStrategy:
    type: RollingUpdate
    rollingUpdate:
      partition: 0                     # Set > 0 for staged rollouts
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      terminationGracePeriodSeconds: 120
      containers:
      - name: postgres
        image: postgres:15.4
        ports:
        - containerPort: 5432
          name: postgres
        env:
        - name: PGDATA
          value: /var/lib/postgresql/data/pgdata  # Subdirectory required
        volumeMounts:
        - name: data
          mountPath: /var/lib/postgresql/data
        resources:
          requests:
            cpu: "500m"
            memory: "1Gi"
          limits:
            memory: "2Gi"
  volumeClaimTemplates:
  - metadata:
      name: data
    spec:
      accessModes: ["ReadWriteOnce"]
      storageClassName: fast-ssd
      resources:
        requests:
          storage: 50Gi
```

### Headless Service (Required for StatefulSet)

```yaml
apiVersion: v1
kind: Service
metadata:
  name: postgres-headless
spec:
  clusterIP: None
  selector:
    app: postgres

  ports:

  - port: 5432

    name: postgres

```



DNS names created:

- `postgres-0.postgres-headless.{namespace}.svc.cluster.local`
- `postgres-1.postgres-headless.{namespace}.svc.cluster.local`

---

## DaemonSet Patterns

Use cases: log collectors, node monitoring, storage drivers, network plugins.

### Selective DaemonSet

```yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: gpu-monitor
spec:
  selector:
    matchLabels:
      app: gpu-monitor
  template:
    spec:
      nodeSelector:
        accelerator: nvidia
      tolerations:
      - key: nvidia.com/gpu
        operator: Exists
        effect: NoSchedule
      containers:
      - name: monitor
        image: nvidia/dcgm-exporter:3.3.0
```

---

## Job and CronJob Patterns

### Parallel Job

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: data-processor
spec:
  parallelism: 5
  completions: 100
  completionMode: Indexed
  backoffLimit: 3
  activeDeadlineSeconds: 3600
  template:
    spec:
      restartPolicy: Never
      containers:
      - name: processor
        image: processor:v1
        env:
        - name: JOB_INDEX
          valueFrom:
            fieldRef:
              fieldPath: metadata.annotations['batch.kubernetes.io/job-completion-index']
```

### CronJob

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: backup
spec:
  schedule: "0 2 * * *"
  timeZone: "America/New_York"
  concurrencyPolicy: Forbid
  successfulJobsHistoryLimit: 3
  failedJobsHistoryLimit: 3
  startingDeadlineSeconds: 600
  jobTemplate:
    spec:
      ttlSecondsAfterFinished: 86400
      template:
        spec:
          restartPolicy: OnFailure
```

---

## Probe Configuration

### Probe Purposes

| Probe | Purpose | On Failure |
|-------|---------|------------|
| startup | Allow slow-starting apps | Blocks liveness checks |
| liveness | Detect deadlocks | Restarts container |
| readiness | Traffic routing | Removes from service endpoints |

### Recommended Template

```yaml
startupProbe:
  httpGet:
    path: /health/startup
    port: 8080
  initialDelaySeconds: 10
  periodSeconds: 5
  failureThreshold: 30          # 150s total startup window

livenessProbe:
  httpGet:
    path: /health/live
    port: 8080
  initialDelaySeconds: 0        # Startup probe handles delay
  periodSeconds: 10
  failureThreshold: 3
  timeoutSeconds: 5


readinessProbe:

  httpGet:
    path: /health/ready

    port: 8080
  initialDelaySeconds: 0

  periodSeconds: 5
  failureThreshold: 3

  timeoutSeconds: 3
```


### Rules

- **Never** couple readiness probes to external dependencies (DB, cache)
- Readiness should check if app can handle requests (queue not full, initialized)
- Liveness should check if app is alive (not deadlocked)
- Always use startup probe for apps that take >10s to start

---

## Resource Calculation

### Baseline Estimates

| Workload | CPU Request | Memory Request | Notes |
|----------|-------------|----------------|-------|

| FastAPI (Python) | 250m | 256Mi | Increase for high concurrency |
| Go microservice | 100m | 64Mi | Very efficient |
| Java (Spring Boot) | 500m | 512Mi | JVM heap considerations |

| Node.js | 250m | 256Mi | V8 heap management |
| PostgreSQL | 500m | 1Gi | Depends on data size |
| Redis | 100m | 256Mi | Memory-bound |


### From Metrics (PromQL)


```promql
# P95 CPU usage over 7 days
quantile_over_time(0.95, rate(container_cpu_usage_seconds_total{pod=~"api-.*"}[5m])[7d:1h])


# P95 Memory usage
quantile_over_time(0.95, container_memory_working_set_bytes{pod=~"api-.*"}[7d:1h])

```

**Formula:**

- Request = P95 × 1.2 (20% headroom)
- Limit (memory) = Request × 2 (spike buffer)
- Limit (CPU) = Omit for latency-sensitive workloads

### QoS Classes

| QoS | Memory | CPU | Use Case |
|-----|--------|-----|----------|
| Guaranteed | requests == limits | requests == limits | Databases, critical |
| Burstable | requests < limits | requests only | Most applications |
| BestEffort | none | none | Never for production |

---

## Topology and Affinity

### Zone Spread (Required for replicas >= 3)

```yaml
topologySpreadConstraints:
- maxSkew: 1
  topologyKey: topology.kubernetes.io/zone
  whenUnsatisfiable: DoNotSchedule
  labelSelector:
    matchLabels:
      app: api
```

### Pod Anti-Affinity (Spread across hosts)

```yaml
affinity:
  podAntiAffinity:
    preferredDuringSchedulingIgnoredDuringExecution:
    - weight: 100
      podAffinityTerm:
        labelSelector:
          matchLabels:
            app: api
        topologyKey: kubernetes.io/hostname
```

### Node Affinity

```yaml
affinity:

  nodeAffinity:
    requiredDuringSchedulingIgnoredDuringExecution:
      nodeSelectorTerms:
      - matchExpressions:

        - key: node-type
          operator: In
          values: ["compute-optimized"]
```


### PodDisruptionBudget

```yaml

apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: api-pdb

spec:
  minAvailable: 2        # Or use maxUnavailable: 1
  selector:
    matchLabels:

      app: api
```

**Rules:**

- Never set `minAvailable: 100%` — blocks all updates
- For 2 replicas: `minAvailable: 1`
- For 3+ replicas: `minAvailable: 2` or `maxUnavailable: 1`
