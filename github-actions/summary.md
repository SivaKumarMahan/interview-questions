# GitHub Actions Summary

## Architecture

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

## Workflow Building Blocks

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

## CI/CD Workflow Pattern

A production workflow commonly runs, in order: checkout, language/tool setup, dependency caching, build, unit tests, test-report upload, code and security checks, Docker build, registry login through short-lived identity, image push by digest, deployment, rollout verification, and notification.

Matrices test multiple supported versions at once. Reusable workflows keep multiple pipelines in sync and prevent copy-paste drift.

## Handoff to Azure DevOps

When GitHub Actions handles CI and Azure DevOps handles CD, GitHub Actions publishes a versioned package or an immutable ACR image digest, along with provenance (where the artifact came from and how it was built) and scan evidence.

Azure DevOps consumes and promotes that same artifact through protected environments — it should not rebuild the application.

Prefer GitHub OIDC to obtain short-lived Azure credentials, grant that identity only the ACR publishing permissions it needs, and protect the production Azure DevOps environment with resource permissions, branch control, approvals, and checks.

If Azure Pipelines already connects directly to GitHub and can own the whole workflow, it's worth comparing that simpler design before committing to a cross-platform handoff.

## Common Failures

| Failure | Common causes |
| --- | --- |
| Workflow not triggered | Wrong event, branch/path filter, file path, YAML syntax, or Actions disabled |
| Step failure | Nonzero exit code, missing dependency, wrong working directory, bad input, or wrong shell |
| Checkout/permission failure | Token scope, private repo access, wrong ref, proxy/network issue, or submodule credentials |
| Missing secret/variable | Wrong scope or context (`secrets`, `vars`, `env`), environment not selected, or secret unavailable to forks |
| Action/dependency/cache failure | Invalid version, removed action, wrong cache key/path, quota, corruption, or proxy |
| Artifact/registry failure | Wrong path/name, retention expired, authentication, repository policy, or image tag |
| Deployment/runner timeout | Missing approval, wrong environment, resource limits, queue capacity, or no runner available |

Start troubleshooting with the workflow syntax, event delivery, the first failed step, effective permissions, runner logs, repository/environment configuration, and GitHub's service status. Add debug output carefully, and never expose secrets in it.
