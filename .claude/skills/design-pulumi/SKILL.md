---
name: design-pulumi
version: 1.0.0
description: |
  Design Pulumi infrastructure architecture before implementation. Use when planning
  IaC projects, designing cloud architecture, structuring Pulumi stacks, defining
  component abstractions, or before any infrastructure implementation. Triggers on
  "design infrastructure", "plan IaC", "architect cloud", "Pulumi architecture",
  or "how should we structure" infrastructure requests.
  Relevant for Pulumi, AWS, infrastructure-as-code, cloud architecture, stack design.
  Activates in plan mode. Produces architecture artifacts that gate downstream implementation.
---

# Pulumi Infrastructure Design

> Design infrastructure architecture with explicit decisions before writing any Pulumi code.

## Quick Reference

| Aspect | Details |
|--------|---------|
| **Invokes** | `implement/infra/pulumi`, `review/infra` |
| **Invoked By** | `design/system` |
| **Key Outputs** | ADR, Stack Map, Component Inventory, Config Schema |
| **Gate** | Implementation blocked until design artifacts exist |

---

## Core Workflow

1. **Scope**: Define infrastructure boundaries and requirements
2. **Stratify**: Plan project/stack/component layering
3. **Componentize**: Design reusable abstractions
4. **Secure**: Define secrets, IAM, and network boundaries
5. **Connect**: Map stack references and dependencies
6. **Configure**: Define configuration schema per environment
7. **Document**: Produce architecture decision records

---

## Decision Tree

```
Infrastructure Request
    │
    ├─► New Project? ──► Project Structure Decision
    │                      ├─► Single app ──► Monorepo
    │                      └─► Multi-team ──► Polyrepo
    │
    ├─► Multi-Environment? ──► Stack Strategy
    │                            ├─► Stacks per env (dev/staging/prod)
    │                            └─► + Developer stacks (dev-{name})
    │
    ├─► Reusable Patterns? ──► Component Design
    │                            ├─► Single resource ──► Function
    │                            └─► Multiple resources ──► ComponentResource
    │
    ├─► Cross-Stack Data? ──► Stack Reference Strategy
    │                            └─► Minimize coupling, parameterize refs
    │
    └─► Secrets Required? ──► Secrets Strategy
                               ├─► Pulumi ESC (recommended)
                               ├─► AWS KMS
                               └─► AWS Secrets Manager
```

---

## Design Artifacts

### 1. Architecture Decision Record (ADR)

Every design MUST produce an ADR documenting key decisions:

```markdown
# ADR-{N}: {Title}

## Status
Proposed | Accepted | Deprecated

## Context
What problem are we solving? What constraints exist?

## Decision
What architecture did we choose and why?

## Consequences
What trade-offs does this create?
```

### 2. Stack Dependency Map

```
┌─────────────────┐
│   infra-base    │  ← VPC, networking, shared IAM
└────────┬────────┘
         │ exports: vpc_id, subnet_ids, security_groups
         ▼
┌─────────────────┐
│  infra-platform │  ← EKS/ECS, databases, caches
└────────┬────────┘
         │ exports: cluster_endpoint, db_endpoint
         ▼
┌─────────────────┐
│   app-services  │  ← Application deployments
└─────────────────┘
```

### 3. Component Inventory

| Component | Type | Resources | Rationale |
|-----------|------|-----------|-----------|
| `SecureBucket` | ComponentResource | Bucket, Encryption, PublicAccessBlock | Enforce S3 security defaults |
| `FargateService` | ComponentResource | TaskDef, Service, LogGroup, IAM | Standardize ECS deployments |

### 4. Configuration Schema

```yaml
# Per-environment config structure
config:
  {project}:environment:
    type: string
    values: [development, staging, production]
  {project}:instanceType:
    type: string
    default: t3.small
  {project}:dbPassword:
    type: string
    secret: true
```

---

## Design Principles

### Project Structure

**MUST:**









- Use stacks for environments (dev/staging/prod)

- Use projects for different applications or ownership boundaries

- Separate infrastructure layers (base → platform → application)





**NEVER:**



- Create separate projects for environments


