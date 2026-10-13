# Hands-on 7: Terraform CI/CD with GitHub Actions on Azure (RG, ACR, AKS)

> Build reusable Terraform modules for a Resource Group, ACR, and AKS, then deploy them from a GitHub Actions pipeline that formats, validates, scans, plans, waits for a manual approval, and applies, using OIDC instead of a client secret.

**Time:** about 1.5 hours. **Level:** Intermediate.

## What you practise

- A modular Terraform layout: `modules/` plus `environments/dev` and `environments/prod`
- Modules for `azurerm_resource_group`, `azurerm_container_registry`, and `azurerm_kubernetes_cluster`
- Giving the AKS kubelet identity `AcrPull` on ACR with `azurerm_role_assignment`
- `for_each` with nested maps to create many resources from one block
- Azure login from GitHub Actions with OIDC (federated credentials, no secret)
- A pipeline with `fmt`, `validate`, a Trivy (tfsec) security scan, a saved plan, and a manual approval before `apply`
- Using an AI CLI to scaffold the project, with clear guardrails

## Prerequisites

| Item | Purpose |
| --- | --- |
| Azure subscription | Target for RG, ACR, and AKS |
| Permission to create an Entra app registration (or a user-assigned managed identity) and assign roles | OIDC identity for the pipeline |
| Storage account `companytfstate` in `tfstate-rg` with container `tfstate` | Remote Terraform state |
| GitHub repository with admin access | Secrets, environments, and workflows |
| Terraform 1.9+, Azure CLI | Local testing |
| Trivy (optional, local) | Run the same security scan before pushing |

## Flow

```text
Developer pushes a branch and opens a pull request
        |
        v
GitHub Actions job: plan  (OIDC login, no secret)
  checkout -> setup-terraform -> fmt -check -> init -> validate
  -> Trivy config scan (fails on HIGH/CRITICAL)
  -> plan -out=tfplan -> upload artifact -> comment plan on PR
        |
        | PR reviewed and merged to main
        v
Push to main: plan job runs again and saves tfplan
        |
        v
GitHub Actions job: apply  (environment: production)
  waits for required reviewers (manual approval)
  -> download tfplan -> init -> apply tfplan
        |
        v
Azure: rg-prod -> ACR (myacr) -> AKS (aks-prod) with AcrPull
```

## Steps

### 1. Create the repository layout

```text
infra-repo/
├── .github/
│   └── workflows/
│       └── terraform-pipeline.yml
├── modules/
│   ├── resource_group/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   ├── acr/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   └── aks/
│       ├── main.tf
│       ├── variables.tf
│       └── outputs.tf
└── environments/
    ├── dev/
    │   ├── main.tf           # calls the modules
    │   ├── providers.tf      # provider and backend blocks
    │   ├── variables.tf
    │   ├── terraform.tfvars  # dev values
    │   └── backend.hcl       # dev state key
    └── prod/
        ├── main.tf
        ├── providers.tf
        ├── variables.tf
        ├── terraform.tfvars  # prod values
        └── backend.hcl       # prod state key
```

- **Modules** hold the logic once.
- **Environments** only call modules with different values and have their **own state file**, so a Dev change can never touch Prod state.

A larger "landing zone" repo follows the same idea with more modules, for example `landingzone/vnet`, `subnet`, `nsg`, and `vm`, plus a root `main.tf`, `variables.tf`, and `outputs.tf`.

### 2. Write the modules

`modules/resource_group/main.tf`:

```hcl
resource "azurerm_resource_group" "this" {
  name     = var.name
  location = var.location
  tags     = var.tags
}
```

`modules/resource_group/variables.tf` and `outputs.tf`:

```hcl
variable "name" {
  type = string
}

variable "location" {
  type = string
}

variable "tags" {
  type    = map(string)
  default = {}
}

output "name" {
  value = azurerm_resource_group.this.name
}

output "location" {
  value = azurerm_resource_group.this.location
}
```

