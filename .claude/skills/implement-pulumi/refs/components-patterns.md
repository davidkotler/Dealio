# Component Resource Patterns

## When to Use Components vs Functions

### Use ComponentResource When

| Scenario | Rationale |
|----------|-----------|
| Grouping 2+ related resources | Logical grouping in resource tree |
| Need visibility in Pulumi Console | Components appear as expandable nodes |
| Enforcing organizational defaults | Encapsulate security/compliance patterns |
| Building reusable abstractions | Share across projects |
| Resources share lifecycle | Create/update/delete together |

### Use Functions When

| Scenario | Rationale |
|----------|-----------|
| Creating single resource with defaults | Simpler, less overhead |
| Helper utilities (naming, tagging) | No state tracking needed |
| Transforming inputs | Pure computation |
| One-off resource creation | Not intended for reuse |

---

## ComponentResource Anatomy

```python
import pulumi
from pulumi_aws import s3
from typing import Optional
from dataclasses import dataclass

@dataclass
class SecureBucketArgs:
    """Arguments for SecureBucket component."""
    bucket_name: pulumi.Input[str]
    versioning_enabled: pulumi.Input[bool] = True
    encryption_algorithm: pulumi.Input[str] = "AES256"
    log_bucket_id: Optional[pulumi.Input[str]] = None

class SecureBucket(pulumi.ComponentResource):
    """
    A secure S3 bucket with encryption, versioning, and public access blocking.
    Enforces organizational security defaults for S3 storage.
    """

    # Type annotations for outputs
    bucket: s3.BucketV2
    bucket_arn: pulumi.Output[str]
    bucket_name: pulumi.Output[str]

    def __init__(
        self,
        name: str,
        args: SecureBucketArgs,
        opts: Optional[pulumi.ResourceOptions] = None
    ):
        # 1. Always call super().__init__ with proper type string
        # Format: <organization>:<module>:<type>
        super().__init__("acmecorp:storage:SecureBucket", name, None, opts)

        # 2. Create child options with parent reference
        child_opts = pulumi.ResourceOptions(parent=self)

        # 3. Create the primary resource
        self.bucket = s3.BucketV2(
            f"{name}-bucket",
            bucket=args.bucket_name,
            opts=child_opts
        )

        # 4. Create related resources with parent chain
        s3.BucketVersioningV2(
            f"{name}-versioning",
            bucket=self.bucket.id,
            versioning_configuration=s3.BucketVersioningV2VersioningConfigurationArgs(
                status="Enabled" if args.versioning_enabled else "Suspended"
            ),
            opts=pulumi.ResourceOptions(parent=self.bucket)
        )

        s3.BucketServerSideEncryptionConfigurationV2(
            f"{name}-encryption",
            bucket=self.bucket.id,
            rules=[s3.BucketServerSideEncryptionConfigurationV2RuleArgs(
                apply_server_side_encryption_by_default=s3.BucketServerSideEncryptionConfigurationV2RuleApplyServerSideEncryptionByDefaultArgs(
                    sse_algorithm=args.encryption_algorithm
                )
            )],
            opts=pulumi.ResourceOptions(parent=self.bucket)
        )

        s3.BucketPublicAccessBlock(
            f"{name}-public-access-block",
            bucket=self.bucket.id,
            block_public_acls=True,
            block_public_policy=True,
            ignore_public_acls=True,
            restrict_public_buckets=True,
            opts=pulumi.ResourceOptions(parent=self.bucket)
        )

        # 5. Optional: Logging configuration
        if args.log_bucket_id:
            s3.BucketLoggingV2(
                f"{name}-logging",
                bucket=self.bucket.id,
                target_bucket=args.log_bucket_id,
                target_prefix=f"{name}/",
                opts=pulumi.ResourceOptions(parent=self.bucket)
            )

        # 6. Set output properties
        self.bucket_arn = self.bucket.arn
        self.bucket_name = self.bucket.bucket

        # 7. CRITICAL: Register all outputs
        self.register_outputs({
            "bucket_arn": self.bucket_arn,
            "bucket_name": self.bucket_name,
        })
```

---

## Type String Convention

Format: `<organization>:<module>:<type>`

| Organization | Module | Type | Full String |
|--------------|--------|------|-------------|
| acmecorp | storage | SecureBucket | `acmecorp:storage:SecureBucket` |
| acmecorp | compute | FargateService | `acmecorp:compute:FargateService` |
| acmecorp | network | VpcComponent | `acmecorp:network:VpcComponent` |
| acmecorp | data | AuroraCluster | `acmecorp:data:AuroraCluster` |

