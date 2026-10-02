# Azure DevOps: Azure Repos, Branching, and Code Review

> Azure Repos, branch policies, code review, merge strategies, permissions, branch recovery, pipeline triggers, and how it compares to GitHub.

## Interview Questions

### 1. What is Azure Repos?

**Answer:**

Azure Repos is Azure DevOps's source control. It supports Git and the older TFVC, with pull requests, branch policies, permissions, search, and integration with Boards and Pipelines.

A developer creates a branch, pushes commits, opens a pull request linked to a work item, and build-validation policies kick off automatically. Required reviewers approve it, and the chosen merge strategy updates the protected branch.

I set up Entra-backed groups, access scoped to only what's needed, no direct or force pushes to main, required reviewers and checks, comment resolution, and an audited bypass path. Git is the normal choice for distributed, modern workflows. TFVC might still exist for centralized legacy needs.

### 2. How do Azure Repos and GitHub differ?

**Answer:**

Both host Git repositories with pull requests, branch protection, and integrations. Azure Repos ties closely into Azure Boards, Pipelines, and Test Plans, with enterprise Azure DevOps permissions.

GitHub has a much broader public ecosystem, along with Actions, Apps, Codespaces, and its own native security and collaboration features.

I weigh identity, repository governance, the CI runner and network model, security features, open-source needs, integrations, data residency, availability, cost, migration effort, and how familiar the team already is with each platform.

Hosting an application on Azure doesn't automatically mean you need Azure Repos, and choosing GitHub doesn't automatically mean you need GitHub Actions either.

I pick whichever combination actually meets the organization's delivery and operational needs.

### 3. How do Azure Repos branch policies work?

**Answer:**

Policies apply to branches like `main`, and can require a minimum number of reviewers, specific or automatic reviewers, resolved comments, linked work items, build validation, status checks, and restrictions on how merges happen.

I require the relevant automated checks and reviewers for anything touching pipelines, infrastructure-as-code, or security-sensitive paths. I test policies with a normal account, and bypass access is limited to an audited emergency group.

There's a balance between safety and speed — flaky or slow checks push people toward bypassing them. I track failed validations, how long reviews take, how often bypass gets used, and defects that show up after merge. Any change to a policy gets reviewed too, since weakening a branch gate affects every release that follows.

### 4. How do you enforce code review in Azure Repos?

**Answer:**

I block direct pushes to protected branches and require pull requests with a minimum number of reviewers. Sensitive paths automatically get required reviewers, an author can't approve their own change where separation of duties matters, comments have to be resolved, and build and security checks have to pass.

A good pull request describes its purpose, risk, tests, deployment plan, and rollback plan. Reviewers look at correctness, security, operations, and any generated artifacts or plans — not just code style.

I audit bypass permissions and stale groups regularly. Emergency changes still go through a traceable path and get reviewed after the fact. Automated formatting removes the low-value comments so reviewers can focus on risk and design instead.

### 5. What merge strategies are available in Azure Repos?

**Answer:**

Azure Repos supports merge commit, squash merge, rebase with fast-forward, and semi-linear merge, depending on policy.

- **Merge** keeps the full branch history, but adds merge commits.
- **Squash** collapses everything into one commit and cleans up noisy feature history.
- **Rebase or fast-forward** gives a linear history, but rewrites the feature commits.
- **Semi-linear** rebases first, then adds a merge commit — keeping things linear while still marking the pull-request boundary.

I pick one strategy and enforce it consistently, based on what the team needs for audit history and releases. For short feature branches, squash is common. I avoid rewriting shared, protected history, and make sure release tags always point at the final reviewed commit.

### 6. How do you manage permissions in Azure Repos?

**Answer:**

I grant permissions through Entra or Azure DevOps groups at the organization, project, repository, and branch level. Developers contribute through pull requests, while force push, delete, bypassing policy, and managing permissions stay restricted.

Service identities only get the specific repository operations they actually need. External users and tokens have an expiry date and an owner. Sensitive repositories or pipeline paths get extra reviewers and protections.

I check the effective permissions, including inheritance and any deny rules, test them with real accounts, and review access periodically. When someone leaves or changes teams, removing them from the group removes their access everywhere at once. Audit logs and branch history back up any investigation.

### 7. How do you recover a deleted branch in Azure Repos?

**Answer:**

I find the last commit through completed pull requests, pipeline checkout logs or artifact metadata, release tags, another clone of the repo, or the Git reflog. Then I confirm it actually matches the revision that was deployed or approved.

```bash
git fetch --all
git branch release/2.4 <commit-sha>
git push origin release/2.4
```

After that, I restore and verify branch policies and permissions, since recreating a branch doesn't automatically bring those back. I hold off on any repository cleanup until recovery is confirmed.

To prevent this: restrict who can delete protected branches, keep release tags, set retention policies, keep backups or mirrors where needed, and limit who has administrative permission.

### 8. How do you trigger Azure Pipelines from Azure Repos?

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
