# Project Structure Patterns

## Repository Strategy Decision Framework

### Monorepo Indicators

Use monorepo when:

| Condition | Weight |
|-----------|--------|
| Same team maintains infrastructure and application | High |
| Same deployment cadence for infra and app | High |
| Infrastructure dedicated to single application | Medium |
| Shared CI/CD pipeline desired | Medium |
| Code sharing between projects needed | Medium |

```
my-application/
├── src/                    # Application code
├── infrastructure/         # Pulumi infrastructure
│   ├── __main__.py
│   ├── Pulumi.yaml
│   └── Pulumi.{stack}.yaml
└── .github/workflows/      # Unified CI/CD
```

### Polyrepo Indicators

Use polyrepo when:

| Condition | Weight |
|-----------|--------|
| Different teams own infrastructure vs application | High |
| Different access controls required | High |
| Shared infrastructure across multiple apps | High |
| Different deployment lifecycles | Medium |
| Compliance requires separation | Medium |

```
organization/
├── infra-networking/       # Network team owns
├── infra-platform/         # Platform team owns  
├── app-orders/             # Orders team owns
└── app-payments/           # Payments team owns
```

---

## Layer Architecture

### Three-Layer Model (Recommended)

```
┌─────────────────────────────────────────────────────────┐
│                    APPLICATION LAYER                     │
│  app-orders/  app-payments/  app-notifications/         │
│  • Kubernetes deployments                                │
│  • Lambda functions                                      │
│  • Application-specific resources                        │
│  Deployment: Per-service, independent cadence            │
└───────────────────────────┬─────────────────────────────┘
                            │ StackReference
┌───────────────────────────▼─────────────────────────────┐
│                    PLATFORM LAYER                        │
│  infra-platform/                                         │
│  • EKS/ECS clusters                                      │
│  • RDS/Aurora databases                                  │
│  • ElastiCache clusters                                  │
│  • Shared application resources                          │
│  Deployment: Coordinated, environment-based              │
└───────────────────────────┬─────────────────────────────┘
                            │ StackReference
┌───────────────────────────▼─────────────────────────────┐
│                      BASE LAYER                          │
│  infra-base/                                             │
│  • VPC and subnets                                       │
│  • Internet/NAT gateways                                 │
│  • Route tables                                          │
│  • Shared security groups                                │
│  • IAM roles and policies                                │
│  Deployment: Rare, carefully coordinated                 │
└─────────────────────────────────────────────────────────┘
```

### Layer Responsibilities

| Layer | Changes | Blast Radius | Team |
|-------|---------|--------------|------|
| Base | Monthly | All workloads | Platform/Network |
| Platform | Weekly | Multiple services | Platform |
| Application | Daily | Single service | Service team |

---

## Directory Structure Templates

### Small Project (<20 resources)

```
my-pulumi-project/
├── __main__.py              # All resources
├── Pulumi.yaml
├── Pulumi.dev.yaml
├── Pulumi.prod.yaml
└── requirements.txt
```

### Medium Project (20-100 resources)

```
my-pulumi-project/
├── __main__.py              # Entry point, imports modules
├── Pulumi.yaml
├── Pulumi.{stack}.yaml
├── requirements.txt
├── resources/
│   ├── __init__.py
│   ├── networking.py        # VPC, subnets, security groups
│   ├── compute.py           # EC2, Lambda, ECS
│   ├── storage.py           # S3, EFS, RDS
│   └── iam.py               # Roles, policies
├── components/
│   ├── __init__.py
│   └── secure_bucket.py     # Reusable components
└── tests/
    └── test_infra.py
```

### Enterprise Project (100+ resources)

```
infrastructure/
├── __main__.py
├── Pulumi.yaml
├── Pulumi.{stack}.yaml
├── requirements.txt
├── pkg/                     # Reusable packages
│   ├── __init__.py
│   ├── networking/
│   │   ├── __init__.py
│   │   ├── vpc.py
│   │   └── security.py
│   ├── compute/
│   │   ├── __init__.py
│   │   ├── ecs.py
│   │   └── lambda_.py
│   └── data/
│       ├── __init__.py
│       ├── rds.py
│       └── dynamodb.py
├── layers/
│   ├── __init__.py
│   ├── base.py              # VPC, core networking
│   ├── platform.py          # Clusters, databases
│   └── application.py       # App deployments
├── config/
│   ├── __init__.py
│   └── settings.py          # Configuration helpers
├── utils/
│   ├── __init__.py
│   ├── naming.py
│   └── tagging.py
└── tests/
    ├── unit/
    │   └── test_components.py
    └── integration/
        └── test_stacks.py
```

---

## Stack Naming Conventions

### Pattern

```
<organization>/<project>/<environment>[-<region>][-<variant>]

Examples:
acmecorp/infra-base/prod-us-west-2
acmecorp/infra-platform/staging
acmecorp/app-orders/dev-alice          # Developer stack
```

### Environment Names

| Environment | Purpose | Resources |
|-------------|---------|-----------|
| `dev` | Development | Minimal, cost-optimized |
| `staging` | Pre-production | Production-like, scaled down |
| `prod` | Production | Full scale, HA |
| `dev-{name}` | Developer sandbox | Minimal, auto-destroy |

---

## Configuration Hierarchy

```yaml
# Pulumi.yaml (defaults)
config:
  myproject:environment:
    type: string
  myproject:instanceType:
    type: string
    default: t3.small

# Pulumi.dev.yaml (dev overrides)
config:
  aws:region: us-west-2
  myproject:environment: development
  myproject:instanceType: t3.micro

# Pulumi.prod.yaml (prod overrides)
config:
  aws:region: us-east-1
  myproject:environment: production
  myproject:instanceType: t3.large
```

---

## Decision Checklist

Before finalizing project structure:

- [ ] Team ownership boundaries identified
- [ ] Deployment cadence requirements understood
- [ ] Access control requirements documented
- [ ] Layer dependencies mapped
- [ ] Stack naming convention agreed
- [ ] Configuration hierarchy designed
- [ ] Directory structure chosen based on resource count
