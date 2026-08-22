# Terraform Interview Questions

Common Terraform interview questions with simple, easy-to-read answers.

---

## 1. How have you used Terraform?

### Short answer

I used Terraform to build cloud environments from code instead of clicking in the console.

### Example of what I built

An application setup on AWS with:

- One VPC with public and private subnets
- Security groups
- A load balancer
- Auto scaling EC2 instances
- An RDS database
- IAM roles
- DNS records and alarms

### How the work was organized

```text
modules/      # reusable code: vpc, compute, database
environments/ # dev, test, prod values
```

Every change went through a pull request. The pipeline ran `fmt`, `validate`, a security scan, and `plan`. Production apply needed an approval.

State was kept in a remote backend that was encrypted, versioned, and locked.

### Interview answer

"I used Terraform to create repeatable environments. For example, I built a VPC with subnets, security groups, a load balancer, auto scaling servers, and an RDS database. I kept reusable code in modules and environment values in separate folders. All changes went through pull requests, and the pipeline ran plan first and applied only after approval."

---

## 2. How would you create cloud resources with Terraform?

### Steps

1. Collect the requirements: what resources, which region, networking, naming, cost.
2. Configure the provider and the remote backend.
3. Pin the Terraform and provider versions.
4. Write the resources, preferably by calling a module.
5. Use variables for values that change per environment.
6. Run the normal command flow.
7. Check the real resource in the cloud after apply.

### Command flow

```bash
terraform fmt
terraform init
terraform validate
terraform plan -out=tfplan
terraform apply tfplan
```

### Interview answer

"First I gather requirements, then I set the provider and remote backend and pin versions. I write resources using modules and variables. I run fmt, init, validate, plan, review the plan, and then apply the saved plan. After apply I check the resource in the cloud, because a successful apply only means the API calls worked."

---

## 3. What happens during init, plan, and apply?

| Command | What it does |
|---|---|
| `terraform init` | Sets up the folder: downloads providers and modules, configures the backend, writes `.terraform.lock.hcl` |
| `terraform plan` | Compares your code with the real infrastructure and shows what will be created, changed, or destroyed |
| `terraform apply` | Makes the changes and saves the result in state |

### Points to remember

- Run `init` again when the backend, modules, or provider versions change.
- `plan` changes nothing. It is safe to run any time.
- `apply tfplan` applies exactly what you reviewed. `apply` without a saved plan makes a fresh plan.

### Interview answer

"`init` prepares the working directory and downloads providers and modules. `plan` shows the difference between my code and the real infrastructure without changing anything. `apply` performs those changes and updates the state file. In pipelines I save the plan with `-out` and apply that file, so I apply exactly what was reviewed."

---

## 4. What is a Terraform backend?

### What it is

A backend is the place where Terraform stores the state file.

- **Local backend:** `terraform.tfstate` on your laptop. Default.
- **Remote backend:** S3, Azure Storage, GCS, or Terraform Cloud.

### Example

```hcl
terraform {
  backend "s3" {
    bucket = "my-tf-state"
    key    = "prod/app/terraform.tfstate"
    region = "us-east-1"
  }
}
```

### Points to remember

- The backend is set up before anything else, so you cannot use normal variables inside it. Use `-backend-config` files instead.
- Keep one state key per environment.
- To change backends, run `terraform init -migrate-state` and take a backup first.

### Interview answer

"A backend decides where the state file is stored. Local means the file sits on your machine, which is not good for teams. Remote backends like S3, Azure Storage, or Terraform Cloud allow shared state with encryption, versioning, and locking. Backend settings cannot use normal variables, so I pass them with a backend config file."

---

## 5. Why use a remote backend?

### Reasons

1. **One shared state** instead of a copy on every laptop.
2. **Locking**, so two people cannot apply at the same time.
3. **Encryption** of a file that can hold sensitive values.
4. **Versioning**, so you can restore an older state.
5. **Access control and audit logs.**
6. **CI/CD can reach it**, laptops are not needed.

### Interview answer

"A remote backend gives the team one shared state file with locking, encryption, versioning, and access control. Without it, everyone keeps their own copy and two applies can overwrite each other. It also lets the pipeline run Terraform instead of running it from a laptop."

---

## 6. How do you store the state file securely?

### Checklist

- Remote backend with encryption at rest and TLS in transit.
- Versioning or soft delete turned on.
- Locking enabled.
- Separate state path per environment.
- Only the pipeline identity can write to production state.
- Never commit state or plan files to Git.

### Example `.gitignore`

```text
*.tfstate
*.tfstate.*
.terraform/
*.tfplan
```

### Important point

Even if an output is marked `sensitive`, the value can still exist inside the state file. So read access must be protected just like write access.

### Interview answer

"State goes into a remote backend with encryption, versioning, locking, and restricted access. Each environment has its own state path, and only the deployment identity can write to production. State can contain secrets even when outputs are marked sensitive, so I protect read access as strongly as write access, and I never commit state to Git."

---

## 7. How do you manage secrets in Terraform?

### Rules

1. Never hardcode a secret in `.tf` files or in a plain `.tfvars` file in Git.
2. Read secrets from a secret store at runtime.
3. Mark variables and outputs as `sensitive`.
4. Protect the backend, because values can land in state.

### Example: read from Azure Key Vault

```hcl
data "azurerm_key_vault_secret" "db_password" {
  name         = "db-password"
  key_vault_id = var.key_vault_id
}

resource "azurerm_mssql_server" "db" {
  name                         = "app-sql"
  administrator_login          = "sqladmin"
  administrator_login_password = data.azurerm_key_vault_secret.db_password.value
}
```

### Example: mark a variable sensitive

```hcl
variable "db_password" {
  type      = string
  sensitive = true
}
```

### Important point

`sensitive = true` only hides the value in CLI output. It does not encrypt state.

### Interview answer

"I keep secrets out of Git. The pipeline logs in with a short-lived identity and reads secrets from Key Vault, Vault, or Secrets Manager. I mark variables and outputs as sensitive, but I explain that this only hides them in output, not in state, so the backend must be encrypted with restricted access. Where possible, the application reads the secret at runtime instead of Terraform passing it."

---

## 8. What challenges have you faced with Terraform?

### Common challenges

| Challenge | How I handle it |
|---|---|
| Two people applying at once | Remote backend with locking, apply only from the pipeline |
| Manual changes in the console (drift) | Scheduled plan, restrict console write access |
| Importing old resources | Write the code first, then import one resource at a time |
| Accidental delete or replace | `prevent_destroy`, review the plan, approvals |
| Secrets ending up in state | Encrypted backend, restricted access |
| Slow plans on big projects | Split into smaller states |
| Provider upgrades breaking code | Pin versions, commit the lock file, upgrade in a separate PR |

### Interview answer

"The most common ones are drift from manual changes, state conflicts when two people apply together, slow plans on large projects, accidental replacement of resources, and provider version upgrades breaking things. I handle them with locked remote state, smaller state files, pinned versions, reviewed plans, and production approvals."

---

## 9. What is drift and how do you detect it?

### What drift is

Drift means the real infrastructure is different from what your Terraform code says. It usually happens when someone changes something in the console during an incident.

### How to detect it

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

### Interview answer

"Drift is when the real resource no longer matches the code, usually after a manual console change. I detect it by running `terraform plan -detailed-exitcode` on a schedule; exit code 2 means drift. I alert with the plan output and check the cloud audit log to see who changed what before deciding what to do."

---

## 10. How do you fix drift?

### Steps

1. Find out what changed, who changed it, and why.
2. Decide with the owner: is the manual change correct?
3. If it **is** correct, update the Terraform code to match and apply.
4. If it is **not** correct, apply the code so Terraform puts the value back.
5. If the resource is not in state at all, import it.
6. Run a plan again and confirm it is clean.

### What to avoid

- Do not auto-revert an emergency fix before someone reviews it.
- Do not hide drift with a wide `ignore_changes`.

### Interview answer

"First I find out what changed and why. If the manual change is correct, I put it into the code so the code stays the source of truth. If it is not correct, an approved apply restores the declared value. If the object is not managed at all, I import it. After that I expect a clean plan, and I reduce console write access so it does not happen again."

---

## 11. Terraform created an S3 bucket and someone added a policy manually. How do you fix it?

### Steps

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

### Interview answer

"I check who added the policy and whether it is safe. If it should stay, I write it in Terraform using `aws_iam_policy_document` and import the existing policy so Terraform manages it. Then I plan and confirm no unexpected changes. If it was not approved, Terraform simply replaces it with the reviewed policy."

