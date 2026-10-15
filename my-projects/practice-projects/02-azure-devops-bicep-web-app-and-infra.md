# Practice Project 2: Azure DevOps Pipelines Deploying Bicep Infrastructure and a Web App to AKS

> This guide walks you through building a multi-stage Azure DevOps YAML pipeline that deploys a VNet, Storage account, ACR and AKS cluster with Bicep, then builds a container image and deploys it to AKS, with separate dev and prod environments and an approval gate on prod.

## Key Concepts

### What you will build

You will build a full "infrastructure + application" delivery flow in Azure DevOps:

- An Azure DevOps project with code in **Azure Repos**, a protected `main` branch (pull request + build validation required).
- An **Azure Resource Manager service connection** that uses **workload identity federation** (no client secret).
- **Variable groups** per environment (`dev-config`, `prod-config`) and one group linked to **Azure Key Vault**.
- **Bicep** code: `main.bicep` calling modules for a VNet with subnets, a secure Storage account, an Azure Container Registry (ACR) and an AKS cluster (Azure CNI Overlay, OIDC issuer, workload identity).
- A **multi-stage pipeline**: Validate -> DeployInfra -> BuildApp -> DeployApp, run first for `dev` and then for `prod`, with a manual approval on `prod`.

Final result: you push a change to `main`, the pipeline validates the Bicep, deploys infra, builds the image in ACR, deploys it to AKS, waits for your approval, and then does the same for prod. You open the Service's public IP in a browser and see "Hello from AKS (dev)".

### Architecture

```text
 Developer
    |  git push / pull request
    v
 Azure Repos (main is protected: PR + build validation)
    |
    v
 Azure Pipelines (azure-pipelines.yml)
    |
    |-- Stage: Validate        az bicep build, build-params, what-if (dev)
    |
    |-- dev stages (template: env-stages.yml)
    |     DeployInfra_dev  -> deployment job -> environment "dev"
    |     BuildApp_dev     -> az acr build -> acrbicepweblabdev01.azurecr.io/webapp:<BuildId>
    |     DeployApp_dev    -> deployment job -> az aks get-credentials + kubectl apply
    |
    |-- prod stages (same template)       [Approval check on environment "prod"]
          DeployInfra_prod -> BuildApp_prod -> DeployApp_prod

 Service connection (workload identity federation) --> Entra ID app / managed identity
                                                      --> RBAC on rg-bicepweb-dev / rg-bicepweb-prod

 Each resource group contains:
   +-------------------------------------------------------------+
   | VNet 10.x.0.0/16                                            |
   |   snet-aks (nodes)          snet-private-endpoints (future) |
   | AKS (system pool, Azure CNI Overlay, OIDC + workload id)    |
   |   kubelet identity --AcrPull--> ACR (Basic, no admin user)  |
   | Storage account (HTTPS only, TLS 1.2, no public blob)       |
   +-------------------------------------------------------------+
```

### Tools and why each one is used

| Tool | What it does here | Why this tool |
| --- | --- | --- |
| Azure Repos | Stores the Bicep, app and pipeline code | Native to Azure DevOps, supports branch policies and PR build validation |
| Azure Pipelines (YAML) | Runs validate, deploy and build stages | Pipeline as code, reviewed in PRs, supports environments and approvals |
| Service connection (WIF) | Lets the pipeline log in to Azure | Workload identity federation means no secret to store or rotate |
| Variable groups | Hold per-environment settings and Key Vault secrets | One place to change values, reused across pipelines |
| Bicep | Declares VNet, Storage, ACR and AKS | Azure-native IaC, cleaner than ARM JSON, day-0 support for new API versions |
| Azure CLI (`az`) | Runs `bicep build`, `what-if`, `deployment group create`, `acr build`, `aks get-credentials` | Same commands work on your laptop and in the pipeline |
| ACR | Stores the container image | Private registry close to AKS, pulled with managed identity |
| AKS | Runs the web app | Managed Kubernetes, common in interviews and real projects |
| kubectl | Applies `deployment.yaml` and `service.yaml` | Standard Kubernetes CLI, preinstalled on Microsoft-hosted agents |

### Prerequisites

- An Azure subscription where you are **Owner** (or Contributor + Role Based Access Control Administrator). The pipeline creates role assignments (AcrPull, Network Contributor), which plain Contributor cannot do.
- An Azure DevOps organization (free at `https://dev.azure.com`). Free tier gives one Microsoft-hosted parallel job after you request the free grant.
- Local tools:

```bash
# Azure CLI 2.60+ (Linux example; see docs for macOS/Windows)
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
az version

# Bicep CLI (installed and managed by Azure CLI)
az bicep install
az bicep upgrade
az bicep version

# Azure DevOps CLI extension
az extension add --name azure-devops

# kubectl (optional locally; hosted agents already have it)
az aks install-cli

# git
git --version
```

- Cost warning: AKS nodes (2 x Standard_D2s_v5 per environment), the AKS public load balancer and public IP cost money every hour. Two environments can cost several dollars per day. Run the **Clean up** section when you finish.
- Check that your subscription has vCPU quota for the chosen VM size in your region (`az vm list-usage --location eastus -o table`).

### Folder structure

```text
bicep-web-aks/
|-- azure-pipelines.yml
|-- pipelines/
|   `-- templates/
|       `-- env-stages.yml
|-- infra/
|   |-- main.bicep
|   |-- main.dev.bicepparam
|   |-- main.prod.bicepparam
|   |-- bicepconfig.json
|   `-- modules/
|       |-- network.bicep
|       |-- storage.bicep
|       |-- acr.bicep
|       `-- aks.bicep
|-- app/
|   |-- Dockerfile
|   `-- index.html
`-- k8s/
    |-- namespace.yaml
    |-- deployment.yaml
    `-- service.yaml
```

### Step-by-step

#### Step 1: Create the Azure DevOps project and repository

Create the project and the Git repository from the CLI so the steps are repeatable. You can also do the same in the web portal.

```bash
ORG_URL="https://dev.azure.com/<org>"
PROJECT="bicep-web-aks"

az login
az devops configure --defaults organization="$ORG_URL"

az devops project create --name "$PROJECT" --visibility private --source-control git
az devops configure --defaults organization="$ORG_URL" project="$PROJECT"

