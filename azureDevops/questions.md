# Azure DevOps Interview Questions

---

### 1. What is Azure DevOps?

**Answer:**

Azure DevOps is Microsoft's platform for the whole application lifecycle. Its main services are Azure Repos for source control, Pipelines for CI/CD, Boards for work tracking, Artifacts for packages, and Test Plans for test management.

A typical flow links a Board work item to a branch and a pull request, runs build, test, and security checks in Pipelines, publishes a versioned package or image, deploys through protected environments, and records evidence of the deployment. Azure DevOps can deploy to Azure or to other platforms just as easily.

I set up Entra-backed groups, access scoped to only what's needed, protected branches, workload-identity service connections, YAML templates, artifact retention, approvals, and audit logs. The real value here is being able to trace a change all the way from code to work item to build to artifact to release — not just running scripts.

---

### 2. What is the difference between Azure Pipelines classic release and YAML pipelines?

**Answer:**

Classic build and release pipelines are configured mostly through the UI. YAML pipelines live in the repository as code, which means they get code review, branching, templates, version history, and are easier to reuse.

Classic releases still show up in older systems, or where a team just prefers managing stages through the UI.

I prefer multi-stage YAML for new work. Changes to production logic go through pull-request review, and environment approvals and checks stay configured outside the YAML file itself, so a code change can't accidentally remove a safety gate.

When migrating, I inventory the tasks, variables, service connections, approvals, artifacts, schedules, and retention settings, rebuild them in YAML and templates, run both pipelines side by side safely, compare the artifacts and deployments they produce, then retire the old credentials once the cutover is done.

---

### 3. How do you design a multi-stage Azure Pipeline?

**Answer:**

I build one artifact that never changes once built, then promote that same artifact through each stage:

```yaml
stages:
- stage: CI
  jobs:
  - job: TestBuildScan
    pool: { vmImage: ubuntu-latest }
    steps:
    - checkout: self
    - script: npm ci && npm test
    - script: docker build -t $(imageRepo):$(Build.SourceVersion) .

- stage: Deploy_Staging
  dependsOn: CI
  jobs:
  - deployment: Deploy
    environment: staging
    strategy:
      runOnce:
        deploy:
          steps:
          - script: ./deploy.sh staging $(Build.SourceVersion)
```

In a real pipeline, CI also scans the image and publishes it, staging runs smoke and integration tests, and production adds environment checks, approval, monitoring, and rollback. Templates standardize the jobs, but each environment's values and identities stay isolated from the others.

I set timeouts, concurrency or exclusive locks, artifact retention, and make sure ownership of each stage is clear.

---

### 4. What are service connections in Azure DevOps?

**Answer:**

A service connection stores how Azure Pipelines authenticates to something external — Azure, Kubernetes, GitHub, or a registry. I prefer Azure Resource Manager connections that use workload identity federation, so there's no long-lived client secret sitting around.

I scope the identity to the smallest subscription, resource group, or resource role it needs, authorize it only for the pipelines that should use it, and keep non-production separate from production. Creating and using a connection is audited, ownership is documented, and connections nobody's using anymore get removed.

If authentication fails, I check that the connection is verified, the tenant and subscription, the federated credential's subject, which pipelines are authorized to use it, the role and its scope, whether RBAC has propagated, the target's network or firewall, and whether the agent can even reach it. I test one allowed and one denied operation to actually prove least privilege is working.

---

### 5. How do you use variables and variable groups in Azure Pipelines?

**Answer:**

Variables hold reusable values. Variable groups share those values across pipelines and can link straight to Key Vault. Templates and parameters are better for decisions that need to be typed and fixed at compile time; variables are just runtime strings.

```yaml
variables:
- group: app-prod-nonsecret
- name: imageTag
  value: $(Build.SourceVersion)
```

I keep non-secret configuration in reviewed files or groups, and put actual secrets in Key Vault or protected secret variables. Production groups are authorized only for the pipelines that need them.

I avoid ever echoing a secret, and I know masking output is a safety net, not a real guarantee.

I also document how precedence works, since template, pipeline, stage, job, and queue-time values can all override each other. Reading the rendered pipeline and its logs helps track down an unexpected value without printing anything sensitive.

---

### 8. How do approvals and environments work in Azure Pipelines?

**Answer:**

An environment represents a deployment target and keeps a history of what's been deployed to it. Approvals and checks can require an authorized approver, a specific branch, business hours, an exclusive lock, an Azure Function or REST call for validation, or other gates before a deployment job is allowed to start.

