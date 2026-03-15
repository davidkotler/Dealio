# Docker Security Reference

> Non-root hardening, capability management, secrets, scanning, image signing, and CIS Benchmark controls.

---

## 1. Non-Root User (Critical)

By default, containers run as root. According to the Sysdig 2024 report, 58% of production containers still run as root — a major privilege escalation risk.

### Debian/Ubuntu-Based Images

```dockerfile
RUN groupadd -r appuser && useradd --no-log-init -r -g appuser appuser
COPY --chown=appuser:appuser . .
USER appuser
```

### Alpine-Based Images

```dockerfile
RUN addgroup -S appuser && adduser -S appuser -G appuser
USER appuser
```

### Distroless Images

Use the `:nonroot` tag variant (UID 65532):

```dockerfile
FROM gcr.io/distroless/static:nonroot
USER nonroot:nonroot
```

### Important Notes

- Place `USER` instruction after all `RUN` commands that require root (package installs, directory creation)
- Place `USER` before `ENTRYPOINT`/`CMD`
- Use named users, not hardcoded UID 1000 — platforms like OpenShift run containers with random UIDs
- Use `--chown` flag on `COPY` to set ownership without extra `RUN chown` layers

---

## 2. Capability Management

Containers receive a default set of Linux capabilities that are often more than needed.

### Compose Configuration

```yaml
services:
  api:
    cap_drop:
      - ALL
    cap_add:
      - NET_BIND_SERVICE     # Only if binding to ports < 1024
    security_opt:
      - no-new-privileges:true
```

### Docker Run

```bash
docker run --cap-drop ALL --cap-add NET_BIND_SERVICE --security-opt no-new-privileges myapp
```

### Common Capabilities

| Capability | Purpose | When Needed |
|------------|---------|-------------|
| `NET_BIND_SERVICE` | Bind to ports below 1024 | Web servers on port 80/443 |
| `CHOWN` | Change file ownership | Almost never at runtime |
| `SYS_PTRACE` | Debugging processes | Only in development |
| `NET_RAW` | Raw sockets | Only for network diagnostics |

**Default**: Drop ALL, then add back only what's strictly required.

---

## 3. Read-Only Filesystem

Prevent runtime filesystem modifications to limit attacker capability:

```yaml
services:
  api:
    read_only: true
    tmpfs:
      - /tmp
      - /var/run
      - /var/cache
```

Applications that write temporary files, PID files, or cache data need `tmpfs` mounts for those specific directories.

---

## 4. Secrets Management

### Build-Time Secrets (BuildKit)

Secrets are mounted as temporary filesystems during specific `RUN` instructions and never persist in image layers.

```dockerfile
# syntax=docker/dockerfile:1

# From file
RUN --mount=type=secret,id=npmrc,target=/root/.npmrc npm ci

# Reading secret value
RUN --mount=type=secret,id=github_token \
    GITHUB_TOKEN=$(cat /run/secrets/github_token) \
    git clone https://${GITHUB_TOKEN}@github.com/org/repo.git
```

```bash
# From file
docker build --secret id=npmrc,src=~/.npmrc .

# From environment variable
docker build --secret id=github_token,env=GITHUB_TOKEN .
```

### SSH Agent Forwarding

For cloning private repositories during build:

```dockerfile
RUN --mount=type=ssh git clone git@github.com:org/private-repo.git
```

```bash
docker build --ssh default -t myapp .
```

### Runtime Secrets (Compose)

```yaml
services:
  api:
    secrets:
      - db_password
    environment:
      DB_PASSWORD_FILE: /run/secrets/db_password

secrets:
  db_password:
    file: ./secrets/db_password.txt
```

### What NEVER to Do

| Anti-Pattern | Why It's Dangerous |
|---|---|
| `ENV API_KEY=secret` | Visible in `docker inspect` and `docker history` |
| `ARG DB_PASSWORD=secret` | Visible in `docker history` and build logs |
| `COPY .env /app/.env` | Persists in image layer — even `RUN rm` doesn't remove from previous layers |
| `--build-arg SECRET=value` with `mode=max` provenance | Build arg values included in attestation metadata |

### Runtime Secrets for Production

- **Docker Swarm Secrets**: Built-in, encrypted at rest and in transit
- **HashiCorp Vault**: Industry standard for secret lifecycle management
- **AWS Secrets Manager / Azure Key Vault / GCP Secret Manager**: Cloud-native
- **Kubernetes Secrets**: Base64-encoded (consider etcd encryption or ExternalSecrets operator)

---

## 5. Vulnerability Scanning

### Tools

| Tool | Type | Best For |
|------|------|----------|
| **Trivy** (Aqua Security) | Open-source | Best all-around: images, IaC, secrets, SBOMs |
| **Docker Scout** | Built-in (Docker CLI) | Local dev, layer-by-layer analysis, base image recommendations |
| **Snyk Container** | Commercial ($45/dev/mo) | Best remediation advice, continuous monitoring |
| **Grype** (Anchore) | Open-source | Clean vulnerability output, `grype explain` deep-dive |

