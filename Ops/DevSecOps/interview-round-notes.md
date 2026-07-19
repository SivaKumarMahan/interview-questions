# Scenario-Based Interview Notes

> Distributed from the former cross-topic scenario notes. Section numbering is retained where useful for interview practice.

## Security & DevSecOps

### 9.1 Preferred tools for SAST & DAST
- **SAST (static, scans source/dependencies):** SonarQube, Semgrep, Checkmarx, Snyk Code; dependency/SCA: OWASP Dependency-Check, Snyk, Dependabot; IaC scanning: tfsec/Checkov/Trivy; secrets: gitleaks/trufflehog.
- **DAST (dynamic, scans the running app):** OWASP ZAP, Burp Suite, Nikto.
- **Containers:** Trivy/Grype for image scanning. Run SAST early in CI (shift-left) and DAST against a deployed staging env.

### 9.2 Secure pipelines against supply chain attacks
- **Pin & verify dependencies:** lockfiles, checksum/hash pinning, pin GitHub Actions to a commit SHA (not a mutable tag).
- **SCA + image scanning** in CI (Snyk/Trivy) to catch vulnerable/malicious deps.
- **Provenance & signing:** SLSA framework, sign artifacts/images with **Sigstore/cosign**, generate an **SBOM** (Syft), verify signatures before deploy.
- **Least privilege for CI:** short-lived OIDC tokens instead of long-lived secrets, scoped runner permissions, isolated ephemeral runners.
- **Protect the pipeline itself:** branch protection, required reviews, secret scanning, trusted internal registries/proxies, and audit logging.

### 9.3 Enforce pipeline security from Git → deployment
- **Source:** branch protection, signed commits, required PR reviews, secret scanning, pre-commit hooks.
- **Build/CI:** SAST + SCA + secret scan gates that fail the build; ephemeral least-privilege runners; verify dependencies.
- **Artifact:** scan and **sign** images (cosign), generate SBOM, push to a private registry, admission control (only signed images deploy — Kyverno/OPA Gatekeeper).
- **Deploy:** OIDC keyless auth, environment approvals for prod, policy-as-code, and full audit trails. **Runtime:** Falco, network policies, continuous scanning.

### 9.4 Store secrets in CI/CD securely
- **Never in code/repos.** Use the platform secret store (GitHub Actions Secrets/Environments, GitLab CI variables masked+protected, Jenkins Credentials).
- **Prefer keyless:** **OIDC federation** to assume cloud IAM roles → no long-lived cloud keys at all.
- **External vaults:** HashiCorp Vault, AWS Secrets Manager, SSM Parameter Store, injected at runtime with short TTLs.
- **Hygiene:** least privilege, mask/rotate secrets, scope to environments, restrict on PRs from forks, and scan for leaked secrets.

### 9.5 Implement code scanning & infrastructure scanning in a DevSecOps pipeline
- **Code:** SAST (SonarQube/Semgrep) + SCA (Snyk/Dependabot) + secret scanning (gitleaks) as CI gates on every PR.
- **Infrastructure:** IaC scanning (Checkov/tfsec/Trivy) on Terraform/Helm/K8s manifests; container image scanning (Trivy); CIS benchmark checks (kube-bench).
- **Gate & report:** fail builds on high/critical, surface results in PRs, track over time; add admission control and runtime scanning (Falco) so security is continuous, not a one-time gate — "shift left" plus runtime.

---
