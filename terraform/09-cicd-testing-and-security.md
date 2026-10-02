# Terraform: CI/CD, Testing, Security and Governance

> Running Terraform in pipelines and GitOps, testing code and modules, secrets management, least-privilege IAM, policy as code, and Terraform Enterprise.

## Key Concepts

### Terraform with GitHub Actions on Azure

```yaml
name: terraform

on:
  pull_request:
  push:
    branches: [main]

permissions:
  id-token: write
  contents: read

jobs:
  terraform:
    runs-on: ubuntu-latest
    environment: production

    steps:
      - uses: actions/checkout@v4

      - uses: azure/login@v2
        with:
          client-id: ${{ secrets.AZURE_CLIENT_ID }}
          tenant-id: ${{ secrets.AZURE_TENANT_ID }}
          subscription-id: ${{ secrets.AZURE_SUBSCRIPTION_ID }}

      - uses: hashicorp/setup-terraform@v3

      - run: terraform init
      - run: terraform validate
      - run: terraform plan -out=tfplan

      - if: github.ref == 'refs/heads/main'
        run: terraform apply tfplan
```

#### Points

- `id-token: write` enables OIDC, so no client secret is stored.
- State lives in an Azure Storage account, which locks with blob leases.
- The `environment` setting gives the approval gate.

### Terraform + Jenkins

```
Developer
  |
  v
Git
  |
  v
Jenkins
  |
  v
terraform fmt
  |
  v
terraform init
  |
  v
terraform validate
  |
  v
terraform plan
  |
  v
Approval
  |
  v
terraform apply
  |
  v
Azure
```

The Jenkins agent needs Terraform CLI, Azure CLI (where required), and Git installed.

```groovy
pipeline {
    agent any

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Terraform Init') {
            steps {
                sh 'terraform init'
            }
        }

        stage('Validate') {
            steps {
                sh 'terraform fmt -check'
                sh 'terraform validate'
            }
        }

        stage('Plan') {
            steps {
                sh 'terraform plan -out=tfplan'
            }
        }

        stage('Approval') {
            steps {
                input message: 'Approve Terraform Apply?'
            }
        }

        stage('Apply') {
            steps {
                sh 'terraform apply -auto-approve tfplan'
            }
        }
    }
}
```

Note that `plan` writes to a saved plan file (`tfplan`) and `apply` applies that exact saved plan - this guarantees what gets approved is exactly what gets applied, with no drift between the two steps. Azure authentication should be handled securely using Jenkins credentials or a suitable federated/workload identity approach, not long-lived secrets pasted into the pipeline.

### Terraform + Azure DevOps

```
Azure Repos
  |
  v
Azure Pipeline
  |
  v
Terraform
  |
  v
Azure
```

```yaml
trigger:
- main

pool:
  vmImage: ubuntu-latest

steps:

- task: TerraformInstaller@1
  inputs:
    terraformVersion: 'latest'

- script: |
    terraform init
  displayName: Terraform Init

- script: |
    terraform fmt -check
    terraform validate
  displayName: Terraform Validate

- script: |
    terraform plan -out=tfplan
  displayName: Terraform Plan

- script: |
    terraform apply -auto-approve tfplan
  displayName: Terraform Apply
```

`TerraformInstaller@1` installs the Terraform CLI onto the pipeline agent - this is the Azure DevOps-specific piece compared to the Jenkins version above.

**Production recommendation:** separate the plan and apply into distinct stages and gate `apply` behind an approval/environment gate, rather than running both in the same script block as shown above.

**Azure authentication:** use an Azure Resource Manager Service Connection, preferably backed by a secure/federated identity rather than a long-lived client secret.

```
Azure DevOps
  |
  v
Service Connection
  |
  v
Azure authentication
  |
  v
Terraform
  |
  v
Azure resources
```

### Terraform + GitHub Actions

Workflow file: `.github/workflows/terraform.yml`

```yaml
name: Terraform

on:
  pull_request:
  push:
    branches:
      - main

jobs:
  terraform:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Terraform
        uses: hashicorp/setup-terraform@v3

      - name: Terraform Init
        run: terraform init

      - name: Terraform Format
        run: terraform fmt -check

      - name: Terraform Validate
        run: terraform validate

      - name: Terraform Plan
        run: terraform plan -out=tfplan

      - name: Terraform Apply
        if: github.ref == 'refs/heads/main'
        run: terraform apply -auto-approve tfplan
```

Note the `if: github.ref == 'refs/heads/main'` guard on the apply step - a PR triggers `init`/`validate`/`plan` (so reviewers see the plan output) but only a push to `main` actually applies.

For Azure authentication, prefer **GitHub OIDC / federated credentials** with Azure rather than storing a long-lived client secret as a GitHub secret:

```
GitHub Actions
  |
  v
OIDC token
  |
  v
Azure Entra ID
  |
  v
Federated identity
  |
  v
Azure
```

The workflow requests a short-lived OIDC token from GitHub, Entra ID validates it against a configured federated credential, and Azure grants access without any long-lived secret ever being stored in GitHub.

