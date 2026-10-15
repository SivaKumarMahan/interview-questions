# Practice Project 3: Terraform 3-Tier Architecture on Azure

> This guide shows how to build a web, app and database tier on Azure with Terraform (azurerm 4.x), keep the state in a locked remote backend, and explain the whole design in an interview.

## Key Concepts

### What you will build

You will write Terraform code that creates a small but realistic 3-tier network on Azure:

- A **web tier**: a Linux VM Scale Set (VMSS) running nginx, behind a public Standard Load Balancer.
- An **app tier**: one private Linux VM running a tiny HTTP API on port 8080. Nginx forwards `/api/` calls to it.
- A **database tier**: Azure Database for PostgreSQL Flexible Server with **private access only** (no public endpoint).

Each tier has its own subnet and its own Network Security Group (NSG). Traffic can only flow internet -> web -> app -> db.

At the end, `terraform output` prints a URL. You open it in the browser and see a page served by one of the VMSS instances. The Terraform state lives in an Azure Storage account, so a teammate (or a pipeline) can run the same code safely.

### Architecture

```text
                         Internet
                            |
                 Public IP (Standard, static)
                            |
                Azure Load Balancer (Standard SKU)
                 rule: TCP 80 -> 80, probe: HTTP /
                 outbound rule: SNAT for backend pool
                            |
+---------------------- VNet 10.10.0.0/16 ----------------------+
|                                                               |
|  snet-web 10.10.1.0/24   NSG: allow 80/443 from Internet      |
|   [VMSS instance] [VMSS instance]   (nginx, cloud-init)       |
|            |                                                  |
|            | TCP 8080 only                                    |
|            v                                                  |
|  snet-app 10.10.2.0/24   NSG: allow 8080 from snet-web only   |
|   [app VM, no public IP] --- NAT Gateway (outbound only)      |
|            |                                                  |
|            | TCP 5432 only                                    |
|            v                                                  |
|  snet-db 10.10.3.0/24    NSG: allow 5432 from snet-app only   |
|   [PostgreSQL Flexible Server, delegated subnet]             |
|   Private DNS zone: <name>.private.postgres.database.azure.com|
+---------------------------------------------------------------+

Terraform state -> Storage account (rg-tfstate) / container tfstate / blob 3tier.tfstate
                   locked with a blob lease, auth with Entra ID (no access keys)
```

### Tools and why each one is used

| Tool | What it does here | Why this tool |
| --- | --- | --- |
| Terraform (>= 1.9) | Declares and creates all Azure resources | Declarative, plan before apply, huge provider ecosystem |
| azurerm provider 4.x | Talks to the Azure Resource Manager API | Official provider for Azure; 4.x is the current major version |
| random provider | Generates the database password | Avoids typing a secret into code or tfvars |
| Azure CLI (`az`) | Login, bootstrap of the state storage, verification | Fast for one-time setup and checks |
| Azure Storage (blob) | Stores `terraform.tfstate` remotely | Shared state, built-in locking with blob leases, versioning |
| cloud-init | Installs nginx on each VMSS instance at boot | Native on Ubuntu images, no extra config tool needed |
| PostgreSQL Flexible Server | Managed database tier | No patching or backups to manage; private access through VNet integration |

### Prerequisites

- An Azure subscription where you are **Owner** or **Contributor + User Access Administrator** (you need to create a role assignment for the state storage).
- Azure CLI 2.60 or newer:

```bash
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
az version
az login
az account set --subscription "<subscription-id>"
```

- Terraform 1.9 or newer:

```bash
wget -O- https://apt.releases.hashicorp.com/gpg | sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list
sudo apt update && sudo apt install -y terraform
terraform version
```

- An SSH key pair: `ssh-keygen -t ed25519 -f ~/.ssh/azure_lab` (Azure VMs also accept RSA keys; ed25519 is supported for Linux VMs).

**Cost warning:** this lab creates a Standard Load Balancer, two Standard public IPs, a NAT gateway, 2 small VMs in a scale set, one app VM and a Burstable PostgreSQL server. If left running it costs roughly a few US dollars per day. Run `terraform destroy` when you finish each session.

### Folder structure

```text
3tier-azure/
├── bootstrap/
│   └── create-state-storage.sh   # one-time az CLI script for the backend
├── cloud-init/
│   ├── web.yaml.tftpl            # nginx install + reverse proxy to app tier
│   └── app.yaml                  # tiny API on port 8080
├── versions.tf                   # terraform + provider versions, backend
├── providers.tf                  # provider configuration
├── variables.tf                  # input variables with types and validation
├── main.tf                       # network, NSGs, LB, VMSS, app VM, database
├── outputs.tf                    # LB public IP, URL, db FQDN
├── terraform.tfvars              # your values (no secrets)
└── .gitignore
```

### Step-by-step

#### Step 1: Bootstrap the remote state storage

Terraform cannot create the storage account that holds its own state (chicken and egg). So we create it once with the Azure CLI. We disable shared key access and use Entra ID (Azure AD) roles instead.

