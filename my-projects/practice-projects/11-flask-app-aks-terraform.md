# Practice Project 11: Flask App on AKS Provisioned with Terraform

> This guide shows how to use Terraform (azurerm 4.x) to create an AKS cluster and an ACR registry, let AKS pull from ACR with a role assignment, and then build and deploy a Flask app to the cluster with kubectl.

## Key Concepts

### What you will build

You will build the infrastructure and the app in two clear layers:

1. **Infrastructure with Terraform**: a resource group, an Azure Container Registry, an AKS cluster (Azure CNI Overlay, OIDC issuer and workload identity enabled), an optional Log Analytics workspace for Container Insights, and an `AcrPull` role assignment for the cluster's kubelet identity.
2. **Application with Azure CLI and kubectl**: build the Flask image in Azure with `az acr build`, then deploy a Deployment and a LoadBalancer Service with `kubectl apply`.

Final result: `terraform output` prints the command to get cluster credentials, `kubectl get svc flask-app` shows a public IP, and `curl http://<external-ip>/` returns JSON with the pod name. Run it a few times and you see different pod names, which shows the load balancing across replicas. At the end, `terraform destroy` removes everything.

### Architecture

```text
 Your laptop
   |
   |  terraform init / plan / apply           (azurerm ~> 4.0)
   v
 +----------------------------- Resource group: rg-flaskdemo-dev ------------------------------+
 |                                                                                             |
 |  Log Analytics (optional) <---- Container Insights (oms_agent)                              |
 |                                        |                                                    |
 |  ACR: acrflaskdemo<random>             |                                                    |
 |   ^   ^                                |                                                    |
 |   |   |  AcrPull role assignment        |                                                    |
 |   |   +--------- kubelet identity --- AKS: aks-flaskdemo-dev                                |
 |   |                                     - system node pool (2 x Standard_D2s_v5)           |
 |   |                                     - Azure CNI Overlay (pods: 192.168.0.0/16)          |
 |   |                                     - OIDC issuer + workload identity                  |
 |   |                                     - Deployment flask-app (2 pods)                    |
 |   |                                     - Service flask-app (type LoadBalancer)             |
 +---|-----------------------------------------------|-----------------------------------------+
     |                                               |
     | az acr build (image built in Azure)           v
 Your laptop                               Azure public IP :80  <---- curl from the internet
```

### Tools and why each one is used

| Tool | What it does here | Why this tool |
| --- | --- | --- |
| Terraform | Creates resource group, ACR, AKS, Log Analytics and role assignment | Declarative, repeatable, reviewable with `plan` |
| azurerm provider 4.x | Talks to Azure Resource Manager for Terraform | Official Azure provider |
| random provider | Generates a unique suffix for the ACR name | ACR names must be globally unique |
| Azure CLI | Login, `az acr build`, `az aks get-credentials` | Official CLI; ACR Tasks builds without local Docker |
| AKS | Runs the Flask containers | Managed Kubernetes, free control plane tier |
| ACR | Stores the Flask image | Private registry, Entra ID auth, no pull secrets needed |
| kubectl | Applies the Deployment and Service | Standard Kubernetes CLI |
| Flask + gunicorn | The sample web app | Small, easy to read |

### Prerequisites

- Azure subscription where you are **Owner** (or Contributor + User Access Administrator). Creating a role assignment needs `Microsoft.Authorization/roleAssignments/write`.
- Tools on your laptop:
  - Terraform 1.9 or newer: `terraform version`
  - Azure CLI 2.60 or newer: `az version`
  - kubectl and kubelogin: `az aks install-cli`
  - Docker is optional (only to run the app locally; `az acr build` builds in Azure)
- Log in and pick the subscription:

```bash
az login
az account set --subscription "<subscription-id>"
az account show --query "{name:name, id:id}" -o table
```

Cost warning: two `Standard_D2s_v5` nodes, a Standard load balancer with a public IP, and a Basic ACR cost a few US dollars per day. Log Analytics adds ingestion cost if enabled. Run `terraform destroy` when you finish.

### Folder structure

```text
flask-aks-terraform/
├── app/
│   ├── app.py
│   ├── requirements.txt
│   └── Dockerfile
├── infra/
│   ├── providers.tf
│   ├── variables.tf
│   ├── main.tf
│   ├── outputs.tf
│   └── terraform.tfvars        # your values (do not commit secrets)
├── k8s/
│   ├── deployment.yaml
│   └── service.yaml
└── .gitignore
```

### Step-by-step