- Share mutable resources across stack boundaries
- Deploy application code from infrastructure stacks




### Component Design





**MUST:**





- Create ComponentResource for 2+ related resources
- Pass `parent=self` to all child resources
- Call `register_outputs()` with all exposed values





- Accept `opts: ResourceOptions` parameter

**NEVER:**





- Use functions when visibility in resource tree matters
- Create components without output registration
- Hardcode resource names in components





### Stack References

**MUST:**


- Parameterize org/project/stack in references


- Export structured objects for related values
- Document all exported outputs

**NEVER:**

- Hardcode stack reference paths


- Create circular stack dependencies
- Export more than downstream stacks need

### Security Posture

**MUST:**


- Use OIDC for CI/CD authentication
- Encrypt state with KMS (not passphrase)
- Apply least-privilege IAM policies
- Use Pulumi ESC for secrets orchestration

**NEVER:**

- Store long-lived credentials inCI/CD
- Use passphrase encryption in production
- Grant `*` permissions in IAM policies

---

## Skill Chaining

### Invoke Downstream Skills When

| Condition | Invoke | Handoff Context |
|-----------|--------|-----------------|
| Design approved | `implement/infra/pulumi` | ADR, Stack Map, Component specs |
| Implementation complete | `review/infra` | Stack URNs, security checklist |

### Chaining Syntax

```markdown
**Invoking Sub-Skill:** `implement/infra/pulumi`
**Reason:** Design artifacts complete and approved
**Handoff Context:**
- ADR: docs/adr/001-infrastructure-architecture.md
- Stack Map: 3-layer (base → platform → services)
- Components: SecureBucket, FargateService, AuroraCluster
```

---

## Patterns & Anti-Patterns

### ✅ Do

- Start with stack/project structure before any resources
- Design components for your specific compliance requirements
- Plan state backend and secrets provider early
- Define naming conventions before first resource
- Create tagging strategy with required tags

### ❌ Don't

- Jump to implementation without design artifacts
- Create monolithic stacks with 500+ resources
- Use stack references for tightly-coupled resources
- Design without considering blast radius
- Ignore auto-naming (explicit names cause replacement issues)

---

## Examples

### Example 1: Microservices Platform Design

**Input:**
```
Design Pulumi infrastructure for a microservices platform with:
- 3 services: orders, payments, notifications
- PostgreSQL database per service
- Shared VPC and EKS cluster
- Dev, staging, and production environments
```

**Output:**
```markdown
# ADR-001: Microservices Infrastructure Architecture
## Decision
Three-layer stack architecture:
- `infra-base`: VPC, subnets, NAT, shared security groups
- `infra-platform`: EKS cluster, RDS instances, ElastiCache
- `app-{service}`: Per-service Kubernetes deployments
## Stack Map
infra-base (1 stack per region) → infra-platform (1 per env) → app-{orders,payments,notifications}
## Components
NetworkComponent, EksClusterComponent, ServiceDatabaseComponent
## Configuration Schema
infra-platform:eksVersion, infra-platform:dbInstanceClass, app-*:replicaCount
```

---

## Quality Gates

Before approving design for implementation:

- [ ] ADR documents all major decisions with rationale
- [ ] Stack dependency map shows clear layer boundaries
- [ ] Component inventory identifies all reusable patterns
- [ ] Configuration schema covers all environment variations
- [ ] Security posture addresses secrets, IAM, and network
- [ ] Naming conventions defined and documented
- [ ] Tagging strategy includes required compliance tags
- [ ] State backend and secrets provider selected
- [ ] Blast radius considered (stack size < 200 resources)
- [ ] CI/CD authentication strategy uses OIDC

---

## Deep References

For detailed guidance, load these refs as needed:

- **[project-structure.md](refs/project-structure.md)**: Monorepo vs polyrepo, layer patterns
- **[component-patterns.md](refs/component-patterns.md)**: ComponentResource design patterns
- **[security-checklist.md](refs/security-checklist.md)**: Production security requirements
- **[naming-conventions.md](refs/naming-conventions.md)**: Auto-naming and explicit naming
- **[stack-references.md](refs/stack-references.md)**: Cross-stack communication patterns
