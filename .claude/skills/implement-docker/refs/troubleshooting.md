# Docker Troubleshooting Reference

> Common build failures, cache misses, Alpine pitfalls, signal handling, and runtime issues.

---

## 1. Build Failures

### "Could not resolve host" During Build

**Cause**: DNS resolution failure inside builder, often with VPN or corporate proxies.

**Fix**:
```bash
# Set DNS explicitly
docker build --network=host -t myapp .

# Or in daemon.json
{
  "dns": ["8.8.8.8", "8.8.4.4"]
}
```

### Cache Mount Not Working

**Cause**: Missing `# syntax=docker/dockerfile:1` directive.

**Fix**: Add as the very first line of the Dockerfile:
```dockerfile
# syntax=docker/dockerfile:1
```

### "failed to solve: process ... did not complete successfully"

**Cause**: A `RUN` command returned non-zero exit code.

**Debug**:
```bash
# Build with progress output
docker build --progress=plain -t myapp .

# Target a specific stage for debugging
docker build --target=builder -t myapp:debug .
docker run -it myapp:debug /bin/sh
```

### COPY Fails — "file not found"

**Cause**: File is excluded by `.dockerignore` or the build context doesn't include it.

**Fix**: Check `.dockerignore` for overly broad patterns. Verify file exists in build context:
```bash
# See what Docker receives as build context
docker build --progress=plain . 2>&1 | head -5
```

---

## 2. Cache Invalidation Issues

### Cache Busts on Every Build Despite No Changes

**Common causes**:




****
****
****
1. `COPY . .` placed before dependency install****
2. `.dockerignore` missing — timestamps on `.git` or IDE f**es chan**
3. Build ARG values changing between builds****
4. Build context includes generated files (dist/, build/, **pycache**/)

**Fix**: Ensure layer ordering follows the pattern:
```dockerfile
COPY package.json package-lock.json ./    # Deps manifest only
RUN npm ci                                 # Install (cached if lockfile unchanged)
COPY . .                                   # Source code (changes most)
```

### Cache Mounts Ignored in CI

**Cause**: CI environments start clean — no local cache exists.

**Fix**: Use external cache backends:
```bash
# GitHub Actions
docker buildx build \
    --cache-from type=gha \
    --cache-to type=gha,mode=max \
    -t myapp .

# Registry cache
docker buildx build \
    --cache-from type=registry,ref=myregistry/myapp:cache \
    --cache-to type=registry,ref=myregistry/myapp:cache,mode=max \
    -t myapp .
```

---

## 3. Alpine Linux Pitfalls

### Python C Extension Compilation Fails

**Symptom**: `pip install` fails with gcc/compilation errors on Alpine.

**Cause**: Alpine uses musl libc instead of glibc. Many Python packages with C extensions (numpy, pandas, cryptography, Pillow) expect glibc.

**Fix**: Use `python:3.13-slim` (Debian-based) instead of Alpine:
```dockerfile
# ❌ Fragile with C extensions
FROM python:3.13-alpine

# ✅ Works reliably
FROM python:3.13-slim
```

### DNS Resolution Issues in Kubernetes

**Symptom**: Intermittent DNS failures with Alpine-based images on Kubernetes.

**Cause**: musl libc's DNS resolver handles DNS-over-TCP differently than glibc, causing issues with some Kubernetes DNS configurations.

**Fix**: Use Debian-slim base images, or for minimal images use distroless or Chainguard.

### Node.js Native Module Failures

**Symptom**: `npm install` succeeds but native modules crash at runtime.

**Cause**: Native modules compiled against musl may behave differently than glibc.

**Fix**: Use `node:22-slim` instead of `node:22-alpine`.

---

## 4. Signal Handling Problems



### Container Takes 10 Seconds to Stop



**Symptom**: `docker stop` hangs for exactly 10 seconds then kills the container.



**Cause**: The application is not receiving SIGTERM because:

1. Shell form `CMD`/`ENTRYPOINT` wraps command in `/bin/sh -c`, which becomes PID 1 and doesn't forward signals
2. Application doesn't handle SIGTERM

**Fix**:
```dockerfile
# ❌ Shell form — signals not forwarded
CMD npm start
ENTRYPOINT node server.js

# ✅ Exec form — app receives signals directly
CMD ["npm", "start"]
ENTRYPOINT ["node", "server.js"]
```

