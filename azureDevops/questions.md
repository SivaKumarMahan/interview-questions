# Azure DevOps Interview Questions

---

### 1. What is Azure DevOps?

**Answer:**

Azure DevOps is Microsoft's application-lifecycle and DevOps platform. Its main services are Azure Repos for source control, Pipelines for CI/CD, Boards for work tracking, Artifacts for packages, and Test Plans for test management.

A typical flow links a Board work item to a branch and pull request, runs build/test/security checks in Pipelines, publishes a versioned package/image, deploys through protected environments, and records deployment evidence. Azure DevOps can deploy to Azure or other platforms.

I configure Entra-backed groups, least privilege, protected branches, workload-identity service connections, YAML templates, artifact retention, approvals, and audit logs. The value is traceability across code, work, build, artifact, and release—not only running scripts.

---

### 2. What is the difference between Azure Pipelines classic release and YAML pipelines?

**Answer:**

Classic build/release pipelines are configured mainly through the UI; YAML pipelines live in the repository as code. YAML supports review, branching, templates, version history, and easier reuse. Classic releases may remain in legacy systems or where teams rely on UI-managed stages.

I prefer multi-stage YAML for new work. Changes to production logic go through pull-request policy, and environment approvals/checks remain controlled outside YAML so a code change cannot remove every gate.

For migration I inventory tasks, variables, service connections, approvals, artifacts, schedules, and retention, reproduce them in YAML/templates, run both paths safely in parallel, compare artifacts/deployments, then decommission old credentials after cutover.

---

### 3. How do you design a multi-stage Azure Pipeline?

**Answer:**

I build one immutable artifact, then promote it:

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

Real CI also scans and publishes; staging runs smoke/integration tests; production uses environment checks, approval, monitoring, and rollback. Templates standardize jobs, but environment values/identities remain isolated. I set timeouts, concurrency/exclusive locks, artifact retention, and clear ownership.

---

### 4. What are service connections in Azure DevOps?

**Answer:**

A service connection stores/configures how Azure Pipelines authenticates to an external target such as Azure, Kubernetes, GitHub, or a registry. I prefer Azure Resource Manager connections using workload identity federation, which avoids a long-lived client secret.

I scope the identity to the smallest subscription/resource group/resource role, authorize only selected pipelines, and separate non-production from production. Creation and use are audited, ownership is documented, and unused connections are removed.

If authentication fails, I check connection verification, tenant/subscription, federated credential subject, pipeline authorization, role/scope, RBAC propagation, target network/firewall, and agent reachability. I test an allowed and denied operation to prove least privilege.

---

### 5. How do you use variables and variable groups in Azure Pipelines?

**Answer:**

Variables hold reusable values; variable groups share values across pipelines and can link to Key Vault. Templates/parameters are better for compile-time typed decisions, while variables are runtime strings.

```yaml
variables:
- group: app-prod-nonsecret
- name: imageTag
  value: $(Build.SourceVersion)
```

I keep non-secret environment configuration in reviewed files/groups and secrets in Key Vault or protected secret variables. Production groups are authorized only to required pipelines. I avoid echoing secrets and know that masking is not a complete protection.

I document precedence because template, pipeline, stage, job, and queue-time values can override each other. Rendered pipeline and logs help investigate an unexpected value without printing sensitive content.

---

### 6. How do you publish and consume artifacts in Azure DevOps?

**Answer:**

The build stage creates a tested artifact once and publishes it with version, commit SHA, checksum, and retention. Deployment stages download that exact artifact rather than rebuilding.

```yaml
- publish: $(Build.ArtifactStagingDirectory)
  artifact: application

- download: current
  artifact: application
```

Pipeline artifacts suit build outputs; Azure Artifacts feeds host NuGet, npm, Maven, Python, and Universal Packages. Container images go to a registry such as ACR.

I restrict write permissions, scan/sign artifacts, avoid secrets, and clean by retention policy. During investigation I verify artifact ID/digest and that the deployed environment used the same version tested in staging.

---

### 7. How do you handle large artifacts efficiently in Azure Pipelines?

**Answer:**

