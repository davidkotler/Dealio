# Networking Reference

## Table of Contents







- Service Types
- Gateway API (Modern Standard)
- AWS Load Balancer Controller
- CNI Selection
- Service Mesh
- DNS Configuration
- Traffic Management

---

## Service Types

| Type | Use Case | External Access | Load Balancing |
|------|----------|-----------------|----------------|
| ClusterIP | Internal services | No | kube-proxy |
| NodePort | Development/testing | Via node IP | kube-proxy |
| LoadBalancer | Production external | Cloud LB | Cloud provider |
| ExternalName | DNS alias | N/A | N/A |
| Headless | StatefulSet, direct pod | No | None (DNS) |

### ClusterIP (Default)

```yaml
apiVersion: v1
kind: Service
metadata:
  name: api
spec:
  type: ClusterIP
  selector:
    app: api
  ports:
  - port: 80
    targetPort: 8080
    protocol: TCP
```

### Headless Service

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
```

DNS records: `postgres-0.postgres-headless.namespace.svc.cluster.local`

---

## Gateway API (Modern Standard)

**⚠️ NGINX Ingress Controller retiring March 2026 — use Gateway API for all new deployments.**

### Gateway API vs Ingress

| Feature | Ingress | Gateway API |
|---------|---------|-------------|
| Traffic splitting | Limited | Native |
| Header-based routing | Controller-dependent | Standard |
| Role separation | No | Yes (infra/app) |
| Multi-tenant | Limited | Built-in |

### Gateway

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: main-gateway
  namespace: gateway-system
spec:
  gatewayClassName: aws-alb     # or: istio, contour, nginx
  listeners:
  - name: https
    port: 443
    protocol: HTTPS
    hostname: "*.example.com"
    tls:
      mode: Terminate
      certificateRefs:
      - name: wildcard-cert
    allowedRoutes:
      namespaces:
        from: Selector
        selector:
          matchLabels:
            gateway-access: "true"
```

### HTTPRoute

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: api-route
  namespace: backend-prod
spec:
  parentRefs:
  - name: main-gateway
    namespace: gateway-system
  hostnames:
  - "api.example.com"
  rules:
  - matches:
    - path:
        type: PathPrefix
        value: /v1
    backendRefs:
    - name: api-v1
      port: 80
      weight: 90
    - name: api-v2
      port: 80
      weight: 10           # Canary
  - matches:
    - path:
        type: PathPrefix
        value: /v2
    backendRefs:
    - name: api-v2
      port: 80
```

### Header-Based Routing

```yaml
rules:
- matches:
  - headers:
    - name: x-canary
      value: "true"
  backendRefs:
  - name: api-canary
    port: 80
- backendRefs:
  - name: api-stable
    port: 80
```

---

## AWS Load Balancer Controller

### ALB Ingress (Legacy — use Gateway API for new)

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: api-ingress
  annotations:
    kubernetes.io/ingress.class: alb
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/healthcheck-path: /health
    alb.ingress.kubernetes.io/healthcheck-interval-seconds: "15"
    alb.ingress.kubernetes.io/ssl-redirect: "443"
    alb.ingress.kubernetes.io/certificate-arn: arn:aws:acm:...
spec:
  rules:
  - host: api.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: api
            port:
              number: 80
```

### NLB for TCP/UDP

```yaml
apiVersion: v1
kind: Service
metadata:
  name: tcp-service
  annotations:
    service.beta.kubernetes.io/aws-load-balancer-type: external
    service.beta.kubernetes.io/aws-load-balancer-nlb-target-type: ip
    service.beta.kubernetes.io/aws-load-balancer-scheme: internet-facing
spec:
  type: LoadBalancer
  ports:
  - port: 5432
    targetPort: 5432
    protocol: TCP
```

---

## CNI Selection

| CNI | Best For | Network Policy | Performance |
|-----|----------|----------------|-------------|
| AWS VPC CNI | EKS native | Via Calico | Excellent |
| Cilium | Modern, eBPF | L3/L4/L7 | Excellent |
| Calico | Enterprise, BGP | L3/L4 | Very good |
| Flannel | Simple/learning | None | Good |

### AWS VPC CNI — Prefix Delegation

```bash
kubectl set env daemonset aws-node -n kube-system \
  ENABLE_PREFIX_DELEGATION=true \
  WARM_PREFIX_TARGET=1
```

IP capacity per node:

| Instance | Default | With Prefix |
|----------|---------|-------------|
| m5.large | 29 | 110 |
| m5.xlarge | 58 | 234 |

### Cilium with VPC CNI

```bash
helm install cilium cilium/cilium \
  --namespace kube-system \
  --set cni.chainingMode=aws-cni \
  --set enableIPv4Masquerade=false \
  --set tunnel=disabled
```

---

## Service Mesh

### When to Use

✅ Use when: mTLS required, complex traffic management, 50+ microservices, infrastructure-layer retry/timeout
❌ Avoid when: <10 services, latency-critical, team lacks expertise

### Performance Impact

| Mesh | Latency Overhead | Memory/Pod |
|------|------------------|------------|
| Linkerd | 15-25% | ~25MB |
| Istio (sidecar) | 25-35% | ~100MB |
| Istio Ambient | 20-30% | 0 (daemonset) |
| Cilium Mesh | 20-30% | ~50MB |

### Istio Ambient Mode (Sidecar-less)

```bash
kubectl label namespace backend-prod istio.io/dataplane-mode=ambient
```

---

## DNS Configuration

### CoreDNS Tuning

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: coredns
  namespace: kube-system
data:
  Corefile: |
    .:53 {
        errors
        health { lameduck 5s }
        ready
        kubernetes cluster.local in-addr.arpa ip6.arpa {
            pods insecure
            fallthrough in-addr.arpa ip6.arpa
            ttl 30
        }
        prometheus :9153
        forward . /etc/resolv.conf { max_concurrent 1000 }
        cache 30
        loop

        reload

        loadbalance


    }


```





### DNS Best Practices


- Create Services before Pods that depend on them

- Use fully qualified names in cross-namespace calls
- Reduce search domain queries:

```yaml
spec:
  dnsConfig:
    options:
    - name: ndots
      value: "2"
```

---

## Traffic Management

### Rate Limiting (Gateway API)

```yaml
apiVersion: gateway.networking.k8s.io/v1alpha2
kind: BackendTrafficPolicy
metadata:
  name: rate-limit
spec:
  targetRef:
    group: gateway.networking.k8s.io
    kind: HTTPRoute
    name: api-route
  rateLimit:
    type: Local
    local:
      requests: 100
      unit: Second
```

### Circuit Breaking (Istio)

```yaml
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: api-circuit-breaker
spec:
  host: api.backend-prod.svc.cluster.local
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 100
      http:
        h2UpgradePolicy: UPGRADE
        http1MaxPendingRequests: 100
        http2MaxRequests: 1000
    outlierDetection:
      consecutive5xxErrors: 5
      interval: 30s
      baseEjectionTime: 30s
      maxEjectionPercent: 50
```

### Retries and Timeouts (Gateway API)

```yaml
rules:
- backendRefs:
  - name: api
    port: 80
  timeouts:
    request: 30s
    backendRequest: 25s
  filters:
  - type: RequestRetry
    requestRetry:
      attempts: 3
      backoff:
        baseInterval: 25ms
        maxInterval: 250ms
      retryOn: [5xx, reset, connect-failure]
```
