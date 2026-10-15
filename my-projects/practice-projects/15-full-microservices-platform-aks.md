# Practice Project 15: Full Microservices CI/CD Platform on AKS with Terraform, Helm and GitHub Actions

> A step-by-step lab that combines Terraform, AKS, ACR, Key Vault, Service Bus, Azure Functions, Helm, GitHub Actions and Azure Monitor into one enterprise-style platform, with passwordless identity everywhere and a phased build plan.

## Key Concepts

### What you will build

You will build a small but realistic platform for an "orders" microservice:

- **Terraform** creates all Azure resources: AKS, ACR, Log Analytics with Container Insights, Key Vault with the Secrets Store CSI driver add-on, workload identity, a Service Bus queue, and a Function App.
- **GitHub Actions** builds the Docker image, scans it with Trivy, pushes it to ACR, and deploys it with Helm. Dev deploys automatically. Prod waits for a human approval.
- **Helm** deploys the same chart to two namespaces, `orders-dev` and `orders-prod`, with different values files.
- **The orders API** (Python FastAPI) accepts an order, checks an API key that comes from Key Vault, and publishes a message to Service Bus. It uses workload identity, so there is no connection string anywhere.
- **The Function App** (Python v2 model) reads messages from the queue and processes them in the background. It uses its own managed identity.
- **Azure Monitor** collects container logs, metrics, Kubernetes audit logs, and Function telemetry. You query everything with KQL.

No passwords, client secrets, or connection strings are stored in code, in GitHub, or in Kubernetes Secrets you create by hand.

### Architecture

```text
                        Developer pushes to GitHub
                                   |
          +------------------------+-------------------------+
          |                        |                         |
   infra.yml (infra/**)     ci-cd.yml (services/, helm/)   functions.yml (functions/**)
   plan on PR               build -> Trivy -> push ACR      deploy dev -> approve -> prod
   apply on main (approval) helm dev -> approve -> prod
          |                        |                         |
          |   all three log in to Azure with OIDC (no secrets) via a user-assigned identity
          v                        v                         v
+------------------------------------------------------------------------------------+
| Azure subscription                                                                  |
|                                                                                     |
|  rg-<prefix>-tfstate: Storage account (Terraform state), GitHub OIDC identity       |
|                                                                                     |
|  rg-<prefix>-platform:                                                              |
|                                                                                     |
|   +-----------+  AcrPull   +---------------------------------------------+          |
|   |   ACR     |<-----------| AKS (OIDC issuer + workload identity)       |          |
|   +-----------+  (kubelet) |  app routing add-on (NGINX ingress)         |          |
|                            |  Key Vault CSI add-on (rotation on)         |          |
|                            |  ns orders-dev:  orders pods (SA "orders")  |          |
|                            |  ns orders-prod: orders pods (SA "orders")  |          |
|                            +--------+-------------------+----------------+          |
|                                     | token exchange    | send message             |
|                                     v                   v                          |
|   +----------------+  Secrets User  +-----------------------------+                |
|   |  Key Vault     |<---------------| id-orders-dev / id-orders-prod|              |
|   |  (RBAC mode)   |                | (user-assigned identities)   |               |
|   +----------------+                +--------------+--------------+                |
|                                                    | Data Sender                   |
|                                                    v                               |
|                                     +-----------------------------+                |
|                                     | Service Bus namespace       |                |
|                                     |  queue orders-dev           |                |
|                                     |  queue orders-prod          |                |
|                                     +--------------+--------------+                |
|                                                    | Data Receiver                 |
|                                                    v                               |
|                                     +-----------------------------+                |
|                                     | Function Apps (dev, prod)   |                |
|                                     |  system-assigned identity   |                |
|                                     +-----------------------------+                |
|                                                                                     |
|   Log Analytics workspace <- Container Insights, AKS audit logs, App Insights       |
+------------------------------------------------------------------------------------+
```

### Tools and why each one is used

| Tool | What it does here | Why this tool |
| --- | --- | --- |
| Terraform (>= 1.9) with azurerm 4.x | Creates every Azure resource and role assignment | Declarative, reviewable plans, remote state, widely used |
| Azure Storage (backend) | Stores Terraform state with locking | Built-in blob lease locking, Entra ID auth, versioning |
| AKS | Runs the orders service in two namespaces | Managed Kubernetes with add-ons for identity, secrets, ingress, monitoring |
| ACR | Stores container images | Private registry, kubelet pulls with managed identity |
| Workload identity | Lets pods get Entra ID tokens | Replaces pod-managed identity, no secrets in pods |
| Key Vault + CSI driver | Mounts secrets as files in pods | Secrets stay in Key Vault, rotation without redeploy |
| Service Bus | Queue between API and background worker | Reliable delivery, retries, dead-letter queue |
| Azure Functions (Python v2) | Consumes queue messages | Event-driven code with built-in Service Bus trigger |
| Helm | Packages Kubernetes manifests with per-env values | One chart, many environments, atomic upgrades and rollback |
| GitHub Actions | CI/CD for infra, app and functions | OIDC to Azure, environments with approvals |
| Trivy | Scans images for vulnerabilities | Free, fast, fails the build on CRITICAL/HIGH |
| Azure Monitor / Log Analytics | Logs, metrics, KQL queries | Native for AKS and Functions, one workspace for all |

### Prerequisites

- An Azure subscription where you are **Owner** (you need to create role assignments).
- Azure CLI 2.60 or newer, Terraform 1.9 or newer, Helm 3.x, kubectl, kubelogin, Docker, Python 3.12, and the GitHub CLI (`gh`).
- A GitHub repository you own, for example `<owner>/orders-platform`.
- Basic knowledge of Docker, Kubernetes objects, and Terraform `plan`/`apply`.
- Resource providers registered: `Microsoft.ContainerService`, `Microsoft.ServiceBus`, `Microsoft.Web`, `Microsoft.Insights`, `Microsoft.OperationalInsights`, `Microsoft.KeyVault`.

```bash
az login
az account set --subscription "<subscription-id>"
for rp in Microsoft.ContainerService Microsoft.ServiceBus Microsoft.Web Microsoft.Insights \
          Microsoft.OperationalInsights Microsoft.KeyVault Microsoft.ContainerRegistry; do
  az provider register --namespace "$rp"
done
```

### Folder structure

```text
orders-platform/
├── .github/
│   └── workflows/
│       ├── infra.yml              # terraform plan on PR, apply on main (approval)
│       ├── ci-cd.yml              # build, Trivy, push, helm dev -> prod
│       └── functions.yml          # deploy Function App dev -> prod
├── infra/
│   ├── bootstrap/
│   │   └── main.tf                # state storage + GitHub OIDC identity (run once, locally)
│   ├── providers.tf               # versions, backend, provider
│   ├── variables.tf
│   ├── main.tf                    # resource group, naming, locals
│   ├── monitoring.tf              # Log Analytics, App Insights, Container Insights DCR
│   ├── acr.tf
│   ├── aks.tf
│   ├── keyvault.tf
│   ├── servicebus.tf
│   ├── identity.tf                # workload identities, federated creds, role assignments
│   ├── function.tf
│   ├── outputs.tf
│   └── terraform.tfvars
├── services/
│   └── orders/
│       ├── app/
│       │   ├── __init__.py
│       │   └── main.py
│       ├── requirements.txt
│       ├── Dockerfile
│       └── .dockerignore
├── functions/
│   └── order-processor/
│       ├── function_app.py
│       ├── host.json
│       └── requirements.txt
└── helm/
    └── app/                       # generic chart, reused by any service
        ├── Chart.yaml
        ├── values.yaml
        ├── values-dev.yaml
        ├── values-prod.yaml
        └── templates/
            ├── _helpers.tpl
            ├── serviceaccount.yaml
            ├── deployment.yaml
            ├── service.yaml
            ├── ingress.yaml
            ├── hpa.yaml
            ├── pdb.yaml
            └── secretproviderclass.yaml
```

### Build it in phases

Do not try to build everything in one evening. Each phase ends with something you can test.

| Phase | Goal | Steps | Done when |
| --- | --- | --- | --- |
| 1. Foundation | Remote state, GitHub OIDC identity, resource group, Log Analytics, ACR, AKS | 1-5, 10 | `kubectl get nodes` works with your Entra ID login |
| 2. App and chart | Orders API, Dockerfile, Helm chart, CI build + Trivy + push + deploy dev | 11-13, 15, 17 | `curl` through the ingress returns `/healthz` OK in dev |
| 3. Secrets and identity | Key Vault, CSI driver, workload identity, API key check | 6, 8 | API returns 401 without key and 202 with the Key Vault key |
| 4. Async processing | Service Bus queue, Function App, functions workflow | 7, 9, 14, 18 | A POST shows up in Function logs a few seconds later |
| 5. Production readiness | Prod namespace with approvals, HPA, PDB, infra workflow, KQL, alerts | 16, 19, 20 | Prod deploys only after approval, dashboards and queries work |

Tip: in phase 1 and 2, you can comment out resources from later phases (Key Vault, Service Bus, Function) and set `keyVault.enabled: false` in the chart. Add them back in later phases.

### Step-by-step

#### Step 1: Bootstrap remote state and the GitHub OIDC identity

Terraform state must exist before the main stack, and GitHub needs an identity before any workflow can run. This small stack is applied once from your laptop with local state.

```hcl
# infra/bootstrap/main.tf
terraform {
  required_version = ">= 1.9.0"
  required_providers {
    azurerm = { source = "hashicorp/azurerm", version = "~> 4.65" }
    random  = { source = "hashicorp/random", version = "~> 3.6" }
  }
}

provider "azurerm" {
  subscription_id     = var.subscription_id
  storage_use_azuread = true
  features {}
}

variable "subscription_id" { type = string }
variable "prefix" { type = string }               # short, lowercase, e.g. "ordlab"
variable "location" {
  type    = string
  default = "eastus2"
}
variable "github_repo" { type = string }          # "<owner>/<repo>"

data "azurerm_subscription" "current" {}
data "azurerm_client_config" "current" {}

resource "random_string" "suffix" {
  length  = 4
  upper   = false
  special = false
}

resource "azurerm_resource_group" "state" {
  name     = "rg-${var.prefix}-tfstate"
  location = var.location
}

resource "azurerm_storage_account" "state" {
  name                            = "st${var.prefix}tf${random_string.suffix.result}"
  resource_group_name             = azurerm_resource_group.state.name
  location                        = azurerm_resource_group.state.location
  account_tier                    = "Standard"
  account_replication_type        = "ZRS"
  min_tls_version                 = "TLS1_2"
  shared_access_key_enabled       = false
  allow_nested_items_to_be_public = false

  blob_properties {
    versioning_enabled = true
    delete_retention_policy {
      days = 14
    }
  }
}

resource "azurerm_storage_container" "state" {
  name                  = "tfstate"
  storage_account_id    = azurerm_storage_account.state.id
  container_access_type = "private"
}

# Identity that GitHub Actions logs in as (OIDC, no client secret)
resource "azurerm_user_assigned_identity" "github" {
  name                = "id-${var.prefix}-github"
  resource_group_name = azurerm_resource_group.state.name
  location            = azurerm_resource_group.state.location
}

locals {
  github_subjects = {
    pr    = "repo:${var.github_repo}:pull_request"
    main  = "repo:${var.github_repo}:ref:refs/heads/main"
    infra = "repo:${var.github_repo}:environment:infra"
    dev   = "repo:${var.github_repo}:environment:dev"
    prod  = "repo:${var.github_repo}:environment:prod"
  }
}

resource "azurerm_federated_identity_credential" "github" {
  for_each            = local.github_subjects
  name                      = "github-${each.key}"
  user_assigned_identity_id = azurerm_user_assigned_identity.github.id
  audience                  = ["api://AzureADTokenExchange"]
  issuer                    = "https://token.actions.githubusercontent.com"
  subject                   = each.value
}

# Lab-level permissions. Tighten these for real use (see Security checklist).
resource "azurerm_role_assignment" "github_contributor" {
  scope                = data.azurerm_subscription.current.id
  role_definition_name = "Contributor"
  principal_id         = azurerm_user_assigned_identity.github.principal_id
}

resource "azurerm_role_assignment" "github_rbac_admin" {
  scope                = data.azurerm_subscription.current.id
  role_definition_name = "Role Based Access Control Administrator"
  principal_id         = azurerm_user_assigned_identity.github.principal_id
}

resource "azurerm_role_assignment" "github_state" {
  scope                = azurerm_storage_account.state.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_user_assigned_identity.github.principal_id
}

resource "azurerm_role_assignment" "me_state" {
  scope                = azurerm_storage_account.state.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = data.azurerm_client_config.current.object_id
}

output "state_storage_account" { value = azurerm_storage_account.state.name }
output "github_client_id" { value = azurerm_user_assigned_identity.github.client_id }
output "github_principal_id" { value = azurerm_user_assigned_identity.github.principal_id }
output "tenant_id" { value = data.azurerm_client_config.current.tenant_id }
```