# A default repo with the project name is created automatically.
az repos list --query "[].{name:name, url:remoteUrl}" -o table
```

What this does:

- `az devops configure --defaults` saves the org and project so you do not repeat `--organization` and `--project` on every command.
- `az devops project create` creates a private project that uses Git.
- `az repos list` shows the clone URL you need for the next step.

#### Step 2: Push your code to Azure Repos

Create the folder structure locally, then add Azure Repos as the remote and push.

```bash
mkdir -p bicep-web-aks/{pipelines/templates,infra/modules,app,k8s}
cd bicep-web-aks
git init -b main

# ... create the files from the next steps ...

git add .
git commit -m "Initial Bicep, app and pipeline"

git remote add origin https://<org>@dev.azure.com/<org>/bicep-web-aks/_git/bicep-web-aks
git push -u origin --all
```

What this does:

- `git init -b main` creates the repo with `main` as the default branch.
- `git remote add origin` points your local repo at Azure Repos.
- `git push -u origin --all` pushes all branches and sets upstream tracking. Git Credential Manager will open a browser to sign in. You can also create a Personal Access Token with **Code (Read & write)** scope if you prefer.

#### Step 3: Write the network module

The VNet has one subnet for AKS nodes and one reserved for private endpoints later. With Azure CNI Overlay, pods do not take VNet IPs, so the node subnet can be small.

`infra/modules/network.bicep`:

```bicep
@description('Azure region')
param location string

@description('VNet name')
param vnetName string

@description('VNet address space, for example 10.10.0.0/16')
param addressPrefix string

@description('Subnet for AKS nodes')
param aksSubnetPrefix string

@description('Subnet reserved for private endpoints')
param peSubnetPrefix string

param tags object = {}

var aksSubnetName = 'snet-aks'
var peSubnetName = 'snet-private-endpoints'

resource vnet 'Microsoft.Network/virtualNetworks@2024-01-01' = {
  name: vnetName
  location: location
  tags: tags
  properties: {
    addressSpace: {
      addressPrefixes: [
        addressPrefix
      ]
    }
    subnets: [
      {
        name: aksSubnetName
        properties: {
          addressPrefix: aksSubnetPrefix
        }
      }
      {
        name: peSubnetName
        properties: {
          addressPrefix: peSubnetPrefix
          privateEndpointNetworkPolicies: 'Enabled'
        }
      }
    ]
  }
}

output vnetName string = vnet.name
output vnetId string = vnet.id
output aksSubnetName string = aksSubnetName
output peSubnetName string = peSubnetName
```

What this does:

- Subnets are declared **inside** the VNet resource. If you declare them as separate child resources and also leave the `subnets` array empty, redeploys can try to delete subnets.
- `privateEndpointNetworkPolicies: 'Enabled'` lets NSGs and route tables apply to private endpoints later.
- Outputs pass the names to the AKS module, which also creates an implicit dependency (AKS waits for the VNet).

#### Step 4: Write the storage module with secure defaults

`infra/modules/storage.bicep`:

```bicep
param location string

@minLength(3)
@maxLength(24)
@description('Globally unique, lowercase letters and numbers only')
param storageAccountName string

@allowed([
  'Standard_LRS'
  'Standard_ZRS'
  'Standard_GRS'
])
param skuName string = 'Standard_LRS'

param tags object = {}

resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: storageAccountName
  location: location
  tags: tags
  kind: 'StorageV2'
  sku: {
    name: skuName
  }
  properties: {
    accessTier: 'Hot'
    supportsHttpsTrafficOnly: true
    minimumTlsVersion: 'TLS1_2'
    allowBlobPublicAccess: false
    allowSharedKeyAccess: false
    defaultToOAuthAuthentication: true
    publicNetworkAccess: 'Enabled'
    networkAcls: {
      defaultAction: 'Allow'
      bypass: 'AzureServices'
    }
  }
}

output storageAccountId string = storage.id
output storageAccountName string = storage.name
```

What this does:

- `supportsHttpsTrafficOnly: true` rejects plain HTTP.
- `minimumTlsVersion: 'TLS1_2'` blocks old TLS versions.
- `allowBlobPublicAccess: false` means no container can ever be made anonymous-public.
- `allowSharedKeyAccess: false` forces Entra ID (RBAC) auth instead of account keys. If a tool you use still needs keys, set this to `true` for the lab.
- `networkAcls.defaultAction: 'Allow'` keeps the lab simple. In a real setup you would set `Deny` and use the private endpoint subnet.

#### Step 5: Write the ACR module

`infra/modules/acr.bicep`:

```bicep
param location string

@minLength(5)
@maxLength(50)
@description('Globally unique, alphanumeric only')
param acrName string

param tags object = {}

resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: acrName
  location: location
  tags: tags
  sku: {
    name: 'Basic'
  }
  properties: {
    adminUserEnabled: false
    publicNetworkAccess: 'Enabled'
  }
}

output acrName string = acr.name
output acrLoginServer string = acr.properties.loginServer
```

What this does:

- `adminUserEnabled: false` disables the shared username/password. AKS pulls with its kubelet managed identity instead.
- `publicNetworkAccess: 'Enabled'` is needed because Microsoft-hosted agents push from the internet. Private ACR needs Premium SKU and self-hosted agents.

#### Step 6: Write the AKS module

The cluster uses a system-assigned identity for the control plane, a single system node pool in your subnet, Azure CNI Overlay, and has the OIDC issuer and workload identity turned on. It also grants AcrPull to the kubelet identity and Network Contributor on the subnet.

`infra/modules/aks.bicep`:

```bicep
param location string
param aksName string
param vnetName string
param aksSubnetName string
param acrName string

@minValue(1)
@maxValue(5)
param nodeCount int = 2

param nodeVmSize string = 'Standard_D2s_v5'
param tags object = {}

var acrPullRoleId = '7f951dda-4ed3-4680-a7ca-43fe172d538d'
var networkContributorRoleId = '4d97b98b-1d4f-4787-a291-c67834d212e7'

resource vnet 'Microsoft.Network/virtualNetworks@2024-01-01' existing = {
  name: vnetName
}

resource aksSubnet 'Microsoft.Network/virtualNetworks/subnets@2024-01-01' existing = {
  parent: vnet
  name: aksSubnetName
}

resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' existing = {
  name: acrName
}

