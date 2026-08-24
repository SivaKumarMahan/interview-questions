## 1. Which security scanning tools do you run on container images at build time and registry time?

**Answer:**

At build time I scan source dependencies and the final image before it's published. Tools may include Trivy, Grype, Snyk, Docker Scout, or a commercial platform. Semgrep and SonarQube cover code and static findings, while Checkov and tfsec cover infrastructure definitions.

I generate an SBOM (a software bill of materials — a list of what's inside the image) with Syft or the build platform. I scan the actual image, not just the Dockerfile, and fail the build based on an agreed policy covering severity, exploitability, fix availability, age, and approved exceptions.

At registry time I enable continuous rescanning through a service such as ECR, ACR, Harbor, JFrog Xray, Nexus IQ, or Prisma. This catches vulnerabilities that get disclosed after an image was already built.

Alerts identify the image digest — which stays fixed once the image is built — along with the deployed workloads, the owner, the exposure, the base image, and the fix deadline. Production admission checks that the image comes from an approved registry, is signed, and meets policy.

I don't treat "zero CVEs" as the whole security program. Base images are pinned and rebuilt regularly. Secrets are scanned separately. Licenses and malware may have their own policy, and runtime controls catch behavior that scanning can't.

Exceptions are time-bound. When a fix is needed, the patched image is rebuilt, retested, signed, promoted, and verified — I don't patch a running container in place.