```bash
cd infra/bootstrap
terraform init
terraform apply \
  -var "subscription_id=<subscription-id>" \
  -var "prefix=<prefix>" \
  -var "github_repo=<owner>/<repo>"
terraform output
```

What this does:

- `shared_access_key_enabled = false` forces Entra ID auth on the state account. `storage_use_azuread = true` tells the provider to use Entra ID too.
- Each federated credential trusts one exact GitHub subject. A PR, a push to `main`, and each GitHub environment get a different subject string.
- `Role Based Access Control Administrator` is needed because the main stack creates role assignments. Restrict it with a condition later.
- The federated credential uses `user_assigned_identity_id`. Provider versions before 4.65 call this argument `parent_id` and also need `resource_group_name`.
- Keep the bootstrap `terraform.tfstate` file safe and out of Git. It is small but it is the only record of these resources.

#### Step 2: Providers, backend and variables

The main stack stores state in the account from Step 1 and pins provider versions.

```hcl
# infra/providers.tf
terraform {
  required_version = ">= 1.9.0"

  required_providers {
    azurerm = { source = "hashicorp/azurerm", version = "~> 4.65" }
    random  = { source = "hashicorp/random", version = "~> 3.6" }
    time    = { source = "hashicorp/time", version = "~> 0.12" }
  }

  backend "azurerm" {
    resource_group_name  = "rg-<prefix>-tfstate"
    storage_account_name = "<state-storage-account>"
    container_name       = "tfstate"
    key                  = "platform.tfstate"
    use_azuread_auth     = true
  }
}

provider "azurerm" {
  subscription_id     = var.subscription_id
  storage_use_azuread = true

  features {
    key_vault {
      purge_soft_delete_on_destroy    = true
      recover_soft_deleted_key_vaults = true
    }
    resource_group {
      # App Insights can create hidden helper resources; false makes lab teardown easier.
      prevent_deletion_if_contains_resources = false
    }
  }
}
```

```hcl
# infra/variables.tf
variable "subscription_id" {
  type        = string
  description = "Target subscription. Required by azurerm 4.x."
}

variable "prefix" {
  type        = string
  description = "Short lowercase name used in all resource names."
  validation {
    condition     = can(regex("^[a-z0-9]{3,8}$", var.prefix))
    error_message = "prefix must be 3-8 lowercase letters or digits."
  }
}

variable "location" {
  type    = string
  default = "eastus2"
}

variable "environments" {
  type    = set(string)
  default = ["dev", "prod"]
}

variable "github_principal_id" {
  type        = string
  description = "Object (principal) ID of the GitHub OIDC identity from bootstrap."
}

variable "admin_object_ids" {
  type        = list(string)
  default     = []
  description = "Entra ID object IDs of humans who need cluster admin and Key Vault secret access."
}

variable "aks_vm_size" {
  type    = string
  default = "Standard_D2s_v5"
}

variable "aks_min_nodes" {
  type    = number
  default = 1
}

variable "aks_max_nodes" {
  type    = number
  default = 3
}

variable "tags" {
  type    = map(string)
  default = { project = "orders-platform", purpose = "lab" }
}
```

```hcl
# infra/terraform.tfvars  (object IDs are not secrets; subscription_id comes from TF_VAR_subscription_id)
prefix              = "<prefix>"
location            = "eastus2"
github_principal_id = "<github_principal_id from bootstrap output>"
admin_object_ids    = ["<your Entra ID user object id>"]
```

What this does:

- `~> 4.65` means "4.65 or any newer 4.x". This guide stays on 4.x; azurerm 5.x is also available, so read its upgrade guide before you move.
- azurerm 4.x requires `subscription_id` in the provider block or the `ARM_SUBSCRIPTION_ID` environment variable.
- `use_azuread_auth = true` makes the backend use Entra ID instead of storage keys. In GitHub, `ARM_USE_OIDC=true` makes it use the OIDC token.
- Commit `.terraform.lock.hcl` so CI uses the exact same provider builds you tested with.

#### Step 3: Resource group and naming

A random suffix keeps globally unique names (ACR, Key Vault, storage) from colliding.

```hcl
# infra/main.tf
data "azurerm_client_config" "current" {}

resource "random_string" "suffix" {
  length  = 4
  upper   = false
  special = false
}

locals {
  name    = "${var.prefix}-${random_string.suffix.result}"   # for names that allow dashes
  compact = "${var.prefix}${random_string.suffix.result}"    # for ACR and storage accounts

  # Kubernetes namespace and service account per environment
  namespaces      = { for env in var.environments : env => "orders-${env}" }
  service_account = "orders"
}

resource "azurerm_resource_group" "main" {
  name     = "rg-${var.prefix}-platform"
  location = var.location
  tags     = var.tags
}
```

What this does:

- `local.namespaces` maps `dev` to `orders-dev` and `prod` to `orders-prod`. The federated credentials and Helm releases both depend on these names, so they live in one place.

#### Step 4: Monitoring (Log Analytics, App Insights, Container Insights)

Create the workspace first because AKS and the Function Apps send data to it.

```hcl
# infra/monitoring.tf
resource "azurerm_log_analytics_workspace" "main" {
  name                = "log-${local.name}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  sku                 = "PerGB2018"
  retention_in_days   = 30
  daily_quota_gb      = 2 # protects your lab budget
  tags                = var.tags
}

resource "azurerm_application_insights" "functions" {
  name                = "appi-${local.name}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  workspace_id        = azurerm_log_analytics_workspace.main.id
  application_type    = "web"
  tags                = var.tags
}

# Container Insights with managed identity auth uses a data collection rule (DCR)
resource "azurerm_monitor_data_collection_rule" "container_insights" {
  name                = "MSCI-${var.location}-aks-${local.name}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location

  destinations {
    log_analytics {
      name                  = "ciworkspace"
      workspace_resource_id = azurerm_log_analytics_workspace.main.id
    }
  }

  data_flow {
    streams      = ["Microsoft-ContainerInsights-Group-Default"]
    destinations = ["ciworkspace"]
  }

  data_sources {
    extension {
      name           = "ContainerInsightsExtension"
      extension_name = "ContainerInsights"
      streams        = ["Microsoft-ContainerInsights-Group-Default"]
      extension_json = jsonencode({
        dataCollectionSettings = {
          interval               = "1m"
          namespaceFilteringMode = "Off"
          enableContainerLogV2   = true
        }
      })
    }
  }
}

resource "azurerm_monitor_data_collection_rule_association" "container_insights" {
  name                    = "ContainerInsightsExtension"
  target_resource_id      = azurerm_kubernetes_cluster.main.id
  data_collection_rule_id = azurerm_monitor_data_collection_rule.container_insights.id
}

# Control plane logs (who changed what in the cluster)
resource "azurerm_monitor_diagnostic_setting" "aks" {
  name                           = "aks-to-law"
  target_resource_id             = azurerm_kubernetes_cluster.main.id
  log_analytics_workspace_id     = azurerm_log_analytics_workspace.main.id
  log_analytics_destination_type = "Dedicated"

  enabled_log { category = "kube-audit-admin" }
  enabled_log { category = "cluster-autoscaler" }
  enabled_log { category = "guard" }
}
```

What this does:

- `daily_quota_gb` caps ingestion so a noisy pod cannot create a surprise bill.
- The DCR turns on `ContainerLogV2`, the current container log table with pod and namespace columns.
- `kube-audit-admin` records write operations against the API server without the huge volume of read events.
- `log_analytics_destination_type = "Dedicated"` writes to resource-specific tables such as `AKSAuditAdmin`.

#### Step 5: ACR and AKS

AKS is the heart of the platform. The add-ons in this block replace a lot of Helm charts you would otherwise install yourself.

```hcl
# infra/acr.tf
resource "azurerm_container_registry" "main" {
  name                = "acr${local.compact}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  sku                 = "Standard"
  admin_enabled       = false
  tags                = var.tags
}
```

```hcl
# infra/aks.tf
resource "azurerm_kubernetes_cluster" "main" {
  name                      = "aks-${local.name}"
  resource_group_name       = azurerm_resource_group.main.name
  location                  = azurerm_resource_group.main.location
  dns_prefix                = "aks-${local.name}"
  sku_tier                  = "Free" # use "Standard" (uptime SLA) for real prod
  automatic_upgrade_channel = "patch"
  node_os_upgrade_channel   = "NodeImage"

  oidc_issuer_enabled       = true
  workload_identity_enabled = true
  local_account_disabled    = true
  image_cleaner_enabled        = true
  image_cleaner_interval_hours = 48

  default_node_pool {
    name                        = "system"
    vm_size                     = var.aks_vm_size
    auto_scaling_enabled        = true
    min_count                   = var.aks_min_nodes
    max_count                   = var.aks_max_nodes
    temporary_name_for_rotation = "systemtmp"

    upgrade_settings {
      max_surge = "33%"
    }
  }

  identity {
    type = "SystemAssigned"
  }

  azure_active_directory_role_based_access_control {
    azure_rbac_enabled = true
    tenant_id          = data.azurerm_client_config.current.tenant_id
  }

  network_profile {
    network_plugin      = "azure"
    network_plugin_mode = "overlay"
    network_data_plane  = "cilium"
    network_policy      = "cilium"
    pod_cidr            = "192.168.0.0/16"
    service_cidr        = "172.16.0.0/16"
    dns_service_ip      = "172.16.0.10"
    load_balancer_sku   = "standard"
  }

  key_vault_secrets_provider {
    secret_rotation_enabled  = true
    secret_rotation_interval = "2m"
  }

  oms_agent {
    log_analytics_workspace_id      = azurerm_log_analytics_workspace.main.id
    msi_auth_for_monitoring_enabled = true
  }

  web_app_routing {
    dns_zone_ids = [] # no Azure DNS zone in this lab; use Host headers
  }

  tags = var.tags

  lifecycle {
    ignore_changes = [default_node_pool[0].node_count]
  }
}
```

