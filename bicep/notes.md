# Azure File Share Backup Automation with Bicep

This project sets up and protects an Azure File Share using repeatable infrastructure code. The steps are:

1. Create or reference a Storage Account and File Share.
2. Create a Recovery Services vault in a supported region.
3. Register the Storage Account with the vault.
4. Define an Azure Files backup policy with the schedule and retention you need.
5. Create the protected item that links the File Share to the policy.
6. Deploy with Azure CLI, then check both the protection status and that a restore point exists.

A minimal vault resource is:

```bicep
param location string = resourceGroup().location
param vaultName string

resource vault 'Microsoft.RecoveryServices/vaults@2023-08-01' = {
  name: vaultName
  location: location
  sku: {
    name: 'RS0'
    tier: 'Standard'
  }
  properties: {}
}
```

## Deployment flow

```bash
az deployment group what-if \
  --resource-group <resource-group> \
  --template-file main.bicep \
  --parameters vaultName=<vault-name>

az deployment group create \
  --resource-group <resource-group> \
  --template-file main.bicep \
  --parameters vaultName=<vault-name>
```

Before this goes to production, I check a few things: the region and API version are supported, soft delete is on, immutability is set where it's required, networking is private, and the deployment identity has only the access it needs. I also plan for retention and cost, set up alerts for backup failures, and run restore tests on a regular schedule.

A successful deployment doesn't prove the backup can actually be restored. I always test a real restore into an isolated location to be sure.
