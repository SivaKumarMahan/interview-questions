# CGI - Interview Questions

Real interview questions with simple, easy-to-read answers.

---

<details><summary>Q1. What is <code>pull_request_target</code> in GitHub Actions?</summary>

`pull_request_target` is a workflow trigger that runs when a pull request is opened or updated, like `pull_request`, but it runs **in the context of the base branch** (the branch the PR wants to merge into), not the PR's code.

| | `pull_request` | `pull_request_target` |
| --- | --- | --- |
| Workflow file used | From the **PR's merge commit** | From the **base branch** |
| Code checked out by default | The PR's merge commit | The **base branch** |
| Secrets for PRs from forks | **No** | **Yes** |
| `GITHUB_TOKEN` for PRs from forks | Read-only | **Read/write** |
| Typical use | Build and test the PR | Label, comment on, or triage PRs from forks |

### Why it exists

PRs from forks run `pull_request` with no secrets and a read-only token, which is safe but means the workflow cannot comment on or label the PR. `pull_request_target` gives the workflow that access because it only runs **trusted code from the base branch**.

### The big risk ("pwn request")

If a `pull_request_target` workflow **checks out the PR's code and runs it** (for example `npm install` or a build script), an attacker's fork can steal your secrets or push to your repo with the write token.

```yaml
# DANGEROUS - do not do this
on: pull_request_target
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          ref: ${{ github.event.pull_request.head.sha }}   # untrusted fork code
      - run: npm install && npm test                        # runs it with secrets
```

### Safe example: label PRs, run no PR code

```yaml
on:
  pull_request_target:
    types: [opened, synchronize]

permissions:
  contents: read
  pull-requests: write

jobs:
  label:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/labeler@v5        # reads changed file paths only
```

### Good practices

- Never check out and execute the PR's code in `pull_request_target`.
- Set the smallest `permissions:` the job needs.
- Do not put PR titles or branch names straight into `run:` scripts (script injection); pass them through `env:`.
- To build untrusted code and then comment with secrets, use `pull_request` to build, then a separate `workflow_run` workflow to comment.

### Interview-ready answer

> "`pull_request_target` runs on pull request events but uses the workflow and code from the base branch, and it gets secrets and a write token even for PRs from forks. That makes it useful for labelling, commenting or triage on fork PRs. The risk is that if you check out and run the PR's code in it, an attacker can steal secrets. So I never execute PR code there, I keep permissions minimal, and for building fork PRs I use the normal `pull_request` trigger."

</details>

<details><summary>Q2. What are Git submodules?</summary>

A **submodule** is another Git repository placed inside your repository at a fixed path. Your repo does not store the submodule's files; it stores **a pointer to one specific commit** of the other repo.

Example: several services share a `common-terraform-modules` repo, and each service includes it as a submodule.

### Main commands

```bash
# Add a submodule
git submodule add https://github.com/org/shared-lib.git libs/shared-lib
git commit -m "Add shared-lib submodule"     # commits .gitmodules and the pinned commit

# Clone a repo together with its submodules
git clone --recurse-submodules https://github.com/org/app.git

# Already cloned without them
git submodule update --init --recursive

# Move the submodule to the latest commit of its branch
git submodule update --remote libs/shared-lib
git add libs/shared-lib
git commit -m "Bump shared-lib"
```

The `.gitmodules` file records each submodule's path and URL:

```ini
[submodule "libs/shared-lib"]
    path = libs/shared-lib
    url = https://github.com/org/shared-lib.git
```

### In CI/CD

```yaml
# GitHub Actions
- uses: actions/checkout@v4
  with:
    submodules: recursive
    token: ${{ secrets.SUBMODULE_PAT }}   # needed if the submodule is a private repo
```

```yaml
# Azure Pipelines
steps:
  - checkout: self
    submodules: recursive
```

### Pros and cons

| Pros | Cons |
| --- | --- |
| Reuse code from another repo | Easy to forget `--recurse-submodules`, leaving empty folders |
| Pinned to an exact commit, so builds are repeatable | Updates are manual: you must bump and commit the pointer |
| Each repo keeps its own history and permissions | CI needs access to every submodule repo |

Alternatives: a **package** (npm, NuGet, a Terraform registry module), a Git **subtree**, or a monorepo.

### Interview-ready answer

