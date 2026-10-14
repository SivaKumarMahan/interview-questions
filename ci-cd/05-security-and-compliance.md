# CI/CD: Security and Compliance

> Code quality and security scanning, vulnerability management, secrets, supply-chain protection, auditability, and multi-tenant isolation.

## Interview Questions

<details><summary>Q1. [Intermediate] How do you integrate code-quality tools like SonarQube?</summary>

**Answer:**

I run unit tests and coverage first, then send the source and coverage data to SonarQube. The pipeline waits for the quality gate and blocks publication if the agreed thresholds aren't met.

The gate checks new-code bugs, vulnerabilities, coverage, duplication, and maintainability. I focus the gate on new code so legacy debt doesn't block adoption, and I set up a separate fix plan for older issues.

Tokens are stored securely, and I make sure the scanner and server versions are compatible.

I keep the report link on the pull request. If something's a false positive, it gets a reviewed exception with a reason and an expiry — developers don't just disable the rule. I also test the gate against a known failing branch to make sure it actually blocks.

</details>

<details><summary>Q2. [Basic] What security tools and scans do you use in pipelines?</summary>

**Answer:**

I use layered controls:

- Secret scanning before or at commit
- SAST for source code
- Software composition analysis and license checks
- IaC and Kubernetes policy scanning
- Container image and SBOM scanning
- DAST against a deployed test environment
- Artifact and image signing, with verification at admission

Findings get prioritized by severity, exploitability, exposure, and environment. High-risk failures block promotion, and any exception needs an owner and an expiry date. Tools run with least privilege — only the access they need — and reports are checked to avoid leaking secrets.

Scanning alone isn't complete security. Protected branches, isolated runners, pinned dependencies and actions, workload identity, runtime monitoring, patching, and an incident response plan are all still necessary.

</details>

<details><summary>Q3. [Basic] What SAST and DAST tools do you prefer?</summary>

**Answer:**

SonarQube, CodeQL, Checkmarx, and Semgrep are common SAST tools. OWASP ZAP and Burp Suite Enterprise are common DAST tools. The right choice depends on languages, framework support, accuracy, CI integration, compliance needs, and who owns the tool.

SAST runs early against source code. DAST tests a running, authorized, non-production target, and needs its rate and scope controlled. I combine both with dependency, secret, IaC, container, and runtime controls.

I tune the rules, keep evidence, set severity gates with expiring exceptions, and track the true-positive and fix rate. No single scanner proves an application is secure.

</details>

<details><summary>Q4. [Intermediate] How do you manage code vulnerabilities?</summary>

**Answer:**

The flow is: discover, validate, prioritize, assign an owner and SLA, remediate or formally accept, rescan, then monitor. I confirm the package, version, and whether the vulnerable code path is actually reachable and used.

The fix might mean updating a library or base image, removing a package, adding a compensating control, or fixing the code directly.

I test for regressions, rebuild the artifact — keeping it immutable — and deploy it progressively. Any exception has to document the business reason, the compensating control, the approver, and an expiry date.

I track metrics like the age of open critical findings, time to fix, recurrence, and false-positive rate.

For an actively exploited issue, I identify which releases are affected, block new deployments, patch and rebuild, rotate any exposed secrets, watch for indicators of compromise, and keep people updated on status.

</details>

<details><summary>Q5. [Intermediate] How do you securely store secrets in CI/CD pipelines?</summary>

**Answer:**

I prefer OIDC or workload identity, so jobs get short-lived cloud credentials instead of long-lived keys. Other secrets live in Vault or a platform secret store, and only the protected job or environment that needs them can see them.

I make sure secrets never end up in Git, YAML, artifacts, cache, Docker layers, command arguments, or logs. Runners are isolated and ephemeral, permissions follow least privilege, and access and rotation get audited. Masking log output is a backup control, not the actual security boundary.

I test that forked or unprotected pipelines can't reach production secrets. If a secret does leak, I revoke and rotate it first, check audit logs and downstream access, remove any retained output, and fix the pipeline.

</details>

<details><summary>Q6. [Advanced] How do you secure pipelines against supply-chain attacks?</summary>

**Answer:**

I protect source and pipeline changes with code review and branch policy. I pin third-party actions, images, and dependencies to specific versions. I restrict runner egress and permissions, isolate untrusted builds, use short-lived identity, and block secrets from reaching fork jobs.

Builds generate SBOMs, scan dependencies, images, and IaC, and sign artifacts using a protected identity. Deployment checks the signature and provenance — meaning where the artifact came from and how it was built — and only deploys artifacts by their fixed digest. Registries are protected and audited.

I review transitive dependencies, runner images, who owns each plugin or action, and the artifact promotion path. My incident plan covers revoking signing credentials, blocking compromised artifacts, identifying which versions are deployed, rebuilding from trusted sources, and rotating any affected secrets.

</details>

<details><summary>Q7. [Advanced] How do you make CI/CD pipelines auditable for compliance?</summary>

**Answer:**

