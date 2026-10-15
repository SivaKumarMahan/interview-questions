# Practice Project 3.2: Terraform CI/CD with GitHub Actions and Azure DevOps

> This guide shows how to run Terraform safely from a pipeline: secretless OIDC login to Azure, checks on every pull request, a plan posted for review, an approved apply of the exact saved plan, and scheduled drift detection, in both GitHub Actions and Azure DevOps.

## Key Concepts

### What you will build

You will take the `envs/prod` configuration from Project 3.1 and stop running Terraform from your laptop. Instead:

1. A pull request triggers **fmt check, validate, tflint, a Checkov security scan and a `terraform plan`**. The plan is posted as a PR comment.
2. Merging to `main` triggers a new plan from the merged code, saved as an artifact.
3. The **apply** job waits for a human approval on the `prod` environment, then applies **exactly that saved plan**.
4. A **scheduled drift check** runs `terraform plan -detailed-exitcode` every weekday and opens an issue if Azure no longer matches the code.
5. Login to Azure uses **OpenID Connect (OIDC) / workload identity federation**. No client secret is stored anywhere.

You will build this twice: once with GitHub Actions and once with Azure Pipelines, so you can discuss both in interviews.

### Architecture

```text
Developer -> feature branch -> Pull Request
                                   |
          +------------------------v-------------------------+
          | CI (PR)                                          |
          | fmt -check | validate | tflint | checkov         |
          | OIDC login (subject: pull_request)               |
          | terraform plan -> PR comment                     |
          +------------------------+-------------------------+
                                   | review + merge (branch protection)
          +------------------------v-------------------------+
          | CD (push to main)                                |
          | job plan  (subject: ref:refs/heads/main)         |
          |   plan -out=tfplan -> upload artifact            |
          | job apply (subject: environment:prod)            |
          |   wait for required reviewers                    |
          |   download artifact -> terraform apply tfplan    |
          +------------------------+-------------------------+
                                   |
                       Azure subscription (prod)
                       State: Storage account, blob lease lock

Scheduled (weekdays 06:00 UTC): plan -detailed-exitcode -> exit 2 = drift -> open issue

OIDC flow: runner asks GitHub/Azure DevOps for a signed JWT -> Entra ID checks
issuer + subject + audience against a federated credential -> returns a
short-lived Azure access token. No secret is stored.
```

### Tools and why each one is used

| Tool | What it does here | Why this tool |
| --- | --- | --- |
| GitHub Actions | Runs PR checks, plan, apply and drift jobs | Native to GitHub, environments with approvals |
| Azure Pipelines | Same flow for teams on Azure DevOps | Stages, environments, approvals and checks |
| OIDC / workload identity federation | Passwordless login to Azure | No secret to leak or rotate |
| `hashicorp/setup-terraform@v3` | Installs a pinned Terraform version | Same version as developers use |
| tflint + azurerm ruleset | Lints for invalid VM sizes, deprecated syntax, unused variables | Catches errors `validate` does not |
| Checkov (or Trivy) | Scans HCL for security misconfigurations | Shift-left security, fails the PR early |
| `actions/github-script@v7` | Posts or updates the plan as a PR comment | Reviewers see the impact without opening logs |
| Environments (GitHub / ADO) | Required reviewers before apply | Human gate for production changes |

### Prerequisites

- Projects 3 and 3.1 done: a working `envs/prod` and the state storage account.
- A GitHub repository (for part A) and/or an Azure DevOps project (for part B).
- Azure permissions to create an app registration and role assignments (Application Administrator in Entra ID or the default "users can register apps" setting, plus Owner or User Access Administrator on the target scope).
- Azure CLI 2.60+ and the GitHub CLI (`gh`) locally:

```bash
az version
gh --version
gh auth login
```

- **Cost warning:** the pipelines themselves are free on public runners within limits, but every apply creates real Azure resources. Destroy prod after practicing.

### Folder structure

```text
infra-live/
├── .github/
│   └── workflows/
│       ├── terraform.yml          # PR checks + plan, apply on main
│       └── terraform-drift.yml    # scheduled drift detection
├── azure-pipelines/
│   ├── terraform.yml              # Azure DevOps Plan -> Apply
│   └── drift.yml                  # Azure DevOps scheduled drift
├── .tflint.hcl
├── .checkov.yaml
├── CODEOWNERS
├── keys/
│   └── azure_lab.pub              # public key only, safe to commit
├── modules/ ...
└── envs/
    ├── dev/ ...
    └── prod/
        ├── backend.tf
        ├── providers.tf
        ├── main.tf
        ├── terraform.tfvars
        └── .terraform.lock.hcl    # committed
```

### Step-by-step

#### Step 1: Make the configuration CI-friendly

A runner has no `~/.ssh` folder and no interactive login. Fix these before writing any pipeline.

```hcl
# envs/prod/terraform.tfvars (changes only)
subscription_id     = "<subscription-id>"     # not a secret; or pass TF_VAR_subscription_id
ssh_public_key_path = "../../keys/azure_lab.pub"
```

```bash
# Lock provider checksums for Linux runners AND your laptop, then commit the lock file
cd envs/prod
terraform providers lock -platform=linux_amd64 -platform=darwin_arm64 -platform=windows_amd64
git add .terraform.lock.hcl keys/azure_lab.pub
```

What this does:

- A **public** SSH key is safe to commit. Never commit a private key.
- `terraform providers lock` records hashes for every platform, so `init` on the runner does not fail with "checksum mismatch" or rewrite the lock file.
- The backend block already has `use_azuread_auth = true`. In CI the backend and the provider both read the same `ARM_*` environment variables, including `ARM_USE_OIDC`.

