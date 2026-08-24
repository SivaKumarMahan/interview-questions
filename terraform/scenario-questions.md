# Terraform Scenario Questions

Real situations you get asked about in interviews, with short answers you can actually say out loud.

---

## 1. How do you manage multiple environments?

### Two ways

**Workspaces** — same code, different state:

```bash
terraform workspace new dev
terraform workspace select dev
terraform apply -var-file=dev.tfvars
```

**Separate folders** — safer for long-lived environments:

```text
environments/dev/    backend.tf  dev.tfvars
environments/test/   backend.tf  test.tfvars
environments/prod/   backend.tf  prod.tfvars
```

Each folder gets its own backend key, credentials, and approval.

### Interview answer

"For short-lived or nearly identical environments I use workspaces. For dev, test, and production I prefer separate folders with their own backend, variables, credentials, and approvals, because it is obvious which environment you are in and a dev job can never touch production state."

---

## 2. How do you stop someone deleting a critical resource?

### Protection layers

```hcl
resource "aws_db_instance" "prod" {
  identifier          = "prod-db"
  deletion_protection = true

  lifecycle {
    prevent_destroy = true
  }
}
```

1. `prevent_destroy` in the lifecycle block
2. Deletion protection on the cloud resource
3. Policy check that fails the build if the plan has a delete
4. Approval before production apply
5. Pipeline credentials without delete permission

### If a destroy already started

Stop new runs, check what is actually gone, restore from backup or replica, import whatever survived, then plan a proper recovery.

### Interview answer

"I use layers: `prevent_destroy` and cloud deletion protection on critical resources, a policy check that rejects plans containing deletes, approval gates, and pipeline credentials without delete rights. If a destroy has already started, I stop the runs, check what really disappeared, restore from backup, and import anything that survived instead of applying blindly."

---

## 3. How do you migrate infrastructure from one cloud to another?

### Steps

1. Build the target environment with new Terraform code, in its own state.
2. Run both environments in parallel.
3. Copy the data: database dump and restore, or replication.
4. Move traffic gradually with DNS.
5. Keep the old environment for a rollback window.
6. Destroy the old environment once everyone agrees.

### Important point

You cannot "migrate state" from AWS to Azure. The resources are different. You write new code and use `terraform import` only for resources that already exist in the target cloud.

### Interview answer

"State does not move between clouds, because the resource types are different, so I write new code for the target cloud in its own state. I run both sides in parallel, copy the data, and shift traffic with DNS so rollback is possible. If some resources already exist in the target cloud, I import them instead of recreating them. The old environment is destroyed only after an agreed rollback window."

---

## 4. The backend lock is stuck. What do you do?

### The error looks like this

```text
Error: Error acquiring the state lock
  ID:        4f1c8b32-...
  Operation: OperationTypeApply
  Who:       runner@ci-agent-3
  Created:   2026-08-05 10:14:03
```

### Steps

1. Look at the lock info: who owns it, which operation, when.
2. Check the pipeline. Is that job still running?
3. Check the cloud activity log. Is Terraform still creating things?
4. Only when nothing is running:

```bash
terraform force-unlock 4f1c8b32-...
```

5. Run a full plan afterwards, in case the crashed run created something.

### Never do

Never delete the lock table or lock object just because a job is waiting.

### Interview answer

"I read the lock record to see who owns it and when it started, then confirm through the pipeline and cloud logs that no apply is still running. Only then do I use `force-unlock` with that exact lock ID. Afterwards I run a full plan, because the crashed run may have created resources that state does not know about. I never delete the lock object just to unblock a waiting job."

---

## 5. How do you prevent people making manual changes?

### Prevention

1. Remove console write access for normal users. Give read-only.
2. All changes go through pull requests and the pipeline.
3. Policy as code blocks anything created outside the standard.
4. Have a documented break-glass role for emergencies.

### Detection

Nightly job:

```bash
terraform plan -detailed-exitcode
```

Exit code 2 means someone changed something.

### After an emergency change

The person who used break-glass access must open a pull request to put the change into code.

### Interview answer

"The best prevention is removing console write access and making the pipeline the only way to change infrastructure, backed by policy checks. For real emergencies there is a break-glass role, but the rule is that the change must be reconciled back into code afterwards. On top of that, a nightly drift plan alerts us when something differs, so nothing silently stays out of code."

---

## 6. How do you encrypt secrets in the state file?

### What you can do

| Control | How |
|---|---|
| Encryption at rest | S3 SSE-KMS, Azure Storage encryption, GCS CMEK |
| Encryption in transit | TLS, which the backends use by default |
| Restrict access | IAM policy on the state bucket, read access is as sensitive as write |
| Versioning | Bucket versioning or soft delete |
| Keep values out | Let the app read secrets at runtime instead of Terraform passing them |

### Example

```hcl
terraform {
  backend "s3" {
    bucket     = "my-tf-state"
    key        = "prod/terraform.tfstate"
    region     = "us-east-1"
    encrypt    = true
    kms_key_id = "arn:aws:kms:us-east-1:111122223333:key/abcd-1234"
  }
}
```

### Important point

Terraform does not encrypt individual values inside state. The whole file is protected by the backend.

### Interview answer

