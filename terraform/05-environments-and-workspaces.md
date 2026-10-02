# Terraform: Environments and Workspaces

> Managing dev, QA, and production with folders, workspaces, and separate state, promoting changes between environments, and a full Azure environment pattern.

## Key Concepts

### Managing multiple environments

```text
modules/                shared code
environments/
  dev/    backend.tf  dev.tfvars
  test/   backend.tf  test.tfvars
  prod/   backend.tf  prod.tfvars
```

1. Separate backend key per environment.
2. Separate credentials and approvals.
3. Same module version, different values.
4. Consistent naming, for example `app-dev-vpc` and `app-prod-vpc`.
5. The pipeline picks the folder, so a job cannot mix dev code with prod credentials.

### An Azure setup pattern

#### Modules to build

```text
resource group
virtual network + subnets + NSGs
private DNS and private endpoints
storage account
key vault
log analytics + application insights
container registry
AKS cluster
database
role assignments
```

#### How to split state

By lifecycle and ownership, not by team preference:

```text
connectivity-state   hub network, DNS, firewall
platform-state       AKS, ACR, monitoring
data-state           databases, storage
app-state            application resources
```

#### Pipeline

```bash
terraform fmt -check
terraform init
terraform validate
checkov -d .
terraform plan -out=tfplan
# approval
terraform apply tfplan
```

#### After apply, check

Private DNS resolves, routes work, RBAC has propagated, diagnostics are arriving in Log Analytics, AKS can pull from ACR, and the application health endpoint responds.

#### Secrets

Terraform creates the Key Vault and grants access to the managed identity. The application reads the secret at runtime, so the value never passes through Terraform state.

## Interview Questions

### 1. How do you reuse the same code for different environments?

#### Folder layout

```text
modules/
  vpc/
  compute/
  database/
environments/
  dev/
    main.tf
    backend.tf
    dev.tfvars
  prod/
    main.tf
    backend.tf
    prod.tfvars
```

#### How it works

Both environments call the same module version and pass different values.

```hcl
module "vpc" {
  source  = "git::https://github.com/myorg/tf-modules.git//vpc?ref=v1.4.0"
  cidr    = var.vpc_cidr
  subnets = var.subnets
}
```

Dev passes a small CIDR and one NAT gateway. Prod passes a bigger CIDR and one NAT gateway per zone.

#### Interview answer

"I keep the common code in versioned modules and give each environment its own small root folder with its own backend, variables, and approvals. Dev and prod call the same module version but pass different values. I avoid writing `if environment == prod` inside modules, because that hides the differences."

### 2. How do you manage deployments for multiple environments?

#### Rules I follow

1. Each environment has its own folder, backend key, and variables file.
2. Each environment has its own cloud account or subscription where possible.
3. Each environment has its own identity and approval level.
4. Shared modules are versioned, and each environment pins a version.
5. The pipeline maps one folder to exactly one environment, so a dev job can never use prod credentials.

#### Promotion flow

```text
dev  -> test the change works
test -> test upgrade and recovery
prod -> same module version, different values, with approval
```

#### Interview answer

"Each environment gets its own root folder, state key, credentials, variables, and approval. The shared logic lives in versioned modules that each environment pins. The pipeline maps a folder to exactly one environment so a job cannot mix dev code with prod credentials. A change is proven in dev and test before the same module version is promoted to production."

### 3. How do you manage multiple environments? *(scenario)*

#### Two ways

**Workspaces** — same code, different state:

```bash
terraform workspace new dev
terraform workspace select dev
terraform apply -var-file=dev.tfvars
```

**Separate folders** — safer for long-lived environments:

```text
environments/dev/    backend.tf  dev.tfvars
environments/test/   backend.tf  test.tfvars
environments/prod/   backend.tf  prod.tfvars
```

Each folder gets its own backend key, credentials, and approval.

#### Interview answer

"For short-lived or nearly identical environments I use workspaces. For dev, test, and production I prefer separate folders with their own backend, variables, credentials, and approvals, because it is obvious which environment you are in and a dev job can never touch production state."

### 4. How do you manage dev, QA, and prod with Terraform? *(scenario)*

#### Layout

```text
modules/                 shared, versioned code
environments/
  dev/    backend.tf  dev.tfvars
  qa/     backend.tf  qa.tfvars
  prod/   backend.tf  prod.tfvars
```

#### What differs per environment

