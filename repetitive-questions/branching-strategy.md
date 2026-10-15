# Repetitive Interview Questions

## What branching strategy do you follow, and how does it ensure safe Production deployments?

**Interviewer:** What branching strategy do you use in your project?

**Candidate:**

I normally use a simple trunk-based strategy. The `main` branch is always kept stable, and developers create short-lived feature branches for their work.

```text
main
  ├── feature/login
  ├── feature/payment
  └── hotfix/production-error
```

### Create a feature branch

```bash
git checkout main
git pull
git checkout -b feature/login
```

The developer makes a small change, tests it locally, and pushes the branch.

```bash
git add .
git commit -m "Add login validation"
git push -u origin feature/login
```

### Open a pull request

The feature branch is merged into `main` only through a pull request. The pull request checks:

- Unit tests.
- Code quality.
- Security scanning.
- Build success.
- Review approval.

Direct pushes to `main` are blocked using branch protection.

### Merge small changes

I prefer small pull requests because they are easier to review, test, and roll back. After approval and successful checks, the change is merged into `main`.

The feature branch is then deleted because its work is complete.

### Build once

The pipeline builds one container image from the merged commit.

```text
orders-api:1.4.2
```

The same image is promoted through Development, Testing, Staging, and Production. I do not rebuild a different image for each environment.

```text
feature branch
-> pull request
-> main
-> build and test
-> Development
-> Testing
-> Staging
-> Production approval
-> Production
```

### Production protection

Before Production deployment, I use:

- Required approvals.
- Successful automated tests.
- A known image tag or digest.
- A rollback plan.
- Deployment monitoring.

### Hotfix workflow

For an urgent Production issue, I create a hotfix branch from `main`.

```bash
git checkout main
git pull
git checkout -b hotfix/payment-timeout
```

The hotfix still goes through a pull request and required tests. After it is merged, the pipeline creates a new release and deploys it through the approved process.

I do not make an untracked change directly in Production.

### When would I use a release branch?

Most teams do not need a long-lived release branch. I use one only when a released version must be supported separately while new development continues on `main`.

For example:

```text
main
release/2.x
```

A fix made for `release/2.x` must also be merged back into `main` when it is still relevant.

### Example

Suppose a developer is adding a payment feature. They create `feature/payment`, open a pull request, and pass all checks.

After merge, the pipeline builds `payment-api:2.1.0`. That exact image is tested in lower environments and later promoted to Production after approval.

If a problem is found, we know the exact commit and image that introduced it, making rollback easier.

### In short

I use short-lived feature branches with a protected `main` branch. Every change goes through a pull request, automated checks, and review.

After merge, the pipeline builds one versioned artifact and promotes the same artifact through all environments. This keeps Production stable and gives us a clear history for auditing and rollback.

---

## How do you resolve merge conflicts?

**Interviewer:** Your pull request has conflicts with `main`. What do you do?

**Candidate:**

I bring the latest `main` into my feature branch, fix the conflicts by hand, test, and push. I never resolve by force-pushing over `main`.

```bash
git checkout feature/payment
git fetch origin
git merge origin/main        # or: git rebase origin/main
git status                   # shows "both modified" files
```

Git marks the conflict in the file:

```text
<<<<<<< HEAD
replicas: 3
image: payment-api:1.4.1
=======
replicas: 5
image: payment-api:1.4.2
>>>>>>> origin/main
```

`HEAD` is my branch, the other side is the incoming change. I do not blindly pick "ours" or "theirs". I check why each change was made and keep the correct final result, then delete the markers.

```bash
git diff --check             # finds leftover conflict markers
git add values.yaml
git commit                   # for a merge
# or: git rebase --continue  # for a rebase
git push                     # after a rebase: git push --force-with-lease
```

Then the PR pipeline runs again, and the reviewer approves.

Useful escape hatches:

```bash
git merge --abort
git rebase --abort
```

Remember:

- Run the tests and build after resolving. A conflict that "looks" fixed can still break the app.
- After a rebase, only force-push my own feature branch, and use `--force-with-lease`, never plain `--force`.
- Small, short-lived branches and pulling `main` often mean fewer conflicts.

## Apart from pre-commit, what other Git hooks and checks are there?

**Interviewer:** Apart from pre-commit hooks, what other hooks and checks do you know, inside and outside Git?

**Candidate:**

Pre-commit is only the first layer. Checks run on the laptop, on the Git server, in CI, in Kubernetes, and in Azure.

### Git hooks

| Hook | Runs | Used for |
| --- | --- | --- |
| `pre-commit` | before a commit is created | format, lint, secret scan |
| `commit-msg` | after the message is written | enforce a format, for example `JIRA-123: message` |
| `pre-push` | before `git push` | run unit tests or quick validation |
| `post-merge`, `post-checkout` | after merge or checkout | install dependencies, local setup |
| `pre-receive`, `update` | on the Git server, before a push is accepted | block pushes to protected branches, reject secrets |
| `post-receive` | on the server, after a push | notify, trigger a build |

Local hooks live in `.git/hooks` and are not shared. I use the **pre-commit framework** so the whole team runs the same hooks:

```yaml
# .pre-commit-config.yaml (pin rev to a current release)
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v5.0.0
    hooks:
      - id: check-yaml
      - id: check-merge-conflict
      - id: trailing-whitespace
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.24.2
    hooks:
      - id: gitleaks
  - repo: https://github.com/antonbabenko/pre-commit-terraform
    rev: v1.99.0
    hooks:
      - id: terraform_fmt
      - id: terraform_tflint
```

```bash
pre-commit install          # install the hooks for this clone
pre-commit run --all-files
```

On hosted Git (Azure Repos, GitHub, GitLab), I cannot add server-side hooks. Branch policies, push protection, and required status checks do that job.

### Checks outside Git

```text
Laptop      -> pre-commit: fmt, lint, Gitleaks
Git server  -> branch policies, required reviewers, PR build validation, push protection
CI          -> tests, SonarQube Quality Gate, dependency scan, Trivy, Checkov, TFLint, Hadolint, kubeconform
Kubernetes  -> admission control: Kyverno or OPA Gatekeeper, Pod Security Admission
Azure       -> Azure Policy (deny public storage, require tags, allowed regions)
```

Remember:

- Local hooks can be skipped with `git commit --no-verify`. That is why the same checks also run in CI, where they cannot be skipped.
- SonarQube, Trivy, and Checkov are CI gates, not Git hooks.
- tfsec is now part of Trivy (`trivy config .`).
- Kyverno or Gatekeeper stop a bad manifest at the cluster even if it got past CI. Azure Policy stops a bad resource even if it was created outside Terraform.