### Comparing Terraform in Jenkins, Azure DevOps, and GitHub Actions

| | Jenkins | Azure DevOps | GitHub Actions |
| --- | --- | --- | --- |
| Terraform CLI | Installed on the agent manually | `TerraformInstaller@1` task | `hashicorp/setup-terraform` action |
| Trigger | Webhook / SCM polling | Repository trigger | Push / PR |
| Azure auth | Credentials or OIDC | Service Connection | OIDC (federated credentials) |
| State storage | Azure Storage (`azurerm` backend) | Azure Storage (`azurerm` backend) | Azure Storage (`azurerm` backend) |
| Approval | `input` step in the Jenkinsfile | Environment approvals | Environments / required reviewers |
| Pipeline file | `Jenkinsfile` | `azure-pipelines.yml` | `.github/workflows/*.yml` |

The state backend is the same everywhere (Azure Storage) regardless of which CI/CD tool drives the pipeline - the differences are all in how each tool triggers, authenticates, and gates the apply step.

### Testing Terraform code

| Check | Command | Catches |
|---|---|---|
| Format | `terraform fmt -check` | Style |
| Syntax | `terraform validate` | Bad references, missing arguments |
| Lint | `tflint` | Bad instance types, unused variables |
| Security | `tfsec .` / `checkov -d .` | Public buckets, missing encryption |
| Drift | `terraform plan -detailed-exitcode` | Manual changes |
| Unit test | `terraform test` / Terratest | Module actually works |
| Policy | OPA / Conftest / Sentinel | Company rules |

#### Native test example

```hcl
# tests/vpc.tftest.hcl
run "vpc_cidr_is_correct" {
  command = plan

  assert {
    condition     = aws_vpc.main.cidr_block == "10.0.0.0/16"
    error_message = "Wrong CIDR"
  }
}
```

### Secrets management

#### Rules

1. Never hardcode a secret in `.tf` or in a `.tfvars` file that is committed.
2. Read secrets from Vault, Key Vault, or Secrets Manager at run time.
3. Mark variables and outputs `sensitive`.
4. Encrypt state and restrict read access.
5. Rotate secrets regularly.
6. Best of all: let the application read the secret at runtime with a managed identity, so Terraform never touches it.

#### Example

```hcl
data "azurerm_key_vault_secret" "db" {
  name         = "db-password"
  key_vault_id = var.key_vault_id
}
```

#### Remember

`sensitive = true` hides the value in CLI output only. The value can still be in state.

### Terraform Enterprise in simple words

#### The idea

- **Terraform CLI (open source)** — you run Terraform on your own machine. The state file sits with you, and nobody else knows what you did.
- **Terraform Enterprise** — the company runs Terraform centrally, with shared state, rules, approvals, and a record of who changed what.

Think of it as personal notes versus a shared company drive.

#### Problems it solves

| Without it | With Terraform Enterprise |
|---|---|
| Everyone has their own state file | One central state |
| Anyone can destroy something | Role-based access control |
| No record of who changed what | Audit logs |
| Someone applies from a laptop | Runs happen on secure workers |
| No guardrails | Sentinel policies block bad plans |

#### How a run works

1. A developer pushes Terraform code to Git.
2. Terraform Enterprise sees the change and starts a run.
3. It runs `terraform plan` on a worker.
4. A reviewer approves.
5. It runs `terraform apply` on the worker.
6. The new state version is stored centrally.

#### Main features

| Feature | Meaning |
|---|---|
| Workspaces | Separate state and variables per environment |
| Remote state | State stored centrally, with version history |
| VCS integration | A Git push starts a run |
| Sentinel | Policy rules, for example "only allow the West Europe region" |
| RBAC | Who can view, plan, or apply |
| Private module registry | Share company modules internally |
| Audit logs | Who did what and when |

#### One-line definition

"Terraform Enterprise is HashiCorp's self-hosted platform for running Terraform centrally, with remote runs, managed state, access control, policy enforcement, and audit logs."

## Interview Questions

### 1. How did you set up Terraform in CI/CD?

#### On a pull request

```yaml
- terraform fmt -check
- terraform init
- terraform validate
- tfsec .        # or checkov
- terraform plan -out=tfplan
```

The plan summary is posted as a PR comment. The full plan file is kept as a protected artifact, because plans can show sensitive values.

#### After merge

1. A protected job picks up the same commit.
2. It gets the state lock.
3. It waits for approval on production.
4. It runs `terraform apply tfplan`.
5. It runs a smoke check afterwards.

#### Rules

- Only the deployment job can apply.
- Only one deployment at a time per state.
- Credentials come from OIDC / workload identity, not stored secrets.

#### Interview answer

"On a pull request the pipeline runs fmt, init, validate, a security scan, and a plan with read-only credentials, and posts the plan summary for review. After merge, a protected stage applies the reviewed plan for that same commit, with production approval and only one job per state. Credentials come from workload identity, and after apply I run a smoke test."

