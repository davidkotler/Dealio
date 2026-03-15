# Dockerfile Patterns Reference

> Extended patterns for multi-stage builds, BuildKit features, and language-specific conventions.

---

## 1. Instruction Ordering Convention

Follow this canonical order for readability and cache efficiency:

```dockerfile
# syntax=docker/dockerfile:1
FROM <base-image> AS <stage-name>

LABEL org.opencontainers.image.title="myapp" \
      org.opencontainers.image.version="1.0.0" \
      org.opencontainers.image.source="https://github.com/org/repo"

ARG <build-time-variables>
ENV <runtime-variables>

WORKDIR /app

# System dependencies (changes rarely)
RUN apt-get update && apt-get install -y --no-install-recommends \
    <packages> \
    && rm -rf /var/lib/apt/lists/*

# Application dependencies (changes occasionally)
COPY package.json package-lock.json ./
RUN npm ci --omit=dev

# Application source (changes frequently)
COPY . .

# Build step
RUN npm run build

EXPOSE <port>

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:3000/health || exit 1

USER nonroot

ENTRYPOINT ["node"]
CMD ["dist/index.js"]
```

**Rationale**: Docker caches each instruction as a layer. When any layer changes, all subsequent layers are invalidated. By placing rarely-changing instructions first and frequently-changing instructions last, we maximize cache reuse.

---

## 2. Multi-Stage Build Patterns

### Pattern A: Two-Stage (Standard)

Separate build environment from runtime. The simplest and most common pattern.

```dockerfile
# syntax=docker/dockerfile:1
FROM node:22 AS builder
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:22-slim AS production
WORKDIR /app
RUN groupadd -r app && useradd --no-log-init -r -g app app
COPY --from=builder --chown=app:app /app/dist ./dist
COPY --from=builder --chown=app:app /app/node_modules ./node_modules
USER app
EXPOSE 3000
CMD ["node", "dist/index.js"]
```

### Pattern B: Three-Stage (Deps Separated)

Separate dependency stage from build stage for better cache granularity. Useful when build is slow but deps are stable.

```dockerfile
# syntax=docker/dockerfile:1
FROM node:22 AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN --mount=type=cache,target=/root/.npm npm ci

FROM node:22 AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

FROM node:22-slim AS production
WORKDIR /app
RUN groupadd -r app && useradd --no-log-init -r -g app app
COPY --from=builder --chown=app:app /app/dist ./dist
RUN npm ci --omit=dev
USER app
EXPOSE 3000
CMD ["node", "dist/index.js"]
```

### Pattern C: Parallel Stages (Multi-Component)

BuildKit automatically parallelizes independent stages. Use for monorepos or apps with separate frontend/backend builds.

```dockerfile
# syntax=docker/dockerfile:1
FROM node:22 AS frontend-deps
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

FROM python:3.13-slim AS backend-deps
WORKDIR /app
COPY backend/requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir -r requirements.txt

FROM node:22 AS frontend-build
WORKDIR /app
COPY --from=frontend-deps /app/node_modules ./node_modules
COPY frontend/ .
RUN npm run build

FROM python:3.13-slim AS production
WORKDIR /app
COPY --from=backend-deps /usr/local/lib/python3.13/site-packages \
     /usr/local/lib/python3.13/site-packages
COPY --from=frontend-build /app/dist ./static
COPY backend/ .
RUN groupadd -r app && useradd --no-log-init -r -g app app
USER app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## 3. Language-Specific Patterns

### Python

```dockerfile
# syntax=docker/dockerfile:1
FROM python:3.13-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir -r requirements.txt

FROM python:3.13-slim
LABEL org.opencontainers.image.title="my-python-app"
WORKDIR /app
RUN groupadd -r app && useradd --no-log-init -r -g app app
COPY --from=builder /usr/local/lib/python3.13/site-packages \
     /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --chown=app:app . .
USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Key decisions**:







- Use `python:3.13-slim` (not Alpine) — musl libc breaks many C extensions
- Copy `site-packages` and `bin` directories from builder — avoids reinstalling
- Use `urllib.request` for health check — no extra dependency required
- `--no-cache-dir` saves ~30% image size on pip packages

