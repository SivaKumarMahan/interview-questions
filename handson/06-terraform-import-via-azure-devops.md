# Hands-on 6: Import Existing Azure Resources into Terraform with an Azure DevOps Pipeline

> Bring resource groups that were created by hand under Terraform management, using a nested-map module structure and an Azure DevOps pipeline, without recreating anything.

**Time:** about 90 minutes. **Level:** Intermediate.

## What you practise

- Writing Terraform configuration that matches resources that already exist
- Config-driven `import` blocks (Terraform 1.5+), with `for_each` (Terraform 1.7+)
- `terraform plan -generate-config-out` to draft configuration
- The classic `terraform import` command with module and `for_each` addresses
- Running the import from Azure DevOps with workload identity
- The safety rule: after import, `terraform plan` must show no changes

## Prerequisites

| Item | Purpose |
| --- | --- |
| Azure subscription with existing resource groups (for example `rg-app`, `rg-data`) | Resources to import |
| Terraform 1.7 or later, azurerm provider 4.x | `import` blocks with `for_each` |
| Storage account `companytfstate` in `tfstate-rg`, container `tfstate` | Remote state |
| Azure DevOps project, service connection `azure-wif-connection` | Workload identity federation with access to the subscription and state account |
| Environment `terraform-import` with an approval check | Approval before the import is written to state |

## Flow

```text
Existing Azure resources (created manually)
        |
        v
Write matching config (nested map -> module.rg[for_each])
        |
        v
import blocks (or terraform import) in the pipeline
        |
        v
terraform plan  -> must show "N to import, 0 to add, 0 to change, 0 to destroy"
        |
        v
Approval -> terraform apply (writes the imported resources to state)
        |
        v
terraform plan again -> "No changes"
```

## Steps

### 1. List what exists

```bash
az group list --query "[?starts_with(name, 'rg-')].{name:name, location:location, tags:tags}" -o json
az group show -n rg-app --query id -o tsv
# /subscriptions/<sub-id>/resourceGroups/rg-app
```

Copy the exact IDs, names, locations, and tags. Your configuration must match them.

### 2. Create the module structure

```text
import-lab/
├── modules/
│   └── resource_group/
│       ├── main.tf
│       ├── variables.tf
│       └── outputs.tf
├── main.tf
├── variables.tf
├── imports.tf
├── backend.tf
├── terraform.tfvars
└── azure-pipelines.yml
```

`modules/resource_group/main.tf`:

```hcl
resource "azurerm_resource_group" "this" {
  name     = var.name
  location = var.location
  tags     = var.tags

  lifecycle {
    prevent_destroy = true   # imported resources must not be deleted by mistake
  }
}
```

`modules/resource_group/variables.tf`:

```hcl
variable "name" { type = string }
variable "location" { type = string }
variable "tags" {
  type    = map(string)
  default = {}
}
```

`modules/resource_group/outputs.tf`:

```hcl
output "id" { value = azurerm_resource_group.this.id }
output "name" { value = azurerm_resource_group.this.name }
```

`prevent_destroy` cannot be set per instance, so it applies to every resource group this module creates. That is what you want for imported, critical resource groups.

### 3. Describe the existing resources as a nested map

`variables.tf`:

```hcl
variable "subscription_id" {
  type = string
}

variable "resource_groups" {
  type = map(object({
    name     = string
    location = string
    tags     = optional(map(string), {})
  }))
}
```

`terraform.tfvars`:

```hcl
resource_groups = {
  rg-app = {
    name     = "rg-app"
    location = "westeurope"
    tags     = { owner = "platform", env = "dev" }
  }
  rg-data = {
    name     = "rg-data"
    location = "westeurope"
    tags     = { owner = "data" }
  }
}
```

`main.tf`:

```hcl
provider "azurerm" {
  features {}
  subscription_id = var.subscription_id
}

module "rg" {
  source   = "./modules/resource_group"
  for_each = var.resource_groups

  name     = each.value.name
  location = each.value.location
  tags     = each.value.tags
}
```

`backend.tf`:

