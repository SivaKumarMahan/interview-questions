# Terraform: Drift, Import and Refactoring

> Detecting and fixing drift from manual changes, importing existing resources, and refactoring resources or a monolithic repo into modules without recreating anything.

## Key Concepts

### Drift detection and fixing

#### Detect

```bash
terraform plan -detailed-exitcode
# 0 = no change, 1 = error, 2 = drift
```

#### Fix

| Case | Action |
|---|---|
| Manual change should stay | Update the code, then apply |
| Manual change was wrong | Approved apply restores the code value |
| Resource not managed at all | `terraform import` |

#### Prevent

Read-only console access, policy checks, and a break-glass process where the change must be put back into code afterwards.

### Drift in a team environment

1. Shared remote state with locking, so nobody works from a private copy.
2. All applies from the pipeline.
3. Nightly drift plan for every environment.
4. Cloud audit logs to identify who changed what.
5. Agreed process for emergency changes.

The technical controls matter, but so does the agreement that nobody edits production by hand.

### Refactoring a monolithic repo into modules

#### Steps

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

#### Safety check

```bash
terraform show -json tfplan | jq -r '.resource_changes[] | select(.change.actions[] == "delete") | .address'
```

If that prints anything unexpected, stop.

## Interview Questions

### 1. What is drift and how do you detect it?

#### What drift is

Drift means the real infrastructure is different from what your Terraform code says. It usually happens when someone changes something in the console during an incident.

#### How to detect it

Run a plan on a schedule:

```bash
terraform plan -detailed-exitcode
```

| Exit code | Meaning |
|---|---|
| 0 | No changes |
| 1 | Error |
| 2 | Differences found (drift) |

Then send an alert with the plan summary and check the cloud activity log to see who changed it.

#### Interview answer

"Drift is when the real resource no longer matches the code, usually after a manual console change. I detect it by running `terraform plan -detailed-exitcode` on a schedule; exit code 2 means drift. I alert with the plan output and check the cloud audit log to see who changed what before deciding what to do."

### 2. What is Terraform drift, and what is meant by a Terraform anomaly?

#### 14.1 What is Terraform drift?

Terraform drift occurs when the actual infrastructure is different from what is stored in the Terraform state file because someone or something changed the infrastructure outside Terraform.

**Example**

Suppose Terraform creates an Azure VM with:

```
VM Size: Standard_B2s
Public IP: Enabled
```

Later, an administrator logs into the Azure Portal and changes the VM size to `Standard_D2s_v3`.

Now:

```
Terraform state  -> Standard_B2s
Actual Azure resource -> Standard_D2s_v3
```

This difference is called Terraform drift.

**How do you detect drift?**

```bash
terraform plan
```

Terraform compares:

- Configuration (`.tf` files)
- State file
- Actual cloud infrastructure

If differences exist, Terraform shows them in the plan.

**How do you fix drift?**

There are three options:

1. **Accept the manual change** - update the Terraform code to match the actual infrastructure.
2. **Revert the manual change** - run `terraform apply`. Terraform changes the infrastructure back to the desired state.
3. **Import unmanaged resources** - if a resource was created manually, run `terraform import` to add it to Terraform state.

**Best practices**

- Never make manual changes in production.
- Use Terraform as the single source of truth.
- Store the state remotely.
- Review `terraform plan` before every deployment.

#### 14.2 What is Terraform anomaly?

Terraform does not have an official concept called "Terraform anomaly."

In interviews, "anomaly" usually means unexpected or abnormal behaviour during Terraform execution.

Examples include:

**State file corruption** - the state file becomes inconsistent or damaged.

**Partial deployment** - Terraform creates some resources but fails before completing all resources.

```
VM created
NSG created
Load Balancer creation failed
```

**State drift** - infrastructure changes outside Terraform.

**Dependency issues** - Terraform tries to create resources in the wrong order because dependencies are missing.

**Provider / API issues** - cloud provider returns errors such as rate limiting, timeout, authentication failure or network interruption.

**Real-world example**

Suppose Terraform creates:

```
Resource Group  ok
ACR             ok
Key Vault       ok
AKS             failed (Quota exceeded)
```

Now the deployment is incomplete. This is an anomalous situation because the infrastructure is only partially provisioned.

You would investigate using:

```bash
terraform plan
terraform state list
terraform state show <resource>
terraform refresh   # older versions
terraform apply
```

#### 14.3 Interview summary (30-second answer)