> "A submodule is a separate Git repo embedded in my repo at a path, pinned to a specific commit. The URL and path are in `.gitmodules`. I clone with `--recurse-submodules` or run `git submodule update --init --recursive`, and in pipelines I enable submodule checkout and give a token if the repo is private. It keeps shared code versioned and repeatable, but updates are manual, so for shared libraries I often prefer publishing a package instead."

</details>

<details><summary>Q3. What is Git LFS?</summary>

**Git LFS (Large File Storage)** is a Git extension for **large binary files** such as images, videos, datasets, models and installers.

Git stores every version of every file in history, so large binaries make the repo slow to clone and can hit size limits. With LFS:

- The repo stores a small **pointer file** (a few lines of text) instead of the binary.
- The real file is stored on an **LFS server** (GitHub, Azure Repos and GitLab all provide one).
- The file is downloaded when you check out a branch that needs it.

### Commands

```bash
git lfs install                     # once per machine
git lfs track "*.psd"               # track a file type
git lfs track "models/**"
git add .gitattributes              # the tracking rules are stored here
git add design.psd
git commit -m "Add design file with LFS"
git push

git lfs ls-files                    # list files stored in LFS
git lfs pull                        # download LFS files for the current checkout
```

`.gitattributes` after tracking:

```text
*.psd filter=lfs diff=lfs merge=lfs -text
```

### Moving files that are already in history

```bash
git lfs migrate import --include="*.zip" --everything   # rewrites history; force-push needed
```

### In CI/CD

```yaml
# GitHub Actions
- uses: actions/checkout@v4
  with:
    lfs: true
```

```yaml
# Azure Pipelines
- checkout: self
  lfs: true
```

### Things to know

- LFS has **storage and bandwidth quotas** on hosted platforms; CI downloads count toward bandwidth.
- Without `git lfs install`, you get the pointer text instead of the real file.
- LFS is for binaries; it does not help with large text files that diff well.

### Interview-ready answer

> "Git LFS keeps large binary files out of normal Git history. The repo stores a small pointer, the real file sits on an LFS server, and it is downloaded on checkout. I run `git lfs install`, track patterns like `*.zip` with `git lfs track`, commit `.gitattributes`, and enable LFS in the pipeline checkout. For files already committed, `git lfs migrate` rewrites history. I keep an eye on storage and bandwidth quotas, because pipelines download LFS files too."

</details>

<details><summary>Q4. What is the difference between merge and rebase?</summary>

Both bring changes from one branch into another, but they shape history differently.

Starting point: `feature` branched from `main`, and both have new commits.

```text
          A---B  feature
         /
    C---D---E    main
```

**Merge** (`git checkout feature && git merge main`) creates a **merge commit** and keeps both histories:

```text
          A---B---M  feature
         /       /
    C---D---E----
```

**Rebase** (`git checkout feature && git rebase main`) **replays your commits on top of** `main`, creating new commits A' and B':

```text
                  A'--B'  feature
                 /
    C---D---E          main
```

| | Merge | Rebase |
| --- | --- | --- |
| History | Keeps the real history, with merge commits | Linear and clean |
| Rewrites commits | No | **Yes**: new commit IDs |
| Safe on shared branches | **Yes** | **No**: others' copies break |
| Conflicts | Resolved once, in the merge commit | May be resolved commit by commit |
| Shows when a branch was merged | Yes | No |

### Commands

```bash
# Merge
git checkout feature
git merge main

# Rebase
git checkout feature
git rebase main
# fix conflicts, then
git add .
git rebase --continue          # or git rebase --abort
git push --force-with-lease    # needed because the commits changed
```

### Golden rule

**Do not rebase commits that others have already pulled** (for example `main` or a shared branch). Rebase your own local or personal feature branch only.

### What I do

- Rebase my feature branch on `main` before opening or updating a PR, to keep it current and linear.
- Merge (through the PR) into `main`, often with squash.
- Use `git pull --rebase` to avoid unneeded merge commits when syncing.

### Interview-ready answer

> "Merge combines two branches with a merge commit and keeps the full history, without rewriting anything. Rebase replays my commits on top of the target branch, giving a linear history but creating new commit IDs. Because rebase rewrites history, I only rebase my own feature branches, then push with `--force-with-lease`, and I never rebase shared branches like main. Into main I merge through a pull request."

</details>

<details><summary>Q5. What is <code>git stash</code>?</summary>

`git stash` **saves your uncommitted changes** in a temporary area and returns your working directory to a clean state, so you can switch tasks and come back later.

