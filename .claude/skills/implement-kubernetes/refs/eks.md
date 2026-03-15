# AWS EKS Reference

## Table of Contents







- Cluster Architecture
- EKS Pod Identity (Recommended)
- IRSA (Legacy)
- Karpenter Configuration
- VPC CNI Configuration
- ALB Ingress Controller
- Cost Optimization
- Observability
- Upgrade Strategy

---

## Cluster Architecture

### Control Plane

| Setting | Development | Production |
|---------|-------------|------------|
| API endpoint | Public | Private (or Public with CIDR) |
| Logging | Minimal | All types enabled |
| Secrets encryption | Optional | Required (KMS) |

```bash
aws eks update-cluster-config --name my-cluster \
  --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}'
```

### Data Plane Options

| Option | Use Case | Cost | Management |
|--------|----------|------|------------|
| Managed Node Groups | General workloads | Medium | Low |
| Karpenter | Cost-optimized | Lowest | Medium |
| Fargate | Burst, serverless | Higher | Lowest |
| Self-managed | Custom AMIs | Medium | High |

**Recommendation:** Karpenter for most workloads, Fargate for spiky/batch.

---

## EKS Pod Identity (Recommended over IRSA)

### Pod Identity vs IRSA

| Feature | Pod Identity | IRSA |
|---------|-------------|------|
| OIDC provider setup | Not required | Required |
| Cross-cluster reuse | Easy | Complex |
| Session tags | Supported | Not supported |
| Auditability | Better | Standard |

### Setup

```bash
# 1. Install Pod Identity Agent
aws eks create-addon --cluster-name my-cluster --addon-name eks-pod-identity-agent

# 2. Create IAM role
aws iam create-role --role-name my-app-role \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "pods.eks.amazonaws.com"},
      "Action": ["sts:AssumeRole", "sts:TagSession"]
    }]
  }'

# 3. Attach permissions
aws iam attach-role-policy --role-name my-app-role \
  --policy-arn arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess

# 4. Create association
aws eks create-pod-identity-association \
  --cluster-name my-cluster \
  --namespace backend-prod \
  --service-account my-app-sa \
  --role-arn arn:aws:iam::123456789012:role/my-app-role
```

### Kubernetes Config

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: my-app-sa
  namespace: backend-prod
  # No annotations needed for Pod Identity
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

## IRSA (Legacy — Use for EKS Anywhere / Cross-Account)

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

Benefits: 30-50% cost savings, seconds-scale scaling, automatic instance selection.

### NodePool

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
```

### EC2NodeClass

```yaml
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

### Workload Requesting Spot

```yaml
spec:
  affinity:
    nodeAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
        nodeSelectorTerms:
        - matchExpressions:
          - key: karpenter.sh/capacity-type
            operator: In
            values: ["spot"]
  tolerations:
  - key: "karpenter.sh/disruption"
    operator: "Exists"
```

### GPU NodePool

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
        values: ["on-demand"]         # Spot unreliable for GPU
      taints:
      - key: nvidia.com/gpu
        effect: NoSchedule
```

---

## VPC CNI Configuration

### Prefix Delegation

```bash
kubectl set env daemonset aws-node -n kube-system \
  ENABLE_PREFIX_DELEGATION=true \
  WARM_PREFIX_TARGET=1

# Pod density: m5.large ~29 → ~110 pods
```

### Security Groups for Pods

```bash
kubectl set env daemonset aws-node -n kube-system ENABLE_POD_ENI=true
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
    - sg-0123456789abcdef0
```

---

## ALB Ingress Controller

### Installation

```bash
helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
  -n kube-system \
  --set clusterName=my-cluster \
  --set serviceAccount.create=false \
  --set serviceAccount.name=aws-load-balancer-controller
```

---

## Cost Optimization

| Strategy | Savings | Commitment |
|----------|---------|------------|
| Spot instances | Up to 90% | None (interruptible) |
| Savings Plans | Up to 72% | 1-3 years |
| Graviton (ARM) | 20-40% | None |

### EKS Support Costs

| Support Type | Cost/Hour |
|-------------|-----------|
| Standard | $0.10 |
| Extended | $0.60 |

Keep clusters on standard support versions (current -2).

### Right-sizing

```bash
helm install goldilocks fairwinds-stable/goldilocks --namespace goldilocks
kubectl label ns backend-prod goldilocks.fairwinds.com/enabled=true
```

---

## Observability

### Container Insights

```bash
aws eks create-addon --cluster-name my-cluster --addon-name amazon-cloudwatch-observability
```

### OpenTelemetry Auto-Instrumentation

```yaml
metadata:
  annotations:
    instrumentation.opentelemetry.io/inject-python: "true"
spec:
  containers:
  - env:
    - name: OTEL_EXPORTER_OTLP_ENDPOINT
      value: "http://cloudwatch-agent.amazon-cloudwatch:4317"
```



---




## Upgrade Strategy






### Order



1. Control plane (managed by AWS)

2. Add-ons (VPC CNI, CoreDNS, kube-proxy, EBS CSI)

3. Node groups (rolling or blue-green)



### Pre-upgrade Checklist

- [ ] Review release notes for breaking changes

- [ ] Check deprecated APIs: `kubectl get --raw /metrics | grep apiserver_requested_deprecated_apis`
- [ ] Validate PDBs allow rolling updates
- [ ] Test in staging

- [ ] Schedule maintenance window

### Update Add-ons

```bash
aws eks describe-addon-versions --addon-name vpc-cni --kubernetes-version 1.29
aws eks update-addon --cluster-name my-cluster --addon-name vpc-cni --addon-version v1.15.0-eksbuild.2
```
