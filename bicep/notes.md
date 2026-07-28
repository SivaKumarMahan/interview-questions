# Azure File Share Backup Automation with Bicep

The project provisions and protects an Azure File Share using repeatable infrastructure code:

1. Create or reference a Storage Account and File Share.
2. Create a Recovery Services vault in a supported region.
3. Register the Storage Account with the vault.
4. Define an Azure Files backup policy with the required schedule and retention.
5. Create the protected item that associates the File Share with the policy.
6. Deploy with Azure CLI and verify both protection status and a restore point.

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

Production considerations include supported-region and API-version validation, soft delete, immutability where required, private networking, least-privilege (minimum required access) deployment identity, retention and cost, alerting on backup failure, and regular restore tests.

A successful deployment is not proof of recoverability; I verify an actual restore into an isolated location.