#### Step 2: Create the Entra ID identity and federated credentials (GitHub)

Use two app registrations: a **plan** identity with read-only rights and an **apply** identity with write rights. A pull request from any branch can then never change Azure.

```bash
#!/usr/bin/env bash
set -euo pipefail
REPO="<org>/<repo>"
SUB_ID="<subscription-id>"
STATE_SA_ID=$(az storage account show -n <storage-account-name> -g rg-tfstate --query id -o tsv)

create_identity() {
  local name=$1
  local app_id
  app_id=$(az ad app create --display-name "$name" --query appId -o tsv)
  az ad sp create --id "$app_id" > /dev/null
  echo "$app_id"
}

PLAN_APP=$(create_identity "gh-terraform-plan")
APPLY_APP=$(create_identity "gh-terraform-apply")

add_fic() {   # app-id, credential-name, subject
  az ad app federated-credential create --id "$1" --parameters "{
    \"name\": \"$2\",
    \"issuer\": \"https://token.actions.githubusercontent.com\",
    \"subject\": \"$3\",
    \"audiences\": [\"api://AzureADTokenExchange\"]
  }"
}

add_fic "$PLAN_APP"  "pull-request" "repo:${REPO}:pull_request"
add_fic "$PLAN_APP"  "main-branch"  "repo:${REPO}:ref:refs/heads/main"
add_fic "$APPLY_APP" "env-prod"     "repo:${REPO}:environment:prod"

# Plan identity: read Azure, read/write state (plan takes a lock = writes a lease)
az role assignment create --assignee "$PLAN_APP"  --role "Reader" --scope "/subscriptions/$SUB_ID"
az role assignment create --assignee "$PLAN_APP"  --role "Storage Blob Data Contributor" --scope "$STATE_SA_ID"

# Apply identity: change resources, read/write state
az role assignment create --assignee "$APPLY_APP" --role "Contributor" --scope "/subscriptions/$SUB_ID"
az role assignment create --assignee "$APPLY_APP" --role "Storage Blob Data Contributor" --scope "$STATE_SA_ID"

echo "PLAN_CLIENT_ID=$PLAN_APP  APPLY_CLIENT_ID=$APPLY_APP"
az account show --query "{tenant:tenantId, subscription:id}" -o table
```

What this does:

- A **federated credential** says: "trust tokens from this issuer, with exactly this subject and audience". No password is created.
- The **subject** depends on what triggered the job:
  - `repo:<org>/<repo>:pull_request` for any `pull_request` event.
  - `repo:<org>/<repo>:environment:prod` for any job that declares `environment: prod`. When a job uses an environment, the subject is the environment, not the branch.
  - `repo:<org>/<repo>:ref:refs/heads/main` for jobs on `main` **without** an environment. We need it for the plan job on push and the scheduled drift job. (If you want only two subjects, run those jobs in a `prod` environment too, but then they would also wait for approval.)
- Subjects are exact matches (unless you use the newer "flexible federated identity credentials" preview). A typo means `AADSTS70021: No matching federated identity record found`.
- `Reader` is enough for most plans. Some resources need extra read actions during refresh (for example storage account keys); give the plan identity a custom role if a plan fails with 403.
- Prefer a resource-group scope over subscription scope for Contributor when possible. Add `User Access Administrator` (or a constrained custom role) only if Terraform creates role assignments.

#### Step 3: Configure the GitHub repository

```bash
REPO="<org>/<repo>"
gh variable set AZURE_TENANT_ID       --repo "$REPO" --body "<tenant-id>"
gh variable set AZURE_SUBSCRIPTION_ID --repo "$REPO" --body "<subscription-id>"
gh variable set AZURE_CLIENT_ID       --repo "$REPO" --body "<plan-client-id>"

# Environment "prod" with its own (apply) client ID
REVIEWER_ID=$(gh api users/<github-username> --jq .id)
gh api -X PUT "repos/$REPO/environments/prod" --input - <<JSON
{
  "reviewers": [{ "type": "User", "id": $REVIEWER_ID }],
  "prevent_self_review": true,
  "deployment_branch_policy": { "protected_branches": true, "custom_branch_policies": false }
}
JSON
gh variable set AZURE_CLIENT_ID --repo "$REPO" --env prod --body "<apply-client-id>"
```

What this does:

- Client, tenant and subscription IDs are **identifiers, not secrets**, so they are stored as variables. There are no Azure secrets in the repo at all.
- The environment-level `AZURE_CLIENT_ID` **overrides** the repo-level one for jobs that use `environment: prod`. So the apply job automatically logs in as the apply identity.
- **Required reviewers** pause the apply job until someone approves. `prevent_self_review` stops the person who triggered the run from approving it.
- The deployment branch policy allows only protected branches (main) to deploy to `prod`.
- You can do the same in the UI: Settings -> Environments -> New environment.

#### Step 4: Add lint and security scan config

```hcl
# .tflint.hcl
config {
  call_module_type = "local"
}

plugin "terraform" {
  enabled = true
  preset  = "recommended"
}

plugin "azurerm" {
  enabled = true
  version = "0.27.0"
  source  = "github.com/terraform-linters/tflint-ruleset-azurerm"
}
```

```yaml
# .checkov.yaml
framework:
  - terraform
quiet: true
compact: true
skip-check:
  # Lab-only exceptions: document a reason for each one
  - CKV_AZURE_97   # VMSS encryption at host (not enabled on the lab subscription)
```

What this does:

- `call_module_type = "local"` makes tflint follow local module calls (`../../modules/...`).
- The azurerm ruleset knows valid VM sizes and other Azure values, so a typo like `Standard_B2ss` fails in CI instead of during apply. Check the latest ruleset version on its releases page and pin it.
- Checkov fails the build on findings such as public storage, NSG rules open to `0.0.0.0/0` on SSH, or missing encryption. Every skipped check should have a comment explaining why. Trivy can do the same job with `trivy config --severity HIGH,CRITICAL --exit-code 1 .`.

#### Step 5: GitHub Actions workflow (PR plan and apply on main)

```yaml
# .github/workflows/terraform.yml
name: terraform

on:
  pull_request:
    branches: [main]
    paths:
      - "envs/prod/**"
      - "modules/**"
      - ".github/workflows/terraform.yml"
  push:
    branches: [main]
    paths:
      - "envs/prod/**"
      - "modules/**"
      - ".github/workflows/terraform.yml"
  workflow_dispatch:

permissions:
  contents: read

# One run per branch at a time; PR runs are replaced by newer pushes, main runs are never cancelled
concurrency:
  group: terraform-prod-${{ github.ref }}
  cancel-in-progress: ${{ github.event_name == 'pull_request' }}

env:
  TF_VERSION: "1.9.8"
  TF_DIR: envs/prod
  TF_IN_AUTOMATION: "true"
  TF_INPUT: "false"
  ARM_USE_OIDC: "true"
  ARM_USE_AZUREAD: "true"
  ARM_CLIENT_ID: ${{ vars.AZURE_CLIENT_ID }}
  ARM_TENANT_ID: ${{ vars.AZURE_TENANT_ID }}
  ARM_SUBSCRIPTION_ID: ${{ vars.AZURE_SUBSCRIPTION_ID }}

jobs:
  checks:
    name: fmt / validate / lint / scan
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: hashicorp/setup-terraform@v3
        with:
          terraform_version: ${{ env.TF_VERSION }}

      - name: terraform fmt
        run: terraform fmt -check -recursive -diff

      - name: terraform validate
        working-directory: ${{ env.TF_DIR }}
        run: |
          terraform init -backend=false
          terraform validate

      - uses: terraform-linters/setup-tflint@v4

      - name: tflint
        env:
          GITHUB_TOKEN: ${{ github.token }}
        run: |
          tflint --init
          tflint --recursive --config "$GITHUB_WORKSPACE/.tflint.hcl"

      - name: checkov
        uses: bridgecrewio/checkov-action@v12
        with:
          directory: .
          config_file: .checkov.yaml

  plan:
    name: plan
    needs: checks
    runs-on: ubuntu-latest
    permissions:
      contents: read
      id-token: write        # allow the job to request an OIDC token
      pull-requests: write   # allow posting the plan comment
    outputs:
      exitcode: ${{ steps.plan.outputs.exitcode }}
    defaults:
      run:
        working-directory: ${{ env.TF_DIR }}
    steps:
      - uses: actions/checkout@v4

      - uses: hashicorp/setup-terraform@v3
        with:
          terraform_version: ${{ env.TF_VERSION }}
          terraform_wrapper: false

      - name: terraform init
        run: terraform init

      - name: terraform plan
        id: plan
        run: |
          set +e
          terraform plan -out=tfplan -detailed-exitcode -lock-timeout=5m -no-color
          ec=$?
          set -e
          echo "exitcode=$ec" >> "$GITHUB_OUTPUT"
          if [ "$ec" -eq 1 ]; then exit 1; fi
          terraform show -no-color tfplan > plan.txt
          {
            echo "### Terraform plan (${TF_DIR})"
            echo '```text'
            tail -c 60000 plan.txt
            echo '```'
          } >> "$GITHUB_STEP_SUMMARY"

      - name: Post plan to PR
        if: github.event_name == 'pull_request'
        uses: actions/github-script@v7
        with:
          script: |
            const fs = require('fs');
            const dir = process.env.TF_DIR;
            const marker = `<!-- terraform-plan:${dir} -->`;
            const fence = '`'.repeat(3);
            let plan = fs.readFileSync(`${dir}/plan.txt`, 'utf8');
            if (plan.length > 60000) {
              plan = plan.substring(plan.length - 60000) + '\n(truncated, see the job summary)';
            }
            const body = [
              marker,
              `#### Terraform plan for \`${dir}\` (exit code ${{ steps.plan.outputs.exitcode }})`,
              '<details><summary>Show plan</summary>',
              '',
              `${fence}text`,
              plan,
              fence,
              '</details>',
              '',
              `Run: ${context.serverUrl}/${context.repo.owner}/${context.repo.repo}/actions/runs/${context.runId}`
            ].join('\n');

            const { data: comments } = await github.rest.issues.listComments({
              owner: context.repo.owner,
              repo: context.repo.repo,
              issue_number: context.issue.number,
            });
            const existing = comments.find(c => c.user.type === 'Bot' && c.body.includes(marker));
            if (existing) {
              await github.rest.issues.updateComment({
                owner: context.repo.owner, repo: context.repo.repo,
                comment_id: existing.id, body,
              });
            } else {
              await github.rest.issues.createComment({
                owner: context.repo.owner, repo: context.repo.repo,
                issue_number: context.issue.number, body,
              });
            }

      - name: Upload plan artifact
        if: github.event_name != 'pull_request' && steps.plan.outputs.exitcode == '2'
        uses: actions/upload-artifact@v4
        with:
          name: tfplan-prod
          path: ${{ env.TF_DIR }}/tfplan
          retention-days: 5

  apply:
    name: apply (prod)
    needs: plan
    if: github.event_name != 'pull_request' && github.ref == 'refs/heads/main' && needs.plan.outputs.exitcode == '2'
    runs-on: ubuntu-latest
    environment: prod        # waits for required reviewers; uses env-level AZURE_CLIENT_ID
    env:
      ARM_CLIENT_ID: ${{ vars.AZURE_CLIENT_ID }}   # resolves to the prod environment's value (apply identity)
    permissions:
      contents: read
      id-token: write
    defaults:
      run:
        working-directory: ${{ env.TF_DIR }}
    steps:
      - uses: actions/checkout@v4

      - uses: hashicorp/setup-terraform@v3
        with:
          terraform_version: ${{ env.TF_VERSION }}
          terraform_wrapper: false

      - name: terraform init
        run: terraform init

      - uses: actions/download-artifact@v4
        with:
          name: tfplan-prod
          path: ${{ env.TF_DIR }}

      - name: terraform apply (saved plan)
        run: terraform apply -lock-timeout=5m tfplan