---

## 12. How do you bring existing (unmanaged) resources into Terraform?

### Steps

1. List the resource, its ID, and its dependencies.
2. Write a resource block at the address you want to keep permanently.
3. Back up the state.
4. Import.
5. Fill in the missing arguments until the plan is clean.

### Example

```bash
terraform import 'module.network.aws_vpc.main' vpc-012345
terraform state show 'module.network.aws_vpc.main'
terraform plan
```

### Import block (Terraform 1.5+)

```hcl
import {
  to = aws_vpc.main
  id = "vpc-012345"
}
```

### Important point

Import only links the real object to a resource address. It does not write your configuration for you. Keep planning until Terraform shows no unwanted changes.

### Interview answer

"I write the resource block first, back up state, then run `terraform import` with the resource address and the real ID. Import only maps the object into state, so afterwards I run `terraform state show`, copy the important settings into my code, and keep planning until there are no unexpected updates. Related resources like subnets and routes are imported separately."

---

## 13. What is the difference between `count` and `for_each`?

| `count` | `for_each` |
|---|---|
| Creates numbered instances: `aws_subnet.app[0]` | Creates named instances: `aws_subnet.app["web"]` |
| Good for identical copies or an on/off switch | Good for named items with different values |
| Removing a middle item shifts all later indexes | Keys stay stable when an item is removed |

### `count` example

```hcl
resource "aws_instance" "web" {
  count         = 3
  ami           = var.ami
  instance_type = "t3.micro"
}
```

### `for_each` example

```hcl
variable "subnets" {
  type = map(object({
    cidr = string
    az   = string
  }))
}

resource "aws_subnet" "app" {
  for_each          = var.subnets
  vpc_id            = aws_vpc.main.id
  cidr_block        = each.value.cidr
  availability_zone = each.value.az
}
```

### Important point

Switching from `count` to `for_each` changes resource addresses, so Terraform may want to destroy and recreate. Use a `moved` block or `terraform state mv` to avoid that.

### Interview answer

"`count` gives numbered instances and is fine when the resources are identical. `for_each` gives named instances from a map or set, which is safer when each item has an identity, because removing one item does not shift the others. If I switch between them, I use `moved` blocks so Terraform does not recreate resources."

---

## 14. What is a lifecycle block?

### The four options

| Option | What it does |
|---|---|
| `prevent_destroy` | Terraform fails instead of deleting the resource |
| `create_before_destroy` | Creates the new resource first, then deletes the old one |
| `ignore_changes` | Ignores changes to listed attributes |
| `replace_triggered_by` | Replaces this resource when another one changes |

### Example

```hcl
resource "aws_db_instance" "prod" {
  identifier = "prod-db"

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_instance" "web" {
  ami = var.ami

  lifecycle {
    create_before_destroy = true
    ignore_changes        = [tags["LastScanned"]]
  }
}
```

### Points to remember

- `prevent_destroy` does not help if you delete the whole resource block from the code.
- `create_before_destroy` can fail when names must be unique or quota is full.
- A wide `ignore_changes` hides real drift, so keep it narrow.

### Interview answer

"`lifecycle` changes how Terraform handles a resource. I use `prevent_destroy` on production databases, `create_before_destroy` when the old and new resource can exist together, `ignore_changes` when another system owns a field like a tag, and `replace_triggered_by` when a change elsewhere must force a replacement. These are helpers, not full protection, so I also use cloud deletion protection and approvals."

---

## 15. How do you allow plan and apply but block deletion?

### Layers of protection

1. `lifecycle { prevent_destroy = true }` on critical resources.
2. Deletion protection on the cloud resource itself (RDS, load balancer, storage).
3. A policy check (Sentinel, OPA, Checkov) that fails the pipeline if the plan contains a delete.
4. Pipeline credentials that do not have delete permission, with a separate break-glass role.
5. Manual approval before production apply.

### Important point

There is no single Terraform switch that says "allow every update but never delete", because a replacement includes a delete.

### Interview answer

"There is no single flag for it, so I use layers. `prevent_destroy` on critical resources, deletion protection on the cloud side, a policy check that rejects plans containing deletes, and pipeline credentials without delete rights. Init, validate, and plan stay allowed because they only read. When a delete is genuinely needed, it goes through a documented break-glass approval."

---

## 16. What are `taint` and `untaint`?

### What they do

- `terraform taint <address>` marks a resource in state as bad, so the next apply replaces it.
- `terraform untaint <address>` removes that mark.

### Better way today

`taint` is deprecated. Use an explicit replace:

```bash
terraform plan -replace='aws_instance.web' -out=tfplan
terraform apply tfplan
```

### Before replacing anything, check

- What depends on this resource
- Whether it holds data
- Whether downtime is acceptable
- Whether create-before-destroy is possible

### Interview answer

"`taint` marks a resource in state so it gets recreated on the next apply, and `untaint` removes that mark. It is deprecated now, so I prefer `terraform apply -replace=<address>` because the replacement is visible in the plan instead of hidden in state. For databases or disks I never use replacement as a quick troubleshooting step."

---

## 17. A resource is not updating properly. Do taint and untaint help?

### First find out why it is not updating

1. Read the plan. Does Terraform even see a change?
2. Check if the field is immutable, which forces a replacement.
3. Check whether `ignore_changes` is hiding it.
4. Check provider errors and permissions.
5. Check whether another tool is changing it back.

### Then decide

- If the code or input was wrong, fix it and apply. No replacement needed.
- If the resource really must be rebuilt, use `-replace` and review every dependent change.
- If someone tainted a healthy resource by mistake, run `terraform untaint <address>` and plan again.

### Interview answer

"I do not start with taint. First I check the plan, the provider error, whether the field is immutable, and whether `ignore_changes` is hiding it. If the object really needs to be rebuilt, I use `apply -replace` so the change is visible in the plan. If someone tainted a healthy resource by mistake, `untaint` avoids an unnecessary replacement."

---

## 18. What is the difference between stateful and stateless resources?

| Stateful | Stateless |
|---|---|
| Holds data: database, disk, storage bucket, queue | Holds no data: web server, container, VM behind a load balancer |
| Replacement needs backup and a data plan | Can be replaced freely |
| Delete is dangerous | Delete is normal |
| Use `prevent_destroy` and deletion protection | Use immutable replacement and health checks |

### Important point

The Terraform state file is not a backup of your data. It only records resource IDs and attributes.

### Interview answer

"Stateful resources hold business data, like databases, disks, and buckets, so replacing them needs backups, replication, and a cutover plan. Stateless resources such as web servers keep no data and can be recreated behind a load balancer. I also mention that the Terraform state file is not a data backup; it only tracks resource details."

---

## 19. How do you reuse the same code for different environments?

### Folder layout

```text
modules/
  vpc/
  compute/
  database/
environments/
  dev/
    main.tf
    backend.tf
    dev.tfvars
  prod/
    main.tf
    backend.tf
    prod.tfvars
```

### How it works

Both environments call the same module version and pass different values.

```hcl
module "vpc" {
  source  = "git::https://github.com/myorg/tf-modules.git//vpc?ref=v1.4.0"
  cidr    = var.vpc_cidr
  subnets = var.subnets
}
```

Dev passes a small CIDR and one NAT gateway. Prod passes a bigger CIDR and one NAT gateway per zone.

### Interview answer

"I keep the common code in versioned modules and give each environment its own small root folder with its own backend, variables, and approvals. Dev and prod call the same module version but pass different values. I avoid writing `if environment == prod` inside modules, because that hides the differences."

---

## 20. What is a Terraform module and why use it?

### What it is

A module is just a folder of Terraform files with inputs and outputs.

- **Root module:** the folder where you run `terraform apply`.
- **Child module:** any folder called with a `module` block.

### Example

```hcl
module "app_server" {
  source        = "./modules/ec2"
  name          = "app-server"
  instance_type = "t3.small"
  subnet_id     = module.vpc.private_subnet_ids[0]
}
```

### Why use it

1. Write once, use many times.
2. Standard tags, encryption, and naming everywhere.
3. Teams do not copy and paste dozens of resource blocks.
4. You can version it and upgrade safely.

### What to avoid

One giant module with 40 boolean flags. Keep modules small and focused.

### Interview answer

