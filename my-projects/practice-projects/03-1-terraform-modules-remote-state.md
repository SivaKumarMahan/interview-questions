# Practice Project 3.1: Terraform Modules, Environments and Remote State

> This guide shows how to refactor the Project 3 code into reusable, versioned modules with separate dev and prod environments, and how to move existing resources into modules without destroying them.

## Key Concepts

### What you will build

In Project 3 everything lived in one root folder. That works for one environment, but copying it for prod means duplicated code that slowly drifts apart. In this project you will:

- Create two reusable modules: `modules/network` (VNet, subnets, NSGs, rules) and `modules/compute` (public load balancer + VM Scale Set).
- Create two thin root configurations: `envs/dev` and `envs/prod`. Each has its own backend `key`, so each has its own state file.
- Use `for_each` so subnets and NSG rules come from one map variable instead of copy-pasted blocks.
- Version the modules with git tags and pin prod to `?ref=v1.0.0`.
- Refactor the **existing** Project 3 resources into modules with `moved {}` blocks and `import {}` blocks, so `terraform plan` shows **no destroy**.

Final result: `terraform plan` in `envs/dev` after the refactor shows `0 to add, 0 to change, 0 to destroy` (only moves and imports), and `envs/prod` can deploy a bigger copy of the same design from a pinned module version.

### Architecture

```text
terraform-azure-modules (git repo, tagged v1.0.0, v1.1.0 ...)
└── modules/
    ├── network   inputs: name_prefix, address_space, subnets map
    │             outputs: vnet_id, subnet_ids, nsg_ids
    └── compute   inputs: subnet_id, instance_count, vm_size, custom_data
                  outputs: lb_public_ip, vmss_id

infra-live (git repo)
└── envs/
    ├── dev/   module "network" (source = ../../modules or ?ref=v1.1.0)
    │          module "compute"
    │          backend key = dev/3tier.tfstate
    └── prod/  module "network" (source = git ...?ref=v1.0.0)
               module "compute"
               backend key = prod/3tier.tfstate

Storage account (rg-tfstate) / container tfstate
├── dev/3tier.tfstate     <- separate state, separate lock
└── prod/3tier.tfstate
```

### Tools and why each one is used

| Tool | What it does here | Why this tool |
| --- | --- | --- |
| Terraform modules | Package network and compute code for reuse | One implementation, many environments |
| `for_each` | Creates subnets, NSGs and rules from maps | Stable keys, no copy-paste, safe add/remove |
| `locals` | Naming and tags in one place | Consistent names; easy to change convention |
| Git tags | Version the modules (`v1.0.0`) | Prod pins a tested version; dev can try new ones |
| `moved {}` blocks | Tell Terraform a resource changed address | Refactor without destroy/recreate |
| `import {}` blocks | Bring existing Azure resources into state | Reviewable in a plan, works in CI |
| azurerm backend | One state file per environment | Isolation: a dev mistake cannot touch prod state |

### Prerequisites

- Project 3 completed (or at least understood). The refactor steps assume its resource names.
- Terraform 1.9 or newer (`moved` needs 1.1+, `import` blocks need 1.5+, `for_each` in import blocks needs 1.7+).
- Azure CLI logged in, and the state storage account from Project 3.
- A git hosting account (GitHub or Azure Repos) for the modules repo.
- **Cost warning:** deploying both dev and prod doubles the Project 3 cost. Deploy prod only briefly, then destroy it.

### Folder structure

```text
terraform-azure-modules/          # repo 1: reusable modules (tagged)
├── modules/
│   ├── network/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   ├── outputs.tf
│   │   └── versions.tf
│   └── compute/
│       ├── main.tf
│       ├── variables.tf
│       ├── outputs.tf
│       └── versions.tf
└── README.md

infra-live/                       # repo 2: environments (what is deployed)
└── envs/
    ├── dev/
    │   ├── backend.tf
    │   ├── providers.tf
    │   ├── main.tf
    │   ├── moved.tf              # temporary, for the refactor
    │   ├── variables.tf
    │   ├── outputs.tf
    │   ├── terraform.tfvars
    │   └── cloud-init/web.yaml
    └── prod/
        └── (same files, different values and backend key)
```

### Step-by-step

#### Step 1: Decide naming and module boundaries

A good module groups resources that are created and changed together, and has a small, clear interface. Too many tiny modules make wiring painful; one giant module is just a monolith.

```text
Naming convention: <type-abbreviation>-<workload>-<env>[-<suffix>]
  rg-3tier-dev            resource group
  vnet-3tier-dev          virtual network
  snet-web                subnet (name is scoped to the VNet)
  nsg-web-3tier-dev       network security group
  lb-web-3tier-dev        load balancer
  vmss-web-3tier-dev      VM scale set
Mandatory tags: project, environment, owner, managed_by=terraform
```

What this does:

