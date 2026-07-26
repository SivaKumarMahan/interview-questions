# Terraform Interview Summary

## 1. Terraform Enterprise in Easy Way

### 🌱 Step 1: Imagine a Real-Life Example

Suppose you and your team need to build houses (infrastructure).

- **Terraform Open Source (CLI)** = You build your house alone with your own tools. You decide everything, you save the blueprint in your notebook, and no one else knows what you did.
- **Terraform Enterprise (TFE)** = Your entire company is building 100s of houses together. You need:
  1. Shared blueprints 📘
  2. Central storage of designs 🗄️
  3. Rules (policies) ⚖️
  4. Manager approvals ✅
  5. Record of who built what 📝

So TFE is like a construction company's project management system for Terraform.

### 🌱 Step 2: What Problem Does TFE Solve?

If teams only use Terraform open-source:

- ❌ Everyone keeps their own state files → conflicts happen
- ❌ No security → anyone can destroy infra by mistake
- ❌ No tracking → you don't know who changed what
- ❌ No automation → someone must run `terraform apply` from their laptop

Terraform Enterprise fixes this:

- ✅ **Centralized state** → No conflicts
- ✅ **Secure remote execution** → No one runs risky code on laptops
- ✅ **Access control** → Only right people can apply
- ✅ **Policies** → Prevent mistakes (like creating expensive servers)
- ✅ **Automation** → Connects with GitHub to auto-deploy

### 🌱 Step 3: How TFE Works (Super Simple Flow)

