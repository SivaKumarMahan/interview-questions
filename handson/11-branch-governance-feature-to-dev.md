# Hands-on 11: Enforce Branch Rules in Azure DevOps (Only feature/* Can Merge into dev)

> Add a branch validation stage to an Azure DevOps pipeline so that only `feature/*` branches can merge into `dev`, make it a required check with branch policies, and run Terraform only after the validation passes.

**Time:** about 45 minutes. **Level:** Intermediate.

## What you practise

- Reading predefined variables: `Build.Reason`, `Build.SourceBranch`, `System.PullRequest.SourceBranch`, `System.PullRequest.TargetBranch`
- Failing a pipeline with a clear error using `##vso[task.logissue]`
- Making the pipeline a **required** build validation on the `dev` branch
- Branch policies and branch security that stop direct pushes and bypasses
- Running Terraform stages only after the branch check passes
- The same idea in GitHub with rulesets and a required status check

## Prerequisites

| Item | Purpose |
| --- | --- |
| Azure DevOps project with an Azure Repos Git repo | Code, branches, and pipeline |
| Branches `main` and `dev` | `dev` is the protected integration branch |
| Project Administrator rights (or Edit policies permission) | Set branch policies and branch security |
| Terraform code in `terraform/` and an Azure Resource Manager service connection | Infrastructure stages that run after validation |
| Environment `infra-dev` with an approval check | Approval before `terraform apply` |

## Flow

```text
Developer opens a PR into dev
            |
            v
Branch policy on dev -> Build validation (Required) -> queues the pipeline
            |
            v
Stage: ValidateBranch
  Build.Reason == PullRequest ?
     |
     +-- yes: target == refs/heads/dev ?
     |          |
     |          +-- source matches refs/heads/feature/*  -> PASS
     |          |
     |          '-- any other source branch              -> FAIL
     |               "Only feature/* branches are allowed to merge into dev"
     |               pipeline fails -> PR cannot complete -> dev stays clean
     |
     '-- no (IndividualCI / BatchCI / Manual): log the run, rely on branch policies
            |
            v (only if ValidateBranch succeeded)
Stage: TerraformPlan   (PR runs and dev runs)
            |
            v (only on dev after merge, not on PRs)
Stage: TerraformApply  (approval on environment infra-dev)
```

| Source branch | Target branch | Result |
| --- | --- | --- |
| `feature/login-page` | `dev` | Allowed |
| `bugfix/typo` | `dev` | Blocked |
| `main` | `dev` | Blocked |
| `hotfix/urgent-fix` | `dev` | Blocked (unless you add it to the allow-list, see step 6) |
| any branch | `main` | Not checked by this rule |

## Steps

### 1. Understand the variables

| Variable | Example in a PR build | Example in a CI build on dev |
| --- | --- | --- |
| `Build.Reason` | `PullRequest` | `IndividualCI`, `BatchCI`, or `Manual` |
| `Build.SourceBranch` | `refs/pull/42/merge` | `refs/heads/dev` |
| `System.PullRequest.SourceBranch` | `refs/heads/feature/login-page` | not set |
| `System.PullRequest.TargetBranch` | `refs/heads/dev` | not set |

Key facts:

- The `System.PullRequest.*` variables exist **only** when `Build.Reason` is `PullRequest`.
- In a PR build, `Build.SourceBranch` is the temporary merge ref (`refs/pull/<id>/merge`), not the feature branch.
- In a CI build after a merge, `Build.SourceBranch` is `refs/heads/dev`. The pipeline **cannot** tell from it which branch was merged. That is why direct pushes must be stopped by branch policies, not by the pipeline.
- All branch values include the `refs/heads/` prefix. Compare full refs.

### 2. Write the pipeline

`azure-pipelines.yml`:

```yaml
trigger:
  branches:
    include:
      - dev
      - main

# For Azure Repos, this pr: section is ignored.
# PR builds are started by the Build validation branch policy (step 3).

pool:
  vmImage: ubuntu-latest

variables:
  azureSubscription: azure-wif-connection
  tfWorkingDir: terraform

stages:
  - stage: ValidateBranch
    displayName: Validate branch rules
    jobs:
      - job: Validate
        steps:
          - checkout: none
          - bash: |
              set -euo pipefail

              echo "Build.Reason       : $BUILD_REASON"
              echo "Build.SourceBranch : $BUILD_SOURCE_BRANCH"

              if [ "$BUILD_REASON" = "PullRequest" ]; then
                echo "PR source branch   : $PR_SOURCE_BRANCH"
                echo "PR target branch   : $PR_TARGET_BRANCH"

                if [ "$PR_TARGET_BRANCH" = "refs/heads/dev" ]; then
                  case "$PR_SOURCE_BRANCH" in
                    refs/heads/feature/*)
                      echo "Allowed: $PR_SOURCE_BRANCH -> dev"
                      ;;
                    *)
                      echo "##vso[task.logissue type=error]Only feature/* branches are allowed to merge into dev (source: $PR_SOURCE_BRANCH)"
                      exit 1
                      ;;
                  esac
                else
                  echo "Target is not dev. No source-branch rule for this target."
                fi
              else
                # IndividualCI, BatchCI, Manual, Schedule, ...
                # Build.SourceBranch is the branch itself (for example refs/heads/dev).
                # The merged source branch is unknown here, so branch policies
                # must block direct pushes to dev.
                echo "Not a PR build. Branch policies protect dev from direct pushes."
              fi
            displayName: Check source and target branch
            env:
              BUILD_REASON: $(Build.Reason)
              BUILD_SOURCE_BRANCH: $(Build.SourceBranch)
              PR_SOURCE_BRANCH: $(System.PullRequest.SourceBranch)
              PR_TARGET_BRANCH: $(System.PullRequest.TargetBranch)

  - stage: TerraformPlan
    displayName: Terraform plan
    dependsOn: ValidateBranch
    condition: succeeded()
    jobs:
      - job: Plan
        steps:
          - task: TerraformInstaller@1
            inputs:
              terraformVersion: '1.9.8'
          - task: TerraformTask@5
            displayName: Terraform init
            inputs:
              provider: azurerm
              command: init
              workingDirectory: $(tfWorkingDir)
              backendServiceArm: $(azureSubscription)
              backendAzureRmResourceGroupName: tfstate-rg
              backendAzureRmStorageAccountName: companytfstate
              backendAzureRmContainerName: tfstate
              backendAzureRmKey: dev.tfstate
          - task: TerraformTask@5
            displayName: Terraform validate
            inputs:
              provider: azurerm
              command: validate
              workingDirectory: $(tfWorkingDir)
          - task: TerraformTask@5
            displayName: Terraform plan
            inputs:
              provider: azurerm
              command: plan
              workingDirectory: $(tfWorkingDir)
              environmentServiceNameAzureRM: $(azureSubscription)
              commandOptions: '-out=tfplan -input=false'
          - task: PublishPipelineArtifact@1
            inputs:
              targetPath: $(tfWorkingDir)/tfplan
              artifact: tfplan

  - stage: TerraformApply
    displayName: Terraform apply (dev)
    dependsOn: TerraformPlan
    condition: |
      and(
        succeeded(),
        ne(variables['Build.Reason'], 'PullRequest'),
        eq(variables['Build.SourceBranch'], 'refs/heads/dev')
      )
    jobs:
      - deployment: Apply
        environment: infra-dev          # approval check configured here
        strategy:
          runOnce:
            deploy:
              steps:
                - checkout: self
                - task: TerraformInstaller@1
                  inputs:
                    terraformVersion: '1.9.8'
                - task: TerraformTask@5
                  displayName: Terraform init
                  inputs:
                    provider: azurerm
                    command: init
                    workingDirectory: $(tfWorkingDir)
                    backendServiceArm: $(azureSubscription)
                    backendAzureRmResourceGroupName: tfstate-rg
                    backendAzureRmStorageAccountName: companytfstate
                    backendAzureRmContainerName: tfstate
                    backendAzureRmKey: dev.tfstate
                - bash: cp $(Pipeline.Workspace)/tfplan/tfplan $(tfWorkingDir)/tfplan
                  displayName: Use the reviewed plan
                - task: TerraformTask@5
                  displayName: Terraform apply
                  inputs:
                    provider: azurerm
                    command: apply
                    workingDirectory: $(tfWorkingDir)
                    environmentServiceNameAzureRM: $(azureSubscription)
                    commandOptions: '-input=false tfplan'
```

Notes:

- The variables are passed through `env:`. This keeps the script simple and avoids quoting problems from inline `$(...)` macros.
- `##vso[task.logissue type=error]` shows the message as a red error in the run summary and on the PR.
- `exit 1` fails the stage. `TerraformPlan` has `dependsOn: ValidateBranch` and `condition: succeeded()`, so it does not run.
- `TerraformApply` runs only after a merge (a CI run on `dev`), never on a PR build. A PR only gets a plan.
- In a deployment job, the `current` pipeline artifacts (here `tfplan`) are downloaded to `$(Pipeline.Workspace)` automatically.

### 3. Make the pipeline a required check on dev

A failing pipeline does **not** block a merge on its own. It blocks the merge only when it is a **required** build validation.