Pipeline definitions and infrastructure code are version-controlled and reviewed. Protected branches and environments, identities with least privilege, separation of duties, and immutable artifacts all build in traceability.

For every release I retain the commit, the pull request and its reviewers, test/scan/policy results, the artifact's digest/signature/SBOM, approvals, deployment logs, the environment and config version, and the verification or rollback result. Logs follow a defined retention period and sit in tamper-resistant storage with restricted access.

I map this evidence to the actual control requirements, and I test that emergency or bypass paths are still audited. Good compliance automation makes the approved path the easy path — manual screenshots are fragile and easy to miss things with.

</details>

<details><summary>Q8. [Advanced] How do you handle multi-tenant CI/CD pipelines? <em>(scenario)</em></summary>

**Answer:** Isolate jobs by namespace or project, use separate credentials, and apply RBAC per team.

**Detailed interview approach:**
I isolate tenants by repository, project, credential scope, runner pool or namespace, cache and artifact path, quota, and deployment environment. Untrusted tenant code can't run on a shared privileged agent, and can't read another tenant's workspace, secrets, logs, or cache.

Jobs run in ephemeral sandboxes, as non-root containers, with restricted network egress, workload identity, and per-tenant concurrency and resource limits. Shared templates are versioned centrally, but changes are compatibility-tested and rolled out gradually.

Audit events carry the tenant and actor identity, so usage and cost can be attributed correctly. High-security or mutually untrusted tenants get dedicated runners or clusters, because namespace or container boundaries alone might not meet the threat model.

</details>

<details><summary>Q9. [Intermediate] How do security checks work in CI/CD? <em>(asked in interview round)</em></summary>

**Answer:**

Security checks are automated stages in the pipeline that scan the code, dependencies, secrets, infrastructure code and container images on every change. This is "shift left" (DevSecOps): find issues in the pull request, not in production. Each check has a policy, for example "fail the build on any Critical or High vulnerability".

**Types of checks:**

| Check | What it finds | Example tools |
|-------|---------------|---------------|
| Secret scanning | Passwords, keys, tokens in code | `gitleaks`, GitHub secret scanning |
| SAST | Insecure code patterns (SQL injection, XSS) | SonarQube, CodeQL, Semgrep |
| SCA / dependency scan | Vulnerable open-source libraries | Dependabot, Snyk, OWASP Dependency-Check |
| IaC scan | Insecure Terraform/Kubernetes config | Checkov, `tfsec`/Trivy, `kics` |
| Container image scan | CVEs in base image and packages | Trivy, `grype`, Defender for Containers |
| DAST | Runtime vulnerabilities in a running app | OWASP ZAP |
| Signing and SBOM | Supply-chain integrity | Cosign, Syft |

**Flow:**

```text
PR opened
   |
   v
Secret scan -> SAST -> SCA -> IaC scan
   |  (fail PR on High/Critical)
   v
Build image -> image scan -> SBOM + sign -> push
   |
   v
Deploy to test -> DAST -> approval -> production
   |
   v
Admission policy (only signed, scanned images) + runtime monitoring
```

**Example (Trivy gate in GitHub Actions):**

```yaml
- name: Scan image
  uses: aquasecurity/trivy-action@0.28.0
  with:
    image-ref: myregistry.azurecr.io/web:${{ github.sha }}
    severity: CRITICAL,HIGH
    exit-code: "1"          # non-zero exit fails the job
    ignore-unfixed: true
```

**Important points:**

- A scan only protects you if it can fail the build (quality gate); report-only scans are often ignored.
- Use branch protection so PRs cannot merge until checks pass.
- Pipeline credentials should use OIDC/workload identity and least privilege, not long-lived secrets.
- Handle false positives with a documented, time-limited exception, not by disabling the scanner.

See also: [CI/CD security and compliance](../ci-cd/05-security-and-compliance.md), [DevSecOps](../ops/02-devsecops.md).

**Interview-ready answer:**

> "I add security checks as automated stages so every change is scanned before it can merge. On the pull request I run secret scanning, SAST with SonarQube or CodeQL, a dependency scan for vulnerable libraries and an IaC scan with Checkov for Terraform. After the image is built I scan it with Trivy, generate an SBOM and sign it. Each scan has a quality gate, for example the build fails on any Critical or High finding, and branch protection blocks the merge until checks pass. In the test environment I can run DAST with OWASP ZAP. The pipeline itself uses OIDC and least-privilege credentials, so the pipeline is not a security risk."

</details>

<details><summary>Q10. [Intermediate] How do you configure quality gates? <em>(asked in interview round)</em></summary>

**Answer:**

A quality gate is an **automated pass/fail condition** that stops the pipeline when code, tests or security don't meet agreed thresholds. The important part is that the pipeline actually **fails** on a red gate, and that the branch cannot be merged without it.

**Typical gates:**