**Typical scenario:** you are halfway through a feature, and you need to fix an urgent bug on another branch. You do not want to commit half-done work.

### Commands

```bash
git stash push -m "WIP: login form"   # save changes (tracked files only)
git stash -u                          # also include untracked (new) files
git stash list                        # stash@{0}: On feature: WIP: login form

git checkout hotfix-branch            # do the urgent work
git checkout feature                  # come back

git stash pop                         # re-apply the latest stash AND remove it
git stash apply stash@{1}             # re-apply a stash but KEEP it in the list
git stash show -p stash@{0}           # see what is inside
git stash drop stash@{0}              # delete one stash
git stash clear                       # delete all stashes
git stash branch new-branch stash@{0} # create a branch from a stash
git stash push -- src/app.js          # stash only some files
```

| | `pop` | `apply` |
| --- | --- | --- |
| Re-applies changes | Yes | Yes |
| Removes from stash list | Yes (if no conflict) | No |

### Things to know

- Stashes are **local only**; they are not pushed to the remote.
- By default untracked and ignored files are **not** stashed; use `-u` (or `-a` for ignored too).
- If `pop` hits a conflict, the stash is kept so you do not lose it.

### Interview-ready answer

> "`git stash` saves my uncommitted changes and gives me a clean working directory, so I can switch branches, for example to fix an urgent bug. I use `git stash push -m` with a message, `-u` to include new files, `git stash list` to see them, and `pop` or `apply` to bring them back. `pop` removes the stash, `apply` keeps it. Stashes are local only, so for anything long-lived I commit to a branch instead."

</details>

<details><summary>Q6. How do you handle vulnerability management in CI/CD?</summary>

The idea is **shift left**: find vulnerabilities as early as possible, block the serious ones automatically, and keep watching after deployment.

### What I scan, and where

| Stage | What it finds | Tools |
| --- | --- | --- |
| Developer machine / pre-commit | Secrets, lint, early issues | pre-commit hooks, IDE plugins (Snyk, SonarLint) |
| Push | Committed secrets | GitHub **secret scanning with push protection**, Gitleaks |
| Pull request | Code flaws (**SAST**) | **CodeQL**, SonarQube, Semgrep |
| Pull request | Vulnerable dependencies (**SCA**) | **Dependabot**, `dependency-review-action`, Snyk, OWASP Dependency-Check |
| Pull request | IaC misconfigurations | **Checkov**, tfsec/Trivy config, KICS |
| Build | Container image CVEs | **Trivy**, Grype, Microsoft Defender for Containers |
| Build | Inventory and trust | **SBOM** (Syft), image **signing** (Cosign / Notation) |
| After deploy to test | Running-app flaws (**DAST**) | OWASP ZAP |
| Runtime | New CVEs in what is already deployed | Defender for Cloud, registry rescans, Dependabot alerts |

### Example: fail the build on critical CVEs

```yaml
- name: Scan image
  uses: aquasecurity/trivy-action@0.28.0
  with:
    image-ref: myacr.azurecr.io/api:${{ github.sha }}
    severity: CRITICAL,HIGH
    exit-code: "1"              # fail the job
    ignore-unfixed: true        # don't block on CVEs with no fix yet

- name: Dependency review
  uses: actions/dependency-review-action@v4
  with:
    fail-on-severity: high
```

### The process around the tools

1. **Gate:** block merges or releases on **Critical/High** findings with a fix available (required status checks).
2. **Triage:** decide if a finding is real and reachable; record accepted risks with an expiry date (for example a `.trivyignore` entry with a ticket).
3. **Fix with SLAs:** for example Critical in 7 days, High in 30 days.
4. **Automate updates:** Dependabot or Renovate PRs for dependencies and base images.
5. **Report:** central view of findings, such as GitHub Security tab, Defender for Cloud or DefectDojo.
6. **Pipeline security itself:** least-privilege tokens, OIDC instead of stored secrets, pinned action versions, protected branches.

### Interview-ready answer

> "I build security into each stage of the pipeline. Secret scanning with push protection stops credentials early. On pull requests I run SAST with CodeQL, dependency scanning with Dependabot and dependency review, and IaC scanning with Checkov. At build time Trivy scans the container image, and I generate an SBOM and sign the image. Critical and high findings with a fix fail the pipeline through required checks. Findings are triaged, exceptions are documented with an expiry, and we fix within agreed SLAs. After deployment, Defender for Cloud keeps scanning for new CVEs."

</details>