"Terraform does not encrypt single values inside state, so I protect the whole file: an encrypted bucket with a customer-managed key, TLS in transit, versioning, and tight IAM so read access is as restricted as write. The better fix is to avoid putting secrets in state at all, by letting the application read them at runtime through managed identity."

---

## 7. How do you enforce policy as code?

### Two places

**Before apply — Terraform side**

- Checkov or tfsec on the code
- Sentinel or OPA / Conftest on the plan JSON

```bash
terraform show -json tfplan > plan.json
conftest test plan.json
```

**In the cluster — Kubernetes side**

- OPA Gatekeeper or Kyverno as admission controllers

### Example rule

```rego
package terraform

deny[msg] {
  b := input.resource.aws_s3_bucket[name]
  b.acl == "public-read"
  msg := sprintf("Bucket '%v' must not be public", [name])
}
```

### Interview answer

"For Terraform I scan the code with Checkov or tfsec and check the plan with Sentinel or OPA, and the pull request fails if a rule is broken. For Kubernetes I use Gatekeeper or Kyverno as admission controllers so anything applied directly to the cluster is also checked. I keep an exception process with an expiry date, otherwise people work around the gate."

---

## 8. How do you design Terraform for a big company with many teams?

### Structure

```text
Private module registry   -> versioned, reviewed modules
Platform team             -> owns modules and standards
Application teams         -> own their root configs, pin module versions
```

### State boundaries

Split by network, shared platform, data, and applications, and by environment. Each has its own state and its own approvers.

### Workflow

Pull request → plan posted as a comment → review → approval → apply. Atlantis or Spacelift can do this automatically.

### Interview answer

"A platform team owns a private registry of versioned modules and the standards. Application teams own small root configurations that pin a module version and have their own state, credentials, and approvers. State is split by network, platform, data, and application. Every change goes through a pull request where the plan is posted for review, and a tool like Atlantis or Spacelift runs it consistently."

---

## 9. How do you reduce lock contention?

### The cause

One huge state file means every team waits for the same lock.

### The fix

1. Split the state by component and environment.
2. Give each pipeline its own state key.
3. Keep applies short by keeping stacks small.
4. Set a sensible lock timeout instead of waiting forever:

```bash
terraform apply -lock-timeout=5m
```

### Interview answer

"Lock contention almost always means the state file is too big and too many teams share it. I split state by environment and component so each pipeline has its own lock, keep stacks small so applies finish quickly, and set a lock timeout so jobs fail with a clear message instead of hanging. I also monitor for locks that stay open, which usually means a crashed run."

---

## 10. How do you stop Terraform replacing resources unexpectedly?

### Find out why first

The plan tells you:

```text
~ resource "aws_instance" "web" {
    ~ availability_zone = "us-east-1a" -> "us-east-1b" # forces replacement
```

### Then decide

| Situation | Action |
|---|---|
| The change is not needed | Revert the code |
| Another system owns that field | Narrow `ignore_changes` |
| Replacement is needed but downtime is not acceptable | `create_before_destroy` plus traffic cutover |
| It is a database or disk | Backup, migrate data, then replace |

### Example

```hcl
lifecycle {
  ignore_changes = [tags["LastPatched"]]
}
```

Keep the list narrow. A wide `ignore_changes` hides real drift.

### Interview answer

"I read the plan to see which argument is marked `forces replacement`, because that tells me whether the field is immutable. If the change is not needed I revert the code; if another system owns the field I add a narrow `ignore_changes`; if replacement really is needed I plan for it with create-before-destroy and a traffic cutover. For anything holding data, I treat it as a migration, not a replace."

---

## 11. How do you make sure changes are peer reviewed?

### Pipeline on a pull request

```bash
terraform fmt -check
terraform init
terraform validate
tfsec .
terraform plan -out=tfplan
```

Post the plan summary as a PR comment.

### Repository rules

- Branch protection on `main`
- At least one approval
- Code owners for modules and production folders
- No direct pushes

### Apply rules

Only the protected job applies, using the same commit and the reviewed plan, after approval.

### Interview answer

"Every change goes through a pull request that runs fmt, validate, security scans, and a plan, and the plan summary is posted as a comment so reviewers can see creates, updates, and destroys. Branch protection requires an approval, and code owners review modules and production folders. Apply only happens from the protected job on that same commit after approval."

---

## 12. How do you detect drift automatically?

### Scheduled job

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

### Handling the result

| Exit code | Action |
|---|---|
| 0 | Nothing to do |
| 1 | Pipeline error, fix the job |
| 2 | Drift, send an alert and open a ticket |

### Do not auto-apply the fix

Someone may have made a valid emergency change. A human decides.

### Interview answer

"I run a nightly read-only plan with `-detailed-exitcode`; exit code 2 means drift, and the job posts a summary and opens a ticket. I do not auto-apply the fix, because the manual change could be a valid emergency fix. A person checks the audit log, decides whether it should stay, and either updates the code or approves an apply to restore it."

---

## 13. How do you fix a dependency cycle error?

### The error

```text
Error: Cycle: aws_security_group.app, aws_security_group.db
```

Usually two security groups reference each other.

### The fix

Use separate rule resources instead of inline rules:

```hcl
resource "aws_security_group" "app" {
  name   = "app-sg"
  vpc_id = var.vpc_id
}

resource "aws_security_group" "db" {
  name   = "db-sg"
  vpc_id = var.vpc_id
}

resource "aws_security_group_rule" "db_from_app" {
  type                     = "ingress"
  from_port                = 5432
  to_port                  = 5432
  protocol                 = "tcp"
  security_group_id        = aws_security_group.db.id
  source_security_group_id = aws_security_group.app.id
}
```

### Other tips

- Remove unnecessary `depends_on`, which often creates the cycle.
- View the graph: `terraform graph | dot -Tsvg > graph.svg`
- Split the resources into two modules if they really belong to different layers.

### Interview answer

"A cycle usually comes from two resources referencing each other, like two security groups with inline rules. I break it by moving the rules into separate `aws_security_group_rule` resources so the groups themselves no longer depend on each other. I also remove unnecessary `depends_on`, since manual dependencies often cause the cycle, and I use `terraform graph` to see the loop."

---

## 14. How do you prevent drift in a multi-cloud setup?

### Approach

1. One pipeline per cloud, each with its own state and identity.
2. Scheduled drift plans for every stack, not just the main one.
3. Same standards everywhere: tags, naming, policy checks.
4. Console write access removed in all clouds, not just one.

### Interview answer

"The approach is the same in each cloud, just applied consistently. That means separate state and identity per cloud, a scheduled drift plan for every stack, the same tagging and policy rules, and read-only console access for normal users. Drift usually appears in whichever cloud has the weakest controls, so the checks have to cover all of them."

---

## 15. Someone ran destroy in production. What now?

### Immediate steps

1. Stop the pipeline and any other running jobs.
2. Find out what was actually deleted from the cloud activity log.
3. Restore in priority order: data first, then compute.
   - Database from snapshot or replica
   - Storage from versioning or backup
4. Re-apply the code for stateless resources.
5. Import anything that survived instead of recreating it.
6. Verify the application, not just the resources.

### Prevent it happening again

- Remove destroy permission from the pipeline identity
- `prevent_destroy` on critical resources
- Approval before any destroy
- Separate state per environment

### Interview answer

"First I stop everything and work out from the audit log what was actually deleted. Data comes back first, from snapshots or replicas, then I re-apply the code for stateless resources and import anything that survived. Once the service is verified, I make it impossible to repeat: no destroy permission for the pipeline identity, `prevent_destroy` on critical resources, and mandatory approval."

---

## 16. How do you secure a Terraform pipeline?

### Controls

| Area | Control |
|---|---|
| Credentials | OIDC / workload identity, no stored keys |
| Permissions | Least privilege, separate identity per environment |
| Code | Branch protection, code owners, pinned actions |
| Scanning | tfsec, Checkov, secret scanning |
| Policy | Sentinel or OPA on the plan |
| Apply | Protected environment, approval, one job per state |
| Logs | Keep them, but redact secrets |

### Interview answer

"The pipeline uses short-lived credentials from workload identity instead of stored keys, with a separate least-privilege identity per environment. Code is protected with branch rules and code owners, and the actions and provider versions are pinned. Every run does security and policy scanning, and apply only happens in a protected environment after approval. Logs are kept for audit but sensitive output is redacted."

---

## 17. The state file is huge and plans take forever. What do you do?

### Split it

```text
network-state   -> VPC, subnets, routing
platform-state  -> cluster, shared services
data-state      -> databases, storage
app-state       -> application resources
```

### Move safely

```hcl
moved {
  from = aws_subnet.private
  to   = module.network.aws_subnet.private
}
```

Back up state first, and both stacks must plan clean afterwards.

### Other speedups

- Replace broad data sources with variables
- Remove unnecessary `depends_on`
- Cache providers in CI

### Interview answer

"A slow plan usually means one state holds too much, so I split it by lifecycle and ownership: network, platform, data, and application. The move itself is a migration, so I back up state and use `moved` blocks, then confirm both stacks plan clean. I also remove broad data sources and unnecessary `depends_on`, and cache providers in CI."

---

## 18. Why is `terraform plan` slow, and how do you speed it up?

### Where the time goes

1. `init` downloading providers and modules
2. Refresh, which calls the cloud API for every resource
3. Data sources that list everything in an account
4. Unnecessary graph dependencies

### Fixes

| Cause | Fix |
|---|---|
| Too many resources | Split the state |
| Broad data sources | Pass IDs as variables |
| Provider download every run | Provider cache or mirror |
| Refresh is the bottleneck | `-refresh=false` for a quick check only, never for the final plan |

### Interview answer

"First I find out where the time goes: provider download, refresh, or data sources. Usually it is refresh on a very large state, so the real fix is splitting the state. I also replace broad data sources with variables, remove unnecessary `depends_on`, and cache providers in CI. I avoid `-target` as a routine speedup because the plan then hides changes."

---

## 19. How do you test Terraform before deploying?

### Order of checks

```bash
terraform fmt -check      # style
terraform validate        # syntax and references
tflint                    # lint rules
tfsec .                   # security
terraform plan -out=tfplan
terraform test            # module tests
```

Then deploy to dev, verify, and promote the same code to test and production.

### Interview answer

"I run fmt and validate for the basics, tflint for lint, tfsec or Checkov for security, and a reviewed plan on every pull request. Modules also have `terraform test` or Terratest cases that build a real example in a sandbox and destroy it. Then the change is proven in dev before the same code is promoted upward."

