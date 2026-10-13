# Hands-on 4: Terraform CI/CD in Azure DevOps with Infracost, SonarQube, and Manual Approval

> Build one Azure DevOps pipeline that checks, costs, scans, and plans Terraform code, waits for a human to approve, and only then applies the exact plan that was reviewed.

**Time:** about 90 minutes. **Level:** Intermediate.

## What you practise

- Terraform `init`, `validate`, and `fmt -check` as fast quality checks
- Infracost cost estimation on the Terraform code and on the saved plan
- SonarQube static analysis of Terraform code with a quality gate that can fail the build
- Saving `terraform plan -out` as a pipeline artifact
- A manual approval with `ManualValidation@1` in an agentless job, or with environment approvals
- Applying the saved plan in a deployment job

This guide covers the Terraform-only pipeline. For the Helm, ACR, and AKS part, see [Hands-on 2](02-azure-devops-terraform-helm-acr-aks.md).

## Prerequisites

| Item | Purpose |
| --- | --- |
| Azure subscription | Target for the Terraform resources |
| Azure DevOps project with a Git repository | Code and pipeline |
| Azure Resource Manager service connection `azure-wif-connection` | Workload identity federation; Contributor on the target resource group, and access to the state storage account |
| Storage account `companytfstate` in `tfstate-rg`, container `tfstate` | Remote Terraform state |
| SonarQube server and service connection `sonarqube-connection` | Static analysis and quality gate |
| SonarQube and Terraform extensions from the Marketplace | Provide the `SonarQube*@7` and `Terraform*` tasks |
| Infracost API key | Stored as a secret pipeline variable `INFRACOST_API_KEY` |
| Environment `terraform-dev` (optional) | Environment approval before apply |

## Pipeline flow

```text
Terraform init -> validate -> fmt -check          (seconds, no cost)
        |
        v
Infracost breakdown on the code                   (cost estimate)
        |
        v
SonarQube analysis + quality gate                  (static code analysis)
        |
        v
Terraform plan -out=tfplan
  -> terraform show -json -> Infracost diff        (exact cost change)
  -> publish tfplan as an artifact
        |
        v
Manual approval (ManualValidation@1, agentless job)
        |
        v
Terraform apply tfplan (deployment job)
```

## Why the order matters

Each stage is more expensive than the one before it. Cheap checks run first, so a bad change fails in seconds, not after a 10-minute plan.

- `fmt` and `validate` need no cloud access and find typos and syntax errors.
- Infracost and SonarQube stop changes that are too expensive or break code rules.
- `terraform plan` talks to Azure and reads state, so it runs only after the code is clean.
- A human reviews the plan and cost, and only then does `apply` change real resources.

## Repository layout

```text
.
├── terraform/
│   ├── main.tf
│   ├── variables.tf
│   ├── providers.tf
│   └── backend.tf
└── azure-pipelines.yml
```

`terraform/backend.tf`:

```hcl
terraform {
  backend "azurerm" {}
}
```

The backend values are passed by the pipeline, so the same code can point at a different state file per environment.

## Steps

### 1. Run the checks locally first

```bash
cd terraform
terraform init -backend=false
terraform validate
terraform fmt -check -recursive
```

`terraform fmt -check` returns exit code 3 and lists the files if any file is not formatted. Run `terraform fmt -recursive` to fix them.

### 2. Try Infracost locally

```bash
curl -fsSL https://raw.githubusercontent.com/infracost/infracost/master/scripts/install.sh | sh
infracost auth login            # or: export INFRACOST_API_KEY=...
infracost breakdown --path .
```

Expected: a table of resources with a monthly cost per resource and a total. Usage-based resources (for example storage transactions) show as "Monthly cost depends on usage".

### 3. Add a SonarQube project file (optional)

You can set the SonarQube properties in the pipeline task, or keep them in `sonar-project.properties` at the repository root:

```properties
sonar.projectKey=terraform-infra
sonar.projectName=terraform-infra
sonar.sources=terraform
sonar.qualitygate.wait=true
sonar.qualitygate.timeout=300
```

SonarQube has IaC rules for Terraform (for example public network access, missing encryption, or open firewall rules). Which rules are available depends on your SonarQube edition and version, so check your edition before relying on them.