### CI/CD Integration

```bash
# Trivy — scan and fail on high/critical
trivy image myapp:latest --severity HIGH,CRITICAL --exit-code 1

# Docker Scout — built into Docker CLI
docker scout cves myapp:latest

# Grype — focused vulnerability output
grype myapp:latest --fail-on critical
```

### Defense-in-Depth Strategy

Run **Trivy in CI/CD pipelines** (automated gate) and **Docker Scout during local development** (fast feedback). Configure CI to fail on CRITICAL severity at minimum.

### GitHub Actions Integration

```yaml
- uses: aquasecurity/trivy-action@master
  with:
    image-ref: myapp:${{ github.sha }}
    format: sarif
    output: trivy-results.sarif
    severity: HIGH,CRITICAL
    exit-code: 1
```

---

## 6. Dockerfile Linting

**hadolint** catches bad practices statically:

```bash
hadolint Dockerfile
```

### Key Hadolint Rules

| Rule | What It Catches |
|------|-----------------|
| DL3006 | Missing version pin on base image |
| DL3007 | Using `:latest` tag |
| DL3008 | Not pinning apt package versions |
| DL3009 | Not deleting apt lists after install |
| DL3013 | Not pinning pip package versions |
| DL3018 | Not pinning apk package versions |
| DL3025 | Using shell form CMD instead of exec form |
| DL3045 | Using `ADD` instead of `COPY` |
| DL4006 | Not using shell pipefail |

### CI Integration

```yaml
# GitHub Actions
- uses: hadolint/hadolint-action@v3.1.0
  with:
    dockerfile: Dockerfile
    failure-threshold: error
```

---

## 7. Image Signing and Supply Chain

### Cosign (Sigstore) — Current Standard

Docker Content Trust (Notary) has been officially retired in favor of Cosign.

```bash
# Key-based signing
cosign sign --key cosign.key myregistry/myapp@sha256:abc123...

# Keyless signing (OIDC — GitHub, Google identity)
cosign sign myregistry/myapp@sha256:abc123...

# Verify
cosign verify --key cosign.pub myregistry/myapp@sha256:abc123...
```

**Always sign by digest, never by tag** — tags are mutable.

### SBOM and Provenance Attestations

```bash
docker buildx build \
    --sbom=true \
    --provenance=mode=max \
    --push \
    -t myregistry/myapp:1.0.0 .
```

These generate SLSA-compatible attestations and SBOMs at build time. Note that `mode=max` provenance includes build argument values — never pass secrets via `--build-arg`.

---

## 8. CIS Docker Benchmark Controls

Key mandates from CIS Docker Benchmark v1.7–1.8:

### Host Level









- Separate `/var/lib/docker` partition

- Audit Docker daemon files


- Never use `--insecure-registry`





### Container Level


- Drop ALL capabilities, add back only needed
- Enable `--no-new-privileges`

- Use `--read-only` filesystem with tmpfs for writable dirs
- Remove setuid/setgid binaries


### Image Level

- No secrets in images
- Use multi-stage builds
- Minimal base images
- Vulnerability scanning in CI

### Audit Tool

```bash
docker run --rm -it \
    --pid host --net host \
    -v /var/run/docker.sock:/var/run/docker.sock \
    docker/docker-bench-security
```

---

## 9. Network Security

```yaml
networks:
  frontend:
    driver: bridge
  backend:
    internal: true    # Blocks all external/internet access
```

- **Never expose database ports** to the host in production
- Bind non-public services to localhost: `127.0.0.1:8080:80`
- Use `internal: true` for networks containing databases and caches
- Disable inter-container communication (ICC) when not needed: `--icc=false`

---

## 10. Security Profiles

### Seccomp

Docker applies a default seccomp profile blocking ~44 dangerous syscalls. Keep it enabled.

### AppArmor

Restricts what actions a container process can perform (file access, network, capabilities).

### No Privileged Mode

Never use `--privileged` or `privileged: true`. The only legitimate use case is Docker-in-Docker (which should itself be avoided in favor of alternatives like kaniko or buildx remote builders).

---

## 11. Minimal Attack Surface Checklist

- [ ] Multi-stage build — no compilers, build tools, or dev deps in runtime
- [ ] Slim or distroless base image
- [ ] No shell, curl, wget unless strictly needed at runtime
- [ ] No SUID/SGID binaries: `RUN find / -perm /6000 -type f -exec chmod a-s {} \; || true`
- [ ] Non-root USER
- [ ] Read-only root filesystem
- [ ] All capabilities dropped
- [ ] Resource limits set
- [ ] No secrets in any layer
- [ ] Scanned for vulnerabilities in CI