> "Terraform drift occurs when the actual infrastructure differs from Terraform's state because of manual or external changes. We usually detect it using `terraform plan` and either update the code or run `terraform apply` to bring the infrastructure back to the desired state.
>
> Terraform anomaly is not an official Terraform term. It generally refers to unexpected situations such as state corruption, partial deployments, provider failures, dependency issues, or infrastructure inconsistencies that require investigation and correction."

### 3. How do you fix drift?

#### Steps

1. Find out what changed, who changed it, and why.
2. Decide with the owner: is the manual change correct?
3. If it **is** correct, update the Terraform code to match and apply.
4. If it is **not** correct, apply the code so Terraform puts the value back.
5. If the resource is not in state at all, import it.
6. Run a plan again and confirm it is clean.

#### What to avoid

- Do not auto-revert an emergency fix before someone reviews it.
- Do not hide drift with a wide `ignore_changes`.

#### Interview answer

"First I find out what changed and why. If the manual change is correct, I put it into the code so the code stays the source of truth. If it is not correct, an approved apply restores the declared value. If the object is not managed at all, I import it. After that I expect a clean plan, and I reduce console write access so it does not happen again."

### 4. How do you handle state drift?

#### Detect

Run a scheduled plan in the pipeline:

```bash
terraform plan -detailed-exitcode -no-color > drift.txt
```

Exit code 2 means drift. Send the report to the team.

#### Fix

| Case | Action |
|---|---|
| The manual change was correct | Update the code, then apply |
| The manual change was wrong | Approved apply restores the code value |
| The resource is not managed | `terraform import` |

#### A weekly drift job can

- Run plan on all environments
- Post a summary to Slack or Teams
- Create a ticket for each real difference

#### Interview answer

"I run scheduled plans to detect drift and alert on exit code 2. Then I check the audit log and decide with the owner whether the manual change should stay. If it should, I update the code; if not, an approved apply restores it. Unmanaged resources get imported. A weekly drift job that posts a summary and opens a ticket keeps this from piling up."

### 5. What is your overall approach to drift?

#### Three parts

**Detect**

```bash
terraform plan -detailed-exitcode   # 2 means drift
```

Run it nightly and alert.

**Decide**

Check the cloud audit log: who changed it and why. Talk to the owner. Was it a valid emergency fix?

**Fix**

- Valid change → put it in the code.
- Invalid change → approved apply restores the declared value.
- Unmanaged resource → import it.

#### Prevent

Limit console write access, use policy as code, and document a break-glass process where the change must be put back into code afterwards.

#### Interview answer

"I detect drift with scheduled read-only plans and alerts, then I check the audit log to see who changed what and why. If the manual change should stay, I put it in the code. If not, an approved apply restores the declared state. I do not silently overwrite an emergency fix. To prevent it, I limit console write access, use policy checks, and require break-glass changes to be reconciled back into code."

### 6. Drift detection and backups *(asked in interview round)*

#### Drift

Drift means the real infrastructure is different from what the code says. Usually someone changed it in the console.

#### How to detect it

```bash
terraform plan -detailed-exitcode
# 0 = no change, 1 = error, 2 = drift
```

Run it nightly in the pipeline and alert on exit code 2. Terraform Cloud has built-in drift detection, and `driftctl` is another option.

#### In a team

- Remote backend with locking, so nobody works from a private copy
- All changes through the pipeline, no console edits
- Scheduled drift scans with alerts

#### Backups

- Turn on bucket versioning or soft delete for the state file
- Encrypt with a managed key and restrict access
- Never keep state in Git
- Test the restore before you need it

### 7. What does it mean when Terraform shows drift? *(scenario)*

#### It means

Something in the cloud no longer matches your code.

#### Three possible reasons

1. Someone changed it manually.
2. Another tool or controller changed it.
3. The provider or cloud changed a default value.

#### What to do

Read the diff, check the audit log, decide with the owner, then either update the code or restore the declared value.

#### Interview answer

"Drift means the real resource no longer matches the code, usually from a manual change, another controller, or a changed provider default. I read the diff and the audit log, decide with the owner whether the new value should stay, and then either put it into the code or apply to restore it. The third cause catches people out, so I always check the provider changelog before assuming a human did it."

### 8. A PR contains only one change, but `terraform plan` shows multiple changes. How do you troubleshoot it?

