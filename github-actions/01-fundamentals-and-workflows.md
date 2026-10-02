# GitHub Actions: Fundamentals and Workflows

> GitHub Actions architecture, workflow building blocks, and how to write a workflow.

## Key Concepts

### Architecture

GitHub Actions is GitHub's built-in, event-driven automation platform. Workflow YAML files live under `.github/workflows/`.

Events such as `push`, `pull_request`, `workflow_dispatch`, schedules, releases, or a repository dispatch create workflow runs. A workflow contains jobs. Each job runs on a GitHub-hosted or self-hosted runner and contains ordered steps that execute commands or reusable actions.

**Typical flow:**

1. A developer pushes a commit or opens a pull request.
2. GitHub checks the workflow's event, branch, and path filters.
3. A runner checks out the exact commit and runs the build, test, scan, and packaging jobs.
4. Artifacts or a container digest are published. The digest is immutable, meaning it never changes once it's created.
5. Protected environments apply reviewers, branch restrictions, and scoped secrets before deployment.
6. The workflow deploys to a VM, Kubernetes, or a cloud target, then reports status and sends notifications.

Some good defaults for production: keep `permissions` scoped to the minimum needed (least privilege), pin third-party actions to trusted, immutable commit SHAs, prefer OIDC federation over long-lived cloud keys, isolate self-hosted runners, protect environments, and keep untrusted pull requests away from deployment secrets.

### Workflow Building Blocks

| Concept | What it does |
| --- | --- |
| Event | Triggers a workflow — for example `push`, `pull_request`, `workflow_dispatch`, or `schedule` |
| Job | Runs on its own runner; jobs run in parallel unless `needs` sets a dependency |
| Step | Runs sequentially inside a job; each step runs a shell command or an action |
| Action | A reusable, packaged automation unit |
| Runner | The execution environment — GitHub-hosted or self-hosted |

Basic Node.js CI example:

```yaml
name: CI

on:
  pull_request:
  push:
    branches: [main]

permissions:
  contents: read

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - name: Check out source
        uses: actions/checkout@v6

      - name: Set up Node.js
        uses: actions/setup-node@v6
        with:
          node-version-file: .nvmrc
          cache: npm

      - name: Install locked dependencies
        run: npm ci

      - name: Run tests
        run: npm test
```

Version tags keep this example readable, but production workflows should pin third-party and reusable actions to reviewed, full commit SHAs, and use dependency automation to update them safely. `npm ci` honors the committed lock file, so it's more reproducible in CI than `npm install`.

## Interview Questions

### 1. What are GitHub Actions?

**Answer:**

GitHub Actions is GitHub's built-in automation platform, and it's event-driven. A workflow is a YAML file stored in `.github/workflows`. Events trigger workflows. Workflows contain jobs. Jobs run on runners. Each job has steps that run commands or reusable actions.

Actions can run CI/CD, scheduled maintenance, issue automation, releases, security scans, and infrastructure workflows. GitHub-hosted runners are convenient and short-lived, spun up fresh for each job. Self-hosted runners are useful when you need private network access or special software, but you have to patch them, isolate them, scale them, and clean them up yourself.

For production, I keep `permissions` scoped to the minimum needed — least privilege. I use protected environments, OIDC federation instead of long-lived cloud keys, actions pinned to trusted versions, concurrency controls, timeouts, artifact retention, and branch protection for workflow files.

### 2. Why is GitHub Actions popular?

**Answer:**

It's popular because the automation lives right next to the code. It reacts directly to GitHub events, has a huge ecosystem of ready-made actions, supports both hosted and self-hosted runners, and integrates well with pull requests, environments, releases, packages, and GitHub's security features.

There are trade-offs, though. Hosted runners can't reach private systems without extra networking. Usage costs can add up. Untrusted marketplace actions carry supply-chain risk. Self-hosted runners need strong isolation and ongoing maintenance.

I choose GitHub Actions when the source already lives in GitHub and the workflow fits its security and runner model. I'd consider Jenkins, Azure Pipelines, GitLab CI, or a dedicated deployment controller instead when customization needs, network placement, governance, or existing platform investment point that way.

### 3. How do you create a GitHub Actions workflow?

**Answer:**

I start by figuring out the triggering event and the outcome I need. Then I split independent work into separate jobs and make deployment depend on CI passing first.

```yaml
name: application-ci

on:
  pull_request:
  push:
    branches: [main]

permissions:
  contents: read

concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: true

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 20
          cache: npm
      - run: npm ci
      - run: npm test
```

I validate the YAML, pin the actions, set explicit permissions and timeouts, cache only dependencies that are safe to cache, and make sure secrets never get printed to logs. A pull request tests the workflow before it merges.

For deployment, I add an environment that requires approval, OIDC authentication, a versioned artifact, smoke tests, health monitoring, and a rollback plan.

### 4. What CI/CD tools have you used in your current role?

**Answer:**

I like to explain tools through the delivery flow rather than just naming them. Here's a typical workflow:

1. GitHub stores the code and protects the main branch.
2. GitHub Actions runs the build, unit tests, linting, SonarQube, dependency scanning, and Trivy.
3. The pipeline publishes an image to a container registry. The image is immutable, meaning once it's built it never changes.
4. Helm packages the Kubernetes configuration.
5. Argo CD or Flux promotes the approved image through each environment.
6. Prometheus, Grafana, and application monitoring confirm the release is healthy.

I've also worked with, or understand, similar patterns in Jenkins, Azure Pipelines, and GitLab CI. In an interview I say exactly what I configured myself, what another team owned, the scale involved, one failure I investigated, and the outcome.

Which tool I pick depends on the repository platform, how much customization is needed, where the runners sit, governance requirements, cost, and the team's existing skills.
