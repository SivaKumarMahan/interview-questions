# DevSecOps Summary

**DevSecOps** integrates security evidence and controls throughout delivery instead of treating security as a final scan.

## Secure CI and GitOps Delivery Flow

```text
pull request -> tests and quality checks -> dependency/SAST/secret/IaC scans
-> image build -> container scan, SBOM, signing -> immutable (not changed after creation) registry
-> reviewed GitOps manifest update -> Argo CD/Flux reconciliation (making actual state match desired state)
-> Kubernetes admission/runtime controls -> observability and response
```

- **OWASP Dependency-Check** or an equivalent tool identifies known vulnerable third-party dependencies.
- **SonarQube** analyzes maintainability, bugs, and configured security rules; its quality gate is one signal, not proof that code is secure.
- **Trivy** or an equivalent scanner examines filesystems, dependencies, IaC, and container images according to the selected mode.
- CI publishes an immutable (not changed after creation) image digest only after required evidence passes; exceptions are risk-owned, approved, time-limited, and tracked.
- CI updates the reviewed deployment repository, while **Argo CD** or **Flux** pulls desired state into Kubernetes. CI does not need broad cluster credentials in this model.
- **Prometheus**, **Grafana**, and centralized logs and traces verify the release; alert routing creates an operational feedback loop.

Pin pipeline dependencies, protect credentials through short-lived identity, generate and retain an SBOM and provenance (where an artifact came from and how it was built), sign artifacts, enforce admission policy, separate duties, and regularly test rollback and incident response.

Scanners reduce risk but do not replace threat modeling, secure design, patching, runtime hardening, or human review.

## Azure Secure Container Delivery Example

```text
GitHub protected branch and pull request
  -> GitHub Actions build, tests, SAST, dependency and secret scans
  -> build image and generate SBOM
  -> Trivy policy scan
  -> sign and publish immutable (not changed after creation) digest to ACR
  -> Azure DevOps protected production environment
  -> approval, branch/policy/health checks
  -> deploy digest to AKS
  -> Defender for Containers + Azure Monitor
  -> verify, promote or roll back
```

This is defense in depth:

- **Trivy in CI** gives fast feedback before promotion and can fail the build according to an agreed severity and exception policy.
- **ACR** stores the immutable (not changed after creation) image and associated supply-chain evidence.
- **Azure DevOps approvals and checks** protect the production resource independently of pipeline YAML.
- **Azure Key Vault and workload identity** prevent application and deployment credentials from being stored in code or images.
- **Defender for Containers** adds registry/running-image vulnerability assessment, posture recommendations and runtime security signals according to the enabled plan and extensions.
- **AKS controls** such as least-privilege (minimum required access) RBAC, network policy, workload identity, restrictive security contexts and image/admission policy limit runtime exposure.

Do not scan only `latest`: deploy and scan the same digest. A new vulnerability database finding after deployment also requires continuous reassessment, ownership, fix deadlines and a tested emergency release path.

## Common DevSecOps Scanners

- **TFLint** validates Terraform style/provider rules and catches common IaC mistakes.
- **Checkov** evaluates IaC against security and compliance policies.
- **SonarQube** performs static code analysis for bugs, vulnerabilities and maintainability issues.
- **Trivy** scans container images, filesystems, SBOMs and supported IaC for vulnerabilities/misconfiguration.
- **OWASP Dependency-Check** identifies known-vulnerable third-party libraries.
- **Gitleaks** detects committed secrets; it should run pre-commit and in CI, but exposed credentials must still be revoked and rotated.
- **Snyk** provides code, dependency, container and IaC vulnerability monitoring.

Pin scanner versions and policy baselines, scan pull requests and release artifacts, triage findings by exploitability and business context, and define an exception expiry/owner. A passing scan is a control signal—not proof that a release is secure.