```bash
#!/usr/bin/env bash
# bootstrap/create-state-storage.sh
set -euo pipefail

LOCATION="eastus"
RG="rg-tfstate"
SA="sttfstate$RANDOM$RANDOM"     # must be globally unique, 3-24 lowercase letters/digits
CONTAINER="tfstate"

az group create --name "$RG" --location "$LOCATION"

az storage account create \
  --name "$SA" \
  --resource-group "$RG" \
  --location "$LOCATION" \
  --sku Standard_ZRS \
  --kind StorageV2 \
  --min-tls-version TLS1_2 \
  --allow-blob-public-access false \
  --allow-shared-key-access false

# Versioning + soft delete let you recover a broken or deleted state file
az storage account blob-service-properties update \
  --account-name "$SA" --resource-group "$RG" \
  --enable-versioning true \
  --enable-delete-retention true --delete-retention-days 30

# Give yourself data-plane access (management-plane Owner is NOT enough)
SA_ID=$(az storage account show -n "$SA" -g "$RG" --query id -o tsv)
ME=$(az ad signed-in-user show --query id -o tsv)
az role assignment create \
  --assignee-object-id "$ME" --assignee-principal-type User \
  --role "Storage Blob Data Contributor" \
  --scope "$SA_ID"

echo "Waiting 60s for the role assignment to propagate..."
sleep 60

az storage container create --name "$CONTAINER" --account-name "$SA" --auth-mode login

echo "storage_account_name = $SA"
```

What this does:

- `--allow-shared-key-access false` turns off account keys. Nobody can read state with a leaked key.
- `Storage Blob Data Contributor` is a **data-plane** role. Being Owner of the subscription does not let you read blobs when keys are disabled.
- `--auth-mode login` creates the container with your Entra ID token instead of a key.
- Versioning keeps old copies of the state, so you can roll back after a bad write.

Run it with `bash bootstrap/create-state-storage.sh` and copy the storage account name it prints.

#### Step 2: Pin versions and configure the backend

```hcl
# versions.tf
terraform {
  required_version = ">= 1.9.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }

  backend "azurerm" {
    resource_group_name  = "rg-tfstate"
    storage_account_name = "<storage-account-name>"
    container_name       = "tfstate"
    key                  = "3tier.tfstate"
    use_azuread_auth     = true
  }
}
```

What this does:

- `~> 4.0` allows any 4.x version but never 5.0, which could have breaking changes.
- `key` is the blob name. Different projects or environments use different keys in the same container.
- `use_azuread_auth = true` makes the backend use your Entra ID login instead of an account key.
- **Locking** is automatic: during `plan`/`apply` Terraform takes a **lease** on the blob. A second run waits or fails with "state blob is already locked".
- Backend blocks cannot use variables. To keep values out of code you can leave the block empty and run `terraform init -backend-config=backend.hcl`.

#### Step 3: Configure the provider

```hcl
# providers.tf
provider "azurerm" {
  features {
    resource_group {
      prevent_deletion_if_contains_resources = true
    }
  }

  subscription_id     = var.subscription_id
  storage_use_azuread = true
}
```

What this does:

- `features {}` is required, even if empty.
- `subscription_id` is **required in azurerm 4.x**. In 3.x the provider took it from `az account show`; in 4.x you must set it here or in the `ARM_SUBSCRIPTION_ID` environment variable.
- `prevent_deletion_if_contains_resources` stops Terraform deleting a resource group that has resources it does not manage.

#### Step 4: Define variables with types and validation

```hcl
# variables.tf
variable "subscription_id" {
  description = "Azure subscription ID to deploy into."
  type        = string
}

variable "project" {
  description = "Short project name used in resource names."
  type        = string
  default     = "3tier"

  validation {
    condition     = can(regex("^[a-z0-9]{2,10}$", var.project))
    error_message = "project must be 2-10 lowercase letters or digits."
  }
}

variable "environment" {
  description = "Environment name."
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "test", "prod"], var.environment)
    error_message = "environment must be dev, test or prod."
  }
}

variable "location" {
  type    = string
  default = "eastus"
}

variable "address_space" {
  type    = string
  default = "10.10.0.0/16"
}

variable "subnet_prefixes" {
  description = "CIDR for each tier."
  type = object({
    web = string
    app = string
    db  = string
  })
  default = {
    web = "10.10.1.0/24"
    app = "10.10.2.0/24"
    db  = "10.10.3.0/24"
  }
}

variable "web_instance_count" {
  type    = number
  default = 2

  validation {
    condition     = var.web_instance_count >= 1 && var.web_instance_count <= 10
    error_message = "web_instance_count must be between 1 and 10."
  }
}

variable "vm_size" {
  type    = string
  default = "Standard_B2s"
}

variable "admin_username" {
  type    = string
  default = "azureuser"
}

variable "ssh_public_key_path" {
  type    = string
  default = "~/.ssh/azure_lab.pub"
}

variable "db_admin_login" {
  type    = string
  default = "pgadmin"
}

variable "tags" {
  type    = map(string)
  default = {}
}
```

What this does:

- `type` catches mistakes early: a string passed to a `number` variable fails at plan time.
- Primitive types are `string`, `number`, `bool`. Complex types are `list()`, `set()`, `map()`, `object({...})`, `tuple([...])`.
- `validation` blocks give a clear error before any API call. Since Terraform 1.9 a validation can also refer to **other** variables.
- There is no password variable. The password is generated in Step 9 so it never sits in a file you might commit.

#### Step 5: Set your values