`modules/acr/main.tf`:

```hcl
resource "azurerm_container_registry" "this" {
  name                = var.name          # globally unique, letters and numbers only
  resource_group_name = var.resource_group_name
  location            = var.location
  sku                 = var.sku           # Basic, Standard, or Premium
  admin_enabled       = false             # use Entra ID / AcrPull, not the admin user
  tags                = var.tags
}

output "id" {
  value = azurerm_container_registry.this.id
}

output "login_server" {
  value = azurerm_container_registry.this.login_server
}
```

`modules/aks/main.tf`:

```hcl
resource "azurerm_kubernetes_cluster" "this" {
  name                = var.name
  location            = var.location
  resource_group_name = var.resource_group_name
  dns_prefix          = var.name
  kubernetes_version  = var.kubernetes_version

  default_node_pool {
    name       = "system"
    vm_size    = var.node_vm_size
    node_count = var.node_count
  }

  identity {
    type = "SystemAssigned"
  }

  network_profile {
    network_plugin      = "azure"
    network_plugin_mode = "overlay"
  }

  tags = var.tags
}

# Let the nodes (kubelet identity) pull images from ACR
resource "azurerm_role_assignment" "acr_pull" {
  scope                            = var.acr_id
  role_definition_name             = "AcrPull"
  principal_id                     = azurerm_kubernetes_cluster.this.kubelet_identity[0].object_id
  skip_service_principal_aad_check = true
}

output "id" {
  value = azurerm_kubernetes_cluster.this.id
}

output "kubelet_object_id" {
  value = azurerm_kubernetes_cluster.this.kubelet_identity[0].object_id
}
```

Each module also needs a `variables.tf` declaring the inputs it uses (`name`, `location`, `resource_group_name`, `sku`, `acr_id`, `kubernetes_version`, `node_vm_size`, `node_count`, `tags`). Note that the role is given to the **kubelet** identity, not the cluster (control plane) identity, because the kubelet pulls images.

### 3. Call the modules from an environment

`environments/prod/providers.tf`:

```hcl
terraform {
  required_version = ">= 1.9.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"   # pin the major version; the lock file pins the exact one
    }
  }

  backend "azurerm" {
    use_oidc         = true
    use_azuread_auth = true   # use Entra ID for the state blob, not storage keys
    # the rest comes from backend.hcl
  }
}

provider "azurerm" {
  features {}
  use_oidc = true
  # subscription_id, client_id, and tenant_id come from ARM_* environment variables
}
```

`environments/prod/backend.hcl`:

```hcl
resource_group_name  = "tfstate-rg"
storage_account_name = "companytfstate"
container_name       = "tfstate"
key                  = "prod/platform.tfstate"
```

`environments/prod/main.tf`:

```hcl
module "rg" {
  source   = "../../modules/resource_group"
  name     = var.resource_group_name
  location = var.location
  tags     = var.tags
}

module "acr" {
  source              = "../../modules/acr"
  name                = var.acr_name
  resource_group_name = module.rg.name
  location            = module.rg.location
  sku                 = "Standard"
  tags                = var.tags
}

module "aks" {
  source              = "../../modules/aks"
  name                = var.aks_name
  resource_group_name = module.rg.name
  location            = module.rg.location
  kubernetes_version  = var.kubernetes_version
  node_vm_size        = var.node_vm_size
  node_count          = var.node_count
  acr_id              = module.acr.id
  tags                = var.tags
}
```

`environments/prod/terraform.tfvars`:

```hcl
resource_group_name = "rg-prod"
location            = "westeurope"
acr_name            = "myacr"
aks_name            = "aks-prod"
kubernetes_version  = "1.32"
node_vm_size        = "Standard_D4s_v5"
node_count          = 3
tags = {
  environment = "prod"
  owner       = "platform-team"
}
```

