# Hands-on 5: Modular Terraform Landing Zone with Nested Maps, for_each, and an Azure DevOps Pipeline

> Build a reusable Azure landing zone (resource groups, VNets, subnets, NSGs, VMs, and an Application Gateway) from small child modules driven by nested-map variables, and deploy it with a multi-stage Azure DevOps pipeline on a self-hosted agent.

**Time:** about 3 hours. **Level:** Intermediate to Advanced.

## What you practise

- Parent (root) and child modules: one module per resource type
- Nested map variables with `optional()` attributes, and `for_each` over them
- Linking modules by key, for example `module.subnet[each.value.subnet_key].id`
- `dynamic` blocks for NSG rules and Application Gateway pools, listeners, and rules
- Reading existing resources with `data "azurerm_public_ip"`
- Linux VMs with SSH keys only (no hardcoded passwords)
- One codebase for Dev, QA, and Prod, each with its own tfvars and state
- A pipeline: install, init, validate, plan, security scan, manual validation, apply

## Prerequisites

| Item | Purpose |
| --- | --- |
| Azure subscription | Target for the landing zone |
| Terraform 1.9 or later, azurerm provider 4.x | `optional()` defaults and current resource schemas |
| Storage account `companytfstate` in `tfstate-rg`, container `tfstate` | Remote state, one key per environment |
| Azure DevOps project, service connection `azure-wif-connection` | Pipeline and Azure access |
| Self-hosted agent pool `self-hosted-linux` | Agent with network access to Azure and the state account |
| Trivy on the agent | Terraform security scan |
| SSH public key | VM login |

## Flow

```text
environments/dev/terraform.tfvars  (nested maps: rgs, vnets, subnets, nsgs, vms, appgw)
        |
        v
environments/dev/main.tf (root / parent module)
        |
        |-- module.resource_group[for_each]
        |-- module.vnet[for_each]        -> uses module.resource_group[rg_key]
        |-- module.subnet[for_each]      -> uses module.vnet[vnet_key]
        |-- module.nsg[for_each]         -> dynamic "security_rule"
        |-- module.public_ip[for_each]
        |-- data.azurerm_public_ip[for_each] (existing IPs)
        |-- module.nic[for_each]         -> uses module.subnet[subnet_key]
        |-- module.vm[for_each]          -> uses module.nic[key]
        '-- module.appgw                 -> locals + dynamic pools, listeners, rules

Pipeline (self-hosted agent):
Install -> Init -> Validate -> Plan -> Security scan -> Manual validation -> Apply
```

## Steps

### 1. Create the folder structure

```text
landing-zone/
├── modules/
│   ├── resource_group/    # main.tf, variables.tf, outputs.tf in each module
│   ├── vnet/
│   ├── subnet/
│   ├── nsg/
│   ├── public_ip/
│   ├── nic/
│   ├── vm/
│   ├── lb/
│   └── appgw/
├── environments/
│   ├── dev/
│   │   ├── backend.tf
│   │   ├── providers.tf
│   │   ├── variables.tf
│   │   ├── main.tf
│   │   ├── outputs.tf
│   │   └── terraform.tfvars
│   ├── qa/                # same files, different tfvars and state key
│   └── prod/
└── azure-pipelines.yml
```

Child modules contain one resource type and no environment values. The environment folders are the parent (root) modules: they call the child modules and hold the values.

### 2. Write small child modules

`modules/resource_group/main.tf`:

```hcl
resource "azurerm_resource_group" "this" {
  name     = var.name
  location = var.location
  tags     = var.tags
}

variable "name" { type = string }
variable "location" { type = string }
variable "tags" {
  type    = map(string)
  default = {}
}

output "name" { value = azurerm_resource_group.this.name }
output "location" { value = azurerm_resource_group.this.location }
output "id" { value = azurerm_resource_group.this.id }
```

Variables and outputs are shown in one file here to save space. In the repo, keep them in `variables.tf` and `outputs.tf`.

`modules/vnet/main.tf`:

```hcl
resource "azurerm_virtual_network" "this" {
  name                = var.name
  location            = var.location
  resource_group_name = var.resource_group_name
  address_space       = var.address_space
}

output "id" { value = azurerm_virtual_network.this.id }
output "name" { value = azurerm_virtual_network.this.name }
output "resource_group_name" { value = azurerm_virtual_network.this.resource_group_name }
```

