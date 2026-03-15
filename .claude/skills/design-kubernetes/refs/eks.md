# AWS EKS Design Patterns

> EKS-specific architecture decisions, identity management, and cost optimization.

---

## Cluster Architecture

### Control Plane Configuration

| Setting | Development | Production |
|---------|-------------|------------|
| API endpoint | Public | Private (or Public with CIDR) |
| Logging | Minimal | All types enabled |
| Secrets encryption | Optional | Required (KMS) |

```bash
# Enable all control plane logging
aws eks update-cluster-config \
  --name my-cluster \
  --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}'
```

### Data Plane Options

| Option | Use Case | Cost | Management |
|--------|----------|------|------------|
| Managed Node Groups | General workloads | Medium | Low |
| Self-managed | Custom AMIs | Medium | High |
| Fargate | Burst, serverless | Higher | Lowest |
| Karpenter | Cost-optimized | Lowest | Medium |

**Recommendation:** Karpenter for most workloads, Fargate for spiky/batch

---

## EKS Pod Identity (Recommended)

### Why Pod Identity over IRSA?

| Feature | Pod Identity | IRSA |
|---------|--------------|------|
| OIDC provider setup | Not required | Required |
| Cross-cluster reuse | Easy | Complex |
| Session tags | Supported | Not supported |
| Auditability | Better | Standard |

### Setup Pod Identity

```bash
# 1. Install Pod Identity Agent add-on
aws eks create-addon \
  --cluster-name my-cluster \
  --addon-name eks-pod-identity-agent

# 2. Create IAM role with trust policy
aws iam create-role \
  --role-name my-app-role \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {
        "Service": "pods.eks.amazonaws.com"
      },
      "Action": ["sts:AssumeRole", "sts:TagSession"]
    }]
  }'

# 3. Attach permissions
aws iam attach-role-policy \
  --role-name my-app-role \
  --policy-arn arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess

# 4. Create pod identity association
aws eks create-pod-identity-association \
  --cluster-name my-cluster \
  --namespace backend-prod \
  --service-account my-app-sa \
  --role-arn arn:aws:iam::123456789012:role/my-app-role
```

### Kubernetes Configuration

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: my-app-sa
  namespace: backend-prod
  # No annotations needed for Pod Identity!
---
apiVersion: apps/v1
kind: Deployment
spec:
  template:
    spec:
      serviceAccountName: my-app-sa
      # Credentials injected automatically
```

---

## IRSA (Legacy/Hybrid)

### When to Use IRSA

- EKS Anywhere clusters
- Hybrid cloud scenarios
- Cross-account access patterns
- Existing IRSA infrastructure

### Setup IRSA

```bash
# 1. Get OIDC provider
OIDC_PROVIDER=$(aws eks describe-cluster --name my-cluster \
  --query "cluster.identity.oidc.issuer" --output text | sed 's|https://||')

# 2. Create trust policy
cat > trust-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {
      "Federated": "arn:aws:iam::123456789012:oidc-provider/${OIDC_PROVIDER}"
    },
    "Action": "sts:AssumeRoleWithWebIdentity",
    "Condition": {
      "StringEquals": {
        "${OIDC_PROVIDER}:aud": "sts.amazonaws.com",
        "${OIDC_PROVIDER}:sub": "system:serviceaccount:backend-prod:my-app-sa"
      }
    }
  }]
}
EOF
```

### Service Account Annotation

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: my-app-sa
  namespace: backend-prod
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/my-app-role
```

---

## Karpenter Configuration

### Why Karpenter?

- **30-50% cost savings** via better bin-packing
- **Faster scaling** than Cluster Autoscaler (seconds vs minutes)
- **Automatic instance selection** based on pod requirements

### NodePool Configuration

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: default
spec:
  template:
    spec:
      requirements:
      - key: kubernetes.io/arch
        operator: In
        values: ["amd64", "arm64"]
      - key: karpenter.sh/capacity-type
        operator: In
        values: ["spot", "on-demand"]
      - key: karpenter.k8s.aws/instance-category
        operator: In
        values: ["c", "m", "r"]
      - key: karpenter.k8s.aws/instance-size
        operator: NotIn
        values: ["nano", "micro", "small"]
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: default
  limits:
    cpu: 1000
    memory: 2000Gi
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 1m
---
apiVersion: karpenter.k8s.aws/v1
kind: EC2NodeClass
metadata:
  name: default
spec:
  amiSelectorTerms:
  - alias: bottlerocket@latest
  subnetSelectorTerms:
  - tags:
      karpenter.sh/discovery: my-cluster
  securityGroupSelectorTerms:
  - tags:
      karpenter.sh/discovery: my-cluster
  role: KarpenterNodeRole-my-cluster
  tags:
    Environment: production
  blockDeviceMappings:
  - deviceName: /dev/xvda
    ebs:
      volumeSize: 100Gi
      volumeType: gp3
      encrypted: true
```

### Workload Requirements for Karpenter

```yaml
spec:
  affinity:
    nodeAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
        nodeSelectorTerms:
        - matchExpressions:
          - key: karpenter.sh/capacity-type
            operator: In
            values: ["spot"]  # Request spot instances
  tolerations:
  - key: "karpenter.sh/disruption"
    operator: "Exists"  # Allow Karpenter to consolidate
