# Bicep: Validation, Troubleshooting, and a Backup Project

> Validating deployments before applying them, troubleshooting failures, and a worked Azure File Share backup automation project.

## Key Concepts

### Azure File Share Backup Automation with Bicep

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

#### Deployment flow

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

## Interview Questions

### 1. How do you validate a Bicep deployment before applying it?

**Answer:**

My validation layers are:

1. The editor's Bicep linter and `az bicep build` for compile and type errors.
2. `az deployment ... validate` for ARM-level validation.
3. `what-if` to see the expected create, modify, and delete changes.
4. Azure Policy and security checks.
5. A test deployment in a lower environment, followed by functional checks.

I pay close attention to deletions, replacements, role assignments, network rules, SKUs, and any properties that what-if can't fully predict. What-if is a useful change artifact to review, but it doesn't replace backups, a staged rollout, or a service-specific recovery plan.

### 2. How do you troubleshoot Bicep deployment failures?

**Answer:**

I start with the failed deployment operation itself, not just the top-level error message:

```bash
az deployment group show -g rg-app-prod -n <deployment-name>
az deployment operation group list \
  -g rg-app-prod -n <deployment-name> -o table
```

I check the error code, resource name, API version, permissions, any policy denial, quota, region/SKU availability, dependency output, naming constraints, and the Activity Log. I try to reproduce the issue through validate/what-if using the same parameters.

Once I've fixed the root cause, I rerun what-if and confirm there's no unintended delete or replacement. ARM deployments can partially create resources before failing, so I check the actual state rather than blindly redeploying or manually deleting resources.

I validate resource health and the dependent application once the deployment succeeds.
### 3. How do you troubleshoot an Azure resource deployment failure?

Use a structured process to find the resource and reason that caused the failure.

#### 1. Check the deployment error

Review the failed deployment in the Azure portal or with the Azure CLI:

```bash
az deployment group show \
  --resource-group <resource-group> \
  --name <deployment-name>
```

Look for the error code, detailed message, and failed resource.

#### 2. Inspect deployment operations

```bash
az deployment operation group list \
  --resource-group <resource-group> \
  --name <deployment-name>
```

The operation history helps identify the exact step that failed.

#### 3. Validate the deployment code

For ARM templates, Bicep, or Terraform, check for:

- Syntax and type errors
- Missing or incorrect parameters
- Invalid resource references
- Incorrect dependency order
- Unsupported or outdated API versions

Validate the deployment before applying it when the tool supports validation or a preview operation.

#### 4. Check access and governance

Confirm that the user, service principal, or managed identity has the required RBAC role at the correct scope. Also check whether an Azure Policy or resource lock is blocking the operation.

Use least privilege: assign only the permissions required by the deployment instead of automatically granting `Owner`.

#### 5. Check Azure constraints

Common causes include:

- A globally unique resource name is already in use.
- The selected SKU is unavailable in the region.
- A subscription or regional quota has been reached.
- The resource type is not registered for the subscription.
- Network, subnet, DNS, or private endpoint settings are invalid.
- A dependent resource does not exist or is in another scope.

#### 6. Review the Activity Log

The Azure Activity Log can show authorization failures, policy denials, and control-plane errors. If a deployment runs in a CI/CD pipeline, inspect the pipeline logs as well.

#### 7. Fix, redeploy, and verify

Correct the template, parameters, access, or Azure configuration. Run validation or a preview, redeploy, and then confirm that every expected resource is healthy.

#### Short interview answer

Start with the deployment error and operation history to identify the failed resource. Then validate the infrastructure code and parameters, verify RBAC and Azure Policy, and check names, regions, SKUs, quotas, API versions, dependencies, and networking. Review the Activity Log for more detail, fix the root cause, redeploy, and verify the result.

#### Worked example: AuthorizationFailed

An ACR deployment fails with `AuthorizationFailed` because the deploying service principal only has the `Reader` role on the resource group. Step 4 above (check access and governance) catches this immediately: `az deployment operation group list` shows the exact operation that was denied, and the fix is to assign the role the deployment actually needs (e.g. `Contributor` scoped to that resource group, or a narrower custom role) rather than reaching for `Owner`. Reassign the role and rerun the pipeline.