"A module is a folder of Terraform code with defined inputs and outputs. The folder I run Terraform in is the root module, and anything I call with a `module` block is a child module. I use modules so teams do not repeat the same resource blocks and so standards like tagging and encryption are applied everywhere. I keep them small, versioned, and documented."

---

## 21. How do you create IAM roles in Terraform?

### Two parts of a role

1. **Trust policy:** who can assume the role.
2. **Permission policy:** what the role can do.

### Example

```hcl
data "aws_iam_policy_document" "trust" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "app" {
  name               = "app-role"
  assume_role_policy = data.aws_iam_policy_document.trust.json
}

resource "aws_iam_role_policy_attachment" "app_s3" {
  role       = aws_iam_role.app.name
  policy_arn = aws_iam_policy.app_s3.arn
}
```

### Good practices

- Use `aws_iam_policy_document` instead of hand-written JSON strings.
- Give only the actions that are needed. Avoid `"*"`.
- Use a module when the same role pattern repeats.
- Test the access after apply and check CloudTrail.

### Interview answer

"I separate the trust policy from the permission policy. I build both with `aws_iam_policy_document` so the JSON is valid and can use variables. I keep permissions least privilege and avoid wildcards. When the same role pattern repeats, I put it in a module with required tags and boundaries, and I test the access after applying."

---

## 22. How do you create an autoscaling group?

### Two pieces

1. A launch template that describes the instance.
2. An autoscaling group that runs several of them.

### Example

```hcl
resource "aws_launch_template" "web" {
  name_prefix   = "web-"
  image_id      = var.ami_id
  instance_type = "t3.small"

  vpc_security_group_ids = [aws_security_group.web.id]
}

resource "aws_autoscaling_group" "web" {
  name                = "web-asg"
  vpc_zone_identifier = module.vpc.private_subnet_ids
  target_group_arns   = [aws_lb_target_group.web.arn]

  min_size         = 2
  desired_capacity = 2
  max_size         = 6

  health_check_type         = "ELB"
  health_check_grace_period = 60

  launch_template {
    id      = aws_launch_template.web.id
    version = "$Latest"
  }
}
```

### After apply, test

- Scale out works
- New instances register as healthy in the target group
- Terminating one instance brings a new one back

### Interview answer

"I create a launch template with the approved image, security groups, and instance profile, then an autoscaling group that spreads across availability zones with min, desired, and max capacity, target group attachment, and health checks. I add a scaling policy on a real metric like CPU or request count. After apply I test scale-out and instance replacement, because seeing the resource created is not proof it works."

---

## 23. How did you set up Terraform in CI/CD?

### On a pull request

```yaml
- terraform fmt -check
- terraform init
- terraform validate
- tfsec .        # or checkov
- terraform plan -out=tfplan
```

The plan summary is posted as a PR comment. The full plan file is kept as a protected artifact, because plans can show sensitive values.

### After merge

1. A protected job picks up the same commit.
2. It gets the state lock.
3. It waits for approval on production.
4. It runs `terraform apply tfplan`.
5. It runs a smoke check afterwards.

### Rules

- Only the deployment job can apply.
- Only one deployment at a time per state.
- Credentials come from OIDC / workload identity, not stored secrets.

### Interview answer

"On a pull request the pipeline runs fmt, init, validate, a security scan, and a plan with read-only credentials, and posts the plan summary for review. After merge, a protected stage applies the reviewed plan for that same commit, with production approval and only one job per state. Credentials come from workload identity, and after apply I run a smoke test."

---

## 24. How do you run Terraform safely in a pipeline?

### Safety list

| Area | What I do |
|---|---|
| Versions | Pin Terraform, providers, and modules; commit the lock file |
| State | Remote, encrypted, versioned, locked, separate per environment |
| Credentials | Short-lived OIDC credentials, least privilege |
| Review | Plan on PR, approval before production apply |
| Concurrency | One apply per state |
| Failure | Stop the pipeline. Do not auto-retry, do not auto-destroy |
| After apply | Smoke test the application, not just the resource |

### Interview answer

"I pin versions, use locked remote state per environment, and get short-lived credentials from workload identity. PRs run plan and policy checks; production applies the reviewed plan after approval, one job at a time. If an apply fails halfway, the pipeline stops and an engineer compares state with the real resources instead of blindly retrying or destroying."

---

## 25. How do you manage deployments for multiple environments?

### Rules I follow

1. Each environment has its own folder, backend key, and variables file.
2. Each environment has its own cloud account or subscription where possible.
3. Each environment has its own identity and approval level.
4. Shared modules are versioned, and each environment pins a version.
5. The pipeline maps one folder to exactly one environment, so a dev job can never use prod credentials.

### Promotion flow

```text
dev  -> test the change works
test -> test upgrade and recovery
prod -> same module version, different values, with approval
```

### Interview answer

"Each environment gets its own root folder, state key, credentials, variables, and approval. The shared logic lives in versioned modules that each environment pins. The pipeline maps a folder to exactly one environment so a job cannot mix dev code with prod credentials. A change is proven in dev and test before the same module version is promoted to production."

---

## 26. You need infrastructure in 10 AWS regions. How do you structure it?

### Approach

1. Write one reusable regional module.
2. Give each region its own state file.
3. Use a pipeline matrix to plan all regions in parallel and control how many apply at once.
4. Keep global resources such as IAM, Route 53, and CloudFront in a separate global stack.

### Why not one big state with provider aliases?

Provider aliases work for a small fixed list, but with one state:

- One failed region can block all the others.
- The blast radius is huge.
- Plans get slow.

### Interview answer

"I build one regional module and give every region its own state so a failure in one region does not block the rest. A pipeline matrix runs the plans in parallel and controls apply concurrency. Region-specific values like CIDRs and availability zones come from variables. Global resources like IAM and DNS live in a separate global stack."

---

## 27. The state file is getting too large. What do you do?

### Split it by boundary

```text
network-state    -> VPC, subnets, routes
platform-state   -> cluster, shared services
data-state       -> databases, buckets
app-state        -> application resources
```

Good boundaries follow ownership, environment, and how often something changes.

### How to move resources safely

1. Back up and lock the state.
2. Add `moved` blocks, or use `terraform state mv` between the exact states.
3. Make sure no resource is owned by two states at the same time.
4. Run a plan in both the old and the new stack. Both must show no changes.

### Connecting the stacks

Use small stable outputs, data sources, or DNS names, not one big shared state.

### Interview answer

"I split the state by lifecycle and ownership, for example network, platform, data, and application. The goal is smaller blast radius and faster plans, not a fixed resource count. Moving resources is a migration, so I back up state, use `moved` blocks or `terraform state mv`, and confirm both old and new stacks plan clean before normal deployments continue."

---

## 28. How do you make Terraform runs faster?

### First measure where the time goes

- Provider and module download
- Refresh (API calls for every resource)
- Data sources
- Apply itself

### Then fix

| Problem | Fix |
|---|---|
| Too many resources in one state | Split into smaller states |
| Broad data sources scanning everything | Pass IDs as variables instead |
| Extra `depends_on` | Remove it and let Terraform infer dependencies |
| Downloading providers every run | Use a provider cache or mirror in CI |
| Slow apply | Tune `-parallelism` within API rate limits |

### What to avoid

Do not make `-target` your normal way to work. It produces an incomplete plan and hides changes.

### Interview answer

"I measure first: is the time going to provider downloads, refresh, or apply? Then I split large states, remove broad data sources and unnecessary `depends_on`, cache providers in CI, and run independent states in parallel. I avoid using `-target` routinely because it hides changes, and I keep a scheduled full plan so the speedups do not hide drift."

---

## 29. Apply succeeded but the resource is not working. How do you debug?

### Important point

A successful apply only means the cloud API accepted the request. It does not mean the service works.

### Debug order

1. Start from the failing user path.
2. Check DNS, route tables, security groups, and NSG rules.
3. Check IAM permissions.
4. Check service health and bootstrap logs.
5. Compare the code, the plan, and `terraform state show` with the console.

### Useful commands

```bash
terraform state show aws_instance.web
terraform output
TF_LOG=DEBUG terraform plan   # use briefly, logs can show secrets
```

### Interview answer

"A successful apply only proves the API calls worked. I start from the failing user path and check DNS, routing, security groups, IAM, and application logs. I compare my code, the plan, and `terraform state show` with what the console shows. I enable `TF_LOG` only briefly because it can expose sensitive values, and I never edit state to fix a runtime problem."

---

## 30. A production apply failed halfway. How do you recover?

### Steps