`modules/subnet/main.tf`:

```hcl
resource "azurerm_subnet" "this" {
  name                 = var.name
  resource_group_name  = var.resource_group_name
  virtual_network_name = var.virtual_network_name
  address_prefixes     = var.address_prefixes
}

output "id" { value = azurerm_subnet.this.id }
```

`modules/public_ip/main.tf`:

```hcl
resource "azurerm_public_ip" "this" {
  name                = var.name
  location            = var.location
  resource_group_name = var.resource_group_name
  allocation_method   = "Static"
  sku                 = "Standard"
}

output "id" { value = azurerm_public_ip.this.id }
```

The `vnet`, `subnet`, `public_ip`, and `vm` modules also need a `variables.tf` that declares every `var.` they use (`name`, `location`, `resource_group_name`, and so on), in the same way as the resource group module.

### 3. NSG module with a dynamic block

`modules/nsg/variables.tf`:

```hcl
variable "name" { type = string }
variable "location" { type = string }
variable "resource_group_name" { type = string }

variable "rules" {
  type = map(object({
    priority                   = number
    direction                  = optional(string, "Inbound")
    access                     = optional(string, "Allow")
    protocol                   = optional(string, "Tcp")
    source_port_range          = optional(string, "*")
    destination_port_range     = string
    source_address_prefix      = optional(string, "*")
    destination_address_prefix = optional(string, "*")
  }))
  default = {}

  validation {
    condition     = alltrue([for r in values(var.rules) : r.priority >= 100 && r.priority <= 4096])
    error_message = "NSG rule priority must be between 100 and 4096."
  }
}
```

`modules/nsg/main.tf`:

```hcl
resource "azurerm_network_security_group" "this" {
  name                = var.name
  location            = var.location
  resource_group_name = var.resource_group_name

  dynamic "security_rule" {
    for_each = var.rules
    content {
      name                       = security_rule.key
      priority                   = security_rule.value.priority
      direction                  = security_rule.value.direction
      access                     = security_rule.value.access
      protocol                   = security_rule.value.protocol
      source_port_range          = security_rule.value.source_port_range
      destination_port_range     = security_rule.value.destination_port_range
      source_address_prefix      = security_rule.value.source_address_prefix
      destination_address_prefix = security_rule.value.destination_address_prefix
    }
  }
}

output "id" { value = azurerm_network_security_group.this.id }
```

One `security_rule` block is generated for each entry in the `rules` map. The map key becomes the rule name.

### 4. NIC and VM modules

`modules/nic/main.tf`:

```hcl
resource "azurerm_network_interface" "this" {
  name                = var.name
  location            = var.location
  resource_group_name = var.resource_group_name

  ip_configuration {
    name                          = "internal"
    subnet_id                     = var.subnet_id
    private_ip_address_allocation = var.private_ip_address == null ? "Dynamic" : "Static"
    private_ip_address            = var.private_ip_address
    public_ip_address_id          = var.public_ip_address_id
  }
}

variable "name" { type = string }
variable "location" { type = string }
variable "resource_group_name" { type = string }
variable "subnet_id" { type = string }
variable "private_ip_address" {
  type    = string
  default = null
}
variable "public_ip_address_id" {
  type    = string
  default = null
}

output "id" { value = azurerm_network_interface.this.id }
output "private_ip_address" { value = azurerm_network_interface.this.private_ip_address }
```

`modules/vm/main.tf`:

```hcl
resource "azurerm_linux_virtual_machine" "this" {
  name                            = var.name
  location                        = var.location
  resource_group_name             = var.resource_group_name
  size                            = var.size
  admin_username                  = var.admin_username
  disable_password_authentication = true
  network_interface_ids           = [var.nic_id]

  admin_ssh_key {
    username   = var.admin_username
    public_key = var.ssh_public_key
  }

  os_disk {
    caching              = "ReadWrite"
    storage_account_type = "StandardSSD_LRS"
  }

  source_image_reference {
    publisher = "Canonical"
    offer     = "ubuntu-24_04-lts"
    sku       = "server"
    version   = "latest"
  }
}

output "id" { value = azurerm_linux_virtual_machine.this.id }
```