```hcl
# terraform.tfvars
subscription_id    = "<subscription-id>"
project            = "3tier"
environment        = "dev"
location           = "eastus"
web_instance_count = 2

tags = {
  owner   = "<your-name>"
  purpose = "terraform-lab"
}
```

```text
# .gitignore
.terraform/
*.tfstate
*.tfstate.*
*.tfplan
tfplan
crash.log
override.tf
override.tf.json
```

What this does:

- `terraform.tfvars` is loaded automatically. Files named `*.auto.tfvars` are loaded too.
- Never commit `.tfstate` or plan files: they can contain secrets in plain text.
- **Do commit** `.terraform.lock.hcl`. It pins exact provider versions and checksums for everyone.

#### Step 6: Resource group, VNet, subnets and NSGs

This is the first part of `main.tf`. Each tier gets a subnet and an NSG with only the rules it needs.

```hcl
# main.tf (part 1 - network)
locals {
  name_prefix = "${var.project}-${var.environment}"
  tags = merge(var.tags, {
    project     = var.project
    environment = var.environment
    managed_by  = "terraform"
  })
}

resource "azurerm_resource_group" "main" {
  name     = "rg-${local.name_prefix}"
  location = var.location
  tags     = local.tags
}

resource "azurerm_virtual_network" "main" {
  name                = "vnet-${local.name_prefix}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  address_space       = [var.address_space]
  tags                = local.tags
}

resource "azurerm_subnet" "web" {
  name                 = "snet-web"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = [var.subnet_prefixes.web]
}

resource "azurerm_subnet" "app" {
  name                 = "snet-app"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = [var.subnet_prefixes.app]
}

resource "azurerm_subnet" "db" {
  name                 = "snet-db"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = [var.subnet_prefixes.db]

  delegation {
    name = "postgres-flexible"
    service_delegation {
      name    = "Microsoft.DBforPostgreSQL/flexibleServers"
      actions = ["Microsoft.Network/virtualNetworks/subnets/join/action"]
    }
  }
}

# ---------- NSG: web ----------
resource "azurerm_network_security_group" "web" {
  name                = "nsg-web-${local.name_prefix}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  tags                = local.tags

  security_rule {
    name                       = "allow-http-https-from-internet"
    priority                   = 100
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_ranges    = ["80", "443"]
    source_address_prefix      = "Internet"
    destination_address_prefix = var.subnet_prefixes.web
  }
}

# ---------- NSG: app ----------
resource "azurerm_network_security_group" "app" {
  name                = "nsg-app-${local.name_prefix}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  tags                = local.tags

  security_rule {
    name                       = "allow-8080-from-web"
    priority                   = 100
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "8080"
    source_address_prefix      = var.subnet_prefixes.web
    destination_address_prefix = var.subnet_prefixes.app
  }

  security_rule {
    name                       = "deny-other-vnet-inbound"
    priority                   = 4000
    direction                  = "Inbound"
    access                     = "Deny"
    protocol                   = "*"
    source_port_range          = "*"
    destination_port_range     = "*"
    source_address_prefix      = "VirtualNetwork"
    destination_address_prefix = "*"
  }
}

# ---------- NSG: db ----------
resource "azurerm_network_security_group" "db" {
  name                = "nsg-db-${local.name_prefix}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  tags                = local.tags

  security_rule {
    name                       = "allow-postgres-from-app"
    priority                   = 100
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "5432"
    source_address_prefix      = var.subnet_prefixes.app
    destination_address_prefix = var.subnet_prefixes.db
  }

  # Needed if you later enable HA (primary and standby replicate inside this subnet)
  security_rule {
    name                       = "allow-intra-db-subnet"
    priority                   = 110
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "*"
    source_port_range          = "*"
    destination_port_range     = "*"
    source_address_prefix      = var.subnet_prefixes.db
    destination_address_prefix = var.subnet_prefixes.db
  }

  security_rule {
    name                       = "deny-other-vnet-inbound"
    priority                   = 4000
    direction                  = "Inbound"
    access                     = "Deny"
    protocol                   = "*"
    source_port_range          = "*"
    destination_port_range     = "*"
    source_address_prefix      = "VirtualNetwork"
    destination_address_prefix = "*"
  }
}

resource "azurerm_subnet_network_security_group_association" "web" {
  subnet_id                 = azurerm_subnet.web.id
  network_security_group_id = azurerm_network_security_group.web.id
}

resource "azurerm_subnet_network_security_group_association" "app" {
  subnet_id                 = azurerm_subnet.app.id
  network_security_group_id = azurerm_network_security_group.app.id
}

resource "azurerm_subnet_network_security_group_association" "db" {
  subnet_id                 = azurerm_subnet.db.id
  network_security_group_id = azurerm_network_security_group.db.id
}
```

What this does:

- `locals` builds one naming prefix and one tag map, so every resource is named and tagged the same way.
- The db subnet is **delegated** to PostgreSQL Flexible Server. A delegated subnet can only hold that service.
- Every NSG has default rules at priority 65000+ which allow all traffic **inside** the VNet (`AllowVnetInBound`). That is why app and db need an explicit `Deny` from `VirtualNetwork` at priority 4000. Without it, the web tier could reach the database directly.
- The default rule `AllowAzureLoadBalancerInBound` lets the LB health probe reach the web VMs, so we do not need a probe rule.
- For 1433 (SQL Server) you would add the same rule with port 1433 instead of 5432.