The Dev folder is the same, with values such as `rg-dev`, `aks-dev`, `node_count = 1`, and `key = "dev/platform.tfstate"`. ACR names are globally unique, so Dev needs its own name, such as `myacrdev`. Check which Kubernetes versions your region supports with `az aks get-versions --location westeurope -o table`.

### 4. (Optional) Use `for_each` with nested maps

When you need many similar resources, describe them in a nested map and loop over it once. This is the pattern used in larger landing-zone repos.

```hcl
variable "resource_groups" {
  type = map(object({
    location = string
    tags     = map(string)
  }))
}

module "rg" {
  source   = "../../modules/resource_group"
  for_each = var.resource_groups

  name     = each.key
  location = each.value.location
  tags     = each.value.tags
}
```

```hcl
resource_groups = {
  "rg-dev-network" = { location = "westeurope", tags = { tier = "network" } }
  "rg-dev-apps"    = { location = "westeurope", tags = { tier = "apps" } }
}
```

Other modules then refer to `module.rg["rg-dev-apps"].name`. Because `for_each` uses map keys, adding or removing one entry does not recreate the others (unlike `count`, which uses list positions).

### 5. Test locally first

```bash
cd environments/dev
az login
export ARM_SUBSCRIPTION_ID=$(az account show --query id -o tsv)

terraform fmt -recursive ../..
terraform init -backend-config=backend.hcl
terraform validate
terraform plan -out=tfplan
```

Fix every error here before you push. It is much faster than debugging in the pipeline.

### 6. Create the OIDC identity in Azure (no client secret)

Create an app registration and service principal (a user-assigned managed identity with federated credentials works the same way):

```bash
APP_ID=$(az ad app create --display-name gh-terraform-infra --query appId -o tsv)
az ad sp create --id $APP_ID
SUB_ID=$(az account show --query id -o tsv)
TENANT_ID=$(az account show --query tenantId -o tsv)
```

Add one federated credential for each kind of workflow run. Replace `<org>/<repo>`:

```bash
for SUBJECT in \
  "repo:<org>/<repo>:ref:refs/heads/main" \
  "repo:<org>/<repo>:pull_request" \
  "repo:<org>/<repo>:environment:production"
do
  NAME=$(echo "$SUBJECT" | tr ':/' '--')
  az ad app federated-credential create --id $APP_ID --parameters "{
    \"name\": \"$NAME\",
    \"issuer\": \"https://token.actions.githubusercontent.com\",
    \"subject\": \"$SUBJECT\",
    \"audiences\": [\"api://AzureADTokenExchange\"]
  }"
done
```

- `ref:refs/heads/main` is used by the **plan** job on a push to `main`.
- `pull_request` is used by the **plan** job on a pull request.
- `environment:production` is used by the **apply** job. When a job sets `environment:`, the token subject is the environment, not the branch.

Give the identity the roles it needs:

```bash
# create and change resources
az role assignment create --assignee $APP_ID \
  --role "Contributor" --scope /subscriptions/$SUB_ID

# needed because Terraform creates the AcrPull role assignment
az role assignment create --assignee $APP_ID \
  --role "Role Based Access Control Administrator" --scope /subscriptions/$SUB_ID

# read and lock the state blob with Entra ID
az role assignment create --assignee $APP_ID \
  --role "Storage Blob Data Contributor" \
  --scope $(az storage account show -n companytfstate -g tfstate-rg --query id -o tsv)
```

In production, scope these roles to the resource groups you manage, and add a condition to the RBAC administrator role so it can only assign `AcrPull`.

### 7. Configure GitHub

1. **Settings → Secrets and variables → Actions**: add `AZURE_CLIENT_ID` (= `$APP_ID`), `AZURE_TENANT_ID`, and `AZURE_SUBSCRIPTION_ID`. These are identifiers, not passwords, but keeping them as secrets keeps them out of logs.
2. **Settings → Environments → New environment** `production`: add **Required reviewers** (one or more people or a team). Optionally restrict **Deployment branches** to `main` and enable "Prevent self-review".
3. **Settings → Branches**: protect `main` and require the `plan` check to pass before merge.

