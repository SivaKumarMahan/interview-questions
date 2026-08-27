# Terraform Governance and Troubleshooting Scenarios

Interview-style "how do you handle X" Terraform questions - accidental deletion, cross-cloud state migration, backend lock debugging, drift prevention, state-file secrets, policy-as-code, enterprise module design, lock contention, and avoiding accidental resource replacement.

Related ground already covered elsewhere isn't repeated here: state layering/splitting and locking mechanics live in `kubernetes-scaling-and-terraform-fundamentals.md` §5, the enterprise `modules/` + `envs/` directory layout lives in `devops-interview-mixed-topics.md` §15, and drift *detection* (as opposed to prevention) lives in §14 of that same file.

## Contents

1. [Preventing accidental deletion of critical resources](#1-preventing-accidental-deletion-of-critical-resources)
2. [Migrating Terraform state across clouds](#2-migrating-terraform-state-across-clouds)
3. [Debugging remote backend locking issues](#3-debugging-remote-backend-locking-issues)
4. [Preventing drift from manually modified resources](#4-preventing-drift-from-manually-modified-resources)
5. [Encrypting secrets in Terraform state](#5-encrypting-secrets-in-terraform-state)
6. [Policy-as-code for Terraform and Kubernetes](#6-policy-as-code-for-terraform-and-kubernetes)
7. [Passing dependencies between modules via outputs](#7-passing-dependencies-between-modules-via-outputs)
8. [Optimizing Terraform state locking performance](#8-optimizing-terraform-state-locking-performance)
9. [Preventing Terraform from accidentally replacing resources](#9-preventing-terraform-from-accidentally-replacing-resources)

---

## 1. Preventing accidental deletion of critical resources

Four layers, used together rather than any single one alone:

1. **`lifecycle.prevent_destroy`** on genuinely critical resources - blocks `terraform destroy` and any replacement that would destroy the resource.

```hcl
resource "azurerm_key_vault" "kv" {
  name = "prod-kv"

  lifecycle {
    prevent_destroy = true
  }
}
```

2. **Always review `terraform plan` before apply** - a plan showing `-` (destroy) or `-/+` (destroy and recreate) against a critical resource should stop the pipeline for human review, not sail through on `-auto-approve`.
3. **RBAC** - restrict who/what can run `terraform apply` against production state to begin with; most accidental deletions come from someone running the wrong command against the wrong workspace, not from a code review that let anything sneaky through.
4. **CI/CD approvals** - require an explicit approval gate before `apply` runs in a production environment, so the plan output is a real checkpoint, not a formality.

Avoid unnecessary destructive changes in the first place - renaming a resource block without a `moved` block, or changing an immutable attribute, can trigger a destroy/recreate you didn't intend.

### Short interview answer

I use `lifecycle.prevent_destroy` on resources that must never be destroyed by Terraform, review every `plan` before `apply` - especially anything showing `-` or `-/+` - and back that with RBAC restricting who can apply against production, plus a CI/CD approval gate so a human sees the plan before it's applied.

---

## 2. Migrating Terraform state across clouds

When migrating infrastructure across providers - for example AWS to Azure - don't try to reuse the old state. The resources and providers are fundamentally different; there's nothing to "migrate" at the resource level, only at the process level.

1. **Back up the old state** before touching anything:

```bash
terraform state pull > terraform.tfstate.backup
```

2. **Create/import the target resources** on the new cloud. New resources get created normally through `terraform apply`; resources that already exist for some other reason get brought under management with `terraform import`:

```bash
terraform import azurerm_resource_group.rg /subscriptions/<sub-id>/resourceGroups/prod-rg
```

3. **Validate with `terraform plan`** against the new state until it shows no unexpected changes.
4. **Migrate application traffic** to the new infrastructure - DNS cutover, connection string changes, whatever the application needs - only once the new infrastructure is confirmed healthy.
5. **Decommission the old infrastructure** last, after traffic has been running successfully on the new cloud for a safe period.

**Narrower case:** if only the *backend* is changing (e.g. moving state storage from one Azure Storage account to another, still within Terraform/Azure) rather than the cloud provider itself, that's much simpler:

```bash
terraform init -migrate-state
```

This copies existing state into the new backend configuration - no resource recreation involved.

### Short interview answer

I don't try to reuse state across providers - the resource types are different, so there's nothing to carry over directly. I back up the old state with `terraform state pull`, stand up the new infrastructure (importing anything that needs to be brought under management), validate with `plan` until it's clean, cut traffic over once the new side is verified healthy, and only then decommission the old infrastructure. If it's just a backend change within the same provider, `terraform init -migrate-state` handles that without any of this.

---

## 3. Debugging remote backend locking issues

1. **Check whether another `plan`/`apply` is actually running** - the most common cause of a "stuck" lock is simply that another operation legitimately holds it.
2. **Read the lock details** - Terraform's lock error includes the lock ID, who holds it, and when it was created.
3. **Inspect the backend directly**, which differs by backend:
   - **Azure Storage** - check active pipelines/users, and look for a stale blob lease on the state blob.
   - **S3 + DynamoDB** - inspect the DynamoDB lock table for a stale entry.
   - **Terraform Cloud** - inspect workspace runs to see if one is genuinely in progress or stuck.
4. **Only once the lock is confirmed stale** (the process that created it is verifiably gone - a crashed CI agent, a killed pipeline, a network partition that never released the lock):

```bash
terraform force-unlock <LOCK_ID>
```

5. **Validate afterward:**

```bash
terraform plan
```

**Prevent recurrence** by avoiding concurrent applies in the first place (serialize CI/CD deployments per environment/state file), and investigate *why* the lock went stale - an interrupted agent, a network failure, or an operation that genuinely hung - rather than just force-unlocking and moving on.

### Short interview answer

First I confirm no other plan/apply is genuinely running, then inspect the backend-specific lock details - a stale blob lease for Azure Storage, the DynamoDB lock table for S3, or workspace runs for Terraform Cloud. Only once I've confirmed the lock is stale do I run `terraform force-unlock`, then validate with `plan`. To prevent recurrence, I serialize CI/CD deployments per environment and investigate why the lock went stale in the first place - usually an interrupted agent or network failure.

---

## 4. Preventing drift from manually modified resources

- **Restrict manual changes with RBAC** - the strongest prevention is simply not letting people have portal/CLI write access to resources Terraform manages.
- **Run `terraform plan` regularly** (e.g. on a schedule, not just on code changes) to detect drift that RBAC didn't prevent.
- **Use remote state**, so drift detection is checking against a shared, authoritative source rather than a stale local file.
- **Import manually created resources** that should be Terraform-managed, rather than leaving them unmanaged forever:

```bash
terraform import azurerm_storage_account.sa /subscriptions/<sub-id>/resourceGroups/rg/providers/Microsoft.Storage/storageAccounts/mystorage
```

- **Use `lifecycle.ignore_changes` only for expected system-managed changes** - for example an autoscaler adjusting replica counts, or a platform auto-assigning a value Terraform shouldn't fight over. Using it broadly just hides real drift instead of preventing it.
- **Enforce code review and CI/CD** as the only path to production changes, so "manual" changes become the exception requiring explicit justification, not the norm.
- **Use Azure Policy and governance** as a backstop - even with RBAC in place, policy can block out-of-band changes that violate organizational rules regardless of who made them.

### Short interview answer

Prevention comes first: RBAC that restricts who can make manual changes at all, backed by Azure Policy as a governance backstop. Detection comes second: regular `terraform plan` runs against remote state, not just plans triggered by code changes. When drift is found, I either import the resource into management or, for genuinely expected system-managed changes, scope `ignore_changes` narrowly rather than broadly.

---

## 5. Encrypting secrets in Terraform state

- Store production state **remotely** (e.g. Azure Storage), never locally.
- Use **encryption at rest** on the state storage.
- Restrict access with **RBAC**, and **private endpoints/firewalls** so the storage account isn't reachable from the open internet.
- Enable **versioning** on the state storage, so a bad or corrupted state write can be recovered.
- Optionally use **customer-managed keys** through Azure Key Vault for an extra layer of control over the encryption key itself.
- **Do not hardcode secrets** in Terraform configuration - retrieve them from Azure Key Vault instead.
- **Mark sensitive variables** so their values are hidden in CLI output:

```hcl
variable "db_password" {
  type      = string
  sensitive = true
}
```

**The trap:** `sensitive = true` only hides the value from CLI/plan *output*. It does **not** encrypt the value inside the state file itself - the plaintext value still ends up in `terraform.tfstate` (or the remote state file) whenever that resource's attributes are recorded. State-file protection has to come from encrypting and restricting access to the state storage itself, not from the `sensitive` flag.

### Short interview answer

I keep production state remote with encryption at rest, RBAC, and private network access, and I enable versioning so a bad state write is recoverable. Secrets themselves come from Azure Key Vault rather than being hardcoded, and I mark sensitive variables - but I'm careful to explain that `sensitive = true` only hides the value in CLI output; it does not encrypt it inside the state file, so protecting the state storage itself is what actually matters.

---

## 6. Policy-as-code for Terraform and Kubernetes

**Terraform pipeline:**

```
terraform fmt
terraform validate
TFLint
tfsec / Checkov / Trivy
terraform plan
approval
terraform apply
```

Terraform-side policies can enforce things like: approved regions only, mandatory tags, encryption required, no public storage access, and restricted network rules - checked automatically before anything reaches `apply`.

**Kubernetes policy tools:**

- **OPA Gatekeeper**
- **Kyverno**
- **Azure Policy for AKS**

Kubernetes-side policies can enforce: non-root containers, only approved registries, required resource requests/limits, required labels, no privileged containers, and restricted `hostPath` volume use.

The two ecosystems are structurally similar - a policy engine evaluates a desired configuration (a Terraform plan, or a Kubernetes admission request) against rules and blocks anything that violates them, before the change ever takes effect.

### Short interview answer

For Terraform, I run `tfsec`/`Checkov`/`Trivy` plus `TFLint` in the pipeline before `plan`, enforcing things like approved regions, mandatory tags, encryption, and no public storage exposure. For Kubernetes, I use an admission-control policy engine - OPA Gatekeeper, Kyverno, or Azure Policy for AKS - to enforce non-root containers, approved registries, required resource limits, and no privileged containers at the point resources are created, not after the fact.

---

## 7. Passing dependencies between modules via outputs

Enterprise Terraform projects split infrastructure into modules (network, AKS, Key Vault, SQL, storage). Those modules usually depend on each other - AKS needs the subnet ID from the network module, for example. The pattern is to expose what a downstream module needs as an **output**, and pass it in as an **input variable** to the module that needs it, rather than hardcoding values or duplicating resource lookups.

```hcl
# modules/network/outputs.tf
output "subnet_id" {
  value = azurerm_subnet.aks.id
}
```

```hcl
# envs/prod/main.tf
module "network" {
  source = "../../modules/network"
  # ...
}

module "aks" {
  source    = "../../modules/aks"
  subnet_id = module.network.subnet_id
}
```

This keeps modules independently reusable - the AKS module doesn't need to know *how* the subnet was created, only that it receives a valid subnet ID - and it makes the dependency graph explicit in code rather than implicit through naming conventions or manual lookups.

### Short interview answer

Each module exposes what other modules need through `outputs.tf`, and the consuming module takes it as an input variable - `subnet_id = module.network.subnet_id`, for example. That keeps modules loosely coupled and reusable, and makes cross-module dependencies explicit in code instead of relying on naming conventions or manual data lookups.

---

## 8. Optimizing Terraform state locking performance

The goal is reducing **lock contention**, not disabling locking - locking is what prevents two concurrent applies from corrupting state.

- **Split large state files by logical component** - Network, AKS, Database, Storage, Monitoring - so an apply to one component doesn't hold a lock that blocks an unrelated apply to another.
- **Separate state per environment** - dev/test/prod each get their own state and lock, so environments never contend with each other.
- **Keep applies small** - the longer an apply runs, the longer it holds the lock; smaller, more targeted applies reduce that window.
- **Serialize CI/CD deployments per environment** - even with split state, two pipeline runs targeting the *same* state/environment should queue rather than race.
- **Use remote backends with locking** in the first place (Azure Storage with blob leases, S3+DynamoDB, Terraform Cloud) rather than a backend without native locking support.
- **Investigate long-running operations and stale locks** rather than routinely force-unlocking - a pattern of frequent stale locks usually points to a pipeline that's timing out or crashing mid-apply, which is the actual problem to fix.

### Short interview answer

I reduce lock contention rather than touch locking itself - splitting state by component and by environment so unrelated applies don't block each other, keeping individual applies small, and serializing CI/CD runs against the same state so they queue instead of race. If stale locks keep showing up, that's a signal to investigate why applies are dying mid-run, not a reason to routinely force-unlock.

---

## 9. Preventing Terraform from accidentally replacing resources

- **Always review `terraform plan`.** A plan showing `-/+` means destroy-and-recreate, not an in-place update - that's the single most important thing to catch before `apply`.
- **Use `lifecycle.prevent_destroy`** for resources that must never be destroyed:

```hcl
resource "azurerm_key_vault" "kv" {
  name = "prod-kv"

  lifecycle {
    prevent_destroy = true
  }
}
```

- **Avoid unnecessary changes to immutable properties** - some resource attributes force replacement when changed (e.g. certain Azure resource name/region/SKU-family fields); changing them without realizing they're immutable is a common accidental-replacement cause.
- **Use `ignore_changes` only where appropriate** - see [§4](#4-preventing-drift-from-manually-modified-resources) above for the same caution against overusing it.
- **Import existing resources** rather than letting Terraform "adopt" them by recreating them under a new identity.
- **Prefer `for_each` over `count`** when the resources have a stable identity that matters. With `count`, removing an item from the middle of a list shifts every subsequent resource's index - and Terraform destroys/recreates everything after that index to realign. `for_each` keys resources by a stable value (like a name), so removing one item only affects that one resource.
- **Version modules**, so a module update doesn't silently change resource configuration for every consumer at once.
- **Require production plan review and approval** before `apply` runs against production state.

### Short interview answer

The plan is the safety net - `-/+` always means destroy-and-recreate, and I review every plan against production for that specifically. `lifecycle.prevent_destroy` backs that up for resources that must never go away. For collections of similar resources, I use `for_each` over `count` specifically because `count` reindexes and can trigger cascading replacement when an item is removed from the middle of the list, while `for_each` only touches the one resource whose key actually changed.