#### Step 7: Load balancer and outbound access

```hcl
# main.tf (part 2 - load balancer)
resource "azurerm_public_ip" "lb" {
  name                = "pip-lb-${local.name_prefix}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  allocation_method   = "Static"
  sku                 = "Standard"
  zones               = ["1", "2", "3"]
  tags                = local.tags
}

resource "azurerm_lb" "web" {
  name                = "lb-web-${local.name_prefix}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  sku                 = "Standard"
  tags                = local.tags

  frontend_ip_configuration {
    name                 = "fe-public"
    public_ip_address_id = azurerm_public_ip.lb.id
  }
}

resource "azurerm_lb_backend_address_pool" "web" {
  name            = "be-web"
  loadbalancer_id = azurerm_lb.web.id
}

resource "azurerm_lb_probe" "http" {
  name                = "probe-http"
  loadbalancer_id     = azurerm_lb.web.id
  protocol            = "Http"
  port                = 80
  request_path        = "/health"
  interval_in_seconds = 5
  number_of_probes    = 2
}

resource "azurerm_lb_rule" "http" {
  name                           = "rule-http"
  loadbalancer_id                = azurerm_lb.web.id
  protocol                       = "Tcp"
  frontend_port                  = 80
  backend_port                   = 80
  frontend_ip_configuration_name = "fe-public"
  backend_address_pool_ids       = [azurerm_lb_backend_address_pool.web.id]
  probe_id                       = azurerm_lb_probe.http.id
  disable_outbound_snat          = true
  idle_timeout_in_minutes        = 4
}

# Explicit outbound internet access for the web instances (apt install, updates)
resource "azurerm_lb_outbound_rule" "web" {
  name                    = "outbound-web"
  loadbalancer_id         = azurerm_lb.web.id
  protocol                = "All"
  backend_address_pool_id = azurerm_lb_backend_address_pool.web.id

  frontend_ip_configuration {
    name = "fe-public"
  }
}

# NAT gateway for the app subnet (private VM, outbound only)
resource "azurerm_public_ip" "nat" {
  name                = "pip-nat-${local.name_prefix}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  allocation_method   = "Static"
  sku                 = "Standard"
  tags                = local.tags
}

resource "azurerm_nat_gateway" "app" {
  name                    = "nat-app-${local.name_prefix}"
  location                = azurerm_resource_group.main.location
  resource_group_name     = azurerm_resource_group.main.name
  sku_name                = "Standard"
  idle_timeout_in_minutes = 10
  tags                    = local.tags
}

resource "azurerm_nat_gateway_public_ip_association" "app" {
  nat_gateway_id       = azurerm_nat_gateway.app.id
  public_ip_address_id = azurerm_public_ip.nat.id
}

resource "azurerm_subnet_nat_gateway_association" "app" {
  subnet_id      = azurerm_subnet.app.id
  nat_gateway_id = azurerm_nat_gateway.app.id
}
```

What this does:

- A **Standard** LB needs a **Standard** public IP. Basic SKU public IPs are retired, so always use Standard.
- Standard LB is "secure by default": inbound traffic is blocked unless an NSG allows it (Step 6 does).
- The **health probe** calls `/health` every 5 seconds. An instance that fails 2 probes is removed from rotation.
- `disable_outbound_snat = true` on the LB rule plus an **outbound rule** gives explicit, predictable outbound SNAT. Azure is retiring "default outbound access" for VMs, so you should always define outbound on purpose.
- The app VM has no public IP and is not behind the LB, so it gets a **NAT gateway** for outbound only (for `apt`). A NAT gateway is the recommended outbound method at scale; you could use one for the web subnet too instead of the outbound rule.

#### Step 8: Web tier (VM Scale Set) and app tier (VM)

First the cloud-init files.

```yaml
# cloud-init/web.yaml.tftpl
#cloud-config
package_update: true
packages:
  - nginx
write_files:
  - path: /etc/nginx/sites-available/default
    content: |
      server {
        listen 80 default_server;
        location /health { return 200 "ok\n"; }
        location /api/ { proxy_pass http://${app_private_ip}:8080/; }
        location / {
          default_type text/html;
          return 200 "<h1>Web tier: $hostname</h1>\n";
        }
      }
runcmd:
  - systemctl enable nginx
  - systemctl restart nginx
```

```yaml
# cloud-init/app.yaml
#cloud-config
write_files:
  - path: /etc/systemd/system/demo-api.service
    content: |
      [Unit]
      Description=Demo API
      After=network.target
      [Service]
      ExecStart=/usr/bin/python3 -m http.server 8080 --directory /opt/api
      Restart=always
      [Install]
      WantedBy=multi-user.target
  - path: /opt/api/index.html
    content: |
      {"tier": "app", "status": "ok"}
runcmd:
  - systemctl daemon-reload
  - systemctl enable --now demo-api
```

Now the compute resources.

