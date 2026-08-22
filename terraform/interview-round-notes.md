# Interview Round Notes

Topics that come up again and again in Terraform interview rounds, with short answers.

---

## 1. Drift detection and backups

### Drift

Drift means the real infrastructure is different from what the code says. Usually someone changed it in the console.

### How to detect it

```bash
terraform plan -detailed-exitcode
# 0 = no change, 1 = error, 2 = drift
```

Run it nightly in the pipeline and alert on exit code 2. Terraform Cloud has built-in drift detection, and `driftctl` is another option.

### In a team

- Remote backend with locking, so nobody works from a private copy
- All changes through the pipeline, no console edits
- Scheduled drift scans with alerts

### Backups

- Turn on bucket versioning or soft delete for the state file
- Encrypt with a managed key and restrict access
- Never keep state in Git
- Test the restore before you need it

---

## 2. `terraform refresh` vs `terraform plan`

| `terraform refresh` | `terraform plan` |
|---|---|
| Updates state to match reality | Shows the difference between code and reality |
| Changes the state file | Changes nothing |
| Standalone command is deprecated | Runs a refresh internally, then shows the diff |

Modern replacement:

```bash
terraform plan -refresh-only     # review the drift
terraform apply -refresh-only    # record it in state, no infrastructure change
```

### Interview answer

"Refresh updates the state file to match the real world; plan shows what apply would do. Plan refreshes in memory first and then shows the difference, without changing anything. The standalone refresh command is deprecated, so I use `plan -refresh-only` to review drift and `apply -refresh-only` when I want to record it in state."

---

## 3. Structuring a large Terraform project

### Layout

```text
modules/
  network/
  compute/
  database/
environments/
  dev/     main.tf  backend.tf  dev.tfvars
  staging/ main.tf  backend.tf  staging.tfvars
  prod/    main.tf  backend.tf  prod.tfvars
```

### Rules

1. Modules hold the logic. Root configs stay thin and just call modules.
2. Version the modules and pin the version in each environment.
3. Separate state per environment, and per layer when the project is big.
4. Layer the state: network, platform, data, application. Smaller blast radius.
5. Pin provider versions and commit the lock file.
6. Run `fmt`, `validate`, `tflint`, and a security scan in CI.

### Workspaces or folders?

Workspaces are fine for short-lived or nearly identical copies. For long-lived dev, staging, and production, separate folders are clearer, because the credentials, backend, and approvals are visible.

---

## 4. State locking and avoiding conflicts

1. Use a backend that supports locking: S3 with a lock file, Azure Storage blob lease, GCS, or Terraform Cloud.
2. Terraform takes the lock during plan and apply and releases it at the end.
3. A second run waits or fails instead of corrupting state.
4. Enable versioning and encryption for recovery.
5. Restrict who may run `force-unlock`.
6. Run applies from CI only, so changes are serialized.

### Stuck lock

Check the lock owner and the pipeline first. Only when nothing is running:

```bash
terraform force-unlock <LOCK_ID>
```

---

## 5. Testing before production

| Stage | What runs |
|---|---|
| Static | `terraform fmt -check`, `terraform validate`, `tflint` |
| Security | `tfsec`, `checkov`, or Trivy |
| Plan review | Plan on every pull request, reviewed by a person |
| Policy | OPA or Sentinel rules, for example no public storage |
| Tests | `terraform test` or Terratest against a sandbox |
| Promotion | Apply in dev, then staging, then production with approval |

---

## 6. Design a module for a multi-tier app

### Structure

```text
modules/
  network/    VPC, public/private/db subnets, routes, NAT, internet gateway
  compute/    autoscaling group or cluster for the app tier
  data/       database with multi-AZ, cache, subnet groups
  security/   security groups and IAM
environments/
  prod/       main.tf (calls the modules), backend.tf, prod.tfvars
```

### Key points to mention

1. **Remote state:** encrypted, versioned, locked, one state per environment.
2. **Layered state:** network, application, and data separately, so a mistake has a smaller blast radius.
3. **Wiring:** module outputs inside a root config, or `terraform_remote_state` between layers.
4. **Inputs and outputs:** CIDRs, instance sizes, and counts as inputs; VPC ID, subnet IDs, and endpoints as outputs.
5. **Tiers:** load balancer in the public tier, application in private subnets, database with no public route.
6. **Security groups reference each other**, not raw CIDR ranges.
7. Pin versions, tag everything, and run security scans in CI.

### Example wiring

```hcl
module "network" {
  source = "../../modules/network"
  cidr   = var.vpc_cidr
}

module "data" {
  source     = "../../modules/data"
  subnet_ids = module.network.db_subnet_ids
}

module "compute" {
  source        = "../../modules/compute"
  subnet_ids    = module.network.private_subnet_ids
  db_endpoint   = module.data.endpoint
}
```
