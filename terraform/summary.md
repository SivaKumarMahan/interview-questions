# Terraform Summary

Quick reference: core concepts, commands, and the functions that come up most often.

---

## 1. Terraform Enterprise in simple words

### The idea

- **Terraform CLI (open source)** — you run Terraform on your own machine. The state file sits with you, and nobody else knows what you did.
- **Terraform Enterprise** — the company runs Terraform centrally, with shared state, rules, approvals, and a record of who changed what.

Think of it as personal notes versus a shared company drive.

### Problems it solves

| Without it | With Terraform Enterprise |
|---|---|
| Everyone has their own state file | One central state |
| Anyone can destroy something | Role-based access control |
| No record of who changed what | Audit logs |
| Someone applies from a laptop | Runs happen on secure workers |
| No guardrails | Sentinel policies block bad plans |

### How a run works

1. A developer pushes Terraform code to Git.
2. Terraform Enterprise sees the change and starts a run.
3. It runs `terraform plan` on a worker.
4. A reviewer approves.
5. It runs `terraform apply` on the worker.
6. The new state version is stored centrally.

### Main features

| Feature | Meaning |
|---|---|
| Workspaces | Separate state and variables per environment |
| Remote state | State stored centrally, with version history |
| VCS integration | A Git push starts a run |
| Sentinel | Policy rules, for example "only allow the West Europe region" |
| RBAC | Who can view, plan, or apply |
| Private module registry | Share company modules internally |
| Audit logs | Who did what and when |

### One-line definition

"Terraform Enterprise is HashiCorp's self-hosted platform for running Terraform centrally, with remote runs, managed state, access control, policy enforcement, and audit logs."

---

## 2. Resource vs data source

### Resource

Terraform **creates and manages** it.

```hcl
resource "google_compute_instance" "vm" {
  name         = "my-vm"
  machine_type = "e2-medium"
  zone         = "us-central1-a"
}
```

### Data source

Terraform only **reads** it. Nothing is created or changed.

```hcl
data "google_compute_image" "ubuntu" {
  family  = "ubuntu-2204-lts"
  project = "ubuntu-os-cloud"
}
```

### Using both together

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

### Interview answer

"A resource is something Terraform creates, updates, and deletes. A data source is read-only, used to look up something that already exists. A common pattern is a data source that finds the latest approved image, and a resource that creates the VM from it, so the module does not hardcode an image ID."

---

## 3. What is a module?

A module is a folder of Terraform code that you can reuse.

- **Local module:** `./modules/vm`
- **Remote module:** from the registry or a Git repo

### Why use one

1. Write once, use many times.
2. Keep the code organised.
3. Every team gets the same standards.

### Example

Instead of copying the same VM block everywhere:

```hcl
module "app_server" {
  source       = "./modules/gcp_vm"
  vm_name      = "app-server"
  machine_type = "e2-medium"
}

module "web_server" {
  source       = "./modules/gcp_vm"
  vm_name      = "web-server"
  machine_type = "e2-small"
}
```

### Interview answer

"A module is a reusable folder of Terraform code with defined inputs and outputs. Instead of copying the same resource blocks into every project, I put the pattern in a module, version it, and call it with different variables. That gives reuse and also consistent tagging, encryption, and naming."

---

## 4. Essential commands

### Everyday

| Command | What it does |
|---|---|
| `terraform init` | Set up the folder, download providers and modules |
| `terraform fmt` | Format the code |
| `terraform validate` | Check syntax and references |
| `terraform plan` | Preview the changes |
| `terraform apply` | Make the changes |
| `terraform destroy` | Delete everything managed here |
| `terraform output` | Show output values |

### Useful

| Command | What it does |
|---|---|
| `terraform show` | Show the current state or a saved plan |
| `terraform plan -out=tfplan` | Save the plan for review |
| `terraform apply tfplan` | Apply exactly what was reviewed |
| `terraform plan -refresh-only` | See drift without proposing changes |
| `terraform console` | Try out expressions and functions |
| `terraform get` | Download or update modules |
| `terraform graph` | Print the dependency graph |

### State and advanced

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

### Deprecated, know the replacement

| Old | Use instead |
|---|---|
| `terraform refresh` | `terraform apply -refresh-only` |
| `terraform taint` | `terraform apply -replace=<address>` |

---

## 5. Project structure

### A normal root module

```text
main.tf         resources and module calls
variables.tf    input variables
outputs.tf      outputs
providers.tf    provider configuration
versions.tf     required_version and required_providers
backend.tf      where state is stored
dev.tfvars      values for this environment
```

### The normal workflow

```text
write code -> init -> fmt -> validate -> plan -> review -> apply -> verify
```

---

## 6. Core blocks

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

### Example

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

---

## 7. Root and child modules

- The folder you run Terraform in is the **root module**.
- Anything called with a `module` block is a **child module**.

### How values flow

```text
tfvars -> root variables -> module inputs -> resources
resources -> module outputs -> root outputs
```

### Rules for a good child module

1. One purpose.
2. Typed inputs with validation.
3. Useful outputs.
4. No environment names or credentials inside.
5. Provider configuration stays at the root.
6. Documented and versioned.

