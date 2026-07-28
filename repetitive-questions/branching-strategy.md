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
