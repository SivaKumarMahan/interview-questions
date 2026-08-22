# Terraform Notes

Short revision notes. One topic per section, with the key points and a small example.

---

## 1. Zero downtime deployments

### Ways to do it

1. **Create before destroy** — bring the new resource up first.
2. **Rolling update** — replace a few instances at a time.
3. **Blue-green** — build a second stack, switch traffic, delete the old one.
4. **Load balancer + health checks** — no traffic until the new instance is healthy.
5. **Test in a lower environment first.**

### Example

```hcl
resource "aws_autoscaling_group" "web" {
  instance_refresh {
    strategy = "Rolling"

    preferences {
      min_healthy_percentage = 90
    }
  }
}
```

### Remember

Databases need their own plan: replica promotion, backups, and a backward-compatible migration.

---

## 2. State file best practices

1. Remote backend, never a local file for team work.
2. Locking on.
3. Encryption at rest and in transit.
4. Versioning or soft delete for recovery.
5. One state key per environment and component.
6. Only the pipeline writes to production state.
7. Never commit state to Git.
8. Treat state as sensitive; it can contain secret values.

```hcl
terraform {
  backend "s3" {
    bucket       = "my-tf-state"
    key          = "prod/app/terraform.tfstate"
    region       = "us-east-1"
    encrypt      = true
    use_lockfile = true
  }
}
```

---

## 3. Testing Terraform code

| Check | Command | Catches |
|---|---|---|
| Format | `terraform fmt -check` | Style |
| Syntax | `terraform validate` | Bad references, missing arguments |
| Lint | `tflint` | Bad instance types, unused variables |
| Security | `tfsec .` / `checkov -d .` | Public buckets, missing encryption |
| Drift | `terraform plan -detailed-exitcode` | Manual changes |
| Unit test | `terraform test` / Terratest | Module actually works |
| Policy | OPA / Conftest / Sentinel | Company rules |

### Native test example

```hcl
# tests/vpc.tftest.hcl
run "vpc_cidr_is_correct" {
  command = plan

  assert {
    condition     = aws_vpc.main.cidr_block == "10.0.0.0/16"
    error_message = "Wrong CIDR"
  }
}
```

---

## 4. Secrets management

### Rules

1. Never hardcode a secret in `.tf` or in a `.tfvars` file that is committed.
2. Read secrets from Vault, Key Vault, or Secrets Manager at run time.
3. Mark variables and outputs `sensitive`.
4. Encrypt state and restrict read access.
5. Rotate secrets regularly.
6. Best of all: let the application read the secret at runtime with a managed identity, so Terraform never touches it.

### Example

```hcl
data "azurerm_key_vault_secret" "db" {
  name         = "db-password"
  key_vault_id = var.key_vault_id
}
```

### Remember

`sensitive = true` hides the value in CLI output only. The value can still be in state.

---

## 5. Performance on large infrastructure

| Problem | Fix |
|---|---|
| One huge state | Split by component and environment |
| Slow refresh | Fewer resources per state |
| Broad data sources | Pass IDs in as variables |
| Provider download every run | Cache or mirror providers in CI |
| API throttling | Lower `-parallelism`, enable provider retries |
| Extra `depends_on` | Remove it, let Terraform infer |

Avoid using `-target` as a normal habit. It gives an incomplete plan.

---

## 6. Multi-cloud

1. One provider block per cloud, with aliases for extra regions or accounts.
2. Provider-specific modules. Do not force AWS and Azure into one generic module.
3. Separate state per cloud, account, environment, and region.
4. Separate identity and pipeline stage per cloud.
5. Share the standards: naming, tags, policy checks.

```hcl
provider "aws" {
  region = "us-east-1"
}

provider "azurerm" {
  features {}
}
```

---

## 7. Resource dependencies

### Implicit (preferred)

Terraform works out the order from references:

```hcl
resource "aws_instance" "app" {
  subnet_id = aws_subnet.private.id   # app waits for the subnet
}
```

### Explicit

Only when there is no reference to infer from:

```hcl
resource "aws_instance" "app" {
  depends_on = [aws_iam_role_policy_attachment.app]
}
```

### Tips

- Too many `depends_on` blocks slow the apply down and can cause cycles.
- `terraform graph | dot -Tsvg > graph.svg` shows the dependency graph.

---

## 8. Versioning modules and providers

```hcl
terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.40"
    }
  }
}

module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "5.8.1"
}
```

### Rules

1. Pin versions in root modules and commit `.terraform.lock.hcl`.
2. Use semantic versioning for your own modules.
3. Upgrade in a dedicated pull request after reading the release notes.
4. Test the upgrade in a lower environment first.
5. Keep a changelog for your modules.

---