### 4. Create the pipeline

`azure-pipelines.yml`:

```yaml
trigger:
  branches:
    include:
      - main
  paths:
    include:
      - terraform

pool:
  vmImage: ubuntu-latest

variables:
  azureSubscription: azure-wif-connection
  tfVersion: '1.9.8'
  tfDir: $(System.DefaultWorkingDirectory)/terraform
  stateKey: dev.tfstate
  # INFRACOST_API_KEY is a secret variable set in the pipeline UI or a variable group

stages:
  # ---------- Stage 1: fast checks ----------
  - stage: Validate
    jobs:
      - job: Validate
        steps:
          - task: TerraformInstaller@1
            inputs:
              terraformVersion: $(tfVersion)
          - task: TerraformTask@5
            displayName: Terraform init
            inputs:
              provider: azurerm
              command: init
              workingDirectory: $(tfDir)
              backendServiceArm: $(azureSubscription)
              backendAzureRmResourceGroupName: tfstate-rg
              backendAzureRmStorageAccountName: companytfstate
              backendAzureRmContainerName: tfstate
              backendAzureRmKey: $(stateKey)
          - task: TerraformTask@5
            displayName: Terraform validate
            inputs:
              provider: azurerm
              command: validate
              workingDirectory: $(tfDir)
          - script: terraform fmt -check -recursive
            displayName: Terraform fmt check
            workingDirectory: $(tfDir)

  # ---------- Stage 2: cost estimate on the code ----------
  - stage: Cost
    dependsOn: Validate
    jobs:
      - job: Infracost
        steps:
          - script: |
              curl -fsSL https://raw.githubusercontent.com/infracost/infracost/master/scripts/install.sh | sh
              infracost breakdown --path $(tfDir) --format table
            displayName: Infracost breakdown (code)
            env:
              INFRACOST_API_KEY: $(INFRACOST_API_KEY)

  # ---------- Stage 3: static analysis + quality gate ----------
  - stage: CodeQuality
    dependsOn: Validate
    jobs:
      - job: SonarQube
        steps:
          - task: SonarQubePrepare@7
            inputs:
              SonarQube: sonarqube-connection
              scannerMode: cli
              configMode: manual
              cliProjectKey: terraform-infra
              cliProjectName: terraform-infra
              cliSources: terraform
              extraProperties: |
                sonar.qualitygate.wait=true
                sonar.qualitygate.timeout=300
          - task: SonarQubeAnalyze@7
            displayName: Run SonarQube analysis
          - task: SonarQubePublish@7
            inputs:
              pollingTimeoutSec: '300'

  # ---------- Stage 4: plan ----------
  - stage: Plan
    dependsOn:
      - Cost
      - CodeQuality
    jobs:
      - job: Plan
        steps:
          - task: TerraformInstaller@1
            inputs:
              terraformVersion: $(tfVersion)
          - task: TerraformTask@5
            displayName: Terraform init
            inputs:
              provider: azurerm
              command: init
              workingDirectory: $(tfDir)
              backendServiceArm: $(azureSubscription)
              backendAzureRmResourceGroupName: tfstate-rg
              backendAzureRmStorageAccountName: companytfstate
              backendAzureRmContainerName: tfstate
              backendAzureRmKey: $(stateKey)
          - task: TerraformTask@5
            displayName: Terraform plan
            inputs:
              provider: azurerm
              command: plan
              workingDirectory: $(tfDir)
              environmentServiceNameAzureRM: $(azureSubscription)
              commandOptions: '-out=tfplan -input=false'
          - script: |
              terraform show -json tfplan > plan.json
              curl -fsSL https://raw.githubusercontent.com/infracost/infracost/master/scripts/install.sh | sh
              infracost breakdown --path plan.json --format table
              infracost diff --path plan.json --format json --out-file infracost-diff.json
              infracost output --path infracost-diff.json --format diff
            displayName: Infracost on the plan
            workingDirectory: $(tfDir)
            env:
              INFRACOST_API_KEY: $(INFRACOST_API_KEY)
          - script: |
              DIFF=$(jq -r '.diffTotalMonthlyCost // "0"' infracost-diff.json)
              echo "Monthly cost change: $DIFF USD"
              if awk -v d="$DIFF" 'BEGIN { exit !(d > 100) }'; then
                echo "##vso[task.logissue type=warning]Cost increase is over 100 USD per month. Check before approving."
              fi
            displayName: Cost threshold check
            workingDirectory: $(tfDir)
          - publish: $(tfDir)/tfplan
            artifact: tfplan
            displayName: Publish plan artifact

  # ---------- Stage 5: manual approval ----------
  - stage: Approve
    dependsOn: Plan
    jobs:
      - job: WaitForApproval
        pool: server                     # agentless job
        timeoutInMinutes: 1440           # job timeout must be longer than the task timeout
        steps:
          - task: ManualValidation@1
            timeoutInMinutes: 1380
            inputs:
              notifyUsers: |
                platform-team@example.com
              approvers: platform-team@example.com
              instructions: 'Review the Terraform plan and the Infracost output in the Plan stage, then approve or reject.'
              onTimeout: reject

  # ---------- Stage 6: apply ----------
  - stage: Apply
    dependsOn: Approve
    condition: and(succeeded(), eq(variables['Build.SourceBranch'], 'refs/heads/main'))
    jobs:
      - deployment: Apply
        environment: terraform-dev       # optional: add approvals and checks here too
        strategy:
          runOnce:
            deploy:
              steps:
                - checkout: self         # deployment jobs do not check out code by default
                - download: current
                  artifact: tfplan
                - script: cp $(Pipeline.Workspace)/tfplan/tfplan $(tfDir)/tfplan
                  displayName: Copy plan into the Terraform folder
                - task: TerraformInstaller@1
                  inputs:
                    terraformVersion: $(tfVersion)
                - task: TerraformTask@5
                  displayName: Terraform init
                  inputs:
                    provider: azurerm
                    command: init
                    workingDirectory: $(tfDir)
                    backendServiceArm: $(azureSubscription)
                    backendAzureRmResourceGroupName: tfstate-rg
                    backendAzureRmStorageAccountName: companytfstate
                    backendAzureRmContainerName: tfstate
                    backendAzureRmKey: $(stateKey)
                - task: TerraformTask@5
                  displayName: Terraform apply (saved plan)
                  inputs:
                    provider: azurerm
                    command: apply
                    workingDirectory: $(tfDir)
                    environmentServiceNameAzureRM: $(azureSubscription)
                    commandOptions: 'tfplan'
```

