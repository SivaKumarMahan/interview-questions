# Bicep: Fundamentals and Structure

> What Bicep is, why to use it over ARM templates, file structure, modules, passing values, and existing vs new resources.

## Interview Questions

<details><summary>Q1. [Basic] What is Azure Bicep?</summary>

**Answer:**

Bicep is Microsoft's declarative language for deploying Azure Resource Manager (ARM) resources. I describe the Azure state I want, and ARM figures out the dependency order and does the idempotent create/update work — meaning it's safe to run the same deployment again.

Bicep compiles down to an ARM JSON template, so it uses the same Azure resource APIs. There's no separate state file to manage.

```bicep
param location string = resourceGroup().location

resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: 'st${uniqueString(resourceGroup().id)}'
  location: location
  sku: { name: 'Standard_LRS' }
  kind: 'StorageV2'
  properties: {
    supportsHttpsTrafficOnly: true
    minimumTlsVersion: 'TLS1_2'
  }
}
```

I keep Bicep in Git, validate it and run what-if in CI, and deploy with an identity that has only the access it needs. Afterward I check the Azure Activity Log, the deployment output, policy compliance, and resource health.

</details>

<details><summary>Q2. [Basic] Why use Bicep instead of raw ARM templates?</summary>

**Answer:**

Bicep is more concise and easier to read than ARM JSON. It gives you type checking, IntelliSense, symbolic references, modules, loops, and conditions, along with simpler expressions — all while keeping full ARM deployment capability underneath.

For example, referencing `storage.id` creates an implicit dependency automatically. In raw JSON I'd usually need a verbose resource ID and an explicit `dependsOn`. Bicep can also decompile existing ARM templates, which helps with migration.

I choose Bicep for Azure-only infrastructure, when the team wants native ARM integration and doesn't need external state. I'd consider Terraform instead when one workflow has to manage multiple cloud providers, or when its module and provider ecosystem is what the team needs.

The right choice depends on scope, team skills, governance, and whatever platform standards already exist.

</details>

<details><summary>Q3. [Basic] What is the basic structure of a Bicep file?</summary>

**Answer:**

A Bicep file commonly has metadata, parameters, variables, resource declarations, modules, and outputs.

```bicep
@description('Deployment environment')
@allowed(['dev', 'prod'])
param environment string

var tags = {
  environment: environment
  managedBy: 'bicep'
}

resource logWorkspace 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: 'log-${environment}'
  location: resourceGroup().location
  tags: tags
  properties: {}
}

output workspaceId string = logWorkspace.id
```

Parameters are the deployment's inputs. Variables calculate internal values. Resources declare the actual Azure objects. Modules let you reuse other Bicep files, and outputs expose non-sensitive results. I avoid putting secrets in outputs, because deployment history can retain them.

</details>

<details><summary>Q4. [Basic] What are Bicep modules?</summary>

**Answer:**

A module is a reusable Bicep file that gets deployed from another Bicep file. I use modules to keep networking, monitoring, compute, and application resources separate, each with a clear set of inputs and outputs.

```bicep
module network './modules/network.bicep' = {
  name: 'network-${environment}'
  params: {
    environment: environment
    addressPrefix: '10.20.0.0/16'
  }
}
```

Modules can be published to a private Bicep registry in Azure Container Registry and versioned there. I keep each module focused on one job, validate its parameters, document its outputs, pin the published version I use, and test breaking changes in a lower environment first.

I avoid building one large module full of unrelated, conditional resources — it quickly becomes hard to own and unsafe to change.

</details>

<details><summary>Q5. [Intermediate] How do you pass values between Bicep modules?</summary>

**Answer:**

The producing module declares an output, and the parent passes that output into another module as a parameter. This creates an implicit dependency between them.

```bicep
module network './network.bicep' = {
  name: 'network'
  params: { location: location }
}

module app './app.bicep' = {
  name: 'app'
  params: {
    subnetId: network.outputs.appSubnetId
  }
}
```

I pass stable values like resource IDs, names, or endpoints — not entire sensitive objects. If two modules belong to different deployment lifecycles, I'd rather look up an existing resource by ID or name, or use an approved configuration output, than couple every deployment into one giant template.

</details>

<details><summary>Q6. [Basic] What is the difference between <code>existing</code> resources and new resources in Bicep?</summary>

**Answer:**

A normal `resource` declaration tells ARM to create or manage that resource. An `existing` declaration just references a resource that's already there, without redeploying it.

```bicep
resource existingVnet 'Microsoft.Network/virtualNetworks@2023-11-01' existing = {
  name: 'vnet-hub-prod'
  scope: resourceGroup('network-subscription-id', 'rg-hub')
}

output hubVnetId string = existingVnet.id
```

The deployment identity needs read access to that referenced scope. If the name or scope is wrong, the deployment fails once it tries to evaluate the resource's properties.

`existing` is useful when a network or Key Vault has a separate owner and lifecycle. It doesn't import that resource into your current deployment for you to modify.

</details>
