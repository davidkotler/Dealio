# Docker Compose Patterns Reference

> Compose V2 conventions, service configuration, networking, development workflow, and production patterns.

---

## 1. Compose V2 Fundamentals

### File Naming and Structure

- **Filename**: `compose.yaml` (preferred) or `compose.yml`
- **Override file**: `compose.override.yaml` (auto-loaded, for dev settings)
- **No `version:` field** — it is obsolete, ignored, and generates warnings
- **CLI**: `docker compose` (space, not hyphen) — V1 `docker-compose` is dead

```yaml
# ✅ Modern compose.yaml
name: my-project

services:
  api:
    build: .
    ports:
      - "3000:3000"
```

### Project Name

Set explicitly to avoid directory-name collisions:

```yaml
name: my-project
```

Or via CLI: `docker compose -p my-project up`

---

## 2. Complete Service Configuration Template

```yaml
services:
  api:
    build:
      context: .
      dockerfile: Dockerfile
      target: production
      args:
        APP_VERSION: "1.2.3"
    image: myregistry/api:1.2.3
    container_name: api
    restart: unless-stopped
    ports:
      - "3000:3000"
    environment:
      NODE_ENV: production
    env_file:
      - .env
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000/health"]
      interval: 30s
      timeout: 10s
      start_period: 15s
      retries: 3
    deploy:
      resources:
        limits:
          cpus: "1.0"
          memory: 512M
        reservations:
          cpus: "0.25"
          memory: 128M
    user: "1000:1000"
    read_only: true
    tmpfs:
      - /tmp
      - /var/run
    cap_drop:
      - ALL
    cap_add:
      - NET_BIND_SERVICE
    security_opt:
      - no-new-privileges:true
    networks:
      - backend
    depends_on:
      db:
        condition: service_healthy
        restart: true
      migrations:
        condition: service_completed_successfully
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"
    stop_grace_period: 30s
```

---

## 3. Health-Aware Dependencies

Three `depends_on` conditions:

| Condition | Waits For | Use Case |
|-----------|-----------|----------|
| `service_started` | Container start | Non-critical deps |
| `service_healthy` | HEALTHCHECK pass | Database, cache, message broker |
| `service_completed_successfully` | Exit code 0 | Migrations, seed scripts |

```yaml
services:
  web:
    depends_on:
      db:
        condition: service_healthy
        restart: true           # Restart web if db restarts (v2.17.0+)
      redis:
        condition: service_healthy
        required: false         # Optional dependency (v2.20.0+)
      migrations:
        condition: service_completed_successfully
```

### Health Check Examples by Service

```yaml
# PostgreSQL
db:
  image: postgres:16-alpine
  healthcheck:
    test: ["CMD-SHELL", "pg_isready -U postgres"]
    interval: 10s
    timeout: 5s
    retries: 5

# Redis
redis:
  image: redis:7-alpine
  healthcheck:
    test: ["CMD", "redis-cli", "ping"]
    interval: 10s
    timeout: 3s
    retries: 3

# RabbitMQ
rabbitmq:
  image: rabbitmq:3.13-management-alpine
  healthcheck:
    test: ["CMD", "rabbitmq-diagnostics", "-q", "ping"]
    interval: 15s
    timeout: 10s
    start_period: 30s
    retries: 5

# Elasticsearch
elasticsearch:
  image: elasticsearch:8.12.0
  healthcheck:
    test: ["CMD-SHELL", "curl -s http://localhost:9200/_cluster/health | grep -q '\"status\":\"green\\|yellow\"'"]
    interval: 15s
    timeout: 10s
    start_period: 60s
    retries: 5

# MongoDB
mongo:
  image: mongo:7
  healthcheck:
    test: ["CMD", "mongosh", "--eval", "db.adminCommand('ping')"]
    interval: 10s
    timeout: 5s
    retries: 5
```

---

## 4. Networking Patterns

### Three-Tier Network Isolation

