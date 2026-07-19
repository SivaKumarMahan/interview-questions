# Terraform Cheatcode

## Safe workflow

```bash
terraform version
terraform fmt -check -recursive
terraform init
terraform validate
terraform plan -out=tfplan
terraform show tfplan
terraform apply tfplan
terraform output
```

Use a reviewed saved plan tied to the same commit. Validate the actual service after apply.

## State and import

```bash
terraform state list
terraform state show '<address>'
terraform state pull > state-backup.json
terraform import '<address>' '<provider-id>'
terraform state mv '<old-address>' '<new-address>'
terraform plan -refresh-only
```

State can contain secrets. Store backups securely and confirm the exact backend/workspace before state operations. Avoid manual JSON editing. `terraform taint` is deprecated for most workflows; prefer `terraform apply -replace='<address>'` after reviewing the full plan.

## Workspaces

```bash
terraform workspace list
terraform workspace show
terraform workspace new <name>
terraform workspace select <name>
```

Workspaces are not always the right production boundary; separate root modules/state often give clearer identities and blast radius.

## Useful inspection

```bash
terraform providers
terraform graph
terraform console
terraform show -json tfplan
terraform plan -detailed-exitcode
```

Detailed exit codes are 0=no differences, 1=error, and 2=changes.

## Nested map and `for_each`

```hcl
variable "items" {
  type = map(object({
    name     = string
    location = string
    tier     = string
  }))
}

resource "azurerm_storage_account" "this" {
  for_each                 = var.items
  name                     = each.value.name
  location                 = each.value.location
  account_tier             = each.value.tier
  resource_group_name      = var.resource_group_name
  account_replication_type = "LRS"
}
```

## Module skeleton

```text
root/
├── main.tf
├── variables.tf
├── outputs.tf
├── providers.tf
├── versions.tf
└── modules/
    ├── network/
    ├── compute/
    └── database/
```

Pin provider/module versions, document inputs/outputs, test modules, and keep environment orchestration at the root.
