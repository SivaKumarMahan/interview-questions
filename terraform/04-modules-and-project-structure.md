# Terraform: Modules and Project Structure

> Root and child modules, designing reusable and shared modules, module versioning, structuring large projects for many teams, and wiring dependencies between separate stacks.

## Key Concepts

### What is a module?

A module is a folder of Terraform code that you can reuse.

- **Local module:** `./modules/vm`
- **Remote module:** from the registry or a Git repo

#### Why use one

1. Write once, use many times.
2. Keep the code organised.
3. Every team gets the same standards.

#### Example

Instead of copying the same VM block everywhere:

```hcl
module "app_server" {
  source       = "./modules/gcp_vm"
  vm_name      = "app-server"
  machine_type = "e2-medium"
}

module "web_server" {
  source       = "./modules/gcp_vm"
  vm_name      = "web-server"
  machine_type = "e2-small"
}
```

#### Interview answer

"A module is a reusable folder of Terraform code with defined inputs and outputs. Instead of copying the same resource blocks into every project, I put the pattern in a module, version it, and call it with different variables. That gives reuse and also consistent tagging, encryption, and naming."

### Root and child modules

- The folder you run Terraform in is the **root module**.
- Anything called with a `module` block is a **child module**.

#### How values flow

```text
tfvars -> root variables -> module inputs -> resources
resources -> module outputs -> root outputs
```

#### Rules for a good child module

1. One purpose.
2. Typed inputs with validation.
3. Useful outputs.
4. No environment names or credentials inside.
5. Provider configuration stays at the root.
6. Documented and versioned.

### Versioning modules and providers

```hcl
terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.40"
    }
  }
}

module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "5.8.1"
}
```

#### Rules

1. Pin versions in root modules and commit `.terraform.lock.hcl`.
2. Use semantic versioning for your own modules.
3. Upgrade in a dedicated pull request after reading the release notes.
4. Test the upgrade in a lower environment first.
5. Keep a changelog for your modules.

### Module versioning and updates

1. Tag releases: `v1.0.0`, `v1.1.0`, `v2.0.0`.
2. Consumers pin a version.
3. Patch = bug fix, minor = new optional input, major = breaking change.
4. A major version needs a migration note.
5. Test the new version in dev before other teams adopt it.

```hcl
module "vpc" {
  source  = "git::https://github.com/myorg/tf-modules.git//vpc?ref=v1.4.0"
}
```

## Interview Questions

### 1. What is a Terraform module and why use it?

#### What it is

A module is just a folder of Terraform files with inputs and outputs.

- **Root module:** the folder where you run `terraform apply`.
- **Child module:** any folder called with a `module` block.

#### Example

```hcl
module "app_server" {
  source        = "./modules/ec2"
  name          = "app-server"
  instance_type = "t3.small"
  subnet_id     = module.vpc.private_subnet_ids[0]
}
```

#### Why use it

1. Write once, use many times.
2. Standard tags, encryption, and naming everywhere.
3. Teams do not copy and paste dozens of resource blocks.
4. You can version it and upgrade safely.

#### What to avoid

One giant module with 40 boolean flags. Keep modules small and focused.

#### Interview answer

"A module is a folder of Terraform code with defined inputs and outputs. The folder I run Terraform in is the root module, and anything I call with a `module` block is a child module. I use modules so teams do not repeat the same resource blocks and so standards like tagging and encryption are applied everywhere. I keep them small, versioned, and documented."

### 2. How do you make code reusable across projects? *(scenario)*

#### Steps

1. Put the common pattern in a module.
2. Keep it in its own Git repo or a private registry.
3. Tag releases: `v1.0.0`.
4. Consumers pin the version.

```hcl
module "vpc" {
  source  = "git::https://github.com/myorg/tf-modules.git//vpc?ref=v1.2.0"
  cidr    = "10.20.0.0/16"
}
```

#### Rules for a reusable module

- No environment names or account IDs inside
- Typed variables with validation
- Useful outputs
- A README and an example

#### Interview answer

"I move repeated patterns into modules that live in their own repo or a private registry with semantic version tags, and consumers pin a version. The module must not contain environment names, account IDs, or credentials; those come in as validated variables. Every module has a README and a working example so other teams can adopt it without reading the internals."

### 3. How do you organize modules for reuse? *(scenario)*

#### Typical set

```text
modules/
  network/     VPC or VNet, subnets, routing
  compute/     VM, autoscaling, or node pools
  database/    managed database with backups
  iam/         roles and role assignments
  monitoring/  alarms and dashboards
```

#### How teams consume them