### 8. Write the workflow

`.github/workflows/terraform-pipeline.yml`:

```yaml
name: terraform-pipeline

on:
  pull_request:
    branches: [main]
    paths: ["environments/prod/**", "modules/**", ".github/workflows/terraform-pipeline.yml"]
  push:
    branches: [main]
    paths: ["environments/prod/**", "modules/**", ".github/workflows/terraform-pipeline.yml"]

permissions:
  id-token: write        # needed to request the OIDC token
  contents: read
  pull-requests: write   # needed to comment the plan on the PR

concurrency:
  group: terraform-prod
  cancel-in-progress: false   # never cancel a running apply

env:
  TF_DIR: environments/prod
  TF_VERSION: 1.9.8
  ARM_USE_OIDC: "true"
  ARM_CLIENT_ID: ${{ secrets.AZURE_CLIENT_ID }}
  ARM_TENANT_ID: ${{ secrets.AZURE_TENANT_ID }}
  ARM_SUBSCRIPTION_ID: ${{ secrets.AZURE_SUBSCRIPTION_ID }}

jobs:
  plan:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: ${{ env.TF_DIR }}
    steps:
      - uses: actions/checkout@v4

      - uses: hashicorp/setup-terraform@v3
        with:
          terraform_version: ${{ env.TF_VERSION }}
          terraform_wrapper: false

      - name: Terraform fmt
        run: terraform fmt -check -recursive ../..

      - name: Terraform init
        run: terraform init -input=false -backend-config=backend.hcl

      - name: Terraform validate
        run: terraform validate -no-color

      - name: Security scan (Trivy config, includes the tfsec checks)
        uses: aquasecurity/trivy-action@0.28.0   # pin to a full commit SHA in real repos
        with:
          scan-type: config
          scan-ref: .
          severity: HIGH,CRITICAL
          exit-code: "1"

      - name: Terraform plan
        run: |
          terraform plan -input=false -no-color -out=tfplan
          terraform show -no-color tfplan > plan.txt

      - name: Upload plan
        uses: actions/upload-artifact@v4
        with:
          name: tfplan
          path: ${{ env.TF_DIR }}/tfplan
          retention-days: 1

      - name: Comment plan on PR
        if: github.event_name == 'pull_request'
        uses: actions/github-script@v7
        with:
          script: |
            const fs = require('fs');
            let plan = fs.readFileSync('${{ env.TF_DIR }}/plan.txt', 'utf8');
            if (plan.length > 60000) { plan = plan.substring(0, 60000) + '\n... truncated ...'; }
            await github.rest.issues.createComment({
              owner: context.repo.owner,
              repo: context.repo.repo,
              issue_number: context.issue.number,
              body: '### Terraform plan (prod)\n```text\n' + plan + '\n```'
            });

  apply:
    needs: plan
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    environment: production     # required reviewers = manual approval
    defaults:
      run:
        working-directory: ${{ env.TF_DIR }}
    steps:
      - uses: actions/checkout@v4

      - uses: hashicorp/setup-terraform@v3
        with:
          terraform_version: ${{ env.TF_VERSION }}
          terraform_wrapper: false

      - name: Download plan
        uses: actions/download-artifact@v4
        with:
          name: tfplan
          path: ${{ env.TF_DIR }}

      - name: Terraform init
        run: terraform init -input=false -backend-config=backend.hcl

      - name: Terraform apply
        run: terraform apply -input=false -auto-approve tfplan
```

What happens:

- On a **pull request**, only the `plan` job runs. The plan is posted as a PR comment for review. `apply` is skipped by its `if:`.
- On a **push to `main`** (the merge), `plan` runs again on the merged code, then `apply` **pauses** until a required reviewer approves it in the Actions UI.
- `apply` uses the saved `tfplan`, so it changes exactly what the reviewer saw, nothing more.
- `concurrency` stops two runs from changing the same state at the same time.