```

What this does:

- **`permissions: id-token: write`** lets the job request an OIDC token from GitHub. Without it, login fails with "Unable to get ACTIONS_ID_TOKEN_REQUEST_URL". Fork PRs never get this token, which is a good safety property.
- **`ARM_USE_OIDC=true` + `ARM_CLIENT_ID/TENANT_ID/SUBSCRIPTION_ID`** are read by both the azurerm provider and the azurerm backend. They fetch the GitHub token and exchange it with Entra ID themselves, so `azure/login` is not needed. Use `azure/login@v2` only if you also run `az` commands.
- `ARM_USE_AZUREAD=true` is the environment form of `use_azuread_auth` for the backend.
- `terraform_wrapper: false` makes `terraform` return its real exit code without the wrapper script, which keeps `-detailed-exitcode` simple.
- **`-detailed-exitcode`**: 0 = no changes, 1 = error, 2 = changes present. We skip artifact and apply when there is nothing to do.
- The PR comment is **updated in place** (found by the hidden marker), so a PR with ten pushes has one plan comment, not ten. GitHub limits comment size to about 65,000 characters, so we truncate.
- The plan from the PR is **not** applied. After merge, the main branch is planned again because main may contain other merged changes. That plan is uploaded, reviewed (job summary) and approved.
- **`apply` applies the saved `tfplan`**. If anything changed state between plan and apply, Terraform refuses with "Saved plan is stale", and you re-run the workflow.
- **`concurrency`**: runs for the same ref queue instead of running in parallel, so two applies never race. The state lock is the second line of defense. Note: GitHub keeps only the newest **pending** run in a group, older pending runs are cancelled.
- The plan artifact can contain sensitive values. Keep retention short and restrict who can read the repo's Actions artifacts.

#### Step 6: Drift detection workflow (GitHub)

```yaml
# .github/workflows/terraform-drift.yml
name: terraform-drift

on:
  schedule:
    - cron: "0 6 * * 1-5"    # 06:00 UTC, Monday to Friday
  workflow_dispatch:

permissions:
  contents: read
  id-token: write
  issues: write

env:
  TF_DIR: envs/prod
  TF_IN_AUTOMATION: "true"
  TF_INPUT: "false"
  ARM_USE_OIDC: "true"
  ARM_USE_AZUREAD: "true"
  ARM_CLIENT_ID: ${{ vars.AZURE_CLIENT_ID }}
  ARM_TENANT_ID: ${{ vars.AZURE_TENANT_ID }}
  ARM_SUBSCRIPTION_ID: ${{ vars.AZURE_SUBSCRIPTION_ID }}

jobs:
  drift:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: ${{ env.TF_DIR }}
    steps:
      - uses: actions/checkout@v4

      - uses: hashicorp/setup-terraform@v3
        with:
          terraform_version: "1.9.8"
          terraform_wrapper: false

      - run: terraform init

      - name: Detect drift
        id: drift
        run: |
          set +e
          terraform plan -detailed-exitcode -lock-timeout=5m -no-color > drift.txt 2>&1
          ec=$?
          set -e
          echo "exitcode=$ec" >> "$GITHUB_OUTPUT"
          if [ "$ec" -eq 1 ]; then cat drift.txt; exit 1; fi

      - name: Open issue on drift
        if: steps.drift.outputs.exitcode == '2'
        env:
          GH_TOKEN: ${{ github.token }}
        run: |
          head -c 60000 drift.txt > body.txt
          gh issue create \
            --title "Terraform drift detected in ${TF_DIR} ($(date -u +%F))" \
            --body-file body.txt \
            --label drift
```

What this does:

- Scheduled workflows run on the **default branch**, so the OIDC subject is `ref:refs/heads/main` and the job uses the read-only plan identity. Drift detection never changes anything.
- Exit code 2 means "Azure differs from code". That can be real drift (someone changed an NSG in the portal) or code merged but not yet applied. Use `terraform plan -refresh-only` if you want only changes made outside Terraform.
- Create the `drift` label first (`gh label create drift`), or remove `--label`.
- Response to drift: either revert Azure by applying the code, or update the code to match the intended change. Never leave drift open.

#### Step 7: Azure DevOps service connection with workload identity federation

In Azure DevOps: **Project settings -> Service connections -> New -> Azure Resource Manager -> Workload identity federation (automatic)**. Choose the subscription and resource group, name it `sc-azure-prod`, and do not tick "Grant access permission to all pipelines".

Then give its identity access to the state storage:

```bash
# The service connection page shows the app registration (client) ID
SC_APP_ID="<service-connection-client-id>"
STATE_SA_ID=$(az storage account show -n <storage-account-name> -g rg-tfstate --query id -o tsv)
az role assignment create --assignee "$SC_APP_ID" \
  --role "Storage Blob Data Contributor" --scope "$STATE_SA_ID"