```hcl
terraform {
  required_version = ">= 1.7.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
  }

  backend "azurerm" {}
}
```

Pass `subscription_id` with `TF_VAR_subscription_id` or in tfvars. The values in tfvars must match Azure exactly: same name, same location, same tags.

### 4. Add `import` blocks (recommended)

`imports.tf`:

```hcl
import {
  for_each = var.resource_groups
  to       = module.rg[each.key].azurerm_resource_group.this
  id       = "/subscriptions/${var.subscription_id}/resourceGroups/${each.value.name}"
}
```

Why this is the safer way:

- The import is part of the plan. You see it in `terraform plan` before anything is written to state.
- It is code. It goes through a pull request, review, and the normal pipeline.
- One block imports every entry in the map, using the same keys as the module.

Rules:

- `import` blocks must be in the root module, but `to` can point into a child module.
- `for_each` inside `import` needs Terraform 1.7 or later. On 1.5 and 1.6, write one `import` block per resource with a fixed key, for example `to = module.rg["rg-app"].azurerm_resource_group.this`.
- After a successful apply, you can delete `imports.tf`. Leaving it is harmless, because Terraform skips resources that are already in state.

### 5. Optional: let Terraform draft the configuration

If you do not know all the attributes, Terraform can write a draft for you. Config generation works with a plain `import` block that points at a root-module resource with no configuration yet:

```hcl
# generate.tf (temporary)
import {
  to = azurerm_resource_group.draft_rg_app
  id = "/subscriptions/<sub-id>/resourceGroups/rg-app"
}
```

```bash
terraform plan -generate-config-out=generated.tf
```

Open `generated.tf`, copy the values (location, tags) into `terraform.tfvars`, then delete `generate.tf` and `generated.tf`. Do not keep both, or the same resource is managed twice.

### 6. The classic CLI way

`terraform import` writes to state immediately. There is no plan and no review, so use it with care.

```bash
terraform init

terraform import 'module.rg["rg-app"].azurerm_resource_group.this' \
  /subscriptions/<sub-id>/resourceGroups/rg-app

terraform import 'module.rg["rg-data"].azurerm_resource_group.this' \
  /subscriptions/<sub-id>/resourceGroups/rg-data
```

Quoting:

- In Bash, put the whole address in single quotes, so the shell keeps the double quotes around the key.
- In PowerShell, escape the inner quotes: `terraform import 'module.rg[\"rg-app\"].azurerm_resource_group.this' <id>`, or use a variable.
- In cmd.exe: `terraform import "module.rg[\"rg-app\"].azurerm_resource_group.this" <id>`.

The module block and the map entry must already exist in the configuration, or the import fails with "Configuration for import target does not exist".

### 7. Back up the state first

```bash
terraform state pull > state-backup-$(date +%Y%m%d%H%M).tfstate
```

Also turn on blob versioning and soft delete on the state storage account:

```bash
az storage account blob-service-properties update \
  --account-name companytfstate -g tfstate-rg \
  --enable-versioning true \
  --enable-delete-retention true --delete-retention-days 30
```

The backup file can contain secrets. Store it somewhere private, not in Git.

### 8. Create the pipeline

`azure-pipelines.yml`:

