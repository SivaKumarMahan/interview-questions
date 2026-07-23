## 1. How do you secure CI/CD artifact storage?
**Answer:** Store in Nexus/Artifactory → Enable RBAC → Use signed artifacts → Encrypt storage.

**Detailed interview approach:**
I protect the path from source to production: branch protection and review, pinned dependencies/actions/plugins, isolated ephemeral runners, short-lived least-privilege identity, SAST/dependency/secret/IaC/container scans, SBOM generation, signed provenance and artifacts, protected registries, and deployment admission verification. Findings have an agreed severity/SLA and a time-limited exception process so gates are both enforceable and usable. If compromise is suspected, I stop promotion, revoke runner and signing credentials, quarantine artifacts, preserve audit evidence, rebuild from a trusted runner/source, and verify signatures before redeployment. Regular patching, egress restrictions, audit retention, and recovery exercises cover the controls scanners cannot.

## 2. How do you secure Docker registry in production?
**Answer:** Enable HTTPS & authentication → Use signed images (Cosign) → Restrict access via IAM.

**Detailed interview approach:**
I inspect the image, runtime configuration, and host separately. Builds use multi-stage Dockerfiles, pinned small trusted bases, `.dockerignore`, dependency cache ordering, and non-root runtime users. CI scans dependencies/image, generates an SBOM, signs the immutable digest, and pushes through TLS to a least-privilege registry; deployment verifies that digest. At runtime I drop capabilities, use seccomp/AppArmor/SELinux, read-only filesystems, limits, no privileged Docker socket, and restricted networking. For slow startup or push failures I measure layer size/cache, registry DNS/auth/TLS, disk and application initialization rather than repeatedly retrying. Rebuild from patched bases and verify functionality/security findings.

## 3. How do you troubleshoot failed Docker image push to registry?
**Answer:** Check registry credentials → Validate image name/tag → Ensure repository exists → Retry with correct login.

**Detailed interview approach:**
I inspect the image, runtime configuration, and host separately. Builds use multi-stage Dockerfiles, pinned small trusted bases, `.dockerignore`, dependency cache ordering, and non-root runtime users. CI scans dependencies/image, generates an SBOM, signs the immutable digest, and pushes through TLS to a least-privilege registry; deployment verifies that digest. At runtime I drop capabilities, use seccomp/AppArmor/SELinux, read-only filesystems, limits, no privileged Docker socket, and restricted networking. For slow startup or push failures I measure layer size/cache, registry DNS/auth/TLS, disk and application initialization rather than repeatedly retrying. Rebuild from patched bases and verify functionality/security findings.