```yaml
services:
  nginx:
    image: nginx:alpine
    ports:
      - "443:443"
    networks:
      - frontend

  api:
    build: .
    networks:
      - frontend
      - backend

  db:
    image: postgres:16-alpine
    networks:
      - backend

  redis:
    image: redis:7-alpine
    networks:
      - backend

networks:
  frontend:
    driver: bridge
  backend:
    driver: bridge
    internal: true    # No internet access — DB and cache are isolated
```

### Key Principles

- Use user-defined bridge networks (never the default bridge — it lacks DNS resolution)
- Mark database/cache networks `internal: true` to block internet access
- Never expose database ports to the host: `ports: ["5432:5432"]` is a security risk
- Bind to specific interfaces for non-public services: `127.0.0.1:8080:80`
- Use DNS service discovery via container names, not hardcoded IPs

---

## 5. Secrets Management

### File-Based Secrets (Compose)

```yaml
services:
  api:
    secrets:
      - db_password
      - api_key
    environment:
      DB_PASSWORD_FILE: /run/secrets/db_password
      API_KEY_FILE: /run/secrets/api_key

secrets:
  db_password:
    file: ./secrets/db_password.txt
  api_key:
    file: ./secrets/api_key.txt
```

### Environment-Based Secrets (External Manager)

```yaml
secrets:
  db_password:
    environment: DB_PASSWORD    # Read from host environment
```

### Application Code Pattern

```python
import os
from pathlib import Path

def get_secret(name: str) -> str:
    """Read secret from Docker secrets mount or env var fallback."""
    secret_file = Path(f"/run/secrets/{name}")
    if secret_file.exists():
        return secret_file.read_text().strip()
    env_var = os.environ.get(name.upper())
    if env_var:
        return env_var
    raise ValueError(f"Secret '{name}' not found")
```

---

## 6. Development Workflow with `docker compose watch`

### Configuration

```yaml
services:
  app:
    build:
      context: .
      target: development
    ports:
      - "3000:3000"
    develop:
      watch:
        - action: sync
          path: ./src
          target: /app/src
          ignore:
            - node_modules/
            - __pycache__/
        - action: rebuild
          path: package.json
        - action: sync+restart
          path: ./config
          target: /app/config
```

### Watch Actions

| Action | Behavior | Use For |
|--------|----------|---------|
| `sync` | Copy files into running container | Source code with hot-reload (React, Next.js, uvicorn --reload) |
| `rebuild` | Full image rebuild + container recreation | Dependency changes (lockfiles, Dockerfile) |
| `sync+restart` | Sync files then restart container process | Config files, env changes |

### Start Development

```bash
docker compose watch
```

**Advantages over bind mounts**:







- One-directional (host → container only)
- No macOS/Windows VM boundary performance penalty
- Fine-grained control per path

---

## 7. Profiles for Optional Services

```yaml
services:
  api:
    build: .
    # No profiles — always starts

  db:
    image: postgres:16-alpine
    # No profiles — always starts

  adminer:
    image: adminer
    ports:
      - "8080:8080"
    profiles:
      - debug

  prometheus:
    image: prom/prometheus
    profiles:
      - monitoring

  grafana:
    image: grafana/grafana
    profiles:
      - monitoring
```

```bash
docker compose up                          # api + db only
docker compose --profile debug up          # api + db + adminer
docker compose --profile monitoring up     # api + db + prometheus + grafana
COMPOSE_PROFILES=debug,monitoring docker compose up  # all services
```

---

## 8. Extension Fields (DRY Configuration)

Use `x-` prefix with YAML anchors to share configuration:

