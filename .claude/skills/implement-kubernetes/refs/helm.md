# Helm Chart Reference

## Table of Contents







- Chart Structure
- Chart.yaml
- Values Design
- Template Best Practices
- Deployment Template
- Hooks
- Testing
- OCI Registry
- Environment Overrides

---

## Chart Structure

```
mychart/
├── Chart.yaml               # Chart metadata (required)
├── Chart.lock               # Dependency lock (generated)
├── values.yaml              # Default configuration
├── values.schema.json       # JSON Schema validation (recommended)
├── .helmignore
├── charts/                  # Dependencies
├── crds/                    # CRDs
├── templates/
│   ├── _helpers.tpl         # Template helpers
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── configmap.yaml
│   ├── secret.yaml
│   ├── ingress.yaml
│   ├── hpa.yaml
│   ├── pdb.yaml
│   ├── serviceaccount.yaml
│   ├── networkpolicy.yaml
│   ├── NOTES.txt            # Post-install instructions
│   └── tests/
│       └── test-connection.yaml
└── README.md
```

---

## Chart.yaml

```yaml
apiVersion: v2
name: my-api
description: A Helm chart for my-api microservice
type: application
version: 1.2.3              # Chart version (SemVer)
appVersion: "2.1.0"         # Application version
kubeVersion: ">=1.26.0"
keywords: [api, backend]
maintainers:
- name: Platform Team
  email: platform@company.com
dependencies:
- name: redis
  version: "17.x.x"
  repository: "https://charts.bitnami.com/bitnami"
  condition: redis.enabled
```

---

## Values Design

```yaml
replicaCount: 3

image:
  repository: myregistry.io/my-api
  tag: "2.1.0"                    # Pin version, never "latest"
  pullPolicy: IfNotPresent
  pullSecrets: []

serviceAccount:
  create: true
  name: ""                         # Auto-generated if empty
  annotations: {}

rbac:
  create: true

resources:
  requests:
    cpu: 250m
    memory: 256Mi
  limits:
    memory: 512Mi
    # cpu: omitted intentionally — avoid throttling

autoscaling:
  enabled: false
  minReplicas: 2
  maxReplicas: 10
  targetCPUUtilizationPercentage: 70

probes:
  liveness:
    enabled: true
    path: /health/live
    initialDelaySeconds: 30
    periodSeconds: 10
  readiness:
    enabled: true
    path: /health/ready
    initialDelaySeconds: 5
    periodSeconds: 5
  startup:
    enabled: true
    path: /health/startup
    failureThreshold: 30

securityContext:
  runAsNonRoot: true
  runAsUser: 1000
  readOnlyRootFilesystem: true

podSecurityContext:
  fsGroup: 2000

ingress:
  enabled: false
  className: ""
  annotations: {}
  hosts:
  - host: api.example.com
    paths:
    - path: /
      pathType: Prefix
  tls: []

env: []
envFrom: []
```