- The abbreviations follow the Microsoft Cloud Adoption Framework style, so names are readable by anyone on Azure.
- Keeping exactly the Project 3 names matters: if a module generates a different name, Terraform must **replace** the resource, and `moved` blocks cannot prevent that.

#### Step 2: Network module - variables

```hcl
# modules/network/variables.tf
variable "name_prefix" {
  description = "Prefix like <project>-<env>, used in resource names."
  type        = string
}

variable "location" {
  type = string
}

variable "resource_group_name" {
  type = string
}

variable "address_space" {
  type = list(string)
}

variable "subnets" {
  description = "Map of subnets keyed by tier name (web, app, db)."
  type = map(object({
    address_prefix     = string
    service_delegation = optional(string)
    nsg_rules = optional(list(object({
      name                    = string
      priority                = number
      direction               = optional(string, "Inbound")
      access                  = optional(string, "Allow")
      protocol                = optional(string, "Tcp")
      source_address_prefix   = string
      destination_port_ranges = list(string)
    })), [])
  }))

  validation {
    condition = alltrue(flatten([
      for s in values(var.subnets) : [for r in s.nsg_rules : r.priority >= 100 && r.priority <= 4096]
    ]))
    error_message = "NSG rule priorities must be between 100 and 4096."
  }
}

variable "tags" {
  type    = map(string)
  default = {}
}
```

What this does:

- `map(object({...}))` describes each subnet. The map **key** (`web`, `app`, `db`) becomes the `for_each` key.
- `optional(type, default)` lets callers skip fields. A subnet without rules gets an empty list.
- The validation checks every rule priority across all subnets before any API call.

#### Step 3: Network module - resources with for_each

```hcl
# modules/network/main.tf
locals {
  # Flatten "subnet -> list of rules" into one map: "web-allow-http" => rule
  nsg_rules = merge([
    for subnet_key, subnet in var.subnets : {
      for rule in subnet.nsg_rules :
      "${subnet_key}-${rule.name}" => merge(rule, { subnet_key = subnet_key })
    }
  ]...)
}

resource "azurerm_virtual_network" "this" {
  name                = "vnet-${var.name_prefix}"
  location            = var.location
  resource_group_name = var.resource_group_name
  address_space       = var.address_space
  tags                = var.tags
}

resource "azurerm_subnet" "this" {
  for_each = var.subnets

  name                 = "snet-${each.key}"
  resource_group_name  = var.resource_group_name
  virtual_network_name = azurerm_virtual_network.this.name
  address_prefixes     = [each.value.address_prefix]

  dynamic "delegation" {
    for_each = each.value.service_delegation == null ? [] : [each.value.service_delegation]
    content {
      name = "delegation"
      service_delegation {
        name    = delegation.value
        actions = ["Microsoft.Network/virtualNetworks/subnets/join/action"]
      }
    }
  }
}

resource "azurerm_network_security_group" "this" {
  for_each = var.subnets

  name                = "nsg-${each.key}-${var.name_prefix}"
  location            = var.location
  resource_group_name = var.resource_group_name
  tags                = var.tags
}

resource "azurerm_network_security_rule" "this" {
  for_each = local.nsg_rules

  name                        = each.value.name
  priority                    = each.value.priority
  direction                   = each.value.direction
  access                      = each.value.access
  protocol                    = each.value.protocol
  source_port_range           = "*"
  destination_port_ranges     = each.value.destination_port_ranges
  source_address_prefix       = each.value.source_address_prefix
  destination_address_prefix  = var.subnets[each.value.subnet_key].address_prefix
  resource_group_name         = var.resource_group_name
  network_security_group_name = azurerm_network_security_group.this[each.value.subnet_key].name
}

resource "azurerm_subnet_network_security_group_association" "this" {
  for_each = var.subnets

  subnet_id                 = azurerm_subnet.this[each.key].id
  network_security_group_id = azurerm_network_security_group.this[each.key].id
}
```

What this does:

- `for_each = var.subnets` creates one subnet per map key. Addresses look like `azurerm_subnet.this["web"]`.
- **Why not `count`?** With `count`, resources are indexed `[0]`, `[1]`, `[2]`. Removing the first item shifts the others, and Terraform destroys and recreates them. With `for_each`, keys are stable strings, so removing `app` only touches `app`.
- `merge([...]...)` uses the `...` expansion to merge a list of maps into one map. The result has a unique key per rule, which `for_each` needs.
- `dynamic "delegation"` adds the block only when `service_delegation` is set (only the db subnet).
- Rules are separate `azurerm_network_security_rule` resources, so adding one rule does not rewrite the whole NSG. **Do not mix** inline `security_rule` blocks and separate rule resources on the same NSG; they fight each other on every plan.

#### Step 4: Network module - outputs and versions

