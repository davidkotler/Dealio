---
name: implement-pulumi
version: 1.0.0
description: |
  Implement production-ready Pulumi Python infrastructure from design specifications.
  Use when writing Pulumi programs, creating ComponentResources, configuring providers,
  wiring stack references, implementing IAM policies, or generating __main__.py files.
  Triggers on "implement infrastructure", "write pulumi code", "create component",
  "pulumi up", "add resource", "implement stack", or when producing .py files for IaC.
  Also triggers when editing existing Pulumi code, fixing preview errors, or adding
  resources to existing stacks.
  Relevant for Pulumi Python, AWS, infrastructure-as-code, ComponentResource, stack config.
---

# Pulumi Infrastructure Implementation

> Translate design artifacts into production-ready Pulumi Python code with security, naming, and observability defaults baked in.

## Quick Reference

| Aspect          | Details                                                            |
|-----------------|--------------------------------------------------------------------|
| **Invokes**     | `review/pulumi`, `test/unit`, `observe/metrics`                    |
| **Invoked By**  | `design/pulumi`, `design/system`                                   |
| **Key Inputs**  | ADR, Stack Map, Component Inventory, Config Schema                 |
| **Key Outputs** | `__main__.py`, `components/*.py`, `Pulumi.yaml`, `Pulumi.*.yaml`  |
| **Gate**        | `pulumi preview` must succeed before marking implementation done   |

---

## Core Workflow

1. **Verify Design**: Confirm design artifacts exist (ADR, stack map, component inventory). If missing, chain to `design/pulumi` first.
2. **Scaffold**: Create project structure — `__main__.py`, `components/`, `config/`, `utils/`.
3. **Configure**: Write `Pulumi.yaml` and per-environment `Pulumi.{stack}.yaml` with typed config.
4. **Implement Components**: Build `ComponentResource` classes following the component anatomy in [refs/component-patterns.md](refs/component-patterns.md).
5. **Wire References**: Connect cross-stack outputs using parameterized `StackReference` per [refs/stack-references.md](refs/stack-references.md).
6. **Secure**: Apply IAM least-privilege, encryption, network isolation per [refs/security-checklist.md](refs/security-checklist.md).
7. **Name**: Use auto-naming by default, kebab-case logical names per [refs/naming-conventions.md](refs/naming-conventions.md).
8. **Export**: Register structured outputs for downstream consumers.
9. **Validate**: Run `pulumi preview` — zero errors before completion.

---

## Decision Tree

```
Implementation Request
├─► New project? ──► Scaffold full structure (Pulumi.yaml, __main__.py, components/)
├─► New component?
│   ├─► 2+ resources? ──► ComponentResource class
│   └─► Single resource? ──► Factory function
├─► Cross-stack data?
│   ├─► Same team/lifecycle? ──► Same stack
│   └─► Different team/lifecycle? ──► StackReference (parameterized)
├─► Explicit name needed?
│   ├─► DNS/import/external? ──► Explicit + delete_before_replace
│   └─► Otherwise? ──► Auto-naming (default)
└─► Stateful resource? ──► protect=True + retain_on_delete + deletion_protection
```

---

### ComponentResource Anatomy (Mandatory Pattern)







Every component MUST follow this structure:

```python
import pulumi
from dataclasses import dataclass

@dataclass
class MyComponentArgs:
    """Typed arguments — use pulumi.Input[] for resource references."""
    name_field: pulumi.Input[str]
    optional_field: pulumi.Input[str] = "default"

class MyComponent(pulumi.ComponentResource):
    """Docstring: what this groups and why."""

    # Declare output type annotations
    primary_id: pulumi.Output[str]
    primary_arn: pulumi.Output[str]

    def __init__(
        self,
        name: str,
        args: MyComponentArgs,
        opts: pulumi.ResourceOptions | None = None,
    ) -> None:
        # 1. Super with three-part type string: "<org>:<module>:<Type>"
        super().__init__("acmecorp:module:MyComponent", name, None, opts)

        # 2. Child opts — always parent=self
        child_opts = pulumi.ResourceOptions(parent=self)

        # 3. Create resources with f"{name}-<suffix>" logical names
        self.primary = aws.some.Resource(
            f"{name}-primary",
            opts=child_opts,
        )

        # 4. Expose outputs as instance attributes
        self.primary_id = self.primary.id
        self.primary_arn = self.primary.arn

        # 5. ALWAYS register outputs — never skip
        self.register_outputs({

            "primary_id": self.primary_id,

            "primary_arn": self.primary_arn,

        })


```





### Naming Rules



- **Logical names**: kebab-case, descriptive of purpose (`"orders-api"` not `"api"`)
- **Auto-naming**: Always use unless explicit name is required (DNS, import, external ref)


- **Explicit names**: MUST set `delete_before_replace=True` in `ResourceOptions`
- **Component children**: Prefix with parent name (`f"{name}-task"`, `f"{name}-logs"`)



### Security Defaults (Apply to Every Resource)