#### Step 1: Write the Flask app and Dockerfile

The app returns the pod hostname, so you can see which replica answered.

```python
# app/app.py
import os
import socket

from flask import Flask, jsonify

app = Flask(__name__)


@app.get("/")
def index():
    return jsonify(
        message="Hello from Flask on AKS, provisioned by Terraform",
        pod=socket.gethostname(),
        version=os.getenv("APP_VERSION", "v1"),
    )


@app.get("/healthz")
def healthz():
    return jsonify(status="ok")
```

```text
# app/requirements.txt
flask==3.1.0
gunicorn==23.0.0
```

```dockerfile
# app/Dockerfile
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .

RUN useradd --create-home --uid 10001 appuser
USER 10001

EXPOSE 5000
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "app:app"]
```

```text
# .gitignore
.terraform/
*.tfstate
*.tfstate.*
crash.log
*.tfvars
!example.tfvars
```

What this does:

- `/healthz` is used by the Kubernetes probes.
- `socket.gethostname()` returns the pod name inside Kubernetes.
- The container runs as a non-root user and serves with gunicorn on port 5000.
- `.gitignore` keeps state files and local variable files out of Git. State can contain sensitive values.

#### Step 2: Configure Terraform and the providers

In azurerm 4.x, `subscription_id` is required in the provider block (or through the `ARM_SUBSCRIPTION_ID` environment variable).

```hcl
# infra/providers.tf
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

  # For a team, store state remotely (see Next improvements):
  # backend "azurerm" {}
}

provider "azurerm" {
  features {}
  subscription_id = var.subscription_id
}
```

What this does:

- `~> 4.0` allows any 4.x release but not 5.0, so a major version with breaking changes is never picked up by accident.
- `features {}` is required, even when empty.
- The provider uses your `az login` session for authentication. In CI you would use OIDC with `ARM_USE_OIDC=true`, `ARM_CLIENT_ID` and `ARM_TENANT_ID`.
- State is local for this lab. Remote state is listed in Next improvements.

#### Step 3: Define variables

```hcl
# infra/variables.tf
variable "subscription_id" {
  description = "Azure subscription ID to deploy into"
  type        = string
}

variable "location" {
  description = "Azure region"
  type        = string
  default     = "eastus"
}

variable "prefix" {
  description = "Short name used in resource names (lowercase letters and numbers)"
  type        = string
  default     = "flaskdemo"

  validation {
    condition     = can(regex("^[a-z0-9]{3,12}$", var.prefix))
    error_message = "prefix must be 3-12 lowercase letters or numbers (it is used in the ACR name)."
  }
}

variable "environment" {
  description = "Environment name, for example dev"
  type        = string
  default     = "dev"
}

variable "node_count" {
  description = "Number of nodes in the system node pool"
  type        = number
  default     = 2
}

variable "node_vm_size" {
  description = "VM size for the system node pool"
  type        = string
  default     = "Standard_D2s_v5"
}

variable "kubernetes_version" {
  description = "AKS Kubernetes version. null means the current AKS default."
  type        = string
  default     = null
}

variable "enable_monitoring" {
  description = "Create Log Analytics and enable Container Insights"
  type        = bool
  default     = false
}
```

```hcl
# infra/terraform.tfvars
subscription_id   = "<subscription-id>"
location          = "eastus"
prefix            = "flaskdemo"
environment       = "dev"
node_count        = 2
enable_monitoring = false
```

What this does:

- The `validation` block catches an invalid prefix at `plan` time instead of failing later in Azure.
- `kubernetes_version = null` lets AKS choose its default supported version. Check available versions with `az aks get-versions -l eastus -o table` if you want to pin one.
- `terraform.tfvars` is loaded automatically. The subscription ID is not a secret, but keep the file out of Git anyway as a habit.

#### Step 4: Create the resource group, Log Analytics and ACR

```hcl
# infra/main.tf  (part 1)
resource "random_string" "suffix" {
  length  = 6
  upper   = false
  special = false
}

locals {
  name     = "${var.prefix}-${var.environment}"
  acr_name = "acr${var.prefix}${random_string.suffix.result}"
  tags = {
    project     = "flask-aks-terraform"
    environment = var.environment
    managed_by  = "terraform"
  }
}

resource "azurerm_resource_group" "rg" {
  name     = "rg-${local.name}"
  location = var.location
  tags     = local.tags
}

resource "azurerm_log_analytics_workspace" "law" {
  count               = var.enable_monitoring ? 1 : 0
  name                = "log-${local.name}"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  sku                 = "PerGB2018"
  retention_in_days   = 30
  tags                = local.tags
}

resource "azurerm_container_registry" "acr" {
  name                = local.acr_name
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  sku                 = "Basic"
  admin_enabled       = false
  tags                = local.tags
}
```