1. Stop automatic retries and keep the lock until you know nothing is running.
2. Save the error, the plan, the state version, and the cloud activity log.
3. Find which resources were actually created.
4. Fix the customer impact first.
5. Reconcile state:
   - Resource created but not in state → import it.
   - In state but does not exist → decide to recreate or `state rm`.
6. Fix the real cause: quota, permission, name conflict, network, provider bug.
7. Run a new full plan, review it, apply, and verify.

### What not to do

Do not run `terraform destroy` to "clean up". It can delete working dependencies.

### Interview answer

"Terraform records the resources that succeeded, so I stop retries, keep evidence, and find out exactly what was created. If something exists in the cloud but not in state, I import it; if state has something that no longer exists, I decide carefully before removing it. Then I fix the real cause, run a fresh full plan, review it, and apply. I never destroy everything to clean up."

---

## 31. How do you manage the state file day to day?

### Treat state like a production database

- Encrypted, versioned, locked remote backend.
- Least privilege access, audit logs on.
- Separate state per environment and component.
- All normal changes go through the pipeline.

### Before any state operation

1. Confirm the exact backend key and workspace.
2. Make sure no apply is running.
3. Save a backup: `terraform state pull > backup.tfstate`.
4. Do one change at a time.
5. Run a full plan afterwards.

### Safe commands

```bash
terraform state list
terraform state show <address>
terraform state mv <old> <new>
terraform state rm <address>     # stops managing, does not delete the resource
terraform import <address> <id>
```

### Interview answer

"I treat state as a protected production database: encrypted, versioned, locked, with least-privilege access and separate states per environment. All normal changes go through the pipeline. Before any state operation I confirm the backend key, check that no apply is running, and pull a backup. I use supported commands like `state mv`, `state rm`, `import`, and `moved` blocks instead of editing the JSON."

---

## 32. How do you handle provider or module version problems?

### Where to look

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

Also check `.terraform.lock.hcl` and the module `version` argument.

### Useful command

```bash
terraform providers        # shows which module needs which provider
terraform init -upgrade    # only when you intend to upgrade
```

### Upgrade process

1. Do it in its own pull request.
2. Read the release notes for breaking changes.
3. Run `init -upgrade`, validate, and test.
4. Compare the plan in a lower environment first.
5. Then promote.

### What to avoid

Do not delete `.terraform.lock.hcl` just to make CI pass. Find out why local and CI picked different versions.

### Interview answer

"I check `required_version`, the provider constraints, the lock file, and the module version, and `terraform providers` shows which module needs what. I pin ranges and commit the lock file. Upgrades happen in their own pull request after reading the release notes, testing in a lower environment, and comparing plans. I never delete the lock file just to make the pipeline pass."

---

## 33. What happens if two people apply at the same time?

### Without locking

Both read the same old state, make conflicting changes, and the last write wins. You can end up with lost state entries, duplicate resources, or broken infrastructure.

### With locking

The second run waits or fails with a message like:

```text
Error: Error acquiring the state lock
Lock Info:
  ID:        1a2b3c
  Operation: OperationTypeApply
  Who:       user@host
```

### Also needed

Locking protects the state file, but it does not make two different business changes compatible. So the pipeline should also allow only one deployment job per state.

### If a lock is stuck after a crashed job

```bash
terraform force-unlock 1a2b3c
```

Only after you have proved nothing is running.

### Interview answer

"Without locking, both runs plan from the same old state and can overwrite each other, which causes lost state entries or duplicate resources. A remote backend with locking makes the second run wait or fail. I also serialize the deployment job per state, because locking protects the file but not the logic. If a lock is stuck after a crash, I confirm no apply is running before using `force-unlock` with the exact ID."

---

## 34. Can you edit the state file manually?

### Technically yes, but do not

Editing the JSON can break lineage, serial numbers, provider addresses, and dependencies, and then the next plan can be destructive.

### Use supported commands instead

| Need | Command |
|---|---|
| Rename or move a resource | `terraform state mv` |
| Stop managing without deleting | `terraform state rm` |
| Adopt an existing resource | `terraform import` |
| Refactor in code, reviewable | `moved` block |

### Example `moved` block

```hcl
moved {
  from = aws_instance.web
  to   = module.compute.aws_instance.web
}
```

### Interview answer

"You can, but I avoid it. Manual JSON edits can break lineage and dependencies and cause destructive plans. I use `state mv`, `state rm`, `import`, and `moved` blocks, always with a backup and a full plan afterwards. And I remind people that changing state does not change the real cloud resource."

---

## 35. How do you recover a deleted state file?

### Steps

1. Stop all applies immediately, or Terraform will plan to recreate everything.
2. Confirm the exact backend key and workspace.
3. Restore the last good version from bucket versioning, soft delete, or Terraform Cloud history.
4. Run a read-only plan and compare with cloud activity after that version.

### If no copy exists at all

1. Build an inventory of the real resources from tags and cloud APIs.
2. Make sure the code matches them.
3. Import them in small groups.
4. Keep planning until there are no unexpected changes.

### Never do this

Never run `terraform apply` against an empty state in production. It will try to create everything again.

### Interview answer

"First I stop all applies, because an empty state makes Terraform want to recreate everything. Then I restore the last good version from bucket versioning or the backend's history and confirm it with a read-only plan. If no copy exists, I rebuild state by importing the real resources in small groups until the plan is clean. Afterwards I turn on versioning, restrict delete permissions, and test the restore procedure."

---

## 36. What is Terraform Enterprise?

### Simple definition

Terraform Enterprise is HashiCorp's self-hosted version of Terraform Cloud. You run it inside your own network.

### What it gives you

| Feature | Meaning |
|---|---|
| Remote runs | Plan and apply run on servers, not laptops |
| Remote state | State stored and versioned centrally |
| Workspaces | Separate state and variables per environment |
| VCS integration | A Git push starts a run |
| RBAC | Control who can plan and who can apply |
| Sentinel policies | Block runs that break the rules |
| Private module registry | Share company modules |
| Audit logs | Who changed what and when |

### Interview answer

"Terraform Enterprise is HashiCorp's self-hosted platform for running Terraform centrally. It gives remote runs, managed state, workspaces, Git integration, role-based access, policy enforcement with Sentinel, a private module registry, and audit logs. Companies use it when they need those controls inside their own network. It does not replace good module design or cloud IAM."

---

## 37. Explain the Terraform Enterprise architecture.

### Flow

```text
Git push or API call
        |
Terraform Enterprise application
  (workspaces, variables, policies, run queue)
        |
Worker (runs init, plan, apply)
        |
Cloud provider APIs
        |
State version + logs stored back
```

### Components

- **Application layer:** UI and API, organizations, workspaces, permissions, run queue.
- **Workers:** run Terraform, need network access to module sources and cloud APIs.
- **Object storage:** state versions and run artifacts.
- **Database and cache:** application metadata.

### Production needs

TLS, secret management, backups of state and metadata, monitoring, an upgrade plan, and tested disaster recovery.

### Interview answer

"A Git webhook or API call reaches the Terraform Enterprise application, which manages workspaces, variables, policies, and the run queue. A worker then runs init, plan, and apply, talking to module sources and cloud APIs, and returns logs and a new state version stored in object storage. In production I also plan for TLS, secrets, backups, monitoring, upgrades, and disaster recovery, and I make sure the workers have the network access they need, not just the UI."

---

## 38. How do you gather requirements before writing Terraform code?

### Questions I ask

| Area | Question |
|---|---|
| Resources | What exactly needs to be built? |
| Environments | How many, and how are they different? |
| Network | VPC, subnets, public or private, connectivity |
| Security | Encryption, secrets, who gets access |
| Naming and tags | What standard does the company use? |
| Scale | Expected traffic, autoscaling limits |
| Availability | Multi-AZ, backup, RTO and RPO |
| Cost | Any budget limit |
| Ownership | Who approves and who operates it |
| Existing resources | Anything already created that must be imported |

### Then

Turn the repeated patterns into modules, keep environment values outside modules, and agree on acceptance tests and rollback before writing code.

### Interview answer

"I write a short requirements list first: resources, environments, networking, security, naming and tagging standards, scaling, availability, backup, cost, and ownership. I also check what already exists and must be imported. Then I turn repeated patterns into modules, keep environment values at the root, and agree on acceptance tests and a rollback plan before I start coding."

---

## 39. The plan wants to destroy and recreate a production database. What do you do?

### Steps