---

## 8. Meta-arguments

| Meta-argument | What it does |
|---|---|
| `count` | Numbered instances, good for identical copies |
| `for_each` | Named instances from a map or set, good when each has an identity |
| `depends_on` | A dependency Terraform cannot infer |
| `lifecycle` | Controls replacement and drift behaviour |
| `provider` | Picks a provider alias |

### `for_each` with a simple map

```hcl
variable "resource_groups" {
  type = map(string)

  default = {
    dev  = "dev-rg"
    test = "test-rg"
    prod = "prod-rg"
  }
}

resource "azurerm_resource_group" "this" {
  for_each = var.resource_groups
  name     = each.value
  location = "centralindia"
}
```

Addresses become `azurerm_resource_group.this["dev"]`, and so on.

### `for_each` with a map of objects

```hcl
variable "storage_accounts" {
  type = map(object({
    name     = string
    location = string
    tier     = string
  }))
}

resource "azurerm_storage_account" "this" {
  for_each                 = var.storage_accounts
  name                     = each.value.name
  location                 = each.value.location
  account_tier             = each.value.tier
  resource_group_name      = azurerm_resource_group.main.name
  account_replication_type = "LRS"
}
```

`each.key` is the map key, `each.value` is the whole object.

### `for_each` over a list of names

```hcl
resource "azurerm_resource_group" "this" {
  for_each = toset(var.resource_group_names)
  name     = each.value
  location = var.location
}
```

`toset()` removes duplicates. If duplicates mean the input is wrong, reject them with validation instead of hiding them.

---

## 9. State and locking

### What state is

A file that maps each Terraform address to the real resource ID, plus the attributes needed to build a plan. It is not your source code and not a backup of your data.

### Locking

Locking stops two applies writing at the same time. If someone else holds it:

```text
Error: Error acquiring the state lock
  ID:   4f1c8b32-...
  Who:  runner@ci-agent-3
```

Wait, or stop that job cleanly. Only after proving nothing is running:

```bash
terraform force-unlock 4f1c8b32-...
```

### Console change example

Someone edits an EC2 instance in the AWS console. Terraform does **not** update your `.tf` files.

1. `terraform plan -refresh-only` to see the drift without proposing changes.
2. Decide whether the change should stay.
3. To keep it, update the code and review a normal plan.
4. To reject it, apply the reviewed plan so Terraform restores the declared value.

### Backend note

Current Terraform versions can lock the S3 backend with `use_lockfile = true`. The older DynamoDB lock table still exists in many projects but is the legacy approach.

---

## 10. Scenario reminders

- Write the configuration **before** you import, and confirm the exact address and ID.
- `prevent_destroy` alone is not full protection. Add deletion protection, policy, and backups.
- Replace an image with a new launch template version plus instance refresh, or blue-green.
- Prefer separate root modules and state for long-lived dev, test, and production.
- A successful apply proves the API calls worked, not that the service works.

---

## 11. Functions you actually use

Try any of these with `terraform console`.

### List functions

**`length()`** — how many items.

```hcl
length(["a", "b", "c"])   # 3
```

**`element()`** — item at an index.

```hcl
element(["Mon", "Tue", "Wed"], 2)   # "Wed"
```

**`slice()`** — a part of a list, end index not included.

```hcl
slice([1, 2, 3, 4, 5], 1, 3)   # [2, 3]
```

**`concat()`** — join lists together.

```hcl
concat(["a", "b"], ["c"])   # ["a", "b", "c"]
```

**`flatten()`** — turn nested lists into one list.

```hcl
flatten([["a", "b"], ["c"], ["d"]])   # ["a", "b", "c", "d"]
```

**`distinct()`** — remove duplicates, keep the order.

```hcl
distinct(["a", "b", "a", "c"])   # ["a", "b", "c"]
```

**`compact()`** — remove empty and null values.

```hcl
compact(["apple", "", "mango", null])   # ["apple", "mango"]
```

**`formatlist()`** — format every item.

```hcl
formatlist("app-%s", ["web", "api"])   # ["app-web", "app-api"]
```

**`toset()`** — convert a list to a set, for `for_each`.

```hcl
toset(["a", "b", "a"])   # ["a", "b"]
```

---

### Map functions

**`keys()` and `values()`**

```hcl
keys({ env = "prod", app = "web" })     # ["app", "env"]
values({ env = "prod", app = "web" })   # ["web", "prod"]
```

**`lookup()`** — read a key with a fallback.

```hcl
variable "db_urls" {
  type = map(string)

  default = {
    dev  = "dev-db.internal"
    prod = "prod-db.internal"
  }
}

output "db_url" {
  value = lookup(var.db_urls, var.environment, "localhost")
}
```

**`merge()`** — combine maps. Later maps win.

```hcl
merge({ Env = "dev", Owner = "team-a" }, { Env = "prod" })
# { Env = "prod", Owner = "team-a" }
```

This is the usual way to build tags:

```hcl
locals {
  tags = merge(var.common_tags, { Component = "database" })
}
```