What this does:

- `random_string` gives a 6-character suffix, so the ACR name (5-50 lowercase alphanumeric characters, globally unique) does not clash with someone else's. The value is saved in state, so it stays the same on later applies.
- `count = var.enable_monitoring ? 1 : 0` creates the workspace only when you turn monitoring on.
- `admin_enabled = false` disables the shared admin username and password. AKS pulls with its managed identity instead.

#### Step 5: Create the AKS cluster

```hcl
# infra/main.tf  (part 2)
resource "azurerm_kubernetes_cluster" "aks" {
  name                = "aks-${local.name}"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  dns_prefix          = "aks-${local.name}"
  kubernetes_version  = var.kubernetes_version
  sku_tier            = "Free"

  oidc_issuer_enabled       = true
  workload_identity_enabled = true

  default_node_pool {
    name                        = "system"
    vm_size                     = var.node_vm_size
    node_count                  = var.node_count
    temporary_name_for_rotation = "systemtmp"

    upgrade_settings {
      max_surge = "10%"
    }
  }

  identity {
    type = "SystemAssigned"
  }

  network_profile {
    network_plugin      = "azure"
    network_plugin_mode = "overlay"
    pod_cidr            = "192.168.0.0/16"
    service_cidr        = "10.0.0.0/16"
    dns_service_ip      = "10.0.0.10"
    load_balancer_sku   = "standard"
  }

  dynamic "oms_agent" {
    for_each = var.enable_monitoring ? [1] : []
    content {
      log_analytics_workspace_id      = azurerm_log_analytics_workspace.law[0].id
      msi_auth_for_monitoring_enabled = true
    }
  }

  tags = local.tags
}
```

What this does:

- `sku_tier = "Free"` has no control plane charge (no uptime SLA). Use `Standard` for production.
- `default_node_pool` is the system node pool. It runs system pods like CoreDNS and, in this lab, your app too. `temporary_name_for_rotation` lets Terraform change properties such as `vm_size` by creating a temporary pool and rotating nodes, instead of failing.
- `upgrade_settings { max_surge = "10%" }` matches the AKS default and avoids a constant diff in `plan`.
- `identity { type = "SystemAssigned" }` gives the cluster a managed identity for the control plane (to create load balancers, public IPs and so on). AKS also creates a separate **kubelet identity** in the node resource group, used by nodes to pull images.
- `network_plugin = "azure"` with `network_plugin_mode = "overlay"` is Azure CNI Overlay: nodes get VNet IPs, pods get IPs from the private `pod_cidr`, so you do not run out of VNet addresses.
- `service_cidr` and `dns_service_ip` must not overlap with the pod CIDR or any network you connect to. `dns_service_ip` must be inside `service_cidr`.
- `oidc_issuer_enabled` and `workload_identity_enabled` prepare the cluster for pods to use Microsoft Entra workload identity (federated credentials) to reach Azure services like Key Vault without secrets.
- The `dynamic "oms_agent"` block adds Container Insights only when monitoring is enabled.

#### Step 6: Let AKS pull from ACR

This is the Terraform version of `az aks update --attach-acr`.

```hcl
# infra/main.tf  (part 3)
resource "azurerm_role_assignment" "aks_acr_pull" {
  scope                            = azurerm_container_registry.acr.id
  role_definition_name             = "AcrPull"
  principal_id                     = azurerm_kubernetes_cluster.aks.kubelet_identity[0].object_id
  principal_type                   = "ServicePrincipal"
  skip_service_principal_aad_check = true
}
```

What this does:

- `scope` limits the permission to this one registry.
- `principal_id` is the **kubelet identity** object ID, not the cluster's control plane identity. The kubelet on each node is what pulls images, so it needs `AcrPull`. This is the most common mistake in this setup.
- `principal_type = "ServicePrincipal"` is correct for managed identities and avoids an extra Entra ID lookup.
- `skip_service_principal_aad_check = true` avoids failures when a brand new identity has not replicated in Entra ID yet.

#### Step 7: Define outputs