1. Developer writes Terraform code (example: create VM in AWS).
2. Pushes code to GitHub.
3. Terraform Enterprise notices change → runs `terraform plan`.
4. Manager approves the plan.
5. TFE applies changes in a secure environment.
6. State is stored safely in TFE (not on anyone's laptop).

### 🌱 Step 4: Key Features (Easy Words)

1. **Workspaces** → Like separate folders for Dev, Test, and Prod environments.
2. **Remote State** → State is stored in TFE, not on your computer.
3. **VCS Integration** → Connect GitHub/GitLab, auto-run Terraform when code changes.
4. **Sentinel** → Rules engine (example: "Only allow servers in Mumbai region").
5. **RBAC (Role Based Access Control)** → Control who can view, plan, or apply.
6. **Private Module Registry** → Share reusable Terraform code inside your company.
7. **Audit Logs** → See who made changes and when.

### 🌱 Step 5: Very Simple Analogy

1. **Terraform OSS** = Personal diary 📝 (only you can see and use it).
2. **Terraform Enterprise** = Company's Google Drive 📂 (shared, secure, tracked, access-controlled).

### 🌱 Step 6: One-Line Interview Definition

👉 Terraform Enterprise is HashiCorp's commercial version of Terraform that helps teams work together on infrastructure safely. It provides remote execution, secure state management, version control integration, role-based access, and policy enforcement.

---

## 2. Q: In Terraform, what is the difference between a resource and a data source?

Can you also give a real-world example of when you would use each one?

**Ans:**

### 1. Resource

A **resource** is something Terraform creates, updates, or deletes in your infrastructure.

Example: Creating a VM, database, storage bucket, etc.

Example Code:

```hcl
resource "google_compute_instance" "vm" {
  name         = "my-vm"
  machine_type = "e2-medium"
  zone         = "us-central1-a"
}
```

💡 Here, Terraform will create the VM in GCP.

### 2. Data Source

A **data source** is read-only — Terraform uses it to fetch existing information from your infrastructure but doesn't create or change anything.

Example: Getting the latest image ID of Ubuntu from GCP to use in a new VM.

Example Code:

```hcl
data "google_compute_image" "ubuntu" {
  family  = "ubuntu-2004-lts"
  project = "ubuntu-os-cloud"
}
```

💡 Here, Terraform just reads the Ubuntu image details; it doesn't create an image.

**Real-World Example of Both Together:**

If you want to create a VM with the latest Ubuntu OS:

1. Use a **data source** to get the latest Ubuntu image.
2. Use a **resource** to create the VM with that image.

---

## 3. Q: What is a Terraform Module, and why would you use one?

Can you also give a real-world example of a module in a project?

**Ans: Terraform Module (Easy Explanation)**

- A **module** in Terraform is like a reusable folder of Terraform code.
- Instead of writing the same code again and again, you put it in a module and reuse it in multiple places.
- A module can be **local** (in your project) or **remote** (downloaded from Terraform Registry or GitHub).

**Why use a Module?**

1. **Reusability** – Write once, use many times.
2. **Organization** – Keep your code clean and structured.
3. **Team Collaboration** – Different teams can share the same module.

**Real-World Example:**

Suppose you often create a Google Cloud VM with the same settings:

1. Machine type: `e2-medium`
2. OS: Ubuntu
3. Startup script installed

Instead of copy-pasting the code every time, you put it in a module called `gcp_vm`.

```hcl
module "app_server" {
  source       = "./modules/gcp_vm"
  vm_name      = "app-server"
  machine_type = "e2-medium"
}
```

Now, whenever you need another VM, just call the module again with different variables — no rewriting needed.

---

## 4. 🚀 Essential Commands

- `terraform init` – Set up your working directory and download providers.
- `terraform validate` – Check your configuration for syntax or logic errors.
- `terraform plan` – Preview what Terraform will do before you apply changes.
- `terraform apply` – Apply changes to reach the desired infrastructure state.
- `terraform destroy` – Remove all managed resources (use with care).

### 🧰 Helpful Utilities

- `terraform fmt` – Automatically format your configuration files.
- `terraform plan -refresh-only` / `terraform apply -refresh-only` – Review and then record remote drift in state without changing infrastructure; prefer these over the deprecated `terraform refresh`.
- `terraform output` – Display outputs defined in your configuration.
- `terraform show` – Inspect the current state or saved plans.
- `terraform get` – Installs/upgrades modules.

### ⚙️ Advanced Operations

- `terraform state` – Interact directly with the state file.
- `terraform import` – Bring existing infrastructure under Terraform management.
- `terraform workspace` – Manage multiple environments (e.g. dev, staging, prod).
- `terraform plan -replace=<address>` / `terraform apply -replace=<address>` – Review and replace a damaged resource; prefer this over the deprecated `terraform taint`.

### 🔐 Authentication & Providers

- `terraform login` – Authenticate with Terraform Cloud.
- `terraform providers` – List all required providers for your configuration.

---

## Structured Terraform Revision Notes

### Workflow and project structure

The normal lifecycle is write configuration → `init` → `fmt`/`validate` → reviewed `plan` → approved `apply` → post-apply verification. Common files include `main.tf`, `variables.tf`, `outputs.tf`, `providers.tf`, `versions.tf`, backend configuration, environment values, and reusable modules. Remote state should be encrypted, access controlled, versioned, audited, and locked.

### Core configuration blocks

- `terraform` declares required Terraform/provider versions and backend settings; a backend stores state but is not a standalone top-level `backend` block.
- `provider` configures access to a platform API; use aliases for multiple regions, subscriptions, or accounts.
- `resource` creates or manages infrastructure, while `data` reads existing information without creating it.
- `variable` defines typed inputs, `locals` defines reusable expressions, and `output` exposes selected values.
- `module` calls a reusable child module with an explicit input/output contract.

### Parent and child modules

The root module orchestrates child modules such as network, compute, database, security, storage, and monitoring. Child modules expose a small input/output contract and hide implementation detail. Values flow from root variables into module inputs; child outputs become inputs to other components only through explicit root wiring.

Good modules are focused, documented, versioned, tested, and free of hardcoded environment names or credentials. Keep provider configuration and environment orchestration at the root where practical. Module version pinning and migration notes prevent one team from breaking every consumer.

### `for_each` with a nested map

A map of objects lets one resource block create stable instances keyed by names such as `dev` and `prod`:

```hcl
variable "storage_accounts" {
  type = map(object({
    name     = string
    location = string
    tier     = string
  }))
}

resource "azurerm_storage_account" "example" {
  for_each                 = var.storage_accounts
  name                     = each.value.name
  location                 = each.value.location
  account_tier             = each.value.tier
  resource_group_name      = "demo-rg"
  account_replication_type = "LRS"
}
```

`each.key` is the stable map key and `each.value` is the complete object. Stable keys make additions and removals easier to review than positional list indexes. This pattern supports environment, region, team, or component maps, but separate state boundaries are still needed when ownership or blast radius differs.

For a list of unique strings, `for_each = toset(var.names)` converts the list to a set whose strings become stable instance keys. Sets are unordered and automatically discard duplicates, so this is appropriate only when uniqueness is intended:

```hcl
resource "azurerm_resource_group" "example" {
  for_each = toset(var.resource_group_names)
  name     = each.value
  location = var.location
}
```

If duplicates indicate bad input, reject them with variable validation instead of silently relying on `toset()`. Use a map of objects when instances need additional per-item attributes.

### Scenario reminders

- Import an existing object only after writing matching configuration and confirming the exact resource address and ID.
- Protect critical resources through reviewed plans, lifecycle controls, provider deletion protection, policy, and backups; `prevent_destroy` alone is not a complete safeguard.
- Use launch templates and autoscaling instance refresh or a blue-green pattern for AMI replacement without avoidable downtime.
- Prefer explicit root modules and separate state for long-lived Dev, QA, and Production boundaries; use workspaces only when their shared configuration and access model is appropriate.

## Meta-Arguments and State Locking

Meta-arguments change how Terraform manages a resource or module:

- `count` creates numbered instances and is suitable when instances are interchangeable.
- `for_each` creates instances with stable map/set keys and is safer when each instance has an identity such as `dev`, `test`, or `prod`.
- `depends_on` declares a dependency Terraform cannot infer from value references; inferred dependencies are preferred when possible.
- `lifecycle` controls replacement and drift behavior through options such as `create_before_destroy`, `prevent_destroy`, and carefully scoped `ignore_changes`.
- `provider` selects a provider configuration or alias, for example a different subscription or region.

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
  location = "Central India"
}
```

State locking prevents concurrent writers from corrupting state or applying incompatible plans. A team backend should provide locking, encryption, access control, version history, and audit logging. If another run holds the lock, identify its owner and active pipeline and wait or stop that run cleanly. Use `terraform force-unlock <LOCK_ID>` or break a backend lease only after proving no operation is running, recording the incident, and backing up or versioning state; an incorrect forced unlock can allow two applies to write concurrently.

The safe team flow is one reviewed plan per state boundary, serialized apply, immutable CI logs, and post-apply verification. Split unrelated environments and components into separate state when their ownership, release cadence, privileges, or blast radius differ.

### State, collaboration, and console drift

State maps Terraform resource addresses to remote object IDs and records the attributes needed to calculate dependency-aware plans. It is not the source code or a general-purpose inventory. Treat it as sensitive because it can contain infrastructure metadata and secret values; keep it in a protected remote backend rather than Git or individual laptops.

When two engineers use the same configuration, the shared backend and locking serialize writes. Before changing anything, pull the reviewed branch and run a fresh plan against the correct backend/workspace. The plan refreshes remote objects in memory and shows whether another apply or an out-of-band change has altered them; backend version history, CI logs, and cloud audit logs show who changed what.

If someone edits an EC2 resource in the AWS Console, Terraform does **not** automatically rewrite the `.tf` files:

1. Run `terraform plan -refresh-only` to review the drift without proposing infrastructure changes.
2. Decide whether the console change is authorized and should become the desired state.
3. To keep it, update the HCL and review a normal plan; optionally apply the reviewed refresh-only plan to record current remote values in state.
4. To reject it, run a reviewed normal plan/apply so Terraform restores the declared configuration.

Use `terraform import` for an existing object that Terraform does not yet manage. Import associates the object with a resource address; configuration must still be written and reviewed. Configuration generation can provide a starting template for supported imports, but generated HCL must be cleaned up and validated rather than accepted blindly.

One common AWS team architecture uses small root modules and reusable child modules, with separate states for environments or components. CI assumes a short-lived IAM role, creates and publishes the plan, and performs the protected apply. The S3 backend stores encrypted state in a versioned, access-logged bucket; current Terraform versions can enable S3 lockfile locking with `use_lockfile = true`. Restrict state and lock-object paths by IAM and provide a tested recovery procedure. DynamoDB-based S3 locking is deprecated, so describe it as a legacy implementation only when that is what the project actually uses.

## Terraform Functions Reference

The most commonly used Terraform built-in functions, grouped by category.

### List functions

**`formatlist()`** — produces a list of strings by formatting several values according to a specification string. Useful for applying a consistent formatting pattern across list elements.

```hcl
locals {
  fruits         = ["apple", "banana", "orange"]
  formatted_list = formatlist("I like %s.", local.fruits)
}

