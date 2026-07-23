# DevSecOps Summary

**DevSecOps** integrates security evidence and controls throughout delivery instead of treating security as a final scan.

## Secure CI and GitOps Delivery Flow

```text
pull request -> tests and quality checks -> dependency/SAST/secret/IaC scans
-> image build -> container scan, SBOM, signing -> immutable registry
-> reviewed GitOps manifest update -> Argo CD/Flux reconciliation
-> Kubernetes admission/runtime controls -> observability and response
```

- **OWASP Dependency-Check** or an equivalent tool identifies known vulnerable third-party dependencies.
- **SonarQube** analyzes maintainability, bugs, and configured security rules; its quality gate is one signal, not proof that code is secure.
- **Trivy** or an equivalent scanner examines filesystems, dependencies, IaC, and container images according to the selected mode.
- CI publishes an immutable image digest only after required evidence passes; exceptions are risk-owned, approved, time-limited, and tracked.
- CI updates the reviewed deployment repository, while **Argo CD** or **Flux** pulls desired state into Kubernetes. CI does not need broad cluster credentials in this model.
- **Prometheus**, **Grafana**, and centralized logs and traces verify the release; alert routing creates an operational feedback loop.

Pin pipeline dependencies, protect credentials through short-lived identity, generate and retain an SBOM and provenance, sign artifacts, enforce admission policy, separate duties, and regularly test rollback and incident response. Scanners reduce risk but do not replace threat modeling, secure design, patching, runtime hardening, or human review.
