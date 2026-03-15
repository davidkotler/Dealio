# Security Checklist for Pulumi Infrastructure

## Pre-Implementation Security Design

### Authentication & Secrets

| Requirement | Decision | Implementation |
|-------------|----------|----------------|
| CI/CD Authentication | OIDC (no long-lived creds) | AWS IAM OIDC Provider |
| Developer Authentication | Pulumi Cloud SSO | SAML/OIDC federation |
| State Encryption | AWS KMS | `--secrets-provider awskms://` |
| Secrets Management | Pulumi ESC | Dynamic credentials via OIDC |
| Application Secrets | AWS Secrets Manager | Rotation enabled |

---

## OIDC Configuration

### Pulumi Cloud OIDC Trust Policy

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {
      "Federated": "arn:aws:iam::ACCOUNT_ID:oidc-provider/api.pulumi.com/oidc"
    },
    "Action": "sts:AssumeRoleWithWebIdentity",
    "Condition": {
      "StringEquals": {
        "api.pulumi.com/oidc:aud": "YOUR_PULUMI_ORG"
      },
      "StringLike": {
        "api.pulumi.com/oidc:sub": "pulumi:deploy:org:YOUR_ORG:project:*:*"
      }
    }
  }]
}
```

### GitHub Actions OIDC Trust Policy

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {
      "Federated": "arn:aws:iam::ACCOUNT_ID:oidc-provider/token.actions.githubusercontent.com"
    },
    "Action": "sts:AssumeRoleWithWebIdentity",
    "Condition": {
      "StringEquals": {
        "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
      },
      "StringLike": {
        "token.actions.githubusercontent.com:sub": "repo:YOUR_ORG/YOUR_REPO:*"
      }
    }
  }]
}
```

---

## IAM Best Practices

### Least Privilege Pattern

```python
# ✅ Specific permissions
policy = aws.iam.Policy("app-policy",
    policy=json.dumps({
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:PutObject",
            ],
            "Resource": [
                bucket.arn.apply(lambda arn: f"{arn}/*"),
            ],
            "Condition": {
                "StringEquals": {
                    "s3:x-amz-server-side-encryption": "AES256"
                }
            }
        }]
    })
)

# ❌ Overly permissive
policy = aws.iam.Policy("bad-policy",
    policy=json.dumps({
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Action": "s3:*",
            "Resource": "*"
        }]
    })
)
```

### Service-Linked Roles

```python
# Use AWS-managed service-linked roles when available
ecs_task_role = aws.iam.Role("ecs-task-role",
    assume_role_policy=json.dumps({
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"Service": "ecs-tasks.amazonaws.com"},
            "Action": "sts:AssumeRole"
        }]
    })
)
```

---

## Network Security

### VPC Design Checklist







- [ ] Private subnets for workloads (no public IPs)
- [ ] Public subnets only for load balancers and bastion
- [ ] NAT Gateway for outbound internet access
- [ ] VPC Flow Logs enabled
- [ ] Network ACLs as secondary defense

### Security Group Patterns

```python
# ✅ Specific CIDR, specific ports
app_sg = aws.ec2.SecurityGroup("app-sg",
    vpc_id=vpc.id,
    ingress=[{
        "protocol": "tcp",
        "from_port": 443,
        "to_port": 443,
        "cidr_blocks": ["10.0.0.0/8"],  # Internal only
        "description": "HTTPS from internal network"
    }],
    egress=[{
        "protocol": "tcp",
        "from_port": 443,
        "to_port": 443,
        "cidr_blocks": ["0.0.0.0/0"],
        "description": "HTTPS to internet"
    }]
)

# ❌ Overly permissive
bad_sg = aws.ec2.SecurityGroup("bad-sg",
    vpc_id=vpc.id,
    ingress=[{
        "protocol": "-1",
        "from_port": 0,
        "to_port": 0,
        "cidr_blocks": ["0.0.0.0/0"]  # Open to world!
    }]
)
```

---

## Data Protection

### S3 Bucket Security

```python
bucket = aws.s3.BucketV2("secure-bucket")

# Encryption at rest
aws.s3.BucketServerSideEncryptionConfigurationV2("bucket-encryption",
    bucket=bucket.id,
    rules=[{
        "apply_server_side_encryption_by_default": {
            "sse_algorithm": "aws:kms",
            "kms_master_key_id": kms_key.arn
        },
        "bucket_key_enabled": True
    }]
)

# Block public access
aws.s3.BucketPublicAccessBlock("bucket-public-block",
    bucket=bucket.id,
    block_public_acls=True,
    block_public_policy=True,
    ignore_public_acls=True,
    restrict_public_buckets=True
)

# Versioning for data protection
aws.s3.BucketVersioningV2("bucket-versioning",
    bucket=bucket.id,
    versioning_configuration={"status": "Enabled"}
)
```