```hcl
# main.tf (part 3 - compute)
resource "azurerm_network_interface" "app" {
  name                = "nic-app-${local.name_prefix}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  tags                = local.tags

  ip_configuration {
    name                          = "internal"
    subnet_id                     = azurerm_subnet.app.id
    private_ip_address_allocation = "Dynamic"
  }
}

resource "azurerm_linux_virtual_machine" "app" {
  name                  = "vm-app-${local.name_prefix}"
  location              = azurerm_resource_group.main.location
  resource_group_name   = azurerm_resource_group.main.name
  size                  = var.vm_size
  admin_username        = var.admin_username
  network_interface_ids = [azurerm_network_interface.app.id]
  custom_data           = base64encode(file("${path.module}/cloud-init/app.yaml"))
  tags                  = local.tags

  admin_ssh_key {
    username   = var.admin_username
    public_key = file(pathexpand(var.ssh_public_key_path))
  }

  os_disk {
    caching              = "ReadWrite"
    storage_account_type = "Standard_LRS"
  }

  source_image_reference {
    publisher = "Canonical"
    offer     = "ubuntu-24_04-lts"
    sku       = "server"
    version   = "latest"
  }

  # NAT gateway must exist before the VM boots, or apt in cloud-init has no internet
  depends_on = [azurerm_subnet_nat_gateway_association.app]
}

resource "azurerm_linux_virtual_machine_scale_set" "web" {
  name                = "vmss-web-${local.name_prefix}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  sku                 = var.vm_size
  instances           = var.web_instance_count
  admin_username      = var.admin_username
  zones               = ["1", "2", "3"]
  upgrade_mode        = "Rolling"
  health_probe_id     = azurerm_lb_probe.http.id
  tags                = local.tags

  custom_data = base64encode(templatefile("${path.module}/cloud-init/web.yaml.tftpl", {
    app_private_ip = azurerm_network_interface.app.private_ip_address
  }))

  admin_ssh_key {
    username   = var.admin_username
    public_key = file(pathexpand(var.ssh_public_key_path))
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
      subnet_id                              = azurerm_subnet.web.id
      load_balancer_backend_address_pool_ids = [azurerm_lb_backend_address_pool.web.id]
    }
  }

  rolling_upgrade_policy {
    max_batch_instance_percent              = 50
    max_unhealthy_instance_percent          = 50
    max_unhealthy_upgraded_instance_percent = 50
    pause_time_between_batches              = "PT30S"
  }

  # Rolling upgrades need the probe to be used by an LB rule first
  depends_on = [azurerm_lb_rule.http, azurerm_lb_outbound_rule.web]
}
```

What this does:

- `custom_data` must be **base64**. `templatefile()` injects the app VM private IP into the nginx config.
- `$hostname` (single dollar, no braces) is an nginx variable, so Terraform leaves it alone. Only `${...}` is a template placeholder.
- `admin_ssh_key` means password login is disabled (`disable_password_authentication` defaults to `true` when a key is set).
- `upgrade_mode` controls what happens when you change the model (for example a new image or new custom_data):
  - `Manual`: nothing happens to existing instances until you upgrade them yourself.
  - `Automatic`: Azure updates all instances at once (can cause downtime).
  - `Rolling`: Azure updates in batches and checks health between batches. It needs `health_probe_id` (or the Application Health extension) and a `rolling_upgrade_policy`.
- Changing `custom_data` on a VMSS updates the model; instances only run cloud-init again when they are reimaged.
- `zones = ["1","2","3"]` spreads instances across availability zones. Remove it if your region has no zones.

#### Step 9: Database tier (PostgreSQL Flexible Server, private access)

**Why Flexible Server and not a VM?** A database VM means you patch the OS, configure backups, and handle failover yourself. Flexible Server is managed, supports VNet integration (no public endpoint at all), automatic backups and optional zone-redundant HA. For a lab, the Burstable `B_Standard_B1ms` SKU keeps cost low.

```hcl
# main.tf (part 4 - database)
resource "random_password" "db" {
  length           = 24
  special          = true
  override_special = "!#%*-_=+"
}

resource "azurerm_private_dns_zone" "postgres" {
  name                = "${local.name_prefix}.private.postgres.database.azure.com"
  resource_group_name = azurerm_resource_group.main.name
  tags                = local.tags
}

resource "azurerm_private_dns_zone_virtual_network_link" "postgres" {
  name                  = "link-${local.name_prefix}"
  resource_group_name   = azurerm_resource_group.main.name
  private_dns_zone_name = azurerm_private_dns_zone.postgres.name
  virtual_network_id    = azurerm_virtual_network.main.id
  registration_enabled  = false
}

resource "azurerm_postgresql_flexible_server" "db" {
  name                          = "psql-${local.name_prefix}-${substr(md5(azurerm_resource_group.main.id), 0, 6)}"
  location                      = azurerm_resource_group.main.location
  resource_group_name           = azurerm_resource_group.main.name
  version                       = "16"
  sku_name                      = "B_Standard_B1ms"
  storage_mb                    = 32768
  backup_retention_days         = 7
  zone                          = "1"
  delegated_subnet_id           = azurerm_subnet.db.id
  private_dns_zone_id           = azurerm_private_dns_zone.postgres.id
  public_network_access_enabled = false
  administrator_login           = var.db_admin_login
  administrator_password        = random_password.db.result
  tags                          = local.tags

  depends_on = [azurerm_private_dns_zone_virtual_network_link.postgres]
}

resource "azurerm_postgresql_flexible_server_database" "app" {
  name      = "appdb"
  server_id = azurerm_postgresql_flexible_server.db.id
  charset   = "UTF8"
  collation = "en_US.utf8"
}
```