| Setting | Dev | Prod |
|---|---|---|
| Instance size | Small | Right-sized |
| Node count | 1 | 3 or more |
| Backups | Short retention | Long retention |
| Approval | None | Required |
| Deletion protection | Off | On |

#### Promotion

Prove the change in dev, then QA, then apply the same module version to prod with different values.

#### Interview answer

"Shared modules hold the logic, and each environment has its own folder with its own backend, variables, credentials, and approvals. What differs between environments is values like sizing, retention, and protection settings, not the code itself. A change is proven in dev and QA before the same module version is promoted to production."

### 5. How do you organize a Terraform project for multiple environments?

#### 15.1 Modules

A module is a reusable collection of Terraform resources. Instead of writing the same code multiple times, we create modules and reuse them.

```
modules/
├── network/
├── aks/
├── acr/
├── keyvault/
└── monitoring/
```

Each module has:

```
main.tf
variables.tf
outputs.tf
```

Example root configuration:

```hcl
module "network" {
  source = "./modules/network"

  vnet_name = "prod-vnet"
}
```

**Benefits**

- Reusable code
- Easier maintenance
- Consistent deployments
- Smaller and cleaner root configuration

In production, modules are usually versioned using Git tags or a Terraform Registry, so teams can safely upgrade versions.

#### 15.2 Environments

Different environments should have separate state files.

```
terraform/

modules/

envs/
├── dev/
│   ├── main.tf
│   ├── backend.tf
│   └── terraform.tfvars
│
├── staging/
│   ├── main.tf
│   ├── backend.tf
│   └── terraform.tfvars
│
└── prod/
    ├── main.tf
    ├── backend.tf
    └── terraform.tfvars
```

Each environment has its own backend, its own state and its own variables. This prevents accidental changes across environments.

#### 15.3 Why not use Workspaces?

Terraform Workspaces let you manage multiple environments from the same configuration.

```bash
terraform workspace new dev
terraform workspace new prod
```

The active workspace is selected with:

```bash
terraform workspace select prod
```

Although convenient, many teams avoid workspaces for production because:

- It's easy to select the wrong workspace.
- All workspaces share the same backend configuration.
- Environment differences become hidden in code using `terraform.workspace`.
- Access control and permissions are harder to separate.

For production, separate directories and separate state files are usually safer and easier to manage.

#### 15.4 Layer the state

Instead of storing everything in one state file, split infrastructure into layers.

```
State 1
Network
- Resource Group
- VNet
- Subnets

State 2
AKS
- Cluster
- Node Pools

State 3
Applications
- Helm Releases
- Kubernetes Resources

State 4
Monitoring
- Log Analytics
- Alerts
```

**Benefits:**

- Smaller blast radius if something goes wrong.
- Faster Terraform operations.
- Teams can work independently.
- Reduced merge conflicts.

#### 15.5 Remote state

Each environment should have its own remote backend.

```
Development
dev.tfstate

Staging
staging.tfstate

Production
prod.tfstate
```

In Azure, these state files are typically stored in an Azure Storage Account with blob leases providing state locking.

#### 15.6 CI/CD pipeline

Avoid running `terraform apply` directly from a developer's laptop.

Typical workflow:

```
Developer
      |
      v
Git Feature Branch
      |
      v
Pull Request
      |
      v
Pipeline
   |
   +-- terraform fmt
   +-- terraform validate
   +-- tflint
   +-- terraform plan
      |
Code Review
      |
Merge
      |
      v
Pipeline
      |
terraform apply
```

This ensures code is reviewed, plans are visible before deployment, and changes are applied consistently.

#### 15.7 Additional best practices

- Use remote state with state locking.
- Keep root modules thin; put most logic into reusable modules.
- Pin provider and module versions to avoid unexpected upgrades.
- Run `terraform fmt`, `terraform validate`, and `tflint` in CI.
- Split infrastructure into multiple state files for better isolation.
- Use pull requests with `terraform plan`, and only run `terraform apply` after approval and merge.

#### 15.8 Interview answer (1-2 minutes)

> "I organize Terraform using reusable modules for components like networking, AKS, ACR, and monitoring. The root configuration simply composes these modules and passes environment-specific variables. For environments such as development, staging, and production, I prefer separate directories with their own backend configuration, state file, and terraform.tfvars rather than relying on workspaces. This provides better isolation, clearer permissions, and reduces the risk of deploying to the wrong environment. I also split infrastructure into multiple state files, such as networking, AKS, and applications, to reduce the impact of changes and allow teams to work independently. Finally, all Terraform changes go through a CI/CD pipeline that runs terraform fmt, terraform validate, tflint, and terraform plan during pull requests, with terraform apply executed only after review and approval."