I keep the critical checks outside the application's YAML, so a pull request can't quietly remove them. The approval screen should show the artifact's digest, what changed, the risk, test and scan evidence, and the rollback plan. Production identity is only made available to that specific protected deployment.

I test the approved, rejected, timed-out, and concurrent cases. Emergency bypass is tightly restricted and audited. Approval supports accountability, but it's not a substitute for automated health and policy checks.

---

### 9. How do you deploy to AKS from Azure Pipelines?

**Answer:**

The pipeline builds, tests, and scans an image, pushes its digest — a fixed reference that always points to that exact image — to ACR, then deploys it through Helm, plain manifests, or by updating a GitOps repository. Authentication uses workload identity or a service connection scoped to only what's needed.

```yaml
- task: HelmDeploy@0
  inputs:
    command: upgrade
    chartType: FilePath
    chartPath: chart
    releaseName: orders
    namespace: orders
    arguments: '--install --atomic --wait --set image.tag=$(Build.SourceVersion)'
```

I set up probes, resource requests, a security context, a PodDisruptionBudget, and NetworkPolicy. Secrets come from Key Vault through the CSI driver. After deployment I check the rollout, events, smoke tests, and error rate and latency. If something's wrong, it triggers a rollback of traffic or the release, and the evidence is kept.

---

### 10. How do you secure Azure Pipelines?

**Answer:**

I protect the repository and its YAML from unreviewed changes, restrict who can edit or queue pipelines, use workload-identity service connections scoped to the minimum needed, protect environments and variable groups, and isolate self-hosted agents. Untrusted pull requests can't reach production secrets or runners.

Tasks, templates, and images are pinned to specific versions and reviewed. The pipeline runs secret, source, dependency, infrastructure-as-code, and image scans, publishes signed artifacts that never change once built, and keeps audit evidence. Secrets never end up in artifacts, cache, or logs.

I review organization and project permissions, which pipelines each service connection is authorized for, agent pools, OAuth token scope, retention settings, and extensions. For a supply-chain incident, I have a plan covering revocation, identifying affected artifacts, and rebuilding from trusted sources.

---

### 11. What is a pipeline template in Azure DevOps?

**Answer:**

Templates are reusable YAML for stages, jobs, steps, or variables. They cut down on duplication and give teams an approved pattern for building, scanning, and deploying.

```yaml
# templates/test.yml
parameters:
- name: nodeVersion
  type: string
  default: '20'

steps:
- task: NodeTool@0
  inputs: { versionSpec: '${{ parameters.nodeVersion }}' }
- script: npm ci && npm test
```

I keep templates in a controlled repository, pin to a specific ref or tag, use typed parameters, document the inputs, and test changes against the teams actually using them. Breaking changes get proper versioning and migration guidance.

Templates should standardize the important controls, but not hide pipeline behavior so deeply that the team using it can't troubleshoot it themselves.

---

### 12. How do you troubleshoot a failed Azure Pipeline?

**Answer:**

I find the first task or stage that actually failed and figure out what kind of failure it is: YAML compilation, a trigger, a queued or agent problem, checkout, a tool command, a service connection, a variable, an artifact, or the deployment itself.

I look at the logs, the timeline, any recent changes to YAML, templates, or tasks, agent demands and capabilities, disk, network, and DNS, permissions, variable scope, artifact paths, and the status of any external service involved. For a deployment failure, I also check the Azure Activity Log, AKS events, policy, quota, and the target's health.

I reproduce it with the same tool image and parameters in a safe environment, fix the actual cause, rerun only the stage that's safe to repeat, and confirm the output downstream looks right. To prevent it happening again, I might pin a version, add an earlier check, add a timeout or more capacity, or make the error message clearer.

---

### 13. What is Azure Repos?

**Answer:**

Azure Repos is Azure DevOps's source control. It supports Git and the older TFVC, with pull requests, branch policies, permissions, search, and integration with Boards and Pipelines.

A developer creates a branch, pushes commits, opens a pull request linked to a work item, and build-validation policies kick off automatically. Required reviewers approve it, and the chosen merge strategy updates the protected branch.

I set up Entra-backed groups, access scoped to only what's needed, no direct or force pushes to main, required reviewers and checks, comment resolution, and an audited bypass path. Git is the normal choice for distributed, modern workflows. TFVC might still exist for centralized legacy needs.

---

### 14. How do Azure Repos branch policies work?

**Answer:**

Policies apply to branches like `main`, and can require a minimum number of reviewers, specific or automatic reviewers, resolved comments, linked work items, build validation, status checks, and restrictions on how merges happen.