What this does:

- `oidc_issuer_enabled` publishes a token issuer URL. `workload_identity_enabled` installs the webhook that injects Azure token files into pods.
- `local_account_disabled` plus `azure_rbac_enabled` means every `kubectl` call uses Entra ID and Azure role assignments. There is no shared admin kubeconfig.
- Azure CNI overlay gives pods IPs from a private range (`pod_cidr`) so you do not burn VNet addresses. Cilium handles network policy.
- `key_vault_secrets_provider` installs the Secrets Store CSI driver with the Azure provider. Rotation re-reads Key Vault every 2 minutes.
- `oms_agent` enables Container Insights. `web_app_routing` enables the managed NGINX ingress controller with the class `webapprouting.kubernetes.azure.com`.
- `ignore_changes` on `node_count` stops Terraform fighting the cluster autoscaler.

#### Step 6: Key Vault and secrets

Key Vault uses RBAC mode, so access is granted with normal Azure role assignments instead of access policies.

```hcl
# infra/keyvault.tf
resource "azurerm_key_vault" "main" {
  name                          = "kv-${local.name}"
  resource_group_name           = azurerm_resource_group.main.name
  location                      = azurerm_resource_group.main.location
  tenant_id                     = data.azurerm_client_config.current.tenant_id
  sku_name                      = "standard"
  rbac_authorization_enabled    = true  # older azurerm: enable_rbac_authorization
  soft_delete_retention_days    = 7
  purge_protection_enabled      = false # set true for real prod
  public_network_access_enabled = true  # lab only; use private endpoint in prod
  tags                          = var.tags
}

# Who can create and update secrets: the GitHub identity (Terraform in CI) and admins
resource "azurerm_role_assignment" "kv_officers" {
  for_each             = toset(concat([var.github_principal_id], var.admin_object_ids))
  scope                = azurerm_key_vault.main.id
  role_definition_name = "Key Vault Secrets Officer"
  principal_id         = each.value
}

# RBAC changes can take a minute to apply. Wait before writing secrets.
resource "time_sleep" "kv_rbac" {
  depends_on      = [azurerm_role_assignment.kv_officers]
  create_duration = "60s"
}

resource "random_password" "api_key" {
  for_each = var.environments
  length   = 32
  special  = false
}

resource "azurerm_key_vault_secret" "api_key" {
  for_each     = var.environments
  name         = "orders-api-key-${each.key}"
  value        = random_password.api_key[each.key].result
  key_vault_id = azurerm_key_vault.main.id
  content_type = "text/plain"
  depends_on   = [time_sleep.kv_rbac]

  lifecycle {
    ignore_changes = [value] # allow rotation in Key Vault without Terraform reverting it
  }
}
```

What this does:

- `rbac_authorization_enabled = true` is the azurerm 4.x name. It was added in 4.42. Older code uses `enable_rbac_authorization`, which is deprecated.
- One secret per environment, so dev pods can never read the prod key.
- `random_password` means nobody types the key. Note the value still lands in Terraform state, which is why the state account is locked down.

#### Step 7: Service Bus

One namespace with one queue per environment. Local (SAS key) auth is turned off, so only Entra ID identities can connect.

```hcl
# infra/servicebus.tf
resource "azurerm_servicebus_namespace" "main" {
  name                = "sb-${local.name}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  sku                 = "Standard"
  local_auth_enabled  = false
  minimum_tls_version = "1.2"
  tags                = var.tags
}

resource "azurerm_servicebus_queue" "orders" {
  for_each     = var.environments
  name         = "orders-${each.key}"
  namespace_id = azurerm_servicebus_namespace.main.id

  max_delivery_count                   = 5
  lock_duration                        = "PT1M"
  default_message_ttl                  = "P7D"
  dead_lettering_on_message_expiration = true
}
```

What this does:

- `local_auth_enabled = false` disables connection strings. This is the strongest way to say "no secrets".
- After 5 failed deliveries a message moves to the dead-letter queue (DLQ) instead of looping forever.

#### Step 8: Identities, federated credentials and role assignments

This file connects everything. Each environment gets its own user-assigned identity that only one Kubernetes service account can use.

```hcl
# infra/identity.tf

# ---------- Workload identity for the orders pods (one per environment) ----------
resource "azurerm_user_assigned_identity" "orders" {
  for_each            = var.environments
  name                = "id-${var.prefix}-orders-${each.key}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  tags                = var.tags
}

resource "azurerm_federated_identity_credential" "orders" {
  for_each            = var.environments
  name                      = "aks-${local.namespaces[each.key]}-${local.service_account}"
  user_assigned_identity_id = azurerm_user_assigned_identity.orders[each.key].id
  audience                  = ["api://AzureADTokenExchange"]
  issuer                    = azurerm_kubernetes_cluster.main.oidc_issuer_url
  subject                   = "system:serviceaccount:${local.namespaces[each.key]}:${local.service_account}"
}

# Read only its own secret (scope = the secret, not the whole vault)
resource "azurerm_role_assignment" "orders_kv" {
  for_each             = var.environments
  scope                = azurerm_key_vault_secret.api_key[each.key].resource_versionless_id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_user_assigned_identity.orders[each.key].principal_id
}

# Send only to its own queue
resource "azurerm_role_assignment" "orders_sb_send" {
  for_each             = var.environments
  scope                = azurerm_servicebus_queue.orders[each.key].id
  role_definition_name = "Azure Service Bus Data Sender"
  principal_id         = azurerm_user_assigned_identity.orders[each.key].principal_id
}

# ---------- Cluster identities ----------
resource "azurerm_role_assignment" "kubelet_acr_pull" {
  scope                            = azurerm_container_registry.main.id
  role_definition_name             = "AcrPull"
  principal_id                     = azurerm_kubernetes_cluster.main.kubelet_identity[0].object_id
  skip_service_principal_aad_check = true
}

# ---------- GitHub Actions identity ----------
resource "azurerm_role_assignment" "github_acr_push" {
  scope                = azurerm_container_registry.main.id
  role_definition_name = "AcrPush"
  principal_id         = var.github_principal_id
}

resource "azurerm_role_assignment" "github_aks_user" {
  scope                = azurerm_kubernetes_cluster.main.id
  role_definition_name = "Azure Kubernetes Service Cluster User Role"
  principal_id         = var.github_principal_id
}

# Lab: cluster-wide. Better: "Azure Kubernetes Service RBAC Writer" scoped to each namespace.
resource "azurerm_role_assignment" "github_aks_rbac" {
  scope                = azurerm_kubernetes_cluster.main.id
  role_definition_name = "Azure Kubernetes Service RBAC Cluster Admin"
  principal_id         = var.github_principal_id
}

# ---------- Humans ----------
resource "azurerm_role_assignment" "admins_aks" {
  for_each             = toset(var.admin_object_ids)
  scope                = azurerm_kubernetes_cluster.main.id
  role_definition_name = "Azure Kubernetes Service RBAC Cluster Admin"
  principal_id         = each.value
}
```

What this does:

- The federated credential says: "trust tokens from this AKS issuer, but only for service account `orders` in namespace `orders-dev`". Any other pod gets rejected.
- `resource_versionless_id` scopes the Key Vault role to a single secret, and it keeps working after the secret rotates to a new version.
- The kubelet identity (not the cluster identity) pulls images, so it gets `AcrPull`.
- `Cluster User Role` lets GitHub download a kubeconfig. The RBAC role controls what it can do inside Kubernetes.

#### Step 9: Function App with identity-based connections

Each environment gets a Function App with a system-assigned identity. Its host storage and its Service Bus trigger both use that identity.

```hcl
# infra/function.tf
resource "azurerm_service_plan" "functions" {
  name                = "asp-${local.name}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  os_type             = "Linux"
  sku_name            = "B1" # small dedicated plan; see Next improvements for Flex Consumption
  tags                = var.tags
}

resource "azurerm_storage_account" "functions" {
  for_each                        = var.environments
  name                            = "st${local.compact}fn${each.key}"
  resource_group_name             = azurerm_resource_group.main.name
  location                        = azurerm_resource_group.main.location
  account_tier                    = "Standard"
  account_replication_type        = "LRS"
  min_tls_version                 = "TLS1_2"
  shared_access_key_enabled       = false
  allow_nested_items_to_be_public = false
  tags                            = var.tags
}

resource "azurerm_linux_function_app" "orders" {
  for_each                      = var.environments
  name                          = "func-${local.name}-orders-${each.key}"
  resource_group_name           = azurerm_resource_group.main.name
  location                      = azurerm_resource_group.main.location
  service_plan_id               = azurerm_service_plan.functions.id
  storage_account_name          = azurerm_storage_account.functions[each.key].name
  storage_uses_managed_identity = true
  https_only                    = true
  functions_extension_version   = "~4"

  identity {
    type = "SystemAssigned"
  }

  site_config {
    always_on                              = true # needed for non-HTTP triggers on a dedicated plan
    ftps_state                             = "Disabled"
    minimum_tls_version                    = "1.2"
    application_insights_connection_string = azurerm_application_insights.functions.connection_string
    application_stack {
      python_version = "3.12"
    }
  }

  app_settings = {
    "ServiceBusConnection__fullyQualifiedNamespace" = "${azurerm_servicebus_namespace.main.name}.servicebus.windows.net"
    "ORDERS_QUEUE"                                  = azurerm_servicebus_queue.orders[each.key].name
    "SCM_DO_BUILD_DURING_DEPLOYMENT"                = "true"
    "ENABLE_ORYX_BUILD"                             = "true"
  }

  tags = var.tags
}

resource "azurerm_role_assignment" "func_storage" {
  for_each             = var.environments
  scope                = azurerm_storage_account.functions[each.key].id
  role_definition_name = "Storage Blob Data Owner"
  principal_id         = azurerm_linux_function_app.orders[each.key].identity[0].principal_id
}

resource "azurerm_role_assignment" "func_sb_receive" {
  for_each             = var.environments
  scope                = azurerm_servicebus_queue.orders[each.key].id
  role_definition_name = "Azure Service Bus Data Receiver"
  principal_id         = azurerm_linux_function_app.orders[each.key].identity[0].principal_id
}
```

What this does:

- `ServiceBusConnection__fullyQualifiedNamespace` is the identity-based connection format. The trigger uses `connection="ServiceBusConnection"` and the runtime finds the namespace from the double-underscore setting, then authenticates with the managed identity.
- `storage_uses_managed_identity = true` sets `AzureWebJobsStorage__accountName` instead of a connection string. That is why the storage account can have shared keys disabled.
- `Storage Blob Data Owner` is what the Functions host needs for its own blob containers (leases, keys, deployment).
- The SCM and Oryx settings match what the deploy action sets, so Terraform does not show drift after each deployment.

#### Step 10: Outputs and first apply

Outputs feed the GitHub variables that the app workflows use.

