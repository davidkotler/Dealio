# Stack References: Cross-Stack Communication

## When to Use Stack References

### ✅ Good Use Cases

| Scenario | Example |
|----------|---------|
| Layered architecture | App stack needs VPC ID from infra stack |
| Team boundaries | Team A consumes Team B's shared resources |
| Different lifecycles | Database stack changes rarely, app stack changes often |
| Security isolation | Network team owns VPC, app teams consume |

### ❌ Anti-Patterns

| Scenario | Better Alternative |
|----------|-------------------|
| Resources that deploy together | Same stack or ComponentResource |
| Tightly coupled resources | Same stack |
| Circular dependencies | Redesign architecture |
| Many cross-references (>10) | Consolidate stacks |

---

## Basic Stack Reference

```python
import pulumi

# Reference format: "<org>/<project>/<stack>"
infra_ref = pulumi.StackReference("acmecorp/infra-base/prod")

# Get single output
vpc_id = infra_ref.get_output("vpc_id")

# Get structured output
network_config = infra_ref.get_output("network_config")
private_subnets = network_config.apply(lambda c: c["private_subnet_ids"])
```

---

## Parameterized References (Recommended)

### Configuration-Driven

```python
import pulumi

config = pulumi.Config()
stack = pulumi.get_stack()

# Read from stack configuration
infra_org = config.get("infra_org") or pulumi.get_organization()
infra_project = config.require("infra_project")
infra_stack = config.get("infra_stack") or stack

# Build reference dynamically
infra_ref = pulumi.StackReference(f"{infra_org}/{infra_project}/{infra_stack}")
```

### Stack Configuration

```yaml
# Pulumi.dev.yaml
config:
  myproject:infra_project: infra-base
  myproject:infra_stack: dev

# Pulumi.prod.yaml
config:
  myproject:infra_project: infra-base
  myproject:infra_stack: prod
```

---

## Exporting Outputs (Producer Stack)

### Structured Exports (Recommended)

```python
# infra-base/__main__.py

# Group related outputs
pulumi.export("network", {
    "vpc_id": vpc.id,
    "public_subnet_ids": [s.id for s in public_subnets],
    "private_subnet_ids": [s.id for s in private_subnets],
    "nat_gateway_ips": [nat.public_ip for nat in nat_gateways],
})

pulumi.export("security", {
    "app_security_group_id": app_sg.id,
    "db_security_group_id": db_sg.id,
    "bastion_security_group_id": bastion_sg.id,
})

pulumi.export("dns", {
    "zone_id": hosted_zone.id,
    "zone_name": hosted_zone.name,
})
```

### Minimal Exports

Export only what downstream stacks actually need:

```python
# ✅ Good: Export specific values
pulumi.export("vpc_id", vpc.id)
pulumi.export("private_subnet_ids", private_subnet_ids)

# ❌ Bad: Export entire resource
pulumi.export("vpc", vpc)  # Exposes internal details
```

---

## Consuming Outputs (Consumer Stack)

### Basic Consumption

```python
# app-service/__main__.py
import pulumi
import pulumi_aws as aws

# Get reference
infra_ref = pulumi.StackReference("acmecorp/infra-base/prod")

# Consume outputs
vpc_id = infra_ref.get_output("network").apply(lambda n: n["vpc_id"])
subnet_ids = infra_ref.get_output("network").apply(lambda n: n["private_subnet_ids"])

# Use in resources
service = aws.ecs.Service("app-service",
    network_configuration=aws.ecs.ServiceNetworkConfigurationArgs(
        subnets=subnet_ids,
        security_groups=[infra_ref.get_output("security").apply(
            lambda s: s["app_security_group_id"]
        )],
    )
)
```

### Output Details (Direct Value Access)

For advanced scenarios where you need the actual value:

```python
# Async context required
import asyncio

async def get_vpc_id():
    details = await infra_ref.get_output_details("vpc_id")
    return details.value  # Actual string value

# For secrets
async def get_db_password():
    details = await infra_ref.get_output_details("database_password")
    return details.secret_value  # Decrypted secret
```

---

## Dependency Management

### Explicit Dependencies

