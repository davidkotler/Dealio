---
name: implement-docker
version: 1.0.0
description: |
  Implement production-ready Dockerfiles, Docker Compose services, .dockerignore files,
  and container build pipelines with multi-stage builds, BuildKit optimizations, and
  security hardening. Use when creating Dockerfiles, writing compose.yaml services,
  containerizing applications, optimizing Docker image size or build speed, reviewing
  Docker configurations, adding health checks, configuring container networking or secrets,
  or setting up CI/CD container builds. Also triggers when editing existing Dockerfiles,
  fixing build failures, migrating from Compose V1 to V2, or hardening container security.
  Relevant for Docker, BuildKit, Compose V2, container security, multi-stage builds,
  .dockerignore, image optimization, OCI images, supply chain security.
---

# Docker Implementation

> Produce minimal, secure, cache-optimized container images and Compose services that are production-ready from the first build.

## Quick Reference

| Aspect | Details |
|--------|---------|
| **Invokes** | `implement/python`, `implement/kubernetes`, `observe/logs` |
| **Invoked By** | `implement/python`, `implement/api`, `implement/react`, `design/kubernetes` |
| **Key Tools** | Write, Edit, Bash(docker build), Bash(hadolint) |

---

## Core Workflow

1. **Detect**: Identify target language/framework and existing Docker artifacts
2. **Scaffold**: Generate `.dockerignore` first, then Dockerfile, then `compose.yaml`
3. **Layer**: Order instructions for maximum cache efficiency — deps before source
4. **Harden**: Non-root user, minimal base image, no secrets in layers
5. **Validate**: Run `hadolint` on Dockerfile; verify build completes
6. **Chain**: Invoke `implement/kubernetes` when K8s manifests are needed

---

## Decision Tree

```
User Request
    │
    ├─► New application containerization?
    │     ├─► Detect language/framework
    │     ├─► Generate .dockerignore
    │     ├─► Generate multi-stage Dockerfile
    │     └─► Generate compose.yaml (if multi-service)
    │
    ├─► Optimize existing Dockerfile?
    │     ├─► Audit layer ordering (deps before source?)
    │     ├─► Add BuildKit cache mounts
    │     ├─► Switch to slim/distroless base
    │     └─► Verify .dockerignore completeness
    │
    ├─► Docker Compose work?
    │     ├─► Use compose.yaml (no version field)
    │     ├─► Add health checks + depends_on conditions
    │     ├─► Configure networks, secrets, resource limits
    │     └─► Add develop.watch for dev workflow
    │
    ├─► Security hardening?
    │     ├─► Non-root USER before ENTRYPOINT
    │     ├─► cap_drop ALL, read_only true
    │     ├─► BuildKit --mount=type=secret for build secrets
    │     └─► See refs/security.md
    │
    └─► Review existing Docker config?
          ├─► Run Quality Gates checklist (below)
          └─► Flag anti-patterns (see Patterns section)
```

---

## Mandatory Standards

### Every Dockerfile MUST

1. Start with `# syntax=docker/dockerfile:1`
2. Use multi-stage builds — separate builder from runtime
3. Pin base image to `major.minor` tag (never `:latest`)
4. Order layers: system deps → lockfiles → install deps → source → build
5. Use `COPY` (never `ADD` unless tar extraction required)
6. Run as non-root `USER` before `ENTRYPOINT`/`CMD`
7. Use exec form for `ENTRYPOINT`/`CMD`: `["binary", "arg"]`
8. Include `HEALTHCHECK` instruction
9. Add OCI labels: `org.opencontainers.image.{title,version,source}`
10. Clean caches in same `RUN` layer: `rm -rf /var/lib/apt/lists/*`

### Every compose.yaml MUST

1. Omit the `version:` field entirely
2. Use `compose.yaml` filename (not `docker-compose.yml`)
3. Define `healthcheck` for every service
4. Use `depends_on` with `condition: service_healthy`
5. Set `deploy.resources.limits` (CPU + memory)
6. Configure log rotation: `max-size: "10m"`, `max-file: "3"`
7. Use named custom bridge networks (never default bridge)
8. Mark database networks `internal: true`
9. Inject secrets via `secrets:` or env files (never hardcoded)
10. Set `restart: unless-stopped` for production services

### Base Image Selection