```hcl
# infra/outputs.tf
output "resource_group" { value = azurerm_resource_group.main.name }
output "aks_name" { value = azurerm_kubernetes_cluster.main.name }
output "acr_name" { value = azurerm_container_registry.main.name }
output "acr_login_server" { value = azurerm_container_registry.main.login_server }
output "key_vault_name" { value = azurerm_key_vault.main.name }
output "tenant_id" { value = data.azurerm_client_config.current.tenant_id }
output "servicebus_fqdn" { value = "${azurerm_servicebus_namespace.main.name}.servicebus.windows.net" }
output "log_analytics_workspace_id" { value = azurerm_log_analytics_workspace.main.workspace_id }

output "workload_client_ids" {
  value = { for env, id in azurerm_user_assigned_identity.orders : env => id.client_id }
}

output "function_app_names" {
  value = { for env, app in azurerm_linux_function_app.orders : env => app.name }
}
```

```bash
cd infra
export TF_VAR_subscription_id="<subscription-id>"
terraform init
terraform fmt -recursive
terraform validate
terraform plan -out tfplan
terraform apply tfplan        # about 10-15 minutes, mostly AKS

# Connect with your own Entra ID account
az aks get-credentials -g "$(terraform output -raw resource_group)" -n "$(terraform output -raw aks_name)"
kubelogin convert-kubeconfig -l azurecli
kubectl get nodes
kubectl get pods -n kube-system | grep -E "secrets-store|ama-logs|azure-wi"
kubectl get pods -n app-routing-system
```

What this does:

- The first apply runs from your laptop. After that, `infra.yml` takes over for every change.
- `kubelogin convert-kubeconfig -l azurecli` tells kubectl to reuse your `az login` token.
- The last two commands prove that the CSI driver, monitoring agent, workload identity webhook and ingress controller are running.

#### Step 11: The orders service (FastAPI)

The API checks an API key, then publishes the order to Service Bus and returns `202 Accepted` right away. The slow work happens later in the Function.

```text
# services/orders/requirements.txt
fastapi==0.115.6
uvicorn[standard]==0.32.1
azure-identity==1.19.0
azure-servicebus==7.13.0
```

```python
# services/orders/app/main.py
import json
import logging
import os
import secrets
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from azure.identity import DefaultAzureCredential
from azure.servicebus import ServiceBusClient, ServiceBusMessage
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format='{"time":"%(asctime)s","level":"%(levelname)s","msg":"%(message)s"}',
)
log = logging.getLogger("orders")

SERVICEBUS_FQDN = os.environ["SERVICEBUS_FQDN"]          # e.g. sb-xyz.servicebus.windows.net
ORDERS_QUEUE = os.environ["ORDERS_QUEUE"]                # orders-dev or orders-prod
API_KEY_FILE = Path(os.getenv("API_KEY_FILE", "/mnt/secrets-store/api-key"))

# In AKS, DefaultAzureCredential picks WorkloadIdentityCredential, using
# AZURE_CLIENT_ID, AZURE_TENANT_ID and AZURE_FEDERATED_TOKEN_FILE injected by the webhook.
credential = DefaultAzureCredential()
sb_client = ServiceBusClient(fully_qualified_namespace=SERVICEBUS_FQDN, credential=credential)


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield
    sb_client.close()
    credential.close()


app = FastAPI(title="orders", lifespan=lifespan)


class OrderIn(BaseModel):
    customer_id: str = Field(min_length=1, max_length=64)
    sku: str = Field(min_length=1, max_length=64)
    quantity: int = Field(gt=0, le=1000)


def expected_api_key() -> str:
    # Read on every call so a rotated secret (CSI rotation) is picked up without a restart.
    if API_KEY_FILE.exists():
        return API_KEY_FILE.read_text().strip()
    return os.getenv("API_KEY", "")


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.get("/readyz")
def readyz():
    if not expected_api_key():
        raise HTTPException(status_code=503, detail="secret not mounted yet")
    return {"status": "ready"}


@app.post("/orders", status_code=202)
def create_order(order: OrderIn, x_api_key: str | None = Header(default=None)):
    key = expected_api_key()
    if not key or not secrets.compare_digest(x_api_key or "", key):
        raise HTTPException(status_code=401, detail="invalid api key")

    order_id = str(uuid.uuid4())
    payload = {
        "order_id": order_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        **order.model_dump(),
    }
    message = ServiceBusMessage(
        json.dumps(payload),
        content_type="application/json",
        message_id=order_id,  # lets Service Bus duplicate detection or the consumer de-duplicate
        application_properties={"event_type": "OrderCreated"},
    )
    with sb_client.get_queue_sender(queue_name=ORDERS_QUEUE) as sender:
        sender.send_messages(message)

    log.info("order accepted order_id=%s queue=%s", order_id, ORDERS_QUEUE)
    return {"order_id": order_id, "status": "accepted"}
```

```python
# services/orders/app/__init__.py
```

What this does:

- There is no connection string. `DefaultAzureCredential` exchanges the projected Kubernetes token for an Entra ID token at runtime.
- `secrets.compare_digest` compares keys in constant time, which avoids timing attacks.
- The endpoints are plain `def`, so FastAPI runs them in a thread pool and the blocking Service Bus call does not freeze the event loop.
- `/readyz` fails until the CSI volume is mounted, so Kubernetes does not send traffic to a pod that cannot authenticate callers.

#### Step 12: Dockerfile and local check

A two-stage build keeps compilers out of the final image. The app runs as a non-root user.

```dockerfile
# syntax=docker/dockerfile:1
# services/orders/Dockerfile
FROM python:3.12-slim AS build
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
RUN apt-get update && apt-get upgrade -y && rm -rf /var/lib/apt/lists/* \
    && useradd --uid 10001 --no-create-home --shell /usr/sbin/nologin appuser
WORKDIR /app
COPY --from=build /install /usr/local
COPY app/ ./app/
USER 10001
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```text
# services/orders/.dockerignore
__pycache__/
*.pyc
.venv/
tests/
```

```bash
cd services/orders
docker build -t orders:local .
echo "local-test-key" > /tmp/api-key
docker run --rm -p 8000:8000 \
  -e SERVICEBUS_FQDN=example.servicebus.windows.net -e ORDERS_QUEUE=orders-dev \
  -e API_KEY_FILE=/secrets/api-key -v /tmp/api-key:/secrets/api-key:ro \
  orders:local
# In another terminal
curl -s localhost:8000/healthz
curl -s localhost:8000/readyz
```

What this does:

- `apt-get upgrade` pulls the latest Debian security patches, which reduces Trivy findings.
- `USER 10001` matches `runAsNonRoot` in the pod spec. Kubernetes can check a numeric user ID, but not a user name.
- The local run only checks health. Sending to Service Bus needs an Azure identity, so you test that in AKS.

#### Step 13: Generic Helm chart

The chart is generic: any small HTTP service can reuse it by changing values. The per-environment differences live only in values files.

```yaml
# helm/app/Chart.yaml
apiVersion: v2
name: app
description: Generic chart for an HTTP microservice on AKS
type: application
version: 0.1.0
appVersion: "1.0.0"
```

```yaml
# helm/app/values.yaml
replicaCount: 1

image:
  repository: ""        # set by CI, e.g. acrxyz.azurecr.io/orders
  tag: ""               # set by CI, the git SHA
  pullPolicy: IfNotPresent

containerPort: 8000

serviceAccount:
  name: orders          # must match the federated credential subject
  clientId: ""          # user-assigned identity client ID, set by CI

env:
  LOG_LEVEL: INFO
  # SERVICEBUS_FQDN and ORDERS_QUEUE are set per environment

keyVault:
  enabled: true
  name: ""              # set by CI
  tenantId: ""          # set by CI
  mountPath: /mnt/secrets-store
  secrets: []           # list of {name, alias}

service:
  port: 80

ingress:
  enabled: true
  className: webapprouting.kubernetes.azure.com
  host: ""

resources:
  requests:
    cpu: 100m
    memory: 128Mi
  limits:
    memory: 256Mi

autoscaling:
  enabled: false
  minReplicas: 2
  maxReplicas: 5
  targetCPUUtilizationPercentage: 70

podDisruptionBudget:
  enabled: false
  minAvailable: 1
```

```yaml
# helm/app/values-dev.yaml
replicaCount: 1
env:
  LOG_LEVEL: DEBUG
  ORDERS_QUEUE: orders-dev
keyVault:
  secrets:
    - name: orders-api-key-dev
      alias: api-key
ingress:
  host: orders-dev.example.internal
```

```yaml
# helm/app/values-prod.yaml
env:
  LOG_LEVEL: INFO
  ORDERS_QUEUE: orders-prod
keyVault:
  secrets:
    - name: orders-api-key-prod
      alias: api-key
ingress:
  host: orders.example.internal
resources:
  requests:
    cpu: 250m
    memory: 256Mi
  limits:
    memory: 512Mi
autoscaling:
  enabled: true
  minReplicas: 2
  maxReplicas: 6
  targetCPUUtilizationPercentage: 70
podDisruptionBudget:
  enabled: true
  minAvailable: 1