### 2. How do you run Terraform safely in a pipeline?

#### Safety list

| Area | What I do |
|---|---|
| Versions | Pin Terraform, providers, and modules; commit the lock file |
| State | Remote, encrypted, versioned, locked, separate per environment |
| Credentials | Short-lived OIDC credentials, least privilege |
| Review | Plan on PR, approval before production apply |
| Concurrency | One apply per state |
| Failure | Stop the pipeline. Do not auto-retry, do not auto-destroy |
| After apply | Smoke test the application, not just the resource |

#### Interview answer

"I pin versions, use locked remote state per environment, and get short-lived credentials from workload identity. PRs run plan and policy checks; production applies the reviewed plan after approval, one job at a time. If an apply fails halfway, the pipeline stops and an engineer compares state with the real resources instead of blindly retrying or destroying."

### 3. How do you build a CI/CD pipeline for Terraform? *(scenario)*

#### Stages

```text
1. Checkout
2. fmt + validate
3. Security scan (tfsec / Checkov)
4. terraform plan -out=tfplan   (read-only credentials)
5. Post plan to the pull request
6. Manual approval           <- production only
7. terraform apply tfplan
8. Smoke test
```

#### GitHub Actions example

```yaml
jobs:
  plan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: hashicorp/setup-terraform@v3
      - run: terraform init
      - run: terraform validate
      - run: terraform plan -out=tfplan

  apply:
    needs: plan
    environment: production   # requires approval
    steps:
      - run: terraform apply tfplan
```

#### Interview answer

"The pull request stage runs fmt, validate, a security scan, and a plan with read-only credentials, and posts the plan for review. After merge, a protected environment requires approval and applies that same reviewed plan, followed by a smoke test. Credentials come from OIDC, state is locked, and only one apply runs per state."

### 4. How do you make sure changes are peer reviewed? *(scenario)*

#### Pipeline on a pull request

```bash
terraform fmt -check
terraform init
terraform validate
tfsec .
terraform plan -out=tfplan
```

Post the plan summary as a PR comment.

#### Repository rules

- Branch protection on `main`
- At least one approval
- Code owners for modules and production folders
- No direct pushes

#### Apply rules

Only the protected job applies, using the same commit and the reviewed plan, after approval.

#### Interview answer

"Every change goes through a pull request that runs fmt, validate, security scans, and a plan, and the plan summary is posted as a comment so reviewers can see creates, updates, and destroys. Branch protection requires an approval, and code owners review modules and production folders. Apply only happens from the protected job on that same commit after approval."

### 5. How do you automate plan reviews? *(scenario)*

#### In the pipeline

```bash
terraform plan -out=tfplan -no-color
terraform show -no-color tfplan > plan.txt
```

Post `plan.txt` as a pull request comment.

#### Add automatic checks on the plan

```bash
terraform show -json tfplan > plan.json
conftest test plan.json                       # policy
terraform show -json tfplan | jq '.resource_changes[] | select(.change.actions[] == "delete") | .address'
```

The second command lists everything that would be deleted, which is the part reviewers miss.

#### Tools

Atlantis and Spacelift post plans and handle apply approval automatically.

#### Interview answer

"The pipeline saves the plan and posts a readable summary as a pull request comment, and it also converts the plan to JSON so policy checks can run automatically and any deletes are listed clearly. Reviewers usually miss deletes in a long plan, so highlighting them is the most useful automation. Atlantis or Spacelift give this workflow out of the box."

### 6. Testing before production *(asked in interview round)*

| Stage | What runs |
|---|---|
| Static | `terraform fmt -check`, `terraform validate`, `tflint` |
| Security | `tfsec`, `checkov`, or Trivy |
| Plan review | Plan on every pull request, reviewed by a person |
| Policy | OPA or Sentinel rules, for example no public storage |
| Tests | `terraform test` or Terratest against a sandbox |
| Promotion | Apply in dev, then staging, then production with approval |

### 7. How do you test Terraform code?

#### Layers of testing

| Layer | Tool | What it catches |
|---|---|---|
| Format | `terraform fmt -check` | Style |
| Syntax | `terraform validate` | Bad references, missing arguments |
| Lint | `tflint` | Wrong instance types, unused variables |
| Security | `tfsec`, `checkov` | Public buckets, missing encryption |
| Plan review | `terraform plan` | Unexpected destroys |
| Unit test | `terraform test` or Terratest | Module actually works |
| Policy | OPA, Sentinel | Company rules |

#### Native test example (Terraform 1.6+)

```hcl
# tests/vpc.tftest.hcl
run "creates_vpc" {
  command = plan

  variables {
    cidr = "10.0.0.0/16"
  }

  assert {
    condition     = aws_vpc.main.cidr_block == "10.0.0.0/16"
    error_message = "VPC CIDR is wrong"
  }
}
```

#### Terratest example