```hcl
# modules/network/outputs.tf
output "vnet_id" {
  value = azurerm_virtual_network.this.id
}

output "vnet_name" {
  value = azurerm_virtual_network.this.name
}

output "subnet_ids" {
  description = "Map of subnet key to subnet ID."
  value       = { for k, s in azurerm_subnet.this : k => s.id }
}

output "nsg_ids" {
  value = { for k, n in azurerm_network_security_group.this : k => n.id }
}
```

```hcl
# modules/network/versions.tf  (same file in modules/compute)
terraform {
  required_version = ">= 1.9.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = ">= 4.0, < 5.0"
    }
  }
}
```

What this does:

- Outputs are the module's public interface. The caller can only see what is output.
- Returning a **map** of IDs lets callers write `module.network.subnet_ids["web"]`.
- Modules declare a **minimum** provider range but **no `provider` block**. The root config configures the provider and passes it down. A provider block inside a module stops you from using `for_each` or `count` on that module.

#### Step 5: Compute module

```hcl
# modules/compute/variables.tf
variable "name_prefix" { type = string }
variable "location" { type = string }
variable "resource_group_name" { type = string }
variable "subnet_id" { type = string }

variable "instance_count" {
  type    = number
  default = 2
}

variable "vm_size" {
  type    = string
  default = "Standard_B2s"
}

variable "zones" {
  type    = list(string)
  default = ["1", "2", "3"]
}

variable "admin_username" {
  type    = string
  default = "azureuser"
}

variable "ssh_public_key" {
  type = string
}

variable "custom_data" {
  description = "Plain-text cloud-init. The module base64-encodes it."
  type        = string
}

variable "tags" {
  type    = map(string)
  default = {}
}
```

```hcl
# modules/compute/main.tf
resource "azurerm_public_ip" "lb" {
  name                = "pip-lb-${var.name_prefix}"
  location            = var.location
  resource_group_name = var.resource_group_name
  allocation_method   = "Static"
  sku                 = "Standard"
  zones               = var.zones
  tags                = var.tags
}

resource "azurerm_lb" "this" {
  name                = "lb-web-${var.name_prefix}"
  location            = var.location
  resource_group_name = var.resource_group_name
  sku                 = "Standard"
  tags                = var.tags

  frontend_ip_configuration {
    name                 = "fe-public"
    public_ip_address_id = azurerm_public_ip.lb.id
  }
}

resource "azurerm_lb_backend_address_pool" "this" {
  name            = "be-web"
  loadbalancer_id = azurerm_lb.this.id
}

resource "azurerm_lb_probe" "http" {
  name                = "probe-http"
  loadbalancer_id     = azurerm_lb.this.id
  protocol            = "Http"
  port                = 80
  request_path        = "/health"
  interval_in_seconds = 5
  number_of_probes    = 2
}

resource "azurerm_lb_rule" "http" {
  name                           = "rule-http"
  loadbalancer_id                = azurerm_lb.this.id
  protocol                       = "Tcp"
  frontend_port                  = 80
  backend_port                   = 80
  frontend_ip_configuration_name = "fe-public"
  backend_address_pool_ids       = [azurerm_lb_backend_address_pool.this.id]
  probe_id                       = azurerm_lb_probe.http.id
  disable_outbound_snat          = true
}

resource "azurerm_lb_outbound_rule" "this" {
  name                    = "outbound-web"
  loadbalancer_id         = azurerm_lb.this.id
  protocol                = "All"
  backend_address_pool_id = azurerm_lb_backend_address_pool.this.id

  frontend_ip_configuration {
    name = "fe-public"
  }
}

resource "azurerm_linux_virtual_machine_scale_set" "this" {
  name                = "vmss-web-${var.name_prefix}"
  location            = var.location
  resource_group_name = var.resource_group_name
  sku                 = var.vm_size
  instances           = var.instance_count
  zones               = var.zones
  admin_username      = var.admin_username
  upgrade_mode        = "Rolling"
  health_probe_id     = azurerm_lb_probe.http.id
  custom_data         = base64encode(var.custom_data)
  tags                = var.tags

  admin_ssh_key {
    username   = var.admin_username
    public_key = var.ssh_public_key
  }

  source_image_reference {
    publisher = "Canonical"
    offer     = "ubuntu-24_04-lts"
    sku       = "server"
    version   = "latest"
  }

  os_disk {
    caching              = "ReadWrite"
    storage_account_type = "Standard_LRS"
  }

  network_interface {
    name    = "nic-web"
    primary = true

    ip_configuration {
      name                                   = "internal"
      primary                                = true
      subnet_id                              = var.subnet_id
      load_balancer_backend_address_pool_ids = [azurerm_lb_backend_address_pool.this.id]
    }
  }

  rolling_upgrade_policy {
    max_batch_instance_percent              = 50
    max_unhealthy_instance_percent          = 50
    max_unhealthy_upgraded_instance_percent = 50
    pause_time_between_batches              = "PT30S"
  }

  depends_on = [azurerm_lb_rule.http, azurerm_lb_outbound_rule.this]
}
```