```hcl
module "network" {
  source  = "app.terraform.io/myorg/network/azurerm"
  version = "2.1.0"

  address_space = var.address_space
  subnets       = var.subnets
}
```

#### Rules

- One module, one purpose
- No environment names inside
- Version everything
- Document inputs and outputs

#### Interview answer

"I build one module per component, network, compute, database, IAM, and monitoring, each with a clear input and output contract and no environment names inside. They are versioned in a registry or Git and consumers pin a version. That way an improvement to the module can be rolled out team by team instead of surprising everyone at once."

### 4. How do you design modules used by many teams?

#### Module rules

1. Small and focused. One module, one job.
2. Clear inputs with types, defaults, and validation.
3. Useful outputs.
4. Secure defaults such as encryption on.
5. No environment names or credentials inside.
6. A README and an `examples/` folder.
7. Semantic versioning: `v1.2.0`.

#### Layout

```text
modules/vpc/
  main.tf
  variables.tf
  outputs.tf
  README.md
  examples/
    complete/
```

#### Consuming it

```hcl
module "vpc" {
  source  = "app.terraform.io/myorg/vpc/aws"
  version = "1.4.0"
}
```

#### Breaking changes

Release a new major version with a migration note. Do not change v1 behaviour under people's feet.

#### Interview answer

"I keep modules small with a clear input and output contract, validation, secure defaults, examples, and documentation, and no environment names or credentials inside. They live in a private registry or Git with semantic versions, and each environment pins a version. Breaking changes get a major version and a migration guide. A platform team owns the standards, but other teams contribute through pull requests instead of copying the module."

### 5. Design a module for a multi-tier app *(asked in interview round)*

#### Structure

```text
modules/
  network/    VPC, public/private/db subnets, routes, NAT, internet gateway
  compute/    autoscaling group or cluster for the app tier
  data/       database with multi-AZ, cache, subnet groups
  security/   security groups and IAM
environments/
  prod/       main.tf (calls the modules), backend.tf, prod.tfvars
```

#### Key points to mention

1. **Remote state:** encrypted, versioned, locked, one state per environment.
2. **Layered state:** network, application, and data separately, so a mistake has a smaller blast radius.
3. **Wiring:** module outputs inside a root config, or `terraform_remote_state` between layers.
4. **Inputs and outputs:** CIDRs, instance sizes, and counts as inputs; VPC ID, subnet IDs, and endpoints as outputs.
5. **Tiers:** load balancer in the public tier, application in private subnets, database with no public route.
6. **Security groups reference each other**, not raw CIDR ranges.
7. Pin versions, tag everything, and run security scans in CI.

#### Example wiring

```hcl
module "network" {
  source = "../../modules/network"
  cidr   = var.vpc_cidr
}

module "data" {
  source     = "../../modules/data"
  subnet_ids = module.network.db_subnet_ids
}

module "compute" {
  source        = "../../modules/compute"
  subnet_ids    = module.network.private_subnet_ids
  db_endpoint   = module.data.endpoint
}
```

### 6. How do you test a module before releasing it?

#### Checklist for the module repo

```text
modules/vpc/
  main.tf
  variables.tf
  outputs.tf
  README.md
  examples/
    complete/      # a working example anyone can run
  tests/
    vpc.tftest.hcl
```

#### CI for the module

```bash
terraform fmt -check -recursive
terraform validate
tflint --recursive
checkov -d .
terraform test
terraform-docs markdown . > README.md
```

#### Release

Tag it with a semantic version:

```bash
git tag v1.4.0
git push origin v1.4.0
```

Consumers pin it:

```hcl
module "vpc" {
  source  = "git::https://github.com/myorg/tf-modules.git//vpc?ref=v1.4.0"
}
```

#### Interview answer

"Each module has a README, a working example, and tests. CI runs fmt, validate, tflint, a security scan, and `terraform test` or Terratest against the example, then generates the docs. Releases are tagged with semantic versions and consumers pin a version, so a change to the module cannot break every team at once. A breaking change means a new major version with a migration note."

### 7. Structuring a large Terraform project *(asked in interview round)*

#### Layout

```text
modules/
  network/
  compute/
  database/
environments/
  dev/     main.tf  backend.tf  dev.tfvars
  staging/ main.tf  backend.tf  staging.tfvars
  prod/    main.tf  backend.tf  prod.tfvars
```

#### Rules

1. Modules hold the logic. Root configs stay thin and just call modules.
2. Version the modules and pin the version in each environment.
3. Separate state per environment, and per layer when the project is big.
4. Layer the state: network, platform, data, application. Smaller blast radius.
5. Pin provider versions and commit the lock file.
6. Run `fmt`, `validate`, `tflint`, and a security scan in CI.