What this does:

- `delegated_subnet_id` + `private_dns_zone_id` = **private access (VNet integration)**. The server gets a private IP in `snet-db` and a name that only resolves inside the VNet.
- The private DNS zone name must end in `.private.postgres.database.azure.com`.
- `depends_on` on the DNS link is needed because Terraform cannot see that the server needs the link to exist first (it only references the zone, not the link). This is a **hidden dependency**.
- `random_password.db.result` is marked **sensitive** by the provider, so it never prints in plan output. It **is** stored in state in plain text, which is one more reason the state backend must be locked down.
- The server name must be globally unique, so we add a short hash suffix.

#### Step 10: Outputs

```hcl
# outputs.tf
output "lb_public_ip" {
  description = "Public IP of the web load balancer."
  value       = azurerm_public_ip.lb.ip_address
}

output "web_url" {
  description = "URL of the web tier."
  value       = "http://${azurerm_public_ip.lb.ip_address}"
}

output "app_private_ip" {
  value = azurerm_network_interface.app.private_ip_address
}

output "db_fqdn" {
  description = "Private FQDN of PostgreSQL (resolves only inside the VNet)."
  value       = azurerm_postgresql_flexible_server.db.fqdn
}

output "db_admin_password" {
  value     = random_password.db.result
  sensitive = true
}
```

What this does:

- Outputs show useful values after apply and can be read by scripts with `terraform output -raw web_url`.
- `sensitive = true` hides the value in CLI output (`<sensitive>`). Terraform forces you to mark an output sensitive if it uses a sensitive value. Read it on purpose with `terraform output -raw db_admin_password`.

#### Step 11: Run the Terraform workflow

```bash
cd 3tier-azure
terraform init                 # downloads providers, connects to the backend
terraform fmt -recursive       # rewrites files to canonical style
terraform validate             # checks syntax and types (no API calls)
terraform plan -out=tfplan     # shows the diff and saves it
terraform apply tfplan         # applies exactly the saved plan
```

What each command does:

- `init`: downloads providers into `.terraform/`, writes/reads `.terraform.lock.hcl`, configures the backend. Re-run it after changing providers, modules or the backend (`-upgrade` to move to newer allowed versions, `-reconfigure` or `-migrate-state` after a backend change).
- `fmt`: formatting only. In CI use `terraform fmt -check -recursive`, which fails if files are not formatted.
- `validate`: checks the configuration is internally valid. It does not check that a VM size exists in your region.
- `plan -out=tfplan`: refreshes state from Azure, compares with code, and saves the plan. Symbols: `+` create, `-` destroy, `~` update in place, `-/+` replace.
- `apply tfplan`: applies the saved plan with no second prompt. If the state changed since the plan, Terraform refuses ("Saved plan is stale"), which protects you.
- `destroy`: deletes everything in state. Use `terraform plan -destroy` first to preview.

#### Step 12: Understand state and the dependency graph

```bash
terraform state list
terraform state show azurerm_lb.web
terraform graph | head -30
```

Expected `state list` output (shortened):

```text
azurerm_lb.web
azurerm_lb_backend_address_pool.web
azurerm_lb_outbound_rule.web
azurerm_lb_probe.http
azurerm_lb_rule.http
azurerm_linux_virtual_machine.app
azurerm_linux_virtual_machine_scale_set.web
azurerm_nat_gateway.app
azurerm_network_security_group.app
...
azurerm_postgresql_flexible_server.db
random_password.db
```

What this shows:

- **State** maps each resource address in code (for example `azurerm_lb.web`) to a real Azure resource ID. Without state, Terraform would not know what it already created.
- Terraform builds a **dependency graph** from references. `azurerm_lb_rule.http` references `azurerm_lb_probe.http.id`, so the probe is created first. Independent resources (like the three NSGs) are created **in parallel** (10 at a time by default, `-parallelism=n` to change).
- `depends_on` is only for hidden dependencies the graph cannot see, like the DNS link in Step 9.
- On destroy, Terraform walks the graph in reverse.

### Verify it works

```bash
terraform output web_url
curl -s "$(terraform output -raw web_url)"
curl -s "$(terraform output -raw web_url)/api/"
```

Expected output:

```text
"http://20.x.x.x"
<h1>Web tier: vmss-web-3tier-dev000001</h1>
{"tier": "app", "status": "ok"}
```

Run `curl` a few times; the hostname should change between instances. Then check the backend health and the database privacy:

```bash
RG=rg-3tier-dev
az network lb show -g $RG -n lb-web-3tier-dev --query "probes[].name" -o tsv
az vmss list-instances -g $RG -n vmss-web-3tier-dev --query "[].{name:name, state:provisioningState}" -o table

# DB has no public access
az postgres flexible-server show -g $RG -n "$(terraform output -raw db_fqdn | cut -d. -f1)" \
  --query "network.publicNetworkAccess" -o tsv
# Expected: Disabled

# From the app VM, the DB name resolves to a private IP and port 5432 is open
az vm run-command invoke -g $RG -n vm-app-3tier-dev --command-id RunShellScript \
  --scripts "getent hosts $(terraform output -raw db_fqdn); timeout 3 bash -c '</dev/tcp/$(terraform output -raw db_fqdn)/5432' && echo DB_REACHABLE"
```

