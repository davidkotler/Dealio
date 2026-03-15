# Workload Design Patterns

> Detailed guidance for selecting and configuring Kubernetes workload controllers.

---

## Deployment Patterns

### Rolling Update Configuration

| Scenario | maxSurge | maxUnavailable | Behavior |
|----------|----------|----------------|----------|
| Zero-downtime | 25% | 0 | Never reduces capacity, slower |
| Balanced | 25% | 25% | Standard trade-off |
| Fast update | 50% | 25% | Prioritizes speed |
| Resource-constrained | 0 | 1 | No extra resources needed |

```yaml
spec:
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 25%
      maxUnavailable: 0  # Zero-downtime
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

---

## StatefulSet Patterns

### When to Use StatefulSet

| Requirement | Use StatefulSet? |
|-------------|------------------|
| Stable network identity | Yes |
| Persistent storage per pod | Yes |
| Ordered deployment/scaling | Yes |
| Simple connection to external DB | No → Deployment |
| Stateless with shared storage | No → Deployment + PVC |

### Database StatefulSet Template

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres
spec:
  serviceName: postgres-headless
  replicas: 3
  podManagementPolicy: OrderedReady  # Parallel for non-ordered
  updateStrategy:
    type: RollingUpdate
    rollingUpdate:
      partition: 0  # Set > 0 for staged rollouts
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

### Headless Service for StatefulSet

```yaml
apiVersion: v1
kind: Service
metadata:
  name: postgres-headless
spec:
  clusterIP: None  # Headless
  selector:
    app: postgres
  ports:
  - port: 5432
    name: postgres
```

**DNS names created:**







- `postgres-0.postgres-headless.{namespace}.svc.cluster.local`
- `postgres-1.postgres-headless.{namespace}.svc.cluster.local`

---

## DaemonSet Patterns

### Use Cases

- Log collectors (Fluent Bit, Filebeat)
- Node monitoring (node-exporter)
- Storage drivers (CSI)
- Network plugins (CNI)

### Selective DaemonSet with Node Selector

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
        accelerator: nvidia  # Only GPU nodes
      tolerations:
      - key: nvidia.com/gpu
        operator: Exists
        effect: NoSchedule
      containers:
      - name: monitor
        image: nvidia/dcgm-exporter:latest
```

---

## Job Patterns

### Parallel Job Processing

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: data-processor
spec:
  parallelism: 5        # Run 5 pods concurrently
  completions: 100      # Total work items
  completionMode: Indexed  # Each pod gets unique index
  backoffLimit: 3
  activeDeadlineSeconds: 3600  # 1 hour timeout
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

### CronJob Best Practices

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: backup
spec:
  schedule: "0 2 * * *"  # 2 AM daily
  timeZone: "America/New_York"  # K8s 1.27+
  concurrencyPolicy: Forbid  # Never overlap
  successfulJobsHistoryLimit: 3
  failedJobsHistoryLimit: 3
  startingDeadlineSeconds: 600  # 10 min window
  jobTemplate:
    spec:
      ttlSecondsAfterFinished: 86400  # Cleanup after 24h
      template:
        spec:
          restartPolicy: OnFailure
```

---

## Probe Configuration

### Probe Types and Purpose

| Probe | Purpose | Failure Action |
|-------|---------|----------------|
| startup | Allow slow-starting apps | Block liveness checks |
| liveness | Detect deadlocks | Restart container |
| readiness | Traffic routing | Remove from service |

### Recommended Configuration

```yaml
spec:
  containers:
  - name: app
    startupProbe:
      httpGet:
        path: /health/startup
        port: 8080
      initialDelaySeconds: 10
      periodSeconds: 5
      failureThreshold: 30  # 150 seconds to start
    livenessProbe:
      httpGet:
        path: /health/live
        port: 8080
      initialDelaySeconds: 0  # Startup probe handles delay
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

### Anti-Patterns

❌ **Don't couple readiness to external dependencies:**
```yaml
# BAD: Fails if database is slow
readinessProbe:
  exec:
    command: ["psql", "-c", "SELECT 1"]
```

✅ **Do check internal state only:**
```yaml
# GOOD: Checks if app can handle requests
readinessProbe:
  httpGet:
    path: /health/ready  # Returns 200 if request queue not full
```

---

## Resource Calculation Guidelines

### Baseline Estimates by Workload Type

| Workload | CPU Request | Memory Request | Notes |
|----------|-------------|----------------|-------|
| FastAPI (Python) | 250m | 256Mi | Increase for high concurrency |
| Go microservice | 100m | 64Mi | Very efficient |
| Java (Spring Boot) | 500m | 512Mi | JVM heap considerations |
| Node.js | 250m | 256Mi | V8 heap management |
| PostgreSQL | 500m | 1Gi | Depends on workload |
| Redis | 100m | 256Mi | Memory-bound |

### Calculating from Metrics

```promql
# P95 CPU usage over 7 days
quantile_over_time(0.95,
  rate(container_cpu_usage_seconds_total{pod=~"api-.*"}[5m])
[7d:1h])

# P95 Memory usage

quantile_over_time(0.95,

  container_memory_working_set_bytes{pod=~"api-.*"}

[7d:1h])

```



**Formula:**

- Request = P95 * 1.2 (20% headroom)
- Limit (memory) = Request * 2 (for spikes)
- Limit (CPU) = Consider omitting for latency-sensitive

---

## Topology and Affinity

### Zone Spread (Production Standard)

```yaml
spec:
  topologySpreadConstraints:
  - maxSkew: 1
    topologyKey: topology.kubernetes.io/zone
    whenUnsatisfiable: DoNotSchedule
    labelSelector:
      matchLabels:
        app: api
```

### Pod Anti-Affinity (Spread Replicas)

```yaml
spec:
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

### Node Affinity (Specific Node Types)

```yaml
spec:
  affinity:
    nodeAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
        nodeSelectorTerms:
        - matchExpressions:
          - key: node-type
            operator: In
            values:
            - compute-optimized
```