<details><summary>Q7. What is the difference between GitHub-hosted and self-hosted runners?</summary>

A **runner** is the machine that runs a GitHub Actions job.

| | GitHub-hosted | Self-hosted |
| --- | --- | --- |
| Who manages it | **GitHub**: patching, images, scaling | **You**: OS, tools, updates, scaling |
| Environment | **Fresh VM for every job**, then destroyed | Usually **persistent** (unless you make it ephemeral) |
| Pre-installed tools | Many (Docker, Node, Python, Azure CLI, …) | Only what you install |
| Network access | Public internet only | Can reach **private networks** (private AKS, databases, on-prem) |
| Hardware | Standard sizes; larger runners and GPU cost extra | Any hardware you choose |
| Cost | Per-minute billing beyond free minutes (free for public repos) | No GitHub minute charges; you pay for the infrastructure |
| Caching | Lost after each job (use `actions/cache`) | Local caches persist, so builds can be faster |
| Security | Isolated and clean every run | You must harden it; leftover files can leak between jobs |
| Setup | None: `runs-on: ubuntu-latest` | Install the runner agent, register it, add labels |

### Using them

```yaml
jobs:
  build:
    runs-on: ubuntu-latest                       # GitHub-hosted

  deploy:
    runs-on: [self-hosted, linux, azure-vnet]    # self-hosted, chosen by labels
```

### When I choose self-hosted

- The job must reach **private resources**: a private AKS API server, a database or Key Vault with private endpoints, on-prem systems.
- **Special hardware or software**: GPUs, licensed tools, a specific OS.
- **Compliance**: builds must run inside our network or region.
- **Cost** at very high build volume.

### Running self-hosted runners well

- Use **Actions Runner Controller (ARC)** on Kubernetes, or VM scale sets, for **ephemeral** runners that autoscale and are destroyed after each job.
- Put them in **runner groups** limited to specific repositories.
- **Do not use self-hosted runners with public repositories**: anyone can open a PR that runs code on your machine.
- Keep the OS and runner version patched; give them a managed identity with least privilege.

### Interview-ready answer

> "GitHub-hosted runners are managed by GitHub. Each job gets a fresh, clean VM with common tools, and you pay per minute. Self-hosted runners are machines I manage. I use them when jobs need to reach private resources like a private AKS cluster or private endpoints, or need special hardware. The trade-off is that I own patching, security and scaling. So I run them as ephemeral, autoscaling runners with Actions Runner Controller, restrict them with runner groups, and never attach them to public repositories."

</details>

<details><summary>Q8. What is the difference between a squash commit and a merge commit?</summary>

These are two ways to complete a pull request.

Feature branch with 4 commits: `wip`, `fix typo`, `add tests`, `address review`.

**Merge commit** keeps all 4 commits and adds a merge commit:

```text
main:  ---o---o-----------M
               \         /
feature:        1--2--3--4
```

**Squash merge** combines all 4 commits into **one new commit** on `main`:

```text
main:  ---o---o---S        (S = all changes from 1-4)
```

| | Merge commit | Squash merge |
| --- | --- | --- |
| Commits added to main | All feature commits + 1 merge commit | **1 commit** |
| History | Full detail, non-linear | **Clean and linear**, one commit per PR |
| Keeps individual commits | Yes | No (they stay only on the deleted branch/PR) |
| Revert a whole feature | Revert the merge commit (`git revert -m 1 <merge>`) | Revert one commit: easy |
| `git bisect` | Can land on small "wip" commits | Each commit is a whole, working change |
| Branch afterwards | Git knows it is merged | Git does not see it as merged; delete the branch, don't keep using it |

There is also a third option, **rebase and merge**: each feature commit is replayed onto `main` with no merge commit (linear history, all commits kept).

```bash
# Squash locally
git checkout main
git merge --squash feature
git commit -m "Add login page (#42)"

# Merge commit locally
git merge --no-ff feature
```

### When I use which

- **Squash**: most feature PRs, where the individual commits are noisy. One PR = one commit on `main`.
- **Merge commit**: merging long-lived branches (for example `release` back into `main`) where the separate commits matter.
- In GitHub and Azure DevOps, you can **limit the allowed merge types** with branch protection or branch policies.

### Interview-ready answer

> "A merge commit brings all the branch's commits into main and adds a merge commit, so the full history is kept. A squash merge combines all the PR's commits into one new commit on main, giving a clean, linear history where each commit is one feature and is easy to revert. I use squash for normal feature PRs and a merge commit for long-lived branches like release branches, and I enforce the allowed merge types through branch policies."