```hcl
# infra/outputs.tf
output "resource_group_name" {
  value = azurerm_resource_group.rg.name
}

output "aks_name" {
  value = azurerm_kubernetes_cluster.aks.name
}

output "acr_name" {
  value = azurerm_container_registry.acr.name
}

output "acr_login_server" {
  value = azurerm_container_registry.acr.login_server
}

output "kubelet_identity_object_id" {
  value = azurerm_kubernetes_cluster.aks.kubelet_identity[0].object_id
}

output "oidc_issuer_url" {
  value = azurerm_kubernetes_cluster.aks.oidc_issuer_url
}

output "get_credentials_command" {
  value = "az aks get-credentials --resource-group ${azurerm_resource_group.rg.name} --name ${azurerm_kubernetes_cluster.aks.name} --overwrite-existing"
}
```

What this does:

- Outputs make the next steps copy-paste friendly, and scripts can read them with `terraform output -raw <name>`.
- `oidc_issuer_url` is what you will need later to create federated credentials for workload identity.
- The raw kubeconfig is deliberately not output. It contains credentials. Use `az aks get-credentials` instead.

#### Step 8: Run terraform init, plan and apply

```bash
cd infra

terraform init
terraform fmt -recursive
terraform validate
terraform plan -out tfplan
terraform apply tfplan
```

Expected end of the apply (values will differ):

```text
Apply complete! Resources: 5 added, 0 changed, 0 destroyed.

Outputs:

acr_login_server = "acrflaskdemoa1b2c3.azurecr.io"
acr_name = "acrflaskdemoa1b2c3"
aks_name = "aks-flaskdemo-dev"
get_credentials_command = "az aks get-credentials --resource-group rg-flaskdemo-dev --name aks-flaskdemo-dev --overwrite-existing"
kubelet_identity_object_id = "00000000-0000-0000-0000-000000000000"
oidc_issuer_url = "https://eastus.oic.prod-aks.azure.com/<tenant-id>/<guid>/"
resource_group_name = "rg-flaskdemo-dev"
```

What this does:

- `init` downloads the azurerm and random providers and creates `.terraform.lock.hcl`. Commit the lock file so everyone uses the same provider versions.
- `fmt` and `validate` catch style and syntax problems before talking to Azure.
- `plan -out tfplan` saves the exact plan. `apply tfplan` applies only that plan, so nothing changes between review and apply.
- AKS creation takes about 5-10 minutes.

#### Step 9: Connect kubectl to the cluster

```bash
eval "$(terraform output -raw get_credentials_command)"
kubectl get nodes -o wide
```

Expected output:

```text
NAME                             STATUS   ROLES    AGE   VERSION   INTERNAL-IP   ...
aks-system-12345678-vmss000000   Ready    <none>   6m    v1.33.x   10.224.0.4    ...
aks-system-12345678-vmss000001   Ready    <none>   6m    v1.33.x   10.224.0.5    ...
```

What this does:

- Runs the `az aks get-credentials` command from the output and merges the cluster into `~/.kube/config`.
- This cluster uses local accounts, so no kubelogin step is needed. If you enable Entra ID integration, also run `kubelogin convert-kubeconfig -l azurecli`.
- Your Kubernetes version will be whatever AKS defaults to at the time you create the cluster.

#### Step 10: Build and push the image with ACR Tasks

`az acr build` uploads the `app/` folder and builds the image inside Azure. You do not need Docker locally.

```bash
ACR_NAME=$(terraform output -raw acr_name)
ACR_LOGIN_SERVER=$(terraform output -raw acr_login_server)
cd ..

az acr build --registry "$ACR_NAME" --image flask-app:v1 ./app
az acr repository show-tags --name "$ACR_NAME" --repository flask-app -o table
```

What this does:

- Builds `app/Dockerfile` in ACR and pushes `flask-app:v1` to the registry.
- You need rights to run ACR Tasks on the registry; as subscription Owner you have them.
- Alternative with local Docker: `az acr login -n "$ACR_NAME"`, then `docker build -t "$ACR_LOGIN_SERVER/flask-app:v1" app && docker push "$ACR_LOGIN_SERVER/flask-app:v1"`.

#### Step 11: Write the Kubernetes manifests

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: flask-app
  labels:
    app: flask-app