```go
func TestVpc(t *testing.T) {
  opts := &terraform.Options{TerraformDir: "../examples/vpc"}
  defer terraform.Destroy(t, opts)
  terraform.InitAndApply(t, opts)

  vpcID := terraform.Output(t, opts, "vpc_id")
  assert.NotEmpty(t, vpcID)
}
```

#### Interview answer

"I test in layers: `fmt` and `validate` for basics, `tflint` for lint, `tfsec` or `checkov` for security, and a reviewed plan on every pull request. For modules I use the native `terraform test` framework or Terratest to deploy into a sandbox, assert the outputs, and destroy. Policy checks with OPA or Sentinel run before apply, and the pipeline blocks a merge if any layer fails."

### 8. How do you test Terraform before deploying? *(scenario)*

#### Order of checks

```bash
terraform fmt -check      # style
terraform validate        # syntax and references
tflint                    # lint rules
tfsec .                   # security
terraform plan -out=tfplan
terraform test            # module tests
```

Then deploy to dev, verify, and promote the same code to test and production.

#### Interview answer

"I run fmt and validate for the basics, tflint for lint, tfsec or Checkov for security, and a reviewed plan on every pull request. Modules also have `terraform test` or Terratest cases that build a real example in a sandbox and destroy it. Then the change is proven in dev before the same code is promoted upward."

### 9. What is TFLint, and how do you use it in CI/CD?

#### 16.1 What is TFLint?

TFLint is a static analysis and linting tool for Terraform. It analyzes Terraform code before deployment and identifies issues such as configuration mistakes, best practice violations, deprecated syntax, and cloud provider-specific problems.

It helps catch errors early, before you run `terraform apply`.

#### 16.2 Why do we use TFLint?

Terraform itself checks syntax with:

```bash
terraform validate
```

But `terraform validate` does not detect many best practice issues.

TFLint provides additional checks, such as:

- Unused variables
- Unused data sources
- Invalid instance types (AWS) or SKUs (Azure)
- Deprecated arguments
- Naming convention issues
- Missing required tags (with custom rules)

#### 16.3 Example

Suppose you write:

```hcl
resource "azurerm_linux_virtual_machine" "vm" {
  size = "Standard_XYZ"
}
```

`terraform validate` may pass because the syntax is correct.

When you run:

```bash
tflint
```

TFLint can detect that `Standard_XYZ` is not a valid Azure VM size (with the Azure plugin enabled).

#### 16.4 Installation

```bash
brew install tflint      # macOS
```

or

```bash
choco install tflint     # Windows
```

#### 16.5 Common commands

Initialize plugins:

```bash
tflint --init
```

Run lint checks:

```bash
tflint
```

Lint a specific directory:

```bash
tflint ./terraform
```

#### 16.6 CI/CD pipeline integration

A typical pipeline includes:

```
Git Push
    |
    v
terraform fmt -check
    |
terraform validate
    |
tflint
    |
terraform plan
    |
Approval
    |
terraform apply
```

If TFLint finds issues, the pipeline fails, preventing low-quality Terraform code from being deployed.

#### 16.7 terraform validate vs TFLint

| Feature | terraform validate | TFLint |
|---|---|---|
| Syntax validation | Yes | No |
| Checks resource configuration | Basic | Advanced |
| Finds best practice issues | No | Yes |
| Provider-specific validation | Limited | Yes |
| CI/CD integration | Yes | Yes |

#### 16.8 Interview answer (30 seconds)

> "TFLint is a linting tool for Terraform that performs static analysis on Terraform code. While `terraform validate` checks syntax and configuration validity, TFLint goes further by identifying best practice violations, deprecated arguments, unused variables, and provider-specific configuration issues. We typically run TFLint in our CI/CD pipeline before `terraform plan` so that configuration problems are caught early and only high-quality Infrastructure as Code is deployed."

### 10. What are tfsec, Checkov and Trivy, and how do they compare?

These are all Infrastructure as Code (IaC) security scanning tools, but they have different purposes.

#### 17.1 tfsec

tfsec scans Terraform code for security misconfigurations before deployment. It checks whether your infrastructure follows security best practices.

**Examples of issues it detects**

- Storage Account allows public access.
- Security Group exposes SSH (port 22) to the internet.
- Azure Key Vault has public network access enabled.
- Encryption is not enabled.
- Logging is disabled.

Run:

```bash
tfsec .
```

#### 17.2 Checkov

Checkov is a policy-as-code security scanner developed by Bridgecrew (Palo Alto Networks). It scans multiple Infrastructure as Code frameworks, not just Terraform.

It supports:

- Terraform
- Kubernetes YAML
- Helm Charts
- CloudFormation
- ARM Templates
- Bicep
- Dockerfiles

**Example**

Suppose your AKS cluster doesn't have RBAC enabled or your Storage Account allows public access.

Running:

```bash
checkov -d .
```

reports these security issues before deployment.

**Why use it?**

- Broader support than tfsec.
- Large library of built-in security policies.
- Can enforce compliance standards like CIS benchmarks.

#### 17.3 Trivy

Trivy is a vulnerability scanner developed by Aqua Security.

