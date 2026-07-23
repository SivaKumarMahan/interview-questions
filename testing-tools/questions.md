## 1. Which security scanning tools do you run on container images at build time and registry time?

**Answer:**

At build time I scan source dependencies and the final image before publication. Tools may include Trivy, Grype, Snyk, Docker Scout, or a commercial platform; Semgrep/SonarQube cover code and selected static findings, while Checkov/tfsec cover infrastructure definitions. I generate an SBOM with Syft or the build platform, scan the actual image rather than only the Dockerfile, and fail on an agreed policy based on severity, exploitability, fix availability, age, and approved exceptions.

At registry time I enable continuous rescanning through ECR, ACR, Harbor, JFrog Xray, Nexus IQ, Prisma, or another approved service. This catches vulnerabilities disclosed after an image was built. Alerts identify the immutable digest, deployed workloads, owner, exposure, base image, and remediation deadline. Production admission verifies approved registry, signature/provenance, and policy.

I do not treat “zero CVEs” as the entire security program. Bases are pinned and rebuilt regularly; secrets are scanned separately; licenses and malware may have their own policy; runtime controls detect behavior scanning cannot. Exceptions are time-bound, and a patched digest is rebuilt, retested, signed, promoted, and verified rather than modifying a running container.