**`zipmap()`** — build a map from two lists.

```hcl
zipmap(["timeout", "retries"], [30, 5])
# { timeout = 30, retries = 5 }
```

**`for` expression** — transform a map.

```hcl
locals {
  prices = { apple = 0.5, banana = 0.3 }

  discounted = { for name, price in local.prices : name => price * 0.9 }
  # { apple = 0.45, banana = 0.27 }
}
```

**Build a `for_each` map from a list of objects**

```hcl
locals {
  users_map = { for u in var.users : u.name => u }
}
```

---

### String functions

**`format()`** — build a string from a pattern.

```hcl
format("web-%s-%02d", "prod", 3)   # "web-prod-03"
```

**`join()` and `split()`**

```hcl
join(",", ["a", "b", "c"])       # "a,b,c"
split(",", "a,b,c")              # ["a", "b", "c"]
split("@", "user1@example.com")  # ["user1", "example.com"]
```

**`replace()`**

```hcl
replace("my.app.name", ".", "-")   # "my-app-name"
```

**`upper()`, `lower()`, `title()`**

```hcl
upper("prod")         # "PROD"
lower("PROD")         # "prod"
title("hello world")  # "Hello World"
```

**`trimspace()` and `chomp()`** — remove spaces or a trailing newline. Useful after `file()`.

```hcl
chomp(file("${path.module}/version.txt"))
```

**`substr()`**

```hcl
substr("terraform", 0, 4)   # "terr"
```

---

### Number and network functions

**`min()`, `max()`, `abs()`, `ceil()`, `floor()`**

```hcl
max(3, 7, 2)   # 7
ceil(4.1)      # 5
```

**`cidrsubnet()`** — split a network into subnets.

```hcl
cidrsubnet("10.0.0.0/16", 8, 0)   # "10.0.0.0/24"
cidrsubnet("10.0.0.0/16", 8, 1)   # "10.0.1.0/24"
```

```hcl
locals {
  subnets = [for i in range(3) : cidrsubnet("10.0.0.0/16", 8, i)]
}
```

**`cidrhost()`** — a specific address inside a network.

```hcl
cidrhost("10.0.1.0/24", 10)   # "10.0.1.10"
```

---

### Validation and safety

**`can()`** — true if the expression works.

```hcl
can(regex("^t3\\.", var.instance_type))
```

**`try()`** — return the first value that works.

```hcl
locals {
  region = try(var.region, "us-east-1")
}
```

**Use them in variable validation**

```hcl
variable "environment" {
  type = string

  validation {
    condition     = contains(["dev", "test", "prod"], var.environment)
    error_message = "Environment must be dev, test, or prod."
  }
}
```

---

### File functions

**`file()`** — read a file as a string. The file must exist before Terraform runs.

```hcl
locals {
  startup_script = file("${path.module}/startup.sh")
}
```

**`templatefile()`** — read a file and fill in variables. Better than `file()` for scripts and config.

```hcl
user_data = templatefile("${path.module}/init.sh.tftpl", {
  app_name = var.app_name
  port     = 8080
})
```

**`fileexists()`, `basename()`, `dirname()`, `abspath()`**

```hcl
fileexists("${path.module}/config.txt")   # true or false
basename("/tmp/app/main.tf")              # "main.tf"
dirname("/tmp/app/main.tf")               # "/tmp/app"
```

### Path values

| Value | Meaning |
|---|---|
| `path.module` | Folder of the current module |
| `path.root` | Folder of the root module |
| `path.cwd` | Current working directory |

---

### Encoding functions

**`jsonencode()` and `jsondecode()`**

```hcl
policy = jsonencode({
  Version = "2012-10-17"
  Statement = [{
    Effect   = "Allow"
    Action   = "s3:GetObject"
    Resource = "${aws_s3_bucket.app.arn}/*"
  }]
})
```

```hcl
locals {
  users = jsondecode(file("${path.module}/users.json"))
}
```

**`yamlencode()` and `yamldecode()`** — the same idea for YAML.

**`base64encode()` and `base64decode()`**

```hcl
resource "aws_instance" "web" {
  user_data = base64encode(file("${path.module}/init.sh"))
}
```

---

## 12. An Azure setup pattern

### Modules to build

```text
resource group
virtual network + subnets + NSGs
private DNS and private endpoints
storage account
key vault
log analytics + application insights
container registry
AKS cluster
database
role assignments
```

### How to split state

By lifecycle and ownership, not by team preference:

```text
connectivity-state   hub network, DNS, firewall
platform-state       AKS, ACR, monitoring
data-state           databases, storage
app-state            application resources
```

### Pipeline

```bash
terraform fmt -check
terraform init
terraform validate
checkov -d .
terraform plan -out=tfplan
# approval
terraform apply tfplan
```

### After apply, check

Private DNS resolves, routes work, RBAC has propagated, diagnostics are arriving in Log Analytics, AKS can pull from ACR, and the application health endpoint responds.

### Secrets

Terraform creates the Key Vault and grants access to the managed identity. The application reads the secret at runtime, so the value never passes through Terraform state.
