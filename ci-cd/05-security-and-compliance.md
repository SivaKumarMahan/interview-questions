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