resource aks 'Microsoft.ContainerService/managedClusters@2024-02-01' = {
  name: aksName
  location: location
  tags: tags
  identity: {
    type: 'SystemAssigned'
  }
  sku: {
    name: 'Base'
    tier: 'Free'
  }
  properties: {
    dnsPrefix: aksName
    agentPoolProfiles: [
      {
        name: 'system'
        mode: 'System'
        count: nodeCount
        vmSize: nodeVmSize
        osType: 'Linux'
        osSKU: 'AzureLinux'
        type: 'VirtualMachineScaleSets'
        vnetSubnetID: aksSubnet.id
      }
    ]
    networkProfile: {
      networkPlugin: 'azure'
      networkPluginMode: 'overlay'
      podCidr: '192.168.0.0/16'
      serviceCidr: '10.100.0.0/16'
      dnsServiceIP: '10.100.0.10'
      loadBalancerSku: 'standard'
    }
    oidcIssuerProfile: {
      enabled: true
    }
    securityProfile: {
      workloadIdentity: {
        enabled: true
      }
    }
  }
}

// Kubelet identity can pull images from ACR
resource acrPull 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(acr.id, aks.id, acrPullRoleId)
  scope: acr
  properties: {
    principalId: aks.properties.identityProfile.kubeletidentity.objectId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', acrPullRoleId)
  }
}

// Control plane identity can manage the node subnet (load balancers, IPs)
resource subnetNetworkContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(aksSubnet.id, aks.id, networkContributorRoleId)
  scope: aksSubnet
  properties: {
    principalId: aks.identity.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', networkContributorRoleId)
  }
}

output aksName string = aks.name
output oidcIssuerUrl string = aks.properties.oidcIssuerProfile.issuerURL
output kubeletObjectId string = aks.properties.identityProfile.kubeletidentity.objectId
```

What this does:

- `existing` resources reference the VNet, subnet and ACR created by other modules without redeploying them.
- `mode: 'System'` makes this the system node pool (runs CoreDNS, metrics-server and so on). For the lab, app pods also run here. In production you add a separate `User` pool and taint the system pool with `CriticalAddonsOnly=true:NoSchedule`.
- `networkPluginMode: 'overlay'` gives pods IPs from `podCidr` (not from the VNet). `serviceCidr` and `podCidr` must not overlap the VNet range.
- `oidcIssuerProfile` + `workloadIdentity` let pods get Entra ID tokens through federated credentials later, without secrets.
- The role assignment `name` uses `guid()` with values known at deployment start (`acr.id`, `aks.id`). The `principalId` can be a runtime value.
- `kubernetesVersion` is not set, so AKS uses the region default. Pin it in real projects and upgrade on purpose.

#### Step 7: Write main.bicep

`infra/main.bicep` wires the modules together.

```bicep
targetScope = 'resourceGroup'

@allowed([
  'dev'
  'prod'
])
param environmentName string

param location string = resourceGroup().location

param vnetAddressPrefix string
param aksSubnetPrefix string
param peSubnetPrefix string

param storageAccountName string
param storageSku string = 'Standard_LRS'

param acrName string
param aksName string
param aksNodeCount int = 2
param aksNodeVmSize string = 'Standard_D2s_v5'

param tags object = {}

var commonTags = union(tags, {
  environment: environmentName
  managedBy: 'bicep'
  project: 'bicep-web-aks'
})

module network 'modules/network.bicep' = {
  name: 'network-${environmentName}'
  params: {
    location: location
    vnetName: 'vnet-bicepweb-${environmentName}'
    addressPrefix: vnetAddressPrefix
    aksSubnetPrefix: aksSubnetPrefix
    peSubnetPrefix: peSubnetPrefix
    tags: commonTags
  }
}

module storage 'modules/storage.bicep' = {
  name: 'storage-${environmentName}'
  params: {
    location: location
    storageAccountName: storageAccountName
    skuName: storageSku
    tags: commonTags
  }
}

module acr 'modules/acr.bicep' = {
  name: 'acr-${environmentName}'
  params: {
    location: location
    acrName: acrName
    tags: commonTags
  }
}

module aks 'modules/aks.bicep' = {
  name: 'aks-${environmentName}'
  params: {
    location: location
    aksName: aksName
    vnetName: network.outputs.vnetName
    aksSubnetName: network.outputs.aksSubnetName
    acrName: acr.outputs.acrName
    nodeCount: aksNodeCount
    nodeVmSize: aksNodeVmSize
    tags: commonTags
  }
}

output acrLoginServer string = acr.outputs.acrLoginServer
output aksName string = aks.outputs.aksName
output storageAccountName string = storage.outputs.storageAccountName
output oidcIssuerUrl string = aks.outputs.oidcIssuerUrl
```

What this does:

- `targetScope = 'resourceGroup'` means you deploy with `az deployment group create`.
- Using module outputs (`network.outputs.vnetName`, `acr.outputs.acrName`) as inputs creates the correct deploy order automatically. No `dependsOn` needed.
- `union()` merges your tags with standard tags so every resource is labeled.

Optional `infra/bicepconfig.json` to make the linter stricter:

```json
{
  "analyzers": {
    "core": {
      "enabled": true,
      "rules": {
        "no-unused-params": { "level": "error" },
        "secure-secrets-in-params": { "level": "error" },
        "use-recent-api-versions": { "level": "warning" }
      }
    }
  }
}
```

#### Step 8: Write the .bicepparam files

The `.bicepparam` format is Bicep syntax, type-checked against `main.bicep` through the `using` line. Change the storage and ACR names to something globally unique.

`infra/main.dev.bicepparam`:

```bicep
using './main.bicep'

param environmentName = 'dev'
param vnetAddressPrefix = '10.10.0.0/16'
param aksSubnetPrefix = '10.10.0.0/22'
param peSubnetPrefix = '10.10.8.0/24'
param storageAccountName = 'stbicepweblabdev01'
param storageSku = 'Standard_LRS'
param acrName = 'acrbicepweblabdev01'
param aksName = 'aks-bicepweb-dev'
param aksNodeCount = 2
param aksNodeVmSize = 'Standard_D2s_v5'
param tags = {
  owner: 'platform-team'
  costCenter: 'lab'
}
```

`infra/main.prod.bicepparam`:

```bicep
using './main.bicep'