There is no password anywhere. The public key comes from a variable that the pipeline sets.

### 5. Define nested-map variables in the root module

`environments/dev/variables.tf`:

```hcl
variable "location" {
  type    = string
  default = "westeurope"
}

variable "ssh_public_key" {
  type        = string
  description = "Set by the pipeline as TF_VAR_ssh_public_key"
}

variable "resource_groups" {
  type = map(object({
    name = string
    tags = optional(map(string), {})
  }))
}

variable "vnets" {
  type = map(object({
    name          = string
    rg_key        = string
    address_space = list(string)
  }))
}

variable "subnets" {
  type = map(object({
    name             = string
    vnet_key         = string
    address_prefixes = list(string)
    nsg_key          = optional(string)
  }))
}

variable "nsgs" {
  type = map(object({
    name   = string
    rg_key = string
    rules = optional(map(object({
      priority                   = number
      direction                  = optional(string, "Inbound")
      access                     = optional(string, "Allow")
      protocol                   = optional(string, "Tcp")
      source_port_range          = optional(string, "*")
      destination_port_range     = string
      source_address_prefix      = optional(string, "*")
      destination_address_prefix = optional(string, "*")
    })), {})
  }))
}

variable "public_ips" {
  type = map(object({
    name   = string
    rg_key = string
  }))
  default = {}
}

variable "vms" {
  type = map(object({
    rg_key         = string
    subnet_key     = string
    size           = optional(string, "Standard_B2s")
    admin_username = optional(string, "azureuser")
    nic = object({
      name               = string
      private_ip_address = optional(string)
    })
    existing_public_ip = optional(object({
      name                = string
      resource_group_name = string
    }))
  }))

  validation {
    condition     = alltrue([for vm in values(var.vms) : can(regex("^Standard_", vm.size))])
    error_message = "VM size must start with Standard_."
  }
}

variable "appgw" {
  type = object({
    name          = string
    rg_key        = string
    subnet_key    = string
    public_ip_key = string
    capacity      = optional(number, 1)
    apps = map(object({
      host_name       = string
      priority        = number
      backend_port    = optional(number, 80)
      backend_vm_keys = list(string)
    }))
  })
}
```

### 6. Fill in `terraform.tfvars`

`environments/dev/terraform.tfvars`:

```hcl
resource_groups = {
  network = { name = "rg-dev-network", tags = { env = "dev" } }
  compute = { name = "rg-dev", tags = { env = "dev" } }
}

vnets = {
  hub = { name = "vnet-dev", rg_key = "network", address_space = ["10.10.0.0/16"] }
}

subnets = {
  web   = { name = "snet-web", vnet_key = "hub", address_prefixes = ["10.10.1.0/24"], nsg_key = "web" }
  appgw = { name = "snet-appgw", vnet_key = "hub", address_prefixes = ["10.10.2.0/24"] }
}

nsgs = {
  web = {
    name   = "nsg-dev-web"
    rg_key = "network"
    rules = {
      allow-http-from-appgw = { priority = 100, destination_port_range = "80", source_address_prefix = "10.10.2.0/24" }
      allow-ssh-from-vpn    = { priority = 110, destination_port_range = "22", source_address_prefix = "10.200.0.0/16" }
    }
  }
}

public_ips = {
  appgw = { name = "pip-dev-appgw", rg_key = "network" }
}

vms = {
  web1 = {
    rg_key     = "compute"
    subnet_key = "web"
    nic        = { name = "nic-dev-web1", private_ip_address = "10.10.1.10" }
  }
  web2 = {
    rg_key     = "compute"
    subnet_key = "web"
    size       = "Standard_B2ms"
    nic        = { name = "nic-dev-web2" }
    existing_public_ip = {
      name                = "pip-dev-web2-existing"
      resource_group_name = "rg-dev-shared"
    }
  }
}

appgw = {
  name          = "agw-dev"
  rg_key        = "network"
  subnet_key    = "appgw"
  public_ip_key = "appgw"
  apps = {
    shop = { host_name = "shop.dev.example.com", priority = 100, backend_vm_keys = ["web1", "web2"] }
    blog = { host_name = "blog.dev.example.com", priority = 110, backend_vm_keys = ["web2"] }
  }
}
```