Notes:

- `INFRACOST_API_KEY` must be a secret variable. Secret variables are not passed to scripts automatically, so map them with `env:`.
- `Cost` and `CodeQuality` both depend only on `Validate`, so they run in parallel.
- The saved plan is applied as-is. If the state changed after the plan (someone else applied), Terraform rejects the plan as stale, and you re-run the pipeline.
- The Apply stage re-runs `terraform init`, because each job runs on a fresh agent with no `.terraform` folder.

### 5. Choose how to approve

You have two options. You can use one or both.

| Option | Where it is configured | Good for |
| --- | --- | --- |
| `ManualValidation@1` in an agentless job | In the YAML | A pause with instructions, inside one pipeline run |
| Approvals and checks on an environment | Pipelines > Environments > `terraform-dev` > Approvals and checks | Central control, used by every pipeline that deploys to that environment |

To add an environment approval: open **Pipelines > Environments**, create `terraform-dev`, open **Approvals and checks**, and add **Approvals** with the approver group. The deployment job then waits before it starts.

### 6. Optional: post the cost to the pull request

For pull request builds, Infracost can post the cost difference as a comment:

```bash
infracost comment azure-repos \
  --path infracost-diff.json \
  --azure-access-token "$(System.AccessToken)" \
  --repo-url "$(Build.Repository.Uri)" \
  --pull-request "$(System.PullRequest.PullRequestId)" \
  --behavior update
```

The build service account needs **Contribute to pull requests** on the repository. Reviewers then see the cost change next to the code change.

### 7. Verify

Push a small change, for example a new storage account in `main.tf`, and watch the run.

Expected:

- `Validate` passes in under a minute. If a file is not formatted, the `fmt` step fails with the file name.
- `Cost` prints a table with the new resource and its monthly cost.
- `CodeQuality` passes, or fails with "QUALITY GATE STATUS: FAILED" if the gate fails.
- `Plan` shows `Plan: 1 to add, 0 to change, 0 to destroy.` and the Infracost diff shows the monthly increase.
- `Approve` waits with the status "Waiting for review".
- After approval, `Apply` shows `Apply complete! Resources: 1 added, 0 changed, 0 destroyed.`

Check the resource:

```bash
az resource list -g rg-dev -o table
```

## Important points

- Apply the saved plan file, not a fresh `terraform apply`. Otherwise the reviewer approved one plan and a different one runs.
- The plan file can contain sensitive values. Keep pipeline artifacts private, and keep retention short.
- `sonar.qualitygate.wait=true` makes the analysis step fail when the quality gate fails. Without it, the pipeline passes even with a red gate.
- For `ManualValidation@1`, the job must be agentless (`pool: server`), and the job timeout must be longer than the task timeout, or the job is cancelled first.
- Pin the Terraform and provider versions, so the plan and apply use the same versions.
- Use workload identity federation for the service connection, so there is no client secret to rotate.

## Common problems

| Problem | Likely cause | Fix |
| --- | --- | --- |
| `fmt` step fails | Files not formatted | Run `terraform fmt -recursive` locally and commit |
| Infracost: "No INFRACOST_API_KEY environment variable is set" | Secret variable not mapped to the script | Add `env: INFRACOST_API_KEY: $(INFRACOST_API_KEY)` |
| SonarQube finds no Terraform files | `sonar.sources` points at the wrong folder | Set `cliSources: terraform` |
| Quality gate times out | Server slow, or timeout too short | Increase `sonar.qualitygate.timeout` and `pollingTimeoutSec` |
| `ManualValidation` fails at once | Task is in an agent job | Put it in a job with `pool: server` |
| Apply fails with "Saved plan is stale" | State changed after the plan | Re-run the pipeline to create a new plan |
| Apply fails with "file not found: tfplan" | No checkout or artifact not copied | Add `checkout: self` and copy the downloaded plan into the Terraform folder |
| "Error acquiring the state lock" | Another run holds the lock | Wait, or after checking, run `terraform force-unlock <lock-id>` |

## Interview questions

<details><summary>Q1. In what order do you run Terraform checks in a pipeline, and why?</summary>

Cheapest first. `fmt` and `validate` take seconds and need no cloud access. Then the cost estimate and static analysis. Then `terraform plan`, which reads state and calls Azure. Then a manual approval, and only then `apply`. A broken change fails early and cheaply, and the expensive and risky steps only run on clean code.

</details>

<details><summary>Q2. Why do you save the plan with <code>-out</code> and apply that file?</summary>

The approver reviews one specific plan. If the apply stage runs a new plan, it might include changes made after the review. Applying the saved file guarantees that exactly the reviewed changes are made. If the state changed in the meantime, Terraform refuses the stale plan, which is also safe.

</details>

<details><summary>Q3. How does Infracost fit into the pipeline?</summary>

Infracost reads the Terraform code or the plan JSON (`terraform show -json tfplan`) and uses a pricing API to show the monthly cost of each resource. `infracost diff` shows the change compared with the current state. I show it to the approver, post it on the pull request, and can warn or fail the build if the increase is over a threshold.

</details>

<details><summary>Q4. What does a SonarQube quality gate do for Terraform code?</summary>

SonarQube analyses the Terraform files with IaC rules, such as storage without encryption or a firewall open to the internet. The quality gate is a set of conditions on the results. With <code>sonar.qualitygate.wait=true</code>, the pipeline waits for the gate result and fails if the gate fails, so bad code cannot reach the plan stage.

</details>

<details><summary>Q5. What is the difference between <code>ManualValidation@1</code> and environment approvals?</summary>

`ManualValidation@1` is a task in the YAML. It runs in an agentless job and pauses the run until someone approves or rejects. Environment approvals are configured on the environment in Azure DevOps, not in the YAML, and apply to every pipeline that deploys to that environment. Environment checks are harder to bypass, because a developer cannot remove them by editing the YAML.

</details>