### RDS Security

```python
db = aws.rds.Instance("database",
    # Encryption
    storage_encrypted=True,
    kms_key_id=kms_key.arn,

    # Network isolation
    publicly_accessible=False,
    vpc_security_group_ids=[db_sg.id],
    db_subnet_group_name=subnet_group.name,

    # Authentication
    iam_database_authentication_enabled=True,

    # Audit logging
    enabled_cloudwatch_logs_exports=["postgresql", "upgrade"],

    # Deletion protection
    deletion_protection=True,

    opts=pulumi.ResourceOptions(protect=True)
)
```

---

## CrossGuard Security Policies

### Required Policies

```python
from pulumi_policy import PolicyPack, ResourceValidationPolicy, EnforcementLevel

def deny_public_s3(args, report_violation):
    if args.resource_type == "aws:s3/bucket:Bucket":
        acl = args.props.get("acl")
        if acl in ["public-read", "public-read-write"]:
            report_violation("S3 buckets must not have public ACLs")

def require_encryption(args, report_violation):
    if args.resource_type == "aws:s3/bucket:Bucket":
        # Check encryption config exists
        pass
    if args.resource_type == "aws:rds/instance:Instance":
        if not args.props.get("storageEncrypted"):
            report_violation("RDS instances must have storage encryption enabled")

def deny_public_rds(args, report_violation):
    if args.resource_type == "aws:rds/instance:Instance":
        if args.props.get("publiclyAccessible"):
            report_violation("RDS instances must not be publicly accessible")

def require_tags(args, report_violation):
    required = ["Environment", "Project", "ManagedBy", "CostCenter"]
    tags = args.props.get("tags", {})
    for tag in required:
        if tag not in tags:
            report_violation(f"Missing required tag: {tag}")

PolicyPack("security-baseline", policies=[
    ResourceValidationPolicy(
        name="deny-public-s3",
        enforcement_level=EnforcementLevel.MANDATORY,
        validate=deny_public_s3
    ),
    ResourceValidationPolicy(
        name="require-encryption",
        enforcement_level=EnforcementLevel.MANDATORY,
        validate=require_encryption
    ),
    ResourceValidationPolicy(
        name="deny-public-rds",
        enforcement_level=EnforcementLevel.MANDATORY,
        validate=deny_public_rds
    ),
    ResourceValidationPolicy(
        name="require-tags",
        enforcement_level=EnforcementLevel.ADVISORY,
        validate=require_tags
    ),
])
```

---

## Resource Protection

### Critical Resources

```python
# Protect stateful resources from accidental deletion
database = aws.rds.Instance("production-db",
    deletion_protection=True,               # AWS-level protection
    skip_final_snapshot=False,
    final_snapshot_identifier="prod-db-final",
    opts=pulumi.ResourceOptions(
        protect=True                        # Pulumi-level protection
    )
)

# Protect state bucket
state_bucket = aws.s3.BucketV2("pulumi-state",
    opts=pulumi.ResourceOptions(
        protect=True,
        retain_on_delete=True               # Keep even if removed from code
    )
)
```



---




## Security Design Review Checklist






### Authentication & Authorization



- [ ] No long-lived credentials in CI/CD
- [ ] OIDC configured for all automated access



- [ ] IAM roles follow least privilege
- [ ] Service accounts have bounded permissions





### Network Security




- [ ] Workloads in private subnets
- [ ] Security groups allow only required traffic

- [ ] VPC Flow Logs enabled


- [ ] No 0.0.0.0/0 ingress rules (except ALB on 443)


### Data Protection


- [ ] All storage encrypted at rest (S3, RDS, EBS)
- [ ] KMS keys with proper key policies

- [ ] S3 buckets block public access

- [ ] Database credentials in Secrets Manager

### Operational Security

- [ ] CloudTrail enabled for API auditing

- [ ] GuardDuty enabled for threat detection
- [ ] Config rules for compliance monitoring
- [ ] Critical resources have `protect=True`

### State & Secrets

- [ ] State encrypted with KMS (not passphrase)
- [ ] Secrets use Pulumi ESC or Secrets Manager
- [ ] State bucket versioned for recovery
- [ ] No secrets in stack configuration files