| Gate | Tool | Fails when |
| --- | --- | --- |
| Unit tests | Maven/Gradle, `pytest`, Jest | Any test fails |
| Coverage | `JaCoCo`, `pytest-cov` | Coverage below threshold (for example 80% on new code) |
| Code quality | SonarQube quality gate | New bugs, vulnerabilities, not-yet-reviewed security hotspots, duplication, coverage on new code |
| Dependencies | OWASP Dependency-Check, Snyk | CVSS above threshold |
| Container image | Trivy, `Grype` | HIGH/CRITICAL fixable vulnerabilities |
| IaC | `Checkov`, `tfsec`/Trivy config | Misconfigurations (public S3, open SGs) |
| Secrets | `Gitleaks` | Secret found |
| Merge | Branch protection / rulesets | Required checks not green, no review |

**SonarQube: make the pipeline wait for the gate:**

1. Define the gate in SonarQube (for example "Sonar way" or a custom gate: coverage on new code at least 80%, no new critical issues, all hotspots reviewed) and assign it to the project.
2. In the pipeline, block until the result is known.

**Scanner property (any CI):**

```bash
mvn -B verify sonar:sonar \
  -Dsonar.qualitygate.wait=true \
  -Dsonar.qualitygate.timeout=300
```

**Jenkins (requires a SonarQube webhook to `https://jenkins.example.com/sonarqube-webhook/`):**

```groovy
stage('SonarQube analysis') {
  steps {
    withSonarQubeEnv('sonarqube') {
      sh 'mvn -B verify sonar:sonar'
    }
  }
}
stage('Quality gate') {
  steps {
    timeout(time: 10, unit: 'MINUTES') {
      waitForQualityGate abortPipeline: true
    }
  }
}
```

**Other gates as commands:**

```bash
# Coverage threshold (Python)
pytest --cov=app --cov-fail-under=80

# Image scan: fail on fixable HIGH/CRITICAL
trivy image --exit-code 1 --severity HIGH,CRITICAL --ignore-unfixed myrepo/orders:${GIT_SHA}

# Secret scan
gitleaks detect --source . --exit-code 1
```

For Maven, the `JaCoCo` `check` goal with a `COVEREDRATIO` rule fails the build below the minimum.

**Enforce at merge time:**

In GitHub branch protection or rulesets (or Azure Repos branch policies), mark the CI job and SonarQube check as **required status checks**, require pull request reviews and block force pushes. That makes the gate mandatory, not advisory.

**Important points:**

- Apply strict thresholds to **new code** so legacy debt doesn't block every build, then improve gradually.
- Exceptions (for example `.trivyignore` entries) need an owner, reason and expiry date.
- Keep gates fast; slow gates push teams to bypass them.

See also: [CI/CD security and compliance](../ci-cd/05-security-and-compliance.md), [Sample pipelines](../repetitive-questions/sample-pipelines-examples.md).

**Interview-ready answer:**

> "I define quality gates as automated pass/fail checks at each stage: unit tests must pass, coverage on new code must be at least 80%, the SonarQube quality gate must be green, and Trivy must find no fixable high or critical vulnerabilities. In SonarQube I create a gate focused on new code and make the pipeline wait for it, using `sonar.qualitygate.wait=true` or, in Jenkins, `waitForQualityGate abortPipeline: true` with a webhook. Trivy runs with `--exit-code 1`, and coverage uses `JaCoCo` `check` or `--cov-fail-under`. Then I make these checks required in branch protection so nobody can merge with a failing gate. Any exception is documented with an owner and an expiry date."

</details>

<details><summary>Q11. [Advanced] How do you secure pipelines against supply chain attacks? <em>(asked in interview round)</em></summary>

**Answer:**

A supply chain attack compromises something you trust: a dependency, a base image, a build tool, a CI plugin or the pipeline itself. Defense covers inputs, the build and the outputs.

| Area | Controls |
| --- | --- |
| Source | Branch protection, required reviews, signed commits, `CODEOWNERS` for pipeline files |
| Dependencies | Lock files, pinned versions, private proxy registry, SCA scanning, Dependabot or Renovate |
| CI | Actions pinned to full commit SHAs, least-privilege tokens, OIDC instead of long-lived keys, ephemeral runners |
| Artifacts | SBOM (Syft), vulnerability scan (Trivy), signing with Sigstore `cosign`, SLSA provenance |
| Deploy | Admission policy that only allows signed images from approved registries |

```yaml
permissions:
  contents: read
  id-token: write   # OIDC to the cloud, no stored secrets
steps:
  - uses: actions/checkout@<full-40-char-commit-sha> # pin, do not use a tag
```

**Interview-ready answer:**

> I treat everything that enters the build as untrusted. Dependencies are locked and pulled through a private proxy, third-party actions are pinned to commit SHAs, and the pipeline uses OIDC with least-privilege permissions instead of stored cloud keys. Every image gets an SBOM, a vulnerability scan and a `cosign` signature with provenance. At deploy time an admission policy rejects any image that is unsigned or comes from an unapproved registry.

See also: [Secure pipelines against supply chain attacks](../ops/02-devsecops.md), [Security scanning and supply chain](../testing-tools/02-security-scanning-and-supply-chain.md)

</details>