| Language | Builder Stage | Runtime Stage |
|----------|--------------|---------------|
| Python | `python:3.13` | `python:3.13-slim` |
| Node.js | `node:22` | `node:22-slim` |
| Go | `golang:1.23` | `gcr.io/distroless/static:nonroot` or `scratch` |
| Java | `eclipse-temurin:21-jdk` | `eclipse-temurin:21-jre-alpine` |
| Rust | `rust:1.80` | `gcr.io/distroless/cc:nonroot` or `scratch` |

### BuildKit Cache Mounts (always use)

```dockerfile
# Python
RUN --mount=type=cache,target=/root/.cache/pip pip install -r requirements.txt

# Node.js
RUN --mount=type=cache,target=/root/.npm npm ci

# Go
RUN --mount=type=cache,target=/go/pkg/mod \
    --mount=type=cache,target=/root/.cache/go-build \
    go build -o /bin/app ./cmd/app

# APT (use sharing=locked)
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends curl
```

---

## Skill Chaining

| Condition | Invoke | Handoff Context |
|-----------|--------|-----------------|
| K8s deployment needed | `implement/kubernetes` | Image name, ports, env vars, health endpoint |
| Python app containerization | `implement/python` | Runtime version, dependency manager |
| Observability instrumentation | `observe/logs` | Log format (JSON to stdout) |
| Security deep review | `review/docker` | Dockerfile + compose.yaml paths |

---

## Patterns & Anti-Patterns

### ✅ Do

- Separate dependency install from source copy for cache efficiency
- Use `--no-install-recommends` with apt-get
- Use `--mount=type=secret` for build-time credentials
- Use `docker compose watch` with `sync` + `rebuild` actions for dev
- Pin package versions in lockfiles (`npm ci`, `pip install -r`)
- Use `.dockerignore` in every project excluding `.git`, `node_modules`, `__pycache__`, `.env`

### ❌ Don't

- Use `:latest` tag on base images or published images
- Put secrets in `ARG`, `ENV`, or `COPY` instructions
- Use shell form for `ENTRYPOINT`/`CMD` (breaks signal handling)
- Run containers as root
- Use `docker-compose` (V1, deprecated) — use `docker compose` (V2)
- Include `version:` field in compose files
- Include `VOLUME` in application Dockerfiles (manage at runtime)
- Use `ADD` when `COPY` suffices
- Expose database ports to the host in production

---

## Example: Python FastAPI Containerization

**Input:** "Containerize my FastAPI app"

**Dockerfile:**
```dockerfile
# syntax=docker/dockerfile:1
FROM python:3.13-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir -r requirements.txt

FROM python:3.13-slim
LABEL org.opencontainers.image.title="my-api"
WORKDIR /app
RUN groupadd -r app && useradd --no-log-init -r -g app app
COPY --from=builder /usr/local/lib/python3.13/site-packages \
     /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --chown=app:app . .
USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## Deep References

For detailed guidance, load these refs as needed:

- **[dockerfile-patterns.md](refs/dockerfile-patterns.md)**: Multi-stage patterns per language, BuildKit features, layer optimization
- **[compose-patterns.md](refs/compose-patterns.md)**: Compose V2 conventions, networking, development workflow, profiles
- **[security.md](refs/security.md)**: Non-root hardening, capability dropping, secrets management, scanning, signing
- **[troubleshooting.md](refs/troubleshooting.md)**: Common build failures, cache misses, Alpine pitfalls, signal handling

---

## Quality Gates

Before completing any Docker implementation task:

- [ ] `# syntax=docker/dockerfile:1` present at line 1
- [ ] Multi-stage build separates builder from runtime
- [ ] Base images pinned to specific version (no `:latest`)
- [ ] Layer order: system deps → lockfiles → dep install → source → build
- [ ] Non-root `USER` set before `ENTRYPOINT`/`CMD`
- [ ] Exec form used for `ENTRYPOINT` and `CMD`
- [ ] `HEALTHCHECK` instruction defined
- [ ] `.dockerignore` present and excludes `.git`, `node_modules`, `.env`, `__pycache__`
- [ ] No secrets in `ARG`, `ENV`, or `COPY` layers
- [ ] Compose: no `version:` field, health-aware `depends_on`, resource limits set
- [ ] `hadolint` produces no errors (warnings acceptable with justification)