```

What this does:

- The automatic option creates an app registration plus a federated credential with issuer `https://vstoken.dev.azure.com/<organization-id>` and subject `sc://<org>/<project>/sc-azure-prod`.
- It also assigns Contributor on the scope you chose. Storage **data-plane** access for the state is a separate role, so we add it.
- For stronger separation, create two service connections (plan read-only, apply contributor), same idea as the GitHub version.

#### Step 8: Azure DevOps pipeline (Plan -> Apply)

There are two common ways to run Terraform in Azure Pipelines:

| Option | How auth works | Trade-off |
| --- | --- | --- |
| `TerraformTaskV4@4` (Microsoft DevLabs marketplace extension) | Task reads the service connection and sets `ARM_*` for you, including OIDC | Must install the extension; less control over CLI flags such as `-detailed-exitcode` |
| `AzureCLI@2` with `addSpnToEnvironment: true` | Task exposes `servicePrincipalId`, `tenantId` and `idToken` to the script; you map them to `ARM_*` | Plain Terraform CLI, no extension, fully visible commands |

This guide uses **`AzureCLI@2`** because every command is visible and it works the same as running Terraform locally.

```yaml
# azure-pipelines/terraform.yml
trigger:
  branches:
    include: [main]
  paths:
    include: [envs/prod/*, modules/*]

pr: none   # for Azure Repos, PR validation is configured as a branch policy (Step 10)

variables:
  TF_VERSION: "1.9.8"
  TF_DIR: envs/prod
  SERVICE_CONNECTION: sc-azure-prod

pool:
  vmImage: ubuntu-latest

stages:
  - stage: Plan
    jobs:
      - job: plan
        steps:
          - checkout: self

          - bash: |
              set -euo pipefail
              curl -sSLo tf.zip "https://releases.hashicorp.com/terraform/$(TF_VERSION)/terraform_$(TF_VERSION)_linux_amd64.zip"
              sudo unzip -o tf.zip -d /usr/local/bin terraform
              terraform version
              terraform fmt -check -recursive
            displayName: Install Terraform and fmt check

          - task: AzureCLI@2
            name: tfplan
            displayName: terraform plan
            inputs:
              azureSubscription: $(SERVICE_CONNECTION)
              scriptType: bash
              scriptLocation: inlineScript
              addSpnToEnvironment: true
              workingDirectory: $(TF_DIR)
              inlineScript: |
                set -euo pipefail
                export ARM_CLIENT_ID="$servicePrincipalId"
                export ARM_TENANT_ID="$tenantId"
                export ARM_OIDC_TOKEN="$idToken"
                export ARM_USE_OIDC=true
                export ARM_USE_AZUREAD=true
                export ARM_SUBSCRIPTION_ID="$(az account show --query id -o tsv)"
                export TF_IN_AUTOMATION=true

                terraform init -input=false
                terraform validate

                set +e
                terraform plan -input=false -out=tfplan -detailed-exitcode -lock-timeout=5m -no-color
                ec=$?
                set -e
                if [ "$ec" -eq 1 ]; then exit 1; fi

                terraform show -no-color tfplan > plan.txt
                { echo '```text'; tail -c 60000 plan.txt; echo '```'; } > plan.md
                echo "##vso[task.uploadsummary]$(pwd)/plan.md"

                if [ "$ec" -eq 2 ]; then changes=true; else changes=false; fi
                echo "##vso[task.setvariable variable=hasChanges;isOutput=true]$changes"

          - publish: $(TF_DIR)/tfplan
            artifact: tfplan
            displayName: Publish plan artifact
            condition: and(succeeded(), eq(variables['tfplan.hasChanges'], 'true'))

  - stage: Apply
    dependsOn: Plan
    condition: >-
      and(succeeded(),
          eq(variables['Build.SourceBranch'], 'refs/heads/main'),
          eq(dependencies.Plan.outputs['plan.tfplan.hasChanges'], 'true'))
    jobs:
      - deployment: apply
        environment: prod          # approvals and checks are configured on this environment
        strategy:
          runOnce:
            deploy:
              steps:
                - checkout: self   # deployment jobs do not check out code by default

                - download: current
                  artifact: tfplan

                - bash: |
                    set -euo pipefail
                    curl -sSLo tf.zip "https://releases.hashicorp.com/terraform/$(TF_VERSION)/terraform_$(TF_VERSION)_linux_amd64.zip"
                    sudo unzip -o tf.zip -d /usr/local/bin terraform
                  displayName: Install Terraform

                - task: AzureCLI@2
                  displayName: terraform apply (saved plan)
                  inputs:
                    azureSubscription: $(SERVICE_CONNECTION)
                    scriptType: bash
                    scriptLocation: inlineScript
                    addSpnToEnvironment: true
                    workingDirectory: $(TF_DIR)
                    inlineScript: |
                      set -euo pipefail
                      export ARM_CLIENT_ID="$servicePrincipalId"
                      export ARM_TENANT_ID="$tenantId"
                      export ARM_OIDC_TOKEN="$idToken"
                      export ARM_USE_OIDC=true
                      export ARM_USE_AZUREAD=true
                      export ARM_SUBSCRIPTION_ID="$(az account show --query id -o tsv)"
                      export TF_IN_AUTOMATION=true

                      cp "$(Pipeline.Workspace)/tfplan/tfplan" ./tfplan
                      terraform init -input=false
                      terraform apply -input=false -lock-timeout=5m tfplan
```