param environmentName = 'prod'
param vnetAddressPrefix = '10.20.0.0/16'
param aksSubnetPrefix = '10.20.0.0/22'
param peSubnetPrefix = '10.20.8.0/24'
param storageAccountName = 'stbicepweblabprod01'
param storageSku = 'Standard_ZRS'
param acrName = 'acrbicepweblabprod01'
param aksName = 'aks-bicepweb-prod'
param aksNodeCount = 3
param aksNodeVmSize = 'Standard_D2s_v5'
param tags = {
  owner: 'platform-team'
  costCenter: 'lab'
}
```

What this does:

- `using './main.bicep'` ties the file to the template, so a typo in a parameter name fails at build time, not at deploy time.
- Dev and prod use different address spaces, so you could peer them later without overlap.
- Prod uses ZRS storage and three nodes. Same template, different values: this is the main benefit of parameter files.

#### Step 9: Build, what-if and deploy from your laptop

Always test locally once before automating. This catches syntax and permission problems fast.

```bash
cd infra

# Compile and lint
az bicep build --file main.bicep --stdout > /dev/null
az bicep build-params --file main.dev.bicepparam --stdout > /dev/null

# Create the resource group
az group create --name rg-bicepweb-dev --location eastus

# Preview changes
az deployment group what-if \
  --resource-group rg-bicepweb-dev \
  --template-file main.bicep \
  --parameters main.dev.bicepparam

# Deploy
az deployment group create \
  --name bicepweb-dev-$(date +%Y%m%d%H%M) \
  --resource-group rg-bicepweb-dev \
  --template-file main.bicep \
  --parameters main.dev.bicepparam
```

What this does:

- `az bicep build` compiles Bicep to ARM JSON and runs the linter. `--stdout` avoids writing a `main.json` file into your repo.
- `az bicep build-params` checks the parameter file against the template.
- `what-if` shows Create / Modify / Delete / NoChange for each resource without changing anything. Read it like a `terraform plan`.
- `az deployment group create` runs an **incremental** deployment: resources not in the template are left alone.

#### Step 10: Create the service connection with workload identity federation

The pipeline needs an identity in Entra ID to deploy. Workload identity federation lets Azure DevOps exchange its own short-lived OIDC token for an Entra ID token, so there is no client secret.

**Option A: automatic (easiest)**

1. Project settings -> Service connections -> New service connection -> **Azure Resource Manager**.
2. Identity type: **App registration (automatic)**. Credential: **Workload identity federation**.
3. Scope level: **Subscription**, then choose the resource group `rg-bicepweb-dev`.
4. Name: `sc-azure-dev`. Do not tick "Grant access permission to all pipelines" (you will authorize the pipeline on first run).
5. Repeat for `rg-bicepweb-prod` with name `sc-azure-prod`.

Azure DevOps creates an app registration, adds the federated credential, and gives it **Contributor** on the chosen resource group.

**Option B: manual (when you cannot create app registrations, or you want a managed identity)**

```bash
# 1. Create a user-assigned managed identity to act as the pipeline identity
az group create --name rg-pipeline-identities --location eastus
az identity create --name id-ado-bicepweb-dev --resource-group rg-pipeline-identities

CLIENT_ID=$(az identity show -n id-ado-bicepweb-dev -g rg-pipeline-identities --query clientId -o tsv)
PRINCIPAL_ID=$(az identity show -n id-ado-bicepweb-dev -g rg-pipeline-identities --query principalId -o tsv)

# 2. In Azure DevOps: New service connection -> Azure Resource Manager ->
#    Identity type "Managed identity" (or "App registration or managed identity (manual)")
#    -> Workload identity federation. Fill subscription, client ID, tenant ID.
#    Azure DevOps then SHOWS you an Issuer and a Subject identifier. Copy them.

# 3. Add the federated credential using the exact values shown by Azure DevOps
az identity federated-credential create \
  --name ado-sc-azure-dev \
  --identity-name id-ado-bicepweb-dev \
  --resource-group rg-pipeline-identities \
  --issuer "<issuer-shown-in-azure-devops>" \
  --subject "<subject-identifier-shown-in-azure-devops>" \
  --audiences "api://AzureADTokenExchange"

# 4. Give the identity rights on the target resource group
RG_ID=$(az group show -n rg-bicepweb-dev --query id -o tsv)
az role assignment create --assignee-object-id "$PRINCIPAL_ID" --assignee-principal-type ServicePrincipal \
  --role "Contributor" --scope "$RG_ID"
az role assignment create --assignee-object-id "$PRINCIPAL_ID" --assignee-principal-type ServicePrincipal \
  --role "Role Based Access Control Administrator" --scope "$RG_ID"
```

What this does:

- The federated credential says: "trust tokens from this issuer, for this exact subject (this one service connection)". Nothing else can use it.
- Always copy the issuer and subject from the Azure DevOps screen. The format has changed over time (older connections used issuer `https://vstoken.dev.azure.com/<organization-id>` and subject `sc://<org>/<project>/<service-connection-name>`; newer ones use an Entra ID issuer).
- The audience is always `api://AzureADTokenExchange`.

**RBAC scope note**

- Scope each service connection to **one resource group**, not the whole subscription. A dev pipeline should not be able to touch prod.
- **Contributor** can create resources but **cannot create role assignments**. Our Bicep creates AcrPull and Network Contributor assignments, so the identity also needs **Role Based Access Control Administrator** (better: with a condition that limits which roles it can assign) or **User Access Administrator** on that resource group. With the automatic option, add this role yourself after creation.
- The resource group must exist before the service connection is scoped to it. Create `rg-bicepweb-prod` now with `az group create`.

#### Step 11: Create variable groups

Variable groups store values per environment. The pipeline loads the right group in each stage.

```bash
az pipelines variable-group create \
  --name dev-config \
  --authorize false \
  --variables resourceGroup=rg-bicepweb-dev location=eastus \
              aksName=aks-bicepweb-dev acrName=acrbicepweblabdev01 \
              paramFile=main.dev.bicepparam appNamespace=webapp

az pipelines variable-group create \
  --name prod-config \
  --authorize false \
  --variables resourceGroup=rg-bicepweb-prod location=eastus \
              aksName=aks-bicepweb-prod acrName=acrbicepweblabprod01 \
              paramFile=main.prod.bicepparam appNamespace=webapp
```

Key Vault-linked group (portal only):

1. Create a Key Vault and a secret, for example `app-api-key`.
2. Give the service connection identity **Key Vault Secrets User** on the vault (RBAC vault) or Get/List secret permissions (access policy vault).
3. Pipelines -> Library -> **+ Variable group** -> name `kv-dev-secrets` -> turn on **Link secrets from an Azure key vault as variables** -> pick `sc-azure-dev` and the vault -> **+ Add** the secrets you need.

What this does:

- Values like `$(resourceGroup)` resolve at runtime in each stage, so the same template works for dev and prod.
- `--authorize false` means each pipeline must be approved to use the group the first time. This is safer than "all pipelines".
- Key Vault secrets are fetched at the start of the job and are masked in logs. They are **not** automatically exposed as environment variables in scripts. You must map them with `env:` (see Q6).
- Keep the variable group names and the names in the `.bicepparam` files in sync. A later improvement is to read them from deployment outputs.

#### Step 12: Write the sample web app and Kubernetes manifests

`app/index.html`:

```html
<!doctype html>
<html><body><h1>Hello from AKS (__ENV__)</h1><p>Deployed by Azure Pipelines.</p></body></html>
```

`app/Dockerfile`:

```dockerfile
FROM nginxinc/nginx-unprivileged:1.27-alpine
ARG APP_ENV=dev
COPY index.html /usr/share/nginx/html/index.html
USER root
RUN sed -i "s/__ENV__/${APP_ENV}/" /usr/share/nginx/html/index.html
USER 101
EXPOSE 8080
```

`k8s/namespace.yaml`:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: webapp
```

`k8s/deployment.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: webapp
  namespace: webapp
  labels:
    app: webapp
spec:
  replicas: 2
  selector:
    matchLabels:
      app: webapp
  template:
    metadata:
      labels:
        app: webapp
    spec:
      containers:
        - name: webapp
          image: IMAGE_PLACEHOLDER
          ports:
            - containerPort: 8080
          resources:
            requests:
              cpu: 50m
              memory: 64Mi
            limits:
              memory: 128Mi
          readinessProbe:
            httpGet:
              path: /
              port: 8080
            initialDelaySeconds: 3
            periodSeconds: 5
          livenessProbe:
            httpGet:
              path: /
              port: 8080
            initialDelaySeconds: 10
            periodSeconds: 10
          securityContext:
            allowPrivilegeEscalation: false
            runAsNonRoot: true
```

`k8s/service.yaml`:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: webapp
  namespace: webapp
spec:
  type: LoadBalancer
  selector:
    app: webapp
  ports:
    - port: 80
      targetPort: 8080
```

What this does:

- `nginx-unprivileged` listens on 8080 and runs as non-root, which matches the `securityContext`.
- `IMAGE_PLACEHOLDER` is replaced by the pipeline with the real image and tag.
- The readiness probe stops traffic going to a pod until it answers. The `LoadBalancer` Service gets a public IP from Azure.

#### Step 13: Write the reusable stage template

One template holds DeployInfra, BuildApp and DeployApp. The main pipeline calls it twice, once per environment.

`pipelines/templates/env-stages.yml`:

```yaml
parameters:
  - name: envName
    type: string
  - name: serviceConnection
    type: string
  - name: variableGroup
    type: string
  - name: dependsOn
    type: string

stages:
  - stage: DeployInfra_${{ parameters.envName }}
    displayName: Deploy infra (${{ parameters.envName }})
    dependsOn: ${{ parameters.dependsOn }}
    condition: and(succeeded(), ne(variables['Build.Reason'], 'PullRequest'))
    variables:
      - group: ${{ parameters.variableGroup }}
    jobs:
      - deployment: DeployInfra
        displayName: Bicep deploy
        environment: ${{ parameters.envName }}
        strategy:
          runOnce:
            deploy:
              steps:
                - checkout: self
                - task: AzureCLI@2
                  displayName: What-if and deploy
                  inputs:
                    azureSubscription: ${{ parameters.serviceConnection }}
                    scriptType: bash
                    scriptLocation: inlineScript
                    workingDirectory: infra
                    inlineScript: |
                      set -euo pipefail
                      az group create --name "$(resourceGroup)" --location "$(location)" --output none
                      az deployment group what-if \
                        --resource-group "$(resourceGroup)" \
                        --template-file main.bicep \
                        --parameters "$(paramFile)"
                      az deployment group create \
                        --name "bicepweb-$(Build.BuildId)" \
                        --resource-group "$(resourceGroup)" \
                        --template-file main.bicep \
                        --parameters "$(paramFile)" \
                        --output table

  - stage: BuildApp_${{ parameters.envName }}
    displayName: Build image (${{ parameters.envName }})
    dependsOn: DeployInfra_${{ parameters.envName }}
    variables:
      - group: ${{ parameters.variableGroup }}
    jobs:
      - job: Build
        steps:
          - task: AzureCLI@2
            displayName: az acr build
            inputs:
              azureSubscription: ${{ parameters.serviceConnection }}
              scriptType: bash
              scriptLocation: inlineScript
              workingDirectory: app
              inlineScript: |
                set -euo pipefail
                az acr build \
                  --registry "$(acrName)" \
                  --image "webapp:$(Build.BuildId)" \
                  --build-arg APP_ENV=${{ parameters.envName }} \
                  .

  - stage: DeployApp_${{ parameters.envName }}
    displayName: Deploy app (${{ parameters.envName }})
    dependsOn: BuildApp_${{ parameters.envName }}
    variables:
      - group: ${{ parameters.variableGroup }}
    jobs:
      - deployment: DeployApp
        displayName: kubectl apply
        environment: ${{ parameters.envName }}
        strategy:
          runOnce:
            deploy:
              steps:
                - checkout: self
                - task: AzureCLI@2
                  displayName: Deploy manifests to AKS
                  inputs:
                    azureSubscription: ${{ parameters.serviceConnection }}
                    scriptType: bash
                    scriptLocation: inlineScript
                    inlineScript: |
                      set -euo pipefail
                      az aks get-credentials \
                        --resource-group "$(resourceGroup)" \
                        --name "$(aksName)" \
                        --overwrite-existing
                      IMAGE="$(acrName).azurecr.io/webapp:$(Build.BuildId)"
                      sed -i "s|IMAGE_PLACEHOLDER|${IMAGE}|" k8s/deployment.yaml
                      kubectl apply -f k8s/namespace.yaml
                      kubectl apply -f k8s/deployment.yaml -f k8s/service.yaml
                      kubectl rollout status deployment/webapp -n "$(appNamespace)" --timeout=180s
                      kubectl get svc webapp -n "$(appNamespace)" -o wide
```

What this does:

- `${{ parameters.x }}` is a **compile-time** template expression. `azureSubscription` must be known at compile time (so pipeline authorization can be checked), which is why the service connection is a template parameter and not a variable from the group.
- `$(resourceGroup)` is a **runtime macro** filled from the variable group of that stage.
- `deployment:` jobs target an **environment**. That is what gives you deployment history and lets approvals and checks pause the stage.
- Deployment jobs do **not** check out code automatically, so `- checkout: self` is required.
- `condition: ... ne(variables['Build.Reason'], 'PullRequest')` means PR validation runs only the Validate stage. The later stages depend on this one, so they are skipped too.
- `az acr build` builds the image in ACR itself, so the agent does not need Docker and nothing is pushed over the agent's network.
- `kubectl rollout status` makes the pipeline fail if pods never become ready.

Alternative for the build step with the Docker task (needs a **Docker Registry** service connection of type Azure Container Registry, which also supports workload identity federation):

```yaml
- task: Docker@2
  displayName: Build and push
  inputs:
    command: buildAndPush
    containerRegistry: sc-acr-dev
    repository: webapp
    dockerfile: app/Dockerfile
    buildContext: app
    tags: |
      $(Build.BuildId)
```

Alternative for the deploy step with the Kubernetes manifest task:

```yaml
- task: KubernetesManifest@1
  displayName: Deploy with KubernetesManifest
  inputs:
    action: deploy
    connectionType: azureResourceManager
    azureSubscriptionConnection: ${{ parameters.serviceConnection }}
    azureResourceGroup: $(resourceGroup)
    kubernetesCluster: $(aksName)
    namespace: webapp
    manifests: |
      k8s/deployment.yaml
      k8s/service.yaml
    containers: |
      $(acrName).azurecr.io/webapp:$(Build.BuildId)
```

With `KubernetesManifest@1`, keep the image in `deployment.yaml` as `acrbicepweblabdev01.azurecr.io/webapp` (any tag). The `containers` input replaces the image reference that matches the repository name.

#### Step 14: Write the main pipeline

`azure-pipelines.yml`:

```yaml
trigger:
  branches:
    include:
      - main
  paths:
    exclude:
      - README.md

# For Azure Repos, PR builds are driven by the branch policy, not a "pr:" block.

pool:
  vmImage: ubuntu-latest

stages:
  - stage: Validate
    displayName: Validate Bicep
    variables:
      - group: dev-config
    jobs:
      - job: Validate
        steps:
          - task: AzureCLI@2
            displayName: Bicep build and what-if (dev)
            inputs:
              azureSubscription: sc-azure-dev
              scriptType: bash
              scriptLocation: inlineScript
              workingDirectory: infra
              inlineScript: |
                set -euo pipefail
                az bicep install
                az bicep build --file main.bicep --stdout > /dev/null
                az bicep build-params --file main.dev.bicepparam --stdout > /dev/null
                az bicep build-params --file main.prod.bicepparam --stdout > /dev/null
                az deployment group what-if \
                  --resource-group "$(resourceGroup)" \
                  --template-file main.bicep \
                  --parameters "$(paramFile)"

  - template: pipelines/templates/env-stages.yml
    parameters:
      envName: dev
      serviceConnection: sc-azure-dev
      variableGroup: dev-config
      dependsOn: Validate

  - template: pipelines/templates/env-stages.yml
    parameters:
      envName: prod
      serviceConnection: sc-azure-prod
      variableGroup: prod-config
      dependsOn: DeployApp_dev
```

What this does:

- `trigger` runs the pipeline on every push to `main` (that is, after a PR is merged).
- The Validate stage compiles both parameter files and shows a what-if against dev. Reviewers can read the what-if in the PR build logs.
- `template:` with different parameters reuses the same three stages for dev and prod. Fixing a bug in the template fixes both environments.
- Prod starts only after `DeployApp_dev` succeeds, so a broken dev deploy blocks prod.

Register the pipeline:

```bash
az pipelines create \
  --name bicep-web-aks \
  --repository bicep-web-aks \
  --repository-type tfsgit \
  --branch main \
  --yml-path azure-pipelines.yml \
  --skip-first-run true
```

#### Step 15: Create environments and the prod approval

Environments are created automatically on first use, but create them first so you can add checks before anything deploys.

1. Pipelines -> **Environments** -> **New environment** -> name `dev`, resource **None**. Repeat for `prod`.
2. Open `prod` -> the three-dot menu -> **Approvals and checks** -> **+** -> **Approvals**.
3. Add yourself (or a group) as approver. Optional: set a timeout (for example 72 hours) and "Approvers can not approve their own runs" for real teams.
4. Optional extra checks on `prod`: **Business hours**, **Branch control** (only `refs/heads/main` can deploy), **Exclusive lock** (one deployment at a time).

What this does:

- **Environment**: a named target (dev, prod) that records which run deployed which commit.
- **Approval**: a person must click Approve before any stage with a deployment job targeting `prod` starts.
- **Checks** live on the resource (environment, service connection, variable group, agent pool), not in YAML. A developer cannot remove them by editing `azure-pipelines.yml`. That is the key security point.

#### Step 16: Protect main with a branch policy

Now no one can push directly to `main`; all changes go through a PR that must pass the pipeline.

```bash
REPO_ID=$(az repos show --repository bicep-web-aks --query id -o tsv)
PIPELINE_ID=$(az pipelines show --name bicep-web-aks --query id -o tsv)

az repos policy approver-count create \
  --repository-id "$REPO_ID" --branch main \
  --blocking true --enabled true \
  --minimum-approver-count 1 \
  --creator-vote-counts false \
  --allow-downvotes false \
  --reset-on-source-push true

az repos policy build create \
  --repository-id "$REPO_ID" --branch main \
  --blocking true --enabled true \
  --build-definition-id "$PIPELINE_ID" \
  --display-name "PR validation" \
  --manual-queue-only false \
  --queue-on-source-update-only true \
  --valid-duration 720
```

What this does:

- `approver-count` requires at least one reviewer who is not the author. `reset-on-source-push` clears approvals when new commits arrive.
- `build create` runs the pipeline on every PR to `main` (with `Build.Reason = PullRequest`, so only Validate runs). `valid-duration 720` means the result expires after 12 hours if `main` moves.
- In the portal the same settings are under Project settings -> Repositories -> bicep-web-aks -> Policies -> Branch policies -> main.

#### Step 17: Run it end to end

```bash
git checkout -b feature/first-deploy
git add .
git commit -m "Add pipeline and infra"
git push -u origin feature/first-deploy

az repos pr create --source-branch feature/first-deploy --target-branch main \
  --title "First deploy" --description "Bicep infra + AKS app"
```