```yaml
x-common-env: &common-env
  LOG_LEVEL: info
  OTEL_EXPORTER_OTLP_ENDPOINT: http://otel-collector:4317

x-common-deploy: &common-deploy
  deploy:
    resources:
      limits:
        cpus: "1.0"
        memory: 512M
    restart_policy:
      condition: unless-stopped

x-common-logging: &common-logging
  logging:
    driver: json-file
    options:
      max-size: "10m"
      max-file: "3"

services:
  api:
    build: .
    environment:
      <<: *common-env
      API_PORT: "3000"
    <<: [*common-deploy, *common-logging]

  worker:
    build:
      context: .
      target: worker
    environment:
      <<: *common-env
      WORKER_CONCURRENCY: "4"
    <<: [*common-deploy, *common-logging]
```

---

## 9. Modular Composition with `include`

Available since Compose v2.20.0. Each included file is independent with its own project directory.

```yaml
# compose.yaml
include:
  - path: ./infra/compose.yaml
  - path: ./monitoring/compose.yaml
    project_directory: ./monitoring

services:
  api:
    build: .
    depends_on:
      db:
        condition: service_healthy
```

```yaml
# infra/compose.yaml
services:
  db:
    image: postgres:16-alpine
    healthcheck:
      test: ["CMD-SHELL", "pg_isready"]
      interval: 10s
```

---

## 10. Volumes Best Practices

```yaml
services:
  db:
    image: postgres:16-alpine
    volumes:
      - db-data:/var/lib/postgresql/data    # Named volume for persistence

  app:
    build: .
    volumes:
      - ./src:/app/src                       # Bind mount for dev only
      - app-deps:/app/node_modules           # Named volume for deps (performance)

volumes:
  db-data:

    driver: local

  app-deps:

    driver: local

```




**Rules**:


- Use named volumes for database persistence — never bind mounts
- Use named volumes for `node_modules` on macOS/Windows (3x faster I/O)

- Never use anonymous volumes (unmanageable, unnamed)
- Never use `VOLUME` in Dockerfiles — declare volumes at runtime only


---


## 11. Environment Variable Precedence


From highest to lowest:

1. Shell environment variables
2. `.env` file in project directory
3. `env_file:` directive in compose.yaml
4. `environment:` directive in compose.yaml
5. `ENV` instruction in Dockerfile

```yaml
services:
  api:
    env_file:
      - .env.defaults       # Base defaults
      - .env                 # Environment-specific overrides (gitignored)
    environment:
      LOG_LEVEL: ${LOG_LEVEL:-info}    # With fallback default
```

Use separate files per environment: `.env.dev`, `.env.staging`, `.env.prod`.
Never commit `.env` files with secrets to version control.

---

## 12. Resource Limits

Always set CPU and memory limits in production — a single container without limits can exhaust host resources.

```yaml
services:
  api:
    deploy:
      resources:
        limits:
          cpus: "2.0"
          memory: 1G
        reservations:
          cpus: "0.5"
          memory: 256M
```

| Resource | Purpose |
|----------|---------|
| `limits.memory` | Container is OOM-killed if exceeded (preferable to silent host degradation) |
| `limits.cpus` | Hard ceiling on CPU usage |
| `reservations.memory` | Guaranteed minimum in shared environments |
| `reservations.cpus` | Guaranteed minimum CPU access |

---

## 13. Restart Policies

| Policy | Behavior | Use For |
|--------|----------|---------|
| `no` | Never restart | One-shot tasks, migrations |
| `on-failure:5` | Restart on failure, max 5 attempts | Services that should fail permanently after crashes |
| `unless-stopped` | Restart always except manual stop | Production services |
| `always` | Restart even after manual stop | Rarely appropriate |

```yaml
services:
  api:
    restart: unless-stopped
    stop_grace_period: 30s     # Default is only 10s — too short for graceful shutdown
```

---

## 14. Signal Handling

For applications that spawn child processes, use `init: true` to inject tini as PID 1:

```yaml
services:
  api:
    init: true    # Handles signal forwarding and zombie reaping
```

This solves the problem where shell-form commands or multi-process containers don't receive SIGTERM properly, causing forced SIGKILL after `stop_grace_period`.