Also confirm locking: run `terraform plan` in two terminals at the same time. The second one should report that the state blob is already locked.

### Common problems and fixes

| Problem | Likely cause | Fix |
| --- | --- | --- |
| `subscription_id is a required provider property` | azurerm 4.x needs it explicitly | Set `subscription_id` in the provider or export `ARM_SUBSCRIPTION_ID` |
| `init` fails with 403 `AuthorizationPermissionMismatch` on the backend | No data-plane role on the storage account, or role not propagated | Assign `Storage Blob Data Contributor` and wait a few minutes |
| `Error acquiring the state lock` | A previous run crashed or another run is active | Make sure nobody else is running; then `terraform force-unlock <lock-id>` |
| Browser times out on the LB IP | NSG on web subnet missing, or cloud-init still running | Check NSG rule for port 80; wait 2-3 minutes; check probe status |
| VMSS instances unhealthy, Rolling upgrade fails | `/health` not served because nginx failed to install (no outbound) | Ensure the outbound rule exists; check `/var/log/cloud-init-output.log` via run-command |
| `SkuNotAvailable` for VM or PostgreSQL | Size not offered in region or zone | Try another region/size; `az vm list-skus -l eastus --size Standard_B -o table` |
| PostgreSQL create fails on subnet | Subnet not delegated or has other resources | Use a dedicated, delegated subnet for Flexible Server |
| Plan shows replacement of the VMSS | You changed a ForceNew argument (for example `zones` or `admin_username`) | Read the plan line `# forces replacement`; revert or plan a maintenance window |

### Clean up

```bash
terraform plan -destroy -out=destroy.tfplan
terraform apply destroy.tfplan

# Optional: remove the state storage when you no longer need it
az group delete --name rg-tfstate --yes --no-wait
```

Check nothing is left: `az group list --query "[?starts_with(name,'rg-3tier')].name" -o tsv` should print nothing.

### Next improvements

- Add HTTPS: put an **Application Gateway with WAF** (or Azure Front Door) in front, with a Key Vault certificate.
- Replace SSH with **Azure Bastion** for admin access and remove all inbound management ports.
- Add VMSS **autoscale** with `azurerm_monitor_autoscale_setting` based on CPU.
- Use **Entra ID authentication** for PostgreSQL and a managed identity on the app VM, so no DB password exists.
- Use `administrator_password_wo` (write-only argument, Terraform 1.11+) so the DB password is not stored in state.
- Turn on zone-redundant HA for PostgreSQL in prod.
- Split into modules and environments (Project 3.1) and add CI/CD (Project 3.2).

### How to explain this project in an interview

> "As a hands-on practice project, I built a 3-tier architecture on Azure using Terraform with the azurerm 4.x provider. The web tier is a Linux VM Scale Set running nginx behind a Standard Load Balancer with a health probe and rolling upgrades. The app tier is a private VM, and the database is PostgreSQL Flexible Server with private VNet access, so it has no public endpoint. Each tier has its own subnet and NSG, and I added explicit deny rules because Azure allows all VNet traffic by default. Outbound access is explicit, using an LB outbound rule for the web tier and a NAT gateway for the app tier. State is stored in an Azure Storage backend with Entra ID auth, shared keys disabled, versioning on, and locking through blob leases. I always run plan with -out and apply the saved plan. The main lessons were hidden dependencies, sensitive values in state, and reading the plan carefully for forced replacements."

Points that impress interviewers:

- You know NSG default rules allow all intra-VNet traffic and you add explicit denies.
- You can explain why outbound access must be explicit (default outbound access retirement, SNAT ports).
- You know sensitive values still land in state, and how you protect state (RBAC, no keys, versioning).
- You can explain `upgrade_mode` options for a VMSS and why Rolling needs a health probe.

## Interview Questions

<details><summary>Q1. [Basic] What is Terraform state and why do we store it remotely?</summary>

**Answer:**

State is a JSON file that maps resource addresses in code (like `azurerm_lb.web`) to real resource IDs in Azure, plus their last known attributes. Terraform uses it to calculate the diff during `plan`.

Storing it remotely (for example in an Azure Storage container) gives:

- One shared source of truth for the team and for pipelines.
- **Locking**, so two applies cannot run at the same time. The azurerm backend uses a blob lease.
- Durability and history through blob versioning and soft delete.
- Access control through Entra ID roles, which matters because state can contain secrets.

</details>

<details><summary>Q2. [Basic] What is the difference between <code>terraform plan</code> and <code>terraform plan -out=tfplan</code> followed by <code>terraform apply tfplan</code>?</summary>

**Answer:**

A plain `terraform plan` only shows the diff. When you later run `terraform apply`, Terraform plans **again**, and the result can differ if someone changed Azure or the code in between.

With `-out=tfplan`, the exact plan is saved. `terraform apply tfplan` applies only those changes, without a new prompt. If the state changed after the plan was made, Terraform rejects the stale plan. This is the safe pattern for pipelines: a human reviews a plan, and exactly that plan is applied.

</details>

<details><summary>Q3. [Basic] Why is <code>subscription_id</code> needed in the azurerm 4.x provider block?</summary>

**Answer:**