```

### GPU Workloads

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: gpu
spec:
  template:
    spec:
      requirements:
      - key: karpenter.k8s.aws/instance-family
        operator: In
        values: ["g5", "p4d"]
      - key: karpenter.sh/capacity-type
        operator: In
        values: ["on-demand"]  # Spot not reliable for GPU
      taints:
      - key: nvidia.com/gpu
        effect: NoSchedule
```

---

## VPC CNI Configuration

### Prefix Delegation (Higher Pod Density)

```bash
# Enable prefix delegation
kubectl set env daemonset aws-node -n kube-system \
  ENABLE_PREFIX_DELEGATION=true \
  WARM_PREFIX_TARGET=1

# Pod density comparison
# Without prefix: ~29 pods/m5.large
# With prefix: ~110 pods/m5.large
```

### Security Groups for Pods

```bash
# Enable security groups for pods
kubectl set env daemonset aws-node -n kube-system \
  ENABLE_POD_ENI=true
```

```yaml
apiVersion: vpcresources.k8s.aws/v1beta1
kind: SecurityGroupPolicy
metadata:
  name: api-sg-policy
  namespace: backend-prod
spec:
  podSelector:
    matchLabels:
      app: api
  securityGroups:
    groupIds:
    - sg-0123456789abcdef0  # RDS access
```

---

## ALB Ingress Controller

### Installation

```bash
# Install via Helm
helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
  -n kube-system \
  --set clusterName=my-cluster \
  --set serviceAccount.create=false \
  --set serviceAccount.name=aws-load-balancer-controller
```

### Internet-facing ALB

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: api-ingress
  annotations:
    kubernetes.io/ingress.class: alb
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/certificate-arn: arn:aws:acm:...
    alb.ingress.kubernetes.io/ssl-redirect: "443"
    alb.ingress.kubernetes.io/healthcheck-path: /health
    alb.ingress.kubernetes.io/healthcheck-interval-seconds: "15"
    alb.ingress.kubernetes.io/actions.ssl-redirect: |
      {"Type": "redirect", "RedirectConfig": { "Protocol": "HTTPS", "Port": "443", "StatusCode": "HTTP_301"}}
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

### Internal ALB

```yaml
metadata:
  annotations:
    alb.ingress.kubernetes.io/scheme: internal
    alb.ingress.kubernetes.io/target-type: ip
```

---

## Cost Optimization

### Savings Strategies

| Strategy | Savings | Commitment |
|----------|---------|------------|
| Spot instances | Up to 90% | None (interruptible) |
| Savings Plans | Up to 72% | 1-3 years |
| Reserved Instances | Up to 75% | 1-3 years |
| Graviton (ARM) | 20-40% | None |

### EKS Version Costs

| Support Type | Cost/Hour |
|--------------|-----------|
| Standard support | $0.10 |
| Extended support | $0.60 |

**Keep clusters on standard support versions** (current -2)

### Right-sizing with Goldilocks

```bash
# Install Goldilocks
helm install goldilocks fairwinds-stable/goldilocks --namespace goldilocks

# Enable on namespace
kubectl label ns backend-prod goldilocks.fairwinds.com/enabled=true

# View recommendations
kubectl port-forward svc/goldilocks-dashboard 8080:80 -n goldilocks
```

### Cost Monitoring

```bash
# Install Kubecost
helm install kubecost kubecost/cost-analyzer \
  --namespace kubecost \
  --set kubecostToken="<token>"

# Or use OpenCost (open source)
helm install opencost opencost/opencost
kubectl cost namespace --window 2h --show-efficiency=true
```

---

## Observability

### Container Insights

```bash
# Install CloudWatch agent
aws eks create-addon \
  --cluster-name my-cluster \
  --addon-name amazon-cloudwatch-observability
```

### Application Signals (APM)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  annotations:
    instrumentation.opentelemetry.io/inject-python: "true"  # Auto-instrument
spec:
  template:
    spec:
      containers:
      - name: api
        env:
        - name: OTEL_EXPORTER_OTLP_ENDPOINT
          value: "http://cloudwatch-agent.amazon-cloudwatch:4317"
```

---

## Upgrade Strategy

### Upgrade Order

1. **Control plane** (AWS managed, just click upgrade)
2. **Add-ons** (VPC CNI, CoreDNS, kube-proxy, EBS CSI)
3. **Node groups** (rolling update or blue-green)

### Pre-upgrade Checklist

- [ ] Review release notes for breaking changes
- [ ] Check deprecated API usage: `kubectl get --raw /metrics | grep apiserver_requested_deprecated_apis`
- [ ] Validate PDBs allow rolling updates
- [ ] Test in staging environment
- [ ] Schedule maintenance window

### Add-on Versions

```bash
# Check recommended versions
aws eks describe-addon-versions \
  --addon-name vpc-cni \
  --kubernetes-version 1.29

# Update add-on
aws eks update-addon \
  --cluster-name my-cluster \
  --addon-name vpc-cni \
  --addon-version v1.15.0-eksbuild.2
```