```

```yaml
# helm/app/templates/_helpers.tpl
{{- define "app.fullname" -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "app.selectorLabels" -}}
app.kubernetes.io/name: {{ .Chart.Name }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{- define "app.labels" -}}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version | replace "+" "_" }}
{{ include "app.selectorLabels" . }}
app.kubernetes.io/version: {{ .Values.image.tag | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}
```

```yaml
# helm/app/templates/serviceaccount.yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: {{ .Values.serviceAccount.name }}
  labels:
    {{- include "app.labels" . | nindent 4 }}
  annotations:
    azure.workload.identity/client-id: {{ required "serviceAccount.clientId is required" .Values.serviceAccount.clientId | quote }}
```

```yaml
# helm/app/templates/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ include "app.fullname" . }}
  labels:
    {{- include "app.labels" . | nindent 4 }}
spec:
  {{- if not .Values.autoscaling.enabled }}
  replicas: {{ .Values.replicaCount }}
  {{- end }}
  revisionHistoryLimit: 5
  selector:
    matchLabels:
      {{- include "app.selectorLabels" . | nindent 6 }}
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  template:
    metadata:
      labels:
        {{- include "app.selectorLabels" . | nindent 8 }}
        azure.workload.identity/use: "true"
    spec:
      serviceAccountName: {{ .Values.serviceAccount.name }}
      securityContext:
        runAsNonRoot: true
        seccompProfile:
          type: RuntimeDefault
      containers:
        - name: {{ .Release.Name }}
          image: "{{ required "image.repository is required" .Values.image.repository }}:{{ required "image.tag is required" .Values.image.tag }}"
          imagePullPolicy: {{ .Values.image.pullPolicy }}
          ports:
            - name: http
              containerPort: {{ .Values.containerPort }}
          env:
            {{- range $key, $value := .Values.env }}
            - name: {{ $key }}
              value: {{ $value | quote }}
            {{- end }}
            {{- if .Values.keyVault.enabled }}
            - name: API_KEY_FILE
              value: "{{ .Values.keyVault.mountPath }}/api-key"
            {{- end }}
          readinessProbe:
            httpGet:
              path: /readyz
              port: http
            periodSeconds: 5
          livenessProbe:
            httpGet:
              path: /healthz
              port: http
            initialDelaySeconds: 10
            periodSeconds: 15
          resources:
            {{- toYaml .Values.resources | nindent 12 }}
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            capabilities:
              drop: ["ALL"]
          volumeMounts:
            - name: tmp
              mountPath: /tmp
            {{- if .Values.keyVault.enabled }}
            - name: secrets-store
              mountPath: {{ .Values.keyVault.mountPath }}
              readOnly: true
            {{- end }}
      volumes:
        - name: tmp
          emptyDir: {}
        {{- if .Values.keyVault.enabled }}
        - name: secrets-store
          csi:
            driver: secrets-store.csi.k8s.io
            readOnly: true
            volumeAttributes:
              secretProviderClass: {{ include "app.fullname" . }}-kv
        {{- end }}
```

```yaml
# helm/app/templates/secretproviderclass.yaml
{{- if .Values.keyVault.enabled }}
apiVersion: secrets-store.csi.x-k8s.io/v1
kind: SecretProviderClass
metadata:
  name: {{ include "app.fullname" . }}-kv
  labels:
    {{- include "app.labels" . | nindent 4 }}
spec:
  provider: azure
  parameters:
    usePodIdentity: "false"
    clientID: {{ .Values.serviceAccount.clientId | quote }}
    keyvaultName: {{ required "keyVault.name is required" .Values.keyVault.name | quote }}
    tenantId: {{ required "keyVault.tenantId is required" .Values.keyVault.tenantId | quote }}
    objects: |
      array:
      {{- range .Values.keyVault.secrets }}
        - |
          objectName: {{ .name }}
          objectType: secret
          objectAlias: {{ .alias }}
      {{- end }}
{{- end }}
```

```yaml
# helm/app/templates/service.yaml
apiVersion: v1
kind: Service
metadata:
  name: {{ include "app.fullname" . }}
  labels:
    {{- include "app.labels" . | nindent 4 }}
spec:
  type: ClusterIP
  selector:
    {{- include "app.selectorLabels" . | nindent 4 }}
  ports:
    - name: http
      port: {{ .Values.service.port }}
      targetPort: http
```

```yaml
# helm/app/templates/ingress.yaml
{{- if .Values.ingress.enabled }}
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: {{ include "app.fullname" . }}
  labels:
    {{- include "app.labels" . | nindent 4 }}
spec:
  ingressClassName: {{ .Values.ingress.className }}
  rules:
    - host: {{ required "ingress.host is required" .Values.ingress.host | quote }}
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: {{ include "app.fullname" . }}
                port:
                  number: {{ .Values.service.port }}
{{- end }}
```

```yaml
# helm/app/templates/hpa.yaml
{{- if .Values.autoscaling.enabled }}
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: {{ include "app.fullname" . }}
  labels:
    {{- include "app.labels" . | nindent 4 }}
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: {{ include "app.fullname" . }}
  minReplicas: {{ .Values.autoscaling.minReplicas }}
  maxReplicas: {{ .Values.autoscaling.maxReplicas }}
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: {{ .Values.autoscaling.targetCPUUtilizationPercentage }}
{{- end }}
```

```yaml
# helm/app/templates/pdb.yaml
{{- if .Values.podDisruptionBudget.enabled }}
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: {{ include "app.fullname" . }}
  labels:
    {{- include "app.labels" . | nindent 4 }}
spec:
  minAvailable: {{ .Values.podDisruptionBudget.minAvailable }}
  selector:
    matchLabels:
      {{- include "app.selectorLabels" . | nindent 6 }}
{{- end }}
```

```bash
# Render locally to catch template errors before CI
helm lint helm/app -f helm/app/values-dev.yaml \
  --set image.repository=acr.example/orders --set image.tag=test \
  --set serviceAccount.clientId=00000000-0000-0000-0000-000000000000 \
  --set keyVault.name=kv-test --set keyVault.tenantId=00000000-0000-0000-0000-000000000000
helm template orders helm/app -f helm/app/values-prod.yaml \
  --set image.repository=acr.example/orders --set image.tag=test \
  --set serviceAccount.clientId=x --set keyVault.name=x --set keyVault.tenantId=x | less
```

What this does:

- The service account annotation `azure.workload.identity/client-id` tells the webhook which identity to use. The pod label `azure.workload.identity/use: "true"` tells it to inject the token volume and `AZURE_*` variables.
- The SecretProviderClass uses `clientID` (workload identity mode). The CSI driver gets a token for the pod's service account and reads only the listed secrets.
- `objectAlias: api-key` makes the file name stable (`/mnt/secrets-store/api-key`) across environments, even though the Key Vault secret names differ.
- `required` makes Helm fail early with a clear message instead of deploying a broken pod.
- `maxUnavailable: 0` plus the readiness probe gives zero-downtime rollouts. The PDB keeps at least one prod pod during node upgrades.
- When the HPA is on, `replicas` is left out of the Deployment so Helm does not reset the scale on every upgrade.

#### Step 14: The Function App (Python v2 model)

The function triggers on each queue message. The queue name comes from an app setting, so the same code works for dev and prod.

```python
# functions/order-processor/function_app.py
import json
import logging

import azure.functions as func

app = func.FunctionApp()


@app.service_bus_queue_trigger(
    arg_name="msg",
    queue_name="%ORDERS_QUEUE%",          # resolved from the app setting
    connection="ServiceBusConnection",    # uses ServiceBusConnection__fullyQualifiedNamespace
)
def process_order(msg: func.ServiceBusMessage) -> None:
    order = json.loads(msg.get_body().decode("utf-8"))
    logging.info(
        "Processing order %s sku=%s qty=%s message_id=%s delivery_count=%s",
        order.get("order_id"), order.get("sku"), order.get("quantity"),
        msg.message_id, msg.delivery_count,
    )

    if order.get("quantity", 0) <= 0:
        # Raising makes the runtime abandon the message; after max_delivery_count it goes to the DLQ.
        raise ValueError(f"invalid quantity for order {order.get('order_id')}")

    # Real work goes here: reserve stock, write to a database, send an email, etc.
    # Make it idempotent: the same message can be delivered more than once.
    logging.info("Order %s processed", order.get("order_id"))
```

```json
{
  "version": "2.0",
  "logging": {
    "applicationInsights": {
      "samplingSettings": { "isEnabled": true, "excludedTypes": "Request" }
    }
  },
  "extensionBundle": {
    "id": "Microsoft.Azure.Functions.ExtensionBundle",
    "version": "[4.*, 5.0.0)"
  },
  "extensions": {
    "serviceBus": {
      "maxConcurrentCalls": 8,
      "autoCompleteMessages": true
    }
  }
}
```

```text
# functions/order-processor/requirements.txt
azure-functions
```

What this does:

- `%ORDERS_QUEUE%` is a binding expression that reads an app setting. Terraform sets it to `orders-dev` or `orders-prod`.
- `connection="ServiceBusConnection"` plus the `__fullyQualifiedNamespace` app setting gives a passwordless trigger using the Function's managed identity.
- The host.json file above is `functions/order-processor/host.json`. Extension bundle 4.x includes the Service Bus extension that supports identity-based connections.
- With `autoCompleteMessages`, a successful run completes the message. An exception abandons it and Service Bus redelivers it.

#### Step 15: Configure GitHub environments and variables

Workflows read non-secret settings from GitHub variables. Nothing here is a secret, because OIDC replaces client secrets.

```bash
REPO="<owner>/<repo>"
cd infra

# Environments: dev (no approval), prod and infra (add required reviewers in the UI)
for env in dev prod infra; do
  gh api -X PUT "repos/$REPO/environments/$env" >/dev/null
done

# Repository-level variables
gh variable set AZURE_CLIENT_ID       -R "$REPO" --body "<github_client_id from bootstrap>"
gh variable set AZURE_TENANT_ID       -R "$REPO" --body "$(terraform output -raw tenant_id)"
gh variable set AZURE_SUBSCRIPTION_ID -R "$REPO" --body "<subscription-id>"
gh variable set ACR_NAME              -R "$REPO" --body "$(terraform output -raw acr_name)"
gh variable set AKS_NAME              -R "$REPO" --body "$(terraform output -raw aks_name)"
gh variable set AKS_RESOURCE_GROUP    -R "$REPO" --body "$(terraform output -raw resource_group)"
gh variable set KEYVAULT_NAME         -R "$REPO" --body "$(terraform output -raw key_vault_name)"
gh variable set SERVICEBUS_FQDN       -R "$REPO" --body "$(terraform output -raw servicebus_fqdn)"

# Environment-level variables (different per environment)
for env in dev prod; do
  gh variable set WORKLOAD_CLIENT_ID -R "$REPO" --env "$env" \
    --body "$(terraform output -json workload_client_ids | jq -r ".$env")"
  gh variable set FUNCTION_APP_NAME -R "$REPO" --env "$env" \
    --body "$(terraform output -json function_app_names | jq -r ".$env")"
done
```

What this does:

- In GitHub, open Settings, Environments, `prod` and `infra`, and add **Required reviewers**. Also limit deployment branches to `main`.
- When a job uses `environment: dev`, `vars.WORKLOAD_CLIENT_ID` resolves to the dev value. The same workflow code works for both environments.
- The OIDC token subject for that job becomes `repo:<owner>/<repo>:environment:dev`, which matches a federated credential from Step 1.

#### Step 16: Infrastructure workflow (plan on PR, apply on main)

PRs show a plan. Merges to `main` create a plan and apply exactly that plan after an approval.

```yaml
# .github/workflows/infra.yml
name: infra

on:
  pull_request:
    paths: ["infra/**", ".github/workflows/infra.yml"]
  push:
    branches: [main]
    paths: ["infra/**", ".github/workflows/infra.yml"]

permissions:
  id-token: write
  contents: read

concurrency:
  group: terraform-platform
  cancel-in-progress: false

env:
  ARM_CLIENT_ID: ${{ vars.AZURE_CLIENT_ID }}
  ARM_TENANT_ID: ${{ vars.AZURE_TENANT_ID }}
  ARM_SUBSCRIPTION_ID: ${{ vars.AZURE_SUBSCRIPTION_ID }}
  ARM_USE_OIDC: "true"
  TF_VAR_subscription_id: ${{ vars.AZURE_SUBSCRIPTION_ID }}
  TF_IN_AUTOMATION: "true"

defaults:
  run:
    working-directory: infra

jobs:
  plan:
    name: Terraform plan
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: hashicorp/setup-terraform@v3
        with:
          terraform_version: 1.9.8
          terraform_wrapper: false

      - name: Format check
        run: terraform fmt -check -recursive

      - name: Init
        run: terraform init -input=false

      - name: Validate
        run: terraform validate

      - name: Plan
        run: |
          terraform plan -input=false -lock-timeout=5m -out=tfplan
          terraform show -no-color tfplan > plan.txt
          {
            echo '### Terraform plan'
            echo '```text'
            tail -c 60000 plan.txt
            echo '```'
          } >> "$GITHUB_STEP_SUMMARY"

      - name: Upload plan
        if: github.event_name == 'push'
        uses: actions/upload-artifact@v4
        with:
          name: tfplan
          path: infra/tfplan
          retention-days: 1

  apply:
    name: Terraform apply
    needs: plan
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    environment: infra
    steps:
      - uses: actions/checkout@v4

      - uses: hashicorp/setup-terraform@v3
        with:
          terraform_version: 1.9.8
          terraform_wrapper: false

      - uses: actions/download-artifact@v4
        with:
          name: tfplan
          path: infra

      - name: Init
        run: terraform init -input=false

      - name: Apply saved plan
        run: terraform apply -input=false -lock-timeout=5m tfplan
```

What this does:

- `id-token: write` lets the job request a GitHub OIDC token. The azurerm provider and backend exchange it for an Azure token because `ARM_USE_OIDC=true`.
- The PR job runs as subject `pull_request`, the push plan as `ref:refs/heads/main`, and apply as `environment:infra`. All three match federated credentials.
- Applying the saved `tfplan` means you apply exactly what the reviewer approved. If state changed in between, Terraform refuses the stale plan.
- `concurrency` stops two applies from running at once. The blob lease lock is a second safety net.
- The plan file can contain sensitive values, so it is kept for one day only.

#### Step 17: Application CI/CD workflow

One workflow builds once, scans, pushes, then promotes the same image to dev and then prod.

```yaml
# .github/workflows/ci-cd.yml
name: ci-cd

on:
  pull_request:
    paths: ["services/orders/**", "helm/app/**", ".github/workflows/ci-cd.yml"]
  push:
    branches: [main]
    paths: ["services/orders/**", "helm/app/**", ".github/workflows/ci-cd.yml"]
  workflow_dispatch:

permissions:
  id-token: write
  contents: read

env:
  IMAGE: ${{ vars.ACR_NAME }}.azurecr.io/orders
  CHART: helm/app

jobs:
  build:
    name: Build, scan, push
    runs-on: ubuntu-latest
    outputs:
      tag: ${{ steps.meta.outputs.tag }}
    steps:
      - uses: actions/checkout@v4

      - name: Compute image tag
        id: meta
        run: echo "tag=${GITHUB_SHA::12}" >> "$GITHUB_OUTPUT"

      - name: Build image
        run: docker build -t "$IMAGE:${{ steps.meta.outputs.tag }}" services/orders

      - name: Scan image with Trivy (fail on CRITICAL/HIGH)
        # Pinned to the commit SHA of release v0.36.0. Tags can be moved; SHAs cannot.
        uses: aquasecurity/trivy-action@ed142fd0673e97e23eac54620cfb913e5ce36c25 # v0.36.0
        with:
          image-ref: ${{ env.IMAGE }}:${{ steps.meta.outputs.tag }}
          format: table
          exit-code: "1"
          ignore-unfixed: true
          vuln-type: os,library
          severity: CRITICAL,HIGH

      - uses: azure/setup-helm@v4
        with:
          version: v3.19.0

      - name: Lint chart
        run: |
          for env in dev prod; do
            helm lint "$CHART" -f "$CHART/values-$env.yaml" \
              --set image.repository=x --set image.tag=x \
              --set serviceAccount.clientId=x --set keyVault.name=x --set keyVault.tenantId=x
          done

      - name: Azure login (OIDC)
        if: github.event_name != 'pull_request'
        uses: azure/login@v2
        with:
          client-id: ${{ vars.AZURE_CLIENT_ID }}
          tenant-id: ${{ vars.AZURE_TENANT_ID }}
          subscription-id: ${{ vars.AZURE_SUBSCRIPTION_ID }}

      - name: Push image to ACR
        if: github.event_name != 'pull_request'
        run: |
          az acr login --name "${{ vars.ACR_NAME }}"
          docker push "$IMAGE:${{ steps.meta.outputs.tag }}"

  deploy-dev:
    name: Deploy to dev
    needs: build
    if: github.event_name != 'pull_request' && github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    environment: dev
    env:
      NAMESPACE: orders-dev
    steps:
      - uses: actions/checkout@v4

      - uses: azure/login@v2
        with:
          client-id: ${{ vars.AZURE_CLIENT_ID }}
          tenant-id: ${{ vars.AZURE_TENANT_ID }}
          subscription-id: ${{ vars.AZURE_SUBSCRIPTION_ID }}

      - uses: azure/setup-helm@v4
        with:
          version: v3.19.0

      - uses: azure/use-kubelogin@v1
        with:
          kubelogin-version: v0.1.6

      - uses: azure/aks-set-context@v4
        with:
          resource-group: ${{ vars.AKS_RESOURCE_GROUP }}
          cluster-name: ${{ vars.AKS_NAME }}
          use-kubelogin: "true"

      - name: Helm upgrade (atomic)
        run: |
          helm upgrade --install orders "$CHART" \
            --namespace "$NAMESPACE" --create-namespace \
            -f "$CHART/values-dev.yaml" \
            --set image.repository="$IMAGE" \
            --set image.tag="${{ needs.build.outputs.tag }}" \
            --set serviceAccount.clientId="${{ vars.WORKLOAD_CLIENT_ID }}" \
            --set keyVault.name="${{ vars.KEYVAULT_NAME }}" \
            --set keyVault.tenantId="${{ vars.AZURE_TENANT_ID }}" \
            --set env.SERVICEBUS_FQDN="${{ vars.SERVICEBUS_FQDN }}" \
            --atomic --wait --timeout 5m

      - name: Smoke test
        run: |
          kubectl -n "$NAMESPACE" rollout status deploy/orders --timeout=2m
          kubectl -n "$NAMESPACE" run smoke-${{ github.run_id }} --rm -i --restart=Never \
            --image=curlimages/curl:8.10.1 -- curl -fsS http://orders/readyz

  deploy-prod:
    name: Deploy to prod
    needs: [build, deploy-dev]
    runs-on: ubuntu-latest
    environment: prod   # required reviewers pause the job here
    env:
      NAMESPACE: orders-prod
    steps:
      - uses: actions/checkout@v4

      - uses: azure/login@v2
        with:
          client-id: ${{ vars.AZURE_CLIENT_ID }}
          tenant-id: ${{ vars.AZURE_TENANT_ID }}
          subscription-id: ${{ vars.AZURE_SUBSCRIPTION_ID }}

      - uses: azure/setup-helm@v4
        with:
          version: v3.19.0

      - uses: azure/use-kubelogin@v1
        with:
          kubelogin-version: v0.1.6

      - uses: azure/aks-set-context@v4
        with:
          resource-group: ${{ vars.AKS_RESOURCE_GROUP }}
          cluster-name: ${{ vars.AKS_NAME }}
          use-kubelogin: "true"

      - name: Helm upgrade (atomic)
        run: |
          helm upgrade --install orders "$CHART" \
            --namespace "$NAMESPACE" --create-namespace \
            -f "$CHART/values-prod.yaml" \
            --set image.repository="$IMAGE" \
            --set image.tag="${{ needs.build.outputs.tag }}" \
            --set serviceAccount.clientId="${{ vars.WORKLOAD_CLIENT_ID }}" \
            --set keyVault.name="${{ vars.KEYVAULT_NAME }}" \
            --set keyVault.tenantId="${{ vars.AZURE_TENANT_ID }}" \
            --set env.SERVICEBUS_FQDN="${{ vars.SERVICEBUS_FQDN }}" \
            --atomic --wait --timeout 5m

      - name: Verify rollout
        run: kubectl -n "$NAMESPACE" rollout status deploy/orders --timeout=2m
```

What this does:

- PRs only build, scan and lint. They never log in to Azure or deploy, so untrusted code cannot reach your cluster.
- Trivy with `exit-code: "1"` and `severity: CRITICAL,HIGH` breaks the build before the image reaches ACR. `ignore-unfixed` skips CVEs that have no patch yet, so the gate stays actionable.
- The Trivy action is pinned to a full commit SHA. In 2026 the trivy-action project went through a supply-chain incident and re-published its release tags with a `v` prefix, so older references such as `@0.28.0` no longer resolve. Pinning third-party actions by SHA (and updating them with Dependabot) protects you from moved or hijacked tags.
- The image is built once and tagged with the commit SHA. Prod deploys the exact same tag that passed dev. No rebuild, no `latest`.
- `--atomic` waits for the rollout and rolls back automatically if pods do not become ready in 5 minutes. Note: Helm 4 renames this flag to `--rollback-on-failure`, which is why the Helm version is pinned to 3.x here.
- `use-kubelogin` is required because the cluster has local accounts disabled and uses Entra ID for every API call.

#### Step 18: Functions deployment workflow

The Function code has its own pipeline because it changes on a different schedule from the API.

```yaml
# .github/workflows/functions.yml
name: functions

on:
  push:
    branches: [main]
    paths: ["functions/order-processor/**", ".github/workflows/functions.yml"]
  pull_request:
    paths: ["functions/order-processor/**", ".github/workflows/functions.yml"]
  workflow_dispatch:

permissions:
  id-token: write
  contents: read

env:
  FUNC_PATH: functions/order-processor

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Install and compile
        run: |
          pip install -r "$FUNC_PATH/requirements.txt"
          python -m py_compile "$FUNC_PATH/function_app.py"

  deploy-dev:
    needs: test
    if: github.event_name != 'pull_request' && github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    environment: dev
    steps:
      - uses: actions/checkout@v4
      - uses: azure/login@v2
        with:
          client-id: ${{ vars.AZURE_CLIENT_ID }}
          tenant-id: ${{ vars.AZURE_TENANT_ID }}
          subscription-id: ${{ vars.AZURE_SUBSCRIPTION_ID }}
      - uses: Azure/functions-action@v1
        with:
          app-name: ${{ vars.FUNCTION_APP_NAME }}
          package: ${{ env.FUNC_PATH }}
          scm-do-build-during-deployment: true
          enable-oryx-build: true

  deploy-prod:
    needs: deploy-dev
    runs-on: ubuntu-latest
    environment: prod
    steps:
      - uses: actions/checkout@v4
      - uses: azure/login@v2
        with:
          client-id: ${{ vars.AZURE_CLIENT_ID }}
          tenant-id: ${{ vars.AZURE_TENANT_ID }}
          subscription-id: ${{ vars.AZURE_SUBSCRIPTION_ID }}
      - uses: Azure/functions-action@v1
        with:
          app-name: ${{ vars.FUNCTION_APP_NAME }}
          package: ${{ env.FUNC_PATH }}
          scm-do-build-during-deployment: true
          enable-oryx-build: true
```

What this does:

- `azure/login@v2` with OIDC means no publish profile is stored in GitHub. The action deploys using the logged-in identity.
- `scm-do-build-during-deployment` and `enable-oryx-build` make Azure install `requirements.txt` on Linux, so native packages match the Function host.
- The same `environment` approvals from Step 15 also gate the Function deployment to prod.

#### Step 19: Observe the platform with KQL

All logs go to one Log Analytics workspace. Open it in the portal, choose **Logs**, and run these queries.

```kusto
// Orders API logs in dev, newest first
ContainerLogV2
| where TimeGenerated > ago(30m)
| where PodNamespace == "orders-dev" and ContainerName == "orders"
| project TimeGenerated, PodName, LogLevel, LogMessage
| order by TimeGenerated desc
```

```kusto
// Pods that restarted in the orders namespaces
KubePodInventory
| where TimeGenerated > ago(1h)
| where Namespace startswith "orders-"
| summarize Restarts = max(ContainerRestartCount) by Namespace, Name
| where Restarts > 0
| order by Restarts desc
```

```kusto
// Kubernetes warning events (failed mounts, image pulls, probe failures)
KubeEvents
| where TimeGenerated > ago(1h)
| where Namespace startswith "orders-" and KubeEventType == "Warning"
| project TimeGenerated, Namespace, Name, Reason, Message
| order by TimeGenerated desc
```

```kusto
// CPU per orders container, in millicores
Perf
| where TimeGenerated > ago(1h)
| where ObjectName == "K8SContainer" and CounterName == "cpuUsageNanoCores"
| where InstanceName endswith "/orders"
| summarize AvgMilliCores = avg(CounterValue) / 1000000 by bin(TimeGenerated, 5m), Computer
| render timechart
```

```kusto
// Function processing logs (workspace-based Application Insights)
AppTraces
| where TimeGenerated > ago(1h)
| where AppRoleName startswith "func-"
| where Message has "Processing order" or Message has "processed"
| project TimeGenerated, AppRoleName, Message
| order by TimeGenerated desc
```

```kusto
// Function failures per 5 minutes
AppRequests
| where TimeGenerated > ago(24h)
| where AppRoleName startswith "func-" and Success == false
| summarize Failures = count() by bin(TimeGenerated, 5m), AppRoleName, OperationName
```

```kusto
// Who changed what in the cluster (control plane audit)
AKSAuditAdmin
| where TimeGenerated > ago(24h)
| where ObjectRef has "orders"
| project TimeGenerated, User = tostring(User.username), Verb, ObjectRef
| order by TimeGenerated desc
```

What this does:

- `ContainerLogV2`, `KubePodInventory`, `KubeEvents` and `Perf` come from Container Insights. `AppTraces` and `AppRequests` come from the workspace-based App Insights. `AKSAuditAdmin` comes from the diagnostic setting.
- Turn the restart and Function failure queries into log search alert rules with an action group (email or Teams) as a next step.
- Check queue health from the CLI: `az servicebus queue show -g <rg> --namespace-name <sb> -n orders-dev --query countDetails`.

#### Step 20: GitOps alternative (optional)

In this lab GitHub Actions runs `helm upgrade` against the cluster (push model). Many teams switch to GitOps (pull model):

- Install Flux with the AKS GitOps extension (`az k8s-configuration flux create ...`) or install Argo CD.
- CI still builds, scans and pushes the image. Instead of running Helm, it commits the new image tag to a config repo (or `values-dev.yaml`).
- Flux or Argo CD watches the repo and applies the Helm release from inside the cluster. Prod promotion becomes a pull request that changes the prod tag.
- Benefits: the cluster API does not need to trust GitHub, Git is the single source of truth, and drift is corrected automatically. The cost: one more system to run and learn.

### End-to-end request walkthrough

1. A client sends `POST /orders` with header `Host: orders-dev.example.internal` and `x-api-key` to the public IP of the app routing load balancer.
2. The managed NGINX ingress controller in `app-routing-system` matches the host and forwards to the `orders` Service in `orders-dev`.
3. A ready `orders` pod receives the request. Readiness passed earlier because the CSI driver mounted `/mnt/secrets-store/api-key`.
4. The CSI driver had used the pod's service account token, exchanged through the AKS OIDC issuer and the federated credential, to read `orders-api-key-dev` from Key Vault (role: Key Vault Secrets User on that secret).
5. The API compares the header with the file content. If they do not match it returns 401.
6. `DefaultAzureCredential` reads `AZURE_FEDERATED_TOKEN_FILE`, sends it to Entra ID, and gets an access token for Service Bus as `id-<prefix>-orders-dev`.
7. The API sends a JSON message to queue `orders-dev` (role: Azure Service Bus Data Sender on that queue) and returns `202 Accepted` with an `order_id`.
8. The dev Function App, which holds a lock on the queue through its managed identity (role: Azure Service Bus Data Receiver), receives the message within seconds.
9. `process_order` logs and handles the order. On success the message is completed. On an exception it is abandoned and retried, and after 5 attempts it moves to the dead-letter queue.
10. Container logs land in `ContainerLogV2`, Function logs in `AppTraces` and `AppRequests`, and you correlate them with the `order_id`.

### Verify it works

```bash
# 1. Infra and add-ons
kubectl get pods -n kube-system -l app=secrets-store-csi-driver
kubectl get pods -n app-routing-system

# 2. App is running with workload identity
kubectl -n orders-dev get deploy,pods,svc,ingress,secretproviderclass
kubectl -n orders-dev get sa orders -o jsonpath='{.metadata.annotations}'; echo
kubectl -n orders-dev exec deploy/orders -- env | grep AZURE_
kubectl -n orders-dev exec deploy/orders -- ls /mnt/secrets-store

# 3. Call the API through the ingress
INGRESS_IP=$(kubectl get svc nginx -n app-routing-system -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
API_KEY=$(az keyvault secret show --vault-name "<key-vault-name>" -n orders-api-key-dev --query value -o tsv)

curl -s -o /dev/null -w "%{http_code}\n" -H "Host: orders-dev.example.internal" \
  -X POST "http://$INGRESS_IP/orders" -H "Content-Type: application/json" \
  -d '{"customer_id":"c1","sku":"book-1","quantity":1}'        # expect 401

curl -s -H "Host: orders-dev.example.internal" -H "x-api-key: $API_KEY" \
  -X POST "http://$INGRESS_IP/orders" -H "Content-Type: application/json" \
  -d '{"customer_id":"c1","sku":"book-1","quantity":2}'        # expect 202 + order_id

# 4. The Function consumed it (queue count should go back to 0)
az servicebus queue show -g "<resource-group>" --namespace-name "<sb-namespace>" \
  -n orders-dev --query "countDetails.{active:activeMessageCount,dlq:deadLetterMessageCount}"

# 5. Prod is isolated: the dev identity has no role on the prod secret or queue
az role assignment list --assignee "<dev-workload-client-id>" --all \
  --query "[].{role:roleDefinitionName, scope:scope}" -o table
```

Expected results: 401 without a key, 202 with the key, active count back to 0 after a few seconds, the order ID visible in `AppTraces`, and prod pods only after the approval in GitHub.

### Common problems and fixes

| Problem | Likely cause | Fix |
| --- | --- | --- |
| `azure/login` fails with `AADSTS700213: No matching federated identity record found` | The token subject does not match any federated credential (for example a job with `environment: prod` but no `environment:prod` credential) | Check the subject in the error, add or fix the credential in bootstrap, match case exactly |
| Pod stuck in `ContainerCreating`, event `FailedMount ... keyvault` 403 | Workload identity lacks Key Vault Secrets User, wrong `clientID` in SecretProviderClass, or RBAC still propagating | Check the role on the secret, compare `clientID` with the Terraform output, wait a few minutes and delete the pod |
| `AADSTS70021: No matching federated identity record` from the app | Federated credential subject does not match namespace or service account name | Subject must be `system:serviceaccount:orders-dev:orders` and the issuer must be the cluster's `oidc_issuer_url` |
| Pod has no `AZURE_CLIENT_ID` variable | Missing pod label `azure.workload.identity/use: "true"` or missing SA annotation | Fix the chart, then restart the deployment (the webhook only acts at pod creation) |
| `ImagePullBackOff` | Kubelet identity lacks AcrPull, or wrong image name or tag | Check the role assignment on ACR for the kubelet identity, run `az aks check-acr` |
| API returns 500 with `Unauthorized access. 'Send' claim(s) are required` | Workload identity lacks Azure Service Bus Data Sender on the queue | Add the role at the queue scope and wait for propagation |
| Function never triggers | Wrong setting name, missing Data Receiver role, `ORDERS_QUEUE` not set, or app stopped | Check `ServiceBusConnection__fullyQualifiedNamespace`, the role, and `AppTraces` for host errors |
| Trivy fails the build on the base image | New CVEs in `python:3.12-slim` or a library | Rebuild with a patched base image, bump the library, or add a reviewed `.trivyignore` entry with an expiry date |
| Trivy step fails with `TOOMANYREQUESTS` downloading the DB | Rate limit on the default vulnerability DB registry | Set a mirror (for example `TRIVY_DB_REPOSITORY`) or cache the DB between runs |
| `helm upgrade --atomic` times out and rolls back | Readiness probe failing (secret not mounted, wrong env var, crash loop) | `kubectl describe pod`, `kubectl logs --previous`, fix, then redeploy |
| `kubectl` says `You must be logged in to the server` in CI | kubelogin not installed or kubeconfig not converted | Keep `azure/use-kubelogin` and `use-kubelogin: "true"` in `aks-set-context` |
| Terraform 403 creating a Key Vault secret | The deployer has no data plane role yet, or RBAC has not propagated | Check `Key Vault Secrets Officer` for the identity running Terraform; keep the `time_sleep` |
| Ingress returns 404 | Missing or wrong `Host` header | Send `-H "Host: orders-dev.example.internal"` or create a DNS record |
| Terraform `state blob is already locked` | A previous run crashed or two runs overlapped | Confirm no run is active, then `terraform force-unlock <lock-id>` |

### Security checklist

- No secrets in Git or GitHub: OIDC for GitHub, workload identity for pods, managed identity for Functions.
- Service Bus `local_auth_enabled = false` and storage `shared_access_key_enabled = false`, so keys cannot be used even if leaked.
- Least privilege by scope: Key Vault Secrets User on one secret, Service Bus Sender and Receiver on one queue, one identity per environment.
- AKS: local accounts disabled, Azure RBAC for Kubernetes, audit logs in Log Analytics, automatic patch upgrades.
- Pods: non-root, read-only root filesystem, all capabilities dropped, seccomp `RuntimeDefault`, resource limits set.
- Images: built once, scanned with Trivy, tagged by commit SHA, pulled with AcrPull only. ACR admin user disabled.
- Pipelines: PRs cannot deploy, prod and infra need approvals, deployment branches limited to `main`, third-party actions pinned (preferably to a commit SHA).
- Terraform state: Entra ID auth only, versioning and soft delete on, access limited to the pipeline identity and admins.
- Tighten the lab shortcuts before real use: split the GitHub identity into a read-only plan identity and an apply identity, add a condition to `Role Based Access Control Administrator`, use namespace-scoped AKS roles, enable Key Vault purge protection, and use private endpoints for Key Vault, ACR and Service Bus.
- Add TLS on the ingress (app routing can use certificates from Key Vault) before any real traffic.

### Clean up

AKS nodes, the load balancer and the B1 plan cost money every hour. Delete everything when you finish a session.

```bash
# 1. Remove Helm releases (deletes the ingress rules and pods)
helm uninstall orders -n orders-dev
helm uninstall orders -n orders-prod

# 2. Destroy the platform (run locally with the same backend)
cd infra
export TF_VAR_subscription_id="<subscription-id>"
terraform destroy

# 3. Destroy bootstrap (state storage and GitHub identity) only when you are completely done
cd bootstrap
terraform destroy -var "subscription_id=<subscription-id>" -var "prefix=<prefix>" -var "github_repo=<owner>/<repo>"

# 4. Check for leftovers
az group list --query "[?contains(name, '<prefix>')].name" -o table
az keyvault list-deleted --query "[].name" -o table
```

Cost notes (rough, pay-as-you-go, check the Azure pricing calculator for your region):

| Resource | Approximate monthly cost if left running |
| --- | --- |
| AKS control plane (Free tier) | 0 |
| 1-3 x Standard_D2s_v5 nodes | about 70 USD per node |
| Standard load balancer + public IP (app routing) | about 20-25 USD |
| ACR Standard | about 20 USD |
| Service Bus Standard | about 10 USD base plus operations |
| App Service plan B1 (both Function Apps) | about 13 USD |
| Log Analytics | about 2-3 USD per GB ingested (capped by `daily_quota_gb`) |
| Key Vault, storage, App Insights | a few USD |

Expect roughly 150-250 USD per month if you leave it all running, or a few USD per day if you destroy it after each session. You can also stop the cluster between sessions with `az aks stop`.

### Next improvements

- Move to the Functions **Flex Consumption** plan to scale to zero and drop the B1 plan cost.
- Add a second microservice (for example `inventory`) that reuses the generic chart, to prove the chart is really generic.
- Switch deployment to GitOps with Flux or Argo CD (Step 20).
- Bring your own VNet, private cluster, and private endpoints for Key Vault, ACR, Service Bus and storage.
- Add Azure Managed Prometheus and Managed Grafana for metrics dashboards, and log search alerts for restarts, DLQ count and Function failures.
- Add KEDA (the AKS add-on) to scale consumers on queue length.
- Plan the ingress future: the NGINX-based app routing controller follows upstream ingress-nginx, which is being retired, so evaluate the Gateway API option in AKS.
- Sign images (Notation or cosign) and enforce signatures with Azure Policy or Ratify.
- Split Terraform into modules (network, aks, data, app-identity) and per-environment state if dev and prod need separate clusters.

### How to explain this project in an interview

> "As a hands-on lab, I built a small microservices platform on AKS to practise putting the main Azure DevOps pieces together. Terraform with azurerm 4.x creates the cluster, ACR, Key Vault, a Service Bus queue, a Function App and a Log Analytics workspace, with state in Azure Storage. The orders API is a FastAPI service. It reads an API key from Key Vault through the Secrets Store CSI driver and publishes orders to Service Bus. A Python Function consumes the queue in the background. I used no secrets anywhere: GitHub Actions logs in with OIDC, pods use workload identity with a federated credential per namespace, and the Function uses its managed identity with an identity-based trigger connection. Service Bus and storage have key-based auth turned off. The CI/CD pipeline builds the image once, scans it with Trivy and fails on critical or high findings, pushes it to ACR tagged by commit SHA, and deploys it with Helm using atomic upgrades. Dev deploys automatically and prod waits for an approval in a GitHub environment. I built it in phases and practised debugging federated identity mismatches and CSI mount failures."

Points that impress interviewers:

- You can explain the token flow: service account token, OIDC issuer, federated credential, Entra ID token.
- You scoped roles to the smallest resource (one secret, one queue) and gave each environment its own identity.
- You promote the same image digest from dev to prod instead of rebuilding.
- You know the failure modes: subject mismatch, RBAC propagation delay, missing pod label, DLQ after max deliveries.
- You can say what you would change for real production: private endpoints, split pipeline identities, GitOps, TLS, purge protection.

## Interview Questions

<details><summary>Q1. [Basic] What does each part of this platform do, in one sentence each?</summary>

**Answer:**

Terraform creates the Azure resources and role assignments. ACR stores images. AKS runs the orders API in `orders-dev` and `orders-prod`. Key Vault holds the API keys, and the CSI driver mounts them as files. Service Bus holds order messages. The Function App processes those messages in the background. GitHub Actions builds, scans, pushes and deploys. Helm templates the Kubernetes objects per environment. Azure Monitor and Log Analytics collect logs and metrics for all of it.

</details>

<details><summary>Q2. [Basic] Why does the API publish to Service Bus instead of doing the work directly?</summary>

**Answer:**

To decouple the fast part from the slow part. The API only validates and enqueues, so it returns `202 Accepted` in milliseconds. The Function does the slow work at its own pace. If the worker is down or slow, messages wait in the queue instead of failing user requests. Service Bus also gives retries, a dead-letter queue, and lets you scale producer and consumer separately.

</details>

<details><summary>Q3. [Basic] How does GitHub Actions log in to Azure without a client secret?</summary>

**Answer:**

With OpenID Connect. The workflow has `permissions: id-token: write`, so GitHub issues a signed token whose subject describes the run, for example `repo:<owner>/<repo>:environment:prod`. A federated identity credential on a user-assigned identity trusts the GitHub issuer and that exact subject. `azure/login@v2` (and Terraform with `ARM_USE_OIDC=true`) exchanges the GitHub token for a short-lived Entra ID token. Nothing long-lived is stored in GitHub.

</details>

<details><summary>Q4. [Intermediate] Explain how a pod gets an Entra ID token with workload identity.</summary>

**Answer:**

1. AKS has an OIDC issuer and the workload identity webhook.
2. The service account `orders` is annotated with `azure.workload.identity/client-id`, and the pod has the label `azure.workload.identity/use: "true"`.
3. The webhook injects a projected service account token file plus `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_FEDERATED_TOKEN_FILE` and `AZURE_AUTHORITY_HOST`.
4. `DefaultAzureCredential` sends that Kubernetes token to Entra ID.
5. Entra ID checks the federated credential on the user-assigned identity: issuer must equal the cluster's OIDC URL, subject must equal `system:serviceaccount:orders-dev:orders`.
6. Entra ID returns an access token for the identity, which then needs normal Azure RBAC roles on the target resource.

</details>

<details><summary>Q5. [Intermediate] Why did you use the Key Vault CSI driver instead of a Kubernetes Secret created by the pipeline?</summary>

**Answer:**

The secret never passes through the pipeline or Git, and it is not stored in etcd unless you choose to sync it. The CSI driver reads it at pod start with the pod's own identity, so access is controlled by Azure RBAC on the specific secret. With `secret_rotation_enabled`, the mounted file is refreshed on an interval, and because the app reads the file on each request, a rotated key works without a redeploy. If an app needs an environment variable, you can add `secretObjects` to sync it into a Kubernetes Secret, but then remember that env vars only update after a pod restart.

</details>

<details><summary>Q6. [Intermediate] How do dev and prod stay isolated when they share one AKS cluster?</summary>

**Answer:**

- Separate namespaces (`orders-dev`, `orders-prod`) and separate Helm releases and values files.
- Separate user-assigned identities, each with a federated credential bound to one namespace and service account.
- Each identity has roles only on its own Key Vault secret and its own queue, so the dev pod cannot read the prod key or send to the prod queue.
- Separate Function Apps with their own identities and queues.
- Prod deploys need a GitHub environment approval.

For stronger isolation (noisy neighbours, cluster upgrades, blast radius), real teams often use separate clusters or subscriptions for prod. Network policies between namespaces are another easy improvement.

</details>

<details><summary>Q7. [Intermediate] What does <code>helm upgrade --install --atomic</code> give you in the pipeline?</summary>

**Answer:**

`--install` creates the release if it does not exist, so the same command works for the first and the hundredth deploy. `--atomic` implies `--wait`: Helm waits until the new pods are ready and, if they are not ready before `--timeout`, it rolls back to the previous revision and the job fails. Combined with readiness probes and `maxUnavailable: 0`, a bad image never fully replaces the good one. In Helm 4 the flag is renamed `--rollback-on-failure`, so pin the Helm version in CI.

</details>

<details><summary>Q8. [Intermediate] How does the Function App connect to Service Bus without a connection string?</summary>

**Answer:**

The trigger uses `connection="ServiceBusConnection"`. Instead of an app setting called `ServiceBusConnection` holding a connection string, there is `ServiceBusConnection__fullyQualifiedNamespace = <namespace>.servicebus.windows.net`. The Service Bus extension (5.x, from extension bundle 4.x) sees the double-underscore setting and authenticates with the Function's managed identity. That identity has Azure Service Bus Data Receiver on the queue. The host storage works the same way with `AzureWebJobsStorage__accountName` and Storage Blob Data Owner.

</details>

<details><summary>Q9. [Advanced] A deploy to dev fails: pods are stuck in ContainerCreating and Helm rolls back. How do you troubleshoot? <em>(scenario)</em></summary>

**Answer:**

1. `kubectl -n orders-dev describe pod <pod>` and read the events. `FailedMount` with `secrets-store` points at the CSI driver.
2. If the error says 403 or `Forbidden`, the identity lacks Key Vault Secrets User on that secret, or the role is new and still propagating.
3. If it says `AADSTS70021` or no matching federated identity, compare the federated credential subject with the namespace and service account name, and the issuer with `az aks show --query oidcIssuerProfile.issuerUrl`.
4. Check the SecretProviderClass `clientID` matches the identity client ID and the `keyvaultName` and object names are correct.
5. Check the CSI driver pods in `kube-system` and their logs.
6. Fix the cause, then redeploy. Pods are only re-mounted on creation, so delete the stuck pod or rerun the pipeline.

</details>

<details><summary>Q10. [Advanced] Orders are accepted with 202 but never processed, and the dead-letter count keeps growing. What do you check? <em>(scenario)</em></summary>

**Answer:**

Messages reach the queue, and the Function receives them but fails every time, so after `max_delivery_count` (5) they move to the DLQ.

- Read `AppExceptions` and `AppTraces` for the Function to see the exception.
- Peek a DLQ message (Service Bus Explorer in the portal) and check `DeadLetterReason` and the body. A schema change in the API is a common cause.
- Check for downstream failures (database, external API) and timeouts versus `lock_duration`. If processing takes longer than the lock, the message is redelivered and counted again.
- After the fix, replay DLQ messages back to the main queue. The handler must be idempotent, keyed on `order_id`, because redelivery can repeat work.
- Add an alert on DLQ count so you see this before users do.

</details>

<details><summary>Q11. [Advanced] What would you change to make this lab production-grade? <em>(scenario)</em></summary>

**Answer:**

- Network: own VNet, private AKS API server or authorized IP ranges, private endpoints for Key Vault, ACR, Service Bus and storage, egress through a firewall.
- Identity: separate plan (read-only) and apply identities for Terraform, a condition on the RBAC Administrator role, namespace-scoped AKS roles for deploys.
- Reliability: Standard AKS tier with availability zones, separate system and user node pools, PDBs and topology spread, Premium Service Bus if you need zones and isolation.
- Delivery: GitOps, image signing, policy enforcement (Azure Policy for AKS), TLS on ingress, DNS.
- Operations: alerts with action groups, dashboards, runbooks, budget alerts, Key Vault purge protection, backup of state.

</details>

<details><summary>Q12. [Advanced] Why build once and promote the same image instead of building separately for dev and prod?</summary>

**Answer:**

A rebuild can produce a different image even from the same commit, because base images and package versions change over time. If prod gets a new build, what you tested in dev is not what you ship. Building once, tagging with the commit SHA, scanning once, and deploying that same tag (or better, the digest) to every environment means prod runs exactly the bits that passed dev. Only configuration changes between environments, and it lives in `values-dev.yaml` and `values-prod.yaml`. It also makes rollback simple: redeploy the previous tag.

</details>