1. Do not apply yet.
2. Find which argument forces the replacement. The plan shows `# forces replacement`.
3. Check the provider docs to confirm the field is immutable.
4. Back up the state and take a database snapshot.
5. Decide:
   - Can the change be made in place through the cloud console or a supported operation? Then change the Terraform design or use a narrow `ignore_changes`.
   - Is the change unnecessary? Revert the code.
   - Is replacement really needed? Plan a migration.

### If replacement is really needed

1. Create the new database beside the old one.
2. Replicate or restore the data.
3. Test the application against it.
4. Move traffic through DNS or connection settings.
5. Keep the old one for a rollback window, then delete it.

### Important point

`create_before_destroy` only helps if two databases can exist at once. Names, quotas, and licences may not allow it.

### Interview answer

"I stop and find out which argument forces the replacement, since the plan marks it. I check the provider docs to see whether the field is immutable and whether the change can be done in place instead. If a real replacement is needed, I treat it as a data migration: build the new database, replicate the data, test the application, switch traffic, keep the old one for a rollback window, and only then destroy it. A lifecycle flag alone is not a downtime plan."

---

## 40. How do you design modules used by many teams?

### Module rules

1. Small and focused. One module, one job.
2. Clear inputs with types, defaults, and validation.
3. Useful outputs.
4. Secure defaults such as encryption on.
5. No environment names or credentials inside.
6. A README and an `examples/` folder.
7. Semantic versioning: `v1.2.0`.

### Layout

```text
modules/vpc/
  main.tf
  variables.tf
  outputs.tf
  README.md
  examples/
    complete/
```

### Consuming it

```hcl
module "vpc" {
  source  = "app.terraform.io/myorg/vpc/aws"
  version = "1.4.0"
}
```

### Breaking changes

Release a new major version with a migration note. Do not change v1 behaviour under people's feet.

### Interview answer

"I keep modules small with a clear input and output contract, validation, secure defaults, examples, and documentation, and no environment names or credentials inside. They live in a private registry or Git with semantic versions, and each environment pins a version. Breaking changes get a major version and a migration guide. A platform team owns the standards, but other teams contribute through pull requests instead of copying the module."

---

## 41. How do you handle state locking in CI/CD?

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

Newer Terraform versions can lock with an S3 lock file. The old DynamoDB table method is legacy but still seen in projects.

### Rules

- One state key per environment or component, so jobs do not queue behind each other.
- Only the deployment identity can write to production state.
- Disable concurrent runs for the same state in the pipeline.

### Stuck lock

```bash
terraform force-unlock <LOCK_ID>
```

Only after checking the pipeline and cloud logs to prove no apply is running.

### Interview answer

"I use a remote backend with native locking and one state key per environment or component so runs do not block each other. Only the deployment identity can write to production, and the pipeline allows one job per state. If a lock stays after a crashed job, I check the lock owner and the pipeline first, and only then run `force-unlock` with that exact ID. I never force-unlock just because a job is waiting."

---

## 42. How do you keep secrets out of state?

### What I do

1. No secrets in Git or plain `.tfvars`.
2. Pipeline logs in with workload identity, no stored keys.
3. Secrets come from Vault, Key Vault, or Secrets Manager.
4. Mark variables and outputs `sensitive`.
5. Where possible, Terraform creates the empty secret container and another process fills the value.
6. Encrypt the backend and restrict read access.

### Example: create the secret container, not the value

```hcl
resource "azurerm_key_vault_secret" "db" {
  name         = "db-password"
  value        = var.db_password   # supplied by pipeline, never committed
  key_vault_id = var.key_vault_id
}
```

Better still, the application reads the secret at runtime using its managed identity, so Terraform never touches the value.

### Interview answer

"Secrets never go into Git or plain tfvars. The pipeline authenticates with workload identity and pulls values from a secret manager. I mark variables and outputs sensitive, but I explain that this only hides output, so the backend must be encrypted with restricted read access. Where possible Terraform creates the secret container and grants access, while the application reads the actual value at runtime."

---

## 43. What is your overall approach to drift?

### Three parts

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

### Prevent

Limit console write access, use policy as code, and document a break-glass process where the change must be put back into code afterwards.

### Interview answer

"I detect drift with scheduled read-only plans and alerts, then I check the audit log to see who changed what and why. If the manual change should stay, I put it in the code. If not, an approved apply restores the declared state. I do not silently overwrite an emergency fix. To prevent it, I limit console write access, use policy checks, and require break-glass changes to be reconciled back into code."

---

## 44. How do you enforce tagging and encryption rules?

### Enforce at more than one layer

| Layer | Tool |
|---|---|
| Code review | Pull requests and code owners |
| CI static scan | Checkov, tfsec, Terrascan |
| Plan-time policy | Sentinel or OPA / Conftest |
| Cloud-side policy | AWS SCP, Azure Policy, GCP Org Policy |

### Simple OPA rule

```rego
package terraform

deny[msg] {
  r := input.resource.aws_instance[name]
  not r.tags.Owner
  msg := sprintf("Instance '%v' is missing the Owner tag", [name])
}
```

### Policy levels

- **Advisory:** warn only.
- **Soft mandatory:** can be overridden with approval.
- **Hard mandatory:** always blocks.

Keep an exception process with an expiry date.

### Interview answer

"I enforce rules in layers. CI runs Checkov or tfsec on the code, Sentinel or OPA checks the plan before apply, and cloud-native policies catch anything created outside Terraform. Rules cover required tags, encryption, allowed regions, and private networking. I classify rules as advisory, soft mandatory, or hard mandatory, keep a time-limited exception process, and test policies with both passing and failing examples."

---

## 45. Explain the resource lifecycle and `create_before_destroy`.

### What Terraform decides for each resource

| Decision | When |
|---|---|
| No change | Code matches reality |
| Update in place | Attribute can be changed |
| Replace | Attribute is immutable |
| Create | Resource is new |
| Destroy | Resource removed from code |

### Default replacement order

1. Destroy the old resource.
2. Create the new one.

That means downtime.

### With `create_before_destroy`

```hcl
lifecycle {
  create_before_destroy = true
}
```

1. Create the new resource.
2. Switch references to it.
3. Destroy the old one.

### It can fail when

- The name must be unique.
- Quota does not allow two at once.
- Something is attached to the old resource.

### Interview answer

"Terraform compares code, state, and reality and decides to do nothing, update in place, replace, create, or destroy. Replacement destroys first and then creates, which causes downtime. `create_before_destroy` reverses that order so the new resource comes up first. It is not a guarantee, because unique names, quotas, and attached resources can block having two at once, so I always confirm the order in the plan."

---

## 46. How do you structure Terraform for multi-cloud?

### Approach

1. Write provider-specific modules. Do not try to hide AWS and Azure behind one generic module.
2. Separate state per cloud, account, environment, and region.
3. Give each cloud its own identity and its own pipeline stage.
4. Share the standards: naming, tags, policy checks, review process.
5. Connect stacks through stable outputs or DNS, not one shared state.

### Example provider setup

```hcl
provider "aws" {
  region = "us-east-1"
}

provider "azurerm" {
  features {}
}
```

### Interview answer

"I use provider-specific modules instead of one generic module that pretends the clouds are the same, and I separate state by cloud, account, environment, and region. Each cloud gets its own least-privilege identity and pipeline stage. What I share across clouds is the standards: naming, tagging, policy checks, and review process. That way one cloud outage or provider bug does not block everything."

---

## 47. Workspaces or separate state files?

| CLI workspaces | Separate state files |
|---|---|
| One config, one backend, different state per workspace | Separate folder, backend, and variables per environment |
| Quick to create | More structure to set up |
| Easy to forget which workspace you are in | The folder makes it obvious |
| Shares backend and credentials | Separate credentials and approvals possible |
| Good for short-lived or test copies | Better for long-lived dev, test, prod |

### Commands

```bash
terraform workspace new dev
terraform workspace select dev
terraform workspace list
```

### Interview answer

"Workspaces reuse one configuration and backend with a different state per workspace. They are handy for temporary or nearly identical environments, but it is easy to forget which one is selected and they share backend and credentials. For long-lived dev, test, and production I prefer separate root folders and state files, because credentials, approvals, and blast radius are then explicit."

---

## 48. How do you debug a failed apply in a big module setup?

### Steps

1. Stop retries and read the exact resource address in the error.
2. Check the usual causes: permissions, quota, name already exists, network, API outage.
3. Compare the saved plan with what failed.
4. Inspect values:

```bash
terraform console
> module.vpc.private_subnet_ids
terraform state show module.compute.aws_instance.web
```

5. Turn on debug logs briefly:

```bash
export TF_LOG=DEBUG
export TF_LOG_PATH=./tf.log
```

6. Compare state with the real resources. Import anything created but not tracked.
7. Fix the cause, run a fresh full plan, apply, and verify.

### Interview answer

"I stop retries and find the exact resource address and provider error, then check permissions, quotas, name conflicts, network, and provider version. I use `terraform console` and `state show` to inspect module inputs and outputs, and I enable `TF_LOG` only briefly because logs can contain sensitive data. If the API created something Terraform did not record, I import it instead of recreating it. Then I fix the cause, run a full plan, and verify the application, not just the resource."

---

## 49. Have you written a custom provider or used external data sources?

### Honest answer

If you have not written a provider, say so, and explain what you would do instead.

### Order of preference

1. Official provider.
2. Community or REST/HTTP provider.
3. `external` data source for simple read-only lookups.
4. Custom provider only when nothing else fits.

### Example: external data source

```hcl
data "external" "config" {
  program = ["python3", "${path.module}/get_config.py"]
}

resource "aws_instance" "app" {
  ami           = data.external.config.result.ami_id
  instance_type = "t3.small"
}
```

Keep it read-only and predictable. Terraform may run it during refresh and planning.

### When a custom provider is justified

An internal API that needs proper create, read, update, delete behaviour, schema validation, and import support.

### Interview answer

"I have not written a production provider, and I would be honest about that. I first look for an official provider, then a REST or HTTP provider, then a read-only `external` data source. I have used data sources to look up existing networks, images, and account details so modules do not hardcode IDs. A custom provider is worth it only for an internal API that needs proper CRUD, validation, and import support, plus tests and ownership."

---

## 50. State is corrupted and versioning was never enabled. How do you recover?

### Steps

1. Stop every plan and apply.
2. Keep the corrupt file, the lock info, the CI logs, and the last plans as evidence.
3. Look for any legitimate copy:
   - Terraform Cloud state history
   - CI artifacts
   - A local `.terraform` or `terraform.tfstate.backup` from the last operator
   - Object storage recovery or a disaster-recovery backup
4. If nothing exists, rebuild:
   - Make sure the code matches the real resources.
   - List the real resource IDs from the cloud.
   - Import them in small dependency-aware groups.
   - Plan after each group.
5. Only resume normal changes when a full plan shows no surprises.

### Never do this

- Never copy a state file from another environment.
- Never use `state rm` as a shortcut to make errors go away.

### Fix it for next time

Turn on encryption, versioning or soft delete, locking, restricted access, audit logs, separate states, and test the restore procedure.

### Interview answer

"I stop all runs and preserve the evidence, then hunt for any legitimate copy: Terraform Cloud history, CI artifacts, a local backup file, or object-store recovery. If nothing exists, I rebuild state by making the code match reality and importing resources in small groups, planning after each group until nothing unexpected appears. I never copy state from another environment. Afterwards I enable versioning, locking, restricted access, and a tested restore procedure."

---

## 51. How do you create an EKS cluster with Terraform?

### What you need

1. VPC with private subnets
2. IAM roles for the cluster and the nodes
3. The EKS cluster itself
4. Managed node groups
5. Add-ons: VPC CNI, CoreDNS, kube-proxy, EBS CSI driver

### Example

```hcl
module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "20.8.4"

  cluster_name    = "payments-prod"
  cluster_version = "1.29"

  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnets

  eks_managed_node_groups = {
    general = {
      min_size     = 3
      desired_size = 3
      max_size     = 12
    }
  }
}
```

### Control plane vs worker nodes

| Control plane (managed by AWS) | Worker nodes (yours) |
|---|---|
| API server | kubelet |
| etcd, stores cluster state | Container runtime |
| Scheduler | Runs your pods |
| Controllers | Networking agents |

### After apply, check

API access, node status, system pods, DNS, storage class, autoscaling, and a test workload.

### Interview answer

"I use a pinned EKS module with a VPC, private subnets, cluster and node IAM roles, managed node groups, and the core add-ons. AWS runs the control plane, which is the API server, etcd, scheduler, and controllers, while worker nodes run kubelet and my pods. I plan cluster, node, and add-on upgrades separately. After apply I check API access, node readiness, system pods, DNS, and a sample workload, because a successful apply alone does not prove the cluster works."

---

## 52. How do you handle provider API rate limits?

### Options

1. Lower parallelism:

```bash
terraform apply -parallelism=5
```

2. Use provider retry settings:

```hcl
provider "aws" {
  region             = "us-east-1"
  retry_mode         = "adaptive"
  max_retries        = 10
}
```

3. Add a small wait between heavy resources:

```hcl
resource "time_sleep" "wait" {
  depends_on      = [aws_iam_role_policy_attachment.app]
  create_duration = "30s"
}
```

4. Split the configuration into smaller states so fewer calls happen at once.

### Interview answer

"I reduce `-parallelism`, turn on the provider's retry and backoff settings, and split large configurations into smaller states so fewer API calls happen at the same time. If one specific resource type always triggers throttling, I add a short `time_sleep` between the stages. I also check whether a quota increase is the real fix."

---

## 53. How do you recover from a corrupted state file?

### If you have a backup

Restore the previous version from the bucket, or use `terraform.tfstate.backup`.

```bash
aws s3api list-object-versions --bucket my-tf-state --prefix prod/terraform.tfstate
aws s3api get-object --bucket my-tf-state --key prod/terraform.tfstate --version-id <id> restored.tfstate
```

### If you have no backup

1. Make sure the code matches the real infrastructure.
2. Import the resources one by one.
3. Run a plan and confirm nothing unexpected appears.

### Prevention

Turn on bucket versioning, keep locking on, and test the restore once in a while.

### Interview answer

"If versioning is on, I restore the previous state version from the bucket and confirm it with a read-only plan. If there is no backup, I rebuild state by importing resources one at a time until the plan is clean. The real fix is prevention: versioning, locking, restricted access, and a restore procedure that has actually been tested."

---

## 54. How do you migrate from one backend to another?

### Steps

```bash
# 1. Back up the current state
terraform state pull > backup.tfstate

# 2. Change the backend block in code

# 3. Migrate
terraform init -migrate-state

# 4. Confirm
terraform plan   # must show no changes
```

### Example: local to S3

```hcl
terraform {
  backend "s3" {
    bucket  = "my-tf-state"
    key     = "prod/terraform.tfstate"
    region  = "us-east-1"
    encrypt = true
  }
}
```

### Points to remember

- Do it in a maintenance window.
- Make sure no one else is running Terraform.
- Keep the old state until the new one is proven.

### Interview answer

"I back up the state with `terraform state pull`, update the backend block, run `terraform init -migrate-state`, and confirm the migration by running a plan that shows no changes. I do it when nobody else is running Terraform, and I keep the old copy until the new backend is proven working."

---

## 55. How do you avoid deleting something by accident?

### Layers

1. Always read the plan, especially the destroy section.
2. `prevent_destroy` on critical resources.
3. Cloud-side deletion protection.
4. Separate state files so a mistake has a smaller blast radius.
5. Pipeline credentials without delete permission.
6. Approval before production apply.
7. Backups that have actually been restored once.

### Example

```hcl
resource "aws_rds_cluster" "prod" {
  cluster_identifier  = "prod-db"
  deletion_protection = true

  lifecycle {
    prevent_destroy = true
  }
}
```

### Quick habit

Search the plan output for `destroy` before approving:

```bash
terraform show -json tfplan | jq '.resource_changes[] | select(.change.actions[] == "delete") | .address'
```

### Interview answer

"I never approve a plan without reading the destroy section. On top of that I use `prevent_destroy` and cloud deletion protection on critical resources, separate state files to limit blast radius, pipeline credentials without delete rights, and mandatory approval for production. For the most critical systems there is a break-glass procedure with two approvers and tested backups."

---

## 56. How do you handle state drift?

### Detect

Run a scheduled plan in the pipeline:

```bash
terraform plan -detailed-exitcode -no-color > drift.txt
```

Exit code 2 means drift. Send the report to the team.

### Fix

| Case | Action |
|---|---|
| The manual change was correct | Update the code, then apply |
| The manual change was wrong | Approved apply restores the code value |
| The resource is not managed | `terraform import` |

### A weekly drift job can

- Run plan on all environments
- Post a summary to Slack or Teams
- Create a ticket for each real difference

