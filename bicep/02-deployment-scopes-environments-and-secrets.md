# Bicep: Deployment, Scopes, Environments, and Secrets

> Deploying Bicep files, supported deployment scopes, handling multiple environments, and securing secrets.

## Interview Questions

<details><summary>Q1. [Basic] How do you deploy a Bicep file?</summary>

**Answer:**

For resource-group scope:

```bash
az bicep build --file main.bicep
az deployment group validate \
  --resource-group rg-app-prod \
  --template-file main.bicep \
  --parameters @prod.bicepparam
az deployment group what-if \
  --resource-group rg-app-prod \
  --template-file main.bicep \
  --parameters @prod.bicepparam
az deployment group create \
  --name app-$(date +%Y%m%d%H%M%S) \
  --resource-group rg-app-prod \
  --template-file main.bicep \
  --parameters @prod.bicepparam
```

CI runs lint/build, validation, policy and security checks, and what-if. A reviewer approves the production diff, and a workload identity does the actual deploy.

Afterward I check the deployment operations, policy results, resource health, diagnostics, and run an application smoke test.

</details>

<details><summary>Q2. [Basic] What deployment scopes does Bicep support?</summary>

**Answer:**

Bicep supports resource group, subscription, management group, and tenant scopes, set using `targetScope`. The scope you choose controls which resource types are available and which deployment command you use.

```bicep
targetScope = 'subscription'

param location string

resource rg 'Microsoft.Resources/resourceGroups@2024-03-01' = {
  name: 'rg-app-prod'
  location: location
}
```

Subscription scope can create resource groups and policy assignments. Management-group and tenant deployments support broader governance work. I use the narrowest scope that gets the job done, and keep high-privilege governance deployments separate from application deployments.

Cross-scope modules make ownership clear.

</details>

<details><summary>Q3. [Intermediate] How do you handle different environments in Bicep?</summary>

**Answer:**

I keep the reusable modules common across environments, and use `.bicepparam` files or pipeline inputs for anything environment-specific and non-secret.

```bicep
using './main.bicep'

param environment = 'prod'
param skuName = 'P1v3'
param instanceCount = 3
```

Dev and production deploy to separate resource groups or subscriptions, with separate identities and approvals. I only add conditions for genuinely optional capabilities — not to pile up environment checks until the template becomes hard to follow.

Secrets come from Key Vault or a secure deployment input, never from a plain parameter.

The pipeline renders what-if for each environment, checks Azure Policy, and promotes the same module version through each stage. Post-deployment checks confirm tags, networking, diagnostics, capacity, and that the application actually behaves correctly.

</details>

<details><summary>Q4. [Intermediate] How do you secure secrets in Bicep deployments?</summary>

**Answer:**

I mark secret parameters with `@secure()` so the values don't show up in normal deployment history, and I avoid outputting them.

```bicep
@secure()
param administratorPassword string
```

Ideally, the workload uses a managed identity and pulls secrets from Key Vault directly. That way Bicep only deploys the identity, the role assignment, and the secret reference — it never handles the secret value itself.

CI authenticates with workload identity federation, and only reads protected values when a resource API genuinely requires them.
I check what-if output, logs, parameter files, outputs, and generated templates for any leakage. Key Vault access follows least privilege — only the permissions actually needed — plus private networking where required, audit logging, rotation, and recovery protection.

</details>