```hcl
# modules/compute/outputs.tf
output "lb_public_ip" {
  value = azurerm_public_ip.lb.ip_address
}

output "vmss_id" {
  value = azurerm_linux_virtual_machine_scale_set.this.id
}

output "backend_pool_id" {
  value = azurerm_lb_backend_address_pool.this.id
}
```

What this does:

- The module takes **plain text** cloud-init and encodes it itself, so callers cannot forget `base64encode`.
- The SSH key is passed as a string, not a file path. Modules should not read files from the caller's disk; the root does that with `file()`.
- The resource is named `this` because the module has one main resource of that type. It reads well: `module.compute.azurerm_lb.this`.
- Note the LB name keeps the `lb-web-` prefix from Project 3 so existing resources match exactly.

#### Step 6: Version the modules with git tags

```bash
cd terraform-azure-modules
git add . && git commit -m "network and compute modules"
git tag -a v1.0.0 -m "First stable release"
git push origin main --tags
```

Module source formats:

```hcl
# Local path: fast iteration while developing modules
source = "../../modules/network"

# Git over HTTPS, a sub-folder (//) and a pinned tag (?ref=)
source = "git::https://github.com/<org>/terraform-azure-modules.git//modules/network?ref=v1.0.0"

# Private registry (Terraform Cloud/Enterprise): use the version argument instead
# source  = "app.terraform.io/<org>/network/azurerm"
# version = "~> 1.0"
```

What this does:

- `//modules/network` selects a folder inside the repo. `?ref=` can be a tag, a branch or a commit SHA.
- Tags follow **semantic versioning**: MAJOR for breaking interface changes, MINOR for new optional inputs, PATCH for fixes.
- Never point prod at `?ref=main`. A merge to main would silently change prod on the next plan.
- After changing a `ref`, run `terraform init -upgrade` (or `terraform get -update`) to download the new version.

#### Step 7: Environment root config (dev)

```hcl
# envs/dev/backend.tf
terraform {
  required_version = ">= 1.9.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
  }

  backend "azurerm" {
    resource_group_name  = "rg-tfstate"
    storage_account_name = "<storage-account-name>"
    container_name       = "tfstate"
    key                  = "dev/3tier.tfstate"
    use_azuread_auth     = true
  }
}
```

```hcl
# envs/dev/providers.tf
provider "azurerm" {
  features {}
  subscription_id     = var.subscription_id
  storage_use_azuread = true
}
```

```hcl
# envs/dev/variables.tf
variable "subscription_id" { type = string }
variable "project" { type = string }
variable "environment" { type = string }
variable "location" { type = string }
variable "address_space" { type = list(string) }

variable "subnets" {
  type = map(object({
    address_prefix     = string
    service_delegation = optional(string)
    nsg_rules = optional(list(object({
      name                    = string
      priority                = number
      direction               = optional(string, "Inbound")
      access                  = optional(string, "Allow")
      protocol                = optional(string, "Tcp")
      source_address_prefix   = string
      destination_port_ranges = list(string)
    })), [])
  }))
}

variable "web_instance_count" { type = number }
variable "vm_size" { type = string }
variable "ssh_public_key_path" { type = string }

variable "owner" {
  type    = string
  default = "platform-team"
}
```

```hcl
# envs/dev/main.tf
locals {
  name_prefix = "${var.project}-${var.environment}"
  tags = {
    project     = var.project
    environment = var.environment
    owner       = var.owner
    managed_by  = "terraform"
  }
}

resource "azurerm_resource_group" "main" {
  name     = "rg-${local.name_prefix}"
  location = var.location
  tags     = local.tags
}

module "network" {
  source = "../../modules/network"
  # prod uses: "git::https://github.com/<org>/terraform-azure-modules.git//modules/network?ref=v1.0.0"

  name_prefix         = local.name_prefix
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  address_space       = var.address_space
  subnets             = var.subnets
  tags                = local.tags
}

module "compute" {
  source = "../../modules/compute"

  name_prefix         = local.name_prefix
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  subnet_id           = module.network.subnet_ids["web"]
  instance_count      = var.web_instance_count
  vm_size             = var.vm_size
  ssh_public_key      = file(pathexpand(var.ssh_public_key_path))
  custom_data         = file("${path.module}/cloud-init/web.yaml")
  tags                = local.tags

  # NSG must be attached before instances start receiving traffic
  depends_on = [module.network]
}
```

```hcl
# envs/dev/outputs.tf
output "web_url" {
  value = "http://${module.compute.lb_public_ip}"
}

output "subnet_ids" {
  value = module.network.subnet_ids
}
```