In azurerm 3.x, the provider could pick the subscription from the current Azure CLI context. In 4.x, `subscription_id` became a **required** setting. You can set it in the provider block or with the `ARM_SUBSCRIPTION_ID` environment variable. This avoids accidental deployments into whatever subscription happens to be selected in the CLI. In pipelines the environment variable is common, so the same code works for several subscriptions.

</details>

<details><summary>Q4. [Intermediate] How does Terraform decide the order in which resources are created? When do you need <code>depends_on</code>?</summary>

**Answer:**

Terraform builds a **dependency graph** from references between resources. If `azurerm_lb_rule.http` uses `azurerm_lb_probe.http.id`, the probe is created first. Resources with no dependency between them are created in parallel. On destroy the graph is walked in reverse.

`depends_on` is only needed for **hidden dependencies** that Terraform cannot see from references. Example from this project: the PostgreSQL server references the private DNS zone, but it also needs the zone's **VNet link** to exist. Nothing in the server block references the link, so we add `depends_on`. Overusing `depends_on` makes plans slower and more conservative, so use it only when needed.

</details>

<details><summary>Q5. [Intermediate] How do you handle sensitive values like a database password in Terraform?</summary>

**Answer:**

- Do not hardcode them or put them in committed tfvars files.
- Generate them (`random_password`) or read them from Key Vault with a data source, or pass them through environment variables like `TF_VAR_db_password`.
- Mark variables and outputs `sensitive = true` so they are hidden in plan and output.
- Remember that `sensitive` only hides values in the CLI. They are still stored **in plain text in state**. So protect state: private storage, Entra ID RBAC, no shared keys, versioning.
- Better: avoid the secret entirely (Entra ID auth for PostgreSQL with managed identity), or use **write-only arguments** (Terraform 1.11+, for example `administrator_password_wo`) which are never stored in state.

</details>

<details><summary>Q6. [Intermediate] Why did you add a Deny rule from <code>VirtualNetwork</code> on the app and db NSGs?</summary>

**Answer:**

Every NSG has default rules. `AllowVnetInBound` (priority 65000) allows all traffic from anywhere in the VNet (and peered VNets). So without extra rules, a web VM could connect straight to the database on 5432, which breaks the tier isolation.

The fix is to allow only the needed flow (app subnet -> db on 5432) at a low priority number (100), and then add a `Deny` from `VirtualNetwork` at a higher number (4000). Lower numbers are evaluated first, so the allow wins for the right source and everything else from the VNet is blocked. The default `AllowAzureLoadBalancerInBound` still lets health probes work.

</details>

<details><summary>Q7. [Advanced] Your VMSS instances are created but the load balancer URL times out. How do you troubleshoot? <em>(scenario)</em></summary>

**Answer:**

Work from the outside in:

1. **Public IP and rule**: confirm `terraform output web_url` matches the LB frontend and that an LB rule exists for port 80.
2. **Probe health**: check the LB metrics "Health Probe Status" in the portal. If 0%, the backends are failing the probe.
3. **NSG**: a Standard LB blocks inbound unless an NSG allows it. Check the web subnet NSG allows 80 from `Internet`. Use `az network watcher test-ip-flow` or "Effective security rules".
4. **Instance software**: use `az vmss run-command invoke` to run `systemctl status nginx` and read `/var/log/cloud-init-output.log`. A common cause is cloud-init failing to install nginx because the instances have **no outbound internet** (no outbound rule or NAT gateway).
5. **Probe path**: make sure the probe path (`/health`) actually returns 200.

Fix the root cause, then reimage instances so cloud-init runs again (`az vmss reimage`).

</details>

<details><summary>Q8. [Advanced] A teammate's laptop crashed during <code>terraform apply</code>. Now everyone gets "state blob is already locked". What do you do? <em>(scenario)</em></summary>

**Answer:**

1. Confirm no apply is really running: ask the team, check pipeline runs.
2. Read the lock info in the error (lock ID, who, when). On Azure you can also see the blob lease state on the `.tfstate` blob.
3. Run `terraform force-unlock <lock-id>`. If that is not possible, break the lease with `az storage blob lease break --blob-name 3tier.tfstate --container-name tfstate --account-name <sa> --auth-mode login`.
4. Run `terraform plan` to see what the crashed apply left behind. Resources created before the crash may be in state already; others may exist in Azure but not in state and need `terraform import`.
5. If state looks corrupted, restore a previous blob **version** (that is why versioning is enabled).

Never force-unlock while another run is truly active; two writers can corrupt the state.

</details>

<details><summary>Q9. [Advanced] Why did you choose PostgreSQL Flexible Server with private access instead of a database VM? <em>(scenario)</em></summary>

**Answer:**

A database VM gives full control but you own OS patching, database upgrades, backups, monitoring, and high availability. Flexible Server is managed: automated backups with point-in-time restore, optional zone-redundant HA, and maintenance windows.

With **private access (VNet integration)**, the server is injected into a delegated subnet and gets a private IP. It has no public endpoint, and the name resolves through a private DNS zone linked to the VNet. Combined with the db NSG allowing only the app subnet on 5432, this gives strong isolation.

Trade-offs: the delegated subnet can only hold Flexible Servers, and private access is chosen at create time (switching to public needs a new server). A VM would still make sense if you need an engine version or extension the managed service does not support.

</details>
