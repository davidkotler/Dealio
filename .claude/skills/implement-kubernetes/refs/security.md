# Security Reference

## Table of Contents







- Pod Security Standards (PSS)
- RBAC Patterns
- Network Policies
- Secrets Management
- Policy Engines (Kyverno)
- Image Security
- Compliance Mapping

---

## Pod Security Standards (PSS)

### Level Selection

| Level | Use Case | Key Restrictions |
|-------|----------|------------------|
| restricted | Production apps (default) | runAsNonRoot, no escalation, drop ALL |
| baseline | Legacy apps needing adjustments | Allows host namespaces, some capabilities |
| privileged | System components only | No restrictions |

### Enable PSS on Namespace

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: backend-prod
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/enforce-version: latest
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/warn: restricted
```

### Restricted Pod Template

```yaml
spec:
  securityContext:
    runAsNonRoot: true
    runAsUser: 1000
    runAsGroup: 3000
    fsGroup: 2000
    seccompProfile:
      type: RuntimeDefault
  containers:
  - name: app
    securityContext:
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
      capabilities:
        drop: ["ALL"]
    volumeMounts:
    - name: tmp
      mountPath: /tmp
    - name: cache
      mountPath: /app/.cache
  volumes:
  - name: tmp
    emptyDir: {}
  - name: cache
    emptyDir: {}
```

### Common PSS Errors and Fixes

| Error | Cause | Fix |
|-------|-------|-----|
| "must run as non-root" | Image runs as root | Add USER in Dockerfile or set runAsUser |
| "read-only root filesystem" | App writes to / | Mount emptyDir for writable paths |
| "privilege escalation" | Missing security context | Add allowPrivilegeEscalation: false |

---

## RBAC Patterns

### Namespace Role (Preferred — Least Privilege)

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  namespace: backend-prod
  name: api-role
rules:
- apiGroups: [""]
  resources: ["configmaps", "secrets"]
  resourceNames: ["api-config", "api-secrets"]   # Specific resources only
  verbs: ["get"]
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["get", "list", "watch"]                 # Read-only
```

### RoleBinding

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: api-role-binding
  namespace: backend-prod
subjects:
- kind: ServiceAccount
  name: api-sa
  namespace: backend-prod
roleRef:
  kind: Role
  name: api-role
  apiGroup: rbac.authorization.k8s.io
```

### Service Account

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: api-sa
  namespace: backend-prod
automountServiceAccountToken: false    # Disable unless needed
```

### RBAC Anti-Patterns

```yaml
# ❌ God mode — never grant
rules:
- apiGroups: ["*"]
  resources: ["*"]
  verbs: ["*"]

# ❌ Wildcard verbs on secrets
rules:
- apiGroups: [""]
  resources: ["secrets"]
  verbs: ["*"]

# ✅ Specific permissions
rules:
- apiGroups: [""]

  resources: ["secrets"]

  resourceNames: ["my-specific-secret"]

  verbs: ["get"]

```



**Rules:**

- Use namespace Role over ClusterRole whenever possible
- Always specify `resourceNames` when accessing secrets/configmaps
- Set `automountServiceAccountToken: false` by default

---

## Network Policies

### Default Deny (Required for Every Namespace)

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
  namespace: backend-prod
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
```

### Allow Specific Traffic

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-api-traffic
  namespace: backend-prod
spec:
  podSelector:
    matchLabels:
      app: api
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: istio-system
    - podSelector:
        matchLabels:
          app: frontend
    ports:
    - protocol: TCP
      port: 8080
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: postgres
    ports:
    - protocol: TCP
      port: 5432
  - to:                                # Always allow DNS
    - namespaceSelector: {}
      podSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - protocol: UDP
      port: 53
```

### Block Instance Metadata (EKS — Prevent SSRF)

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: block-metadata
spec:

  podSelector: {}
  policyTypes:

  - Egress
  egress:

  - to:
    - ipBlock:

        cidr: 0.0.0.0/0
        except:

        - 169.254.169.254/32