**Interviewer:** If a PR contains only one change, but `terraform plan` shows multiple changes, how would you troubleshoot it?

**Candidate:**

First, I would not assume Terraform is wrong. I would check whether the additional changes are caused by state drift, provider changes, dependencies, or the Terraform configuration itself.

#### 3.1 Check the PR diff

First I verify exactly what changed:

```bash
git diff main...HEAD
```

I want to confirm there isn't an indirect change in a module, variable, `.tfvars` file, or shared configuration.

#### 3.2 Check the Terraform plan

```bash
terraform plan
```

I carefully classify the changes:

```
+     -> resource creation
-     -> resource destruction
~     -> resource modification
-/+   -> resource replacement
```

Then I identify which resources are changing unexpectedly.

#### 3.3 Check for Terraform state drift

Someone may have manually changed the Azure resource outside Terraform.

I would refresh the state and compare:

```bash
terraform plan -refresh-only
```

If this shows unexpected changes, I know there is likely infrastructure drift.

#### 3.4 Check Terraform state

I verify whether Terraform's state matches the actual resources:

```bash
terraform state list
terraform state show <resource>
```

I also check whether resources were renamed, moved, imported, or deleted outside Terraform.

#### 3.5 Check provider and module versions

A provider upgrade can change how Terraform interprets a resource.

```bash
terraform providers
```

I would also check `.terraform.lock.hcl` and recent changes to modules.

#### 3.6 Check dependencies

One small change can legitimately affect multiple resources.

For example:

```
VNet change
   |
Subnet
   |
Private Endpoint
   |
AKS configuration
```

So I check the dependency relationship before assuming the extra changes are unexpected.

#### 3.7 Check variables and environment

I verify that the PR pipeline is using the correct:

- `.tfvars`
- Environment variables
- Backend
- Workspace / state
- Terraform version
- Provider version

A very common issue is running the plan against the wrong state or environment.

#### 3.8 Check the plan again

After finding and fixing the root cause:

```bash
terraform plan
```

I expect the plan to contain only the intended change.

#### 3.9 Strong interview answer

> "If one PR change produces multiple Terraform changes, I first review the plan and classify the unexpected changes. Then I check the Git diff, state drift using `terraform plan -refresh-only`, Terraform state, provider and module versions, dependencies, and whether the pipeline is using the correct backend and variables. A common reason is infrastructure drift or a provider/module change. I don't blindly apply the plan until I understand why every unexpected resource is changing."

### 9. Terraform Plan Shows Unexpected Changes for a One-Line Edit

#### The situation

```hcl
sku = "Standard"
```

changed to:

```hcl
sku = "Premium"
```

but `terraform plan` shows 15 resources changing.

#### Possible reasons