The QA and Prod folders have the same variables with different names, address ranges, sizes, and numbers of VMs. Adding a VM is a new entry in the `vms` map, not new code.

### 7. Call the child modules with `for_each`

`environments/dev/main.tf`:

```hcl
module "resource_group" {
  source   = "../../modules/resource_group"
  for_each = var.resource_groups

  name     = each.value.name
  location = var.location
  tags     = each.value.tags
}

module "vnet" {
  source   = "../../modules/vnet"
  for_each = var.vnets

  name                = each.value.name
  location            = module.resource_group[each.value.rg_key].location
  resource_group_name = module.resource_group[each.value.rg_key].name
  address_space       = each.value.address_space
}

module "subnet" {
  source   = "../../modules/subnet"
  for_each = var.subnets

  name                 = each.value.name
  resource_group_name  = module.vnet[each.value.vnet_key].resource_group_name
  virtual_network_name = module.vnet[each.value.vnet_key].name
  address_prefixes     = each.value.address_prefixes
}

module "nsg" {
  source   = "../../modules/nsg"
  for_each = var.nsgs

  name                = each.value.name
  location            = module.resource_group[each.value.rg_key].location
  resource_group_name = module.resource_group[each.value.rg_key].name
  rules               = each.value.rules
}

resource "azurerm_subnet_network_security_group_association" "this" {
  for_each = { for k, s in var.subnets : k => s if s.nsg_key != null }

  subnet_id                 = module.subnet[each.key].id
  network_security_group_id = module.nsg[each.value.nsg_key].id
}

module "public_ip" {
  source   = "../../modules/public_ip"
  for_each = var.public_ips

  name                = each.value.name
  location            = module.resource_group[each.value.rg_key].location
  resource_group_name = module.resource_group[each.value.rg_key].name
}

# Existing public IPs that were created outside this code
data "azurerm_public_ip" "existing" {
  for_each = { for k, vm in var.vms : k => vm.existing_public_ip if vm.existing_public_ip != null }

  name                = each.value.name
  resource_group_name = each.value.resource_group_name
}

module "nic" {
  source   = "../../modules/nic"
  for_each = var.vms

  name                 = each.value.nic.name
  location             = module.resource_group[each.value.rg_key].location
  resource_group_name  = module.resource_group[each.value.rg_key].name
  subnet_id            = module.subnet[each.value.subnet_key].id
  private_ip_address   = each.value.nic.private_ip_address
  public_ip_address_id = try(data.azurerm_public_ip.existing[each.key].id, null)
}

module "vm" {
  source   = "../../modules/vm"
  for_each = var.vms

  name                = "vm-dev-${each.key}"
  location            = module.resource_group[each.value.rg_key].location
  resource_group_name = module.resource_group[each.value.rg_key].name
  size                = each.value.size
  admin_username      = each.value.admin_username
  ssh_public_key      = var.ssh_public_key
  nic_id              = module.nic[each.key].id
}
```

How the links work:

- `each.key` is the map key (`web1`), and `each.value` is the object for that key.
- `module.subnet[each.value.subnet_key].id` looks up another module instance by its key. This also creates the dependency, so Terraform builds the subnet before the NIC.
- The NIC and VM use the same key (`each.key`), so `web1` VM always gets the `web1` NIC.

### 8. Application Gateway with locals and dynamic blocks

In the root module, build the backend IP lists from the NIC outputs:

```hcl
locals {
  appgw_apps = {
    for app_key, app in var.appgw.apps : app_key => merge(app, {
      backend_ips = [for vm_key in app.backend_vm_keys : module.nic[vm_key].private_ip_address]
    })
  }
}

module "appgw" {
  source = "../../modules/appgw"

  name                = var.appgw.name
  location            = module.resource_group[var.appgw.rg_key].location
  resource_group_name = module.resource_group[var.appgw.rg_key].name
  subnet_id           = module.subnet[var.appgw.subnet_key].id
  public_ip_id        = module.public_ip[var.appgw.public_ip_key].id
  capacity            = var.appgw.capacity
  apps                = local.appgw_apps
}
```

`modules/appgw/main.tf`:

```hcl
locals {
  gateway_ip_name    = "${var.name}-gwip"
  frontend_ip_name   = "${var.name}-feip"
  frontend_port_name = "${var.name}-port-80"
}

resource "azurerm_application_gateway" "this" {
  name                = var.name
  location            = var.location
  resource_group_name = var.resource_group_name

  sku {
    name     = "Standard_v2"
    tier     = "Standard_v2"
    capacity = var.capacity
  }

  gateway_ip_configuration {
    name      = local.gateway_ip_name
    subnet_id = var.subnet_id
  }

  frontend_ip_configuration {
    name                 = local.frontend_ip_name
    public_ip_address_id = var.public_ip_id
  }

  frontend_port {
    name = local.frontend_port_name
    port = 80
  }

  dynamic "backend_address_pool" {
    for_each = var.apps
    content {
      name         = "${backend_address_pool.key}-pool"
      ip_addresses = backend_address_pool.value.backend_ips
    }
  }

  dynamic "backend_http_settings" {
    for_each = var.apps
    content {
      name                  = "${backend_http_settings.key}-http"
      cookie_based_affinity = "Disabled"
      port                  = backend_http_settings.value.backend_port
      protocol              = "Http"
      request_timeout       = 30
    }
  }

  dynamic "http_listener" {
    for_each = var.apps
    content {
      name                           = "${http_listener.key}-listener"
      frontend_ip_configuration_name = local.frontend_ip_name
      frontend_port_name             = local.frontend_port_name
      protocol                       = "Http"
      host_name                      = http_listener.value.host_name
    }
  }

  dynamic "request_routing_rule" {
    for_each = var.apps
    content {
      name                       = "${request_routing_rule.key}-rule"
      rule_type                  = "Basic"
      priority                   = request_routing_rule.value.priority
      http_listener_name         = "${request_routing_rule.key}-listener"
      backend_address_pool_name  = "${request_routing_rule.key}-pool"
      backend_http_settings_name = "${request_routing_rule.key}-http"
    }
  }
}

variable "name" { type = string }
variable "location" { type = string }
variable "resource_group_name" { type = string }
variable "subnet_id" { type = string }
variable "public_ip_id" { type = string }
variable "capacity" { type = number }
variable "apps" {
  type = map(object({
    host_name    = string
    priority     = number
    backend_port = number
    backend_ips  = list(string)
  }))
}
```

Each app in the map creates a pool, HTTP settings, a host-based listener, and a routing rule. The names are built from the same key, so they always match. Notes:

- The Application Gateway needs its own dedicated subnet (`snet-appgw` here).
- `Standard_v2` needs a Standard SKU, static public IP, and every routing rule needs a unique `priority`.
- The `lb` module follows the same pattern: `azurerm_lb` with a frontend IP, and `dynamic` blocks or separate `for_each` resources for backend pools, probes, and rules.

### 9. Backend and provider per environment

`environments/dev/backend.tf`:

```hcl
terraform {
  required_version = ">= 1.9.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
  }

  backend "azurerm" {
    resource_group_name  = "tfstate-rg"
    storage_account_name = "companytfstate"
    container_name       = "tfstate"
    key                  = "landing-zone-dev.tfstate"
  }
}
```

`environments/dev/providers.tf`:

```hcl
provider "azurerm" {
  features {}
  # azurerm 4.x needs a subscription ID. It is read from ARM_SUBSCRIPTION_ID,
  # which the pipeline task sets from the service connection.
}
```

QA and Prod use `landing-zone-qa.tfstate` and `landing-zone-prod.tfstate`, so an error in Dev can never change Prod.

### 10. Run it locally once

```bash
cd environments/dev
export TF_VAR_ssh_public_key="$(cat ~/.ssh/id_rsa.pub)"
export ARM_SUBSCRIPTION_ID="$(az account show --query id -o tsv)"
terraform init
terraform validate
terraform plan -out=tfplan
```

Expected: the plan lists instances with their keys, such as `module.vm["web1"].azurerm_linux_virtual_machine.this` and `module.nsg["web"].azurerm_network_security_group.this`.

### 11. Create the pipeline

`azure-pipelines.yml`:

```yaml
trigger:
  branches:
    include:
      - main

parameters:
  - name: environment
    type: string
    default: dev
    values:
      - dev
      - qa
      - prod

pool:
  name: self-hosted-linux           # self-hosted agent pool

variables:
  azureSubscription: azure-wif-connection
  tfVersion: '1.9.8'
  tfDir: $(System.DefaultWorkingDirectory)/environments/${{ parameters.environment }}
  stateKey: landing-zone-${{ parameters.environment }}.tfstate

stages:
  - stage: Plan
    jobs:
      - job: Plan
        steps:
          - task: TerraformInstaller@1
            displayName: Install Terraform
            inputs:
              terraformVersion: $(tfVersion)
          - task: TerraformTask@5
            displayName: Terraform init
            inputs:
              provider: azurerm
              command: init
              workingDirectory: $(tfDir)
              backendServiceArm: $(azureSubscription)
              backendAzureRmResourceGroupName: tfstate-rg
              backendAzureRmStorageAccountName: companytfstate
              backendAzureRmContainerName: tfstate
              backendAzureRmKey: $(stateKey)
          - task: TerraformTask@5
            displayName: Terraform validate
            inputs:
              provider: azurerm
              command: validate
              workingDirectory: $(tfDir)
          - task: TerraformTask@5
            displayName: Terraform plan
            inputs:
              provider: azurerm
              command: plan
              workingDirectory: $(tfDir)
              environmentServiceNameAzureRM: $(azureSubscription)
              commandOptions: '-out=tfplan -input=false'
            env:
              TF_VAR_ssh_public_key: $(SSH_PUBLIC_KEY)
          - publish: $(tfDir)/tfplan
            artifact: tfplan

  - stage: SecurityScan
    dependsOn: Plan
    jobs:
      - job: Trivy
        steps:
          - script: |
              trivy --version
              trivy config --severity HIGH,CRITICAL --exit-code 1 .
            displayName: Trivy IaC scan
            workingDirectory: $(System.DefaultWorkingDirectory)

  - stage: Approve
    dependsOn: SecurityScan
    jobs:
      - job: ManualValidation
        pool: server
        timeoutInMinutes: 1440
        steps:
          - task: ManualValidation@1
            timeoutInMinutes: 1380
            inputs:
              notifyUsers: platform-team@example.com
              approvers: platform-team@example.com
              instructions: 'Review the plan for ${{ parameters.environment }} and approve.'
              onTimeout: reject

  - stage: Apply
    dependsOn: Approve
    jobs:
      - job: Apply
        steps:
          - download: current
            artifact: tfplan
          - script: cp $(Pipeline.Workspace)/tfplan/tfplan $(tfDir)/tfplan
            displayName: Copy saved plan
          - task: TerraformInstaller@1
            inputs:
              terraformVersion: $(tfVersion)
          - task: TerraformTask@5
            displayName: Terraform init
            inputs:
              provider: azurerm
              command: init
              workingDirectory: $(tfDir)
              backendServiceArm: $(azureSubscription)
              backendAzureRmResourceGroupName: tfstate-rg
              backendAzureRmStorageAccountName: companytfstate
              backendAzureRmContainerName: tfstate
              backendAzureRmKey: $(stateKey)
          - task: TerraformTask@5
            displayName: Terraform apply
            inputs:
              provider: azurerm
              command: apply
              workingDirectory: $(tfDir)
              environmentServiceNameAzureRM: $(azureSubscription)
              commandOptions: 'tfplan'
```

Notes:

- `SSH_PUBLIC_KEY` is a pipeline variable (or a variable group linked to Key Vault). Terraform reads any `TF_VAR_<name>` environment variable as the value of `var.<name>`.
- The security scan here runs after the plan, as in the source design. Moving it before the plan fails insecure code faster.
- tfsec is now part of Trivy, and `trivy config .` runs the same checks. The old `tfsec .` command still exists but is no longer actively developed. Checkov is another common choice.
- The self-hosted agent gives you control over installed tools, network access to private endpoints, and isolation from other teams. You must patch and clean it yourself.
- Standard jobs check out the repository automatically, so the Apply job has the code. If you use a deployment job instead, add `checkout: self`.

### 12. Verify

```bash
az group list --query "[?starts_with(name, 'rg-dev')].name" -o table
az network vnet subnet list -g rg-dev-network --vnet-name vnet-dev -o table
az network nsg rule list -g rg-dev-network --nsg-name nsg-dev-web -o table
az vm list -g rg-dev -o table
az network application-gateway show -g rg-dev-network -n agw-dev \
  --query "httpListeners[].hostNames" -o tsv
terraform state list
```