spec:
  replicas: 2
  selector:
    matchLabels:
      app: flask-app
  template:
    metadata:
      labels:
        app: flask-app
    spec:
      securityContext:
        runAsNonRoot: true
      containers:
        - name: flask-app
          image: ACR_LOGIN_SERVER/flask-app:v1
          ports:
            - containerPort: 5000
          env:
            - name: APP_VERSION
              value: "v1"
          readinessProbe:
            httpGet:
              path: /healthz
              port: 5000
            initialDelaySeconds: 5
            periodSeconds: 10
          livenessProbe:
            httpGet:
              path: /healthz
              port: 5000
            initialDelaySeconds: 15
            periodSeconds: 20
          resources:
            requests:
              cpu: 100m
              memory: 128Mi
            limits:
              cpu: 500m
              memory: 256Mi
```

```yaml
# k8s/service.yaml
apiVersion: v1
kind: Service
metadata:
  name: flask-app
  labels:
    app: flask-app
spec:
  type: LoadBalancer
  selector:
    app: flask-app
  ports:
    - name: http
      port: 80
      targetPort: 5000
```

What this does:

- `ACR_LOGIN_SERVER` is a placeholder that you replace at deploy time, so the file is not tied to one random registry name.
- Two replicas with readiness and liveness probes. Requests and limits keep the pods well behaved on small nodes.
- The Service selects pods with `app: flask-app`. `type: LoadBalancer` makes AKS create a public IP on the cluster's Standard load balancer (bonus step). Use `ClusterIP` plus an ingress if you do not want a public IP per service.

#### Step 12: Deploy the app

```bash
sed "s|ACR_LOGIN_SERVER|$ACR_LOGIN_SERVER|g" k8s/deployment.yaml | kubectl apply -f -
kubectl apply -f k8s/service.yaml

kubectl rollout status deployment/flask-app --timeout=180s
kubectl get svc flask-app --watch
```

What this does:

- `sed` writes the real registry name into the image field and pipes the result to `kubectl apply`. The file on disk is not changed.
- `rollout status` waits until both pods are ready.
- `--watch` shows the Service until `EXTERNAL-IP` changes from `<pending>` to a real IP (usually under 2 minutes). Press Ctrl+C to stop watching.

#### Step 13: Understand why the kubernetes provider is not used here

You could deploy the Deployment and Service with Terraform's `kubernetes` provider. This guide does not, on purpose.

The problem: a provider is configured **before** resources are planned. If the `kubernetes` provider gets its `host` and certificates from `azurerm_kubernetes_cluster.aks`, those values are unknown during the first plan (the cluster does not exist yet). Terraform's documentation warns that this can cause errors or, worse, the provider connecting to the wrong cluster (for example a default `localhost`). It also breaks when the cluster must be replaced: the provider still points at the old credentials during the plan.

Recommended options:

- **Separate root modules (best)**: `infra/` creates AKS and ACR. A second folder, for example `k8s-apps/`, reads the cluster with a data source and uses the `kubernetes` or `helm` provider. Run them as two applies (two pipeline stages).
- **kubectl, Helm or GitOps (this guide)**: Terraform owns Azure resources; app manifests are applied by kubectl, Helm, or Argo CD/Flux. This is the most common real-world split.
- **Same configuration, carefully**: possible, but create the cluster first with `terraform apply -target=azurerm_kubernetes_cluster.aks`, then run a full apply. Avoid this for anything long-lived.

Example of the second root module reading an existing cluster:

```hcl
# k8s-apps/main.tf  (separate folder and separate state)
data "azurerm_kubernetes_cluster" "aks" {
  name                = "aks-flaskdemo-dev"
  resource_group_name = "rg-flaskdemo-dev"
}

provider "kubernetes" {
  host                   = data.azurerm_kubernetes_cluster.aks.kube_config[0].host
  cluster_ca_certificate = base64decode(data.azurerm_kubernetes_cluster.aks.kube_config[0].cluster_ca_certificate)
  client_certificate     = base64decode(data.azurerm_kubernetes_cluster.aks.kube_config[0].client_certificate)
  client_key             = base64decode(data.azurerm_kubernetes_cluster.aks.kube_config[0].client_key)
}
```

What this does:

- The data source reads a cluster that already exists, so all values are known at plan time.
- The certificate fields work only for clusters with local accounts. For Entra ID clusters, use an `exec` block that runs `kubelogin get-token --login azurecli --server-id 6dae42f8-4368-4678-94ff-3960e28e3630` (the well-known AKS server application ID) instead of client certificates.
- Note that the kubeconfig values end up in the Terraform state of the second module, so protect that state.

### Verify it works

```bash
kubectl get deploy,pods,svc -l app=flask-app -o wide
```

Expected output (names and IPs will differ):

```text
NAME                        READY   UP-TO-DATE   AVAILABLE   AGE
deployment.apps/flask-app   2/2     2            2           3m