---

## 20. How do you make code reusable across projects?

### Steps

1. Put the common pattern in a module.
2. Keep it in its own Git repo or a private registry.
3. Tag releases: `v1.0.0`.
4. Consumers pin the version.

```hcl
module "vpc" {
  source  = "git::https://github.com/myorg/tf-modules.git//vpc?ref=v1.2.0"
  cidr    = "10.20.0.0/16"
}
```

### Rules for a reusable module

- No environment names or account IDs inside
- Typed variables with validation
- Useful outputs
- A README and an example

### Interview answer

"I move repeated patterns into modules that live in their own repo or a private registry with semantic version tags, and consumers pin a version. The module must not contain environment names, account IDs, or credentials; those come in as validated variables. Every module has a README and a working example so other teams can adopt it without reading the internals."

---

## 21. How do you scale Terraform for a large team?

### What matters most

1. Small state files, so teams do not block each other.
2. Versioned modules, so standards are shared.
3. Pull-request workflow with plan on every change.
4. One apply job per state.
5. Separate credentials and approvals per environment.
6. Clear ownership: who owns which stack.

### Interview answer

"Scaling is mostly about boundaries. Keep small state files per component and environment, so teams do not queue behind one lock. Use versioned shared modules so standards stay consistent, a pull-request workflow where the plan is reviewed, and one apply job per state. Each environment has its own credentials and approvers, and every stack has a named owner."

---

## 22. How do you automate plan reviews?

### In the pipeline

```bash
terraform plan -out=tfplan -no-color
terraform show -no-color tfplan > plan.txt
```

Post `plan.txt` as a pull request comment.

### Add automatic checks on the plan

```bash
terraform show -json tfplan > plan.json
conftest test plan.json                       # policy
terraform show -json tfplan | jq '.resource_changes[] | select(.change.actions[] == "delete") | .address'
```

The second command lists everything that would be deleted, which is the part reviewers miss.

### Tools

Atlantis and Spacelift post plans and handle apply approval automatically.

### Interview answer

"The pipeline saves the plan and posts a readable summary as a pull request comment, and it also converts the plan to JSON so policy checks can run automatically and any deletes are listed clearly. Reviewers usually miss deletes in a long plan, so highlighting them is the most useful automation. Atlantis or Spacelift give this workflow out of the box."

---

## 23. Why is `terraform apply` slow?

### Common causes

| Cause | Fix |
|---|---|
| Many resources in one state | Split the state |
| API rate limiting | Lower `-parallelism`, enable provider retries |
| Resources that are slow by nature (RDS, clusters) | Nothing to fix, plan the window |
| Long dependency chains | Remove unnecessary `depends_on` |

### Example

```bash
terraform apply -parallelism=5 tfplan
```

Lowering parallelism can actually be faster when the provider is throttling you.

### Interview answer

"I check whether it is the number of resources, API throttling, or resources that are simply slow to create like databases and clusters. Splitting the state helps most. If the provider is throttling, lowering parallelism and enabling retries is often faster than pushing more requests. Unnecessary `depends_on` also serializes work that could run in parallel."

---

## 24. How do you enforce rules like naming and tagging?

### Where the checks run

1. **Variable validation** — fails immediately with a clear message.

```hcl
variable "name" {
  type = string

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{2,20}$", var.name))
    error_message = "Name must be lowercase letters, numbers, and hyphens."
  }
}
```

2. **Default tags in the provider** — nobody can forget them.

```hcl
provider "aws" {
  default_tags {
    tags = {
      Environment = var.environment
      Owner       = var.owner
      ManagedBy   = "terraform"
    }
  }
}
```

3. **Policy check on the plan** — Sentinel, OPA, or Checkov.
4. **Cloud policy** — catches anything created outside Terraform.

### Interview answer

"I start with variable validation and provider default tags, so the right thing happens by default and bad input fails early with a clear message. Then a policy check on the plan with OPA or Sentinel enforces the rules in CI, and a cloud-native policy catches whatever is created outside Terraform. Layering them means one gap does not let everything through."

---

## 25. How do you set up least privilege IAM in Terraform?

### Rules

1. No `Owner`, `Editor`, or `*` on production.
2. Use narrow predefined roles, or a custom role with only the needed permissions.
3. Grant at the smallest scope: one bucket, one resource group, not the whole subscription.
4. Use workload identity instead of static keys.

### GCP example

```hcl
resource "google_storage_bucket_iam_member" "app_reader" {
  bucket = google_storage_bucket.data.name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_service_account.app.email}"
}
```

### Azure example

```hcl
resource "azurerm_role_assignment" "app_reader" {
  scope                = azurerm_storage_account.data.id
  role_definition_name = "Storage Blob Data Reader"
  principal_id         = azurerm_user_assigned_identity.app.principal_id
}
```

### Interview answer

"I grant a narrow role at the smallest possible scope, on the single bucket or resource group rather than the whole project or subscription, and I avoid primitive roles like Owner or Editor. Identities use workload identity or managed identity so there are no static keys to leak. When something is denied, I read the audit log to find the exact missing permission instead of widening the role to make it pass."

---

## 26. Terraform cannot authenticate to the cloud. How do you debug it?

### Check in this order

1. Which credentials is Terraform actually using?