Expected: two resource groups, two subnets, two NSG rules, two VMs (`vm-dev-web1`, `vm-dev-web2`), and an Application Gateway with listeners for `shop.dev.example.com` and `blog.dev.example.com`. Running `terraform plan` again shows `No changes.`

## Important points

- **for_each vs count:** `for_each` uses stable keys like `web1`. Removing `web1` deletes only `web1`. With `count`, removing an item in the middle shifts the indexes, and Terraform wants to recreate the items after it.
- **optional() and validation:** `optional(string, "default")` keeps tfvars short. `validation` blocks stop bad input (wrong priority, wrong size) at plan time with a clear message.
- **Keys are addresses:** renaming a map key (`web1` to `frontend1`) means destroy and create. Use a `moved` block if you must rename.
- **Separate state per environment:** separate state files (or separate storage accounts) limit the blast radius, allow different access per environment, and avoid one huge, slow plan.
- **Data sources for existing resources:** `data "azurerm_public_ip"` only reads. Terraform never changes or deletes the existing IP.
- **No secrets in tfvars:** SSH keys and other values come from the pipeline or Key Vault.

## Common problems

| Problem | Likely cause | Fix |
| --- | --- | --- |
| `Invalid index` on `module.subnet[...]` | Key in tfvars does not match a key in the map | Check spelling of `subnet_key`, `rg_key`, `vnet_key` |
| `The "for_each" value depends on resource attributes that cannot be determined until apply` | `for_each` built from values known only after apply | Build `for_each` from input variables or static keys only |
| Plan wants to destroy and recreate many VMs | Map keys renamed or `count` used | Keep keys stable; use `moved` blocks |
| Application Gateway: subnet error | Subnet shared with other resources | Use a dedicated subnet for the Application Gateway |
| `subscription_id is a required provider property` | azurerm 4.x without subscription ID | Set `ARM_SUBSCRIPTION_ID` or `subscription_id` in the provider |
| `trivy: command not found` | Tool not installed on the self-hosted agent | Install Trivy on the agent image |
| Data source: public IP not found | Wrong name or resource group | Check with `az network public-ip show -g <rg> -n <name>` |

## Clean up

```bash
cd environments/dev
terraform destroy
```

In a pipeline, use a separate destroy pipeline with its own approval.

## Interview questions

<details><summary>Q1. Why use <code>for_each</code> with maps instead of <code>count</code>?</summary>

`for_each` gives each instance a stable key, such as `module.vm["web1"]`. Adding or removing one entry only affects that entry. `count` uses list positions, so removing an item in the middle shifts the index of every item after it, and Terraform plans to destroy and recreate them. Maps also let me store several settings per instance.

</details>

<details><summary>Q2. How do you connect resources created by different modules?</summary>

Each child module exposes outputs such as `id` and `name`. In the root module, I pass them into other modules by key, for example `subnet_id = module.subnet[each.value.subnet_key].id`. The tfvars entry for a VM only holds the subnet key. This reference also tells Terraform the dependency order, so I do not need `depends_on`.

</details>

<details><summary>Q3. What is a <code>dynamic</code> block, and when do you use it?</summary>

A `dynamic` block generates repeated nested blocks inside one resource from a map or list, such as `security_rule` in an NSG or listeners in an Application Gateway. I use it when the number of nested blocks changes per environment. I avoid it when the number is fixed, because plain blocks are easier to read.

</details>

<details><summary>Q4. How do you deploy Dev, QA, and Prod from one codebase?</summary>

The child modules are shared. Each environment has a small root folder (or workspace) with its own `terraform.tfvars` and its own backend state key. The pipeline takes the environment as a parameter and points at that folder and state. Prod has stricter approvals. Code is the same, only data differs.

</details>

<details><summary>Q5. How do you use an existing resource that Terraform did not create?</summary>

If I only need to read it, I use a data source, such as `data "azurerm_public_ip"`, and pass its `id` to the resource that needs it. Terraform never changes it. If Terraform should manage it from now on, I import it into state with an `import` block or `terraform import`, and then write matching configuration.

</details>