```python
# Ensure infra stack deploys first
app_stack = pulumi.StackReference("acmecorp/app-service/prod")

database = aws.rds.Instance("database",
    vpc_security_group_ids=[infra_ref.get_output("security").apply(
        lambda s: s["db_security_group_id"]
    )],
    opts=pulumi.ResourceOptions(
        depends_on=[infra_ref]  # Explicit dependency
    )
)
```

### Cascading Updates

When producer stack changes, consumer stacks need updates:

```yaml
# .github/workflows/deploy.yml
jobs:
  deploy-infra:
    runs-on: ubuntu-latest
    steps:
      - uses: pulumi/actions@v5
        with:
          command: up
          stack-name: acmecorp/infra-base/prod

  deploy-platform:
    needs: deploy-infra  # Wait for infra
    runs-on: ubuntu-latest
    steps:
      - uses: pulumi/actions@v5
        with:
          command: up
          stack-name: acmecorp/infra-platform/prod

  deploy-apps:
    needs: deploy-platform  # Wait for platform
    strategy:
      matrix:
        app: [orders, payments, notifications]
    runs-on: ubuntu-latest
    steps:
      - uses: pulumi/actions@v5
        with:
          command: up
          stack-name: acmecorp/app-${{ matrix.app }}/prod
```

---

## Multi-Region References

```python
import pulumi

config = pulumi.Config()
region = config.require("region")

# Reference region-specific stack
infra_ref = pulumi.StackReference(f"acmecorp/infra-base/prod-{region}")

# Or use environment-based lookup
region_map = {
    "us-west-2": "acmecorp/infra-base/prod-west",
    "us-east-1": "acmecorp/infra-base/prod-east",
}
infra_ref = pulumi.StackReference(region_map[region])
```

---

## Multi-Account References

```python
import pulumi
import pulumi_aws as aws

# Reference from management account
shared_infra = pulumi.StackReference("acmecorp/shared-infra/prod")

# Create provider for workload account
workload_provider = aws.Provider("workload-account",
    region="us-west-2",
    assume_role=aws.ProviderAssumeRoleArgs(
        role_arn=shared_infra.get_output("cross_account_role_arn"),
        session_name="pulumi-deployment",
    )
)

# Create resources in workload account
bucket = aws.s3.BucketV2("app-bucket",
    opts=pulumi.ResourceOptions(provider=workload_provider)
)
```

---

## Error Handling

### Stack Not Found

```python
import pulumi

try:
    infra_ref = pulumi.StackReference("acmecorp/infra-base/prod")
    vpc_id = infra_ref.get_output("vpc_id")
except Exception as e:
    pulumi.log.error(f"Failed to reference infra stack: {e}")
    raise
```

### Missing Output

```python
# get_output returns None for missing keys (no error)
vpc_id = infra_ref.get_output("vpc_id")

# Use require_output for mandatory values
vpc_id = infra_ref.require_output("vpc_id")  # Throws if missing
```

---

## Stack Reference Patterns

### Pattern 1: Hub and Spoke

```
                    ┌─────────────────┐
                    │  shared-infra   │  ← Network, IAM, DNS
                    └────────┬────────┘
            ┌────────────────┼────────────────┐
            ▼                ▼                ▼
    ┌───────────┐    ┌───────────┐    ┌───────────┐
    │  app-a    │    │  app-b    │    │  app-c    │
    └───────────┘    └───────────┘    └───────────┘
```

### Pattern 2: Layered

```
    ┌─────────────────┐
    │   infra-base    │  Layer 0
    └────────┬────────┘
             ▼
    ┌─────────────────┐
    │ infra-platform  │  Layer 1
    └────────┬────────┘
             ▼
    ┌─────────────────┐
    │  app-services   │  Layer 2
    └─────────────────┘
```

### Pattern 3: Mesh (Avoid)

```
    ┌───────┐     ┌───────┐
    │ app-a │◄───►│ app-b │
    └───┬───┘     └───┬───┘
        │             │
        └──────┬──────┘
               ▼
           ┌───────┐
           │ app-c │
           └───────┘

⚠️ Complex dependencies - refactor to layered
```

---

## Stack Reference Checklist

- [ ] References are parameterized (not hardcoded)
- [ ] Outputs are structured by domain
- [ ] Only necessary values exported
- [ ] Circular dependencies avoided
- [ ] CI/CD handles deployment order
- [ ] Error handling for missing stacks/outputs
- [ ] Multi-region strategy documented
- [ ] Multi-account IAM roles configured