output "formatted_list_output" {
  value = local.formatted_list
}
# formatted_list_output = ["I like apple.", "I like banana.", "I like orange."]
```

**`flatten()`** — transforms a nested list or tuple into a flat list.

```hcl
locals {
  nested_list = [
    ["item1", "item2"],
    ["item3", "item4", "item5"],
    ["item6"],
  ]
  flat_list = flatten(local.nested_list)
}

output "flat_list_output" {
  value = local.flat_list
}
```

**`concat()`** — concatenates two or more lists into a single list.

```hcl
variable "list1" {
  default = ["a", "b", "c"]
}
variable "list2" {
  default = ["d", "e", "f"]
}
output "combined_list" {
  value = concat(var.list1, var.list2)
}
```

**`element()`** — retrieves an element from a list at a specified index.

```hcl
locals {
  weekdays      = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
  third_weekday = element(local.weekdays, 2)  # "Wednesday"
}
```

**`slice()`** — extracts a sublist, given a starting index and an (exclusive) ending index.

```hcl
locals {
  numbers          = [1, 2, 3, 4, 5]
  selected_numbers = slice(local.numbers, 1, 3)  # [2, 3]
}
```

**`compact()`** — takes a list of strings and returns a new list with any null or empty-string elements removed.

```text
> compact(["apple", "", "mango", null, "grape"])
["apple", "mango", "grape"]
```

**`distinct()`** — removes duplicates from a list, keeping the first occurrence of each value and preserving relative ordering.

```text
> distinct(["a", "b", "a", "c", "d", "b"])
["a", "b", "c", "d"]
```

### Map functions

**`merge()`** — combines multiple maps into a single map (`merge(map1, map2, …)`). Useful for aggregating configuration from multiple sources into flexible, modular configs. Later maps override earlier keys.

```hcl
variable "base_config" {
  type    = map(string)
  default = { key1 = "value1", key2 = "value2" }
}
variable "additional_config" {
  type    = map(string)
  default = { key2 = "new_value2", key3 = "value3" }
}
output "extended_config" {
  value = merge(var.base_config, var.additional_config)
}
```

**`lookup()`** — safely accesses the value of a key in a map, returning a default if the key does not exist. Useful for dynamically fetching values from variable configurations.

```hcl
variable "environment_vars" {
  type = map(string)
  default = {
    dev  = "dev-database-url"
    prod = "prod-database-url"
  }
}
variable "current_environment" {
  type    = string
  default = "prod"
}
output "database_url" {
  value = lookup(var.environment_vars, var.current_environment, "default-database-url")
}
```

**`zipmap()`** — creates a map by pairing elements from two lists (keys and values).

```hcl
variable "config_keys" {
  type    = list(string)
  default = ["max_connections", "timeout", "retry_limit"]
}
variable "config_values" {
  type    = list(number)
  default = [100, 30, 5]
}
output "application_config" {
  value = zipmap(var.config_keys, var.config_values)
}
```

It is also handy for dynamically assigning tags to resources:

```hcl
variable "resource_names" {
  type    = list(string)
  default = ["web", "db", "app"]
}
resource "aws_instance" "example" {
  count         = length(var.resource_names)
  ami           = "ami-0c55b159cbfafe1f0"
  instance_type = "t2.micro"
  tags          = zipmap(["Name"], [var.resource_names[count.index]])
}
```

## Azure Infrastructure Automation Pattern

For Azure, compose reviewed modules for resource groups, VNets/subnets, NSGs, private DNS/endpoints, storage, Key Vault, Log Analytics/Application Insights, ACR, AKS, databases, role assignments and the required ingress/egress components. Modules should expose stable inputs and outputs, keep environment-specific values at the root, and avoid creating a tightly coupled all-in-one state file. State boundaries normally follow lifecycle and ownership, for example connectivity, shared platform, data and application environments.

Run `fmt`, `validate`, security/policy checks and a plan in CI; use an encrypted/versioned remote backend with locking and apply only an approved saved plan through a protected environment. Terraform creates infrastructure and grants identities, but applications should retrieve secrets at runtime through managed identity and Key Vault rather than passing secret values through state. After apply, verify private DNS, routes, RBAC propagation, diagnostic ingestion, AKS/ACR access and the user-facing health path.

**`length()`** — returns the length of a list, string, or map. **`keys()`** — returns a list of a map's keys. **`values()`** — returns a list of a map's values.

```hcl
variable "tags" {
  type = map(string)
  default = {
    "Name" = "my-instance"
    "Env"  = "production"
    "App"  = "web"
  }
}
locals {
  tag_count  = length(var.tags)
  tag_keys   = keys(var.tags)
  tag_values = values(var.tags)
}
```

**Transforming a map with a `for` expression** — to transform the values of a map, use an object `for` expression. (The old `map()` function was removed in Terraform 0.12+; use the comprehension form instead.)

```hcl
locals {
  prices = {
    apple  = 0.5
    banana = 0.3
    orange = 0.7
  }
  discounted_prices = { for fruit, price in local.prices : fruit => price * 0.9 }
}
```

### String functions

**`format()`** — creates a formatted string by substituting values into placeholders.

```hcl
variable "environment" {
  type    = string
  default = "dev"
}
resource "aws_instance" "example" {
  count         = 3
  ami           = "ami-0c55b159cbfafe1f0"
  instance_type = "t2.micro"
  tags = {
    Name = format("instance-%s-%02d", var.environment, count.index + 1)
  }
}
```

**`replace()`** — replaces occurrences of a substring with another (`replace(string, search, replace)`).

```hcl
variable "file_paths" {
  type    = list(string)
  default = ["C:\\Users\\user1\\documents\\file1.txt", "D:\\Data\\file2.txt", "E:\\Projects\\file3.txt"]
}
output "standardized_file_paths" {
  value = [for path in var.file_paths : replace(path, "\\", "/")]
}
```

**`split()`** — splits a string into a list of substrings based on a delimiter. Below, the name part of each email builds a dynamic instance name, and `replace` swaps dots for hyphens:

```hcl
variable "user_emails" {
  type    = list(string)
  default = ["user1@example.com", "user2@example.com", "user3@example.com"]
}
resource "aws_instance" "user_instances" {
  count         = length(var.user_emails)
  ami           = "ami-0c55b159cbfafe1f0"
  instance_type = "t2.micro"
  tags = {
    Name = replace(split("@", var.user_emails[count.index])[0], ".", "-")
  }
}
```

**`join()`** — concatenates a list of strings into a single string separated by a delimiter.

```hcl
locals {
  join_string = join(",", ["a", "b", "c"])  # "a,b,c"
}
output "join_string" {
  value = local.join_string
}
```

**`title()` / `upper()` / `lower()`** — change letter casing.

```text
> title("hello world")
Hello World
> upper("Hello World")
HELLO WORLD
> lower("HELLO WORLD")
hello world
```

**`chomp()`** — trims trailing newline characters from a string. Useful when reading content with `file()` and removing unwanted trailing `\n`.

```hcl
variable "file_path" {
  type    = string
  default = "path/to/file.txt"
}
output "file_content" {
  value = chomp(file(var.file_path))
}
```

### Validation and error handling

**`can()` / `try()`** handle situations where a value may not exist or may be null, making configurations more robust.

**`can()`** evaluates an expression and returns `true` if it succeeds (exists and is non-null), or `false` if it errors:

```hcl
variable "example_variable" {
  type = string
}
locals {
  variable_exists = can(var.example_variable)
}
```

**`try()`** returns the first argument that evaluates without error, providing a fallback for null/missing values:

```hcl
variable "example_variable" {
  type    = string
  default = null
}
locals {
  safe_variable = try(var.example_variable, "default_value")
}
```

### File functions

**`abspath()`** — converts a relative path to an absolute path.

```hcl
locals {
  relative_path = "main.tf"
  absolute_path = abspath(local.relative_path)
}
output "absolute_path_output" {
  value = local.absolute_path
}
# absolute_path_output = "/Users/akhileshmishra3/terraform-blogs/main.tf"
```

**`basename()`** — extracts the filename (last component) from a path.

```hcl
locals {
  file_path = "/Users/akhileshmishra3/terraform-blogs/main.tf"
  file_name = basename(local.file_path)  # "main.tf"
}
```

**`fileexists()`** — checks whether a file exists at the given path.

```hcl
variable "file_to_check" {
  type    = string
  default = "files/config.txt"
}
locals {
  file_exists = fileexists(var.file_to_check)
}
```

**`file()`** — reads the contents of a file at the given path and returns them as a string. It only works with files that exist before Terraform runs; it cannot read files created dynamically during a Terraform operation.

```hcl
locals {
  file_content = file("${path.module}/config.txt")
}
```

`path.module` is a built-in that represents the directory of the current Terraform module. `file()` is often used to load configuration or data from files into a configuration (parsing it further with `yamldecode`/`jsondecode` as appropriate).

### Encoding / decoding functions

**`yamlencode()`** — encodes a given value to a string using YAML 1.2 block syntax (`jsonencode()` does the same for JSON).

**`base64encode()`** — encodes a string as base64. Useful for sensitive values (e.g. Kubernetes Secret data) and for encoding custom startup scripts.

```hcl
variable "db_password" {
  type      = string
  sensitive = true
}
resource "kubernetes_secret" "example" {
  metadata {
    name = "db-credentials"
  }
  data = {
    password = base64encode(var.db_password)
  }
}
```

```hcl
variable "user_data" {
  type    = string
  default = "#!/bin/bash\napt-get update\napt-get install -y nginx"
}
resource "aws_instance" "example" {
  ami           = "ami-12345678"
  instance_type = "t2.micro"
  user_data     = base64encode(var.user_data)
}
```