1. Go to **Repos -> Branches**.
2. On `dev`, select **...** -> **Branch policies**.
3. Under **Build validation**, select **+**:
   - Build pipeline: this pipeline
   - Trigger: **Automatic**
   - Policy requirement: **Required**
   - Build expiration: **Immediately when dev is updated**
   - Display name: `Branch rules + Terraform plan`
4. Save.

Now every PR into `dev` queues the pipeline with `Build.Reason = PullRequest`. If the run fails, the **Complete** button is blocked.

For Azure Repos, the `pr:` section in YAML is ignored. PR builds come only from this build validation policy.

### 4. Add the other branch policies on dev

On the same **Branch policies** page:

| Policy | Setting | Why |
| --- | --- | --- |
| Require a minimum number of reviewers | 1 or 2; do not allow requestors to approve their own changes | A human reviews every change |
| Check for linked work items | Required | Every change is traceable |
| Check for comment resolution | Required | Review comments are closed before merge |
| Limit merge types | For example, squash merge only | Clean history on `dev` |
| Build validation | Required (step 3) | Branch rule and Terraform plan must pass |

When a branch has required policies, changes must go through a pull request. A plain `git push` to `dev` is rejected.

### 5. Lock down branch security

Policies can be bypassed by users with bypass permissions. Remove them for most people.

1. **Repos -> Branches -> dev -> ... -> Branch security**.
2. For **Contributors** (and other normal groups), set to **Deny**:
   - **Bypass policies when pushing**
   - **Bypass policies when completing pull requests**
   - **Force push (rewrite history, delete branches and lock branches)**
3. Give bypass only to a small break-glass group, and audit its use.

Azure DevOps branch policies cannot restrict **which source branch** may open a PR into `dev`. The branch policies make sure a PR and a passing build are required. The pipeline check adds the source-branch rule. You need both.

### 6. Allow hotfix branches (optional)

Extend the allow-list in the `case` statement:

```bash
case "$PR_SOURCE_BRANCH" in
  refs/heads/feature/*|refs/heads/hotfix/*)
    echo "Allowed: $PR_SOURCE_BRANCH -> dev"
    ;;
  *)
    echo "##vso[task.logissue type=error]Only feature/* or hotfix/* branches are allowed to merge into dev (source: $PR_SOURCE_BRANCH)"
    exit 1
    ;;
esac
```

To keep the rule in one place for many repos, put the validation stage in a YAML template in a shared repo and reference it with `extends` or `template`.

### 7. Verify the rules

Create test branches and open PRs into `dev`:

```bash
git checkout dev && git pull
git checkout -b feature/test-allowed
echo "# allowed" >> README.md
git commit -am "Test allowed branch" && git push -u origin feature/test-allowed

git checkout dev
git checkout -b bugfix/test-blocked
echo "# blocked" >> README.md
git commit -am "Test blocked branch" && git push -u origin bugfix/test-blocked

# try a direct push to dev
git checkout dev
echo "# direct" >> README.md
git commit -am "Direct push"
git push origin dev
```

Open two PRs in Azure Repos: `feature/test-allowed -> dev` and `bugfix/test-blocked -> dev`.

Expected results:

| Test | Expected result |
| --- | --- |
| PR from `feature/test-allowed` | `ValidateBranch` passes, `TerraformPlan` runs, PR can be completed after review |
| PR from `bugfix/test-blocked` | `ValidateBranch` fails with "Only feature/* branches are allowed to merge into dev", later stages are skipped, PR cannot be completed |
| Direct `git push origin dev` | Rejected by the server with a message that the branch requires a pull request |
| After the feature PR is merged | CI run on `dev` passes validation, plans, and waits for approval on `infra-dev` before apply |

Reset the local `dev` branch after the rejected push: `git reset --hard origin/dev`.

### 8. GitHub equivalent

In GitHub, use a **ruleset** (or classic branch protection) on `dev`:

- Require a pull request before merging, with required approvals
- Require status checks to pass, and add the `branch-rules` check below
- Block force pushes, and limit the bypass list

`.github/workflows/branch-rules.yml`:

```yaml
name: branch-rules
on:
  pull_request:
    branches: [dev]

jobs:
  branch-rules:
    runs-on: ubuntu-latest
    steps:
      - name: Only feature/* can merge into dev
        env:
          HEAD_REF: ${{ github.head_ref }}
        run: |
          case "$HEAD_REF" in
            feature/*) echo "Allowed: $HEAD_REF -> dev" ;;
            *) echo "::error::Only feature/* branches are allowed to merge into dev"; exit 1 ;;
          esac
```

`github.head_ref` is the PR source branch **without** the `refs/heads/` prefix.

## Important points