```bash
aws sts get-caller-identity
az account show
gcloud auth list
```

2. Are the environment variables set in the pipeline?

```bash
ARM_CLIENT_ID  ARM_CLIENT_SECRET  ARM_TENANT_ID  ARM_SUBSCRIPTION_ID
AWS_ROLE_ARN   AWS_WEB_IDENTITY_TOKEN_FILE
```

3. Has the secret or certificate expired?
4. Is the right subscription, project, or account selected?
5. Does the identity have the role it needs?
6. For OIDC, does the trust condition match the repo and branch?

### Interview answer

"I first confirm which identity Terraform is actually using with `sts get-caller-identity` or `az account show`, because the problem is usually a different identity than expected. Then I check whether the environment variables are set in the job, whether the secret expired, whether the right subscription is selected, and whether the role assignment exists. For OIDC I check that the trust condition matches the repository and branch."

---

## 27. How do you keep shared modules secure?

### Controls

1. Modules live in a private registry or a protected repo.
2. Code owner review before release.
3. Security scanning in the module's own pipeline.
4. Secure defaults: encryption on, public access off.
5. Semantic versions, so a change cannot silently reach everyone.

### Example of a secure default

```hcl
variable "public_access" {
  type    = bool
  default = false
}
```

Make the safe option the default, and make the unsafe option something you have to ask for.

### Interview answer

"Modules live in a protected repo with code owner review and their own security scanning, and they are released with semantic versions so nothing reaches consumers silently. The important part is secure defaults: encryption on, public access off, so a team has to deliberately opt out of safety rather than remember to opt in."

---

## 28. How do you monitor Terraform changes in production?

### What to capture

1. The plan artifact for every run, stored and access controlled.
2. A notification to Slack or Teams with the summary before apply.
3. Approval recorded with who approved and when.
4. Apply logs stored for audit.
5. Cloud audit logs to correlate.

### Machine-readable output

```bash
terraform apply -json tfplan | tee apply.json
```

### After apply

Run a smoke check, and watch dashboards and alarms for the next few minutes.

### Interview answer

"Every run stores its plan as an artifact, posts a summary to the team channel, and records who approved it. Apply output is kept in JSON for the audit trail, and I correlate it with cloud audit logs. After apply the pipeline runs a smoke check and I watch the service dashboards, because the value is in noticing a bad change quickly, not just in having the logs."

---

## 29. How do you do immutable infrastructure?

### The idea

Do not patch a running server. Build a new image and replace the servers.

### Flow

1. Build and scan a new image, tagged with a version.
2. Update the launch template to that image.
3. Autoscaling instance refresh replaces instances gradually.
4. Health checks decide whether the new instances stay.
5. Roll back by pointing at the previous image version.

### Example

```hcl
resource "aws_launch_template" "web" {
  image_id = var.ami_id   # a new AMI means a new template version
}

resource "aws_autoscaling_group" "web" {
  instance_refresh {
    strategy = "Rolling"

    preferences {
      min_healthy_percentage = 90
    }
  }
}
```

### Interview answer

"Instead of changing servers in place, I build a new versioned image, point the launch template at it, and let the autoscaling instance refresh replace instances gradually while health checks protect the rollout. Rollback is just pointing back at the previous image version. Data stays outside the instances, in managed services, so replacing a server is never risky."

---

## 30. Terraform wants to destroy something critical. How do you react?

### Steps

1. Stop. Do not approve the apply.
2. Find the reason in the plan: `# forces replacement`, or the resource was removed from the code.
3. If someone deleted the resource block by mistake, restore the code.
4. If a field forces replacement, check the provider docs for whether it can change in place.
5. Verify backups before doing anything.

### Quick check on any plan

```bash
terraform show -json tfplan | jq -r '.resource_changes[] | select(.change.actions[] == "delete") | .address'
```

### Interview answer

"I stop and find out why. Either the resource block was removed from the code by mistake, or an immutable field is forcing replacement, and the plan says which one. I check the provider docs to see whether the change can be done in place, and I verify backups before doing anything. I also run a jq check over the plan JSON so deletes are never buried in a long output."

---

## 31. A `terraform import` failed. What do you check?

### Checklist

| Check | Detail |
|---|---|
| ID format | Each resource type has its own format, for example a subnet needs `subnet-abc123`, an Azure resource needs the full resource ID |
| Resource address | Quote it if it has brackets: `'module.net.aws_subnet.app["a"]'` |
| Provider alias | Add `-provider=aws.west` if the resource lives in another region or account |
| Permissions | The identity must be able to read the resource |
| Already managed | Another state may already own it |
| Resource type | The block type must match the real object |

### Example

```bash
terraform import 'module.network.aws_subnet.private["a"]' subnet-0abc123
```

### After import

```bash
terraform state show 'module.network.aws_subnet.private["a"]'
terraform plan   # keep fixing the code until this is clean
```

### Interview answer

"I check the ID format for that specific resource type, quote the address when it contains brackets, and make sure I am using the right provider alias for the region or account. I also confirm the identity can read the resource and that no other state already manages it. After a successful import I use `state show` to copy the real settings into my code and keep planning until nothing unexpected appears."

---

## 32. How do you handle provider version conflicts?