If you prefer a local CLI, the scan step can be `trivy config --severity HIGH,CRITICAL --exit-code 1 .`. tfsec is now part of Trivy; `aquasecurity/tfsec-action` still exists, but new work should use Trivy. To accept a known finding, add an ignore with a reason (for example a `.trivyignore` entry or an inline `#trivy:ignore:<check-id>` comment) instead of turning the scan off.

### 9. Run it and verify

1. Create a branch, change something small (for example a tag in `terraform.tfvars`), and open a pull request.
2. Check that `plan` passes and a plan comment appears on the PR.
3. Merge. The `apply` job shows **Waiting for review**. Click **Review deployments → production → Approve and deploy**.
4. Check the result in Azure:

```bash
az group show -n rg-prod -o table
az acr show -n myacr --query loginServer -o tsv
az aks show -g rg-prod -n aks-prod --query provisioningState -o tsv

# AcrPull on the kubelet identity
KUBELET_ID=$(az aks show -g rg-prod -n aks-prod --query identityProfile.kubeletidentity.objectId -o tsv)
az role assignment list --assignee $KUBELET_ID --all -o table

# end-to-end check that the cluster can pull from ACR
az aks check-acr -g rg-prod -n aks-prod --acr myacr.azurecr.io
```

Expected: the resource group exists, the ACR login server is `myacr.azurecr.io`, AKS is `Succeeded`, the kubelet identity has `AcrPull`, and `check-acr` reports success. A second run with no code changes should show `No changes.` in the plan.

## Using an AI CLI to scaffold the project

An AI CLI inside the editor (for example Gemini CLI, Claude Code, or GitHub Copilot in VS Code) can create the first version of this layout in minutes. Example prompts:

- "Generate a Terraform project with modules for an Azure resource group, ACR, and AKS, and environments dev and prod with tfvars and an azurerm backend. Pin azurerm to ~> 4.0."
- "Explain what `modules/aks/main.tf` does, line by line, and which inputs are required."
- "Why is `terraform plan` failing with this error? Here is the error message: ..."
- "Review these modules against Terraform and AKS best practices: naming, tagging, identities, and least privilege."
- "Write a GitHub Actions workflow that uses OIDC, runs fmt, validate, Trivy config scan, plan, and applies only after an environment approval."

Guardrails:

- **AI output is a draft.** Read and understand every generated line before you commit it.
- **Always run** `terraform fmt`, `terraform validate`, and `terraform plan`, and read the plan. AI tools often invent arguments or use old provider syntax.
- **Never paste secrets, state files, plan files, or real tfvars** into an AI tool. State and plans can contain passwords and keys.
- **Pin** Terraform, provider, and GitHub Action versions; do not accept "latest" from generated code.
- Check that the generated code follows your standards: no admin users, no public endpoints by default, managed identities, and tags.
- The pipeline (scan, review, approval) still applies to AI-written code. The AI saves setup time; you still own the architecture and the result.

## Important points

- **OIDC** gives the job a short-lived token. There is no client secret to store, rotate, or leak.
- Each environment has its own **state file** and, ideally, its own identity and subscription. Use a read-only identity for PR plans if you want to be stricter.
- The saved plan is applied with the **same Terraform version, provider versions, and code**. Commit `.terraform.lock.hcl` and pin the Terraform version. If the state changes between plan and apply, Terraform rejects the stale plan; run the pipeline again.
- The plan file can contain **sensitive values**. Keep artifact retention short, limit who can read the repository, and never commit plan files.
- Pin third-party actions (Trivy, github-script) to a full commit SHA; tags can be moved.
- Manual changes in the portal cause drift. Run a scheduled `terraform plan` to detect it.

## Common problems

