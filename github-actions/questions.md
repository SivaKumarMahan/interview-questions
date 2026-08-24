## 1. What CI/CD tools have you used in your current role?

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

## 2. How are SonarQube, Docker, and Trivy integrated in pipelines?

**Answer:**

I place quality and security checks before an image is published or deployed:

```text
checkout → test → SonarQube → quality gate → Docker build
         → Trivy scan → push immutable image → deploy → smoke test
```

```yaml
jobs:
  build:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@v4
      - name: Test
        run: npm ci && npm test -- --coverage
      - name: SonarQube scan
        uses: SonarSource/sonarqube-scan-action@v3
        env:
          SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}
          SONAR_HOST_URL: ${{ secrets.SONAR_HOST_URL }}
      - name: Build image
        run: docker build -t app:${{ github.sha }} .
      - name: Scan image
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: app:${{ github.sha }}
          severity: HIGH,CRITICAL
          exit-code: "1"
```

SonarQube checks source code quality and test coverage. Trivy checks the built image and its dependencies. I pin action versions to approved releases, set up a vulnerability exception process with an expiry date, upload scan reports even when a job fails, and never push or deploy an image if a required gate fails.

## 3. How do you trigger a GitHub Actions workflow in another repository?

**Answer:**

The best approach depends on who owns each repository. For loosely coupled systems, I prefer publishing a versioned artifact or image and letting the consumer repository detect or promote that version on its own.

When a direct trigger is needed, common options are `repository_dispatch`, calling `workflow_dispatch` through the API, or a reusable workflow — that last one works when repositories share an organization and a trust model.

The caller needs permission to invoke the target repository. I prefer a GitHub App token with narrow, short-lived access over a broad personal access token.

The payload should only carry identifiers, like a version number and source commit, never secrets. The target repository validates the sender, checks the artifact exists, and confirms the environment is allowed before it deploys.

I also add concurrency control, make the workflow idempotent, meaning safe to run more than once, keep audit logs, and attach a correlation ID. That way duplicate requests can't deploy twice, and both workflow runs stay traceable.

## 4. What is the purpose of `repository_dispatch` in GitHub Actions?

**Answer:**

`repository_dispatch` is a custom event sent through the GitHub API. It lets an external system or another repository start a workflow and pass a small JSON payload.

```yaml
on:
  repository_dispatch:
    types: [deploy-version]

jobs:
  deploy:
    if: github.event.client_payload.environment == 'staging'
    runs-on: ubuntu-latest
    steps:
      - run: echo "Deploying ${{ github.event.client_payload.version }}"
```

I use it for controlled cross-repository orchestration, not as an open production deployment endpoint. The sender needs the right repository permission. The receiver validates the event type and payload. Environment protection still controls what reaches production.

GitHub limits how big the payload can be, so artifacts stay in a registry or artifact store. The event itself carries only metadata.

## 5. How would you trigger a CI/CD pipeline in Repo A from changes in Repo B?

**Answer:**

Say Repo B builds a shared library and Repo A deploys an application. My preferred flow is:

1. Repo B tests and publishes an immutable library or image version.
2. Repo B authenticates with a GitHub App token.
3. It sends a dispatch event to Repo A with the version, source commit, and correlation ID.
4. Repo A checks that the version exists and is approved.
5. Repo A runs its own tests and gets environment approval before deploying.

```bash
gh api --method POST repos/company/repo-a/dispatches \
  -f event_type=dependency-released \
  -F 'client_payload[version]=2.3.1' \
  -F 'client_payload[source_sha]=abc123'
```

I prevent loops by defining one-way ownership, add concurrency control per environment, and keep the workflow idempotent.

If Repo A only needs a dependency update, a pull request from Dependabot or an update bot is often safer. It goes through normal review instead of triggering a deployment directly.

## 6. What are GitHub Actions?

**Answer:**

GitHub Actions is GitHub's built-in automation platform, and it's event-driven. A workflow is a YAML file stored in `.github/workflows`. Events trigger workflows. Workflows contain jobs. Jobs run on runners. Each job has steps that run commands or reusable actions.

Actions can run CI/CD, scheduled maintenance, issue automation, releases, security scans, and infrastructure workflows. GitHub-hosted runners are convenient and short-lived, spun up fresh for each job. Self-hosted runners are useful when you need private network access or special software, but you have to patch them, isolate them, scale them, and clean them up yourself.

For production, I keep `permissions` scoped to the minimum needed — least privilege. I use protected environments, OIDC federation instead of long-lived cloud keys, actions pinned to trusted versions, concurrency controls, timeouts, artifact retention, and branch protection for workflow files.

## 7. How do you create a GitHub Actions workflow?

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

## 8. Why is GitHub Actions popular?

**Answer:**

It's popular because the automation lives right next to the code. It reacts directly to GitHub events, has a huge ecosystem of ready-made actions, supports both hosted and self-hosted runners, and integrates well with pull requests, environments, releases, packages, and GitHub's security features.

There are trade-offs, though. Hosted runners can't reach private systems without extra networking. Usage costs can add up. Untrusted marketplace actions carry supply-chain risk. Self-hosted runners need strong isolation and ongoing maintenance.

I choose GitHub Actions when the source already lives in GitHub and the workflow fits its security and runner model. I'd consider Jenkins, Azure Pipelines, GitLab CI, or a dedicated deployment controller instead when customization needs, network placement, governance, or existing platform investment point that way.