### Pin the versions

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
```

### Commit the lock file

`.terraform.lock.hcl` belongs in Git for root modules. It keeps CI and laptops on the same versions.

### Debug

```bash
terraform providers        # which module needs which provider
terraform version
terraform init -upgrade    # only when upgrading on purpose
```

### Interview answer

"I pin `required_version` and provider constraints and commit the lock file so CI and laptops resolve the same versions. `terraform providers` shows which module is pulling in a conflicting constraint, which is usually an old module needing an update. Upgrades happen deliberately in their own pull request, and I never delete the lock file just to make the pipeline pass."

---

## 33. How do you secure the state file?

### Checklist

1. Remote backend, never local for shared work
2. Encryption at rest with a managed key
3. Versioning or soft delete
4. Locking
5. IAM: only the pipeline identity writes, few humans read
6. Separate state per environment
7. Never in Git

### Example

```hcl
terraform {
  backend "azurerm" {
    resource_group_name  = "tfstate-rg"
    storage_account_name = "tfstateprod"
    container_name       = "tfstate"
    key                  = "prod/app.tfstate"
  }
}
```

### Interview answer

"State goes in a remote backend with encryption, versioning, locking, and tight IAM, separated per environment, and never in Git. The point I always make is that state can contain secret values, so read access has to be as restricted as write access, and the restore procedure should be tested before you actually need it."

---

## 34. How do you roll back a bad deployment?

### Terraform has no rollback command

Rollback means: revert the code and apply again.

```bash
git revert <bad-commit>
terraform plan -out=rollback.tfplan   # review it carefully
terraform apply rollback.tfplan
```

### What re-applying old code will NOT do

- Bring back deleted data
- Undo a database migration
- Reverse everything a provider did

### So plan for it in advance

- Backups you have actually restored once
- Blue-green or canary so rollback is a traffic switch
- Deletion protection on data resources

### Important point

Restoring an old **state** file is not a rollback. It only makes Terraform believe wrong information.

### Interview answer

"There is no rollback command. I revert the code to the last good commit and apply a new reviewed plan. But I always say clearly that this does not bring back deleted data or undo a database migration, so real rollback safety comes from backups, blue-green deployment, and deletion protection. Restoring an old state file is not a rollback; it just makes Terraform believe something untrue."

---

## 35. How do you monitor and notify on Terraform deployments?

### In the pipeline

```bash
terraform apply -json tfplan > apply.json
```

Send the summary to Slack or Teams:

```bash
curl -X POST -H 'Content-type: application/json' \
  --data "{\"text\":\"Terraform apply finished for prod: $(jq -r '.[] | select(.type==\"change_summary\") | .message' apply.json)\"}" \
  "$SLACK_WEBHOOK"
```

### Also monitor

- Alarms and dashboards created by Terraform itself
- Cloud audit logs for changes made outside Terraform
- Drift job results

### Interview answer

"The pipeline produces JSON output and posts a change summary to the team channel, so everyone can see what was applied and by whom. Terraform also creates the alarms and dashboards for the resources it builds, so the service is monitored from day one. On top of that, cloud audit logs and the nightly drift job catch changes that did not come from the pipeline."

---

## 36. How do you manage GCP IAM or Azure RBAC in Terraform?

### Keep bindings in code, not in the console

**Azure**

```hcl
resource "azurerm_role_assignment" "app_kv" {
  scope                = azurerm_key_vault.app.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_user_assigned_identity.app.principal_id
}
```

**GCP**

```hcl
resource "google_project_iam_member" "app_logs" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.app.email}"
}
```

### Careful with authoritative resources

`google_project_iam_policy` and `google_project_iam_binding` replace existing bindings and can lock people out. Prefer `_member`, which only adds one binding.

### Interview answer

"I keep role assignments in Terraform so access is reviewed like any other change, granting narrow roles at the smallest scope. One thing I always mention is that in GCP the `_policy` and `_binding` resources are authoritative and can remove existing access, so I use `_member` unless I truly intend to own the whole policy."

---

## 37. A teammate changed something in the console. What do you do?

### Steps

1. Run a plan to see the difference.
2. Check the audit log for who and why.
3. Ask them: was this a temporary fix or the new intended setting?
4. If it should stay, put it in the code and apply.
5. If not, an approved apply restores the code value.
6. Tell the team, and tighten console access if it keeps happening.

### Interview answer

"I run a plan to see exactly what differs and check the audit log for who changed it and why. Then I talk to that person, because a manual change is often a valid emergency fix. If it should stay, I put it in the code so the code stays the source of truth; if not, an approved apply restores it. If it keeps happening, the real fix is removing console write access."

---

## 38. Apply is failing because of API rate limits. What do you do?

### Fixes

```bash
terraform apply -parallelism=5 tfplan
```

```hcl
provider "aws" {
  region      = "us-east-1"
  max_retries = 10
  retry_mode  = "adaptive"
}
```

```hcl
provider "google" {
  project                     = var.project_id
  request_timeout             = "60s"
  batching {
    enable_batching = true
  }
}
```

### Longer-term fixes

- Split the configuration so fewer calls happen at once
- Request a quota increase
- Stagger pipelines instead of running them all at 9am

### Interview answer

"I lower `-parallelism`, enable the provider's retry and backoff settings, and split large configurations so fewer API calls happen at once. If it keeps happening I request a quota increase and stagger the pipelines, because throttling is usually caused by many jobs starting at the same time rather than one big apply."

---

## 39. How do you secure Terraform code in GitHub?

### Repository settings

1. Branch protection on `main`, no direct pushes
2. Required reviews and code owners
3. Required status checks: fmt, validate, tfsec, plan
4. Secret scanning and push protection turned on

### Workflow settings

```yaml
permissions:
  id-token: write   # OIDC
  contents: read