### 6. How do you provision environments end to end? *(scenario)*

#### Pieces

1. `modules/` for reusable components.
2. `environments/<env>.tfvars` for values.
3. A pipeline that picks the environment from the branch or an input.
4. Environment-specific sizing, for example small nodes in dev, larger in prod.
5. Application deployment handled by a separate tool such as Argo CD or Helm.
6. Cost control in dev: scale down or destroy outside working hours.

#### Pipeline snippet

```yaml
- run: terraform init -backend-config=envs/${{ inputs.env }}.backend.hcl
- run: terraform plan -var-file=envs/${{ inputs.env }}.tfvars -out=tfplan
```

#### Interview answer

"Reusable modules plus one tfvars file per environment, and the pipeline selects the backend config and var file for the chosen environment. Terraform builds the platform, for example the cluster and node groups sized per environment, and application deployment is handled separately by Argo CD or Helm. For dev I add a scheduled scale-down or destroy outside working hours to control cost, while production stays permanent."

### 7. Workspaces or separate state files?

| CLI workspaces | Separate state files |
|---|---|
| One config, one backend, different state per workspace | Separate folder, backend, and variables per environment |
| Quick to create | More structure to set up |
| Easy to forget which workspace you are in | The folder makes it obvious |
| Shares backend and credentials | Separate credentials and approvals possible |
| Good for short-lived or test copies | Better for long-lived dev, test, prod |

#### Commands

```bash
terraform workspace new dev
terraform workspace select dev
terraform workspace list
```

#### Interview answer

"Workspaces reuse one configuration and backend with a different state per workspace. They are handy for temporary or nearly identical environments, but it is easy to forget which one is selected and they share backend and credentials. For long-lived dev, test, and production I prefer separate root folders and state files, because credentials, approvals, and blast radius are then explicit."

### 8. How do you manage multiple Terraform workspaces across environments?

**Interviewer:** How do you manage multiple Terraform workspaces across environments?

In most production environments, I prefer separate state files and separate directories for each environment rather than relying only on Terraform workspaces.

For example:

```
terraform/
├── envs/
│   ├── dev/
│   ├── test/
│   └── prod/
└── modules/
    ├── network/
    ├── aks/
    └── sql/
```

Each environment has:

- Its own remote backend (separate state file)
- Its own `terraform.tfvars`
- Its own pipeline
- Separate access permissions

This reduces the risk of accidentally applying changes to the wrong environment.

I use Terraform workspaces only when the infrastructure is almost identical and the only difference is configuration values, such as creating temporary environments or feature branches.

When using workspaces, I create and switch them like this:

```bash
terraform workspace new dev
terraform workspace new test
terraform workspace new prod

terraform workspace select dev
terraform plan
terraform apply
```

I can also reference the current workspace inside the code:

```hcl
resource "azurerm_resource_group" "rg" {
  name = "rg-${terraform.workspace}"
}
```

#### 10.1 Best practices I follow

- Keep a separate remote state for each environment.
- Use modules so infrastructure code is reusable.
- Store environment-specific values in `.tfvars` files.
- Protect production with approval gates in the CI/CD pipeline.
- Lock the state using the Azure Storage backend to prevent concurrent updates.
- Use the same Terraform version and provider versions across environments.

#### 10.2 Short interview conclusion

> "For production environments, I prefer separate directories and separate remote state files for dev, test, and prod because it's safer and provides better isolation. I use Terraform workspaces only for nearly identical environments or temporary deployments where only configuration values change."

### 9. What are the benefits of modules and workspaces?

#### Modules

- Reuse the same tested code everywhere
- Standard tags, encryption, and naming
- Teams do not copy and paste
- Change one module, upgrade many projects

#### Workspaces

- Same code, separate state per environment
- Quick to create for short-lived copies

#### Typical layout

```text
terraform/
  modules/
    networking/
    database/
    compute/
  environments/
    dev/
    test/
    prod/
  global/
    iam/
    dns/
```

#### Interview answer

"Modules give reuse and consistency, so every team gets the same tagging, encryption, and naming without copying code. Workspaces let the same configuration hold separate state per environment. Together they reduce duplication, but for long-lived production boundaries I still prefer separate folders and state files over workspaces, because permissions and blast radius are clearer."