### Values Schema (values.schema.json)

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["image", "replicaCount"],
  "properties": {
    "replicaCount": {
      "type": "integer",
      "minimum": 1
    },
    "image": {
      "type": "object",
      "required": ["repository"],
      "properties": {
        "repository": { "type": "string" },
        "tag": {
          "type": "string",
          "pattern": "^[a-zA-Z0-9][a-zA-Z0-9._-]*$"
        },
        "pullPolicy": {
          "type": "string",
          "enum": ["Always", "Never", "IfNotPresent"]
        }
      }
    },
    "resources": {
      "type": "object",
      "properties": {
        "requests": {
          "type": "object",
          "required": ["memory"],
          "properties": {
            "cpu": { "type": "string" },
            "memory": { "type": "string" }
          }
        },
        "limits": {
          "type": "object",
          "required": ["memory"],
          "properties": {
            "memory": { "type": "string" }
          }
        }
      }
    }
  }
}
```

---

## Template Best Practices

### _helpers.tpl

```yaml
{{/*
Chart name, truncated to 63 chars
*/}}
{{- define "mychart.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Full name: release-chartname, truncated
*/}}
{{- define "mychart.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Standard labels
*/}}
{{- define "mychart.labels" -}}
helm.sh/chart: {{ include "mychart.chart" . }}
{{ include "mychart.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "mychart.selectorLabels" -}}
app.kubernetes.io/name: {{ include "mychart.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Service account name
*/}}
{{- define "mychart.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "mychart.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}
```

### Key Rules

Use `include` over `template` (pipeable):
```yaml
labels:
  {{- include "mychart.labels" . | nindent 4 }}
```

Use `required` for mandatory values:
```yaml
image: {{ required "image.repository is required" .Values.image.repository }}
```

Always quote string values:
```yaml
value: {{ .Values.logLevel | quote }}
```

---

## Deployment Template

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ include "mychart.fullname" . }}
  labels:
    {{- include "mychart.labels" . | nindent 4 }}
spec:
  {{- if not .Values.autoscaling.enabled }}
  replicas: {{ .Values.replicaCount }}
  {{- end }}
  selector:
    matchLabels:
      {{- include "mychart.selectorLabels" . | nindent 6 }}
  template:
    metadata:
      annotations:
        checksum/config: {{ include (print $.Template.BasePath "/configmap.yaml") . | sha256sum }}
        {{- with .Values.podAnnotations }}
        {{- toYaml . | nindent 8 }}
        {{- end }}
      labels:
        {{- include "mychart.selectorLabels" . | nindent 8 }}
    spec:
      {{- with .Values.imagePullSecrets }}
      imagePullSecrets:
        {{- toYaml . | nindent 8 }}
      {{- end }}
      serviceAccountName: {{ include "mychart.serviceAccountName" . }}
      securityContext:
        {{- toYaml .Values.podSecurityContext | nindent 8 }}
      containers:
      - name: {{ .Chart.Name }}
        securityContext:
          {{- toYaml .Values.securityContext | nindent 12 }}
        image: "{{ .Values.image.repository }}:{{ .Values.image.tag | default .Chart.AppVersion }}"
        imagePullPolicy: {{ .Values.image.pullPolicy }}
        ports:
        - name: http
          containerPort: {{ .Values.service.port }}
          protocol: TCP
        {{- if .Values.probes.liveness.enabled }}
        livenessProbe:
          httpGet:
            path: {{ .Values.probes.liveness.path }}
            port: http
          initialDelaySeconds: {{ .Values.probes.liveness.initialDelaySeconds }}
          periodSeconds: {{ .Values.probes.liveness.periodSeconds }}
        {{- end }}
        {{- if .Values.probes.readiness.enabled }}
        readinessProbe:
          httpGet:
            path: {{ .Values.probes.readiness.path }}
            port: http
          initialDelaySeconds: {{ .Values.probes.readiness.initialDelaySeconds }}
          periodSeconds: {{ .Values.probes.readiness.periodSeconds }}
        {{- end }}
        {{- if .Values.probes.startup.enabled }}
        startupProbe:
          httpGet:
            path: {{ .Values.probes.startup.path }}
            port: http
          failureThreshold: {{ .Values.probes.startup.failureThreshold }}
          periodSeconds: 5
        {{- end }}
        resources:
          {{- toYaml .Values.resources | nindent 12 }}
        {{- with .Values.env }}
        env:
          {{- toYaml . | nindent 12 }}
        {{- end }}
        {{- with .Values.envFrom }}
        envFrom:
          {{- toYaml . | nindent 12 }}
        {{- end }}
        volumeMounts:
        - name: tmp
          mountPath: /tmp
      volumes:
      - name: tmp
        emptyDir: {}
      {{- with .Values.nodeSelector }}
      nodeSelector:
        {{- toYaml . | nindent 8 }}
      {{- end }}
      {{- with .Values.affinity }}
      affinity:
        {{- toYaml . | nindent 8 }}
      {{- end }}
      {{- with .Values.tolerations }}
      tolerations:
        {{- toYaml . | nindent 8 }}
      {{- end }}
```

---

## Hooks

### Pre-upgrade Database Migration

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: {{ include "mychart.fullname" . }}-migrate
  annotations:
    "helm.sh/hook": pre-upgrade,pre-install
    "helm.sh/hook-weight": "-5"
    "helm.sh/hook-delete-policy": before-hook-creation,hook-succeeded
spec:
  ttlSecondsAfterFinished: 600
  template:
    spec:
      restartPolicy: Never
      containers:
      - name: migrate
        image: "{{ .Values.image.repository }}:{{ .Values.image.tag }}"
        command: ["python", "manage.py", "migrate"]
        envFrom:
        - secretRef:
            name: {{ include "mychart.fullname" . }}-secrets
```

---

## Testing

### Connection Test

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: "{{ include "mychart.fullname" . }}-test-connection"
  annotations:
    "helm.sh/hook": test
spec:
  containers:
  - name: wget
    image: busybox
    command: ['wget']
    args: ['{{ include "mychart.fullname" . }}:{{ .Values.service.port }}{{ .Values.probes.readiness.path }}']
  restartPolicy: Never
```

```bash
helm test my-release --logs
```

---

## OCI Registry Distribution

```bash
helm package mychart/
helm push mychart-1.2.3.tgz oci://myregistry.io/charts
helm install myrelease oci://myregistry.io/charts/mychart --version 1.2.3
```



---



## Environment Overrides



### values-staging.yaml

```yaml

replicaCount: 2
resources:

  requests:
    cpu: 100m

    memory: 128Mi
  limits:

    memory: 256Mi
autoscaling:

  enabled: false
```



### values-production.yaml


```yaml
replicaCount: 3
resources:

  requests:
    cpu: 500m
    memory: 512Mi

  limits:
    memory: 1Gi
autoscaling:

  enabled: true
  minReplicas: 3
  maxReplicas: 20

```

### Install

```bash
helm install myrelease ./mychart -f values-production.yaml --set image.tag=v2.1.1
```