## 9. Infrastructure as Code principles

| Principle | What it means |
|---|---|
| Declarative | Describe the end state, not the steps |
| Version controlled | All code in Git, reviewed through pull requests |
| Modular | Reusable components with inputs and outputs |
| Automated | The pipeline applies changes, not a laptop |
| Idempotent | Running twice produces the same result |
| Documented | README, examples, and clear variables |
| Tested | Validate, scan, plan, and test before apply |

---

## 10. Drift detection and fixing

### Detect

```bash
terraform plan -detailed-exitcode
# 0 = no change, 1 = error, 2 = drift
```

### Fix

| Case | Action |
|---|---|
| Manual change should stay | Update the code, then apply |
| Manual change was wrong | Approved apply restores the code value |
| Resource not managed at all | `terraform import` |

### Prevent

Read-only console access, policy checks, and a break-glass process where the change must be put back into code afterwards.

---

## 11. Managing multiple environments

```text
modules/                shared code
environments/
  dev/    backend.tf  dev.tfvars
  test/   backend.tf  test.tfvars
  prod/   backend.tf  prod.tfvars
```

1. Separate backend key per environment.
2. Separate credentials and approvals.
3. Same module version, different values.
4. Consistent naming, for example `app-dev-vpc` and `app-prod-vpc`.
5. The pipeline picks the folder, so a job cannot mix dev code with prod credentials.

---

## 12. Provider compatibility

1. Pin with `~>` so patch updates come in but major versions do not.
2. Commit the lock file so CI and laptops match.
3. `terraform providers` shows which module requires which provider.
4. Read the release notes before upgrading; providers do have breaking changes.
5. Never delete the lock file just to make CI pass.

---

## 13. Tagging and labelling

### Set defaults once

```hcl
provider "aws" {
  default_tags {
    tags = {
      Environment = var.environment
      Owner       = var.owner
      CostCenter  = var.cost_center
      ManagedBy   = "terraform"
    }
  }
}
```

### Or merge in a module

```hcl
locals {
  tags = merge(var.common_tags, {
    Component = "database"
  })
}
```

### Why it matters

Tags drive cost reports, ownership, automated cleanup, and compliance checks. Enforce them with variable validation and a policy check.

---

## 14. Module versioning and updates

1. Tag releases: `v1.0.0`, `v1.1.0`, `v2.0.0`.
2. Consumers pin a version.
3. Patch = bug fix, minor = new optional input, major = breaking change.
4. A major version needs a migration note.
5. Test the new version in dev before other teams adopt it.

```hcl
module "vpc" {
  source  = "git::https://github.com/myorg/tf-modules.git//vpc?ref=v1.4.0"
}
```

---

## 15. Monitoring and logging

1. Create the alarms and dashboards in Terraform along with the resource, so nothing ships unmonitored.
2. Enable cloud logging: CloudTrail, Azure Activity Log, GCP Audit Logs.
3. Alert on drift job results and failed applies.
4. Send apply summaries to the team channel.

```hcl
resource "aws_cloudwatch_metric_alarm" "cpu" {
  alarm_name          = "web-high-cpu"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EC2"
  comparison_operator = "GreaterThanThreshold"
  threshold           = 80
  evaluation_periods  = 2
  period              = 300
  statistic           = "Average"
  alarm_actions       = [aws_sns_topic.alerts.arn]
}
```

---

## 16. Drift in a team environment

1. Shared remote state with locking, so nobody works from a private copy.
2. All applies from the pipeline.
3. Nightly drift plan for every environment.
4. Cloud audit logs to identify who changed what.
5. Agreed process for emergency changes.

The technical controls matter, but so does the agreement that nobody edits production by hand.

---

## 17. Blue-green and canary rollouts

### Blue-green

1. Build a complete second stack (green) beside the live one (blue).
2. Test green privately.
3. Switch the load balancer or DNS to green.
4. Keep blue for the rollback window, then destroy it.

### Canary

1. Send a small percentage of traffic to the new version.
2. Watch error rate and latency.
3. Increase gradually, or roll back quickly.

### With Terraform

Terraform builds both stacks and the routing. The traffic percentage is usually driven by a weighted target group, weighted DNS record, or a service mesh, and changed through the pipeline.

---

## 18. Idempotency and avoiding re-creation

### Causes of unwanted recreation

| Cause | Fix |
|---|---|
| `timestamp()` or `uuid()` in a name | Use a stable name |
| Changing an immutable field | Check the provider docs first |
| Switching `count` to `for_each` | Use `moved` blocks |
| Another tool changing a field | Narrow `ignore_changes` |
| Renaming a resource in code | Use a `moved` block, not a rename |

### Habit

Always read the plan for `forces replacement` before approving.

