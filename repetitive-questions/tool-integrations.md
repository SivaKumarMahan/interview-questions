# Repetitive Interview Questions: Tool Integrations

> How the tools on the resume connect to each other: pipelines with Azure, Terraform, Bicep, AKS, and security scanners; AKS with ACR, Key Vault, and monitoring; applications with Application Insights; Azure with Splunk; Functions with Service Bus; and more. Each answer says what connects to what, how they log in, and a small working example.

Interviewers often ask "How did you connect X with Y?" They want three things:

1. **The flow:** what talks to what, in which order.
2. **The authentication:** how one tool proves who it is to the other. This is the part most people forget.
3. **One real detail:** a task name, a command, or a setting that shows you have done it.

## Integration map

| Area | Integration | Section |
| --- | --- | --- |
| Pipelines and Azure login | Azure DevOps, GitHub Actions, GitLab CI, Jenkins with Azure | [Part 1](#part-1-pipelines-logging-in-to-azure) |
| Pipelines and IaC | Terraform login to Azure; Azure DevOps, GitHub Actions, GitLab CI, Jenkins with Terraform/OpenTofu and Bicep | [Part 2](#part-2-pipelines-with-terraform-opentofu-and-bicep) |
| Pipelines and app hosting | Pipelines with Docker, ACR, Helm, and AKS; connecting to AKS (Entra ID, local accounts, private clusters); Jenkins with Kubernetes; App Service and Functions deploys | [Part 3](#part-3-pipelines-with-docker-acr-helm-aks-and-app-service) |
| Security in pipelines | SonarQube, Trivy, Checkov, commercial scanners, secret scanning, Azure Policy | [Part 4](#part-4-security-tools-in-pipelines) |
| Secrets and identity | Key Vault with AKS, App Service, Functions, Azure DevOps, Jenkins, Terraform; Managed Identity | [Part 5](#part-5-secrets-and-identity) |
| Kubernetes platform | AKS with ACR, Application Gateway, Azure Policy, PostgreSQL | [Part 6](#part-6-aks-platform-integrations) |
| Monitoring | Azure Monitor vs Application Insights vs Log Analytics; applications with Application Insights; AKS with Azure Monitor and Prometheus; Grafana; alerts to Teams; Splunk setup; Azure and AKS with Splunk; Prometheus, Grafana, and Splunk together | [Part 7](#part-7-monitoring-and-alerting) |
| Serverless and messaging | Functions with Service Bus, Storage, and Event Grid | [Part 8](#part-8-serverless-and-messaging) |
| Configuration and artifacts | Terraform with Ansible; Ansible with Azure; pipelines with Nexus and Azure Artifacts; Git with pipelines | [Part 9](#part-9-configuration-management-artifacts-and-git) |

## The one rule behind every integration

```text
Tool A wants to call Tool B
-> Tool A proves its identity (managed identity, OIDC token, service connection, or a token)
-> Tool B checks the permission (RBAC role, scope)
-> Tool A gets only the access it needs
```

Prefer, in this order:

1. **Managed identity** when the tool runs inside Azure (VM, AKS, App Service, Functions).
2. **Workload identity federation (OIDC)** when the tool runs outside Azure (GitHub Actions, GitLab CI, Azure DevOps hosted agents). No secret is stored anywhere.
3. **Service principal with a secret** only when nothing else works. Store the secret in Key Vault and rotate it.

---

# Part 1: Pipelines logging in to Azure

## How does Azure DevOps connect to Azure?

**Interviewer:** How does your Azure DevOps pipeline get permission to deploy to Azure?

**Candidate:**

Through an **Azure Resource Manager service connection** that uses **workload identity federation**. The pipeline gets a short-lived token from Entra ID at run time, so there is no client secret to store or rotate.

```text
Pipeline job starts
-> Azure DevOps issues an OIDC token for the service connection
-> Entra ID trusts that token (federated credential on the app registration or managed identity)
-> Entra ID returns an Azure access token
-> the task runs az / Terraform / Bicep with that token
```

### Setup steps

1. Project settings -> Service connections -> New -> Azure Resource Manager -> **Workload identity federation**.
2. Choose the subscription and resource group scope.
3. Give the identity only the roles it needs, for example **Contributor** on the app resource group, not Owner on the subscription.
4. Add **approvals and checks** on the service connection or on the Production environment.

### Example

```yaml
- task: AzureCLI@2
  displayName: Show the identity the pipeline uses
  inputs:
    azureSubscription: sc-azure-prod      # service connection name
    scriptType: bash
    scriptLocation: inlineScript
    inlineScript: |
      az account show --query "{subscription:name, user:user.name}" -o table
```

### Remember

- One service connection per environment (dev, prod). A dev pipeline should not be able to touch prod.
- If a task fails with `AuthorizationFailed`, read the action and scope in the error and add only that role.
- A service connection is just stored login details for an outside service. Azure is the most common type, but there are others: **Docker Registry** (ACR), **Kubernetes**, **GitHub**, **SonarQube**, **Generic** (URL and token), and marketplace ones like Snyk. The YAML only names the connection; the credential never appears in the pipeline.

## How does GitHub Actions connect to Azure?

**Interviewer:** How do you log in to Azure from GitHub Actions without storing a secret?

**Candidate:**

With **OpenID Connect (OIDC)**. I create an Entra ID app registration or a user-assigned managed identity, add a **federated credential** that trusts my repo and branch or environment, and use `azure/login`.

```text
Workflow runs
-> GitHub issues an OIDC token (repo, branch, environment are inside it)
-> Entra ID checks the federated credential matches
-> Entra ID returns an Azure token
-> az, Terraform, or Bicep commands run
```

### Example

```yaml
permissions:
  id-token: write     # needed to request the OIDC token
  contents: read

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: production
    steps:
      - uses: actions/checkout@v4
      - uses: azure/login@v2
        with:
          client-id: ${{ vars.AZURE_CLIENT_ID }}
          tenant-id: ${{ vars.AZURE_TENANT_ID }}
          subscription-id: ${{ vars.AZURE_SUBSCRIPTION_ID }}
      - run: az group list -o table
```

### Remember

- The federated credential **subject** must match exactly, for example `repo:my-org/my-repo:environment:production`. A mismatch gives `AADSTS70021: No matching federated identity record found`.
- Client ID, tenant ID, and subscription ID are not secrets. They can be repository variables.

## How does GitLab CI connect to Azure?

**Interviewer:** How does a GitLab pipeline log in to Azure?

**Candidate:**

The same OIDC idea. GitLab issues an ID token to the job with `id_tokens`. Entra ID trusts it through a federated credential whose subject is the GitLab project and branch.

```yaml
deploy:
  image: mcr.microsoft.com/azure-cli
  id_tokens:
    AZURE_JWT:
      aud: api://AzureADTokenExchange
  script:
    - az login --service-principal -u "$AZURE_CLIENT_ID" --tenant "$AZURE_TENANT_ID" --federated-token "$AZURE_JWT"
    - az account set --subscription "$AZURE_SUBSCRIPTION_ID"
    - az group list -o table
```

Federated credential subject example: `project_path:my-group/my-project:ref_type:branch:ref:main`.

## How does Jenkins connect to Azure?

**Interviewer:** Jenkins does not have a built-in Azure login. How did you handle it?

**Candidate:**

It depends on where Jenkins runs:

| Jenkins runs on | Login method |
| --- | --- |
| An Azure VM or VM Scale Set | **Managed identity** on the VM: `az login --identity`. No secret at all. |
| AKS (agents as Pods) | **AKS Workload Identity** on the agent Pod's service account. |
| Outside Azure | Service principal. The secret is stored in Jenkins Credentials (better: fetched from Key Vault) and never printed. |

```groovy
pipeline {
  agent { label 'azure-agent' }
  stages {
    stage('Azure login') {
      steps {
        // Agent VM has a user-assigned managed identity
        sh 'az login --identity --username "$AZURE_CLIENT_ID"'
        sh 'az account set --subscription "$AZURE_SUBSCRIPTION_ID"'
      }
    }
  }
}
```

With a service principal secret instead:

```groovy
withCredentials([usernamePassword(credentialsId: 'azure-sp',
                 usernameVariable: 'ARM_CLIENT_ID', passwordVariable: 'ARM_CLIENT_SECRET')]) {
  sh 'az login --service-principal -u "$ARM_CLIENT_ID" -p "$ARM_CLIENT_SECRET" --tenant "$ARM_TENANT_ID"'
}
```

---

# Part 2: Pipelines with Terraform, OpenTofu, and Bicep

## How do you authenticate Terraform to Azure?

**Interviewer:** How does Terraform log in to Azure?

**Candidate:**

Through the **azurerm provider**. The provider and the backend both read `ARM_*` environment variables, so the `.tf` code has no credentials. The login method depends on where Terraform runs:

| Where Terraform runs | Login method | What to set |
| --- | --- | --- |
| My laptop | Azure CLI session | `az login`, then `az account set`. Terraform uses the CLI token. |
| Azure DevOps | ARM service connection with **workload identity federation** | `ARM_USE_OIDC=true`, `ARM_OIDC_TOKEN`, `ARM_CLIENT_ID`, `ARM_TENANT_ID` (see the Azure DevOps example below) |
| GitHub Actions / GitLab CI | **OIDC** federated credential | `ARM_USE_OIDC=true` plus client, tenant, subscription IDs |
| Azure VM, VMSS, or AKS agent | **Managed identity** | `ARM_USE_MSI=true` (and `ARM_CLIENT_ID` for a user-assigned identity) |
| Old setups only | Service principal + client secret | `ARM_CLIENT_SECRET` from Key Vault or the CI secret store |

```hcl
provider "azurerm" {
  features {}
  # No secrets here. Login details come from ARM_* environment variables.
  # In azurerm 4.x the subscription ID is required: set it here or in ARM_SUBSCRIPTION_ID.
}
```

### Remember

- Prefer OIDC or managed identity. A client secret is a long-lived password that can leak and must be rotated.
- The identity needs a role on the target scope (for example **Contributor** on the resource group) and **Storage Blob Data Contributor** on the state container. If it creates role assignments, it also needs **Role Based Access Control Administrator** (or User Access Administrator), ideally with conditions.
- Never put credentials in the `provider` block or in `.tfvars`. They end up in Git.

## How does Terraform keep its state in Azure?

Every pipeline below uses the same **azurerm backend**. Learn this once.

```hcl
terraform {
  backend "azurerm" {
    resource_group_name  = "rg-tfstate"
    storage_account_name = "sttfstateprod01"
    container_name       = "tfstate"
    key                  = "app/prod.tfstate"
    use_azuread_auth     = true   # Entra ID login, no storage account key
  }
}
```

- State is a blob. **Locking** uses a blob lease, so two runs cannot change the same state at the same time.
- The pipeline identity needs **Storage Blob Data Contributor** on the container.
- Turn on blob versioning and soft delete so a broken state can be restored.
- OpenTofu uses the same backend block. Replace `terraform` with `tofu` in the commands.

## How do you integrate Azure DevOps with Terraform?

**Interviewer:** Walk me through your Terraform pipeline in Azure DevOps.

**Candidate:**

Two stages. **Plan** runs on every pull request and on main. **Apply** runs only on main, after a manual approval on the Production environment, and it applies the exact plan file that was reviewed.

```text
Pull request
-> terraform fmt -check, validate, Checkov
-> terraform plan (shown in the PR)
Merge to main
-> plan again, save tfplan as a pipeline artifact
-> approval on the "prod" environment
-> terraform apply tfplan
```

### Example

```yaml
stages:
- stage: Plan
  jobs:
  - job: plan
    steps:
    - task: AzureCLI@2
      inputs:
        azureSubscription: sc-azure-prod
        scriptType: bash
        scriptLocation: inlineScript
        addSpnToEnvironment: true          # exposes servicePrincipalId, idToken, tenantId
        inlineScript: |
          export ARM_CLIENT_ID=$servicePrincipalId
          export ARM_TENANT_ID=$tenantId
          export ARM_OIDC_TOKEN=$idToken
          export ARM_USE_OIDC=true
          export ARM_SUBSCRIPTION_ID=$(az account show --query id -o tsv)
          terraform init -input=false
          terraform plan -input=false -out=tfplan
    - publish: tfplan
      artifact: tfplan

- stage: Apply
  dependsOn: Plan
  condition: and(succeeded(), eq(variables['Build.SourceBranch'], 'refs/heads/main'))
  jobs:
  - deployment: apply
    environment: prod                       # approval is set on this environment
    strategy:
      runOnce:
        deploy:
          steps:
          - checkout: self
          - download: current
            artifact: tfplan
          # same AzureCLI@2 login block as above, then:
          # terraform init -input=false
          # terraform apply -input=false $(Pipeline.Workspace)/tfplan/tfplan
```

### Remember

- `addSpnToEnvironment: true` gives `idToken` only when the service connection uses workload identity federation.
- Apply the **saved plan file**, so what was approved is what runs.
- `terraform plan -detailed-exitcode` returns exit code **2** when there are changes. A scheduled pipeline can use it for **drift detection** and alert when someone changed Azure by hand.
- Instead of a script, you can use the **Terraform marketplace extension** tasks (`TerraformInstaller@1` and `TerraformTask@5` with `command: init/plan/apply` and `backendServiceArm`). Same flow, less shell code. A deployment job does not check out code automatically, so add `checkout: self` before `init` in the apply stage.
- For dev, QA, and prod, I reuse **one stage template** with parameters. Each environment has its own state key (`dev.tfstate`, `prod.tfstate`), its own `.tfvars`, and its own service connection. Only prod has an approval.

## How do you integrate GitHub Actions with Terraform?

**Interviewer:** How does your GitHub Actions workflow run Terraform?

**Candidate:**

OIDC login, then `hashicorp/setup-terraform`. The plan is posted to the pull request. Apply runs on main in a GitHub **environment** with required reviewers.

```yaml
permissions:
  id-token: write
  contents: read
  pull-requests: write

env:
  ARM_CLIENT_ID: ${{ vars.AZURE_CLIENT_ID }}
  ARM_TENANT_ID: ${{ vars.AZURE_TENANT_ID }}
  ARM_SUBSCRIPTION_ID: ${{ vars.AZURE_SUBSCRIPTION_ID }}
  ARM_USE_OIDC: true          # Terraform azurerm provider and backend read the GitHub token

jobs:
  plan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: hashicorp/setup-terraform@v3
      - run: terraform init -input=false
      - run: terraform fmt -check
      - run: terraform validate
      - run: terraform plan -input=false -out=tfplan
      - uses: actions/upload-artifact@v4
        with: { name: tfplan, path: tfplan }

  apply:
    needs: plan
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    environment: production      # required reviewers approve here
    steps:
      - uses: actions/checkout@v4
      - uses: hashicorp/setup-terraform@v3
      - uses: actions/download-artifact@v4
        with: { name: tfplan }
      - run: terraform init -input=false
      - run: terraform apply -input=false tfplan
```

### Remember

- With `ARM_USE_OIDC=true`, the provider requests the token itself. You do not need `azure/login` for Terraform, only for `az` commands.
- The apply job's federated credential subject is the **environment** (`environment:production`), so only that environment can reach prod.
- For OpenTofu, use `opentofu/setup-opentofu` and `tofu` commands.

## How do you integrate GitLab CI with Terraform or OpenTofu?

**Candidate:**

Same shape as the others: `id_tokens` for login, a plan job that saves the plan as an artifact, and a manual apply job on the protected main branch.

```yaml
stages: [validate, plan, apply]

default:
  image:
    name: ghcr.io/opentofu/opentofu:1.9
    entrypoint: [""]      # the image's entrypoint is tofu; GitLab needs a shell
  id_tokens:
    AZURE_JWT:
      aud: api://AzureADTokenExchange

variables:
  ARM_USE_OIDC: "true"
  ARM_CLIENT_ID: $AZURE_CLIENT_ID
  ARM_TENANT_ID: $AZURE_TENANT_ID
  ARM_SUBSCRIPTION_ID: $AZURE_SUBSCRIPTION_ID

before_script:
  - export ARM_OIDC_TOKEN="$AZURE_JWT"
  - tofu init -input=false

validate:
  stage: validate
  script:
    - tofu fmt -check
    - tofu validate

plan:
  stage: plan
  script:
    - tofu plan -input=false -out=tfplan
  artifacts:
    paths: [tfplan]

apply:
  stage: apply
  script:
    - tofu apply -input=false tfplan
  rules:
    - if: $CI_COMMIT_BRANCH == "main"
      when: manual          # someone clicks to approve
  environment: production
```

GitLab also has a built-in Terraform state backend, but on Azure I keep state in the azurerm backend so all tools share one place.

## How do you integrate Jenkins with Terraform?

**Candidate:**

A Declarative Pipeline with plan, an `input` approval step, and apply. Jenkins logs in to Azure with the agent VM's managed identity.

```groovy
pipeline {
  agent { label 'terraform' }
  environment {
    ARM_USE_MSI         = 'true'                   // use the agent VM's managed identity
    ARM_CLIENT_ID       = credentials('tf-msi-client-id')
    ARM_SUBSCRIPTION_ID = credentials('azure-subscription-id')
    ARM_TENANT_ID       = credentials('azure-tenant-id')
  }
  stages {
    stage('Init and validate') {
      steps {
        sh 'terraform init -input=false'
        sh 'terraform fmt -check && terraform validate'
      }
    }
    stage('Plan') {
      steps {
        sh 'terraform plan -input=false -out=tfplan'
        sh 'terraform show -no-color tfplan > plan.txt'
        archiveArtifacts artifacts: 'plan.txt'
      }
    }
    stage('Approve') {
      when { branch 'main' }
      steps {
        timeout(time: 30, unit: 'MINUTES') {
          input message: 'Apply this plan to production?', submitter: 'platform-leads'
        }
      }
    }
    stage('Apply') {
      when { branch 'main' }
      steps { sh 'terraform apply -input=false tfplan' }
    }
  }
}
```

For the backend with managed identity, add `use_msi = true` (and `client_id` for a user-assigned identity) in the azurerm backend block, or pass them with `-backend-config`.

## How do you integrate pipelines with Bicep?

**Interviewer:** How do you deploy Bicep from a pipeline?

**Candidate:**

With the Azure CLI. I run `what-if` first so reviewers see the changes, then `az deployment group create` with a `.bicepparam` file per environment.

```text
Pull request
-> az bicep build (lint and compile)
-> az deployment group what-if (show changes)
Merge to main
-> approval
-> az deployment group create
```

### Azure DevOps example

```yaml
- task: AzureCLI@2
  displayName: Bicep what-if
  inputs:
    azureSubscription: sc-azure-prod
    scriptType: bash
    scriptLocation: inlineScript
    inlineScript: |
      az bicep build --file main.bicep
      az deployment group what-if \
        --resource-group rg-app-prod \
        --template-file main.bicep \
        --parameters main.prod.bicepparam

- task: AzureCLI@2
  displayName: Bicep deploy
  inputs:
    azureSubscription: sc-azure-prod
    scriptType: bash
    scriptLocation: inlineScript
    inlineScript: |
      az deployment group create \
        --name "app-$(Build.BuildId)" \
        --resource-group rg-app-prod \
        --template-file main.bicep \
        --parameters main.prod.bicepparam
```

### GitHub Actions example

```yaml
- uses: azure/login@v2
  with:
    client-id: ${{ vars.AZURE_CLIENT_ID }}
    tenant-id: ${{ vars.AZURE_TENANT_ID }}
    subscription-id: ${{ vars.AZURE_SUBSCRIPTION_ID }}
- run: |
    az deployment group create \
      --resource-group rg-app-prod \
      --template-file main.bicep \
      --parameters main.prod.bicepparam
```

### Terraform vs Bicep in one line each

- **Bicep:** Azure only, no state file (Azure is the state), new Azure features on day one.
- **Terraform/OpenTofu:** many providers, needs a state file, plan shows exact changes, bigger module ecosystem.

## How do you integrate Terraform with Key Vault?

**Candidate:**

Terraform reads secrets from Key Vault with a data source instead of keeping them in `.tfvars` files.

```hcl
data "azurerm_key_vault" "kv" {
  name                = "kv-app-prod"
  resource_group_name = "rg-security-prod"
}

data "azurerm_key_vault_secret" "db_password" {
  name         = "postgres-admin-password"
  key_vault_id = data.azurerm_key_vault.kv.id
}

resource "azurerm_postgresql_flexible_server" "db" {
  # ...
  administrator_password = data.azurerm_key_vault_secret.db_password.value
}
```

The pipeline identity needs the **Key Vault Secrets User** role. Remember that the value still ends up in the **state file**, so state access must be restricted.

## How do you integrate Terraform with AKS and Helm?

**Candidate:**

Terraform creates the AKS cluster. For what runs inside the cluster, I keep a clear line:

- **Terraform:** AKS, node pools, ACR, networking, identities, role assignments.
- **Helm in the pipeline:** applications and most cluster add-ons.

Putting the cluster and its Helm releases in the **same** Terraform state causes problems: the Kubernetes and Helm providers need the cluster to exist before plan, so a cluster replacement can break the whole plan. If Terraform must install something like an ingress controller, I put it in a separate state that reads the cluster with a data source.

```hcl
resource "azurerm_kubernetes_cluster" "aks" {
  name                = "aks-app-prod"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  dns_prefix          = "aksappprod"
  oidc_issuer_enabled       = true
  workload_identity_enabled = true

  default_node_pool {
    name                 = "system"
    vm_size              = "Standard_D4s_v5"
    auto_scaling_enabled = true
    min_count            = 2
    max_count            = 4
  }

  identity { type = "SystemAssigned" }
}

# Let the cluster pull images from ACR
resource "azurerm_role_assignment" "acr_pull" {
  scope                = azurerm_container_registry.acr.id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_kubernetes_cluster.aks.kubelet_identity[0].object_id
}
```

---

# Part 3: Pipelines with Docker, ACR, Helm, AKS, and App Service

## The common container flow

Every CI tool below follows the same flow. Only the syntax changes.

```text
Build the image (Docker)
-> scan it (Trivy)
-> push it to ACR with a unique tag (Git commit SHA or build number)
-> deploy to AKS with Helm, using that tag
-> AKS pulls the image from ACR (AcrPull role on the kubelet identity)
-> check the rollout
```

**Build once, promote the same image.** The image tested in dev is the exact image that goes to prod. Only the Helm values change.

## How do you integrate Azure DevOps with Docker and ACR?

**Candidate:**

I create a **Docker Registry service connection** to ACR (it can use workload identity federation), then use the `Docker@2` task.

```yaml
- task: Docker@2
  displayName: Build and push
  inputs:
    containerRegistry: sc-acr-prod          # Docker Registry service connection
    repository: orders-api
    command: buildAndPush
    Dockerfile: src/Dockerfile
    tags: |
      $(Build.SourceVersion)
```

Another option is `az acr build`, which builds the image inside ACR, so the agent does not need Docker:

```bash
az acr build --registry myacrprod --image orders-api:$(Build.SourceVersion) src/
```

## How do you integrate GitHub Actions with ACR?

```yaml
- uses: azure/login@v2
  with:
    client-id: ${{ vars.AZURE_CLIENT_ID }}
    tenant-id: ${{ vars.AZURE_TENANT_ID }}
    subscription-id: ${{ vars.AZURE_SUBSCRIPTION_ID }}
- run: |
    az acr login --name myacrprod
    docker build -t myacrprod.azurecr.io/orders-api:${{ github.sha }} src/
    docker push myacrprod.azurecr.io/orders-api:${{ github.sha }}
```

The login identity needs the **AcrPush** role on the registry.

## How do you connect to AKS?

**Interviewer:** How do you connect to an AKS cluster, and how does it know who you are?

**Candidate:**

I log in to Azure, download the kubeconfig with `az aks get-credentials`, and use `kubectl`. On our clusters, login is through **Microsoft Entra ID**, so `kubectl` gets my Entra token through **kubelogin**.

```bash
az login
az account set --subscription "<subscription-id>"
az aks get-credentials -g rg-aks-prod -n aks-app-prod --overwrite-existing
kubelogin convert-kubeconfig -l azurecli      # reuse the az login token
kubectl get nodes
```

### Authentication vs authorization

```text
Authentication (who are you?)  -> Entra ID token, checked by the AKS API server
Authorization (what can you do?) -> Azure RBAC for Kubernetes, or Kubernetes RBAC (Role + RoleBinding to an Entra group)
```

- Wrong or missing login gives `401 Unauthorized`.
- Logged in but no role gives `Error from server (Forbidden)`. Then I fix the role, not the login.

### Local accounts vs Entra ID

| | Local accounts | Entra ID |
| --- | --- | --- |
| How | Certificate-based **cluster-admin** kubeconfig: `az aks get-credentials --admin` | Your own Entra user, group, or managed identity |
| Who is it in the audit log | A shared admin, nobody in particular | The real person or pipeline identity |
| Access control | All or nothing | Per namespace, through Azure RBAC or Kubernetes RBAC |

In production I **disable local accounts**, so nobody can bypass Entra ID with a shared admin certificate:

```bash
az aks update -g rg-aks-prod -n aks-app-prod --disable-local-accounts   # needs Entra ID integration turned on
```

Keep one Entra **admin group** (`--aad-admin-group-object-ids`) for break-glass access, with Privileged Identity Management if possible.

### If the cluster is private

The API server has only a private IP, so `kubectl` from the internet does not work. Options:

1. Run `kubectl` from a machine in the VNet or a peered VNet: a jump box through **Azure Bastion**, a VPN or ExpressRoute connection, or a **self-hosted pipeline agent** in the VNet.
2. Use **`az aks command invoke`**. Azure runs the command inside the cluster for you, so no network path is needed. Good for quick checks and emergencies, not for normal deploys.

```bash
az aks command invoke -g rg-aks-prod -n aks-app-prod --command "kubectl get pods -n orders"

# Send local files (for example manifests) with the command
az aks command invoke -g rg-aks-prod -n aks-app-prod \
  --command "kubectl apply -f deployment.yaml -n orders" --file deployment.yaml
```

### Remember

- Pipelines connect the same way, but with their own identity (service connection or managed identity) and `kubelogin convert-kubeconfig -l azurecli` or `-l msi`, never with a person's account.
- The private DNS zone of a private cluster must resolve from wherever `kubectl` runs. Most "cannot connect" problems on private clusters are DNS.

## How do you integrate pipelines with AKS?

**Interviewer:** How does your pipeline deploy to AKS?

**Candidate:**

The pipeline logs in to Azure, gets the cluster credentials, converts them for Entra ID login with `kubelogin`, and runs `helm upgrade --install`.

```text
az login (service connection or OIDC)
-> az aks get-credentials
-> kubelogin convert-kubeconfig -l azurecli
-> helm upgrade --install --wait --atomic
-> kubectl rollout status
```

### Azure DevOps example

```yaml
- task: AzureCLI@2
  displayName: Deploy to AKS with Helm
  inputs:
    azureSubscription: sc-azure-prod
    scriptType: bash
    scriptLocation: inlineScript
    inlineScript: |
      az aks get-credentials -g rg-aks-prod -n aks-app-prod --overwrite-existing
      kubelogin convert-kubeconfig -l azurecli
      helm upgrade --install orders-api ./charts/orders-api \
        --namespace orders --create-namespace \
        -f ./charts/orders-api/values-prod.yaml \
        --set image.repository=myacrprod.azurecr.io/orders-api \
        --set image.tag=$(Build.SourceVersion) \
        --wait --timeout 10m --atomic
      kubectl -n orders rollout status deploy/orders-api
```

### Remember

- `--atomic` rolls the release back automatically if the deploy fails or times out.
- The pipeline identity needs a Kubernetes role on the cluster. With **Azure RBAC for Kubernetes**, give **Azure Kubernetes Service RBAC Writer** scoped to the namespace, not cluster admin.
- Azure DevOps also has built-in tasks that take an ARM service connection plus the resource group and cluster name, and get the credentials for you: `KubernetesManifest@1` (plain YAML) and `HelmDeploy@1` (Helm). I use the CLI approach because it is the same in every CI tool, which makes it easy to explain and debug.

```yaml
- task: HelmDeploy@1
  inputs:
    connectionType: Azure Resource Manager
    azureSubscription: sc-azure-prod
    azureResourceGroup: rg-aks-prod
    kubernetesCluster: aks-app-prod
    namespace: orders
    command: upgrade
    chartType: FilePath
    chartPath: charts/orders-api
    releaseName: orders-api
    install: true
    overrideValues: image.tag=$(Build.SourceVersion)
```

- Two separate logins are involved: **pipeline -> AKS** (service connection) to deploy, and **AKS -> ACR** (AcrPull on the kubelet identity) to pull the image. The pipeline being able to push to ACR does not mean the cluster can pull.

## How do you integrate Jenkins with Kubernetes?

**Interviewer:** How did you integrate Jenkins with Kubernetes?

**Candidate:**

There are two separate integrations, and interviewers often mix them up:

1. **Jenkins agents run as Pods in Kubernetes** (the Kubernetes plugin). Each build gets a fresh Pod and the Pod is deleted after the build. No idle agent VMs.
2. **Jenkins deploys applications to Kubernetes** (kubectl or Helm from a pipeline stage).

### 1. Jenkins agents as Kubernetes Pods

```text
Build is triggered
-> Jenkins controller asks the Kubernetes API for a new Pod
-> the Pod starts with the containers the build needs (jnlp agent, azure-cli, helm)
-> the build runs inside the Pod
-> the Pod is deleted
```

Setup:

1. Install the **Kubernetes** plugin.
2. Manage Jenkins -> Clouds -> New cloud -> Kubernetes. Add the cluster URL, the namespace (for example `jenkins-agents`), and credentials. If the controller runs inside the same cluster, it can use its own service account.
3. Give the controller's service account a Role that can create and delete Pods in the agents namespace only.

```groovy
pipeline {
  agent {
    kubernetes {
      yaml '''
        apiVersion: v1
        kind: Pod
        metadata:
          labels:
            azure.workload.identity/use: "true"   # AKS Workload Identity injects an Azure token
        spec:
          serviceAccountName: jenkins-agent       # annotated with the managed identity client ID
          containers:
          - name: azcli
            image: mcr.microsoft.com/azure-cli:2.67.0
            command: ["sleep"]
            args: ["infinity"]
          - name: helm
            image: alpine/helm:3.16.4
            command: ["sleep"]
            args: ["infinity"]
      '''
    }
  }
  stages {
    stage('Build and push image') {
      steps {
        container('azcli') {
          sh '''
            az login --service-principal -u "$AZURE_CLIENT_ID" -t "$AZURE_TENANT_ID" \
              --federated-token "$(cat $AZURE_FEDERATED_TOKEN_FILE)"
            az acr build --registry myacrprod --image orders-api:$GIT_COMMIT .
          '''
        }
      }
    }
    stage('Deploy') {
      steps {
        container('helm') {
          sh '''
            helm upgrade --install orders-api ./charts/orders-api -n orders \
              --set image.tag=$GIT_COMMIT --wait --atomic
          '''
        }
      }
    }
  }
}
```

- `az acr build` builds the image inside ACR, so the agent Pod needs no Docker daemon, no privileged mode, and no host Docker socket. (Kaniko was the usual answer for this, but Google archived it in 2025.)
- The `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, and `AZURE_FEDERATED_TOKEN_FILE` variables are injected by AKS Workload Identity. The managed identity needs **AcrPush** on the registry.
- The `helm` container uses the Pod's Kubernetes service account, so `jenkins-agent` needs a RoleBinding in the `orders` namespace.

### 2. Jenkins deploying to a cluster from outside

If Jenkins runs on a VM, store a kubeconfig as a **Secret file** credential and use it only in the deploy stage:

```groovy
stage('Deploy to AKS') {
  steps {
    withCredentials([file(credentialsId: 'aks-prod-kubeconfig', variable: 'KUBECONFIG')]) {
      sh 'kubectl -n orders set image deploy/orders-api app=myacrprod.azurecr.io/orders-api:$GIT_COMMIT'
      sh 'kubectl -n orders rollout status deploy/orders-api --timeout=5m'
    }
  }
}
```

On Azure, a better option is the VM's managed identity: `az login --identity`, then `az aks get-credentials` and `kubelogin convert-kubeconfig -l msi`. Then there is no kubeconfig file to protect.

## How do you integrate Helm with ACR?

**Candidate:**

ACR stores Helm charts as **OCI artifacts**, so images and charts live in one registry with the same access control.

```bash
# Log in to ACR for Helm with a short-lived token
TOKEN=$(az acr login --name myacrprod --expose-token --output tsv --query accessToken)
helm registry login myacrprod.azurecr.io \
  --username 00000000-0000-0000-0000-000000000000 --password "$TOKEN"

# Package and push the chart
helm package ./charts/orders-api --version 1.4.0
helm push orders-api-1.4.0.tgz oci://myacrprod.azurecr.io/helm

# Install from ACR
helm upgrade --install orders-api oci://myacrprod.azurecr.io/helm/orders-api \
  --version 1.4.0 -n orders -f values-prod.yaml
```

The all-zeros user name is the fixed user name ACR expects when you log in with an access token.

## How do you deploy to App Service and Azure Functions from a pipeline?

**Interviewer:** How have you used Web Apps, App Service, and Azure Functions in your CI/CD?

**Candidate:**

Same idea as AKS: **build once, deploy the same package everywhere**. CI builds and tests the code and publishes a zip or JAR as an artifact. CD deploys that artifact to each environment through an ARM service connection. Only the app settings change per environment.

```text
Push to main
-> CI: build, unit tests, SonarQube, package (zip/JAR), publish artifact
-> Deploy to Dev  -> Deploy to QA -> approval on "prod" environment
-> Prod: deploy to the "staging" slot -> health check -> swap with production
-> check Application Insights for errors after the swap
```

### Azure DevOps example

```yaml
# Web App (App Service): deploy to the staging slot, then swap
- task: AzureWebApp@1
  inputs:
    azureSubscription: sc-azure-prod
    appType: webAppLinux
    appName: app-orders-prod
    deployToSlotOrASE: true
    resourceGroupName: rg-app-prod
    slotName: staging
    package: $(Pipeline.Workspace)/drop/orders-api.jar

- task: AzureAppServiceManage@0
  inputs:
    azureSubscription: sc-azure-prod
    Action: Swap Slots
    WebAppName: app-orders-prod
    ResourceGroupName: rg-app-prod
    SourceSlot: staging

# Function App
- task: AzureFunctionApp@2
  inputs:
    azureSubscription: sc-azure-prod
    appType: functionAppLinux
    appName: func-docs-prod
    package: $(Pipeline.Workspace)/drop/function.zip
```

In GitHub Actions the same steps are `azure/login` (OIDC), then `azure/webapps-deploy@v3` or `Azure/functions-action@v1`.

### Remember

- **Config stays out of the package.** App settings per environment, secrets as Key Vault references, so the same zip works in dev and prod.
- **Slots give zero downtime and easy rollback.** Warm up the staging slot, swap, and swap back if something breaks. Mark settings that must not move (like the slot's own connection strings) as **deployment slot settings**.
- If the app runs as a **container** on App Service, the pipeline pushes the image to ACR and updates the image tag. The app pulls with its managed identity (AcrPull, `acrUseManagedIdentityCreds`), not with the ACR admin user.
- The Function's code deploy does not change its **triggers**. The trigger (HTTP, timer, Service Bus, Blob) starts each run; the pipeline only ships new code and settings.

---

# Part 4: Security tools in pipelines

## Where each scanner fits

```text
Pull request
-> secret scan            (no passwords or keys in the code)
-> SonarQube              (code quality, bugs, code vulnerabilities, coverage)
-> dependency scan        (known CVEs in libraries)
-> Checkov                (misconfigurations in Terraform, Bicep, Dockerfile, Kubernetes YAML)
Build
-> Docker build
-> Trivy image scan       (CVEs in the OS packages and libraries inside the image)
-> push to ACR only if all gates pass
Deploy
-> Azure Policy           (Azure blocks non-compliant resources even if the pipeline missed them)
```

Each tool **fails the pipeline** when its gate fails. A scan that only writes a report does not stop anything.

## How do you integrate SonarQube with pipelines?

**Interviewer:** How did you integrate SonarQube, and how does the quality gate stop a bad build?

**Candidate:**

The pipeline runs the scanner, sends the results to the SonarQube server, then **waits for the quality gate** result. If the gate fails, the pipeline fails.

```text
Pipeline runs tests with coverage
-> scanner sends code and coverage to SonarQube
-> SonarQube checks the quality gate (for example: no new critical issues, coverage on new code >= 80%)
-> pipeline waits for the result
-> gate failed = pipeline fails, pull request cannot merge
```

### Azure DevOps

Install the SonarQube extension and create a **SonarQube service connection** with a token.

```yaml
- task: SonarQubePrepare@7
  inputs:
    SonarQube: sc-sonarqube
    scannerMode: cli
    configMode: manual
    cliProjectKey: orders-api
    cliSources: src
- script: dotnet test --collect:"XPlat Code Coverage"
- task: SonarQubeAnalyze@7
- task: SonarQubePublish@7
  inputs:
    pollingTimeoutSec: '300'
```

Order matters: **Prepare -> build and test -> Analyze -> Publish**. `SonarQubePrepare` must run **before** the build, because it sets up the scanner. For Maven or Gradle use `scannerMode: other` (the Maven/Gradle task runs the analysis); for .NET use `scannerMode: dotnet`; for everything else use `cli`.

To block the pull request, add the SonarQube result as a **status check** in the branch policy.

### Jenkins

Add the server under Manage Jenkins -> System -> SonarQube servers, and add a **webhook** in SonarQube that points to `https://<jenkins>/sonarqube-webhook/`. Without the webhook, `waitForQualityGate` waits until the timeout.

```groovy
stage('SonarQube') {
  steps {
    withSonarQubeEnv('sonarqube') {
      sh 'mvn -B verify sonar:sonar -Dsonar.projectKey=orders-api'
    }
  }
}
stage('Quality gate') {
  steps {
    timeout(time: 10, unit: 'MINUTES') {
      waitForQualityGate abortPipeline: true
    }
  }
}
```

### GitHub Actions and GitLab CI

```yaml
# GitHub Actions
- uses: SonarSource/sonarqube-scan-action@v5
  env:
    SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}
    SONAR_HOST_URL: ${{ vars.SONAR_HOST_URL }}
  with:
    args: -Dsonar.qualitygate.wait=true
```

```yaml
# GitLab CI
sonarqube:
  image: sonarsource/sonar-scanner-cli:latest
  script:
    - sonar-scanner -Dsonar.qualitygate.wait=true
  variables:
    SONAR_TOKEN: $SONAR_TOKEN
    SONAR_HOST_URL: $SONAR_HOST_URL
```

`sonar.qualitygate.wait=true` makes the scanner itself wait and fail when the gate fails.

## How do you integrate Trivy with pipelines?

**Interviewer:** How does Trivy stop a vulnerable image from reaching production?

**Candidate:**

Trivy scans the image after the build and **before the push**. `--exit-code 1` makes the step fail when it finds HIGH or CRITICAL issues, so the image never reaches ACR.

```bash
docker build -t myacrprod.azurecr.io/orders-api:$TAG .

trivy image \
  --severity HIGH,CRITICAL \
  --ignore-unfixed \
  --exit-code 1 \
  myacrprod.azurecr.io/orders-api:$TAG

docker push myacrprod.azurecr.io/orders-api:$TAG
```

- `--ignore-unfixed` skips CVEs that have no fixed version yet, so the team is not blocked by things they cannot fix.
- Accepted risks go in a `.trivyignore` file with the CVE ID, a reason, and an expiry date, reviewed in a pull request.
- Trivy can also scan the repository (`trivy fs .`) for vulnerable dependencies and secrets, and IaC files (`trivy config .`).
- Write a report for the pipeline: `--format sarif -o trivy.sarif` (GitHub code scanning) or `--format template --template "@contrib/junit.tpl"` (Azure DevOps and GitLab test results).

The same commands work in every CI tool. Only the step syntax changes.

### Azure DevOps example

Trivy runs from its official image (pinned version), so nothing is installed on the agent.

```yaml
- task: Cache@2                       # reuse the vulnerability DB between runs
  inputs:
    key: trivy-db | "$(Agent.OS)"
    path: $(Pipeline.Workspace)/.trivycache

- script: |
    docker run --rm \
      -v /var/run/docker.sock:/var/run/docker.sock \
      -v $(Pipeline.Workspace)/.trivycache:/root/.cache/trivy \
      -v $(Build.SourcesDirectory):/out \
      aquasec/trivy:0.58.1 image \
        --severity HIGH,CRITICAL --ignore-unfixed --exit-code 1 \
        --format template --template "@contrib/junit.tpl" -o /out/trivy-junit.xml \
        myacrprod.azurecr.io/orders-api:$(Build.SourceVersion)
  displayName: Trivy image scan (before push)

- task: PublishTestResults@2           # findings show in the Tests tab
  condition: always()
  inputs:
    testResultsFormat: JUnit
    testResultsFiles: trivy-junit.xml
```

- **Pin the Trivy version** (image tag or digest), never `latest`. Security tools are supply-chain targets too.
- The Docker socket mount lets Trivy scan the image that was just built on the agent, before it is pushed.
- To scan an image that is already in ACR, Trivy uses the Docker login, so run `az acr login` first.
- Scanning at build time is not enough. New CVEs appear every day, so I also rescan what is running: **Defender for Containers** scans ACR and the cluster, or the **Trivy Operator** scans workloads inside AKS.

## How do you integrate Checkov with Terraform and Bicep?

**Interviewer:** How do you stop insecure infrastructure code from being deployed?

**Candidate:**

Checkov scans the IaC in the pull request. It finds problems such as a public storage account, a missing NSG, or Key Vault without purge protection, and fails the pipeline.

```bash
# Scan Terraform source
checkov -d infra/ --framework terraform --quiet --compact

# Scan the Terraform plan (sees the final values after variables and modules)
terraform plan -out=tfplan
terraform show -json tfplan > tfplan.json
checkov -f tfplan.json --framework terraform_plan

# Scan Bicep
checkov -d bicep/ --framework bicep

# Scan Dockerfiles and Kubernetes manifests
checkov -d . --framework dockerfile,kubernetes,helm
```

- Scanning the **plan** is more accurate than scanning the source, because values from variables and modules are resolved.
- To accept a finding, add a comment with the reason next to the resource:

```hcl
resource "azurerm_storage_account" "logs" {
  #checkov:skip=CKV_AZURE_33:Queue logging not needed, this account has no queues
  # ...
}
```

- Output for the pipeline UI: `-o junitxml` or `-o sarif`.

## How do commercial scanners plug into pipelines?

**Interviewer:** Instead of SonarQube and Trivy, which commercial tools could you use, and how do you integrate them?

**Candidate:**

I group them by the **type of check**, because that tells you where they go in the pipeline:

| Check | Open source I used | Commercial options |
| --- | --- | --- |
| SAST (our code) | SonarQube | Checkmarx One, Veracode, Coverity, GitHub Advanced Security (CodeQL) |
| SCA (libraries) | Trivy fs, OWASP Dependency-Check | Snyk Open Source, Mend.io, Black Duck, JFrog Xray |
| Container image | Trivy | Snyk Container, Prisma Cloud, Aqua, JFrog Xray, Defender for Containers |
| IaC | Checkov, Trivy config | Prisma Cloud (Checkov's commercial version), Snyk IaC, Wiz |
| DAST (running app) | OWASP ZAP | Veracode DAST, Invicti, Burp Suite Enterprise |

The integration pattern is always the same:

```text
Install the marketplace extension or CLI
-> create a service connection (or Key Vault secret) with the tool's API token
-> add the scan task in the right stage
-> set a severity threshold and fail the build when it is crossed
-> results go to the tool's central dashboard
```

```yaml
# Snyk in Azure DevOps
- task: SnykSecurityScan@1
  inputs:
    serviceConnectionEndpoint: sc-snyk
    testType: container
    dockerImageName: myacrprod.azurecr.io/orders-api:$(Build.SourceVersion)
    severityThreshold: high
    failOnIssues: true

# GitHub Advanced Security for Azure DevOps
- task: AdvancedSecurity-Codeql-Init@1
  inputs:
    languages: java
- task: AdvancedSecurity-Codeql-Autobuild@1
- task: AdvancedSecurity-Dependency-Scanning@1
- task: AdvancedSecurity-Codeql-Analyze@1
```

### Remember

- These are not one-to-one swaps. SonarQube is mostly **code quality** (bugs, smells, coverage); Checkmarx and Veracode are mostly **security**. Many teams keep SonarQube and add a commercial security tool.
- What you pay for: one dashboard across all projects, central policies, support, and reports for audits.
- Only claim hands-on experience with the tools you really used. Say the others are tools you know how to plug in.

## How do you integrate secret scanning with pipelines and Git?

**Candidate:**

Two layers:

1. **Block the push:** GitHub push protection, GitLab secret push protection, or GitHub Advanced Security for Azure DevOps stop a commit that contains a secret.
2. **Scan in the pipeline:** a scanner such as Gitleaks or `trivy fs --scanners secret .` fails the build if a secret is found.

```bash
gitleaks detect --source . --redact --exit-code 1
```

If a secret does leak, deleting the commit is not enough. **Rotate the secret first**, because it is already in the Git history and maybe in clones and logs.

## How do you integrate Azure Policy with your pipelines?

**Interviewer:** Your pipelines already have Checkov. Why also Azure Policy?

**Candidate:**

Checkov checks code **before** deploy, only for code that goes through the pipeline. Azure Policy checks **every** request to Azure, including portal clicks and scripts. It is the last safety net.

```text
Pipeline deploys Terraform/Bicep
-> Azure Resource Manager receives the request
-> Azure Policy evaluates it
-> effect: Deny (request fails), Audit (allowed but marked non-compliant), Modify or DeployIfNotExists (fixes it)
```

Example: assign the built-in policy that denies storage accounts with public network access.

```bash
az policy assignment create \
  --name deny-public-storage \
  --scope /subscriptions/<sub-id>/resourceGroups/rg-app-prod \
  --policy "<policy-definition-id>" \
  --params '{"effect": {"value": "Deny"}}'
```

- Roll out new policies with **Audit** first, fix what is non-compliant, then switch to **Deny**.
- When a deploy fails with `RequestDisallowedByPolicy`, the error names the policy assignment. Fix the code, or ask for an exemption with a reason and an expiry date.
- Policies can be kept as code (Bicep or Terraform) and deployed by a pipeline, like everything else.

---

# Part 5: Secrets and identity

## How does an application use a Managed Identity to reach other Azure services?

**Interviewer:** How do your applications connect to Storage, Key Vault, or Service Bus without a password?

**Candidate:**

The app runs with a **managed identity**. I give that identity an RBAC role on the target resource. In code, the Azure SDK's `DefaultAzureCredential` finds the identity automatically.

```text
App (App Service, Function, VM, or AKS Pod)
-> asks the local identity endpoint for a token
-> Entra ID returns a token for the managed identity
-> app calls Storage / Key Vault / Service Bus with the token
-> the service checks the RBAC role
```

```python
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient

credential = DefaultAzureCredential()   # managed identity in Azure, az login on a laptop
blob = BlobServiceClient("https://stdocsprod.blob.core.windows.net", credential=credential)
```

The common scenario "keep the database connection string safe" is the same flow with Key Vault in the middle:

```python
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

kv = SecretClient("https://kv-app-prod.vault.azure.net", DefaultAzureCredential())
conn_str = kv.get_secret("postgres-connection-string").value   # read at startup, cached, refreshed on rotation
```

On App Service I do not even need this code: a Key Vault reference in the app settings does it (see below). The best answer goes one step further: with **Entra ID login to PostgreSQL**, the managed identity's token is the password, so there is no connection-string secret left to protect.

Common roles:

| Target | Role |
| --- | --- |
| Key Vault secrets | Key Vault Secrets User |
| Blob Storage | Storage Blob Data Reader / Contributor |
| Service Bus | Azure Service Bus Data Sender / Receiver |
| ACR | AcrPull / AcrPush |
| PostgreSQL | Entra ID admin, or a database role mapped to the identity |

- **System-assigned:** lives and dies with the resource. **User-assigned:** a separate resource that can be shared and created before the app.
- Data-plane roles (like Storage Blob Data Reader) are different from management roles (like Contributor). Contributor alone cannot read blob data with Entra ID login.

## How do you integrate AKS with Key Vault?

**Interviewer:** How do Pods in AKS read secrets from Key Vault?

**Candidate:**

With the **Key Vault Secrets Provider** add-on (Secrets Store CSI driver) and **AKS Workload Identity**. The secret is mounted into the Pod as a file, and can also be synced to a Kubernetes Secret for environment variables.

```text
Pod starts with a service account
-> the service account is linked to a managed identity (federated credential)
-> the CSI driver gets a token for that identity
-> the CSI driver reads the secret from Key Vault
-> the secret is mounted as a file in the Pod
```

### Setup

```bash
# 1. Turn on the add-on, OIDC issuer, and Workload Identity
az aks enable-addons -g rg-aks-prod -n aks-app-prod --addons azure-keyvault-secrets-provider
az aks update -g rg-aks-prod -n aks-app-prod --enable-oidc-issuer --enable-workload-identity

# 2. Create an identity and let it read secrets
az identity create -g rg-aks-prod -n id-orders-api
az role assignment create --role "Key Vault Secrets User" \
  --assignee "<identity-principal-id>" --scope "<key-vault-resource-id>"

# 3. Trust the Kubernetes service account
ISSUER=$(az aks show -g rg-aks-prod -n aks-app-prod --query oidcIssuerProfile.issuerUrl -o tsv)
az identity federated-credential create -g rg-aks-prod --identity-name id-orders-api \
  --name orders-api-sa --issuer "$ISSUER" \
  --subject system:serviceaccount:orders:orders-api \
  --audience api://AzureADTokenExchange
```

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: orders-api
  namespace: orders
  annotations:
    azure.workload.identity/client-id: "<identity-client-id>"
---
apiVersion: secrets-store.csi.x-k8s.io/v1
kind: SecretProviderClass
metadata:
  name: orders-api-kv
  namespace: orders
spec:
  provider: azure
  parameters:
    clientID: "<identity-client-id>"
    keyvaultName: kv-app-prod
    tenantId: "<tenant-id>"
    objects: |
      array:
        - |
          objectName: postgres-password
          objectType: secret
```

In the Deployment: add the label `azure.workload.identity/use: "true"` to the Pod template, set `serviceAccountName: orders-api`, and mount a CSI volume with `secretProviderClass: orders-api-kv`.

### Remember

- The secret is read when the Pod **starts**. Turn on rotation (`--enable-secret-rotation`) and make the app re-read the file, or restart the Pods after a rotation.
- If the app needs an **environment variable**, add `secretObjects` to the `SecretProviderClass`. The driver then also creates a Kubernetes Secret (it exists only while a Pod mounts the volume). Environment variables change only after a Pod restart, and the value is now also in etcd, so the mounted file is better.
- If the secret cannot be read, the Pod stays in **`ContainerCreating`** and `kubectl describe pod` shows the mount error. Check the role, the federated credential subject (namespace and service account name), and the Key Vault name.
- If Key Vault has public access turned off, it needs a private endpoint and the `privatelink.vaultcore.azure.net` DNS zone linked to the AKS VNet.
- Workload Identity replaced the old **AAD Pod Identity**, which is retired.

## How do you integrate App Service and Azure Functions with Key Vault?

**Candidate:**

With **Key Vault references** in app settings. The app reads a normal environment variable; App Service fetches the value from Key Vault using the app's managed identity.

```text
App setting:  DB_PASSWORD = @Microsoft.KeyVault(SecretUri=https://kv-app-prod.vault.azure.net/secrets/postgres-password/)
```

```bash
az webapp config appsettings set -g rg-app-prod -n app-orders-prod --settings \
  "DB_PASSWORD=@Microsoft.KeyVault(VaultName=kv-app-prod;SecretName=postgres-password)"
```

- The app's managed identity needs **Key Vault Secrets User**.
- If the reference fails, the portal shows the setting with a red error and the app gets the literal `@Microsoft.KeyVault(...)` text. Check the identity, the role, and Key Vault networking.
- With no version in the URI, App Service picks up a new secret version within about a day, or right away after a restart.

## How do you integrate Azure DevOps with Key Vault?

**Candidate:**

Two ways:

1. **Variable group linked to Key Vault:** Library -> Variable group -> "Link secrets from an Azure key vault". Pipelines read the secrets as variables, and they are masked in logs.
2. **`AzureKeyVault@2` task:** fetches selected secrets at run time.

```yaml
- task: AzureKeyVault@2
  inputs:
    azureSubscription: sc-azure-prod
    KeyVaultName: kv-app-prod
    SecretsFilter: 'postgres-password,sonar-token'
    RunAsPreJob: false
- script: ./migrate.sh
  env:
    DB_PASSWORD: $(postgres-password)     # secrets must be mapped into env explicitly
```

Secret variables are not passed to scripts automatically. Map them with `env:`, as above.

In GitHub Actions, the same idea is `azure/login` followed by `az keyvault secret show`, and then `::add-mask::` so the value is hidden in logs.

## How do you integrate Jenkins with Key Vault?

**Interviewer:** Where do your Jenkins pipelines keep their secrets?

**Candidate:**

Never in the Jenkinsfile or Git. Small, Jenkins-only secrets go in the **Jenkins Credentials** store and are used with `withCredentials`, which masks them in the console log. Production secrets stay in **Key Vault**, and Jenkins reads them at run time with its own Azure identity.

```text
Jenkins agent (Azure VM with managed identity, or AKS Pod with Workload Identity)
-> gets an Azure token (no secret stored in Jenkins)
-> reads the secret from Key Vault (Key Vault Secrets User role)
-> uses it in one stage, masked in the log
```

Two ways to do it:

```groovy
// 1. Azure Key Vault plugin: Key Vault URL and an Azure credential (for example
//    a managed identity credential) are set once under Manage Jenkins
withAzureKeyvault([[secretType: 'Secret', name: 'postgres-password', envVariable: 'DB_PASSWORD']]) {
  sh './migrate.sh'
}

// 2. Plain Azure CLI with the agent's managed identity
sh '''
  az login --identity --username "$AZURE_CLIENT_ID" > /dev/null
  DB_PASSWORD=$(az keyvault secret show --vault-name kv-app-prod -n postgres-password --query value -o tsv)
  ./migrate.sh
'''
```

### Remember

- With the plain CLI, Jenkins does not know the value, so it **cannot mask it**. Do not `echo` it and do not use `set -x`. The plugin masks values for you.
- The Key Vault plugin can also show Key Vault secrets as normal Jenkins credentials, so existing `withCredentials` code keeps working.
- Jenkins Credentials are encrypted with keys in `$JENKINS_HOME/secrets`. Anyone with admin access or a full backup of Jenkins home can decrypt them, which is one more reason to keep the important secrets in Key Vault.

---

# Part 6: AKS platform integrations

## How do you integrate AKS with ACR?

**Interviewer:** How does AKS pull images from a private ACR?

**Candidate:**

I attach the registry to the cluster. That gives the cluster's **kubelet identity** the **AcrPull** role on the registry. No image pull secret is needed.

```bash
az aks update -g rg-aks-prod -n aks-app-prod --attach-acr myacrprod

# Check that the cluster can pull
az aks check-acr -g rg-aks-prod -n aks-app-prod --acr myacrprod.azurecr.io
```

If a Pod shows `ImagePullBackOff` with `401 Unauthorized`, check the AcrPull role. If it shows a network or `403` error, check ACR network rules or the private endpoint DNS (`privatelink.azurecr.io`).

## How do you integrate AKS with Application Gateway?

**Interviewer:** How does traffic from the internet reach your Pods?

**Candidate:**

Through **Application Gateway with WAF** in front of AKS. The **Application Gateway Ingress Controller (AGIC)** watches Kubernetes Ingress objects and updates the Application Gateway configuration to send traffic straight to Pod IPs.

```text
User
-> Application Gateway (public IP, TLS, WAF rules)
-> AGIC turned the Ingress rules into listeners, rules, and backend pools
-> Pod IPs in AKS
```

```bash
az aks enable-addons -g rg-aks-prod -n aks-app-prod \
  --addons ingress-appgw --appgw-id "<application-gateway-resource-id>"
```

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: orders-api
  namespace: orders
  annotations:
    appgw.ingress.kubernetes.io/ssl-redirect: "true"
    appgw.ingress.kubernetes.io/health-probe-path: /healthz
spec:
  ingressClassName: azure-application-gateway
  tls:
  - hosts: [api.example.com]
    secretName: api-tls
  rules:
  - host: api.example.com
    http:
      paths:
      - path: /orders
        pathType: Prefix
        backend:
          service:
            name: orders-api
            port:
              number: 80
```

- The Application Gateway needs a network path to the Pod IPs (same VNet or peered VNets).
- Microsoft's newer option is **Application Gateway for Containers**, which uses the Kubernetes Gateway API. Know the name, and that AGIC is the older, widely used option.
- WAF runs in **Detection** mode first, then **Prevention** after you tune false positives.

## How do you integrate AKS with Azure Policy?

**Candidate:**

The **Azure Policy add-on** installs Gatekeeper in the cluster. Policies assigned in Azure become admission rules in Kubernetes.

```bash
az aks enable-addons -g rg-aks-prod -n aks-app-prod --addons azure-policy
```

Examples of what it blocks: privileged containers, images from registries other than my ACR, Pods without CPU and memory limits, and Services of type LoadBalancer with a public IP. Start with **Audit**, then move to **Deny**.

## How do you connect AKS or App Service to Azure Database for PostgreSQL securely?

**Candidate:**

```text
App (AKS Pod or App Service)
-> VNet (App Service uses VNet integration)
-> private endpoint or VNet-injected PostgreSQL Flexible Server (no public access)
-> Private DNS zone privatelink.postgres.database.azure.com resolves the name to a private IP
-> login with Entra ID (managed identity) or a password from Key Vault
-> TLS required (sslmode=require)
```

- Most connection failures here are **DNS**: the Private DNS zone is not linked to the app's VNet, so the name resolves to a public IP.
- With Entra ID login, the app gets a token from its managed identity and uses it as the password. No database password is stored at all.

---

# Part 7: Monitoring and alerting

## The big picture

```text
Applications  -> Application Insights  -┐
Azure resources -> diagnostic settings  -┼-> Log Analytics workspace -> KQL alerts -> Action Group -> email, Teams, on-call
AKS (logs)    -> Container Insights     -┘
AKS (metrics) -> Managed Prometheus -> Azure Monitor workspace -> Grafana dashboards + Prometheus alerts
Azure logs    -> Event Hub -> Splunk (central logs and dashboards for the operations team)
```

## How do Azure Monitor, Application Insights, and Log Analytics fit together?

**Interviewer:** What is the difference between Azure Monitor, Application Insights, and Log Analytics, and how do they work together?

**Candidate:**

They are not three separate products. **Azure Monitor** is the umbrella. **Application Insights** is the part that collects telemetry from the application. The **Log Analytics workspace** is where the logs are stored and queried with KQL.

| Component | What it is | Example data |
| --- | --- | --- |
| Azure Monitor | The whole platform: metrics, logs, alerts, action groups, workbooks | Platform metrics, alert rules |
| Application Insights | Application performance monitoring (APM) inside Azure Monitor | Requests, response times, dependencies, exceptions, traces, availability tests |
| Log Analytics workspace | The log store with KQL | `AppRequests`, `AppExceptions`, `ContainerLogV2`, `AzureDiagnostics` |
| Azure Monitor workspace | A different store, for Prometheus metrics | Managed Prometheus time series |

```text
App (instrumented)          -> Application Insights -┐
AKS (Azure Monitor Agent)   -> Container Insights   -┼-> one Log Analytics workspace
Azure resources             -> diagnostic settings  -┘        |
                                                      KQL, workbooks, alert rules
                                                              |
                                                      Action Group -> email / Teams / on-call
```

Example: an API starts returning HTTP 500.

```text
Application Insights records the failed request and the exception (same operation ID)
-> stored in AppRequests and AppExceptions in the workspace
-> log alert "failed requests > 20 in 5 minutes" fires
-> Action Group notifies the team
-> engineer follows the operation ID to the exception, the failing dependency, and the container logs
```

### Remember

- "Which Azure Monitor component collects app telemetry automatically?" **Application Insights**, through auto-instrumentation (App Service, Functions, the Java agent) or the OpenTelemetry Distro.
- Linking Application Insights to a workspace does **not** instrument the app. The app still needs the agent or SDK and the connection string.
- One workspace per environment keeps app logs and infrastructure logs together, so one KQL query can join them.

## How do you integrate an application with Azure Monitor (Application Insights)?

**Interviewer:** How did you connect your application to Azure Monitor?

**Candidate:**

I create an **Application Insights** resource that stores its data in a **Log Analytics workspace**, and give the app the **connection string**. The app sends requests, dependencies (SQL, HTTP calls), exceptions, traces, and custom metrics.

```text
App with the Azure Monitor OpenTelemetry Distro
-> sends telemetry using APPLICATIONINSIGHTS_CONNECTION_STRING
-> Application Insights (stored in Log Analytics)
-> Application Map, Failures, Performance, Live Metrics
-> KQL queries and alerts
```

### Three ways to turn it on

| Hosting | How |
| --- | --- |
| App Service / Functions | Turn on Application Insights in the portal or Bicep. For .NET, Java, Node.js, and Python on App Service, auto-instrumentation can work without code changes. |
| AKS or VMs | Add the **Azure Monitor OpenTelemetry Distro** to the app and set the connection string as an environment variable. |
| Java anywhere | Attach the Application Insights Java agent (`-javaagent:applicationinsights-agent.jar`). No code change. |

### Python example

```python
# pip install azure-monitor-opentelemetry
from azure.monitor.opentelemetry import configure_azure_monitor

configure_azure_monitor()   # reads APPLICATIONINSIGHTS_CONNECTION_STRING from the environment
```

### Bicep example

```bicep
resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: 'appi-orders-prod'
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalytics.id
  }
}

// pass appInsights.properties.ConnectionString to the app as APPLICATIONINSIGHTS_CONNECTION_STRING
```

### Useful KQL

```kusto
// Failed requests per operation in the last hour
AppRequests
| where TimeGenerated > ago(1h)
| summarize total = count(), failed = countif(Success == false) by OperationName
| extend failurePercent = round(100.0 * failed / total, 2)
| order by failed desc
```

### Remember

- Use the **connection string**, not the old instrumentation key. Instrumentation-key-only ingestion is no longer supported.
- Turn on **sampling** for busy apps to control cost.
- An **availability test** (standard test) calls a URL from several Azure regions and alerts when it fails. This catches problems even when nobody is using the app.

## How do you integrate AKS with Azure Monitor?

**Interviewer:** How do application logs from AKS reach Azure Monitor?

**Candidate:**

Two parts:

1. **Container Insights** for logs: container stdout/stderr, Kubernetes events, and node and Pod inventory go to Log Analytics.
2. **Azure Monitor managed service for Prometheus** for metrics, stored in an Azure Monitor workspace, with **Azure Managed Grafana** for dashboards.

```bash
# Logs: Container Insights
az aks enable-addons -g rg-aks-prod -n aks-app-prod --addons monitoring \
  --workspace-resource-id "<log-analytics-workspace-id>"

# Metrics: managed Prometheus, linked to Managed Grafana
az aks update -g rg-aks-prod -n aks-app-prod \
  --enable-azure-monitor-metrics \
  --azure-monitor-workspace-resource-id "<azure-monitor-workspace-id>" \
  --grafana-resource-id "<managed-grafana-id>"
```

```kusto
// Pods that restarted in the last 24 hours
KubePodInventory
| where TimeGenerated > ago(24h)
| summarize restarts = max(PodRestartCount) by Namespace, Name
| where restarts > 0
| order by restarts desc
```

How the **application logs** get there:

```text
App writes logs to stdout/stderr (JSON is best)
-> container runtime writes them to the node (/var/log/containers)
-> Azure Monitor Agent (DaemonSet, added by Container Insights) reads them
-> a data collection rule (DCR) decides what is kept
-> ContainerLogV2 table in Log Analytics
```

```kusto
// Errors from one namespace in the last hour
ContainerLogV2
| where TimeGenerated > ago(1h)
| where PodNamespace == "orders" and LogMessage has "ERROR"
| project TimeGenerated, PodName, ContainerName, LogMessage
| order by TimeGenerated desc
```

- The app needs no logging library for this. Container logs show **what the app printed**.
- For request timings, exceptions, and dependency calls, I also instrument the app with **Application Insights** (Java agent or OpenTelemetry Distro, connection string from a Secret). That telemetry lands in the same workspace.
- Container logs can be expensive. In the DCR I use the **ContainerLogV2** schema, exclude noisy namespaces like `kube-system`, and use the **Basic** logs plan for noisy, low-value tables. In Terraform this is the `oms_agent` block on the cluster plus a data collection rule.

## How do you integrate Prometheus and Grafana with AKS?

**Interviewer:** You built Prometheus and Grafana dashboards. How did they connect to the cluster and the apps?

**Candidate:**

There are two common setups:

| Option | What it is | When I pick it |
| --- | --- | --- |
| **Managed** (Azure Monitor managed Prometheus + Azure Managed Grafana) | Azure runs the storage and Grafana. AKS sends metrics with one setting. | Less to operate, Entra ID login to Grafana, long retention. |
| **Self-hosted** (`kube-prometheus-stack` Helm chart) | Prometheus Operator, Prometheus, Alertmanager, Grafana, node-exporter, and kube-state-metrics in the cluster. | Full control, works the same on any cluster. |

### Self-hosted example

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm upgrade --install monitoring prometheus-community/kube-prometheus-stack \
  -n monitoring --create-namespace -f monitoring-values.yaml
```

### How an app's metrics get in

The app exposes `/metrics`. A **ServiceMonitor** tells Prometheus to scrape it.

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: orders-api
  namespace: orders
  labels:
    release: monitoring            # must match the Prometheus selector of the chart
spec:
  selector:
    matchLabels:
      app: orders-api
  endpoints:
  - port: http
    path: /metrics
    interval: 30s
```

### How Grafana connects

- Self-hosted: Grafana has Prometheus as a data source, set up by the chart.
- Managed: Azure Managed Grafana uses its managed identity with the **Monitoring Data Reader** role on the Azure Monitor workspace. Grafana can also add **Azure Monitor** and **Log Analytics** as data sources, so one dashboard can show Prometheus metrics and KQL logs together.

Useful PromQL:

```promql
# CPU used by each Pod compared to its request
sum by (namespace, pod) (rate(container_cpu_usage_seconds_total{container!=""}[5m]))
/
sum by (namespace, pod) (kube_pod_container_resource_requests{resource="cpu"})
```

## How do you integrate Azure resources with Log Analytics?

**Candidate:**

With **diagnostic settings**. Every Azure resource (Key Vault, Application Gateway, PostgreSQL, Storage, AKS control plane) can send its logs and metrics to a Log Analytics workspace, a Storage account (cheap archive), or an Event Hub (to Splunk).

```bash
az monitor diagnostic-settings create \
  --name to-law \
  --resource "<key-vault-resource-id>" \
  --workspace "<log-analytics-workspace-id>" \
  --logs '[{"categoryGroup":"allLogs","enabled":true}]' \
  --metrics '[{"category":"AllMetrics","enabled":true}]'
```

Diagnostic settings are easy to forget on new resources. I set them in the Bicep or Terraform module, and use an Azure Policy with **DeployIfNotExists** to add them to anything created without them.

## How do you integrate Azure Monitor alerts with email, Teams, and on-call?

**Interviewer:** How does an alert reach the right person?

**Candidate:**

An **alert rule** watches a signal. When it fires, it calls an **Action Group**. The Action Group sends email or SMS, or calls a webhook that posts to Teams or creates an on-call incident.

```text
Alert rule (metric, KQL log query, activity log, or availability test)
-> severity (Sev0 to Sev4)
-> Action Group for that severity
   Sev0-Sev1 -> on-call tool (phone or page) + Teams + email
   Sev2      -> Teams + email
   Sev3-Sev4 -> email or a ticket only
```

```bash
# Action Group with email and a webhook (for example a Teams Workflows webhook)
az monitor action-group create -g rg-monitoring -n ag-platform-sev1 --short-name platsev1 \
  --action email oncall oncall@example.com \
  --action webhook teams "https://<teams-workflow-webhook-url>"

# Metric alert: VM CPU above 85% for 15 minutes
az monitor metrics alert create -g rg-monitoring -n vm-cpu-high \
  --scopes "<vm-resource-id>" \
  --condition "avg Percentage CPU > 85" \
  --window-size 15m --evaluation-frequency 5m --severity 2 \
  --action ag-platform-sev1
```

Log alert example in KQL, for failed backup jobs:

```kusto
AddonAzureBackupJobs
| where TimeGenerated > ago(24h)
| where JobOperation == "Backup" and JobStatus == "Failed"
| project TimeGenerated, BackupItemUniqueId, JobFailureCode
```

### Remember

- Teams **Office 365 connectors** (classic incoming webhooks) are being retired. Use a **Teams Workflows** webhook or a Logic App instead.
- Use **alert processing rules** to mute alerts during planned maintenance.
- Every paging alert should link to a **runbook**. An alert that nobody acts on is noise, so delete or tune it.

## How do you integrate Prometheus Alertmanager with Teams or on-call?

**Candidate:**

Prometheus evaluates **alerting rules** and sends firing alerts to **Alertmanager**. Alertmanager groups them, removes duplicates, and routes them by labels such as `severity` and `team`.

```yaml
# PrometheusRule (kube-prometheus-stack)
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: orders-api
  namespace: orders
  labels:
    release: monitoring
spec:
  groups:
  - name: orders-api
    rules:
    - alert: OrdersApiHighErrorRate
      expr: |
        sum(rate(http_requests_total{app="orders-api",status=~"5.."}[5m]))
        / sum(rate(http_requests_total{app="orders-api"}[5m])) > 0.05
      for: 10m
      labels:
        severity: critical
      annotations:
        summary: "orders-api 5xx rate above 5% for 10 minutes"
```

Alertmanager then sends `critical` alerts to the on-call tool and everything to a Teams channel through a webhook receiver. With managed Prometheus, the same rules are **Prometheus rule groups** in Azure, and they fire Azure Monitor Action Groups.

## How do you set up Splunk from scratch?

**Interviewer:** Can you build Splunk from scratch?

**Candidate:**

Splunk is not built like an app; it is **deployed and configured**. At a high level:

```text
Sources (VMs, apps, AKS, Azure)
-> Universal Forwarder (port 9997) or HTTP Event Collector, HEC (port 8088)
-> Indexers: parse, index, and store the data
-> Search Head: SPL searches, dashboards, alerts
-> notifications: email, Teams, ServiceNow
```

| Component | Job |
| --- | --- |
| Universal Forwarder | Small agent on servers. Reads log files and Windows event logs, sends them to the indexers. |
| Heavy Forwarder (optional) | Filters or parses data before indexing; runs add-ons like the Microsoft Cloud Services add-on. |
| HEC | Token-based HTTPS endpoint for apps and the Kubernetes collector. |
| Indexer | Stores and indexes data. Clustered for high availability. |
| Search Head | The UI for searches, dashboards, and alerts. |
| Deployment Server | Pushes input configs to all forwarders from one place. |

Steps:

1. **Install:** one all-in-one Splunk Enterprise instance for a small setup, or separate indexers and search heads for production. Many companies use **Splunk Cloud**, where Splunk runs the indexers and search heads and we only onboard data.
2. **Create indexes** per environment or data type (`aks_prod`, `linux_os`, `azure_prod`) with a retention period (`frozenTimePeriodInSecs`). Separate indexes make access control and retention easy.
3. **Onboard data:** forwarder `inputs.conf` for servers, HEC tokens for apps and AKS, Event Hub add-on for Azure (below).
4. **Build dashboards and alerts:** error count, HTTP 5xx rate, latency, Pod restarts; scheduled searches that alert to Teams or ServiceNow.
5. **Secure it:** roles that see only their team's indexes, TLS between forwarders and indexers, HEC tokens in Key Vault, SSO with Entra ID (SAML).

```ini
# inputs.conf on a Universal Forwarder
[monitor:///opt/orders/logs/app.log]
index = app_prod
sourcetype = orders:log
```

### Remember

- Plan the **license** (daily ingest volume) and storage first. Filter noisy logs at the source.
- Be honest about scope. In my case Splunk already existed, so I say I **integrated** Azure workloads with Splunk and built the dashboards and alerts, and I explain how I would set it up from scratch.

## How do you integrate Azure with Splunk?

**Interviewer:** How did you get Azure logs into Splunk?

**Candidate:**

Splunk does not read Log Analytics directly. The usual path is **diagnostic settings to Event Hub**, and Splunk pulls from the Event Hub.

```text
Azure resources (diagnostic settings), Activity Log, Entra ID logs
-> Azure Event Hub
-> Splunk Add-on for Microsoft Cloud Services (on a Splunk heavy forwarder) reads the Event Hub
-> Splunk index (for example azure_prod)
-> Splunk dashboards and alerts
```

Steps:

1. Create an Event Hubs namespace and an event hub, for example `eh-splunk`.
2. Point diagnostic settings at it: `--event-hub eh-splunk --event-hub-rule <authorization-rule-id>`.
3. Create an app registration for Splunk with the **Azure Event Hubs Data Receiver** role.
4. Configure the add-on input with the namespace, event hub, and consumer group.
5. Build dashboards and alerts on the index.

Other paths:

- **HTTP Event Collector (HEC):** the app or a Function pushes events to Splunk over HTTPS with a HEC token. Good for application events.
- **Universal Forwarder** on VMs: reads log files from disk and sends them to Splunk.

Example Splunk search:

```text
index=azure_prod sourcetype="mscs:azure:eventhub" "properties.resultType"="Failed"
| stats count by "properties.operationName"
| sort - count
```

## How do you integrate AKS with Splunk?

**Candidate:**

With the **Splunk OpenTelemetry Collector for Kubernetes**, installed by Helm. It runs as a DaemonSet, reads container logs from every node, adds Kubernetes metadata (namespace, Pod, container), and sends them to Splunk through HEC.

```bash
helm repo add splunk-otel-collector-chart https://signalfx.github.io/splunk-otel-collector-chart
helm upgrade --install splunk-otel splunk-otel-collector-chart/splunk-otel-collector \
  -n splunk --create-namespace \
  --set clusterName=aks-app-prod \
  --set splunkPlatform.endpoint=https://splunk.example.com:8088/services/collector \
  --set splunkPlatform.token="$SPLUNK_HEC_TOKEN" \
  --set splunkPlatform.index=k8s_prod
```

The older **Splunk Connect for Kubernetes** reached end of support. The OpenTelemetry collector is its replacement. **Fluent Bit** with its `splunk` output plugin is a common alternative.

```text
App writes JSON logs to stdout
-> node log files (/var/log/containers)
-> collector DaemonSet adds cluster, namespace, Pod, container
-> buffers and retries if Splunk is down
-> HTTPS + HEC token -> index aks_prod -> dashboards and alerts
```

- In a real setup, the HEC token is not passed with `--set`. It comes from Key Vault into a Kubernetes Secret, and the chart uses it with `secret.create=false` and `secret.name=<secret>`.
- If AKS egress goes through Azure Firewall, allow outbound HTTPS to the HEC endpoint (8088, or 443 for Splunk Cloud).
- The HEC token should be allowed to write only to the cluster's indexes. Exclude noisy namespaces at the collector to save license.
- The app needs no Splunk library. It just logs to stdout.

## How do Prometheus, Grafana, and Splunk work together?

**Interviewer:** You have Splunk, Grafana, and Prometheus. How do you use them together without watching three screens all day?

**Candidate:**

Each tool has one job, and **alerts** tell me where to look:

| Tool | Job | Example |
| --- | --- | --- |
| Prometheus | Collects metrics and fires alerts | CPU, memory, Pod restarts, request rate, 5xx rate |
| Grafana | Shows the metrics on dashboards | AKS health, API latency per service |
| Splunk | Stores and searches logs | Exceptions, stack traces, HTTP 500 details |

```text
Prometheus alert: orders-api latency 200 ms -> 5 s, Pod restarts rising
-> Grafana dashboard: which service, since when, memory at 95%
-> Splunk: index=aks_prod service=orders-api "OutOfMemoryError"
-> root cause: memory leak in the new release -> roll back
-> confirm in Grafana that latency is normal again
```

How I connect them:

- The same **labels** everywhere (cluster, namespace, service, version), so a Grafana panel and a Splunk search point at the same thing.
- Grafana dashboards have **links** to a ready-made Splunk search for that service and time range. Grafana Enterprise can also add Splunk as a data source with a plugin.
- Alertmanager and Splunk alerts go to the **same Teams channel and on-call tool**, with the severity in the alert.
- **Saved searches** in Splunk for common problems (5xx, timeouts, OOM, auth failures).

Rule to remember: **metrics tell you that something is wrong, logs tell you why.**

## How do you connect deployments with monitoring?

**Candidate:**

After every deploy, the pipeline checks health instead of finishing blindly:

1. `kubectl rollout status` or a call to the `/healthz` endpoint.
2. A short check of the error rate in Application Insights or Prometheus.
3. If the check fails, roll back with `helm rollback` or by swapping App Service slots back.

I also mark each deployment on the dashboards (a Grafana annotation or an Application Insights release annotation). When a graph changes, everyone can see it lines up with a deploy.

---

# Part 8: Serverless and messaging

## How do you integrate Azure Functions with Service Bus?

**Interviewer:** How did your Azure Functions work with Service Bus?

**Candidate:**

The API puts a request message on a **Service Bus queue** and returns right away. A **Service Bus-triggered Function** picks up each message, does the slow work (for example, generating a document), and writes the result to **Blob Storage**.

```text
API receives a request
-> sends a message to the Service Bus queue (returns 202 Accepted)
-> Function is triggered by the message (peek-lock)
-> Function generates the document
-> Function writes the file to Blob Storage
-> message is completed (removed from the queue)
-> if it fails many times, the message moves to the dead-letter queue
```

### Example (Python v2 programming model)

```python
import azure.functions as func

app = func.FunctionApp()

@app.service_bus_queue_trigger(arg_name="msg", queue_name="doc-requests",
                               connection="ServiceBusConnection")
@app.blob_output(arg_name="outfile", path="documents/{MessageId}.pdf",
                 connection="DocsStorage")
def generate_document(msg: func.ServiceBusMessage, outfile: func.Out[bytes]):
    request = msg.get_body().decode("utf-8")
    pdf_bytes = build_pdf(request)      # your document logic
    outfile.set(pdf_bytes)
```

### Login without connection strings (managed identity)

```text
ServiceBusConnection__fullyQualifiedNamespace = sb-docs-prod.servicebus.windows.net
DocsStorage__blobServiceUri                    = https://stdocsprod.blob.core.windows.net
```

The Function App's managed identity needs **Azure Service Bus Data Receiver** on the queue and **Storage Blob Data Contributor** on the container.

### Remember

- **Peek-lock:** the message is hidden while the Function works. If the Function succeeds, the message is completed. If it fails, the message comes back and is retried.
- After **max delivery count** (10 by default) the message goes to the **dead-letter queue**. Alert on the dead-letter count, because nobody looks there otherwise.
- Make the Function **idempotent** (the same message processed twice gives the same result), because Service Bus delivers **at least once**. Naming the file by message or request ID does this.
- The trigger scales the Function out based on the queue length. Limit concurrency in `host.json` so you do not overload the database.

## How do you integrate Event Grid with Functions and Storage?

**Candidate:**

**Event Grid** delivers events, such as "a blob was created", to a handler like a Function or a webhook. It pushes the event, so nothing has to keep checking the storage account.

```text
File uploaded to Blob Storage
-> Storage account publishes a BlobCreated event to Event Grid
-> Event Grid subscription with a filter (container, file type)
-> Function with an Event Grid trigger runs
```

```bash
az eventgrid event-subscription create \
  --name new-invoices \
  --source-resource-id "<storage-account-id>" \
  --endpoint-type azurefunction \
  --endpoint "<function-resource-id>/functions/process_invoice" \
  --included-event-types Microsoft.Storage.BlobCreated \
  --subject-begins-with /blobServices/default/containers/invoices/
```

### Scenario: a Function turns uploaded files into PDFs

```text
User uploads invoice.docx to the input/ container
-> BlobCreated event, filtered to input/ only
-> Function runs (Event Grid trigger, or a Blob trigger with source EventGrid)
-> reads the file, generates the PDF
-> writes output/invoice.pdf
-> failures: retry, then dead-letter; bad files moved to failed/
```

- **Filter on the input container.** If the Function's own output also raised events, it would trigger itself in a loop.
- **Managed identity** with Storage Blob Data Reader on `input/` and Contributor on `output/`. No storage account key in app settings.
- **Idempotent:** if `output/invoice.pdf` already exists, skip. Events can arrive more than once.
- **10,000 uploads at once:** put a **Service Bus queue** between Event Grid and the Function (the design in the section above). The queue absorbs the spike, `host.json` limits concurrency, and failed jobs go to the dead-letter queue.
- Very long jobs (many minutes) fit better in **Container Apps Jobs** than in one Function run.

### Service Bus vs Event Grid

| | Service Bus | Event Grid |
| --- | --- | --- |
| Model | Queue or topic; the consumer pulls messages | Push; Event Grid calls your handler |
| Use for | Commands and work items that must not be lost (orders, document jobs) | Reacting to events (a blob was created, a resource changed) |
| Features | Ordering with sessions, dead-letter queue, transactions, duplicate detection | Filtering, fan-out to many handlers, retries, dead-letter to storage |

---

# Part 9: Configuration management, artifacts, and Git

## How do you integrate Terraform with Ansible?

**Interviewer:** Where does Terraform stop and Ansible start?

**Candidate:**

**Terraform builds the infrastructure. Ansible configures what runs on it.**

```text
Terraform/Bicep creates VMs with tags (role=web, env=prod)
-> Ansible dynamic inventory finds the VMs by tag
-> Ansible playbook installs packages, applies OS hardening, configures the app
-> the same playbook runs later for patching and config drift
```

I do not use Terraform `remote-exec` provisioners for configuration. They run only once, at creation, are hard to re-run, and failures leave a half-built VM.

## How do you integrate Ansible with Azure?

**Candidate:**

With the **`azure.azcollection`** collection and the **Azure dynamic inventory plugin**, so I never keep a static list of IP addresses.

```yaml
# inventory/prod.azure_rm.yml   (the file name must end with azure_rm.yml)
plugin: azure.azcollection.azure_rm
auth_source: auto            # managed identity, environment variables, or az login
include_vm_resource_groups:
  - rg-web-prod
keyed_groups:
  - prefix: role
    key: tags.role           # creates groups like role_web
conditional_groups:
  linux: "'linux' in os_profile.system"
```

```bash
ansible-galaxy collection install azure.azcollection
ansible-inventory -i inventory/prod.azure_rm.yml --graph
ansible-playbook -i inventory/prod.azure_rm.yml patch.yml --limit role_web
```

From a pipeline (Azure DevOps, Jenkins, or GitHub Actions), the same command runs after the Azure login step. SSH keys come from Key Vault or the CI credential store, never from the repo.

## How do you integrate pipelines with Nexus and Azure Artifacts?

**Interviewer:** How do your pipelines publish and use packages?

**Candidate:**

The build publishes a **versioned package** (Maven JAR, npm, NuGet, Python wheel) to the artifact repository. Other builds and deploys pull that exact version. **Promotion** means moving the same package from a dev feed or view to a release one after testing, not rebuilding it.

### Azure DevOps with Azure Artifacts

```yaml
- task: NuGetAuthenticate@1          # also npmAuthenticate@0, PipAuthenticate@1, MavenAuthenticate@0
- script: dotnet nuget push "**/*.nupkg" --source "https://pkgs.dev.azure.com/<org>/_packaging/<feed>/nuget/v3/index.json" --api-key az
```

Azure Artifacts feeds have **views** (`@local`, `@prerelease`, `@release`). Promoting a package to `@release` is the approval step.

### Jenkins with Nexus

```groovy
stage('Publish to Nexus') {
  steps {
    configFileProvider([configFile(fileId: 'maven-settings-nexus', variable: 'MAVEN_SETTINGS')]) {
      sh 'mvn -B -s "$MAVEN_SETTINGS" deploy -DskipTests'
    }
  }
}
```

The Maven `settings.xml` holds the Nexus credentials and is stored in Jenkins (Config File Provider plugin), not in Git. Snapshots go to a `maven-snapshots` repository and releases to `maven-releases`, which does not allow overwriting a version.

## How do you integrate Git with your pipelines?

**Candidate:**

Git is where everything starts. The integration has three parts: **triggers**, **pull request checks**, and **branch protection**.

| | Azure Repos + Azure DevOps | GitHub + GitHub Actions | GitLab + GitLab CI | Jenkins |
| --- | --- | --- | --- | --- |
| Trigger | `trigger:` and `pr:` in YAML | `on: push` / `pull_request` | Pipelines on push and merge request | Multibranch Pipeline + webhook from the Git server |
| PR check | Branch policy -> **Build validation** | **Required status checks** | **Pipelines must succeed** setting | Status reported back to the Git server |
| Protection | Branch policies: reviewers, linked work item, comment resolution | Rulesets or branch protection, CODEOWNERS | Protected branches, approval rules, CODEOWNERS | Done on the Git server side |

```text
Developer opens a pull request to main
-> the pipeline runs build, tests, SonarQube, Checkov, Trivy, and terraform plan
-> results show on the pull request
-> merge is blocked until checks pass and a reviewer approves
-> merge to main triggers the deploy pipeline
```

---

# Quick answers for the interview

| Question | Short answer |
| --- | --- |
| How does a pipeline log in to Azure without a secret? | Workload identity federation (OIDC): Azure DevOps service connection, GitHub `azure/login` with `id-token: write`, GitLab `id_tokens`. |
| How does AKS pull from a private ACR? | `az aks update --attach-acr`: AcrPull for the kubelet identity. No pull secret. |
| How do Pods read Key Vault secrets? | Key Vault Secrets Provider (CSI driver) + Workload Identity + `SecretProviderClass`. |
| How does App Service read Key Vault? | `@Microsoft.KeyVault(...)` app setting references + managed identity with Key Vault Secrets User. |
| Where is Terraform state? | azurerm backend in a Storage account; blob lease for locking; Entra ID auth; versioning on. |
| How is a Terraform apply approved? | Saved plan file, approval on the environment (Azure DevOps or GitHub) or `input` step (Jenkins) or manual job (GitLab), then apply that plan. |
| How do Jenkins and Kubernetes connect? | Kubernetes plugin runs agents as Pods; deploy with Helm/kubectl using a kubeconfig credential or managed identity. |
| How does SonarQube block a build? | Quality gate: `SonarQubePublish`, `waitForQualityGate abortPipeline: true`, or `sonar.qualitygate.wait=true`. |
| How does Trivy block an image? | `trivy image --severity HIGH,CRITICAL --exit-code 1` before `docker push`. |
| How does Checkov fit with Terraform? | Scan source and the JSON plan in the pull request; fail on findings; skip only with a written reason. |
| How does an app send telemetry to Azure Monitor? | Application Insights connection string + Azure Monitor OpenTelemetry Distro or auto-instrumentation. |
| How does AKS send metrics and logs? | Container Insights to Log Analytics; managed Prometheus to an Azure Monitor workspace; Grafana for dashboards. |
| How does an alert reach Teams? | Alert rule -> Action Group -> webhook to a Teams Workflow (or Logic App). |
| How do Azure logs get to Splunk? | Diagnostic settings -> Event Hub -> Splunk Add-on for Microsoft Cloud Services. AKS: Splunk OTel Collector via HEC. |
| How do Functions use Service Bus? | Service Bus trigger with peek-lock; managed identity (`__fullyQualifiedNamespace`); dead-letter queue after max delivery count; idempotent code. |
| Terraform vs Ansible? | Terraform builds infrastructure; Ansible configures servers, found by the Azure dynamic inventory. |
| How does Terraform log in to Azure? | azurerm provider reads `ARM_*` variables: `az login` locally, OIDC in pipelines, managed identity on Azure agents; client secret only as a last resort. |
| How do you connect to AKS? | `az aks get-credentials` + `kubelogin` with Entra ID; RBAC decides what you can do; local accounts disabled. |
| How do you reach a private AKS cluster? | From inside the VNet (Bastion jump box, VPN, self-hosted agent) or `az aks command invoke`. |
| How do you deploy to App Service and Functions? | Build once; `AzureWebApp@1` to a staging slot then swap; `AzureFunctionApp@2`; settings and Key Vault references per environment. |
| How does Jenkins read Key Vault? | Agent's managed identity or Workload Identity + Azure Key Vault plugin (`withAzureKeyvault`) or `az keyvault secret show`. |
| Azure Monitor vs Application Insights vs Log Analytics? | Azure Monitor is the platform; Application Insights collects app telemetry; Log Analytics stores logs for KQL and alerts. |
| How would you set up Splunk? | Forwarders or HEC -> indexers -> search head; indexes per environment with retention; dashboards, alerts, RBAC, TLS, SSO. |
| Prometheus, Grafana, and Splunk together? | Prometheus alerts, Grafana shows where, Splunk logs show why. Shared labels and links between them. |
| Commercial alternatives to SonarQube and Trivy? | Checkmarx, Veracode, GitHub Advanced Security (code); Snyk, Prisma Cloud, JFrog Xray, Defender for Containers (images). Same pattern: extension, token, threshold, fail the build. |

Related files: [cicd-flow.md](cicd-flow.md), [sample-pipelines-examples.md](sample-pipelines-examples.md), [secrets-management.md](secrets-management.md), [zero-downtime-deployment.md](zero-downtime-deployment.md), and [rollback-strategy.md](rollback-strategy.md).
