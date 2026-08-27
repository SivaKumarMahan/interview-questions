# Terraform CI/CD Integrations

Wiring Terraform into Jenkins, Azure DevOps, and GitHub Actions specifically, plus the broader set of things Terraform is used for beyond just creating infrastructure the first time.

For Terraform state locking with an `azurerm` backend and the PR → plan → apply enterprise flow, see `devops-interview-mixed-topics.md` §15 and `kubernetes-scaling-and-terraform-fundamentals.md` §5 - that ground is already covered elsewhere and isn't repeated here.

## Contents

1. [Terraform uses beyond creating infrastructure](#1-terraform-uses-beyond-creating-infrastructure)
2. [Terraform + Jenkins](#2-terraform--jenkins)
3. [Terraform + Azure DevOps](#3-terraform--azure-devops)
4. [Terraform + GitHub Actions](#4-terraform--github-actions)
5. [Comparing the three](#5-comparing-the-three)

---

## 1. Terraform uses beyond creating infrastructure

Terraform is used for the broader lifecycle of resources, not just the initial `terraform apply`:

1. **Modify existing infrastructure** - change resource attributes and reconcile them via plan/apply.
2. **Manage infrastructure configuration** over time as requirements change.
3. **Detect configuration drift** with `terraform plan` - compares real infrastructure against the state file.
4. **Import existing manually created infrastructure** with `terraform import`, bringing resources that were created by hand under Terraform management.
5. **Lifecycle management** using resource-level meta-arguments:
   - `create_before_destroy` - creates the replacement resource before destroying the old one, avoiding downtime on replacement.
   - `prevent_destroy` - blocks `terraform destroy`/replacement of a resource entirely, as a safety rail for critical resources (e.g. a production database).
   - `ignore_changes` - tells Terraform to ignore drift on specific attributes (e.g. ones modified outside Terraform, like autoscaler-adjusted replica counts).
6. **Manage multiple environments** with reusable modules and variables (dev/staging/prod from the same module, different variable values).
7. **Create reusable Terraform modules** so common patterns aren't copy-pasted across projects.
8. **Automate infrastructure changes through CI/CD** rather than running `terraform apply` from a laptop.
9. **Manage non-infrastructure resources** - Terraform providers exist for Kubernetes objects, GitHub (repos, teams, branch protection), and Azure DevOps (projects, pipelines, permissions), so Terraform can manage more than just cloud infrastructure.
10. **Standardization and compliance** - enforcing consistent resource configuration (tags, naming, network rules) across an organization through shared modules and policy checks.
11. **Disaster recovery** - recreating infrastructure from code in a new region/subscription if the original is lost, since the desired state already exists as code.

Terraform is primarily Infrastructure as Code / resource lifecycle management. It is **not** a replacement for Ansible - Ansible is generally better for configuring software *inside* already-running servers (packages, config files, services), while Terraform is better at creating/managing the resources themselves.

---

## 2. Terraform + Jenkins

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

---

## 3. Terraform + Azure DevOps

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

---

## 4. Terraform + GitHub Actions

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

---

## 5. Comparing the three

| | Jenkins | Azure DevOps | GitHub Actions |
| --- | --- | --- | --- |
| Terraform CLI | Installed on the agent manually | `TerraformInstaller@1` task | `hashicorp/setup-terraform` action |
| Trigger | Webhook / SCM polling | Repository trigger | Push / PR |
| Azure auth | Credentials or OIDC | Service Connection | OIDC (federated credentials) |
| State storage | Azure Storage (`azurerm` backend) | Azure Storage (`azurerm` backend) | Azure Storage (`azurerm` backend) |
| Approval | `input` step in the Jenkinsfile | Environment approvals | Environments / required reviewers |
| Pipeline file | `Jenkinsfile` | `azure-pipelines.yml` | `.github/workflows/*.yml` |

The state backend is the same everywhere (Azure Storage) regardless of which CI/CD tool drives the pipeline - the differences are all in how each tool triggers, authenticates, and gates the apply step.