What this does:

- **`addSpnToEnvironment: true`** exposes `servicePrincipalId`, `tenantId` and, for workload identity federation, **`idToken`** to the script. Mapping `idToken` to `ARM_OIDC_TOKEN` lets the provider and backend log in with OIDC. No secret exists.
- The `idToken` is short-lived and is not refreshed during the step. Very long applies can fail with an expired token. Newer azurerm versions can request fresh tokens from Azure DevOps directly using the service connection ID and `SYSTEM_ACCESSTOKEN`; check the azurerm provider authentication docs for the exact settings if you hit this.
- `$(TF_VERSION)` and `$(Pipeline.Workspace)` are **pipeline macros** replaced before the script runs; `$servicePrincipalId` and `$ec` are normal shell variables.
- `##vso[task.setvariable ...;isOutput=true]` creates an output variable. The Apply stage reads it with `dependencies.Plan.outputs['plan.tfplan.hasChanges']` (stage.job.step.variable), so Apply is skipped when there is nothing to change.
- `##vso[task.uploadsummary]` adds the plan to the run's **Extensions** tab for reviewers.
- `publish` uploads `tfplan` as a **pipeline artifact**; `download: current` puts it in `$(Pipeline.Workspace)/tfplan/` in the Apply stage.
- A **deployment job** targeting `environment: prod` pauses until the environment's approvals and checks pass. It also records deployment history on the environment.
- Pipeline runs with the same service connection can still overlap; add an **Exclusive lock** check on the `prod` environment so only one run deploys at a time.

#### Step 9: Azure DevOps environment approvals and drift schedule

In **Pipelines -> Environments -> New environment** create `prod`, then **Approvals and checks**:

- **Approvals**: add approvers; untick "Allow approvers to approve their own runs".
- **Branch control**: allowed branches `refs/heads/main`, so a feature branch pipeline can never deploy.
- **Exclusive lock**: one deployment at a time.

Drift detection pipeline:

```yaml
# azure-pipelines/drift.yml
trigger: none
pr: none

schedules:
  - cron: "0 6 * * 1-5"
    displayName: Weekday drift check
    branches:
      include: [main]
    always: true          # run even if there were no code changes

variables:
  TF_VERSION: "1.9.8"
  TF_DIR: envs/prod

pool:
  vmImage: ubuntu-latest

steps:
  - bash: |
      set -euo pipefail
      curl -sSLo tf.zip "https://releases.hashicorp.com/terraform/$(TF_VERSION)/terraform_$(TF_VERSION)_linux_amd64.zip"
      sudo unzip -o tf.zip -d /usr/local/bin terraform
    displayName: Install Terraform

  - task: AzureCLI@2
    displayName: Detect drift
    inputs:
      azureSubscription: sc-azure-prod-plan    # read-only connection if you created one
      scriptType: bash
      scriptLocation: inlineScript
      addSpnToEnvironment: true
      workingDirectory: $(TF_DIR)
      inlineScript: |
        set -euo pipefail
        export ARM_CLIENT_ID="$servicePrincipalId" ARM_TENANT_ID="$tenantId" ARM_OIDC_TOKEN="$idToken"
        export ARM_USE_OIDC=true ARM_USE_AZUREAD=true
        export ARM_SUBSCRIPTION_ID="$(az account show --query id -o tsv)"
        terraform init -input=false
        set +e
        terraform plan -input=false -detailed-exitcode -lock-timeout=5m -no-color
        ec=$?
        set -e
        if [ "$ec" -eq 2 ]; then
          echo "##vso[task.logissue type=error]Drift detected in $(TF_DIR)"
          exit 1
        fi
        exit "$ec"
```

What this does:

- `always: true` is important: by default a scheduled run is skipped if nothing changed in the repo, but drift happens in Azure, not in git.
- Failing the run on drift turns it red and triggers the pipeline's failure notifications (email or Teams).

#### Step 10: Branch protection

The pipeline is only as safe as the rules around `main`.

GitHub (Settings -> Rules -> Rulesets, target `main`):

```text
- Require a pull request before merging, 1-2 approvals
- Require review from Code Owners (CODEOWNERS: /envs/prod/ @<org>/platform-team)
- Dismiss stale approvals when new commits are pushed
- Require status checks: "fmt / validate / lint / scan" and "plan"
- Require branches to be up to date before merging
- Block force pushes and deletions; require linear history
- Do not allow bypass, including admins
```

Azure Repos (Project settings -> Repositories -> main -> Policies):

```text
- Require a minimum number of reviewers (2), do not allow requestors to approve their own changes
- Check for comment resolution
- Build validation: a PR pipeline (same Plan stage, no Apply) set to Required
- Automatically included reviewers for /envs/prod/*
- Limit merge types (squash merge)
```

What this does:

- Required checks mean a PR with failing fmt, lint, scan or plan cannot merge.
- CODEOWNERS makes the platform team review every prod change.
- Combined with the environment approval, a prod change needs a reviewed PR **and** an approved deployment.

### Verify it works

1. Create a branch, change `web_instance_count` in `envs/prod/terraform.tfvars`, push and open a PR.

```bash
git switch -c scale-web
sed -i 's/web_instance_count = 3/web_instance_count = 4/' envs/prod/terraform.tfvars
git commit -am "Scale web tier to 4" && git push -u origin scale-web
gh pr create --fill
gh pr checks --watch
```

Expected: all checks pass and the PR has a comment like:

```text
#### Terraform plan for `envs/prod` (exit code 2)
  # module.compute.azurerm_linux_virtual_machine_scale_set.this will be updated in-place
  ~ instances = 3 -> 4
Plan: 0 to add, 1 to change, 0 to destroy.
```

2. Merge the PR. The `apply (prod)` job shows **Waiting for review**. Approve it in the Actions UI, then check:

```bash
gh run list --workflow terraform.yml --limit 3
az vmss show -g rg-3tier-prod -n vmss-web-3tier-prod --query sku.capacity -o tsv
# 4
```

3. Test drift: change something in the portal (for example add a tag to the VNet), then run `gh workflow run terraform-drift.yml`. Expected: a new issue "Terraform drift detected in envs/prod".

4. Test a failing check: add a badly formatted line to a `.tf` file. Expected: `terraform fmt -check` fails and the PR cannot be merged.

### Common problems and fixes

| Problem | Likely cause | Fix |
| --- | --- | --- |
| `AADSTS70021: No matching federated identity record found` | Subject in the token does not match any federated credential | Check event type: PR = `pull_request`, job with environment = `environment:prod`, main without environment = `ref:refs/heads/main` |
| `Unable to get ACTIONS_ID_TOKEN_REQUEST_URL` | Job lacks `id-token: write`, or PR comes from a fork | Add the permission; fork PRs cannot get Azure tokens by design |
| Backend init 403 `AuthorizationPermissionMismatch` | Identity has no Storage Blob Data role on the state account | Assign `Storage Blob Data Contributor` on the storage account |
| `Saved plan is stale` during apply | Another apply changed state after this plan was made | Re-run the workflow to create a fresh plan |
| `Error acquiring the state lock` in PR plan | An apply or another plan holds the lease | `-lock-timeout=5m` waits; investigate if it persists |
| Plan fails with 403 on a read (for example listKeys) | Read-only identity lacks a specific read action | Add a custom role with that action to the plan identity |
| ADO apply fails mid-way with token expired | `idToken` is short-lived and not refreshed | Split large applies, or use the provider's Azure DevOps token refresh settings |
| Checkov fails on a lab-only setting | Policy correctly flags a weak setting | Fix it, or skip with a documented reason in `.checkov.yaml` |
| `init` rewrites `.terraform.lock.hcl` in CI | Lock file lacks hashes for linux_amd64 | Run `terraform providers lock -platform=linux_amd64 ...` and commit |

### Clean up

```bash
# Destroy prod infrastructure (from a trusted machine with the apply identity, or a manual workflow)
cd envs/prod && terraform destroy

# Remove identities and their role assignments
for APP in <plan-client-id> <apply-client-id>; do
  az role assignment delete --assignee "$APP"   # remove role assignments first
  az ad app delete --id "$APP"
done

# GitHub: delete the prod environment and variables
gh api -X DELETE repos/<org>/<repo>/environments/prod
gh variable delete AZURE_CLIENT_ID --repo <org>/<repo>
```

In Azure DevOps, delete the `sc-azure-prod` service connection (this can also delete the app registration it created) and the `prod` environment.

### Next improvements

- Add `terraform test` and Infracost (cost diff in the PR comment).
- Run the same workflow for `envs/dev` and `envs/prod` with a matrix, and auto-apply dev without approval.
- Pin third-party actions to a full commit SHA and let Dependabot update them.
- Add policy as code: OPA/Conftest on `terraform show -json tfplan`, or Azure Policy deny rules as a backstop.
- Encrypt the plan artifact, or switch to HCP Terraform remote runs where plans never leave the platform.
- Send drift results to a Teams or Slack channel and track time-to-resolve.

### How to explain this project in an interview

> "As a hands-on practice project, I automated Terraform for an Azure environment in both GitHub Actions and Azure DevOps. Authentication uses OIDC workload identity federation, so there are no client secrets. In GitHub I created federated credentials for the pull_request subject, the main branch and the prod environment, and used a read-only identity for plans and a contributor identity only in the approved apply job. Every pull request runs fmt check, validate, tflint, a Checkov scan and a plan that is posted as a PR comment. After merge, main is planned again, the plan file is uploaded as an artifact, and the apply job waits for required reviewers and applies exactly that saved plan. A concurrency group and the state lock prevent parallel applies. A scheduled job uses plan with detailed-exitcode to detect drift and open an issue. In Azure DevOps I built the same flow with AzureCLI tasks, an environment approval, and a deployment job."

Points that impress interviewers:

- You know the OIDC subject changes when a job uses an environment, and design federated credentials accordingly.
- You apply the saved plan from main, not the PR plan, and you know what "stale plan" protects against.
- You separate plan and apply identities (least privilege) and block forks from getting tokens.
- You treat drift detection as a scheduled, alerting process, not a manual check.

## Interview Questions

<details><summary>Q1. [Basic] Why use OIDC instead of a client secret for Terraform in CI/CD?</summary>

**Answer:**

With a client secret, a long-lived password sits in the CI system. It can leak through logs or a compromised repo, and it must be rotated before it expires.

With OIDC (workload identity federation), the CI platform issues a short-lived signed token for each job. Entra ID trusts it only if the issuer, subject (for example `repo:org/repo:environment:prod`) and audience match a federated credential. Azure returns an access token valid for about an hour. Nothing long-lived is stored, nothing needs rotation, and the trust can be limited to a specific branch or environment.

</details>

<details><summary>Q2. [Basic] What does <code>terraform plan -detailed-exitcode</code> return and where do you use it?</summary>

**Answer:**

