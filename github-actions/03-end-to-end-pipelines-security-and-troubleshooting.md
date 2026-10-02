# GitHub Actions: End-to-End Pipelines, Security, and Troubleshooting

> A full CI/CD pattern to EKS with Terraform, SonarQube/Docker/Trivy integration, and common workflow failures.

## Key Concepts

### CI/CD Workflow Pattern

A production workflow commonly runs, in order: checkout, language/tool setup, dependency caching, build, unit tests, test-report upload, code and security checks, Docker build, registry login through short-lived identity, image push by digest, deployment, rollout verification, and notification.

Matrices test multiple supported versions at once. Reusable workflows keep multiple pipelines in sync and prevent copy-paste drift.

### End-to-End GitHub Actions, Terraform, EKS, and Kubernetes Project

**Architecture:**

- Modular Terraform provisions a VPC, public/private subnets, routes, security controls, IAM roles, and an EKS cluster.
- Terraform state uses a remote backend that is encrypted, versioned, and locked. Production applies need approval and use short-lived identity.
- A Node.js application is built into a small container image. It's published with a commit-SHA tag or digest, so the image is immutable, meaning it never changes after it's created. That way the exact image that gets tested is the one that gets deployed.
- Kubernetes manifests use Kustomize overlays for environment differences and define Deployments, Services, Ingress, probes, and resource limits.
- Prometheus and Grafana provide cluster and application monitoring.

**GitHub Actions flow:**

```text
pull request → lint/test → Terraform and manifest validation → security scans
merge → build image → Trivy scan → sign/publish digest
      → update/deploy desired state → rollout and application verification
```

The workflow uses GitHub OIDC federation instead of stored cloud access keys. Third-party actions are pinned to trusted versions or commit SHAs. Production environments are restricted, and untrusted pull requests never get deployment credentials. The image that gets tested is the same image that gets deployed.

When something fails, I check the first failed job, then the runner and action version, OIDC claims and IAM trust, registry authentication, the Terraform plan and state, EKS endpoint connectivity, Kubernetes events, Ingress health, and monitoring dashboards.

I only retry a job when it's idempotent, meaning safe to run more than once, and when I know the underlying cause was temporary.

### Common Failures

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

## Interview Questions

### 1. How are SonarQube, Docker, and Trivy integrated in pipelines?

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
