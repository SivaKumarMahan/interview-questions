## 1. How do you integrate vulnerability scanning in CI/CD pipelines?

**Answer:** Run static scans (Snyk, Trivy) during build, fail builds with critical CVEs, and automatically create tickets for fix. Mini-case: Trivy caught a base image CVE; pipeline failed and developers patched the image before deployment.

**Detailed interview approach:**
I protect the path from source to production: branch protection and review, pinned dependencies/actions/plugins, isolated ephemeral runners, short-lived least-privilege (minimum required access) identity, SAST/dependency/secret/IaC/container scans, SBOM generation, signed provenance (where an artifact came from and how it was built) and artifacts, protected registries, and deployment admission verification.

Findings have an agreed severity/SLA and a time-limited exception process so gates are both enforceable and usable.

If compromise is suspected, I stop promotion, revoke runner and signing credentials, isolate artifacts, preserve audit evidence, rebuild from a trusted runner/source, and verify signatures before redeployment.

Regular patching, egress restrictions, audit retention, and recovery exercises cover the controls scanners cannot.

## 2. How do you monitor and enforce container image provenance (where an artifact came from and how it was built) across environments?

**Answer:** Enforce signed images and immutable (not changed after creation) tags, require SBOMs (software bill of materials) on each image, and gate deployments based on SBOM and vulnerability thresholds.

Mini-case: A new release’s SBOM showed a vulnerable dependency; gate logic prevented deployment until the image was rebuilt with patched dependency.
**Detailed interview approach:**
I protect the path from source to production: branch protection and review, pinned dependencies/actions/plugins, isolated ephemeral runners, short-lived least-privilege (minimum required access) identity, SAST/dependency/secret/IaC/container scans, SBOM generation, signed provenance (where an artifact came from and how it was built) and artifacts, protected registries, and deployment admission verification.

Findings have an agreed severity/SLA and a time-limited exception process so gates are both enforceable and usable.

If compromise is suspected, I stop promotion, revoke runner and signing credentials, isolate artifacts, preserve audit evidence, rebuild from a trusted runner/source, and verify signatures before redeployment.

Regular patching, egress restrictions, audit retention, and recovery exercises cover the controls scanners cannot.

## 3. How do you manage secrets scanning and prevention of accidental commits?

**Answer:** Use pre-commit hooks (git-secrets), CI scanning for secrets, and push-blocking hooks in company repos; rotate any found secrets and enforce developer training.

Mini-case: A developer accidentally committed an API key; pre-commit hook blocked the push locally and the CI scan caught a subsequent attempt and auto-rotated the leaked key.
**Detailed interview approach:**
Secrets belong in Vault, Key Vault, Secret Manager, or the CI credential store, not Git, YAML, images, command arguments, or artifacts. Jobs obtain a short-lived identity and fetch only the secret needed for that stage; masking is a secondary control because encoded or transformed values can still leak.

Rotation uses an overlap period: issue new value, update consumers, verify, revoke old value, and audit failures. If scanning finds a committed secret, I revoke it immediately, inspect usage, remove it from active history where appropriate, and rotate downstream credentials—deleting the line is not sufficient.

Pre-commit/server-side scans, protected logs, least privilege (only the permissions needed), expiry, and rotation tests prevent recurrence.

## 4. How do you implement end-to-end supply-chain security for container images?

**Answer:** Sign and verify images (Cosign), scan images during build (Trivy/Anchore), use reproducible builds, enforce image provenance (where an artifact came from and how it was built) in registries, and block unsigned or vulnerable images in the pipeline.

Mini-case: In a pipeline, I added a build step that runs Trivy, then Cosign signs the image on success.

The registry policy rejects any image without a valid signature — preventing a compromised build from reaching prod.

**Detailed interview approach:**
I protect the path from source to production: branch protection and review, pinned dependencies/actions/plugins, isolated ephemeral runners, short-lived least-privilege (minimum required access) identity, SAST/dependency/secret/IaC/container scans, SBOM generation, signed provenance (where an artifact came from and how it was built) and artifacts, protected registries, and deployment admission verification.

Findings have an agreed severity/SLA and a time-limited exception process so gates are both enforceable and usable.

If compromise is suspected, I stop promotion, revoke runner and signing credentials, isolate artifacts, preserve audit evidence, rebuild from a trusted runner/source, and verify signatures before redeployment.

Regular patching, egress restrictions, audit retention, and recovery exercises cover the controls scanners cannot.

## 5. How do you secure CI/CD pipelines from supply chain attacks?

**Answer:** Pin dependencies → Verify container/image signatures (Cosign) → Scan dependencies → Restrict external plugin usage.

**Detailed interview approach:**
I protect the path from source to production: branch protection and review, pinned dependencies/actions/plugins, isolated ephemeral runners, short-lived least-privilege (minimum required access) identity, SAST/dependency/secret/IaC/container scans, SBOM generation, signed provenance (where an artifact came from and how it was built) and artifacts, protected registries, and deployment admission verification.

