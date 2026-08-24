## 1. How do you integrate vulnerability scanning in CI/CD pipelines?

**Answer:** Run static scans like Snyk or Trivy during the build. Fail the build if it finds critical CVEs, and automatically create a ticket to fix them.

Mini-case: Trivy caught a CVE in a base image. The pipeline failed, and developers patched the image before it went out.

**Detailed interview approach:**
I protect the whole path from source to production. That means branch protection and code review, pinned dependencies, actions, and plugins, and isolated ephemeral build runners.

Identities used by the pipeline are short-lived and least-privilege, meaning they only get the access they need for that one job. I run SAST, dependency, secret, IaC, and container scans, and generate an SBOM (a software bill of materials — a list of what's inside the build).

Images and artifacts are signed with provenance, meaning you can prove where they came from and how they were built. Registries are protected, and deployment requires admission checks before anything runs.

Findings get an agreed severity and SLA. Exceptions are allowed, but only for a limited time, so the gate stays enforceable instead of becoming a rubber stamp.

If I suspect a compromise, I stop promotion right away. I revoke runner and signing credentials, isolate the affected artifacts, and preserve audit evidence. Then I rebuild from a trusted runner and source, and verify signatures before redeploying.

Regular patching, egress restrictions, audit retention, and recovery drills cover what scanners alone can't catch.

## 2. How do you monitor and enforce container image provenance across environments?

**Answer:** Require signed images and immutable tags — once a tag is created, it can't be changed. Every image needs an SBOM, and deployments are gated on the SBOM and on vulnerability thresholds.

Mini-case: A new release's SBOM showed a vulnerable dependency. The gate blocked deployment until the image was rebuilt with the dependency patched.

**Detailed interview approach:**
I protect the whole path from source to production. That means branch protection and code review, pinned dependencies, actions, and plugins, and isolated ephemeral build runners.

Identities used by the pipeline are short-lived and least-privilege. I run SAST, dependency, secret, IaC, and container scans, and generate an SBOM.

Images and artifacts are signed with provenance. Registries are protected, and deployment requires admission checks before anything runs.

Findings get an agreed severity and SLA. Exceptions are allowed, but only for a limited time, so the gate stays enforceable instead of becoming a rubber stamp.

If I suspect a compromise, I stop promotion right away. I revoke runner and signing credentials, isolate the affected artifacts, and preserve audit evidence. Then I rebuild from a trusted runner and source, and verify signatures before redeploying.

Regular patching, egress restrictions, audit retention, and recovery drills cover what scanners alone can't catch.

## 3. How do you manage secrets scanning and prevention of accidental commits?

**Answer:** Use pre-commit hooks like git-secrets, CI scanning for secrets, and push-blocking hooks in company repos. Rotate any secret that gets found, and train developers to avoid this.

Mini-case: A developer accidentally committed an API key. The pre-commit hook blocked the push locally. When they tried again, the CI scan caught it and auto-rotated the leaked key.

**Detailed interview approach:**
Secrets belong in a secret manager such as Vault, Key Vault, or the CI credential store. They should never live in Git, YAML files, container images, command arguments, or build artifacts.

Each job gets a short-lived identity and fetches only the secret it needs for that stage. Masking log output is a secondary control, not the main one — an encoded or transformed value can still leak.

Rotation uses an overlap period. I issue the new value, update consumers, verify it works, then revoke the old value and check for anything that failed.

If a scan finds a secret that was already committed, I revoke it immediately. I check where it was used, remove it from active history where appropriate, and rotate any downstream credentials — just deleting the line from the file is not enough.

Pre-commit and server-side scans, protected logs, least privilege, expiry, and rotation tests all help prevent it happening again.

## 4. How do you implement end-to-end supply-chain security for container images?

**Answer:** Sign and verify images with Cosign. Scan images during the build with Trivy or Anchore. Use reproducible builds, enforce image provenance in registries, and block unsigned or vulnerable images in the pipeline.

Mini-case: In a pipeline, I added a build step that runs Trivy, then Cosign signs the image on success.

The registry policy rejects any image without a valid signature — preventing a compromised build from reaching prod.

**Detailed interview approach:**
I protect the whole path from source to production. That means branch protection and code review, pinned dependencies, actions, and plugins, and isolated ephemeral build runners.

Identities used by the pipeline are short-lived and least-privilege. I run SAST, dependency, secret, IaC, and container scans, and generate an SBOM.

Images and artifacts are signed with provenance. Registries are protected, and deployment requires admission checks before anything runs.

Findings get an agreed severity and SLA. Exceptions are allowed, but only for a limited time, so the gate stays enforceable instead of becoming a rubber stamp.

If I suspect a compromise, I stop promotion right away. I revoke runner and signing credentials, isolate the affected artifacts, and preserve audit evidence. Then I rebuild from a trusted runner and source, and verify signatures before redeploying.

Regular patching, egress restrictions, audit retention, and recovery drills cover what scanners alone can't catch.

## 5. How do you secure CI/CD pipelines from supply chain attacks?

**Answer:** Pin dependencies → Verify container/image signatures (Cosign) → Scan dependencies → Restrict external plugin usage.

**Detailed interview approach:**
I protect the whole path from source to production. That means branch protection and code review, pinned dependencies, actions, and plugins, and isolated ephemeral build runners.

Identities used by the pipeline are short-lived and least-privilege. I run SAST, dependency, secret, IaC, and container scans, and generate an SBOM.

Images and artifacts are signed with provenance. Registries are protected, and deployment requires admission checks before anything runs.

Findings get an agreed severity and SLA. Exceptions are allowed, but only for a limited time, so the gate stays enforceable instead of becoming a rubber stamp.

If I suspect a compromise, I stop promotion right away. I revoke runner and signing credentials, isolate the affected artifacts, and preserve audit evidence. Then I rebuild from a trusted runner and source, and verify signatures before redeploying.

Regular patching, egress restrictions, audit retention, and recovery drills cover what scanners alone can't catch.

## 6. How do you enforce code quality checks before merging in CI/CD?

**Answer:** Add mandatory linting, unit tests, SonarQube scans in Jenkins/GitHub Actions → Fail build if checks don’t pass → Protect main branch with approval rules.

**Detailed interview approach:**
I protect the whole path from source to production. That means branch protection and code review, pinned dependencies, actions, and plugins, and isolated ephemeral build runners.

Identities used by the pipeline are short-lived and least-privilege. I run SAST, dependency, secret, IaC, and container scans, and generate an SBOM.

Images and artifacts are signed with provenance. Registries are protected, and deployment requires admission checks before anything runs.

Findings get an agreed severity and SLA. Exceptions are allowed, but only for a limited time, so the gate stays enforceable instead of becoming a rubber stamp.

If I suspect a compromise, I stop promotion right away. I revoke runner and signing credentials, isolate the affected artifacts, and preserve audit evidence. Then I rebuild from a trusted runner and source, and verify signatures before redeploying.

Regular patching, egress restrictions, audit retention, and recovery drills cover what scanners alone can't catch.

## 7. How do you enforce security scans in CI/CD?

**Answer:** Add SAST (code scan with SonarQube) and DAST (OWASP ZAP) → Container image scans (Trivy/Anchore) → IaC scans (Checkov, tfsec).

**Detailed interview approach:**
I protect the whole path from source to production. That means branch protection and code review, pinned dependencies, actions, and plugins, and isolated ephemeral build runners.

Identities used by the pipeline are short-lived and least-privilege. I run SAST, dependency, secret, IaC, and container scans, and generate an SBOM.

Images and artifacts are signed with provenance. Registries are protected, and deployment requires admission checks before anything runs.

Findings get an agreed severity and SLA. Exceptions are allowed, but only for a limited time, so the gate stays enforceable instead of becoming a rubber stamp.

If I suspect a compromise, I stop promotion right away. I revoke runner and signing credentials, isolate the affected artifacts, and preserve audit evidence. Then I rebuild from a trusted runner and source, and verify signatures before redeploying.

Regular patching, egress restrictions, audit retention, and recovery drills cover what scanners alone can't catch.


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

Integration tests run after deploying to the dev EKS cluster. GitHub Actions uses OIDC-based access to invoke tests against the deployed endpoints.

End-to-end tests with Cypress run in dedicated GitHub Actions runners with browser capabilities, targeting staging after deployment. Test results and artifacts get uploaded for review.

ArgoCD deployments include readiness gates that verify system health before the deployment completes. Failed tests in GitHub Actions automatically create an issue for developers, with a link to the run and its logs.

## 10. How do you ensure integration tests work across different environments?

**Answer:** Tests read config from env vars/Terraform outputs → Kubernetes Jobs seed fixtures → Wiremock for external dependencies → env-specific databases via Terraform + migrations → cleanup jobs → ArgoCD keeps consistent app state.

**Detailed interview approach:**
I structure integration tests to read configuration from environment variables injected by GitHub Actions workflows. Each test job pulls environment-specific endpoints from Terraform outputs and EKS service discovery.

Test data is managed through Kubernetes Jobs that seed test fixtures before test execution.

For external dependencies, I use Wiremock containers deployed alongside the application to give consistent responses. Database tests run against environment-specific databases provisioned by Terraform, with migrations applied to keep the schema compatible.

After tests complete, cleanup jobs remove test data, and ArgoCD ensures consistent application state across environments, making integration tests reliable across the pipeline.