---

## Common Component Patterns

### 1. Network Foundation

```python
class VpcComponent(pulumi.ComponentResource):
    """VPC with public/private subnets across multiple AZs."""

    vpc: ec2.Vpc
    public_subnet_ids: pulumi.Output[list[str]]
    private_subnet_ids: pulumi.Output[list[str]]
    nat_gateway_ips: pulumi.Output[list[str]]
```

**Encapsulates:**







- VPC with DNS support
- Public subnets with internet gateway
- Private subnets with NAT gateways
- Route tables and associations

### 2. Database Cluster

```python
class AuroraClusterComponent(pulumi.ComponentResource):
    """Aurora PostgreSQL cluster with security defaults."""

    cluster: rds.Cluster

    cluster_endpoint: pulumi.Output[str]

    reader_endpoint: pulumi.Output[str]

    security_group_id: pulumi.Output[str]

```



**Encapsulates:**

- RDS cluster with encryption
- Subnet group
- Security group with restricted ingress
- Parameter group with tuned settings
- Enhanced monitoring

### 3. Container Service


```python

class FargateServiceComponent(pulumi.ComponentResource):
    """ECS Fargate service with ALB integration."""


    service: ecs.Service

    task_definition: ecs.TaskDefinition
    target_group_arn: pulumi.Output[str]

    service_url: pulumi.Output[str]
```


**Encapsulates:**

- Task definition with logging

- ECS service with capacity provider
- Target group and health checks
- IAM task role and execution role

- CloudWatch log group

### 4. Serverless Function


```python
class LambdaFunctionComponent(pulumi.ComponentResource):

    """Lambda function with VPC, tracing, and logging."""

    function: lambda_.Function

    function_arn: pulumi.Output[str]
    function_name: pulumi.Output[str]
    log_group_name: pulumi.Output[str]

```

**Encapsulates:**

- Lambda function with X-Ray tracing
- IAM execution role
- CloudWatch log group with retention
- VPC configuration (optional)
- Dead letter queue (optional)

---

## Resource Options Passthrough

Always accept and use `ResourceOptions`:

```python
class MyComponent(pulumi.ComponentResource):
    def __init__(
        self,
        name: str,
        args: MyComponentArgs,
        opts: Optional[pulumi.ResourceOptions] = None
    ):
        super().__init__("org:module:MyComponent", name, None, opts)

        # Inherit from component opts but override parent
        child_opts = pulumi.ResourceOptions(
            parent=self,
            # Inherit other options from component
            provider=opts.provider if opts else None,
            depends_on=opts.depends_on if opts else None,
        )
```

---

## Output Registration Patterns

### Minimal Outputs

```python
self.register_outputs({
    "id": self.primary_resource.id,
    "arn": self.primary_resource.arn,
})
```

### Structured Outputs

```python
self.register_outputs({
    "primary": {
        "id": self.primary.id,
        "arn": self.primary.arn,
    },
    "security": {
        "security_group_id": self.sg.id,
        "kms_key_arn": self.key.arn,
    },
    "endpoints": {
        "primary": self.primary_endpoint,
        "reader": self.reader_endpoint,
    },
})
```

---

## Anti-Patterns to Avoid

### ❌ Missing Parent Reference

```python
# WRONG: Child resources not parented
self.bucket = s3.Bucket(f"{name}-bucket")  # No parent!
```

### ❌ Missing Output Registration

```python
# WRONG: Outputs not registered
self.bucket_arn = self.bucket.arn
# Missing: self.register_outputs(...)
```

### ❌ Hardcoded Names

```python
# WRONG: Hardcoded resource name
self.bucket = s3.Bucket("my-bucket", bucket="hardcoded-name")
```

### ❌ Wrong Type String Format

```python
# WRONG: Invalid type string
super().__init__("SecureBucket", name, None, opts)  # Missing org:module
```

---

## Testing Components

```python
import unittest
import pulumi

class ComponentMocks(pulumi.runtime.Mocks):
    def new_resource(self, args):
        return [f"{args.name}-id", args.inputs]

    def call(self, args):
        return {}

pulumi.runtime.set_mocks(ComponentMocks())

class TestSecureBucket(unittest.TestCase):
    @pulumi.runtime.test
    def test_creates_bucket_with_encryption(self):
        from components.secure_bucket import SecureBucket, SecureBucketArgs

        bucket = SecureBucket("test", SecureBucketArgs(
            bucket_name="test-bucket"
        ))

        def check_arn(arn):
            self.assertIsNotNone(arn)

        bucket.bucket_arn.apply(check_arn)
```