Findings have an agreed severity/SLA and a time-limited exception process so gates are both enforceable and usable.

If compromise is suspected, I stop promotion, revoke runner and signing credentials, isolate artifacts, preserve audit evidence, rebuild from a trusted runner/source, and verify signatures before redeployment.

Regular patching, egress restrictions, audit retention, and recovery exercises cover the controls scanners cannot.

## 6. How do you enforce code quality checks before merging in CI/CD?

**Answer:** Add mandatory linting, unit tests, SonarQube scans in Jenkins/GitHub Actions → Fail build if checks don’t pass → Protect main branch with approval rules.

**Detailed interview approach:**
I protect the path from source to production: branch protection and review, pinned dependencies/actions/plugins, isolated ephemeral runners, short-lived least-privilege (minimum required access) identity, SAST/dependency/secret/IaC/container scans, SBOM generation, signed provenance (where an artifact came from and how it was built) and artifacts, protected registries, and deployment admission verification.

Findings have an agreed severity/SLA and a time-limited exception process so gates are both enforceable and usable.

If compromise is suspected, I stop promotion, revoke runner and signing credentials, isolate artifacts, preserve audit evidence, rebuild from a trusted runner/source, and verify signatures before redeployment.

Regular patching, egress restrictions, audit retention, and recovery exercises cover the controls scanners cannot.

## 7. How do you enforce security scans in CI/CD?

**Answer:** Add SAST (code scan with SonarQube) and DAST (OWASP ZAP) → Container image scans (Trivy/Anchore) → IaC scans (Checkov, tfsec).

**Detailed interview approach:**
I protect the path from source to production: branch protection and review, pinned dependencies/actions/plugins, isolated ephemeral runners, short-lived least-privilege (minimum required access) identity, SAST/dependency/secret/IaC/container scans, SBOM generation, signed provenance (where an artifact came from and how it was built) and artifacts, protected registries, and deployment admission verification.

Findings have an agreed severity/SLA and a time-limited exception process so gates are both enforceable and usable.

If compromise is suspected, I stop promotion, revoke runner and signing credentials, isolate artifacts, preserve audit evidence, rebuild from a trusted runner/source, and verify signatures before redeployment.

Regular patching, egress restrictions, audit retention, and recovery exercises cover the controls scanners cannot.


## 8. What types of testing do you include in your CI/CD pipeline, and at what stages do they run?

**Answer:** Unit tests on every commit with coverage → Trivy image scan after build → integration tests in dev → `terraform plan` validation → e2e (Cypress) + performance (k6) in staging → post-deploy smoke tests → required PR checks + ArgoCD health gates.
**Detailed interview approach:**
The GitHub Actions workflow includes multiple testing stages. Unit tests run on every commit using language-specific frameworks with coverage enforcement.

After building container images, I conduct security scanning with Trivy. For deployments to dev, the pipeline runs integration tests against the deployed APIs.

Terraform plan validation runs before any infrastructure changes are applied. In staging, I execute end-to-end tests with Cypress and performance tests using k6.

Post-deployment smoke tests verify core functionality in every environment. Each test stage is a required check in GitHub pull requests, and failures block promotion to higher environments.

ArgoCD's health checks provide an additional validation layer after deployment.

## 9. How do you automate unit, integration, and end-to-end tests in your pipeline?

**Answer:** GitHub Actions automates all layers → unit tests in build stage → integration tests against dev EKS via OIDC → Cypress e2e against staging → artifacts uploaded → ArgoCD readiness gates → failed tests auto-create issues.

**Detailed interview approach:**
GitHub Actions workflows automate all testing. Unit tests run in the build stage, triggered on every push, using workspace-mounted volumes for test reports and coverage data.

Integration tests run after deploying to the dev EKS cluster, with GitHub Actions having OIDC-based access to invoke tests against deployed endpoints.

End-to-end tests using Cypress run in dedicated GitHub Actions runners with browser capabilities, targeting staging environments after deployment. Test results and artifacts are uploaded to GitHub Actions artifacts for review.

ArgoCD deployments include readiness gates that verify system health before completing the deployment, and failed tests in GitHub Actions automatically create issues for developers to address, with links to the specific runs and logs.

## 10. How do you ensure integration tests work across different environments?

**Answer:** Tests read config from env vars/Terraform outputs → Kubernetes Jobs seed fixtures → Wiremock for external dependencies → env-specific databases via Terraform + migrations → cleanup jobs → ArgoCD keeps consistent app state.

**Detailed interview approach:**
I structure integration tests to read configuration from environment variables injected by GitHub Actions workflows. Each test job pulls environment-specific endpoints from Terraform outputs and EKS service discovery.

Test data is managed through Kubernetes Jobs that seed test fixtures before test execution.

For external dependencies, I use Wiremock containers deployed alongside the application in test environments to provide consistent responses. Database tests run against environment-specific databases provisioned by Terraform, using migrations to ensure schema compatibility.

After tests complete, cleanup jobs remove test data, and ArgoCD ensures consistent application state across environments, making integration tests reliable across the pipeline.