- The pipeline check only blocks a merge when it is a **Required** build validation on `dev`.
- For Azure Repos, PR builds come from the build validation policy. The YAML `pr:` trigger is ignored.
- `System.PullRequest.SourceBranch` and `TargetBranch` exist only when `Build.Reason` is `PullRequest`.
- In a CI run on `dev`, the pipeline cannot know which branch was merged. Branch policies and branch security stop direct pushes.
- Azure DevOps branch policies cannot limit source branch names. The pipeline check fills this gap.
- Run `terraform plan` on PRs, and `terraform apply` only on `dev` after merge, behind an approval.
- Deny bypass permissions for normal users, or the rules can be skipped.

## Common problems

| Problem | Likely cause | Fix |
| --- | --- | --- |
| PR variables are empty or show the text `$(System.PullRequest.SourceBranch)` | The run is not a PR build (CI or manual), so the variables do not exist | Check `Build.Reason` first; only read PR variables when it is `PullRequest` |
| Every PR fails, even from `feature/*` | Comparing `feature/*` with `refs/heads/feature/...`, or using `Build.SourceBranch` (`refs/pull/<id>/merge`) | Compare `System.PullRequest.SourceBranch` with `refs/heads/feature/*` |
| Pipeline fails but the PR can still be completed | Build validation is **Optional**, or not added at all | Set Policy requirement to **Required** |
| PR build never starts | `pr:` trigger used instead of a build validation policy | Add the pipeline under **Build validation** on `dev` |
| A user merged a blocked PR anyway | User has **Bypass policies when completing pull requests** | Deny the bypass permissions for that group |
| Direct pushes to `dev` still work | No required policies on `dev`, or the user has bypass when pushing | Add required policies and deny bypass when pushing |
| Urgent hotfix cannot reach `dev` | Allow-list has only `feature/*` | Add `refs/heads/hotfix/*` to the `case` statement |
| `terraform apply` runs on a PR | Apply stage condition does not check `Build.Reason` | Add `ne(variables['Build.Reason'], 'PullRequest')` to the condition |

## Clean up

```bash
git push origin --delete feature/test-allowed bugfix/test-blocked
git branch -D feature/test-allowed bugfix/test-blocked
```

Abandon the test PRs in Azure Repos. Keep the branch policies if this is a real repo; remove them only in a lab project.

## Interview questions

<details><summary>Q1. How do you enforce a branching strategy such as "only feature branches can merge into dev"?</summary>

I combine branch policies and a pipeline check. On `dev`, I require pull requests with reviewers, linked work items, and a required build validation. The build validation pipeline has a first stage that reads `Build.Reason`, `System.PullRequest.SourceBranch`, and `System.PullRequest.TargetBranch`. If the target is `refs/heads/dev` and the source does not match `refs/heads/feature/*`, it logs an error and fails. Because the build is required, the PR cannot be completed. I also deny bypass permissions so nobody can skip the rules.

</details>

<details><summary>Q2. Why do you need both a pipeline check and branch policies?</summary>

They cover different gaps. Azure DevOps branch policies can require a PR, reviewers, and a passing build, but they cannot restrict the source branch name. The pipeline can check the source branch, but a failing pipeline does nothing unless the policy marks it as required, and the pipeline cannot see direct pushes. So the policy forces every change through a PR and a required build, and the pipeline enforces the naming rule inside that build.

</details>

<details><summary>Q3. Which predefined variables do you use, and what do they contain?</summary>

`Build.Reason` tells me why the run started, such as `PullRequest`, `IndividualCI`, or `Manual`. `System.PullRequest.SourceBranch` and `System.PullRequest.TargetBranch` give the PR branches as full refs, like `refs/heads/feature/login`, but only in PR builds. `Build.SourceBranch` is `refs/pull/42/merge` in a PR build and `refs/heads/dev` in a CI build on dev. I pass them to the script through `env:` and always compare full refs.

</details>

<details><summary>Q4. How do you allow hotfix branches without weakening the rule?</summary>

I add `refs/heads/hotfix/*` to the allow-list in the validation script, so the pattern stays explicit and reviewed in Git. The hotfix PR still needs reviewers, linked work items, and the required build. I do not give people bypass permissions for urgent fixes, because that skips every check. If many repos use the rule, I keep the validation in a shared YAML template so the allow-list is changed in one place.

</details>

<details><summary>Q5. How does this protect your Terraform environments?</summary>

Terraform stages depend on `ValidateBranch` with `condition: succeeded()`, so a branch that breaks the rule never reaches `terraform plan`. On a PR, the pipeline only runs a plan, so reviewers can see the change. `terraform apply` runs only on `dev` after the merge, never on a PR build, and it waits for approval on the `infra-dev` environment. This means only reviewed feature work, from a clean `dev` branch, can change the dev infrastructure, and the state is not changed by untested branches.

</details>