```hcl
# envs/dev/terraform.tfvars
subscription_id     = "<subscription-id>"
project             = "3tier"
environment         = "dev"
location            = "eastus"
address_space       = ["10.10.0.0/16"]
web_instance_count  = 2
vm_size             = "Standard_B2s"
ssh_public_key_path = "~/.ssh/azure_lab.pub"

subnets = {
  web = {
    address_prefix = "10.10.1.0/24"
    nsg_rules = [
      { name = "allow-http-https-from-internet", priority = 100, source_address_prefix = "Internet", destination_port_ranges = ["80", "443"] }
    ]
  }
  app = {
    address_prefix = "10.10.2.0/24"
    nsg_rules = [
      { name = "allow-8080-from-web", priority = 100, source_address_prefix = "10.10.1.0/24", destination_port_ranges = ["8080"] },
      { name = "deny-other-vnet-inbound", priority = 4000, access = "Deny", protocol = "*", source_address_prefix = "VirtualNetwork", destination_port_ranges = ["0-65535"] }
    ]
  }
  db = {
    address_prefix     = "10.10.3.0/24"
    service_delegation = "Microsoft.DBforPostgreSQL/flexibleServers"
    nsg_rules = [
      { name = "allow-postgres-from-app", priority = 100, source_address_prefix = "10.10.2.0/24", destination_port_ranges = ["5432"] },
      { name = "allow-intra-db-subnet", priority = 110, protocol = "*", source_address_prefix = "10.10.3.0/24", destination_port_ranges = ["0-65535"] },
      { name = "deny-other-vnet-inbound", priority = 4000, access = "Deny", protocol = "*", source_address_prefix = "VirtualNetwork", destination_port_ranges = ["0-65535"] }
    ]
  }
}
```

What this does:

- The root is **thin**: it wires modules together and holds environment values. Logic lives in modules.
- `module.network.subnet_ids["web"]` passes an output of one module into another. Terraform adds this to the dependency graph.
- `depends_on = [module.network]` on a module waits for **every** resource in that module. Use it sparingly because it can make plans show more "known after apply" values.
- The app VM and PostgreSQL from Project 3 can stay as resources in this root for now (or become a `modules/database` module as an exercise).

#### Step 8: Prod environment

`envs/prod` has the same `.tf` files. Only three things differ:

```hcl
# envs/prod/backend.tf (only the key differs)
    key = "prod/3tier.tfstate"
```

```hcl
# envs/prod/main.tf (pinned module versions)
module "network" {
  source = "git::https://github.com/<org>/terraform-azure-modules.git//modules/network?ref=v1.0.0"
  # ... same inputs as dev
}

module "compute" {
  source = "git::https://github.com/<org>/terraform-azure-modules.git//modules/compute?ref=v1.0.0"
  # ... same inputs as dev
}
```

```hcl
# envs/prod/terraform.tfvars (bigger, separate address space)
environment        = "prod"
address_space      = ["10.20.0.0/16"]
web_instance_count = 3
vm_size            = "Standard_D2s_v5"
```

What this does:

- **Separate state per environment**: a broken dev apply or a stuck dev lock never affects prod. Each environment can also use a different subscription and a different storage account with tighter RBAC.
- Prod pins `v1.0.0`; dev can test `v1.1.0` first. Promotion = change the `ref` in prod through a pull request.
- Why folders instead of **Terraform workspaces**? CLI workspaces share one backend config and the same code, which makes it easy to apply to the wrong workspace and hard to give prod different permissions. Separate folders are explicit and easy to review.

#### Step 9: Refactor existing resources with moved blocks

If dev was already deployed with the flat Project 3 code, simply switching to modules makes Terraform think the old addresses were deleted and new ones added: **destroy and recreate**. `moved` blocks fix this by telling Terraform the new address of the same object.

```hcl
# envs/dev/moved.tf
moved {
  from = azurerm_virtual_network.main
  to   = module.network.azurerm_virtual_network.this
}

moved {
  from = azurerm_subnet.web
  to   = module.network.azurerm_subnet.this["web"]
}
moved {
  from = azurerm_subnet.app
  to   = module.network.azurerm_subnet.this["app"]
}
moved {
  from = azurerm_subnet.db
  to   = module.network.azurerm_subnet.this["db"]
}

moved {
  from = azurerm_network_security_group.web
  to   = module.network.azurerm_network_security_group.this["web"]
}
moved {
  from = azurerm_network_security_group.app
  to   = module.network.azurerm_network_security_group.this["app"]
}
moved {
  from = azurerm_network_security_group.db
  to   = module.network.azurerm_network_security_group.this["db"]
}

moved {
  from = azurerm_subnet_network_security_group_association.web
  to   = module.network.azurerm_subnet_network_security_group_association.this["web"]
}
moved {
  from = azurerm_subnet_network_security_group_association.app
  to   = module.network.azurerm_subnet_network_security_group_association.this["app"]
}
moved {
  from = azurerm_subnet_network_security_group_association.db
  to   = module.network.azurerm_subnet_network_security_group_association.this["db"]
}

moved {
  from = azurerm_lb.web
  to   = module.compute.azurerm_lb.this
}
moved {
  from = azurerm_linux_virtual_machine_scale_set.web
  to   = module.compute.azurerm_linux_virtual_machine_scale_set.this
}
# ... same pattern for public IP, backend pool, probe, rule, outbound rule
```