I require the relevant automated checks and reviewers for anything touching pipelines, infrastructure-as-code, or security-sensitive paths. I test policies with a normal account, and bypass access is limited to an audited emergency group.

There's a balance between safety and speed — flaky or slow checks push people toward bypassing them. I track failed validations, how long reviews take, how often bypass gets used, and defects that show up after merge. Any change to a policy gets reviewed too, since weakening a branch gate affects every release that follows.

---

### 15. How do you enforce code review in Azure Repos?

**Answer:**

I block direct pushes to protected branches and require pull requests with a minimum number of reviewers. Sensitive paths automatically get required reviewers, an author can't approve their own change where separation of duties matters, comments have to be resolved, and build and security checks have to pass.

A good pull request describes its purpose, risk, tests, deployment plan, and rollback plan. Reviewers look at correctness, security, operations, and any generated artifacts or plans — not just code style.

I audit bypass permissions and stale groups regularly. Emergency changes still go through a traceable path and get reviewed after the fact. Automated formatting removes the low-value comments so reviewers can focus on risk and design instead.

---

### 16. What merge strategies are available in Azure Repos?

**Answer:**

Azure Repos supports merge commit, squash merge, rebase with fast-forward, and semi-linear merge, depending on policy.

- **Merge** keeps the full branch history, but adds merge commits.
- **Squash** collapses everything into one commit and cleans up noisy feature history.
- **Rebase or fast-forward** gives a linear history, but rewrites the feature commits.
- **Semi-linear** rebases first, then adds a merge commit — keeping things linear while still marking the pull-request boundary.

I pick one strategy and enforce it consistently, based on what the team needs for audit history and releases. For short feature branches, squash is common. I avoid rewriting shared, protected history, and make sure release tags always point at the final reviewed commit.

---

### 17. How do you trigger Azure Pipelines from Azure Repos?

**Answer:**

The YAML `trigger` section controls CI runs by branch and path. A branch's build-validation policy separately runs a pipeline for pull requests.

```yaml
trigger:
  branches:
    include: [main]
  paths:
    include: [src/*]
    exclude: [docs/*]
```

I'm careful to avoid duplicate runs by understanding the difference between a CI trigger and a PR policy trigger, and I test the path filters. Pipeline resource triggers can kick off a downstream pipeline once an artifact has actually been published.

For releases, I prefer triggering off an explicit artifact version or pipeline completion rather than a broad trigger. Branch policy makes sure the PR validation pipeline is required and can't be quietly skipped by a normal contributor.

---

### 18. How do you manage permissions in Azure Repos?

**Answer:**

I grant permissions through Entra or Azure DevOps groups at the organization, project, repository, and branch level. Developers contribute through pull requests, while force push, delete, bypassing policy, and managing permissions stay restricted.

Service identities only get the specific repository operations they actually need. External users and tokens have an expiry date and an owner. Sensitive repositories or pipeline paths get extra reviewers and protections.

I check the effective permissions, including inheritance and any deny rules, test them with real accounts, and review access periodically. When someone leaves or changes teams, removing them from the group removes their access everywhere at once. Audit logs and branch history back up any investigation.

---

### 19. How do you recover a deleted branch in Azure Repos?

**Answer:**

I find the last commit through completed pull requests, pipeline checkout logs or artifact metadata, release tags, another clone of the repo, or the Git reflog. Then I confirm it actually matches the revision that was deployed or approved.

```bash
git fetch --all
git branch release/2.4 <commit-sha>
git push origin release/2.4
```

After that, I restore and verify branch policies and permissions, since recreating a branch doesn't automatically bring those back. I hold off on any repository cleanup until recovery is confirmed.

To prevent this: restrict who can delete protected branches, keep release tags, set retention policies, keep backups or mirrors where needed, and limit who has administrative permission.

---

### 20. How do Azure Repos and GitHub differ?

**Answer:**

Both host Git repositories with pull requests, branch protection, and integrations. Azure Repos ties closely into Azure Boards, Pipelines, and Test Plans, with enterprise Azure DevOps permissions.

GitHub has a much broader public ecosystem, along with Actions, Apps, Codespaces, and its own native security and collaboration features.

I weigh identity, repository governance, the CI runner and network model, security features, open-source needs, integrations, data residency, availability, cost, migration effort, and how familiar the team already is with each platform.

Hosting an application on Azure doesn't automatically mean you need Azure Repos, and choosing GitHub doesn't automatically mean you need GitHub Actions either.

I pick whichever combination actually meets the organization's delivery and operational needs.