1. **The SKU change forces replacement of a dependent resource**, and other resources reference attributes of that resource (e.g., an ID that changes when it's recreated), cascading the diff outward.
2. **State drift** — someone changed resources manually in the Azure portal/CLI, so Terraform's state no longer matches real infrastructure, and `plan` is now reconciling many unrelated differences at once, not just the SKU change.
3. **A module or provider version was upgraded** around the same time, changing default values or attribute names it manages, so `plan` shows changes across all resources built from that module.
4. **Someone else merged unrelated changes** into the same branch/state that hadn't been applied yet.
5. **A shared variable or `for_each`/`count` value changed indirectly** (e.g., a computed variable used across many resources), so a "small" edit ripples widely.

#### Troubleshooting approach

```bash
terraform plan -out=tfplan
terraform show -json tfplan | jq '.resource_changes[] | {address, change: .change.actions}'
git log -p <file>              # confirm only the intended line changed
terraform state list
terraform plan -target=<resource>   # isolate the change to just the SKU resource
```

Compare the plan's "before/after" values resource by resource to see whether the extra changes are genuinely caused by the SKU change (cascading dependency) or are unrelated drift.

#### Short interview answer

"A one-line SKU change causing 15 resources to change usually means either that SKU forces a resource replacement whose ID/attributes other resources depend on, or there's state drift from manual changes outside Terraform. I'd run `terraform plan -out` and inspect the JSON output per resource to see exactly what's changing and why, and use `-target` to isolate whether it's a real dependency chain or unrelated drift that needs a `terraform refresh`/import to reconcile."

### 10. How do you detect drift automatically? *(scenario)*

#### Scheduled job

```yaml
on:
  schedule:
    - cron: "0 2 * * *"

jobs:
  drift:
    steps:
      - run: terraform init
      - run: terraform plan -detailed-exitcode -no-color -out=drift.tfplan
```

#### Handling the result

| Exit code | Action |
|---|---|
| 0 | Nothing to do |
| 1 | Pipeline error, fix the job |
| 2 | Drift, send an alert and open a ticket |

#### Do not auto-apply the fix

Someone may have made a valid emergency change. A human decides.

#### Interview answer

"I run a nightly read-only plan with `-detailed-exitcode`; exit code 2 means drift, and the job posts a summary and opens a ticket. I do not auto-apply the fix, because the manual change could be a valid emergency fix. A person checks the audit log, decides whether it should stay, and either updates the code or approves an apply to restore it."

### 11. How do you prevent people making manual changes? *(scenario)*

#### Prevention

1. Remove console write access for normal users. Give read-only.
2. All changes go through pull requests and the pipeline.
3. Policy as code blocks anything created outside the standard.
4. Have a documented break-glass role for emergencies.

#### Detection

Nightly job:

```bash
terraform plan -detailed-exitcode
```

Exit code 2 means someone changed something.

#### After an emergency change

The person who used break-glass access must open a pull request to put the change into code.

#### Interview answer

"The best prevention is removing console write access and making the pipeline the only way to change infrastructure, backed by policy checks. For real emergencies there is a break-glass role, but the rule is that the change must be reconciled back into code afterwards. On top of that, a nightly drift plan alerts us when something differs, so nothing silently stays out of code."

### 12. Preventing drift from manually modified resources

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

#### Short interview answer

Prevention comes first: RBAC that restricts who can make manual changes at all, backed by Azure Policy as a governance backstop. Detection comes second: regular `terraform plan` runs against remote state, not just plans triggered by code changes. When drift is found, I either import the resource into management or, for genuinely expected system-managed changes, scope `ignore_changes` narrowly rather than broadly.

### 13. A teammate changed something in the console. What do you do? *(scenario)*

#### Steps

1. Run a plan to see the difference.
2. Check the audit log for who and why.
3. Ask them: was this a temporary fix or the new intended setting?
4. If it should stay, put it in the code and apply.
5. If not, an approved apply restores the code value.
6. Tell the team, and tighten console access if it keeps happening.

#### Interview answer

"I run a plan to see exactly what differs and check the audit log for who changed it and why. Then I talk to that person, because a manual change is often a valid emergency fix. If it should stay, I put it in the code so the code stays the source of truth; if not, an approved apply restores it. If it keeps happening, the real fix is removing console write access."

### 14. Terraform created an S3 bucket and someone added a policy manually. How do you fix it?

#### Steps

1. Look at the current policy and check CloudTrail for who added it.
2. Decide if the policy should stay.
3. If yes, write it in code:

```hcl
data "aws_iam_policy_document" "bucket" {
  statement {
    effect    = "Allow"
    actions   = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.app.arn}/*"]

    principals {
      type        = "AWS"
      identifiers = [aws_iam_role.app.arn]
    }
  }
}

resource "aws_s3_bucket_policy" "app" {
  bucket = aws_s3_bucket.app.id
  policy = data.aws_iam_policy_document.bucket.json
}
```

4. If Terraform sees it as an existing separate object, import it:

```bash
terraform import aws_s3_bucket_policy.app my-bucket
```

5. Run a plan and check the JSON difference. Ordering can look different without changing meaning.
6. If the policy was not approved, let Terraform replace it and test allow and deny behaviour.

#### Interview answer

"I check who added the policy and whether it is safe. If it should stay, I write it in Terraform using `aws_iam_policy_document` and import the existing policy so Terraform manages it. Then I plan and confirm no unexpected changes. If it was not approved, Terraform simply replaces it with the reviewed policy."

### 15. How do you prevent drift in a multi-cloud setup? *(scenario)*

#### Approach

1. One pipeline per cloud, each with its own state and identity.
2. Scheduled drift plans for every stack, not just the main one.
3. Same standards everywhere: tags, naming, policy checks.
4. Console write access removed in all clouds, not just one.

#### Interview answer

"The approach is the same in each cloud, just applied consistently. That means separate state and identity per cloud, a scheduled drift plan for every stack, the same tagging and policy rules, and read-only console access for normal users. Drift usually appears in whichever cloud has the weakest controls, so the checks have to cover all of them."

### 16. How do you bring existing (unmanaged) resources into Terraform?

#### Steps

1. List the resource, its ID, and its dependencies.
2. Write a resource block at the address you want to keep permanently.
3. Back up the state.
4. Import.
5. Fill in the missing arguments until the plan is clean.

#### Example

```bash
terraform import 'module.network.aws_vpc.main' vpc-012345
terraform state show 'module.network.aws_vpc.main'
terraform plan
```

#### Import block (Terraform 1.5+)

```hcl
import {
  to = aws_vpc.main
  id = "vpc-012345"
}
```

#### Important point

Import only links the real object to a resource address. It does not write your configuration for you. Keep planning until Terraform shows no unwanted changes.

#### Interview answer

"I write the resource block first, back up state, then run `terraform import` with the resource address and the real ID. Import only maps the object into state, so afterwards I run `terraform state show`, copy the important settings into my code, and keep planning until there are no unexpected updates. Related resources like subnets and routes are imported separately."

### 17. A `terraform import` failed. What do you check? *(scenario)*

#### Checklist

| Check | Detail |
|---|---|
| ID format | Each resource type has its own format, for example a subnet needs `subnet-abc123`, an Azure resource needs the full resource ID |
| Resource address | Quote it if it has brackets: `'module.net.aws_subnet.app["a"]'` |
| Provider alias | Add `-provider=aws.west` if the resource lives in another region or account |
| Permissions | The identity must be able to read the resource |
| Already managed | Another state may already own it |
| Resource type | The block type must match the real object |

#### Example

```bash
terraform import 'module.network.aws_subnet.private["a"]' subnet-0abc123
```

#### After import

```bash
terraform state show 'module.network.aws_subnet.private["a"]'
terraform plan   # keep fixing the code until this is clean
```

#### Interview answer

"I check the ID format for that specific resource type, quote the address when it contains brackets, and make sure I am using the right provider alias for the region or account. I also confirm the identity can read the resource and that no other state already manages it. After a successful import I use `state show` to copy the real settings into my code and keep planning until nothing unexpected appears."

### 18. What are the prerequisites before importing a VPC in Terraform?

**Answer:**

I gather the exact details first: account, region, VPC ID, CIDR and IPv6 settings, DNS attributes, tenancy, tags, ownership, and what depends on it. The provider alias and credentials must point at that account and region, and a matching resource block or module address must already exist in code.

I also confirm the VPC is not already managed in another state file.

Importing a VPC does not automatically import the things inside it. Subnets, route tables, gateways, ACLs, endpoints, and peering connections each need their own import and their own address. Before I start, I lock and back up the remote state and decide those addresses up front.

Then I import, run `state show` to see what Terraform recorded, and update the configuration to match without triggering a replacement. I review a full plan and test connectivity afterward.

This process keeps an adoption exercise from accidentally changing production networking.

### 19. How do you pass arguments to a VPC while using `terraform import`?

**Answer:**

You don't. Import only maps a provider resource ID to an existing Terraform address — it does not take configuration arguments. For example:

```bash
terraform import aws_vpc.prod vpc-0123456789
```

CIDR, DNS settings, tenancy, and tags belong in the `aws_vpc` resource block, and can be supplied there through variables. After import, I check `terraform state show aws_vpc.prod` and run a plan, then adjust the code until it matches the live VPC with no unexpected changes.

Newer import blocks make the mapping reviewable in code, but they still don't replace writing the resource configuration.

### 20. How do you refactor a lot of resources without downtime?

#### Preferred way: `moved` blocks

```hcl
moved {
  from = aws_instance.app
  to   = module.compute.aws_instance.app
}
```

Terraform shows the move in the plan, and reviewers can see nothing is being destroyed.

#### Older way: state commands

```bash
terraform state mv aws_instance.app module.compute.aws_instance.app
```

#### Safety checks

```bash
terraform state pull > backup.tfstate
terraform plan -out=refactor.plan
terraform show -json refactor.plan | jq '.resource_changes[] | select(.change.actions[] == "delete") | .address'
```

If that command prints anything unexpected, stop.

#### Do it in small pull requests

Move one module or one group at a time, each with a clean plan.

#### Interview answer

"I prefer `moved` blocks, because the move is visible in the plan and reviewable, instead of a state command that someone has to remember to run. I back up state first, then check the plan JSON to confirm no deletes are hiding in it. I split the refactor into small pull requests, one group at a time, and each must plan clean before the next one starts."