Complete the PR after the validation build passes. The merge triggers the full run. On the first run, Azure DevOps asks you to **Permit** the pipeline to use the service connections, variable groups and environments. When the run reaches `DeployInfra_prod`, approve it.

### Verify it works

```bash
# Pipeline run status
az pipelines runs list --pipeline-ids "$PIPELINE_ID" --top 1 \
  --query "[0].{status:status,result:result}" -o table
# Expected: status completed, result succeeded

# Infra exists
az resource list -g rg-bicepweb-dev --query "[].{name:name,type:type}" -o table
# Expected: vnet-bicepweb-dev, stbicepweblabdev01, acrbicepweblabdev01, aks-bicepweb-dev, ...

# Storage secure settings
az storage account show -n stbicepweblabdev01 -g rg-bicepweb-dev \
  --query "{https:enableHttpsTrafficOnly,tls:minimumTlsVersion,publicBlob:allowBlobPublicAccess}"
# Expected: {"https": true, "publicBlob": false, "tls": "TLS1_2"}

# AKS features
az aks show -n aks-bicepweb-dev -g rg-bicepweb-dev \
  --query "{plugin:networkProfile.networkPlugin,mode:networkProfile.networkPluginMode,oidc:oidcIssuerProfile.enabled,wi:securityProfile.workloadIdentity.enabled}"
# Expected: {"mode": "overlay", "oidc": true, "plugin": "azure", "wi": true}

# Image in ACR
az acr repository show-tags --name acrbicepweblabdev01 --repository webapp -o table

# App running
az aks get-credentials -g rg-bicepweb-dev -n aks-bicepweb-dev --overwrite-existing
kubectl get pods -n webapp
# Expected: 2 pods, STATUS Running, READY 1/1
EXTERNAL_IP=$(kubectl get svc webapp -n webapp -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
curl -s "http://${EXTERNAL_IP}"
# Expected: <h1>Hello from AKS (dev)</h1>
```

In Azure DevOps, open Pipelines -> Environments -> `prod` and confirm the deployment history shows the run and who approved it.

### Common problems and fixes

| Problem | Likely cause | Fix |
| --- | --- | --- |
| `AuthorizationFailed ... Microsoft.Authorization/roleAssignments/write` | Service connection identity has only Contributor | Add Role Based Access Control Administrator (or User Access Administrator) on the resource group |
| `AADSTS700213: No matching federated identity record found` | Issuer or subject in the federated credential does not match | Copy the exact issuer and subject from the service connection page and recreate the credential |
| Run stuck with "This pipeline needs permission to access a resource" | First use of a service connection, environment or variable group | Click **View** -> **Permit** on the run page |
| `StorageAccountAlreadyTaken` or ACR name taken | Names are global | Change `storageAccountName` / `acrName` in the `.bicepparam` and variable group |
| `ErrImagePull` / `401 Unauthorized` in pods | AcrPull missing or not yet propagated for the kubelet identity | Check the role assignment on ACR; wait a few minutes; run `az aks check-acr -n <aks> -g <rg> --acr <acr>.azurecr.io` |
| AKS create fails with quota error | Not enough vCPU for the VM size in the region | Use a smaller size or request quota |
| Service `EXTERNAL-IP` stays `<pending>` | AKS identity cannot manage the subnet or LB | Confirm Network Contributor on `snet-aks`; check `kubectl describe svc webapp -n webapp` events |
| What-if shows unexpected deletes in subnets | Subnets managed both inline and as child resources, or changed in portal | Manage subnets only in the VNet `subnets` array |
| Key Vault secret empty in script | Secret variables are not mapped to env vars | Add `env: API_KEY: $(app-api-key)` to the step |
| Prod deployed without approval | Approval added to the wrong environment, or stage has no deployment job | Add the check on the `prod` environment; deploys must use `deployment:` jobs |

### Clean up

```bash
# Delete both environments' resources (AKS also deletes its MC_ node resource group)
az group delete --name rg-bicepweb-dev --yes --no-wait
az group delete --name rg-bicepweb-prod --yes --no-wait
az group delete --name rg-pipeline-identities --yes --no-wait

# Optional: remove Azure DevOps project (deletes repo, pipelines, service connections)
az devops project delete --id $(az devops project show --project bicep-web-aks --query id -o tsv) --yes

# If you used the automatic service connection, also delete its app registration in Entra ID
```

### Next improvements

- Build the image once and promote the same digest to prod (`az acr import` or a shared registry) instead of building per environment.
- Add a `User` node pool, taint the system pool, enable cluster autoscaler.
- Enable Microsoft Entra ID integration with Azure RBAC for Kubernetes and disable local accounts; use `kubelogin` in the pipeline.
- Lock down Storage and ACR with private endpoints in `snet-private-endpoints` and use self-hosted agents (Managed DevOps Pools) inside the VNet.
- Use a real workload identity: a user-assigned identity + federated credential + Kubernetes ServiceAccount so the app reads Storage without keys.
- Add PSRule for Azure or Checkov to the Validate stage, and post the what-if summary as a PR comment.
- Move to Helm or Kustomize overlays for per-environment manifests.
- Use Azure Verified Modules (AVM) from the Bicep public registry instead of hand-written modules.

### How to explain this project in an interview

> "This was a hands-on lab I built to practice end-to-end delivery on Azure DevOps. The code lives in Azure Repos with a branch policy on main, so every change needs a reviewer and a passing validation build. The pipeline logs in to Azure through a service connection that uses workload identity federation, so there is no client secret to rotate, and each environment's connection is scoped to its own resource group. Infrastructure is Bicep: a main file calling modules for the VNet, a storage account with secure defaults, ACR and an AKS cluster using Azure CNI Overlay with OIDC and workload identity enabled. The pipeline runs Bicep build and what-if first, then a reusable stage template deploys infra, builds the image with az acr build, and deploys to AKS with kubectl. The same template runs for dev and prod, with values from variable groups, and prod is protected by an approval check on the environment."

Points that impress interviewers:

- You know checks and approvals live on the environment, not in YAML, so developers cannot bypass them.
- You can explain why the pipeline identity needs a role-assignment permission beyond Contributor, and how to scope it.
- You use what-if as a "plan" step and understand incremental vs complete deployment modes.
- You know the difference between compile-time `${{ }}`, runtime `$( )` and `$[ ]` expressions in YAML.

## Interview Questions

<details><summary>Q1. [Basic] What is a service connection in Azure DevOps, and why prefer workload identity federation over a client secret?</summary>