What this does:

- During `plan`, Terraform updates state addresses instead of planning destroy/create. The plan shows lines like `# azurerm_lb.web has moved to module.compute.azurerm_lb.this`.
- `moved` blocks are code, so they are reviewed in a pull request and run in CI. Everyone sharing the state gets the same result.
- Keep them until every environment and every copy of the state has applied them. In a shared module, keep them for at least one major version; removing a `moved` block early makes an un-migrated state plan a destroy.
- **Old way:** `terraform state mv azurerm_lb.web module.compute.azurerm_lb.this`. It works, but it changes state immediately, is not reviewed, and must be repeated by hand for each environment. Use it only for quick one-off fixes, and back up state first with `terraform state pull > backup.tfstate`.

#### Step 10: Import the NSG rules with import blocks

Project 3 used **inline** `security_rule` blocks. The module uses **separate** rule resources. The rules already exist in Azure, but there is no state entry for `azurerm_network_security_rule.this[...]`. Without action, Terraform tries to create them and Azure returns "already exists". Import blocks fix this.

```hcl
# envs/dev/imports.tf
locals {
  sub          = "/subscriptions/<subscription-id>/resourceGroups/rg-3tier-dev/providers/Microsoft.Network/networkSecurityGroups"
  import_rules = {
    "web-allow-http-https-from-internet" = "${local.sub}/nsg-web-3tier-dev/securityRules/allow-http-https-from-internet"
    "app-allow-8080-from-web"            = "${local.sub}/nsg-app-3tier-dev/securityRules/allow-8080-from-web"
    "app-deny-other-vnet-inbound"        = "${local.sub}/nsg-app-3tier-dev/securityRules/deny-other-vnet-inbound"
    "db-allow-postgres-from-app"         = "${local.sub}/nsg-db-3tier-dev/securityRules/allow-postgres-from-app"
    "db-allow-intra-db-subnet"           = "${local.sub}/nsg-db-3tier-dev/securityRules/allow-intra-db-subnet"
    "db-deny-other-vnet-inbound"         = "${local.sub}/nsg-db-3tier-dev/securityRules/deny-other-vnet-inbound"
  }
}

import {
  for_each = local.import_rules
  to       = module.network.azurerm_network_security_rule.this[each.key]
  id       = each.value
}
```

```bash
cd envs/dev
terraform init
terraform plan -out=tfplan
```

Expected plan summary:

```text
Plan: 6 to import, 0 to add, 0 to change, 0 to destroy.
# (a few "to change" in-place updates are OK, see the notes below; "to destroy" must stay 0)
```

What this does:

- `import` blocks (Terraform 1.5+) are planned like normal changes, so you see the result before anything is written to state. `for_each` inside import blocks needs Terraform 1.7+.
- The keys match the module's `"${subnet_key}-${rule.name}"` keys from Step 3.
- If the plan also shows `~ update in place`, your module values differ slightly from what exists. In this refactor that is expected for a few rules: Project 3 used `destination_port_range = "8080"` or `"*"`, while the module always sets `destination_port_ranges`. A small in-place rule update is harmless; a **replace** or **destroy** is not. The same applies to the VMSS if the module's cloud-init text differs from Project 3 (an in-place model update, no instance replacement).
- To bring in resources that have **no code yet**, run `terraform plan -generate-config-out=generated.tf` and Terraform writes starter HCL for you to clean up.
- After applying, delete `imports.tf` (and later `moved.tf`). They are no-ops once state is updated.

#### Step 11: Share outputs between configurations

Another team's config (for example an AKS or app config) needs the app subnet ID from this network. Two options:

```hcl
# Option A: read the other state file
data "terraform_remote_state" "network" {
  backend = "azurerm"
  config = {
    resource_group_name  = "rg-tfstate"
    storage_account_name = "<storage-account-name>"
    container_name       = "tfstate"
    key                  = "dev/3tier.tfstate"
    use_azuread_auth     = true
  }
}

# usage: data.terraform_remote_state.network.outputs.subnet_ids["app"]
```

```hcl
# Option B: look up the real resource in Azure
data "azurerm_subnet" "app" {
  name                 = "snet-app"
  virtual_network_name = "vnet-3tier-dev"
  resource_group_name  = "rg-3tier-dev"
}

# usage: data.azurerm_subnet.app.id
```

What this does:

| Aspect | `terraform_remote_state` | Provider data source |
| --- | --- | --- |
| Reads from | The other team's state file | Azure API |
| Access needed | Read on the **whole state** (which may contain secrets) | Reader on the resource only |
| Coupling | Tied to the producer's backend location and output names | Tied only to the resource name/ID |
| Works if producer is not Terraform | No | Yes |
| Typical use | Small teams, same trust boundary | Cross-team, least privilege |

