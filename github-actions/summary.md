# GitHub Actions Summary

## Architecture

GitHub Actions is an event-driven automation platform built into GitHub. Workflow YAML files live under `.github/workflows/`. Events such as `push`, `pull_request`, `workflow_dispatch`, schedules, releases, or repository dispatch create workflow runs. A workflow contains jobs; each job runs on a GitHub-hosted or self-hosted runner and contains ordered steps that execute commands or reusable actions.

**Typical flow:**

1. A developer pushes a commit or opens a pull request.
2. GitHub evaluates workflow event, branch, and path filters.
3. A runner checks out the exact commit and executes build, test, scan, and packaging jobs.
4. Artifacts or an immutable container digest are published.
5. Protected environments apply reviewers, branch restrictions, and scoped secrets before deployment.
6. The workflow deploys to VM, Kubernetes, or cloud targets and reports status/notifications.

Use least-privilege `permissions`, pin third-party actions to trusted immutable commit SHAs, prefer OIDC federation over long-lived cloud keys, isolate self-hosted runners, protect environments, and keep untrusted pull requests away from deployment secrets.

## Workflow Building Blocks

- **Events** trigger a workflow, for example `push`, `pull_request`, `workflow_dispatch` or `schedule`.
- **Jobs** run on separate runners and run in parallel unless `needs` defines a dependency.
- **Steps** run sequentially inside a job and can execute a shell command or an action.
- **Actions** are reusable automation units.
- **Runners** provide the execution environment and can be GitHub-hosted or self-hosted.

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

Version tags keep this example readable, but production workflows should pin third-party and reusable actions to reviewed full commit SHAs and use dependency automation to update them safely. `npm ci` honors the committed lock file and is more reproducible than `npm install` in CI.

## CI/CD Workflow Pattern

A production workflow commonly has checkout, language/tool setup, dependency caching, build, unit tests, test-report upload, code/security checks, Docker build, registry login through short-lived identity, image push by digest, deployment, rollout verification, and notification. Matrices can test supported versions; reusable workflows prevent copy/paste drift.

## Handoff to Azure DevOps

When GitHub Actions performs CI and Azure DevOps performs CD, GitHub Actions publishes a versioned package or immutable ACR image digest together with provenance and scan evidence. Azure DevOps consumes and promotes that same artifact through protected environments; it must not rebuild the application.

Prefer GitHub OIDC to obtain short-lived Azure credentials, grant the identity only the required ACR publishing permissions, and protect the production Azure DevOps environment with resource permissions, branch control, approvals and checks. If Azure Pipelines already connects directly to GitHub and can own the full workflow, compare that simpler design before maintaining a cross-platform handoff.

## Common Failures

- **Workflow not triggered:** wrong event, branch/path filter, file path, syntax, or disabled Actions.
- **Step failure:** nonzero command, missing dependency, incorrect working directory, input, or shell.
- **Checkout/permission failure:** token scope, private repository access, wrong ref, proxy/network, or submodule credentials.
- **Missing secret/variable:** wrong scope or context (`secrets`, `vars`, `env`), environment not selected, or unavailable fork secret.
- **Action/dependency/cache failure:** invalid version, removed action, wrong key/path, quota, corruption, or proxy.
- **Artifact/registry failure:** wrong path/name, retention expiry, authentication, repository policy, or image tag.
- **Deployment/runner timeout:** missing approval, wrong environment, resource limits, queue capacity, or unavailable runner.

Start with workflow syntax, event delivery, first failed step, effective permissions, runner logs, repository/environment configuration, and GitHub service status. Add debug output carefully without exposing secrets.
