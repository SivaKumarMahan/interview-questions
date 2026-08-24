# Scenario-Based Interview Notes

> Distributed from the former cross-topic scenario notes. Section numbering is retained where useful for interview practice.

## Security & DevSecOps

### 9.1 Preferred tools for SAST and DAST

- **SAST scans source code and dependencies without running the app:** SonarQube, Semgrep, Checkmarx, Snyk Code. For dependency scanning: OWASP Dependency-Check, Snyk, Dependabot. For IaC: tfsec, Checkov, Trivy. For secrets: gitleaks, trufflehog.
- **DAST scans the app while it's running:** OWASP ZAP, Burp Suite, Nikto.
- **Containers:** Trivy or Grype for image scanning. Run SAST early in CI, and run DAST against a deployed staging environment.

### 9.2 Secure pipelines against supply chain attacks

- **Pin and verify dependencies:** use lockfiles, pin by checksum/hash, and pin GitHub Actions to a commit SHA instead of a mutable tag.
- **Scan dependencies and images in CI** (Snyk/Trivy) to catch vulnerable or malicious packages.
- **Prove where artifacts came from, and sign them:** follow the SLSA framework, sign artifacts and images with **Sigstore/cosign**, generate an **SBOM** (Syft), and verify signatures before deploy.
- **Give CI only the access it needs:** short-lived OIDC tokens instead of long-lived secrets, scoped runner permissions, and isolated ephemeral runners.
- **Protect the pipeline itself:** branch protection, required reviews, secret scanning, trusted internal registries/proxies, and audit logging.

### 9.3 Enforce pipeline security from Git to deployment

- **Source:** branch protection, signed commits, required PR reviews, secret scanning, pre-commit hooks.
- **Build/CI:** SAST, SCA, and secret-scan gates that fail the build; ephemeral runners that only have the access they need; verified dependencies.
- **Artifact:** scan and **sign** images (cosign), generate an SBOM, push to a private registry, and only allow signed images to deploy through admission control (Kyverno/OPA Gatekeeper).
- **Deploy:** OIDC keyless auth, approvals for production environments, policy as code, and full audit trails.
- **Runtime:** Falco, network policies, and continuous scanning.

### 9.4 Store secrets in CI/CD securely

- **Never put secrets in code or repos.** Use the platform's secret store (GitHub Actions Secrets/Environments, GitLab CI masked and protected variables, Jenkins Credentials).
- **Prefer keyless auth:** use **OIDC federation** to assume cloud IAM roles, so there are no long-lived cloud keys at all.
- **External vaults:** HashiCorp Vault, AWS Secrets Manager, or SSM Parameter Store, injected at runtime with short lifetimes.
- **Hygiene:** give secrets only the access they need, mask and rotate them, scope them to specific environments, restrict them on PRs from forks, and scan for leaked secrets.

### 9.5 Implement code scanning and infrastructure scanning in a DevSecOps pipeline

- **Code:** SAST (SonarQube/Semgrep), dependency scanning (Snyk/Dependabot), and secret scanning (gitleaks) as CI gates on every PR.
- **Infrastructure:** IaC scanning (Checkov/tfsec/Trivy) on Terraform/Helm/Kubernetes manifests, container image scanning (Trivy), and CIS benchmark checks (kube-bench).
- **Gate and report:** fail builds on high/critical findings, surface results in PRs, and track them over time. Add admission control and runtime scanning (Falco) so security keeps running after deploy, not just once at the gate — "shift left" plus runtime.

---