Prefer data sources (or a shared config store such as App Configuration or Key Vault) across team boundaries. `terraform_remote_state` is fine inside one team.

### Verify it works

```bash
cd envs/dev
terraform plan
terraform state list | grep module.
terraform output web_url
curl -s "$(terraform output -raw web_url)"
```

Expected output:

```text
No changes. Your infrastructure matches the configuration.

module.compute.azurerm_lb.this
module.compute.azurerm_linux_virtual_machine_scale_set.this
module.network.azurerm_network_security_rule.this["app-allow-8080-from-web"]
module.network.azurerm_subnet.this["web"]
...
"http://20.x.x.x"
<h1>Web tier: ...</h1>
```

Check that the two environments have separate state blobs:

```bash
az storage blob list --account-name <storage-account-name> --container-name tfstate \
  --auth-mode login --query "[].name" -o tsv
# dev/3tier.tfstate
# prod/3tier.tfstate
```

### Common problems and fixes

| Problem | Likely cause | Fix |
| --- | --- | --- |
| Plan shows destroy + create after moving to modules | Missing or wrong `moved` block | Add `moved` for each old address; check map keys like `["web"]` match exactly |
| Plan shows `forces replacement` on a moved resource | Module builds a different name or a ForceNew argument changed | Make the module produce the exact old name/settings |
| `A resource with the ID ... already exists` | Resource exists in Azure but not in state | Add an `import` block, plan, apply |
| `Module not installed` | New module or changed `ref` | Run `terraform init` (add `-upgrade` after a ref change) |
| Git module download fails in CI | Private repo, no credentials | Use a deploy key or token via `git config url.<auth-url>.insteadOf` |
| `for_each` value depends on resource attributes that cannot be determined until apply | Map keys come from computed values | Keys must be known at plan time; build keys from variables, not resource outputs |
| Rules keep flapping on every plan | Inline `security_rule` and separate rule resources on the same NSG | Use only one style |

### Clean up

```bash
cd envs/prod && terraform destroy
cd ../dev && terraform destroy
```

Destroy prod first if you created it only for practice. Remove the `dev/` and `prod/` blobs from the container if you will not reuse them.

### Next improvements

- Add `modules/database` for PostgreSQL and private DNS.
- Write module tests with `terraform test` (`.tftest.hcl` files, Terraform 1.6+), using `command = plan` for fast checks.
- Generate module docs automatically with `terraform-docs`.
- Use a private module registry with `version = "~> 1.0"` constraints instead of raw git refs.
- Add `preconditions`/`postconditions` (`lifecycle` blocks) to catch bad inputs, such as overlapping CIDRs.
- Look at Terragrunt or Terraform Stacks if the number of environments and regions grows.

### How to explain this project in an interview

> "As a follow-up lab to my 3-tier Azure project, I refactored the flat Terraform code into two reusable modules, network and compute, and created separate dev and prod root folders. Each environment has its own backend key, so state and locks are isolated. The network module takes a map of subnets with their NSG rules and uses for_each, so adding or removing a subnet does not shift other resources like count would. I versioned the modules with git tags and pinned prod to a specific ref, so a change to main never silently reaches prod. The interesting part was migrating the already-deployed environment: I used moved blocks to map old addresses to module addresses, and import blocks for NSG rules that changed from inline blocks to separate resources. The goal was a plan with zero destroys, and I reviewed it before applying."

Points that impress interviewers:

- You explain `for_each` vs `count` with the index-shift problem.
- You prefer `moved` and `import` blocks over manual `terraform state` commands because they are reviewed and repeatable.
- You know modules should not contain provider blocks.
- You can compare `terraform_remote_state` with data sources in terms of least privilege.

## Interview Questions

<details><summary>Q1. [Basic] What is a Terraform module and why use one?</summary>

**Answer:**

A module is a folder of `.tf` files with input variables and outputs. Every configuration is already a module (the **root module**); a module called with a `module` block is a **child module**.

Reasons to use modules:

- Reuse: one network design used by dev, test and prod.
- Consistency: naming, tags and security rules are enforced in one place.
- Smaller root configs that are easy to review.
- Versioning: consumers pin a tested version.

Avoid wrapping a single resource in a module with no added value; it only adds indirection.

</details>

<details><summary>Q2. [Basic] What is the difference between <code>count</code> and <code>for_each</code>?</summary>

**Answer:**

`count` creates N copies indexed by number: `azurerm_subnet.this[0]`. `for_each` takes a map or set of strings and indexes by key: `azurerm_subnet.this["web"]`.

With `count`, removing an item in the middle shifts the indexes of everything after it, so Terraform destroys and recreates those resources. With `for_each`, keys are stable, so only the removed key is affected. Use `count` for simple on/off (`count = var.enabled ? 1 : 0`) or truly identical copies, and `for_each` for anything with an identity.

</details>

<details><summary>Q3. [Basic] How do you pin a module version from git, and why?</summary>