**Answer:**

A service connection stores how a pipeline authenticates to an external system, such as an Azure subscription. With a client secret, the secret sits in Azure DevOps, expires (often after 1-2 years) and can leak. With workload identity federation, Azure DevOps issues a short-lived OIDC token for each job, and Entra ID trusts that token because of a federated credential that matches the issuer and the subject (the specific service connection). There is nothing to rotate and nothing to steal. Microsoft now recommends WIF as the default for Azure Resource Manager connections, and you can convert existing secret-based connections to WIF.

</details>

<details><summary>Q2. [Basic] What is the difference between a deployment job and a normal job in Azure Pipelines?</summary>

**Answer:**

A deployment job (`- deployment:`) targets an **environment** and uses a **strategy** (`runOnce`, `rolling`, `canary`) with lifecycle hooks such as `preDeploy`, `deploy`, `routeTraffic` and `postRouteTraffic`. Because it targets an environment, it records deployment history and is paused by the environment's approvals and checks. A normal job (`- job:`) has none of this. Two gotchas: deployment jobs do not run `checkout` automatically, and they download pipeline artifacts by default in `runOnce`.

</details>

<details><summary>Q3. [Intermediate] Where do approvals and checks live, and why does that matter?</summary>

**Answer:**

They are configured on protected **resources**: environments, service connections, variable groups, agent pools, secure files and repositories. They are not in the YAML file. That matters because a developer who can edit `azure-pipelines.yml` cannot delete the prod approval. Common checks are Approvals, Branch control (only `main` may use the prod service connection), Business hours, Exclusive lock, Required template (the pipeline must extend an approved template), and Invoke Azure Function / REST API for custom gates. Checks are evaluated when a stage that uses the resource is about to start.

</details>

<details><summary>Q4. [Intermediate] Explain <code>${{ }}</code>, <code>$( )</code> and <code>$[ ]</code> in Azure Pipelines YAML.</summary>

**Answer:**

- `${{ parameters.x }}` is a **template expression**, evaluated at compile time when the YAML is expanded. Use it for parameters, conditional insertion and anything that must be known before the run starts, such as `azureSubscription` or `environment`.
- `$(var)` is a **macro**, replaced at runtime just before a task runs. Variable group values use this.
- `$[ variables.x ]` is a **runtime expression**, evaluated at runtime and used in `condition:` and in variable definitions, for example to read output variables from another stage via `stageDependencies`.

A common mistake is putting `$(serviceConnectionName)` in `azureSubscription`; it fails because resource authorization needs the value at compile time.

</details>

<details><summary>Q5. [Intermediate] What does <code>az deployment group what-if</code> do, and what are its limits?</summary>

**Answer:**

It sends the template to Azure Resource Manager and returns the predicted change for each resource: Create, Delete (only in complete mode), Modify, NoChange, Ignore or Deploy. It changes nothing. Limits: it can show "noise" (properties that look changed but are not, for example defaults filled by the resource provider), it cannot always evaluate `reference()` values for resources that do not exist yet, and it does not detect data-plane changes. Use it as a review aid, like a plan, and store the output in the pipeline logs for approvers.

</details>

<details><summary>Q6. [Intermediate] A Key Vault-linked variable group is attached, but the script sees an empty value. Why? <em>(scenario)</em></summary>

**Answer:**

Secret variables, including all Key Vault-linked ones, are not mapped into environment variables automatically, to avoid leaking them to every process. Fix it by mapping explicitly:

```yaml
- bash: ./call-api.sh
  env:
    API_KEY: $(app-api-key)
```

Other causes: the service connection identity lacks **Key Vault Secrets User** (or Get/List in access policies), the secret was not added to the variable group's list, the secret is disabled or expired, or the Key Vault firewall blocks the Microsoft-hosted agent.

</details>

<details><summary>Q7. [Advanced] Your Bicep deploy fails with <code>AuthorizationFailed</code> on <code>roleAssignments/write</code>, even though the service connection is Contributor. What do you do? <em>(scenario)</em></summary>

**Answer:**

Contributor has a `NotActions` on `Microsoft.Authorization/*/Write`, so it cannot create role assignments. The template creates AcrPull and Network Contributor assignments, so the identity needs **Role Based Access Control Administrator** or **User Access Administrator** at the resource group scope. Best practice is Role Based Access Control Administrator with a **condition** that only allows assigning specific role IDs (AcrPull, Network Contributor) to service principals. Alternatives: a platform team pre-creates the role assignments, or you split identity setup into a separate, more privileged pipeline. Do not make the pipeline Owner of the subscription.

</details>

<details><summary>Q8. [Advanced] Why Azure CNI Overlay instead of classic Azure CNI or kubenet?</summary>

**Answer:**

Classic Azure CNI gives every pod an IP from the VNet subnet, which burns IP space fast and forces large subnets. Kubenet saves IPs but uses route tables, has limits (400 nodes), and is being retired. Azure CNI Overlay gives nodes VNet IPs but pods get IPs from a private overlay CIDR (`podCidr`), so subnets stay small, there is no route table to manage, and performance is close to classic CNI. Pods reach VNet resources through the node IP (SNAT). Choose classic CNI (or pod subnet mode) only if external systems must reach pods directly by IP.

</details>

<details><summary>Q9. [Advanced] How would you stop someone from deploying to prod from a feature branch? <em>(scenario)</em></summary>

**Answer:**

Use several layers. In YAML, put a condition on prod stages: `eq(variables['Build.SourceBranch'], 'refs/heads/main')`. Because YAML can be edited, also add a **Branch control** check on the `prod` environment and the `sc-azure-prod` service connection that allows only `refs/heads/main` and requires branch protection. Add an **Approval** check, and a **Required template** check so pipelines must extend your approved template. Finally, the branch policy on `main` means code only reaches `main` through a reviewed PR with a passing build.

</details>

<details><summary>Q10. [Intermediate] Why give AcrPull to the kubelet identity and not the cluster identity?</summary>

**Answer:**

AKS has two identities. The **control plane (cluster) identity** manages Azure resources such as load balancers, public IPs and the subnet; that is why it gets Network Contributor on the subnet. The **kubelet identity** is the one the nodes use when pulling images, so AcrPull must go to the kubelet identity (`identityProfile.kubeletidentity.objectId`). `az aks update --attach-acr` does the same assignment for you. Neither of these is the identity your app pods use; for that you use workload identity with a federated credential on a user-assigned managed identity.

</details>