- **S3**: Encryption + public access block + versioning
- **RDS**: `storage_encrypted=True`, `publicly_accessible=False`, `deletion_protection=True`
- **IAM**: Specific actions, specific resources, conditions where possible — never `"*"/"*"`

- **Security Groups**: Named ports, specific CIDRs, description on every rule
- **Stateful resources**: `protect=True` in ResourceOptions
- **CI/CD**: OIDC authentication — never long-lived credentials


- **State**: KMS encryption — never passphrase in production

### Configuration Management


```python
import pulumi

config = pulumi.Config()

stack = pulumi.get_stack()

# Required values — fail fast
db_instance_class = config.require("dbInstanceClass")



# Optional with defaults
replica_count = config.get_int("replicaCount") or 2



# Secrets — automatically encrypted in state
db_password = config.require_secret("dbPassword")

# Structured config


network_config = config.require_object("network")

```

### Stack References (Parameterized)


```python

config = pulumi.Config()
stack = pulumi.get_stack()


infra_ref = pulumi.StackReference(
    f"{config.get('infraOrg') or pulumi.get_organization()}"

    f"/{config.require('infraProject')}"
    f"/{config.get('infraStack') or stack}"
)



vpc_id = infra_ref.require_output("network").apply(lambda n: n["vpc_id"])

```

### Output Exports (Structured)


```python
# Group related outputs by domain


pulumi.export("network", {
    "vpc_id": vpc.id,
    "private_subnet_ids": [s.id for s in private_subnets],
})


pulumi.export("database", {


    "endpoint": db.endpoint,
    "port": db.port,
})
```


### Tagging (All Taggable Resources)


```python
default_tags = {

    "Environment": pulumi.get_stack(),
    "Project": pulumi.get_project(),

    "ManagedBy": "pulumi",
}


# Apply via provider default_tags or per-resource
provider = aws.Provider("aws-provider",

    default_tags=aws.ProviderDefaultTagsArgs(tags=default_tags),
)

```



---

## Patterns & Anti-Patterns


### ✅ Do

- Scaffold from design artifacts — never start from scratch without an ADR

- Use `dataclass` for component args — typed, documented, IDE-friendly

- Use `pulumi.ResourceOptions(parent=self)` on every child resource
- Call `register_outputs()` on every ComponentResource
- Use `require_output()` for mandatory cross-stack values

- Use provider `default_tags` for organization-wide tagging

- Put orchestration in `__main__.py`, logic in `components/`
- Run `pulumi preview` before declaring implementation complete


### ❌ Don't

- Create child resources without `parent=self` — breaks resource tree visibility
- Skip `register_outputs()` — breaks Pulumi Console and downstream references
- Hardcode stack reference paths — use config-driven parameterization

- Use `"*"` in IAM actions or resources — always scope to specific ARNs

- Use passphrase encryption for production state — use KMS
- Export entire resource objects — export only the specific values consumers need
- Put business logic in `__main__.py` — keep it to wiring and orchestration

- Use PascalCase or snake_case for logical names — use kebab-case

---

## Skill Chaining



| Condition                          | Invoke             | Handoff Context                              |
|------------------------------------|--------------------|----------------------------------------------|
| No design artifacts exist          | `design/pulumi`    | Requirements, constraints, environment list   |

| Implementation complete            | `review/pulumi`    | Stack URNs, preview output, security posture  |
| Components need unit tests         | `test/unit`        | Component classes, expected outputs           |
| Monitoring resources created       | `observe/metrics`  | Resource ARNs, dashboard requirements         |

### Chaining Syntax

```markdown

**Invoking Sub-Skill:** `review/pulumi`
**Reason:** Implementation complete, preview passes
**Handoff Context:**

- Stack: acmecorp/app-service/dev
- Components: SecureBucket, FargateService
- Preview: 12 resources to create, 0 errors
```

---


## Quality Gates

Before marking implementation complete:

- [ ] Design artifacts (ADR, stack map) referenced and followed
- [ ] `pulumi preview` succeeds with zero errors
- [ ] All ComponentResources call `register_outputs()`
- [ ] All child resources have `parent=self`
- [ ] Logical names are kebab-case and descriptive
- [ ] Auto-naming used unless explicit name justified
- [ ] Explicit names have `delete_before_replace=True`

- [ ] IAM policies use specific actions and resource ARNs
- [ ] Stateful resources have `protect=True`
- [ ] S3 buckets have encryption + public access block
- [ ] Stack references are parameterized via config
- [ ] Outputs are structured by domain
- [ ] Tags include Environment, Project, ManagedBy
- [ ] No secrets in stack config files (use `config.require_secret`)

---

## Deep References

Load these refs as needed for detailed guidance:

- **[component-patterns.md](refs/component-patterns.md)**: ComponentResource anatomy, type strings, output registration, testing
- **[naming-conventions.md](refs/naming-conventions.md)**: Auto-naming config, explicit naming risks, naming utilities, refactoring with aliases
- **[security-checklist.md](refs/security-checklist.md)**: OIDC setup, IAM patterns, network security, CrossGuard policies, resource protection
- **[stack-references.md](refs/stack-references.md)**: Parameterized references, structured exports, multi-region/account patterns, dependency management