Unlike tfsec and Checkov, Trivy focuses on container images, filesystems, Kubernetes clusters, and also supports IaC scanning.

It checks:

- Docker images for known CVEs.
- Kubernetes manifests.
- Terraform files.
- Secrets accidentally committed to code.
- Open-source dependencies.

**Example**

Scan a Docker image:

```bash
trivy image myacr.azurecr.io/orders-api:v1
```

It reports vulnerabilities such as Critical, High, Medium and Low. This helps prevent deploying vulnerable images.

#### 17.4 Comparison

| Tool | Primary Purpose | Supports |
|---|---|---|
| tfsec | Terraform security scanning | Terraform |
| Checkov | Multi-IaC security and compliance | Terraform, Kubernetes, Helm, CloudFormation, ARM, Bicep, Dockerfile |
| Trivy | Vulnerability scanning | Container images, filesystems, Kubernetes clusters, IaC, secrets, dependencies |

#### 17.5 Interview answer

> "tfsec and Checkov are Infrastructure as Code security scanners that check Terraform code for misconfigurations before deployment, such as public storage accounts or open security groups. Checkov supports more frameworks than tfsec, including Kubernetes, Helm and Dockerfiles, and can enforce compliance standards like CIS. Trivy is different - it is mainly a vulnerability scanner for container images, and it also scans filesystems, Kubernetes clusters, IaC files and committed secrets. In a pipeline, I run tfsec or Checkov on the Terraform code and Trivy on the built Docker image before pushing it to ACR."

### 11. How do you manage secrets in Terraform?

#### Rules

1. Never hardcode a secret in `.tf` files or in a plain `.tfvars` file in Git.
2. Read secrets from a secret store at runtime.
3. Mark variables and outputs as `sensitive`.
4. Protect the backend, because values can land in state.

#### Example: read from Azure Key Vault

```hcl
data "azurerm_key_vault_secret" "db_password" {
  name         = "db-password"
  key_vault_id = var.key_vault_id
}

resource "azurerm_mssql_server" "db" {
  name                         = "app-sql"
  administrator_login          = "sqladmin"
  administrator_login_password = data.azurerm_key_vault_secret.db_password.value
}
```

#### Example: mark a variable sensitive

```hcl
variable "db_password" {
  type      = string
  sensitive = true
}
```

#### Important point

`sensitive = true` only hides the value in CLI output. It does not encrypt state.

#### Interview answer

"I keep secrets out of Git. The pipeline logs in with a short-lived identity and reads secrets from Key Vault, Vault, or Secrets Manager. I mark variables and outputs as sensitive, but I explain that this only hides them in output, not in state, so the backend must be encrypted with restricted access. Where possible, the application reads the secret at runtime instead of Terraform passing it."

### 12. Terraform Hardcoded Credentials

#### The code

```hcl
provider "azurerm" {
  features {}

  client_id       = "12345678"
  client_secret   = "super-secret-password"
  subscription_id = "abcdef"
  tenant_id       = "xyz"
}
```

#### What is wrong

Hardcoding a service principal's `client_id`/`client_secret` directly in `.tf` files means the credentials end up in source control (and in Terraform state, which is even more sensitive). Anyone with repo access — or access to old commits — has standing production credentials.

#### How to authenticate securely instead

**Option A — Environment variables (simplest, works locally and in CI):**

```hcl
provider "azurerm" {
  features {}
}
```

```bash
export ARM_CLIENT_ID="..."
export ARM_CLIENT_SECRET="..."
export ARM_SUBSCRIPTION_ID="..."
export ARM_TENANT_ID="..."
```

In Azure DevOps, these are supplied via a **Service Connection** (Azure Resource Manager), and the pipeline uses `AzureCLI@2` or the Terraform task, which injects credentials automatically without ever exposing them in the YAML.

**Option B — Workload Identity Federation / OIDC (preferred, no stored secret at all):**
Azure DevOps issues a short-lived OIDC token that Azure trusts via a federated credential, so there is no long-lived client secret to leak or rotate.

**Option C — Managed Identity** if running from an Azure agent (e.g., a self-hosted agent VM with a system-assigned identity).

#### Short interview answer

"Hardcoded client secrets in Terraform files are a serious risk since they land in source control and in state. I'd remove them from the provider block entirely and authenticate through an Azure DevOps service connection using Workload Identity Federation (OIDC) where possible, or environment variables (`ARM_*`) backed by a Key Vault–stored secret otherwise — never committed to the repo."

### 13. How do you keep secrets out of state?

#### What I do

1. No secrets in Git or plain `.tfvars`.
2. Pipeline logs in with workload identity, no stored keys.
3. Secrets come from Vault, Key Vault, or Secrets Manager.
4. Mark variables and outputs `sensitive`.
5. Where possible, Terraform creates the empty secret container and another process fills the value.
6. Encrypt the backend and restrict read access.

#### Example: create the secret container, not the value