- `0`: success, no changes.
- `1`: error.
- `2`: success, there are changes.

In pipelines it lets you skip the apply stage when there is nothing to do, and it is the basis of **drift detection**: a scheduled plan returning 2 means Azure differs from the code. Remember that a normal `set -e` shell treats 2 as failure, so capture the code with `set +e` first.

</details>

<details><summary>Q3. [Basic] Why do we save the plan with <code>-out</code> and apply the plan file instead of running <code>terraform apply</code> directly?</summary>

**Answer:**

A reviewer approves what they saw. If the apply job runs `terraform apply` without a plan file, Terraform plans again, and the result may differ (new commits, someone changed Azure). Applying the saved file applies exactly the reviewed changes. If the state changed after the plan was created, Terraform rejects it as stale, which forces a fresh plan and a fresh review.

</details>

<details><summary>Q4. [Intermediate] Your apply job in GitHub fails with <code>AADSTS70021: No matching federated identity record found</code>, but the plan job works. Why? <em>(scenario)</em></summary>

**Answer:**

The plan and apply jobs present **different subjects**. The apply job declares `environment: prod`, so its token subject is `repo:<org>/<repo>:environment:prod`, not `ref:refs/heads/main`. If the app registration only has credentials for `pull_request` and `ref:refs/heads/main`, Entra ID rejects the apply token.

Fix: add a federated credential with subject `repo:<org>/<repo>:environment:prod` on the identity the apply job uses (check that `AZURE_CLIENT_ID` at environment level points to it). Also check the environment name's exact spelling and case.

</details>

<details><summary>Q5. [Intermediate] How do you prevent two Terraform applies from running at the same time?</summary>

**Answer:**

Use several layers:

1. **Pipeline concurrency**: GitHub `concurrency` group for the environment with `cancel-in-progress: false`; in Azure DevOps an **Exclusive lock** check on the environment.
2. **State locking**: the azurerm backend takes a blob lease. A second run waits (`-lock-timeout`) or fails instead of corrupting state.
3. **Saved plans**: even if two runs plan in parallel, the second apply fails with a stale plan error.
4. **Process**: only the pipeline has write access to prod; humans do not run apply from laptops.

</details>

<details><summary>Q6. [Intermediate] What do tflint and Checkov catch that <code>terraform validate</code> does not?</summary>

**Answer:**

`terraform validate` checks syntax, types and references only. It does not call Azure, so an invalid VM size passes.

- **tflint** with the azurerm ruleset catches provider-specific errors (invalid VM sizes or SKUs), deprecated syntax, unused variables and naming rules.
- **Checkov** (or Trivy) catches **security** misconfigurations: NSG rules open to the internet on SSH/RDP, storage allowing public access, missing encryption, missing diagnostics.

Running both in the PR gives fast feedback before anyone spends time reviewing a plan.

</details>

<details><summary>Q7. [Advanced] How do you run Terraform with workload identity federation in Azure DevOps without the Terraform marketplace task?</summary>

**Answer:**

Create an Azure Resource Manager service connection of type workload identity federation. Use `AzureCLI@2` with `addSpnToEnvironment: true`. The task logs in and exposes `servicePrincipalId`, `tenantId` and `idToken` to the script. Map them:

```bash
export ARM_CLIENT_ID="$servicePrincipalId"
export ARM_TENANT_ID="$tenantId"
export ARM_OIDC_TOKEN="$idToken"
export ARM_USE_OIDC=true
export ARM_SUBSCRIPTION_ID="$(az account show --query id -o tsv)"
```

The provider and the backend then authenticate with OIDC. Grant the service connection's identity `Storage Blob Data Contributor` on the state account. A caveat is that `idToken` is short-lived and not refreshed within the step, so very long applies may fail; newer azurerm versions can fetch fresh tokens from Azure DevOps using the service connection ID.

</details>

<details><summary>Q8. [Advanced] The scheduled drift job reports changes every morning, but nobody changed anything in the portal. How do you investigate? <em>(scenario)</em></summary>

**Answer:**

1. Read the plan diff. Is it a real change or noise?
2. **Unapplied code**: something merged to main but the apply was never approved. Plan shows the code change. Fix: finish or revert the deployment.
3. **Azure-side automation**: Azure Policy (`modify`/`deployIfNotExists`) adds tags or settings, or a platform service updates a field. Fix: add those attributes to code, or use `lifecycle { ignore_changes = [tags["..."]] }` for fields owned by another system.
4. **Provider defaults or normalization**: values like case differences or computed defaults causing a perpetual diff. Upgrade the provider or set the value explicitly.
5. Use `terraform plan -refresh-only` to see only out-of-band changes, and the Activity Log to see who or what changed the resource.

The goal is a drift job that is quiet when everything is fine, so a real alert gets attention.

</details>

<details><summary>Q9. [Advanced] How would you design least-privilege identities for a Terraform pipeline? <em>(scenario)</em></summary>

**Answer:**

- **Plan identity**: `Reader` on the target scope plus `Storage Blob Data Contributor` on the state account (plans take a lock lease). Its federated credentials cover `pull_request` and `ref:refs/heads/main`. Even a malicious PR cannot change Azure with it.
- **Apply identity**: `Contributor` scoped to the resource groups it manages (not the whole subscription when possible), plus state access. Add role-assignment rights only if Terraform manages RBAC, ideally with a constrained custom role or conditions. Its only federated credential is `environment:prod`, which is protected by required reviewers and branch rules.
- Separate identities per environment, so dev pipelines cannot touch prod.
- Disable shared keys on the state account and audit role assignments regularly.

</details>