NAME                             READY   STATUS    RESTARTS   AGE   IP              NODE
pod/flask-app-6f7d9c5b8c-2xkqp   1/1     Running   0          3m    192.168.0.27    aks-system-12345678-vmss000000
pod/flask-app-6f7d9c5b8c-t9w4r   1/1     Running   0          3m    192.168.1.14    aks-system-12345678-vmss000001

NAME                TYPE           CLUSTER-IP    EXTERNAL-IP    PORT(S)        AGE
service/flask-app   LoadBalancer   10.0.142.33   20.115.42.81   80:30652/TCP   3m
```

Notice the pod IPs come from `192.168.0.0/16` (the overlay pod CIDR) and the Service IP from `10.0.0.0/16`.

```bash
EXTERNAL_IP=$(kubectl get svc flask-app -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
for i in 1 2 3 4; do curl -s "http://$EXTERNAL_IP/"; echo; done
```

```text
{"message":"Hello from Flask on AKS, provisioned by Terraform","pod":"flask-app-6f7d9c5b8c-2xkqp","version":"v1"}
{"message":"Hello from Flask on AKS, provisioned by Terraform","pod":"flask-app-6f7d9c5b8c-t9w4r","version":"v1"}
...
```

Confirm the ACR integration and the role assignment:

```bash
az aks check-acr \
  --resource-group "$(terraform -chdir=infra output -raw resource_group_name)" \
  --name "$(terraform -chdir=infra output -raw aks_name)" \
  --acr "$ACR_LOGIN_SERVER"

az role assignment list \
  --assignee "$(terraform -chdir=infra output -raw kubelet_identity_object_id)" \
  --all --query "[].{role:roleDefinitionName, scope:scope}" -o table
```

Confirm Terraform has no drift:

```bash
terraform -chdir=infra plan
```

```text
No changes. Your infrastructure matches the configuration.
```

### Common problems and fixes

| Problem | Likely cause | Fix |
| --- | --- | --- |
| `subscription_id is a required provider property` | azurerm 4.x needs it explicitly | Set `subscription_id` in the provider (via variable) or export `ARM_SUBSCRIPTION_ID` |
| `AuthorizationFailed ... roleAssignments/write` | Your account cannot create role assignments | Use an Owner or User Access Administrator account, or ask an admin |
| ACR `name already in use` or invalid name | ACR names are global and alphanumeric only | Change `prefix`; keep the random suffix |
| Pods `ImagePullBackOff` with `401 Unauthorized` | AcrPull given to the wrong identity, or role not propagated yet | Use `kubelet_identity[0].object_id`; wait 1-2 minutes; run `az aks check-acr` |
| Pods `ImagePullBackOff` with `not found` | Placeholder not replaced or wrong tag | `kubectl describe pod`; check `az acr repository show-tags` |
| `EXTERNAL-IP` stays `<pending>` | Public IP quota, policy blocking public IPs, or cluster identity lacks rights | `kubectl describe svc flask-app` and check events |
| `VM size not allowed` or quota error during apply | Region quota or SKU not available | Change `node_vm_size` or region; request quota |
| Plan always shows a change in `upgrade_settings` | Block missing while AKS sets defaults | Keep `upgrade_settings { max_surge = "10%" }` |
| `kubernetes` provider tries `localhost` | Provider configured from a resource that does not exist yet | Split into two root modules or use `-target` for the first apply |
| `terraform destroy` hangs on the resource group | Resources created outside Terraform (for example by kubectl) still exist | Delete the Service first (`kubectl delete -f k8s/`), then destroy |

### Clean up

Delete Kubernetes objects first so the load balancer rule and public IP are removed by AKS cleanly, then destroy the infrastructure.

```bash
kubectl delete -f k8s/service.yaml
kubectl delete deployment flask-app

terraform -chdir=infra destroy
```

Confirm nothing is left:

```bash
az group list --query "[?contains(name, 'flaskdemo')].name" -o tsv
kubectl config delete-context aks-flaskdemo-dev
```

What this does:

- `terraform destroy` deletes AKS (and its node resource group `MC_...`), ACR, Log Analytics, the role assignment and the resource group.
- The `az group list` query should return nothing after a few minutes.

Rough cost guide (varies by region and over time):

| Resource | Approximate cost |
| --- | --- |
| AKS control plane (Free tier) | 0 |
| 2 x Standard_D2s_v5 nodes | Largest part, roughly 0.1 USD per node per hour |
| Standard load balancer + public IP | Small hourly charge plus data |
| ACR Basic | Small daily charge |
| Log Analytics (if enabled) | Per GB ingested |

To pause instead of destroy, `az aks stop -g rg-flaskdemo-dev -n aks-flaskdemo-dev` stops the nodes (you still pay for disks and the public IP).

### Next improvements

- Store state remotely in an Azure Storage account with `backend "azurerm"` and `use_azuread_auth = true`, with state locking and versioning.
- Run Terraform from a pipeline (GitHub Actions with OIDC): `plan` on pull requests, `apply` on merge with approval.
- Put the cluster in your own VNet and subnet (`vnet_subnet_id`) and consider a private cluster.
- Enable Entra ID integration with Azure RBAC (`azure_active_directory_role_based_access_control`) and set `local_account_disabled = true`.
- Add a separate user node pool for apps and keep the system pool for system pods only.
- Enable the cluster autoscaler (`auto_scaling_enabled`, `min_count`, `max_count`).
- Use workload identity for the app to read secrets from Key Vault.
- Replace the LoadBalancer Service with an ingress or Gateway API and TLS.
- Move the infra into reusable modules and add `tflint` and `checkov` in CI.

### How to explain this project in an interview

> "This is a hands-on lab I built to practice Terraform with AKS. Terraform with azurerm 4.x creates a resource group, an ACR with the admin user disabled, an optional Log Analytics workspace, and an AKS cluster using Azure CNI Overlay, a system-assigned identity, and the OIDC issuer and workload identity turned on. Then I give AcrPull on the registry to the cluster's kubelet identity, because the kubelet is what pulls images, not the control plane identity. I output the get-credentials command, build the image in Azure with az acr build, and deploy a Deployment with probes and resource limits plus a LoadBalancer Service with kubectl. I kept Kubernetes objects out of the same Terraform apply on purpose, because a kubernetes provider configured from a cluster that does not exist yet is unreliable. In a real setup I would split it into two root modules or use GitOps. At the end I clean up with terraform destroy."

Points that impress interviewers:

- You know the difference between the cluster identity and the kubelet identity, and which one needs `AcrPull`.
- You can explain the provider-configuration problem with the `kubernetes` provider and how to avoid it.
- You used `plan -out` and `apply tfplan`, a validated variable, and a random suffix for globally unique names.
- You can explain Azure CNI Overlay versus classic Azure CNI and why it saves VNet IP addresses.

## Interview Questions

<details><summary>Q1. [Basic] Why do we grant <code>AcrPull</code> to the kubelet identity and not to the cluster identity?</summary>

**Answer:**

AKS has two identities. The cluster (control plane) identity manages Azure resources for the cluster, such as load balancers, public IPs and disks. The kubelet identity is assigned to the node pool VMs, and the kubelet on each node pulls container images. Image pulls from ACR are authenticated with the kubelet identity, so that is the identity that needs `AcrPull` on the registry. In Terraform it is `azurerm_kubernetes_cluster.aks.kubelet_identity[0].object_id`. `az aks update --attach-acr` does the same thing.

</details>

<details><summary>Q2. [Basic] What do <code>terraform init</code>, <code>plan</code> and <code>apply</code> do?</summary>

**Answer:**

- `init` prepares the working folder: downloads providers, configures the backend for state, and creates the dependency lock file.
- `plan` compares the configuration with the state and real infrastructure and shows what it will add, change or destroy. With `-out tfplan` it saves that plan.
- `apply` makes the changes. `apply tfplan` applies exactly the saved plan, which is the safe pattern in pipelines because nothing can change between review and apply.

</details>

<details><summary>Q3. [Basic] What changed in the azurerm provider 4.x that often breaks old code?</summary>

**Answer:**

The most visible change is that `subscription_id` is now required in the provider block (or through `ARM_SUBSCRIPTION_ID`). Version 4 also renamed or removed several deprecated arguments, for example on AKS `enable_auto_scaling` became `auto_scaling_enabled` and some network and identity arguments were cleaned up. When upgrading from 3.x, pin the version, read the upgrade guide, and run `plan` to see what changes before applying.

</details>

<details><summary>Q4. [Intermediate] What is Azure CNI Overlay and why use it?</summary>

**Answer:**

With classic Azure CNI, every pod gets an IP from the VNet subnet, so a large cluster can use thousands of VNet IPs and you must plan big subnets. With Azure CNI Overlay, only nodes get VNet IPs. Pods get IPs from a private `pod_cidr` (like `192.168.0.0/16`) that is not part of the VNet, and traffic leaving the cluster is NATed to the node IP. This saves VNet address space and makes scaling easier, while keeping Azure CNI performance. In Terraform it is `network_plugin = "azure"` and `network_plugin_mode = "overlay"`.

</details>

<details><summary>Q5. [Intermediate] Why is it risky to use the kubernetes provider in the same apply that creates the cluster?</summary>

**Answer:**

Terraform configures providers before it creates resources. If the `kubernetes` provider gets its host and certificates from `azurerm_kubernetes_cluster`, those values are unknown in the first plan, and the provider may fail or fall back to defaults like `localhost`. If the cluster is replaced later, the plan uses old credentials. The safe approaches are two root modules with separate state (infra first, then apps using a data source), or keeping app deployment in kubectl, Helm or GitOps. If you must use one configuration, apply the cluster first with `-target` and then run a full apply.

</details>

<details><summary>Q6. [Intermediate] Pods are stuck in <code>ImagePullBackOff</code> right after <code>terraform apply</code>. How do you troubleshoot? <em>(scenario)</em></summary>

**Answer:**

1. `kubectl describe pod <name>` and read the Events. `401 Unauthorized` means an auth problem; `not found` means a wrong image name or tag.
2. For auth: check the role assignment targets the kubelet identity, not the cluster identity: `az role assignment list --assignee <kubelet-object-id> --all`.
3. Run `az aks check-acr -g <rg> -n <aks> --acr <acr>.azurecr.io`, which tests pulling from the nodes.
4. Role assignments can take a minute or two to propagate; delete the pod to retry.
5. For not found: `az acr repository show-tags -n <acr> --repository flask-app` and check the image field, for example that the `ACR_LOGIN_SERVER` placeholder was replaced.

</details>

<details><summary>Q7. [Intermediate] What are <code>oidc_issuer_enabled</code> and <code>workload_identity_enabled</code> used for?</summary>

**Answer:**

`oidc_issuer_enabled` makes AKS publish an OIDC issuer URL that signs Kubernetes service account tokens. `workload_identity_enabled` installs the workload identity webhook that injects environment variables and a projected token into pods that use an annotated service account. Together they let a pod exchange its service account token for a Microsoft Entra token through a federated credential on a managed identity. The app can then access Key Vault, Storage or a database without any secret in the cluster. It replaces the older pod-managed identity.

</details>

<details><summary>Q8. [Advanced] Your team shares this Terraform code. How do you manage state safely? <em>(scenario)</em></summary>

**Answer:**

Use a remote backend in an Azure Storage account (`backend "azurerm"`), one state file per environment (separate keys or folders). The azurerm backend uses blob leases for state locking, so two people cannot apply at once. Enable blob versioning and soft delete to recover from mistakes, use Entra ID auth (`use_azuread_auth = true`) instead of storage account keys, restrict access with RBAC, and disable public network access where possible. Never commit `.tfstate` to Git, because state can contain sensitive values such as kubeconfig credentials. Run applies only from a pipeline with approvals.

</details>

<details><summary>Q9. [Advanced] Someone scaled the node pool in the portal. What happens on the next <code>terraform plan</code>, and how do you handle it? <em>(scenario)</em></summary>

**Answer:**

Terraform refreshes state from Azure and sees `node_count` differs from the configuration, so `plan` shows an in-place change back to the configured value. You can either update the code to match if the change was intended, or apply to revert it. If you enable the cluster autoscaler, the node count is expected to change outside Terraform, so you set `auto_scaling_enabled = true` with `min_count` and `max_count`, and Terraform no longer manages the exact count. In general, use `lifecycle { ignore_changes = [...] }` only for fields that are intentionally managed elsewhere, and restrict portal write access to avoid drift.

</details>

<details><summary>Q10. [Advanced] How would you change this design for production?</summary>

**Answer:**

- Remote state with locking, and Terraform run from CI with OIDC and approvals.
- AKS `Standard` tier for the uptime SLA, availability zones, and a separate user node pool with autoscaling.
- Own VNet and subnets, private cluster or authorized IP ranges, and private endpoint for ACR (Premium SKU).
- Entra ID with Azure RBAC and local accounts disabled.
- Container Insights and Azure Monitor managed Prometheus enabled.
- Workload identity plus Key Vault for app secrets.
- Ingress or Gateway API with TLS instead of a public IP per Service.
- Apps deployed by Helm or GitOps from a separate repository or stage, not by the infra Terraform.

</details>
