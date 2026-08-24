# DevSecOps Summary

**DevSecOps** builds security checks and evidence into every stage of delivery, instead of running one big security scan at the end.

## Secure CI and GitOps Delivery Flow

```text
pull request -> tests and quality checks -> dependency/SAST/secret/IaC scans
-> image build -> container scan, SBOM, signing -> registry (image never changes once pushed)
-> reviewed GitOps manifest update -> Argo CD/Flux reconciliation (making the cluster match Git)
-> Kubernetes admission/runtime controls -> observability and response
```

- **OWASP Dependency-Check**, or a similar tool, flags third-party dependencies with known vulnerabilities.
- **SonarQube** checks maintainability, bugs, and configured security rules. Its quality gate is one useful signal, not proof the code is secure.
- **Trivy**, or a similar scanner, checks filesystems, dependencies, IaC, and container images depending on the mode you run it in.
- CI only publishes an image once it has passed the required checks, and once published that image digest never changes. Any exception needs an owner, approval, a time limit, and tracking.
- CI updates the reviewed deployment repository, and **Argo CD** or **Flux** pulls the desired state into Kubernetes from there. CI itself doesn't need broad cluster credentials in this setup.
- **Prometheus**, **Grafana**, and centralized logs and traces confirm the release is healthy, and alert routing closes the feedback loop.

Pin your pipeline's dependencies, protect credentials with short-lived identities, generate and keep an SBOM along with proof of how each artifact was built, sign artifacts, enforce admission policy, separate duties between people, and regularly test rollback and incident response.

Scanners reduce risk, but they don't replace threat modeling, secure design, patching, runtime hardening, or a human review.

## Azure Secure Container Delivery Example

```text
GitHub protected branch and pull request
  -> GitHub Actions build, tests, SAST, dependency and secret scans
  -> build image and generate SBOM
  -> Trivy policy scan
  -> sign and publish the image digest to ACR (it won't change after this)
  -> Azure DevOps protected production environment
  -> approval, branch/policy/health checks
  -> deploy digest to AKS
  -> Defender for Containers + Azure Monitor
  -> verify, promote or roll back
```

This is defense in depth — several independent layers of protection:

- **Trivy in CI** gives fast feedback before promotion, and can fail the build based on an agreed severity level and exception policy.
- **ACR** stores the image, which never changes after it's pushed, along with its supply-chain evidence.
- **Azure DevOps approvals and checks** protect the production environment independently of the pipeline's YAML.
- **Azure Key Vault and workload identity** keep application and deployment credentials out of code and images entirely.
- **Defender for Containers** adds vulnerability assessment for the registry and running images, posture recommendations, and runtime security signals, depending on the plan and extensions enabled.
- **AKS controls** such as RBAC scoped to only what's needed, network policy, workload identity, restrictive security contexts, and image/admission policy all limit what can go wrong at runtime.

Don't just scan `latest` — deploy and scan the exact same digest. A new vulnerability found after deployment also needs ongoing reassessment, a clear owner, a fix deadline, and a tested emergency release path.

## Common DevSecOps Scanners

- **TFLint** checks Terraform style and provider rules, and catches common IaC mistakes.
- **Checkov** checks IaC against security and compliance policies.
- **SonarQube** does static code analysis for bugs, vulnerabilities, and maintainability issues.
- **Trivy** scans container images, filesystems, SBOMs, and supported IaC for vulnerabilities and misconfiguration.
- **OWASP Dependency-Check** flags third-party libraries with known vulnerabilities.
- **Gitleaks** detects committed secrets. Run it pre-commit and in CI, but remember: a caught secret still needs to be revoked and rotated, not just deleted.
- **Snyk** covers code, dependency, container, and IaC vulnerability monitoring.

Pin your scanner versions and policy baselines, scan both pull requests and release artifacts, triage findings by how exploitable and how business-critical they are, and give every exception an owner and an expiry date. A passing scan is one signal — it doesn't prove a release is secure.