```


**Rules:**

- Always include DNS egress in allow policies
- Block IMDS (169.254.169.254) on EKS unless Pod Identity is used
- Apply default-deny before any allow policies

---

## Secrets Management

### External Secrets Operator (Production Recommended)

**SecretStore:**
```yaml
apiVersion: external-secrets.io/v1beta1
kind: SecretStore
metadata:
  name: aws-secrets
  namespace: backend-prod
spec:
  provider:
    aws:
      service: SecretsManager
      region: us-east-1
      auth:
        jwt:
          serviceAccountRef:
            name: external-secrets-sa
```

**ExternalSecret:**
```yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: api-secrets
  namespace: backend-prod
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: aws-secrets
    kind: SecretStore
  target:
    name: api-secrets
    creationPolicy: Owner
  data:
  - secretKey: DATABASE_URL
    remoteRef:
      key: prod/api/database
      property: connection_string
  - secretKey: API_KEY
    remoteRef:
      key: prod/api/keys
      property: api_key
```

### Sealed Secrets (GitOps-Friendly)

```bash
kubeseal --format yaml < secret.yaml > sealed-secret.yaml
```

```yaml
apiVersion: bitnami.com/v1alpha1
kind: SealedSecret
metadata:
  name: api-secrets
  namespace: backend-prod
spec:
  encryptedData:
    DATABASE_URL: AgBy3i4...
```

---

## Policy Engines (Kyverno)

### Require Labels

```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: require-labels
spec:
  validationFailureAction: Enforce
  rules:
  - name: check-labels
    match:
      any:
      - resources:
          kinds: [Pod]
    validate:
      message: "Labels 'app' and 'team' are required"
      pattern:
        metadata:
          labels:
            app: "?*"
            team: "?*"
```

### Require Resource Limits

```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: require-limits
spec:
  validationFailureAction: Enforce
  rules:
  - name: check-limits
    match:
      any:
      - resources:
          kinds: [Pod]
    validate:
      message: "Memory limits are required"
      pattern:
        spec:
          containers:
          - resources:
              limits:
                memory: "?*"
```

### Mutate: Add Default Security Context

```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: add-security-context
spec:
  rules:
  - name: add-run-as-non-root
    match:
      any:
      - resources:
          kinds: [Pod]
    mutate:
      patchStrategicMerge:
        spec:
          securityContext:
            runAsNonRoot: true
            seccompProfile:
              type: RuntimeDefault
```

### Block Latest Tag

```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: disallow-latest
spec:
  validationFailureAction: Enforce
  rules:
  - name: validate-tag
    match:
      any:
      - resources:
          kinds: [Pod]
    validate:
      message: "Using 'latest' tag is not allowed"
      pattern:
        spec:
          containers:
          - image: "!*:latest"
```

### Require Signed Images

```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: verify-images
spec:
  validationFailureAction: Enforce
  rules:
  - name: verify-signature
    match:
      any:
      - resources:
          kinds: [Pod]
    verifyImages:
    - imageReferences: ["myregistry.io/*"]
      attestors:
      - entries:
        - keys:
            publicKeys: |
              -----BEGIN PUBLIC KEY-----
              ...
              -----END PUBLIC KEY-----
```

---

## Compliance Mapping

### SOC 2

| Control | K8s Implementation |
|---------|-------------------|
| Access Control | RBAC, ServiceAccounts |
| Network Security | NetworkPolicies, PSS |
| Audit Logging | API audit logs, Falco |
| Encryption | TLS, etcd encryption, secrets |

### HIPAA

| Requirement | Implementation |
|-------------|---------------|
| Access Controls | RBAC + audit logging |
| Encryption in Transit | mTLS (service mesh) |
| Encryption at Rest | StorageClass encryption |
| Audit Trail | API server audit logs |

### PCI-DSS

| Requirement | Implementation |
|-------------|---------------|
| Network Segmentation | NetworkPolicies, namespaces |
| Secure Configuration | PSS restricted, Kyverno |
| Vulnerability Management | Trivy scanning, signed images |
| Access Control | RBAC, Pod Identity |