### Python with Poetry

```dockerfile
# syntax=docker/dockerfile:1
FROM python:3.13-slim AS builder
WORKDIR /app
ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1
RUN pip install poetry
COPY pyproject.toml poetry.lock ./
RUN --mount=type=cache,target=/root/.cache/pypoetry \
    poetry install --only=main --no-root

FROM python:3.13-slim
WORKDIR /app
RUN groupadd -r app && useradd --no-log-init -r -g app app
COPY --from=builder /app/.venv .venv
COPY --chown=app:app . .
ENV PATH="/app/.venv/bin:$PATH"
USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Python with uv

```dockerfile
# syntax=docker/dockerfile:1
FROM python:3.13-slim AS builder
WORKDIR /app
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project
COPY . .
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

FROM python:3.13-slim
WORKDIR /app
RUN groupadd -r app && useradd --no-log-init -r -g app app
COPY --from=builder /app/.venv .venv
COPY --chown=app:app . .
ENV PATH="/app/.venv/bin:$PATH"
USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Node.js

```dockerfile
# syntax=docker/dockerfile:1
FROM node:22-slim AS builder
WORKDIR /app
COPY package.json package-lock.json ./
RUN --mount=type=cache,target=/root/.npm npm ci
COPY . .
RUN npm run build

FROM node:22-slim
LABEL org.opencontainers.image.title="my-node-app"
WORKDIR /app
ENV NODE_ENV=production
RUN groupadd -r app && useradd --no-log-init -r -g app app
COPY --from=builder --chown=app:app /app/dist ./dist
COPY --from=builder --chown=app:app /app/node_modules ./node_modules
USER app
EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD node -e "fetch('http://localhost:3000/health').then(r => process.exit(r.ok ? 0 : 1))" || exit 1
CMD ["node", "dist/index.js"]
```

### Go

```dockerfile
# syntax=docker/dockerfile:1
FROM golang:1.23 AS builder
WORKDIR /src
COPY go.mod go.sum ./
RUN --mount=type=cache,target=/go/pkg/mod go mod download
COPY . .
RUN --mount=type=cache,target=/root/.cache/go-build \
    CGO_ENABLED=0 GOOS=linux go build -ldflags="-s -w" -o /bin/app ./cmd/app

FROM gcr.io/distroless/static:nonroot
LABEL org.opencontainers.image.title="my-go-app"
USER nonroot:nonroot

COPY --from=builder /bin/app /app

EXPOSE 8080

ENTRYPOINT ["/app"]

```



**Key decisions**:

- `CGO_ENABLED=0` produces a fully static binary — can run on `scratch` or `distroless/static`
- `-ldflags="-s -w"` strips debug info (~30% smaller binary)
- `distroless/static:nonroot` provides CA certs and `/etc/passwd` — needed for HTTPS and non-root

### Java (Spring Boot)

```dockerfile
# syntax=docker/dockerfile:1
FROM eclipse-temurin:21-jdk AS builder
WORKDIR /app
COPY pom.xml .
RUN --mount=type=cache,target=/root/.m2 mvn dependency:go-offline
COPY src ./src
RUN --mount=type=cache,target=/root/.m2 mvn clean package -DskipTests

FROM eclipse-temurin:21-jre-alpine
LABEL org.opencontainers.image.title="my-java-app"
WORKDIR /app
RUN addgroup -S spring && adduser -S spring -G spring
COPY --from=builder --chown=spring:spring /app/target/*.jar app.jar
USER spring
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s --start-period=60s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost:8080/actuator/health || exit 1
ENTRYPOINT ["java", "-jar", "app.jar"]
```

---

## 4. BuildKit Advanced Features

### Heredoc Syntax

Requires `# syntax=docker/dockerfile:1`. Eliminates backslash-escaped multi-line commands.

```dockerfile
RUN <<EOF
apt-get update
apt-get install -y --no-install-recommends curl git wget
rm -rf /var/lib/apt/lists/*
EOF
```

Also for inline file creation:

```dockerfile
COPY <<EOF /app/config.yaml
server:
  port: 8080
  host: 0.0.0.0
EOF
```

### Named Build Contexts

Allow `COPY` from multiple source directories:

```bash
docker buildx build \
  --build-context docs=./documentation \
  --build-context configs=./deploy/configs \
  -t myapp .
```

```dockerfile
COPY --from=docs README.md ./
COPY --from=configs production.yaml ./config.yaml
```

### Secret Mounts

For build-time credentials that must never persist in layers:

```dockerfile
RUN --mount=type=secret,id=npm_token \
    NPM_TOKEN=$(cat /run/secrets/npm_token) npm ci
```

```bash
docker build --secret id=npm_token,src=$HOME/.npmrc -t myapp .
# Or from environment variable:
docker build --secret id=npm_token,env=NPM_TOKEN -t myapp .
```

### SSH Mounts

For cloning private repositories:

```dockerfile
RUN --mount=type=ssh git clone git@github.com:org/private-repo.git
```

```bash
docker build --ssh default -t myapp .
```

### External Cache for CI/CD

```bash
# Registry-backed cache (best for teams)
docker buildx build \
    --cache-from type=registry,ref=myregistry/myapp:cache \
    --cache-to type=registry,ref=myregistry/myapp:cache,mode=max \
    -t myapp:latest --push .

# GitHub Actions cache
docker buildx build \
    --cache-from type=gha \
    --cache-to type=gha,mode=max \
    -t myapp:latest .
```

`mode=max` caches all intermediate layers including multi-stage build stages. `mode=min` (default) caches only final image layers.

---

## 5. .dockerignore Template

Every project must have a `.dockerignore`. This template covers most cases:

```gitignore
# Version control
.git
.gitignore

# Dependencies (installed inside container)
node_modules
.venv
__pycache__
*.pyc
*.pyo

# Build artifacts
dist
build
*.egg-info

# Environment and secrets
.env
.env.*
*.pem
*.key

# IDE and editor
.vscode
.idea
*.swp
*.swo
.DS_Store

# Tests and docs (not needed in production image)
tests/
test/
coverage/
htmlcov/
*.md
!README.md

# Docker files (prevent recursive context)
Dockerfile*
compose*.yaml
compose*.yml
docker-compose*.yml
.dockerignore
```

---

## 6. Multi-Platform Builds

For ARM-based cloud (AWS Graviton) and Apple Silicon:


```bash
# Create a builder with multi-platform support

docker buildx create --name multiplatform --use


# Build for multiple architectures
docker buildx build \

    --platform linux/amd64,linux/arm64 \
    --push \

    -t myregistry/myapp:1.0.0 .
```


Three strategies for multi-arch:

1. **QEMU emulation** (easiest, no Dockerfile changes, slow for heavy builds)
2. **Multiple native builder nodes** (fastest, requires arch-specific runners)
3. **Cross-compilation** using `TARGETOS`/`TARGETARCH` ARGs (best for Go, Rust)

```dockerfile
# Go cross-compilation pattern
ARG TARGETOS TARGETARCH
RUN CGO_ENABLED=0 GOOS=${TARGETOS} GOARCH=${TARGETARCH} go build -o /bin/app
```

---

## 7. OCI Labels

Always add metadata labels following the OCI annotation spec:

```dockerfile
LABEL org.opencontainers.image.title="my-service" \
      org.opencontainers.image.description="API service for order management" \
      org.opencontainers.image.version="1.2.3" \
      org.opencontainers.image.source="https://github.com/org/repo" \
      org.opencontainers.image.authors="team@example.com" \
      org.opencontainers.image.created="2025-01-15T10:00:00Z"
```

For dynamic values (version, commit SHA, build time), use build ARGs:

```dockerfile
ARG APP_VERSION=dev
ARG GIT_SHA=unknown
LABEL org.opencontainers.image.version="${APP_VERSION}" \
      org.opencontainers.image.revision="${GIT_SHA}"
```

```bash
docker build --build-arg APP_VERSION=1.2.3 --build-arg GIT_SHA=$(git rev-parse --short HEAD) .
```