```

- Use OIDC, not long-lived keys in secrets
- Pin actions to a version or commit SHA
- Use environments with required reviewers for production

### If a secret is committed

Rotate it immediately. Removing it from history is not enough, it has already been exposed.

### Interview answer

"Branch protection with required reviews and status checks, code owners on modules and production folders, and secret scanning with push protection. The workflow uses OIDC instead of stored keys, pins actions, and applies only through a protected environment with required reviewers. If a secret ever gets committed, I rotate it immediately, because cleaning the history does not make it un-leaked."

---

## 40. What does it mean when Terraform shows drift?

### It means

Something in the cloud no longer matches your code.

### Three possible reasons

1. Someone changed it manually.
2. Another tool or controller changed it.
3. The provider or cloud changed a default value.

### What to do

Read the diff, check the audit log, decide with the owner, then either update the code or restore the declared value.

### Interview answer

"Drift means the real resource no longer matches the code, usually from a manual change, another controller, or a changed provider default. I read the diff and the audit log, decide with the owner whether the new value should stay, and then either put it into the code or apply to restore it. The third cause catches people out, so I always check the provider changelog before assuming a human did it."

---

## 41. How do you reduce total Terraform execution time?

### Quick wins

| Action | Effect |
|---|---|
| Split large states | Biggest win, refresh is the usual bottleneck |
| Cache providers in CI | Saves the download every run |
| Replace broad data sources with variables | Fewer API calls |
| Run independent stacks in parallel | Wall-clock time drops |
| Tune `-parallelism` | Helps or hurts depending on throttling |

### Keep a full plan somewhere

If you optimize by narrowing scope, keep a scheduled full plan so nothing goes unnoticed.

### Interview answer

"The biggest win is splitting large states, because refresh is normally the bottleneck. After that: cache providers in CI, replace broad data sources with variables, and run independent stacks in parallel. I tune parallelism carefully since raising it can trigger throttling. And whatever I narrow for speed, I keep a scheduled full plan so nothing is hidden."

---

## 42. What if the apply fails halfway?

### What Terraform does

Resources that succeeded are recorded in state. Terraform does not roll back the ones already created.

### Steps

1. Stop retries.
2. Read the exact error and resource address.
3. Compare state with the real cloud resources.
4. Reconcile:
   - Created but not in state → import it
   - In state but missing → decide recreate or `state rm`
5. Fix the real cause: quota, permission, name conflict, network.
6. Run a fresh full plan, review, apply, verify.

### Do not

Do not run destroy to "clean up", and do not blindly re-run apply hoping it works.

### Interview answer

"Terraform keeps whatever succeeded in state, so it is not all-or-nothing. I stop retries, read the exact error, and compare state with the real resources. If something was created but not recorded, I import it; if state has something that no longer exists, I decide carefully. Then I fix the actual cause, run a fresh full plan, and apply. I never destroy everything to clean up."

---

## 43. How do you implement rollback?

### There is no rollback command

Rollback means revert the code and apply a new plan.

```bash
git revert <bad-commit>
terraform plan -out=rollback.tfplan
terraform apply rollback.tfplan
```

### Design for rollback in advance

| Change type | How to roll back |
|---|---|
| Stateless app or servers | Blue-green or previous image version, switch traffic |
| Configuration change | Revert the code and apply |
| Database schema | Backward-compatible migration plus a restore plan |
| Deleted data | Only backups can help |

### Interview answer

"Rollback is reverting the code and applying a new reviewed plan, not restoring an old state file. Applying old code cannot bring back deleted data or undo a migration, so I design for rollback up front. That means blue-green so rollback is just a traffic switch, backward-compatible migrations, deletion protection, and backups that have actually been restored once in a test."

---

## 44. How do you organize modules for reuse?

### Typical set

```text
modules/
  network/     VPC or VNet, subnets, routing
  compute/     VM, autoscaling, or node pools
  database/    managed database with backups
  iam/         roles and role assignments
  monitoring/  alarms and dashboards
```

### How teams consume them

```hcl
module "network" {
  source  = "app.terraform.io/myorg/network/azurerm"
  version = "2.1.0"