I first determine why the artifact is large and whether all files are deployment inputs. I remove build caches/debug output, use package/container registries, compress suitable content, split independent packages, and use incremental dependency caching—not artifact rebuilding.

Artifacts have explicit retention and immutable versions. Agents and storage are placed close to consumers where possible; parallel downloads are used only if supported and beneficial. I monitor upload/download time, size trend, storage cost, and deployment time.

For very large datasets or VM images, I use the appropriate storage/image service and pass a versioned reference through the pipeline rather than transferring it as a normal pipeline artifact.

---

### 8. How do approvals and environments work in Azure Pipelines?

**Answer:**

An environment represents a deployment target and records deployment history. Approvals and checks can require authorized users, branch control, business hours, exclusive lock, Azure Function/REST validation, or other gates before a deployment job starts.

I keep critical checks outside application YAML so a pull request cannot remove them. Approval shows artifact digest, change, risk, test/scan evidence, and rollback plan. Production identity is available only to that protected deployment.

I test approved, rejected, timed-out, and concurrent cases. Emergency bypass is restricted and audited. Approval supports accountability but does not replace automated health and policy gates.

---

### 9. How do you deploy to AKS from Azure Pipelines?

**Answer:**

The pipeline builds/tests/scans an image, pushes its immutable digest to ACR, and deploys through Helm/manifests or updates a GitOps repository. Authentication uses workload identity/service connection with least privilege.

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

I configure probes, requests, security context, PDB, and NetworkPolicy; secrets come from Key Vault/CSI. After deployment I check rollout, events, smoke tests, error/latency. Failure triggers traffic/release rollback while evidence is retained.

---

### 10. How do you secure Azure Pipelines?

**Answer:**

I protect repository and YAML changes, restrict pipeline editing/queueing, use least-privilege workload-identity service connections, protect environments and variable groups, and isolate self-hosted agents. Untrusted pull requests cannot access production secrets or runners.

Tasks/templates/images are pinned and reviewed. The pipeline runs secret, source, dependency, IaC, and image scans, publishes signed immutable artifacts, and records audit evidence. Secrets never enter artifacts/cache/logs.

I review organization/project permissions, service connection authorization, agent pools, OAuth token scope, retention, and extensions. A supply-chain incident plan covers revocation, artifact identification, and rebuild from trusted inputs.

---

### 11. What is a pipeline template in Azure DevOps?

**Answer:**

Templates are reusable YAML for stages, jobs, steps, or variables. They reduce duplication and provide approved build/security/deployment patterns.

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

I keep templates in a controlled repository, pin repository refs/tags, use typed parameters, document inputs, and test changes against representative consumers. Breaking changes get versioning/migration guidance. Templates standardize controls but should not hide pipeline behavior so deeply that application teams cannot troubleshoot.

---

### 12. How do you troubleshoot a failed Azure Pipeline?

**Answer:**

I identify the first failed stage/task and classify: YAML compilation, trigger, queue/agent, checkout, tool command, service connection, variable, artifact, or deployment.

I inspect logs, timeline, recent YAML/template/task changes, agent demands/capabilities, disk/network/DNS, permissions, variable scope, artifact paths, and external service status. For deployment I also check Azure Activity Log, AKS events, policy, quota, and target health.

I reproduce with the same tool image/parameters in a safe environment, fix the cause, rerun only an idempotent stage, and validate downstream output. Prevention may pin a version, improve a precheck, add timeout/capacity, or clarify errors.

---

### 13. What is Azure Repos?

**Answer:**

Azure Repos is Azure DevOps source control. It supports Git and legacy TFVC, with pull requests, branch policies, permissions, search, and integration with Boards/Pipelines.

A developer creates a branch, pushes commits, opens a pull request linked to a work item, and build-validation policies run. Required reviewers approve and the chosen merge strategy updates the protected branch.

I configure Entra-backed groups, least privilege, no direct/force push on main, required reviewers/checks, comment resolution, and audited bypass. Git is the normal choice for distributed modern workflows; TFVC may exist for centralized legacy needs.

---

### 14. How do Azure Repos branch policies work?

**Answer:**

Policies apply to branches such as `main` and can require minimum reviewers, specific/automatic reviewers, comment resolution, linked work items, build validation, status checks, and merge restrictions.