```hcl
resource "azurerm_key_vault_secret" "db" {
  name         = "db-password"
  value        = var.db_password   # supplied by pipeline, never committed
  key_vault_id = var.key_vault_id
}
```

Better still, the application reads the secret at runtime using its managed identity, so Terraform never touches the value.

#### Interview answer

"Secrets never go into Git or plain tfvars. The pipeline authenticates with workload identity and pulls values from a secret manager. I mark variables and outputs sensitive, but I explain that this only hides output, so the backend must be encrypted with restricted read access. Where possible Terraform creates the secret container and grants access, while the application reads the actual value at runtime."

### 14. How do you use a secret manager with Terraform?

#### Vault example

```hcl
data "vault_generic_secret" "db" {
  path = "secret/database/app"
}

resource "aws_db_instance" "app" {
  identifier = "app-db"
  username   = data.vault_generic_secret.db.data["username"]
  password   = data.vault_generic_secret.db.data["password"]
}
```

#### AWS Secrets Manager example

```hcl
data "aws_secretsmanager_secret_version" "db" {
  secret_id = "prod/app/db"
}

locals {
  db = jsondecode(data.aws_secretsmanager_secret_version.db.secret_string)
}
```

#### Remember

Any value used in a resource can end up in state, so:

- Encrypt state
- Restrict read access
- Rotate secrets regularly
- Mark outputs `sensitive`

#### Interview answer

"I keep the secret in Vault, Key Vault, or Secrets Manager and read it with a data source at run time, so nothing is hardcoded. I mark outputs sensitive and encrypt the backend, because the value can still end up in state. For the most sensitive values I prefer that Terraform only grants access and the application reads the secret at runtime."

### 15. How do you encrypt secrets in the state file? *(scenario)*

#### What you can do

| Control | How |
|---|---|
| Encryption at rest | S3 SSE-KMS, Azure Storage encryption, GCS CMEK |
| Encryption in transit | TLS, which the backends use by default |
| Restrict access | IAM policy on the state bucket, read access is as sensitive as write |
| Versioning | Bucket versioning or soft delete |
| Keep values out | Let the app read secrets at runtime instead of Terraform passing them |

#### Example

```hcl
terraform {
  backend "s3" {
    bucket     = "my-tf-state"
    key        = "prod/terraform.tfstate"
    region     = "us-east-1"
    encrypt    = true
    kms_key_id = "arn:aws:kms:us-east-1:111122223333:key/abcd-1234"
  }
}
```

#### Important point

Terraform does not encrypt individual values inside state. The whole file is protected by the backend.

#### Interview answer

"Terraform does not encrypt single values inside state, so I protect the whole file: an encrypted bucket with a customer-managed key, TLS in transit, versioning, and tight IAM so read access is as restricted as write. The better fix is to avoid putting secrets in state at all, by letting the application read them at runtime through managed identity."

### 16. Encrypting secrets in Terraform state

- Store production state **remotely** (e.g. Azure Storage), never locally.
- Use **encryption at rest** on the state storage.
- Restrict access with **RBAC**, and **private endpoints/firewalls** so the storage account isn't reachable from the open internet.
- Enable **versioning** on the state storage, so a bad or corrupted state write can be recovered.
- Optionally use **customer-managed keys** through Azure Key Vault for an extra layer of control over the encryption key itself.
- **Do not hardcode secrets** in Terraform configuration - retrieve them from Azure Key Vault instead.
- **Mark sensitive variables** so their values are hidden in CLI output:

```hcl
variable "db_password" {
  type      = string
  sensitive = true
}
```

**The trap:** `sensitive = true` only hides the value from CLI/plan *output*. It does **not** encrypt the value inside the state file itself - the plaintext value still ends up in `terraform.tfstate` (or the remote state file) whenever that resource's attributes are recorded. State-file protection has to come from encrypting and restricting access to the state storage itself, not from the `sensitive` flag.

#### Short interview answer

I keep production state remote with encryption at rest, RBAC, and private network access, and I enable versioning so a bad state write is recoverable. Secrets themselves come from Azure Key Vault rather than being hardcoded, and I mark sensitive variables - but I'm careful to explain that `sensitive = true` only hides the value in CLI output; it does not encrypt it inside the state file, so protecting the state storage itself is what actually matters.

### 17. How do you secure a Terraform pipeline? *(scenario)*

#### Controls

| Area | Control |
|---|---|
| Credentials | OIDC / workload identity, no stored keys |
| Permissions | Least privilege, separate identity per environment |
| Code | Branch protection, code owners, pinned actions |
| Scanning | tfsec, Checkov, secret scanning |
| Policy | Sentinel or OPA on the plan |
| Apply | Protected environment, approval, one job per state |
| Logs | Keep them, but redact secrets |

#### Interview answer

"The pipeline uses short-lived credentials from workload identity instead of stored keys, with a separate least-privilege identity per environment. Code is protected with branch rules and code owners, and the actions and provider versions are pinned. Every run does security and policy scanning, and apply only happens in a protected environment after approval. Logs are kept for audit but sensitive output is redacted."