  address_space = var.address_space
  subnets       = var.subnets
}
```

### Rules

- One module, one purpose
- No environment names inside
- Version everything
- Document inputs and outputs

### Interview answer

"I build one module per component, network, compute, database, IAM, and monitoring, each with a clear input and output contract and no environment names inside. They are versioned in a registry or Git and consumers pin a version. That way an improvement to the module can be rolled out team by team instead of surprising everyone at once."

---

## 45. Two people run apply at the same time. What happens?

### With a locking backend

The second one is refused:

```text
Error: Error acquiring the state lock
```

### Without locking

Both plan from the same old state and both write. The result can be a lost state entry, a duplicate resource, or infrastructure that no longer matches state.

### The full fix

1. A backend with locking
2. Applies only from the pipeline
3. One job per state

### Interview answer

"With a locking backend the second run is refused with a state lock error, which is the correct behaviour. Without locking, both runs plan from the same old state and one overwrites the other, causing lost entries or duplicate resources. Locking protects the file, but I also serialize the pipeline per state, because two valid changes can still conflict logically."

---

## 46. How do you build a CI/CD pipeline for Terraform?

### Stages

```text
1. Checkout
2. fmt + validate
3. Security scan (tfsec / Checkov)
4. terraform plan -out=tfplan   (read-only credentials)
5. Post plan to the pull request
6. Manual approval           <- production only
7. terraform apply tfplan
8. Smoke test
```

### GitHub Actions example

```yaml
jobs:
  plan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: hashicorp/setup-terraform@v3
      - run: terraform init
      - run: terraform validate
      - run: terraform plan -out=tfplan

  apply:
    needs: plan
    environment: production   # requires approval
    steps:
      - run: terraform apply tfplan
```

### Interview answer

"The pull request stage runs fmt, validate, a security scan, and a plan with read-only credentials, and posts the plan for review. After merge, a protected environment requires approval and applies that same reviewed plan, followed by a smoke test. Credentials come from OIDC, state is locked, and only one apply runs per state."

---

## 47. How does a team share state?

### Setup

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

### Rules for the team

1. One state key per environment and component.
2. Locking always on.
3. Versioning on for recovery.
4. Humans get read access, the pipeline gets write access.
5. Nobody applies from a laptop against production.

### Interview answer

"State lives in a shared remote backend with encryption, locking, and versioning, with one key per environment and component. The pipeline is the only identity that writes to production; engineers get read access so they can plan but not apply. That combination is what actually prevents two people overwriting each other."

---

## 48. You changed a variable and want to see the impact. What do you do?

### Run a plan

```bash
terraform plan -var-file=prod.tfvars -out=tfplan
```

### What to look for

1. Not just the resource you expected. Look at everything.
2. Any `forces replacement`.
3. Any destroy.
4. Changed outputs, which other stacks may depend on.

### Machine-readable check

```bash
terraform show -json tfplan | jq -r '.resource_changes[] | "\(.change.actions | join(",")) \(.address)"'
```

### Do not use `-target` to "just check one thing"

It hides everything else.

### Interview answer

"I run a plan with the right var file and read the whole thing, not just the resource I expected to change, because an immutable field can turn a small value change into a replacement. I look specifically for `forces replacement`, destroys, and changed outputs that other stacks depend on. I avoid `-target`, because narrowing the plan hides exactly what I am trying to catch."

---

## 49. The state file is corrupted or deleted. What do you do?

### Steps

1. Stop all runs immediately.
2. Restore the previous version from the backend:

```bash
aws s3api list-object-versions --bucket my-tf-state --prefix prod/terraform.tfstate
```

Azure Storage: restore the blob snapshot. Terraform Cloud: restore from state history.

3. Run a read-only plan to confirm the restored state matches reality.
4. If no copy exists, rebuild by importing resources in small groups.

### Prevention

Versioning, soft delete, locking, restricted delete permissions, and a restore you have practised.

### Interview answer

"First I stop all runs, because with an empty state Terraform will plan to recreate everything. Then I restore the previous version from bucket versioning or the backend's history and confirm it with a read-only plan. If there is genuinely no copy, I rebuild state by importing resources in small groups until the plan is clean. Afterwards I make sure versioning and delete protection are on and that the restore procedure is documented and tested."

---

## 50. How do you manage dev, QA, and prod with Terraform?

### Layout

```text
modules/                 shared, versioned code
environments/
  dev/    backend.tf  dev.tfvars
  qa/     backend.tf  qa.tfvars
  prod/   backend.tf  prod.tfvars
```

### What differs per environment

| Setting | Dev | Prod |
|---|---|---|
| Instance size | Small | Right-sized |
| Node count | 1 | 3 or more |
| Backups | Short retention | Long retention |
| Approval | None | Required |
| Deletion protection | Off | On |

### Promotion

Prove the change in dev, then QA, then apply the same module version to prod with different values.

### Interview answer

"Shared modules hold the logic, and each environment has its own folder with its own backend, variables, credentials, and approvals. What differs between environments is values like sizing, retention, and protection settings, not the code itself. A change is proven in dev and QA before the same module version is promoted to production."

---

## 51. How do you provision environments end to end?

### Pieces

1. `modules/` for reusable components.
2. `environments/<env>.tfvars` for values.
3. A pipeline that picks the environment from the branch or an input.
4. Environment-specific sizing, for example small nodes in dev, larger in prod.
5. Application deployment handled by a separate tool such as Argo CD or Helm.
6. Cost control in dev: scale down or destroy outside working hours.

### Pipeline snippet

```yaml
- run: terraform init -backend-config=envs/${{ inputs.env }}.backend.hcl
- run: terraform plan -var-file=envs/${{ inputs.env }}.tfvars -out=tfplan
```

### Interview answer

"Reusable modules plus one tfvars file per environment, and the pipeline selects the backend config and var file for the chosen environment. Terraform builds the platform, for example the cluster and node groups sized per environment, and application deployment is handled separately by Argo CD or Helm. For dev I add a scheduled scale-down or destroy outside working hours to control cost, while production stays permanent."