### Interview answer

"I run scheduled plans to detect drift and alert on exit code 2. Then I check the audit log and decide with the owner whether the manual change should stay. If it should, I update the code; if not, an approved apply restores it. Unmanaged resources get imported. A weekly drift job that posts a summary and opens a ticket keeps this from piling up."

---

## 57. What are the benefits of modules and workspaces?

### Modules

- Reuse the same tested code everywhere
- Standard tags, encryption, and naming
- Teams do not copy and paste
- Change one module, upgrade many projects

### Workspaces

- Same code, separate state per environment
- Quick to create for short-lived copies

### Typical layout

```text
terraform/
  modules/
    networking/
    database/
    compute/
  environments/
    dev/
    test/
    prod/
  global/
    iam/
    dns/
```

### Interview answer

"Modules give reuse and consistency, so every team gets the same tagging, encryption, and naming without copying code. Workspaces let the same configuration hold separate state per environment. Together they reduce duplication, but for long-lived production boundaries I still prefer separate folders and state files over workspaces, because permissions and blast radius are clearer."

---

## 58. How do you use a secret manager with Terraform?

### Vault example

```hcl
data "vault_generic_secret" "db" {
  path = "secret/database/app"
}

resource "aws_db_instance" "app" {
  identifier = "app-db"
  username   = data.vault_generic_secret.db.data["username"]
  password   = data.vault_generic_secret.db.data["password"]
}
```

### AWS Secrets Manager example

```hcl
data "aws_secretsmanager_secret_version" "db" {
  secret_id = "prod/app/db"
}

locals {
  db = jsondecode(data.aws_secretsmanager_secret_version.db.secret_string)
}
```

### Remember

Any value used in a resource can end up in state, so:

- Encrypt state
- Restrict read access
- Rotate secrets regularly
- Mark outputs `sensitive`

### Interview answer

"I keep the secret in Vault, Key Vault, or Secrets Manager and read it with a data source at run time, so nothing is hardcoded. I mark outputs sensitive and encrypt the backend, because the value can still end up in state. For the most sensitive values I prefer that Terraform only grants access and the application reads the secret at runtime."

---

## 59. How do you handle multiple regions and multiple accounts?

### Multiple regions: provider alias

```hcl
provider "aws" {
  region = "us-east-1"
}

provider "aws" {
  alias  = "west"
  region = "us-west-2"
}

resource "aws_s3_bucket" "backup" {
  provider = aws.west
  bucket   = "app-backup-west"
}
```

### Multiple accounts: assume role

```hcl
provider "aws" {
  alias  = "prod"
  region = "us-east-1"

  assume_role {
    role_arn = "arn:aws:iam::111122223333:role/TerraformRole"
  }
}
```

### Sharing values between stacks

```hcl
data "terraform_remote_state" "network" {
  backend = "s3"

  config = {
    bucket = "my-tf-state"
    key    = "network/terraform.tfstate"
    region = "us-east-1"
  }
}

resource "aws_instance" "app" {
  subnet_id = data.terraform_remote_state.network.outputs.private_subnet_ids[0]
}
```

### Interview answer

"For multiple regions I use provider aliases, and for multiple accounts I use a provider with `assume_role` into a Terraform role in the target account. I keep separate state per account and region but share the same modules so everything is built the same way. Stacks exchange values through remote state outputs or stable interfaces like DNS."

---

## 60. How do you test Terraform code?

### Layers of testing

| Layer | Tool | What it catches |
|---|---|---|
| Format | `terraform fmt -check` | Style |
| Syntax | `terraform validate` | Bad references, missing arguments |
| Lint | `tflint` | Wrong instance types, unused variables |
| Security | `tfsec`, `checkov` | Public buckets, missing encryption |
| Plan review | `terraform plan` | Unexpected destroys |
| Unit test | `terraform test` or Terratest | Module actually works |
| Policy | OPA, Sentinel | Company rules |

### Native test example (Terraform 1.6+)

```hcl
# tests/vpc.tftest.hcl
run "creates_vpc" {
  command = plan

  variables {
    cidr = "10.0.0.0/16"
  }

  assert {
    condition     = aws_vpc.main.cidr_block == "10.0.0.0/16"
    error_message = "VPC CIDR is wrong"
  }
}
```

### Terratest example

```go
func TestVpc(t *testing.T) {
  opts := &terraform.Options{TerraformDir: "../examples/vpc"}
  defer terraform.Destroy(t, opts)
  terraform.InitAndApply(t, opts)

  vpcID := terraform.Output(t, opts, "vpc_id")
  assert.NotEmpty(t, vpcID)
}
```

### Interview answer

"I test in layers: `fmt` and `validate` for basics, `tflint` for lint, `tfsec` or `checkov` for security, and a reviewed plan on every pull request. For modules I use the native `terraform test` framework or Terratest to deploy into a sandbox, assert the outputs, and destroy. Policy checks with OPA or Sentinel run before apply, and the pipeline blocks a merge if any layer fails."

---

## 61. How do you get zero-downtime updates?

### Techniques

1. **Create before destroy**

```hcl
resource "aws_launch_template" "web" {
  lifecycle {
    create_before_destroy = true
  }
}
```

2. **Rolling update with instance refresh**

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

3. **Blue-green** — build the new stack beside the old one, move traffic with DNS or the load balancer, then delete the old stack.

4. **Health checks** — do not send traffic until the new instance passes.

5. **Databases** — use a replica that can be promoted, or a managed service with failover.

### Interview answer

"For stateless tiers I use immutable replacement: a new launch template version, an autoscaling instance refresh with a minimum healthy percentage, and health checks before traffic is sent. For bigger changes I use blue-green, so traffic moves only after the new stack is verified and rollback is just switching back. Databases need their own plan with replicas, backups, and application-level migration."

---

## 62. How do you validate input variables?

### Simple validation

```hcl
variable "environment" {
  type        = string
  description = "Deployment environment"

  validation {
    condition     = contains(["dev", "test", "prod"], var.environment)
    error_message = "Environment must be dev, test, or prod."
  }
}

variable "instance_type" {
  type    = string
  default = "t3.micro"

  validation {
    condition     = can(regex("^t3\\.", var.instance_type))
    error_message = "Only t3 instance types are allowed."
  }
}
```

### Typed objects

```hcl
variable "subnets" {
  type = map(object({
    cidr = string
    az   = string
  }))
}
```

### Preconditions

```hcl
resource "aws_instance" "app" {
  lifecycle {
    precondition {
      condition     = var.environment != "prod" || var.instance_type != "t3.micro"
      error_message = "Production cannot use t3.micro."
    }
  }
}
```

### Interview answer

"I use `validation` blocks in variable declarations so bad input fails immediately with a clear message, for example only allowing dev, test, or prod, or only approved instance types. I also use strong types like `map(object({...}))` instead of plain strings, and `precondition` blocks when the rule depends on more than one value. Failing early is much cheaper than failing during apply."

---

## 63. How do you provision resources across two accounts?

### Example

```hcl
provider "aws" {
  alias  = "app"
  region = "us-east-1"
}

provider "aws" {
  alias  = "logs"
  region = "us-east-1"

  assume_role {
    role_arn = "arn:aws:iam::${var.logs_account_id}:role/TerraformRole"
  }
}

# Bucket in the logging account
resource "aws_s3_bucket" "logs" {
  provider = aws.logs
  bucket   = "app-logs-${var.environment}"
}

# Role in the app account
resource "aws_iam_role" "app" {
  provider = aws.app
  name     = "app-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

# Bucket policy allowing the app account role
resource "aws_s3_bucket_policy" "logs" {
  provider = aws.logs
  bucket   = aws_s3_bucket.logs.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { AWS = aws_iam_role.app.arn }
      Action    = ["s3:PutObject"]
      Resource  = "${aws_s3_bucket.logs.arn}/*"
    }]
  })
}
```

### Interview answer

"I define one provider alias per account, with `assume_role` pointing at a Terraform role in the target account, then set `provider = aws.<alias>` on each resource. The trust and resource policies together allow cross-account access. In larger setups there is a management account holding the Terraform roles and a separate account for state, all with least-privilege permissions."

---

## 64. How do you refactor a lot of resources without downtime?

### Preferred way: `moved` blocks

```hcl
moved {
  from = aws_instance.app
  to   = module.compute.aws_instance.app
}
```

Terraform shows the move in the plan, and reviewers can see nothing is being destroyed.