---

## 19. Cost management

1. Right-size in dev: small instances, one node, short backup retention.
2. Turn dev off outside working hours.
3. Use spot or preemptible instances for non-critical workloads.
4. Tag everything for cost allocation.
5. Create budgets and alerts in Terraform.
6. Run a cost estimate in the pipeline, for example with Infracost.

```hcl
variable "instance_type" {
  type = map(string)

  default = {
    dev  = "t3.small"
    prod = "m6i.large"
  }
}
```

---

## 20. Changing autoscaling groups and load balancers without downtime

1. A new launch template version does not replace running instances by itself.
2. Use instance refresh with a minimum healthy percentage to roll them gradually.
3. Keep health checks strict so bad instances never receive traffic.
4. Use connection draining (deregistration delay) so in-flight requests finish.
5. For load balancer changes, add the new listener or target group before removing the old one.

```hcl
resource "aws_lb_target_group" "web" {
  deregistration_delay = 30
}
```

---

## 21. Refactoring a monolithic repo into modules

### Steps

1. Find the repeated blocks: network, compute, database.
2. Create a module for each, with clear inputs and outputs.
3. Restructure the folders:

```text
modules/
environments/dev/
environments/prod/
```

4. Move resources with `moved` blocks so nothing is destroyed.
5. Do it in small pull requests, one component at a time.
6. Each step must plan clean before the next one.
7. Update the pipeline and the documentation.

### Safety check

```bash
terraform show -json tfplan | jq -r '.resource_changes[] | select(.change.actions[] == "delete") | .address'
```

If that prints anything unexpected, stop.

---

## 22. Cross-region dependencies

1. Use provider aliases for each region.
2. Keep separate state per region.
3. Pass values between regions as variables, or read them from remote state.
4. Deploy in a defined order through the pipeline.

```hcl
provider "aws" {
  alias  = "dr"
  region = "us-west-2"
}

resource "aws_s3_bucket" "dr_backup" {
  provider = aws.dr
  bucket   = "app-backup-dr"
}
```

### Remember

Some services are global (IAM, Route 53, CloudFront). Keep those in one global stack instead of duplicating them per region.

---

## 23. Terraform with GitHub Actions on Azure

```yaml
name: terraform

on:
  pull_request:
  push:
    branches: [main]

permissions:
  id-token: write
  contents: read

jobs:
  terraform:
    runs-on: ubuntu-latest
    environment: production

    steps:
      - uses: actions/checkout@v4

      - uses: azure/login@v2
        with:
          client-id: ${{ secrets.AZURE_CLIENT_ID }}
          tenant-id: ${{ secrets.AZURE_TENANT_ID }}
          subscription-id: ${{ secrets.AZURE_SUBSCRIPTION_ID }}

      - uses: hashicorp/setup-terraform@v3

      - run: terraform init
      - run: terraform validate
      - run: terraform plan -out=tfplan

      - if: github.ref == 'refs/heads/main'
        run: terraform apply tfplan
```

### Points

- `id-token: write` enables OIDC, so no client secret is stored.
- State lives in an Azure Storage account, which locks with blob leases.
- The `environment` setting gives the approval gate.

---

## 24. State, replacement, and provisioners

### State

Keep it in an encrypted remote backend with locking, versioning, audit logs, and least-privilege access. Protect read access as strongly as write access.

### Replacement

`terraform taint` is deprecated. Use:

```bash
terraform apply -replace='module.app.aws_instance.web'
```

Check dependencies, data, downtime, and rollback before replacing anything.

### Provisioners

`local-exec`, `remote-exec`, and `file` are last-resort escape hatches, not a configuration management tool.

Problems with them:

- Hard to make idempotent
- Can fail after the resource is already created
- Errors are hard to recover from

Better options: cloud-init or user data, a pre-baked image, a managed service, Ansible, or a native provider resource.

---

## 25. CIDR basics

```text
10.0.0.0/16   = 65,536 addresses    (a whole VPC)
10.0.1.0/24   = 256 addresses       (a subnet)
10.0.1.0/28   = 16 addresses        (a small subnet)
```

The number after the slash is how many bits are fixed. The remaining bits are host addresses.

### Planning tips

1. Plan non-overlapping ranges across environments and clouds, or peering will fail later.
2. Leave room to grow. You cannot easily shrink or move a subnet afterwards.
3. Cloud providers reserve some addresses in every subnet, so the usable count is lower than the raw number. AWS reserves 5 per subnet.

### Useful function

```hcl
locals {
  subnets = [for i in range(3) : cidrsubnet("10.0.0.0/16", 8, i)]
  # 10.0.0.0/24, 10.0.1.0/24, 10.0.2.0/24
}
```
