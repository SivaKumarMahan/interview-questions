# Terraform: Fundamentals and Workflow

> What Terraform and IaC are, the core blocks, resources vs data sources, dependencies, essential commands, and the init/plan/apply workflow, plus a cross-topic set of scenario reminders.

## Key Concepts

### Infrastructure as Code principles

| Principle | What it means |
|---|---|
| Declarative | Describe the end state, not the steps |
| Version controlled | All code in Git, reviewed through pull requests |
| Modular | Reusable components with inputs and outputs |
| Automated | The pipeline applies changes, not a laptop |
| Idempotent | Running twice produces the same result |
| Documented | README, examples, and clear variables |
| Tested | Validate, scan, plan, and test before apply |

### Terraform uses beyond creating infrastructure

Terraform is used for the broader lifecycle of resources, not just the initial `terraform apply`:

1. **Modify existing infrastructure** - change resource attributes and reconcile them via plan/apply.
2. **Manage infrastructure configuration** over time as requirements change.
3. **Detect configuration drift** with `terraform plan` - compares real infrastructure against the state file.
4. **Import existing manually created infrastructure** with `terraform import`, bringing resources that were created by hand under Terraform management.
5. **Lifecycle management** using resource-level meta-arguments:
   - `create_before_destroy` - creates the replacement resource before destroying the old one, avoiding downtime on replacement.
   - `prevent_destroy` - blocks `terraform destroy`/replacement of a resource entirely, as a safety rail for critical resources (e.g. a production database).
   - `ignore_changes` - tells Terraform to ignore drift on specific attributes (e.g. ones modified outside Terraform, like autoscaler-adjusted replica counts).
6. **Manage multiple environments** with reusable modules and variables (dev/staging/prod from the same module, different variable values).
7. **Create reusable Terraform modules** so common patterns aren't copy-pasted across projects.
8. **Automate infrastructure changes through CI/CD** rather than running `terraform apply` from a laptop.
9. **Manage non-infrastructure resources** - Terraform providers exist for Kubernetes objects, GitHub (repos, teams, branch protection), and Azure DevOps (projects, pipelines, permissions), so Terraform can manage more than just cloud infrastructure.
10. **Standardization and compliance** - enforcing consistent resource configuration (tags, naming, network rules) across an organization through shared modules and policy checks.
11. **Disaster recovery** - recreating infrastructure from code in a new region/subscription if the original is lost, since the desired state already exists as code.

Terraform is primarily Infrastructure as Code / resource lifecycle management. It is **not** a replacement for Ansible - Ansible is generally better for configuring software *inside* already-running servers (packages, config files, services), while Terraform is better at creating/managing the resources themselves.

### Core blocks

| Block | Purpose |
|---|---|
| `terraform` | Required versions and backend settings |
| `provider` | How to reach the cloud API; use aliases for extra regions or accounts |
| `resource` | Something Terraform creates and manages |
| `data` | Something Terraform only reads |
| `variable` | Typed input |
| `locals` | Reusable expressions inside the configuration |
| `output` | Values exposed to the caller or another stack |
| `module` | A call to a reusable child module |
| `moved` | Tells Terraform an address changed, so it does not recreate |
| `import` | Declarative import of an existing resource |

#### Example

```hcl
terraform {
  required_version = ">= 1.6.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.100"
    }
  }
}

provider "azurerm" {
  features {}
}

variable "location" {
  type    = string
  default = "centralindia"
}

locals {
  name_prefix = "app-${var.environment}"
}

resource "azurerm_resource_group" "main" {
  name     = "${local.name_prefix}-rg"
  location = var.location
}

output "resource_group_name" {
  value = azurerm_resource_group.main.name
}
```

### Resource vs data source

#### Resource

Terraform **creates and manages** it.

```hcl
resource "google_compute_instance" "vm" {
  name         = "my-vm"
  machine_type = "e2-medium"
  zone         = "us-central1-a"
}
```

#### Data source

Terraform only **reads** it. Nothing is created or changed.

```hcl
data "google_compute_image" "ubuntu" {
  family  = "ubuntu-2204-lts"
  project = "ubuntu-os-cloud"
}
```

#### Using both together

Look up the latest image, then build a VM from it:

```hcl
resource "google_compute_instance" "vm" {
  name         = "my-vm"
  machine_type = "e2-medium"
  zone         = "us-central1-a"

  boot_disk {
    initialize_params {
      image = data.google_compute_image.ubuntu.self_link
    }
  }
}
```

#### Interview answer

"A resource is something Terraform creates, updates, and deletes. A data source is read-only, used to look up something that already exists. A common pattern is a data source that finds the latest approved image, and a resource that creates the VM from it, so the module does not hardcode an image ID."

### Resource dependencies

#### Implicit (preferred)

Terraform works out the order from references:

```hcl
resource "aws_instance" "app" {
  subnet_id = aws_subnet.private.id   # app waits for the subnet
}
```