```yaml
trigger: none                       # run manually for imports

parameters:
  - name: importMode
    displayName: Import mode
    type: string
    default: blocks
    values:
      - blocks                      # import blocks in plan/apply
      - cli                         # classic terraform import commands

pool:
  vmImage: ubuntu-latest

variables:
  azureSubscription: azure-wif-connection
  tfVersion: '1.9.8'
  tfDir: $(System.DefaultWorkingDirectory)

stages:
  - stage: Plan
    jobs:
      - job: ImportPlan
        steps:
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
              backendAzureRmKey: import-lab.tfstate

          - task: AzureCLI@2
            displayName: Back up state, import (CLI mode), and plan
            inputs:
              azureSubscription: $(azureSubscription)
              scriptType: bash
              scriptLocation: inlineScript
              addSpnToEnvironment: true       # exposes servicePrincipalId, tenantId, idToken
              workingDirectory: $(tfDir)
              inlineScript: |
                set -euo pipefail

                # Terraform authentication with workload identity (OIDC)
                export ARM_CLIENT_ID="$servicePrincipalId"
                export ARM_TENANT_ID="$tenantId"
                export ARM_OIDC_TOKEN="$idToken"
                export ARM_USE_OIDC=true
                export ARM_SUBSCRIPTION_ID="$(az account show --query id -o tsv)"
                export TF_VAR_subscription_id="$ARM_SUBSCRIPTION_ID"

                terraform state pull > state-backup.tfstate

                if [ "${{ parameters.importMode }}" = "cli" ]; then
                  for key in rg-app rg-data; do   # map keys equal the RG names here
                    addr="module.rg[\"$key\"].azurerm_resource_group.this"
                    if terraform state show "$addr" > /dev/null 2>&1; then
                      echo "$addr is already in state, skipping"
                    else
                      terraform import -input=false "$addr" \
                        "/subscriptions/$ARM_SUBSCRIPTION_ID/resourceGroups/$key"
                    fi
                  done
                fi

                terraform plan -input=false -out=tfplan

                # Safety check: fail if the plan deletes or replaces anything
                terraform show -json tfplan > plan.json
                BAD=$(jq '[.resource_changes[]? | select(.change.actions | index("delete"))] | length' plan.json)
                if [ "$BAD" -gt 0 ]; then
                  echo "##vso[task.logissue type=error]Plan deletes or replaces $BAD resource(s). Fix the configuration."
                  exit 1
                fi

          - publish: $(tfDir)/state-backup.tfstate
            artifact: state-backup
          - publish: $(tfDir)/tfplan
            artifact: tfplan

  - stage: Apply
    dependsOn: Plan
    jobs:
      - deployment: ApplyImport
        environment: terraform-import    # approval check configured here
        strategy:
          runOnce:
            deploy:
              steps:
                - checkout: self
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
                    backendAzureRmKey: import-lab.tfstate
                - task: TerraformTask@5
                  displayName: Terraform apply (saved plan)
                  inputs:
                    provider: azurerm
                    command: apply
                    workingDirectory: $(tfDir)
                    environmentServiceNameAzureRM: $(azureSubscription)
                    commandOptions: 'tfplan'
```

Notes:

- `addSpnToEnvironment: true` makes the service connection details available to the script. With workload identity, `idToken` is a short-lived OIDC token, and the `ARM_*` variables pass it to both the azurerm provider and the azurerm backend.
- Another option is to run Terraform with the Azure CLI login of the task: set `ARM_USE_CLI=true` (the default when no other credentials are set) and `ARM_SUBSCRIPTION_ID`. For the backend, also set `use_azuread_auth = true` if storage account keys are disabled.
- You can also run commands through `TerraformTask@5` with `command: custom` and `customCommand: import`, but a loop over many resources is easier in a script.
- The state backup artifact can contain secrets. Restrict access to the pipeline artifacts.
- In CLI mode, the import is written to state in the Plan stage, before the approval. Blocks mode is safer, because nothing is written until the approved apply.

### 9. Read the plan

Good plan in blocks mode:

```text
module.rg["rg-app"].azurerm_resource_group.this: Preparing import... [id=/subscriptions/<sub-id>/resourceGroups/rg-app]
module.rg["rg-data"].azurerm_resource_group.this: Preparing import... [id=/subscriptions/<sub-id>/resourceGroups/rg-data]

Plan: 2 to import, 0 to add, 0 to change, 0 to destroy.
```

A plan that shows `~ update in-place` on an imported resource means your configuration does not match Azure, for example different tags. Fix the tfvars and plan again.

A plan that shows `-/+ destroy and then create replacement` must never be applied. For a resource group, this usually means the name or location in tfvars is different from Azure. Destroying a resource group deletes everything in it.

### 10. Verify

After the approved apply, run:

```bash
terraform state list
terraform plan
```

Expected:

```text
module.rg["rg-app"].azurerm_resource_group.this
module.rg["rg-data"].azurerm_resource_group.this

No changes. Your infrastructure matches the configuration.
```