I require relevant automated validation and CODEOWNER-like path reviewers for pipeline/IaC/security paths. Policies are tested with normal accounts; bypass is limited to an audited emergency group.

I balance safety and speed: flaky or slow checks create bypass pressure. Policy metrics include failed validation, review duration, bypass use, and defects after merge. Changes to policies follow review because weakening a branch gate affects every release.

---

### 15. How do you enforce code review in Azure Repos?

**Answer:**

I block direct pushes to protected branches and require pull requests with minimum reviewers. Required reviewers are automatically added for sensitive paths, authors cannot satisfy independent approval where separation is required, comments must be resolved, and build/security checks must pass.

A good PR describes purpose, risk, tests, deployment, and rollback. Reviewers inspect correctness, security, operations, and generated artifacts/plans—not only style.

I audit bypass permissions and stale groups. Emergency changes still use a traceable path and receive retrospective review. Automated formatting removes low-value review comments so human attention stays on risk and design.

---

### 16. What merge strategies are available in Azure Repos?

**Answer:**

Azure Repos supports merge commit, squash merge, rebase with fast-forward, and semi-linear merge depending on policy.

- **Merge** preserves branch history but adds merge commits.
- **Squash** creates one target commit and cleans noisy feature history.
- **Rebase/fast-forward** produces a linear graph but rewrites feature commits.
- **Semi-linear** rebases then creates a merge commit, keeping linearity and PR boundary.

I choose and enforce a consistent strategy based on audit/history and release needs. For short feature branches squash is common. I avoid rewriting shared protected history and ensure release tags point to the reviewed final commit.

---

### 17. How do you trigger Azure Pipelines from Azure Repos?

**Answer:**

YAML `trigger` controls CI pushes by branch/path; branch build-validation policy runs a pipeline for pull requests in Azure Repos.

```yaml
trigger:
  branches:
    include: [main]
  paths:
    include: [src/*]
    exclude: [docs/*]
```

I avoid duplicate runs by understanding CI vs. PR policy triggers and test path filters. Pipeline resource triggers can start downstream pipelines after a successful published artifact.

For release, I prefer explicit artifact version/pipeline completion over a broad trigger. Branch policy ensures the PR validation pipeline is required and cannot be silently skipped by normal contributors.

---

### 18. How do you manage permissions in Azure Repos?

**Answer:**

I grant permissions through Entra/Azure DevOps groups at organization, project, repository, and branch scope. Developers can contribute through PRs, while force push, delete, bypass policy, and permission management remain restricted.

Service identities receive only repository operations they need. External users and tokens have expiry/owner. Sensitive repositories or pipeline paths receive additional reviewers and protections.

I inspect effective permissions including inheritance/deny, test with representative accounts, and review access periodically. When someone leaves or changes team, group membership removes access centrally. Audit logs and branch history support investigation.

---

### 19. How do you recover a deleted branch in Azure Repos?

**Answer:**

I find the last commit through completed PRs, pipeline checkout logs/artifact metadata, release tags, another clone, or Git reflog. I confirm it matches the expected deployed/approved revision.

```bash
git fetch --all
git branch release/2.4 <commit-sha>
git push origin release/2.4
```

Then I restore/verify branch policies and permissions because branch recreation may not restore all controls. I avoid repository cleanup until recovery. Prevention includes protected-branch deletion restrictions, release tags, retention, backups/mirrors where required, and limited administrative permission.

---

### 20. How do Azure Repos and GitHub differ?

**Answer:**

Both host Git repositories with pull requests, protection/policies, and integrations. Azure Repos is closely integrated with Azure Boards/Pipelines/Test Plans and enterprise Azure DevOps permissions. GitHub offers a broad public ecosystem, Actions, Apps, Codespaces, and GitHub-native security/collaboration.

I evaluate identity, repository governance, CI runner/network model, security features, open-source needs, integrations, data residency, availability, cost, migration, and team familiarity. An Azure-hosted application does not automatically require Azure Repos, and choosing GitHub does not automatically require GitHub Actions. I select the combined platform that meets organizational delivery and operational requirements.