#### Explicit

Only when there is no reference to infer from:

```hcl
resource "aws_instance" "app" {
  depends_on = [aws_iam_role_policy_attachment.app]
}
```

#### Tips

- Too many `depends_on` blocks slow the apply down and can cause cycles.
- `terraform graph | dot -Tsvg > graph.svg` shows the dependency graph.

### Essential commands

#### Everyday

| Command | What it does |
|---|---|
| `terraform init` | Set up the folder, download providers and modules |
| `terraform fmt` | Format the code |
| `terraform validate` | Check syntax and references |
| `terraform plan` | Preview the changes |
| `terraform apply` | Make the changes |
| `terraform destroy` | Delete everything managed here |
| `terraform output` | Show output values |

#### Useful

| Command | What it does |
|---|---|
| `terraform show` | Show the current state or a saved plan |
| `terraform plan -out=tfplan` | Save the plan for review |
| `terraform apply tfplan` | Apply exactly what was reviewed |
| `terraform plan -refresh-only` | See drift without proposing changes |
| `terraform console` | Try out expressions and functions |
| `terraform get` | Download or update modules |
| `terraform graph` | Print the dependency graph |

#### State and advanced

| Command | What it does |
|---|---|
| `terraform state list` | List managed resources |
| `terraform state show <addr>` | Show one resource's attributes |
| `terraform state mv <old> <new>` | Move or rename an address |
| `terraform state rm <addr>` | Stop managing it, without deleting it |
| `terraform state pull > backup.tfstate` | Back up the state |
| `terraform import <addr> <id>` | Bring an existing resource under management |
| `terraform apply -replace=<addr>` | Recreate one resource (replaces `taint`) |
| `terraform force-unlock <id>` | Remove a stuck lock, only after checking |
| `terraform workspace list / new / select` | Manage workspaces |

#### Deprecated, know the replacement

| Old | Use instead |
|---|---|
| `terraform refresh` | `terraform apply -refresh-only` |
| `terraform taint` | `terraform apply -replace=<address>` |

### Project structure

#### A normal root module

```text
main.tf         resources and module calls
variables.tf    input variables
outputs.tf      outputs
providers.tf    provider configuration
versions.tf     required_version and required_providers
backend.tf      where state is stored
dev.tfvars      values for this environment
```

#### The normal workflow

```text
write code -> init -> fmt -> validate -> plan -> review -> apply -> verify
```

### Scenario reminders

- Write the configuration **before** you import, and confirm the exact address and ID.
- `prevent_destroy` alone is not full protection. Add deletion protection, policy, and backups.
- Replace an image with a new launch template version plus instance refresh, or blue-green.
- Prefer separate root modules and state for long-lived dev, test, and production.
- A successful apply proves the API calls worked, not that the service works.

## Interview Questions

### 1. How have you used Terraform?

#### Short answer

I used Terraform to build cloud environments from code instead of clicking in the console.

#### Example of what I built

An application setup on AWS with:

- One VPC with public and private subnets
- Security groups
- A load balancer
- Auto scaling EC2 instances
- An RDS database
- IAM roles
- DNS records and alarms

#### How the work was organized

```text
modules/      # reusable code: vpc, compute, database
environments/ # dev, test, prod values
```

Every change went through a pull request. The pipeline ran `fmt`, `validate`, a security scan, and `plan`. Production apply needed an approval.

State was kept in a remote backend that was encrypted, versioned, and locked.

#### Interview answer

"I used Terraform to create repeatable environments. For example, I built a VPC with subnets, security groups, a load balancer, auto scaling servers, and an RDS database. I kept reusable code in modules and environment values in separate folders. All changes went through pull requests, and the pipeline ran plan first and applied only after approval."

### 2. What is the difference between Terraform and OpenTofu?

Terraform and OpenTofu are Infrastructure as Code tools with very similar configuration language and workflows. OpenTofu began as a fork after HashiCorp changed Terraform's license.

| Terraform | OpenTofu |
| --- | --- |
| Developed by HashiCorp | Community-governed under the Linux Foundation |
| Uses HashiCorp's source-available Business Source License for current releases | Uses the open-source Mozilla Public License 2.0 |
| Integrates with HCP Terraform and HashiCorp products | Focuses on an open, vendor-neutral ecosystem |
| Uses the `terraform` command | Uses the `tofu` command |

The main commands are similar:

```bash
terraform init
terraform plan
terraform apply
```

```bash
tofu init
tofu plan
tofu apply
```

Many configurations and providers work with both, but they are developed independently and compatibility should be tested before switching an existing project. Terraform can be practical for teams that use HashiCorp support and HCP Terraform. OpenTofu is attractive to teams that require an open-source, community-governed tool.

### 3. How would you create cloud resources with Terraform?

#### Steps