### 18. How do you secure Terraform code in GitHub? *(scenario)*

#### Repository settings

1. Branch protection on `main`, no direct pushes
2. Required reviews and code owners
3. Required status checks: fmt, validate, tfsec, plan
4. Secret scanning and push protection turned on

#### Workflow settings

```yaml
permissions:
  id-token: write   # OIDC
  contents: read
```

- Use OIDC, not long-lived keys in secrets
- Pin actions to a version or commit SHA
- Use environments with required reviewers for production

#### If a secret is committed

Rotate it immediately. Removing it from history is not enough, it has already been exposed.

#### Interview answer

"Branch protection with required reviews and status checks, code owners on modules and production folders, and secret scanning with push protection. The workflow uses OIDC instead of stored keys, pins actions, and applies only through a protected environment with required reviewers. If a secret ever gets committed, I rotate it immediately, because cleaning the history does not make it un-leaked."

### 19. How do you keep shared modules secure? *(scenario)*

#### Controls

1. Modules live in a private registry or a protected repo.
2. Code owner review before release.
3. Security scanning in the module's own pipeline.
4. Secure defaults: encryption on, public access off.
5. Semantic versions, so a change cannot silently reach everyone.

#### Example of a secure default

```hcl
variable "public_access" {
  type    = bool
  default = false
}
```

Make the safe option the default, and make the unsafe option something you have to ask for.

#### Interview answer

"Modules live in a protected repo with code owner review and their own security scanning, and they are released with semantic versions so nothing reaches consumers silently. The important part is secure defaults: encryption on, public access off, so a team has to deliberately opt out of safety rather than remember to opt in."

### 20. How do you set up least privilege IAM in Terraform? *(scenario)*

#### Rules

1. No `Owner`, `Editor`, or `*` on production.
2. Use narrow predefined roles, or a custom role with only the needed permissions.
3. Grant at the smallest scope: one bucket, one resource group, not the whole subscription.
4. Use workload identity instead of static keys.

#### GCP example

```hcl
resource "google_storage_bucket_iam_member" "app_reader" {
  bucket = google_storage_bucket.data.name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_service_account.app.email}"
}
```

#### Azure example

```hcl
resource "azurerm_role_assignment" "app_reader" {
  scope                = azurerm_storage_account.data.id
  role_definition_name = "Storage Blob Data Reader"
  principal_id         = azurerm_user_assigned_identity.app.principal_id
}
```

#### Interview answer

"I grant a narrow role at the smallest possible scope, on the single bucket or resource group rather than the whole project or subscription, and I avoid primitive roles like Owner or Editor. Identities use workload identity or managed identity so there are no static keys to leak. When something is denied, I read the audit log to find the exact missing permission instead of widening the role to make it pass."

### 21. How do you manage GCP IAM or Azure RBAC in Terraform? *(scenario)*

#### Keep bindings in code, not in the console

**Azure**

```hcl
resource "azurerm_role_assignment" "app_kv" {
  scope                = azurerm_key_vault.app.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_user_assigned_identity.app.principal_id
}
```

**GCP**

```hcl
resource "google_project_iam_member" "app_logs" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.app.email}"
}
```

#### Careful with authoritative resources

`google_project_iam_policy` and `google_project_iam_binding` replace existing bindings and can lock people out. Prefer `_member`, which only adds one binding.

#### Interview answer

"I keep role assignments in Terraform so access is reviewed like any other change, granting narrow roles at the smallest scope. One thing I always mention is that in GCP the `_policy` and `_binding` resources are authoritative and can remove existing access, so I use `_member` unless I truly intend to own the whole policy."

### 22. How do you enforce tagging and encryption rules?

#### Enforce at more than one layer

| Layer | Tool |
|---|---|
| Code review | Pull requests and code owners |
| CI static scan | Checkov, tfsec, Terrascan |
| Plan-time policy | Sentinel or OPA / Conftest |
| Cloud-side policy | AWS SCP, Azure Policy, GCP Org Policy |

#### Simple OPA rule

```rego
package terraform

deny[msg] {
  r := input.resource.aws_instance[name]
  not r.tags.Owner
  msg := sprintf("Instance '%v' is missing the Owner tag", [name])
}
```

#### Policy levels

- **Advisory:** warn only.
- **Soft mandatory:** can be overridden with approval.
- **Hard mandatory:** always blocks.

Keep an exception process with an expiry date.

#### Interview answer

"I enforce rules in layers. CI runs Checkov or tfsec on the code, Sentinel or OPA checks the plan before apply, and cloud-native policies catch anything created outside Terraform. Rules cover required tags, encryption, allowed regions, and private networking. I classify rules as advisory, soft mandatory, or hard mandatory, keep a time-limited exception process, and test policies with both passing and failing examples."

### 23. How do you enforce policy as code? *(scenario)*

#### Two places

**Before apply — Terraform side**

- Checkov or tfsec on the code
- Sentinel or OPA / Conftest on the plan JSON