#### Workspaces or folders?

Workspaces are fine for short-lived or nearly identical copies. For long-lived dev, staging, and production, separate folders are clearer, because the credentials, backend, and approvals are visible.

### 8. How do you design Terraform for a big company with many teams? *(scenario)*

#### Structure

```text
Private module registry   -> versioned, reviewed modules
Platform team             -> owns modules and standards
Application teams         -> own their root configs, pin module versions
```

#### State boundaries

Split by network, shared platform, data, and applications, and by environment. Each has its own state and its own approvers.

#### Workflow

Pull request → plan posted as a comment → review → approval → apply. Atlantis or Spacelift can do this automatically.

#### Interview answer

"A platform team owns a private registry of versioned modules and the standards. Application teams own small root configurations that pin a module version and have their own state, credentials, and approvers. State is split by network, platform, data, and application. Every change goes through a pull request where the plan is posted for review, and a tool like Atlantis or Spacelift runs it consistently."

### 9. How do you scale Terraform for a large team? *(scenario)*

#### What matters most

1. Small state files, so teams do not block each other.
2. Versioned modules, so standards are shared.
3. Pull-request workflow with plan on every change.
4. One apply job per state.
5. Separate credentials and approvals per environment.
6. Clear ownership: who owns which stack.

#### Interview answer

"Scaling is mostly about boundaries. Keep small state files per component and environment, so teams do not queue behind one lock. Use versioned shared modules so standards stay consistent, a pull-request workflow where the plan is reviewed, and one apply job per state. Each environment has its own credentials and approvers, and every stack has a named owner."

### 10. How do you handle dependencies between separate stacks?

#### Option 1: remote state (simple, but couples the stacks)

```hcl
data "terraform_remote_state" "network" {
  backend = "s3"

  config = {
    bucket = "my-tf-state"
    key    = "network/terraform.tfstate"
    region = "us-east-1"
  }
}

resource "aws_instance" "app" {
  subnet_id = data.terraform_remote_state.network.outputs.private_subnet_ids[0]
}
```

#### Option 2: pass values in as variables (looser)

```hcl
variable "vpc_id" {
  type = string
}
```

The pipeline supplies the value. The application stack does not need read access to the network state.

#### Option 3: look it up by tag

```hcl
data "aws_vpc" "main" {
  tags = {
    Name = "prod-vpc"
  }
}
```

#### Option 4: Terragrunt

```hcl
dependency "vpc" {
  config_path = "../vpc"
}

inputs = {
  vpc_id     = dependency.vpc.outputs.vpc_id
  subnet_ids = dependency.vpc.outputs.private_subnets
}
```

#### Pipeline order

```text
network -> data -> application -> monitoring
```

#### Keep outputs stable

Once another stack depends on an output, treat it like a public interface. Do not rename or remove it without a version bump and a migration note.

#### Interview answer

"I connect stacks through a small number of stable outputs. The simplest way is a `terraform_remote_state` data source, but that gives the application stack read access to the network state. I often prefer passing values in as variables from the pipeline instead, or looking resources up by tag. Terragrunt can wire dependencies automatically. The main rule is to treat those outputs as a public interface and deploy the stacks in a defined order."
### 11. Passing dependencies between modules via outputs

Enterprise Terraform projects split infrastructure into modules (network, AKS, Key Vault, SQL, storage). Those modules usually depend on each other - AKS needs the subnet ID from the network module, for example. The pattern is to expose what a downstream module needs as an **output**, and pass it in as an **input variable** to the module that needs it, rather than hardcoding values or duplicating resource lookups.

```hcl
# modules/network/outputs.tf
output "subnet_id" {
  value = azurerm_subnet.aks.id
}
```

```hcl
# envs/prod/main.tf
module "network" {
  source = "../../modules/network"
  # ...
}

module "aks" {
  source    = "../../modules/aks"
  subnet_id = module.network.subnet_id
}
```

This keeps modules independently reusable - the AKS module doesn't need to know *how* the subnet was created, only that it receives a valid subnet ID - and it makes the dependency graph explicit in code rather than implicit through naming conventions or manual lookups.

#### Short interview answer

Each module exposes what other modules need through `outputs.tf`, and the consuming module takes it as an input variable - `subnet_id = module.network.subnet_id`, for example. That keeps modules loosely coupled and reusable, and makes cross-module dependencies explicit in code instead of relying on naming conventions or manual data lookups.
