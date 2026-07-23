## 1. Which container registry should you trust for production images?

**Answer:**

I trust an organization-approved registry—not an image merely because it is public or popular. The registry must provide strong identity and least-privilege repositories, TLS and encryption, immutable tags or digest-based deployment, vulnerability scanning, audit logs, retention and recovery, replication/availability, and integration with signing, SBOM, and admission policy. Examples may include ECR, ACR, GCR/Artifact Registry, JFrog Artifactory, Nexus, Harbor, or another managed internal service.

Base images come from allowlisted publishers, are mirrored internally, pinned by digest, scanned, and rebuilt on an owned schedule. CI authenticates with short-lived identity, signs the resulting digest, and only the release workflow can write production repositories. Kubernetes or the runtime verifies approved registry, signature/provenance, and policy before deployment.

I test pull behavior during registry/AZ failure and monitor auth failures, scan findings, replication lag, storage, and unusual downloads. A private registry alone is not a trust guarantee; provenance and controlled production promotion establish trust.

## 2. How do you sign software artifacts and verify them before deployment?

**Answer:**

I sign the immutable digest after the build and security checks, using a protected key or keyless workload identity tied to the CI workflow. Containers and OCI Helm charts can use Cosign; classic Helm charts can use provenance signatures; packages may use ecosystem-native signing. The signature and provenance identify the source commit, builder/workflow, artifact digest, and relevant attestations such as SBOM or test results.

Deployment policy verifies digest, signature identity/issuer, expected repository/workflow, and required attestations before admitting or promoting the artifact. Keys have owners, rotation, revocation, and audit; CI jobs do not receive long-lived exported private keys. Offline or recovery verification is tested.

Signing proves origin and integrity, not quality. Code review, tests, scanning, policy checks, and runtime controls remain necessary. If a key or workflow is compromised, I revoke trust, identify every affected digest, rebuild from a trusted pipeline, and prevent those artifacts from deployment.