1. Collect the requirements: what resources, which region, networking, naming, cost.
2. Configure the provider and the remote backend.
3. Pin the Terraform and provider versions.
4. Write the resources, preferably by calling a module.
5. Use variables for values that change per environment.
6. Run the normal command flow.
7. Check the real resource in the cloud after apply.

#### Command flow

```bash
terraform fmt
terraform init
terraform validate
terraform plan -out=tfplan
terraform apply tfplan
```

#### Interview answer

"First I gather requirements, then I set the provider and remote backend and pin versions. I write resources using modules and variables. I run fmt, init, validate, plan, review the plan, and then apply the saved plan. After apply I check the resource in the cloud, because a successful apply only means the API calls worked."

### 4. What happens during init, plan, and apply?

| Command | What it does |
|---|---|
| `terraform init` | Sets up the folder: downloads providers and modules, configures the backend, writes `.terraform.lock.hcl` |
| `terraform plan` | Compares your code with the real infrastructure and shows what will be created, changed, or destroyed |
| `terraform apply` | Makes the changes and saves the result in state |

#### Points to remember

- Run `init` again when the backend, modules, or provider versions change.
- `plan` changes nothing. It is safe to run any time.
- `apply tfplan` applies exactly what you reviewed. `apply` without a saved plan makes a fresh plan.

#### Interview answer

"`init` prepares the working directory and downloads providers and modules. `plan` shows the difference between my code and the real infrastructure without changing anything. `apply` performs those changes and updates the state file. In pipelines I save the plan with `-out` and apply that file, so I apply exactly what was reviewed."

### 5. `terraform refresh` vs `terraform plan` *(asked in interview round)*

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

#### Interview answer

"Refresh updates the state file to match the real world; plan shows what apply would do. Plan refreshes in memory first and then shows the difference, without changing anything. The standalone refresh command is deprecated, so I use `plan -refresh-only` to review drift and `apply -refresh-only` when I want to record it in state."

### 6. What is the difference between stateful and stateless resources?

| Stateful | Stateless |
|---|---|
| Holds data: database, disk, storage bucket, queue | Holds no data: web server, container, VM behind a load balancer |
| Replacement needs backup and a data plan | Can be replaced freely |
| Delete is dangerous | Delete is normal |
| Use `prevent_destroy` and deletion protection | Use immutable replacement and health checks |

#### Important point

The Terraform state file is not a backup of your data. It only records resource IDs and attributes.

#### Interview answer

"Stateful resources hold business data, like databases, disks, and buckets, so replacing them needs backups, replication, and a cutover plan. Stateless resources such as web servers keep no data and can be recreated behind a load balancer. I also mention that the Terraform state file is not a data backup; it only tracks resource details."

### 7. What dependencies are needed for an IP address or networking resource?

**Answer:**

It depends on the address type and the traffic path.

A public-facing EC2 instance typically needs a VPC, a subnet that assigns public IPs, an internet gateway with a route, a network ACL, a security group, and an Elastic IP association.

A private address may need route tables, NAT or another egress path, DNS, peering or transit routing, or a load balancer in front of it.

Where one resource references another, like `subnet_id = aws_subnet.public.id`, Terraform works out the order on its own. I prefer that over `depends_on`, because the reference also documents the real relationship between the resources. I only reach for `depends_on` when there's a dependency Terraform can't see from an attribute — for example, waiting for a policy attachment to finish before a service calls an API.

After apply, I check the real thing: that routing works, ACLs and security groups behave as expected, DNS resolves, and the application port responds from the actual source.

### 8. How do you gather requirements before writing Terraform code?

#### Questions I ask

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

#### Then

Turn the repeated patterns into modules, keep environment values outside modules, and agree on acceptance tests and rollback before writing code.

#### Interview answer

"I write a short requirements list first: resources, environments, networking, security, naming and tagging standards, scaling, availability, backup, cost, and ownership. I also check what already exists and must be imported. Then I turn repeated patterns into modules, keep environment values at the root, and agree on acceptance tests and a rollback plan before I start coding."

### 9. What challenges have you faced with Terraform?

#### Common challenges

| Challenge | How I handle it |
|---|---|
| Two people applying at once | Remote backend with locking, apply only from the pipeline |
| Manual changes in the console (drift) | Scheduled plan, restrict console write access |
| Importing old resources | Write the code first, then import one resource at a time |
| Accidental delete or replace | `prevent_destroy`, review the plan, approvals |
| Secrets ending up in state | Encrypted backend, restricted access |
| Slow plans on big projects | Split into smaller states |
| Provider upgrades breaking code | Pin versions, commit the lock file, upgrade in a separate PR |

#### Interview answer

"The most common ones are drift from manual changes, state conflicts when two people apply together, slow plans on large projects, accidental replacement of resources, and provider version upgrades breaking things. I handle them with locked remote state, smaller state files, pinned versions, reviewed plans, and production approvals."