</details>

<details><summary>Q9. What is a CODEOWNERS file?</summary>

`CODEOWNERS` is a file that says **which people or teams own which files** in a repository. When a PR changes those files, the owners are **automatically requested as reviewers**, and with branch protection their **approval can be required**.

### Where to put it

`.github/CODEOWNERS`, the repository root, or `docs/CODEOWNERS`. GitHub uses the first one it finds in that order. It applies on the PR's **base branch**.

### Example

```text
# Default owner for everything
*                       @org/platform-team

# Terraform
/infra/                 @org/cloud-team

# Pipelines must be approved by DevOps
/.github/workflows/     @org/devops-team

# All SQL files, anywhere
*.sql                   @org/dba-team

# One file, one person
/src/payments/config.yaml   @alice @org/payments-team
```

### Rules to remember

- Syntax is like `.gitignore`.
- **The last matching pattern wins**, so put general rules at the top and specific ones at the bottom.
- Owners must have **write access** to the repo; teams must be visible.
- To enforce it, turn on **"Require review from Code Owners"** in branch protection or a ruleset.
- Protect the CODEOWNERS file itself by giving it an owner, so nobody can quietly remove themselves from reviews.

### Azure DevOps

Azure Repos does not read a CODEOWNERS file. The same result comes from the branch policy **"Automatically included reviewers"**, with a path filter (for example `/infra/*`) and the option to make them required.

### Interview-ready answer

> "CODEOWNERS maps file paths to the people or teams who own them. When a PR touches those paths, the owners are added as reviewers automatically, and with 'Require review from Code Owners' in branch protection, the PR can't merge without their approval. I keep it in `.github/CODEOWNERS`, remember that the last matching pattern wins, and use it so that, for example, the DevOps team must approve workflow changes and the cloud team must approve Terraform. In Azure DevOps I get the same with automatically included reviewers and path filters."

</details>

<details><summary>Q10. What are branch policies?</summary>

**Branch policies** are rules on important branches (like `main` or `release/*`) that **control how code gets in**. They force changes to go through a pull request that meets quality checks. In Azure DevOps they are called **branch policies**; in GitHub they are **branch protection rules** or **rulesets**.

### Azure DevOps branch policies

| Policy | What it does |
| --- | --- |
| **Require a minimum number of reviewers** | For example 2 approvals; options to block self-approval and reset votes on new pushes |
| **Check for linked work items** | Every PR must link a Boards work item |
| **Check for comment resolution** | All PR comments must be resolved |
| **Limit merge types** | Allow only squash, for example |
| **Build validation** | A pipeline must pass on the PR before it can complete |
| **Status checks** | An external service (for example SonarQube) must post a success status |
| **Automatically included reviewers** | Add reviewers by path (for example `/infra/*`), optional or required |

When any policy is set, **direct pushes to the branch are blocked**; changes must come through a PR. Bypass permission should be given to very few people.

### GitHub equivalents

| Rule | What it does |
| --- | --- |
| Require a pull request before merging | No direct pushes |
| Required approvals, dismiss stale approvals | Approval count; new commits reset approvals |
| Require review from Code Owners | Owners from CODEOWNERS must approve |
| Require status checks to pass | CI jobs must succeed; optionally branch must be up to date |
| Require conversation resolution | All comments resolved |
| Require signed commits / linear history | Signed commits; no merge commits |
| Block force pushes and deletions | Protects history |
| Rulesets | The same rules, applied across **many repos and branches** at org level, with bypass lists |

### Interview-ready answer

> "Branch policies protect important branches like main. In Azure DevOps I set a minimum of two reviewers, required linked work items, comment resolution, build validation so the PR pipeline must pass, limited merge types, and automatically included reviewers for sensitive paths. Once a policy is on, nobody can push directly; everything goes through a PR. In GitHub I do the same with branch protection or rulesets, plus required status checks and code owner review."

</details>

<details><summary>Q11. How do you avoid duplicating YAML code in workflows across repositories?</summary>

When many repositories have nearly the same pipeline, copying YAML means every fix must be made in every repo. Instead, **write it once in a central repo and reuse it**.

### GitHub Actions

**1. Reusable workflows** (reuse whole jobs)

Central repo `org/ci-templates`, file `.github/workflows/dotnet-build.yml`:

```yaml
on:
  workflow_call:
    inputs:
      project:
        type: string
        required: true
    secrets:
      SONAR_TOKEN:
        required: false

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: dotnet build ${{ inputs.project }}
      - run: dotnet test ${{ inputs.project }}
```

Calling it from any repo:

```yaml
jobs:
  ci:
    uses: org/ci-templates/.github/workflows/dotnet-build.yml@v1
    with:
      project: src/Api/Api.csproj
    secrets: inherit
```

**2. Composite actions** (reuse a group of steps inside a job)

```yaml
# org/actions/setup-tools/action.yml
name: Setup tools
runs:
  using: composite
  steps:
    - uses: azure/login@v2
      with: { client-id: ..., tenant-id: ..., subscription-id: ... }
    - run: az aks install-cli
      shell: bash
```

```yaml
steps:
  - uses: org/actions/setup-tools@v1
```

**3. Other options**

- **Workflow templates** in the org's `.github` repo, so new repos start from a standard file.
- **Rulesets with required workflows**, to force a security scan in every repo.
- **Matrix** strategy, to avoid repeating the same job for each version or environment.

| | Reusable workflow | Composite action |
| --- | --- | --- |
| Reuses | Whole **jobs** | **Steps** inside one job |
| Can set `runs-on` | Yes | No (runs on the caller's runner) |
| Secrets | Passed with `secrets:` or `secrets: inherit` | Passed as inputs |

### Azure DevOps

**Templates** in a central repo, referenced as a repository resource:

```yaml
resources:
  repositories:
    - repository: templates
      type: git
      name: Platform/pipeline-templates
      ref: refs/tags/v1.2.0

extends:
  template: dotnet-pipeline.yml@templates
  parameters:
    project: src/Api/Api.csproj
```

Step, job, stage and variable templates are all possible. `extends` templates, together with a "Required template" check on environments, can **enforce** that every pipeline uses the approved template.

### Good practices

- **Version** the shared templates with tags (`@v1`, `ref: refs/tags/v1.2.0`) so a change does not break every repo at once.
- Use **parameters/inputs** instead of copy-pasting small differences.
- Document the templates and test changes before tagging a new version.

### Interview-ready answer

> "I keep shared pipeline logic in a central templates repo instead of copying YAML. In GitHub Actions I use reusable workflows with `workflow_call` for whole jobs and composite actions for common steps, and repos call them pinned to a version tag with inputs and `secrets: inherit`. In Azure DevOps I use step, job and stage templates from a repository resource, and `extends` templates with a required-template check to enforce standards. A fix in one place reaches every repo when they move to the new version."

</details>

<details><summary>Q12. What is <code>git cherry-pick</code>?</summary>

`git cherry-pick` **copies one or more specific commits** from one branch and applies them to your current branch as **new commits**, without merging the whole branch.

**Typical use case:** a bug fix was committed to `main`, and the same fix is needed on `release/2.3`, which must not get the other new features from `main`.

```bash
git checkout release/2.3
git cherry-pick -x a1b2c3d          # -x adds "(cherry picked from commit a1b2c3d)" to the message
git push
```

### Other forms

```bash
git cherry-pick a1b2c3d e4f5g6h     # several commits
git cherry-pick A^..B               # a range, including A
git cherry-pick -n a1b2c3d          # apply changes but don't commit yet
git cherry-pick -m 1 <merge-sha>    # pick a merge commit (choose parent 1 as the mainline)
```

### If there is a conflict

```bash
# fix the files
git add .
git cherry-pick --continue
# or give up
git cherry-pick --abort
```

### When to use it, and when not

| Use it for | Avoid it for |
| --- | --- |
| Hotfixes and backports to release branches | Moving many commits (merge or rebase instead) |
| A commit made on the wrong branch | Regularly syncing two branches: it creates duplicate commits with different IDs |

Platforms have it built in: GitHub (with a backport action or the CLI) and **Azure DevOps has a "Cherry-pick" button** on a completed PR that creates a new branch and PR to the target branch.

### Interview-ready answer

> "Cherry-pick applies a specific commit from one branch onto another as a new commit, without merging everything else. I mainly use it for hotfixes: the fix goes into main, then I cherry-pick it with `-x` onto the release branch so the message records where it came from. If there is a conflict I resolve it and run `--continue`. I avoid using it to sync branches regularly, because it creates duplicate commits. In Azure DevOps I can also cherry-pick a completed PR straight from the UI."

</details>