**Answer:**

Use the `ref` query parameter with a tag:

`source = "git::https://github.com/<org>/terraform-azure-modules.git//modules/network?ref=v1.0.0"`

The `//` selects a sub-folder. Pinning means the module code only changes when someone edits the `ref` in a reviewed pull request. If you point at a branch like `main`, any merge changes what the next plan does, even in prod. For registry modules, use the `version` argument with a constraint like `~> 1.0`. After changing a ref, run `terraform init -upgrade`.

</details>

<details><summary>Q4. [Intermediate] What does a <code>moved</code> block do, and how is it different from <code>terraform state mv</code>?</summary>

**Answer:**

Both tell Terraform that an existing object now has a different address (for example after renaming a resource or moving it into a module), so it is not destroyed and recreated.

- `moved {}` is **code**. It shows up in `terraform plan` as "has moved to", goes through code review and CI, and works for every environment and every user automatically. Module authors can ship `moved` blocks so consumers upgrade safely.
- `terraform state mv` changes state **immediately**, with no plan and no review. You must run it by hand in every environment.

Prefer `moved` blocks. Use `state mv` only for urgent one-off fixes, after `terraform state pull` to back up state.

</details>

<details><summary>Q5. [Intermediate] When would you use an <code>import</code> block, and what does <code>-generate-config-out</code> do?</summary>

**Answer:**

Use an `import` block when a resource already exists in Azure but is not in Terraform state. Examples: something created in the portal, or a resource whose Terraform type changed during a refactor (inline NSG rules becoming separate rule resources).

```hcl
import {
  to = azurerm_resource_group.legacy
  id = "/subscriptions/<subscription-id>/resourceGroups/rg-legacy"
}
```

The import is shown in `plan` and only written during `apply`, so it is reviewable. `terraform plan -generate-config-out=generated.tf` writes HCL for imported resources that have no `resource` block yet. The generated code is a starting point; you clean it up and usually move it into modules.

</details>

<details><summary>Q6. [Intermediate] <code>terraform_remote_state</code> or a data source: which do you use to share network IDs with another team? <em>(scenario)</em></summary>

**Answer:**

I would usually use a **provider data source** such as `data "azurerm_subnet"` or `data "azurerm_virtual_network"`.

- `terraform_remote_state` needs read access to the **whole** state file, which can contain secrets like generated passwords. It also couples the consumer to the producer's backend location and output names.
- A data source needs only Reader on the resource, and works even if the producer stops using Terraform.

`terraform_remote_state` is acceptable within one team that already shares state access. Across teams, I would use data sources or publish values to a shared store such as Key Vault or App Configuration.

</details>

<details><summary>Q7. [Advanced] Why separate folders per environment instead of Terraform CLI workspaces?</summary>

**Answer:**

CLI workspaces give multiple state files for the **same** code and backend config. Problems:

- It is easy to forget `terraform workspace select` and apply to the wrong environment.
- All workspaces share one backend config, so prod state sits next to dev with the same access rights.
- Differences between environments end up as `terraform.workspace == "prod" ? ... : ...` conditionals.

Separate folders (`envs/dev`, `envs/prod`) have their own backend key (or even separate storage accounts and subscriptions), their own tfvars, and can pin different module versions. Promotion is a visible pull request. Workspaces are still handy for short-lived copies such as feature-branch test environments.

</details>

<details><summary>Q8. [Advanced] After moving resources into a module, the plan wants to destroy and recreate the VM Scale Set. How do you fix it? <em>(scenario)</em></summary>

**Answer:**

1. Read the plan carefully. If it says `must be replaced` with `# forces replacement` on an attribute, the address mapping is fine but a **value** changed (for example the module builds a different `name`, or `zones` differ). Fix the module input or naming so it matches the existing resource exactly.
2. If it shows a separate `destroy` of the old address and `create` of the new address, the `moved` block is missing or wrong. Check spelling, module name and map keys (`["web"]` vs `["Web"]`).
3. Re-plan until the summary shows only moves, `0 to destroy`.
4. As extra safety on critical resources, add `lifecycle { prevent_destroy = true }` during the refactor, so an accidental destroy fails the plan.

Never apply a plan that destroys stateful resources during a pure refactor.

</details>

<details><summary>Q9. [Advanced] How would you design a module interface so it can evolve without breaking consumers?</summary>

**Answer:**

- Keep required inputs few; use `optional()` attributes with defaults for new features, so old callers still work (a MINOR version bump).
- Validate inputs with `validation` blocks so errors are clear.
- Output IDs as maps keyed by stable names, not lists.
- Do not put `provider` blocks in modules; let the root pass providers (use `configuration_aliases` when a module needs multiple providers, like hub and spoke subscriptions).
- When renaming internal resources, ship `moved` blocks inside the module.
- Follow semantic versioning, keep a CHANGELOG, and test with `terraform test` before tagging.

</details>