`No changes` is the goal. The resource groups now belong to Terraform, and nothing was recreated. Check in the Azure portal that the resource groups and their contents are unchanged.

### 11. Import the children next

Import in dependency order: resource groups first, then VNets, then subnets and NSGs, then NICs and VMs. Each child module references its parent by key, for example `module.rg[each.value.rg_key].name`, so the parent must be in configuration first. Add one layer per pull request, and confirm `No changes` after each layer.

## Important points

- **The key rule:** after import, `terraform plan` must show `No changes`. Change the configuration until it does. Never apply a plan that destroys or replaces an imported resource.
- Import only adds resources to state. It does not create or change anything in Azure.
- `import` blocks are reviewable and run through plan. `terraform import` writes to state immediately.
- Back up the state, and use blob versioning on the state storage account.
- Add `lifecycle { prevent_destroy = true }` on critical imported resources.
- Use the same map keys in tfvars, module `for_each`, and import blocks, so addresses are predictable.
- Lock down manual changes after the migration (RBAC, Azure Policy), or the code drifts again.

## Common problems

| Problem | Likely cause | Fix |
| --- | --- | --- |
| "Resource already managed by Terraform" | Address is already in state | Check with `terraform state list`; skip it or remove with `terraform state rm` only if it is wrong |
| "parsing ... expected the segment resourceGroups" or ID not found | Wrong ID casing or format, such as `resourcegroups` | Copy the ID from `az group show --query id -o tsv` |
| Plan wants to replace the resource group | Name or location in tfvars differs from Azure | Make tfvars match Azure exactly |
| Plan wants to update tags | Tags in Azure differ from tfvars | Add the existing tags to tfvars, or accept the change on purpose |
| "Configuration for import target does not exist" | Module call or map key missing | Add the entry to `resource_groups` before importing |
| `Index value required` or quote errors on the CLI | Shell removed the quotes around the key | Use single quotes around the whole address in Bash |
| "Error acquiring the state lock" | Another run holds the lock | Wait; if the run died, check and run `terraform force-unlock <lock-id>` |
| 403 when reading state | Identity lacks access to the storage account | Grant `Storage Blob Data Contributor` on the state account |

## Interview questions

<details><summary>Q1. How do you bring manually created Azure resources under Terraform?</summary>

First I write configuration that matches the existing resources, usually with modules and a nested map in tfvars. Then I import them, preferably with `import` blocks so the import is part of the plan and goes through review. I run `terraform plan` until it shows only imports and no changes or destroys, apply after approval, and confirm that a final plan shows `No changes`.

</details>

<details><summary>Q2. What is the difference between <code>import</code> blocks and <code>terraform import</code>?</summary>

`terraform import` is a CLI command that writes one resource into state immediately, with no plan and no review. `import` blocks (Terraform 1.5+) are code. They are shown in `terraform plan`, can be reviewed in a pull request, can use `for_each` (1.7+), and the state is changed only on `apply`. Import blocks can also generate draft configuration with `-generate-config-out`.

</details>

<details><summary>Q3. After an import, the plan wants to replace the resource. What do you do?</summary>

I do not apply it. A replace means an attribute that forces a new resource, such as name or location, is different in my configuration. I compare the plan output with the real resource (`az group show`), fix the configuration, and plan again until the plan shows `No changes` or only intended in-place updates.

</details>

<details><summary>Q4. How do you write the address of a module with <code>for_each</code> in <code>terraform import</code>?</summary>

The address is `module.<name>["<key>"].<resource_type>.<resource_name>`, for example `module.rg["rg-app"].azurerm_resource_group.this`. In Bash I wrap the whole address in single quotes so the double quotes around the key are not removed by the shell. PowerShell and cmd need escaped inner quotes.

</details>

<details><summary>Q5. How do you make an import safe in a pipeline?</summary>

I back up the state and enable blob versioning on the state account. I use import blocks so the import is in the plan. A script step fails the build if the plan contains any delete or replace. The plan is saved and applied only after an environment approval. Critical resources have `prevent_destroy`, and I import in order: resource groups first, then their children.

</details>