```bash
terraform show -json tfplan > plan.json
conftest test plan.json
```

**In the cluster — Kubernetes side**

- OPA Gatekeeper or Kyverno as admission controllers

#### Example rule

```rego
package terraform

deny[msg] {
  b := input.resource.aws_s3_bucket[name]
  b.acl == "public-read"
  msg := sprintf("Bucket '%v' must not be public", [name])
}
```

#### Interview answer

"For Terraform I scan the code with Checkov or tfsec and check the plan with Sentinel or OPA, and the pull request fails if a rule is broken. For Kubernetes I use Gatekeeper or Kyverno as admission controllers so anything applied directly to the cluster is also checked. I keep an exception process with an expiry date, otherwise people work around the gate."

### 24. Policy-as-code for Terraform and Kubernetes

**Terraform pipeline:**

```
terraform fmt
terraform validate
TFLint
tfsec / Checkov / Trivy
terraform plan
approval
terraform apply
```

Terraform-side policies can enforce things like: approved regions only, mandatory tags, encryption required, no public storage access, and restricted network rules - checked automatically before anything reaches `apply`.

**Kubernetes policy tools:**

- **OPA Gatekeeper**
- **Kyverno**
- **Azure Policy for AKS**

Kubernetes-side policies can enforce: non-root containers, only approved registries, required resource requests/limits, required labels, no privileged containers, and restricted `hostPath` volume use.

The two ecosystems are structurally similar - a policy engine evaluates a desired configuration (a Terraform plan, or a Kubernetes admission request) against rules and blocks anything that violates them, before the change ever takes effect.

#### Short interview answer

For Terraform, I run `tfsec`/`Checkov`/`Trivy` plus `TFLint` in the pipeline before `plan`, enforcing things like approved regions, mandatory tags, encryption, and no public storage exposure. For Kubernetes, I use an admission-control policy engine - OPA Gatekeeper, Kyverno, or Azure Policy for AKS - to enforce non-root containers, approved registries, required resource limits, and no privileged containers at the point resources are created, not after the fact.

### 25. How do you enforce rules like naming and tagging? *(scenario)*

#### Where the checks run

1. **Variable validation** — fails immediately with a clear message.

```hcl
variable "name" {
  type = string

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{2,20}$", var.name))
    error_message = "Name must be lowercase letters, numbers, and hyphens."
  }
}
```

2. **Default tags in the provider** — nobody can forget them.

```hcl
provider "aws" {
  default_tags {
    tags = {
      Environment = var.environment
      Owner       = var.owner
      ManagedBy   = "terraform"
    }
  }
}
```

3. **Policy check on the plan** — Sentinel, OPA, or Checkov.
4. **Cloud policy** — catches anything created outside Terraform.

#### Interview answer

"I start with variable validation and provider default tags, so the right thing happens by default and bad input fails early with a clear message. Then a policy check on the plan with OPA or Sentinel enforces the rules in CI, and a cloud-native policy catches whatever is created outside Terraform. Layering them means one gap does not let everything through."

### 26. What is Terraform Enterprise?

#### Simple definition

Terraform Enterprise is HashiCorp's self-hosted version of Terraform Cloud. You run it inside your own network.

#### What it gives you

| Feature | Meaning |
|---|---|
| Remote runs | Plan and apply run on servers, not laptops |
| Remote state | State stored and versioned centrally |
| Workspaces | Separate state and variables per environment |
| VCS integration | A Git push starts a run |
| RBAC | Control who can plan and who can apply |
| Sentinel policies | Block runs that break the rules |
| Private module registry | Share company modules |
| Audit logs | Who changed what and when |

#### Interview answer

"Terraform Enterprise is HashiCorp's self-hosted platform for running Terraform centrally. It gives remote runs, managed state, workspaces, Git integration, role-based access, policy enforcement with Sentinel, a private module registry, and audit logs. Companies use it when they need those controls inside their own network. It does not replace good module design or cloud IAM."

### 27. Explain the Terraform Enterprise architecture.

#### Flow

```text
Git push or API call
        |
Terraform Enterprise application
  (workspaces, variables, policies, run queue)
        |
Worker (runs init, plan, apply)
        |
Cloud provider APIs
        |
State version + logs stored back
```

#### Components

- **Application layer:** UI and API, organizations, workspaces, permissions, run queue.
- **Workers:** run Terraform, need network access to module sources and cloud APIs.
- **Object storage:** state versions and run artifacts.
- **Database and cache:** application metadata.

#### Production needs

TLS, secret management, backups of state and metadata, monitoring, an upgrade plan, and tested disaster recovery.

#### Interview answer

"A Git webhook or API call reaches the Terraform Enterprise application, which manages workspaces, variables, policies, and the run queue. A worker then runs init, plan, and apply, talking to module sources and cloud APIs, and returns logs and a new state version stored in object storage. In production I also plan for TLS, secrets, backups, monitoring, upgrades, and disaster recovery, and I make sure the workers have the network access they need, not just the UI."