### Older way: state commands

```bash
terraform state mv aws_instance.app module.compute.aws_instance.app
```

### Safety checks

```bash
terraform state pull > backup.tfstate
terraform plan -out=refactor.plan
terraform show -json refactor.plan | jq '.resource_changes[] | select(.change.actions[] == "delete") | .address'
```

If that command prints anything unexpected, stop.

### Do it in small pull requests

Move one module or one group at a time, each with a clean plan.

### Interview answer

"I prefer `moved` blocks, because the move is visible in the plan and reviewable, instead of a state command that someone has to remember to run. I back up state first, then check the plan JSON to confirm no deletes are hiding in it. I split the refactor into small pull requests, one group at a time, and each must plan clean before the next one starts."

---

## 65. How do you create resources from external data?

### Example: create users from a JSON file

```hcl
locals {
  users = jsondecode(file("${path.module}/users.json"))

  users_map = { for u in local.users : u.username => u }
}

resource "aws_iam_user" "team" {
  for_each = local.users_map

  name = each.key

  tags = {
    Department = each.value.department
  }
}
```

### Example: from an API

```hcl
data "http" "services" {
  url = "https://registry.example.com/services"
}

locals {
  services = jsondecode(data.http.services.response_body).items
}

resource "aws_lb_target_group" "services" {
  for_each = { for s in local.services : s.name => s }

  name     = each.key
  port     = each.value.port
  protocol = "HTTP"
  vpc_id   = var.vpc_id
}
```

### Warning

If the external data changes between runs, your plan changes too. Keep the source stable and read-only.

### Interview answer

"I read the data with `jsondecode(file(...))`, the `http` data source, or an `external` data source, turn it into a map in `locals`, and drive `for_each` from that map so each item has a stable key. The important warning is that the plan now depends on outside data, so the source must be stable and read-only, otherwise every run produces a different plan."

---

## 66. How do you extend Terraform when no provider exists?

### Options from easiest to hardest

1. **Existing provider** — check the registry first.
2. **`http` data source** — read-only calls to a REST API.
3. **`external` data source** — run a small script that returns JSON.
4. **`terraform_data` with a provisioner** — last resort for a one-off action.
5. **Custom provider** — write it in Go with the Terraform Plugin Framework.

### External data source example

```hcl
data "external" "cmdb" {
  program = ["python3", "${path.module}/lookup.py"]

  query = {
    app_name = var.app_name
  }
}
```

The script reads JSON from stdin and prints a flat JSON object.

### When to build a real provider

Your internal system needs full create, read, update, delete behaviour, schema validation, and import support. Then you also need tests, versioning, and an owner.

### Interview answer

"First I check whether an official or community provider already exists. For simple read-only needs I use the `http` or `external` data source. A custom provider written in Go with the Plugin Framework is worth it only when an internal API needs real CRUD support, schema validation, and import, and when someone will own and test it long term."

---

## 67. How do you handle database schema changes?

### Separate the two jobs

| Terraform | Migration tool |
|---|---|
| Creates the database server, network, backups, users | Creates tables and changes schema |

Terraform is declarative and does not track table versions. Use Flyway, Liquibase, Alembic, or your application's migration framework for schema.

### Terraform side

```hcl
resource "aws_db_instance" "app" {
  identifier              = "app-db"
  engine                  = "postgres"
  instance_class          = "db.t3.medium"
  allocated_storage       = 20
  backup_retention_period = 7
  skip_final_snapshot     = false

  lifecycle {
    prevent_destroy = true
  }
}

output "db_endpoint" {
  value     = aws_db_instance.app.endpoint
  sensitive = true
}
```

### Pipeline side

```text
1. Take a snapshot
2. Run the migration tool
3. Deploy the application version that matches the schema
4. Keep the migration backward compatible so rollback is possible
```

### Interview answer

"I keep them separate: Terraform creates the database instance, networking, backups, and users, and a dedicated migration tool like Flyway or Liquibase handles the schema through the deployment pipeline. Before a migration the pipeline takes a snapshot, and migrations are written to be backward compatible so the previous application version still works if we need to roll back."

---

## 68. How do you set up state locking for a team?

### S3 backend

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

### Azure backend

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

Azure Storage uses blob leases for locking automatically.

### Serialize the pipeline too

```yaml
# GitLab CI
terraform_apply:
  script:
    - terraform apply -auto-approve tfplan
  resource_group: terraform-${CI_ENVIRONMENT_NAME}
```

### Interview answer

"I use a backend with native locking: S3 with a lock file, Azure Storage with blob leases, GCS, or Terraform Cloud. On top of that the pipeline allows one apply job per state so two changes cannot queue into each other. I also monitor for locks that stay too long, since that usually means a job crashed, and force-unlock is a controlled procedure, not something anyone can run."

---

## 69. How do you run a GitOps workflow with Terraform?

### The idea

Git is the source of truth. Nothing is applied by hand.

### Flow

```text
Pull request  -> plan + checks, posted for review
Merge to main -> apply with approval
Nightly job   -> drift plan, alert if the cloud differs from Git
```

### GitHub Actions example

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
    steps:
      - uses: actions/checkout@v4

      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_ARN }}
          aws-region: us-east-1

      - uses: hashicorp/setup-terraform@v3

      - run: terraform init
      - run: terraform plan -out=tfplan

      - name: Apply
        if: github.ref == 'refs/heads/main'
        run: terraform apply tfplan
```

### Drift job

```bash
terraform plan -detailed-exitcode || \
  gh issue create --title "Infrastructure drift detected"
```

### Tools

Atlantis and Spacelift do this pull-request workflow for you, including plan comments and approval before apply.

### Interview answer

"Git holds the desired state and nothing is applied by hand. A pull request triggers plan and policy checks and posts the result for review, and merging to main triggers the apply with approval. A nightly drift job compares reality with Git and opens an issue if they differ. Tools like Atlantis or Spacelift give this workflow out of the box with plan comments and approvals."

---

## 70. How do you test a module before releasing it?

### Checklist for the module repo

```text
modules/vpc/
  main.tf
  variables.tf
  outputs.tf
  README.md
  examples/
    complete/      # a working example anyone can run
  tests/
    vpc.tftest.hcl
```

### CI for the module

```bash
terraform fmt -check -recursive
terraform validate
tflint --recursive
checkov -d .
terraform test
terraform-docs markdown . > README.md
```

### Release

Tag it with a semantic version:

```bash
git tag v1.4.0
git push origin v1.4.0
```

Consumers pin it:

```hcl
module "vpc" {
  source  = "git::https://github.com/myorg/tf-modules.git//vpc?ref=v1.4.0"
}
```

### Interview answer

"Each module has a README, a working example, and tests. CI runs fmt, validate, tflint, a security scan, and `terraform test` or Terratest against the example, then generates the docs. Releases are tagged with semantic versions and consumers pin a version, so a change to the module cannot break every team at once. A breaking change means a new major version with a migration note."

---

## 71. How do you handle dependencies between separate stacks?

### Option 1: remote state (simple, but couples the stacks)

```hcl
data "terraform_remote_state" "network" {
  backend = "s3"

  config = {
    bucket = "my-tf-state"
    key    = "network/terraform.tfstate"
    region = "us-east-1"
  }
}

resource "aws_instance" "app" {
  subnet_id = data.terraform_remote_state.network.outputs.private_subnet_ids[0]
}
```

### Option 2: pass values in as variables (looser)

```hcl
variable "vpc_id" {
  type = string
}
```

The pipeline supplies the value. The application stack does not need read access to the network state.

### Option 3: look it up by tag

```hcl
data "aws_vpc" "main" {
  tags = {
    Name = "prod-vpc"
  }
}
```

### Option 4: Terragrunt

```hcl
dependency "vpc" {
  config_path = "../vpc"
}

inputs = {
  vpc_id     = dependency.vpc.outputs.vpc_id
  subnet_ids = dependency.vpc.outputs.private_subnets
}
```

### Pipeline order

```text
network -> data -> application -> monitoring
```

### Keep outputs stable

Once another stack depends on an output, treat it like a public interface. Do not rename or remove it without a version bump and a migration note.

### Interview answer

"I connect stacks through a small number of stable outputs. The simplest way is a `terraform_remote_state` data source, but that gives the application stack read access to the network state, so I often prefer passing values in as variables from the pipeline or looking resources up by tag. Terragrunt can wire dependencies automatically. The main rule is to treat those outputs as a public interface and deploy the stacks in a defined order."