| Problem | Likely cause | Fix |
| --- | --- | --- |
| `AADSTS70021: No matching federated identity record found` | The token subject does not match any federated credential (for example, the job uses `environment: production` but only a branch credential exists) | Add a credential with the exact subject shown in the error |
| `Unable to get ACTIONS_ID_TOKEN_REQUEST_URL` | Missing `id-token: write` permission, or a PR from a fork | Add the permission; fork PRs do not get OIDC tokens by design |
| `AuthorizationFailed` on the role assignment | The identity can create resources but cannot assign roles | Grant `Role Based Access Control Administrator` (with a condition) or `User Access Administrator` |
| Backend `403` or `KeyBasedAuthenticationNotPermitted` | No data-plane role on the state storage account | Grant `Storage Blob Data Contributor` and set `use_azuread_auth = true` |
| `Error acquiring the state lock` | A previous run crashed, or two runs overlap | Use `concurrency`; after checking no run is active, `terraform force-unlock <lock-id>` |
| `Saved plan is stale` | Something changed the state after the plan | Run the pipeline again to create a fresh plan |
| Trivy fails the build | A HIGH or CRITICAL misconfiguration | Fix the code, or add a documented ignore for an accepted risk |
| `fmt -check` fails | Code not formatted | Run `terraform fmt -recursive` locally and commit |

## Clean up

```bash
cd environments/prod
terraform init -backend-config=backend.hcl
terraform destroy

az ad app delete --id $APP_ID
```

In a real project, destroy through the pipeline (for example a separate, approved `destroy` workflow) rather than from a laptop.

## Interview questions

<details><summary>Q1. Why use OIDC instead of a client secret for Terraform in GitHub Actions?</summary>

With a client secret, a long-lived password is stored in GitHub, must be rotated, and can leak through logs or a compromised workflow. With OIDC, GitHub issues a short-lived signed token for each job. Entra ID trusts it only if the issuer, audience, and subject match a federated credential, for example `repo:<org>/<repo>:environment:production`. So only that repository, branch, or environment can log in, and there is nothing to rotate. In the workflow I set `id-token: write`, `ARM_USE_OIDC=true`, and the client, tenant, and subscription IDs.

</details>

<details><summary>Q2. How does manual approval work in GitHub Actions?</summary>

I create a GitHub environment called `production` and add required reviewers, and optionally restrict it to the `main` branch. The `apply` job sets `environment: production`. When the run reaches that job, it pauses with "Waiting for review". A reviewer checks the plan and clicks approve, then the job runs. The environment also changes the OIDC subject, so only approved production jobs can get the production identity.

</details>

<details><summary>Q3. Why save the plan to a file and apply that file?</summary>

`terraform plan -out=tfplan` freezes the exact set of changes. The reviewer approves that plan, and `terraform apply tfplan` applies exactly those changes, with no new surprises from code or state that changed in between. If the state changed, Terraform rejects the stale plan. The plan must be applied with the same code and provider versions, and it can contain sensitive values, so the artifact is kept for a short time and access is limited.

</details>

<details><summary>Q4. How does the tfsec or Trivy security gate work?</summary>

tfsec is now part of Trivy. `trivy config` scans the Terraform code for misconfigurations, such as a public storage account, ACR with the admin user enabled, or AKS without network policy. I run it after `validate` and before `plan`, with `severity: HIGH,CRITICAL` and `exit-code: 1`. If it finds a problem, the job fails and the PR cannot be merged because `main` requires the check. Accepted risks are ignored with a documented reason, not by disabling the scan.

</details>

<details><summary>Q5. How do you use AI tools safely for infrastructure as code?</summary>

I use an AI CLI to scaffold modules, explain code, and suggest fixes for errors, which saves setup time. But I treat the output as a draft: I read every line, run `fmt`, `validate`, and `plan`, and check the plan carefully. I never paste secrets, state, or plan files into the tool. I pin provider and action versions myself, and the same pipeline controls apply: security scan, code review, and manual approval before anything reaches production.

</details>
