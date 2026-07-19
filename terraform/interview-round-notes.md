# Scenario-Based Interview Notes

> Distributed from the former cross-topic scenario notes. Section numbering is retained where useful for interview practice.

## Terraform & Infrastructure as Code

### 6.1 Drift detection (incl. in a team environment) & backup strategy
- **Drift** = real infrastructure differs from the Terraform state/config (someone changed it manually).
- **Detect:** `terraform plan` (shows diffs), `terraform plan -detailed-exitcode` in CI (exit code 2 = drift) run on a schedule; tools like `driftctl`, or Terraform Cloud/Enterprise drift detection.
- **Team environment:** use a **remote backend with state locking** (S3 + DynamoDB, or Terraform Cloud) so no two runs clobber state; enforce changes only through the pipeline (no manual console changes); scheduled drift scans that alert.
- **Backups:** enable **S3 versioning** on the state bucket (point-in-time restore), restrict access via IAM + encryption (SSE-KMS), and keep state out of Git. Terraform Cloud keeps state history automatically.

### 6.2 `terraform refresh` vs `terraform plan`
- **`terraform refresh`** (now folded into `plan`/`apply` as the refresh step; standalone command deprecated): updates the **state file** to match real-world resources — it reconciles state with actual infra but does **not** change infra or config.
- **`terraform plan`:** computes and shows the **diff** between desired config and current state (it refreshes state first, then diffs). It makes **no changes**.
- Key point: refresh mutates state to reality; plan shows what apply *would* do. Modern Terraform: use `terraform plan -refresh-only` to preview state reconciliation.

### 6.3 Structuring large Terraform projects (workspaces & modules) / organizing code & multiple environments
- **Modules:** encapsulate reusable components (network, eks, rds) with clear inputs/outputs; version them (registry/Git tags). Keep root configs thin, composing modules.
- **Environments:** prefer **separate directories/state per environment** (`envs/dev`, `envs/staging`, `envs/prod`) with their own backend/tfvars — clearer blast radius and permissions than workspaces.
- **Workspaces:** useful for near-identical, low-risk variations sharing one config/backend, but they hide differences behind `terraform.workspace` and share a backend — I avoid them for prod separation.
- **Best practices:** remote state per env, DRY via modules, pin provider/module versions, use `tflint`/`terraform validate`/`fmt`, layer state (network vs app) to reduce blast radius, and drive everything through CI with plan-on-PR + apply-on-merge.

### 6.4 State locking & avoiding conflicts in remote backends
- Use a backend that supports locking: **S3 + DynamoDB** table (the lock item prevents concurrent applies), Terraform Cloud, or GCS.
- Terraform acquires the lock on `plan`/`apply` and releases it after; concurrent runs wait or fail fast rather than corrupting state.
- Enable **S3 versioning + encryption** for recovery; restrict who can `force-unlock`. Run applies only from CI to serialize changes.

### 6.5 Testing Terraform before production
- **Static:** `terraform fmt -check`, `terraform validate`, `tflint`, security scanning (`tfsec`/`checkov`/Trivy) in CI.
- **Plan review:** `terraform plan` on every PR, human-reviewed; policy-as-code gates (**OPA/Sentinel**) to enforce rules (e.g. no public S3).
- **Unit/integration tests:** the native **`terraform test`** framework, or **Terratest** (Go) to deploy to an ephemeral env and assert real behavior, then destroy.
- **Promotion:** apply to dev/staging first, then prod through the pipeline with approvals.

### 6.6 Design a Terraform module for a multi-tier app with proper state management (coding round)
Structure:
```
modules/
  network/   # VPC, subnets (public/private/db), routes, NAT, IGW
  compute/   # ASG/EKS or ECS for app tier
  data/      # RDS (multi-AZ), ElastiCache, subnet groups
  security/  # security groups, IAM
envs/
  prod/  main.tf (composes modules) + backend.tf + prod.tfvars
```
Key points to mention:
- **Remote state:** S3 backend + DynamoDB locking, encrypted, versioned; separate state per environment.
- **Layered state** (network vs app vs data) to limit blast radius; wire dependencies with `terraform_remote_state` or module outputs.
- **Inputs/outputs:** parameterize CIDRs, instance sizes, counts; output VPC/subnet/SG IDs and endpoints.
- **Tiers:** public tier (ALB), private app tier (autoscaled compute), isolated DB tier (no public route); security groups reference each other rather than CIDRs.
- Pin versions, tag everything, add `tfsec`/`checkov` in CI.

---