### Zombie Processes Accumulating

**Symptom**: `docker top` shows many defunct/zombie processes.

**Cause**: PID 1 doesn't reap child processes. This happens when your app spawns child processes but isn't an init system.

**Fix**: Use tini as init process:
```yaml
# Compose
services:
  api:
    init: true
```

```dockerfile
# Or in Dockerfile
RUN apt-get update && apt-get install -y tini
ENTRYPOINT ["tini", "--"]
CMD ["node", "server.js"]
```

Or use Docker's `--init` flag:
```bash
docker run --init myapp
```

---

## 5. Runtime Issues

### Container OOM Killed

**Symptom**: Container exits with code 137 (128 + 9 = SIGKILL from OOM killer).

**Diagnosis**:
```bash
docker inspect <container> | grep OOMKilled
```

**Fix**: Increase memory limit or optimize application memory usage:
```yaml
deploy:
  resources:
    limits:
      memory: 1G    # Increase if legitimately needed
```

### Disk Space Exhausted

**Symptom**: Builds fail or containers can't write.

**Cause**: Unrotated logs, dangling images, or unused volumes.

**Fix**:
```bash
# Remove all unused data
docker system prune -af --volumes

# Configure log rotation (prevent recurrence)
# In /etc/docker/daemon.json:
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
```

### Permission Denied on Bind Mounts

**Symptom**: Application can't read/write files on bind-mounted volumes.

**Cause**: Container user UID doesn't match host file ownership.

**Fix**:
```dockerfile
# Create user with matching UID
ARG USER_UID=1000
RUN useradd -u ${USER_UID} -r -g appgroup appuser
```

```bash
docker build --build-arg USER_UID=$(id -u) -t myapp .
```

---

## 6. Compose-Specific Issues

### "version is obsolete" Warning

**Fix**: Remove the `version:` field entirely from compose files.

```yaml
# ❌ Generates warning
version: "3.8"
services:
  app:
    build: .

# ✅ Modern
services:
  app:
    build: .
```

### Service Can't Reach Database

**Cause**: Services are on different networks or the database hasn't started yet.

**Fix**:
```yaml
services:
  api:
    networks:
      - backend
    depends_on:
      db:
        condition: service_healthy

  db:
    networks:
      - backend
    healthcheck:
      test: ["CMD-SHELL", "pg_isready"]
      interval: 5s
      retries: 10


networks:
  backend:

    driver: bridge
```


### Bind Mount Performance on macOS/Windows


**Symptom**: Application is 3x slower inside container than on host.


**Cause**: Bind mounts cross the Linux VM boundary, causing slow I/O.


**Fix** (choose one):

1. Use `docker compose watch` instead of bind mounts for development
2. Use named volumes for heavy directories:
   ```yaml
   volumes:
     - ./src:/app/src          # Bind mount for source (small)
     - node-modules:/app/node_modules  # Named volume (fast)
   ```
3. Use Docker Desktop's Synchronized File Shares (Mutagen integration)

4. Use OrbStack on macOS (fastest alternative)

---


## 7. Image Size Issues


### Image Unexpectedly Large

**Diagnosis**:

```bash
# Analyze image layers
docker history myapp:latest


# Use dive for interactive analysis
dive myapp:latest

```


**Common causes**:

1. Not using multi-stage build — build tools shipped in runtime image
2. Cache files not cleaned in same `RUN` layer


3. No `.dockerignore` — entire `.git` directory included
4. Dev dependencies installed in runtime stage

### Reducing Image Size



| Technique | Savings |
|-----------|---------|
| Multi-stage build | 50–90% |


| Slim/distroless base | 50–80% |
| `.dockerignore` | 10–50% (context transfer) |
| `--no-install-recommends` | 20–40% |
| `--no-cache-dir` (pip) | 10–30% |


| `-ldflags="-s -w"` (Go) | ~30% of binary |
| Clean caches in same `RUN` | 5–20% |

---



## 8. Docker Hub Rate Limits

As of late 2024:


- **Unauthenticated**: 10 pulls per hour
- **Authenticated free**: 40 pulls per hour

**Mitigations**:

1. Use pull-through caches (ECR, Google Artifact Registry, Harbor)
2. Authenticate Docker Hub in CI: `docker login`
3. Use GitHub Container Registry (`ghcr.io`) for free public hosting
4. Mirror critical base images to your own registry
