## 1. How do you secure CI/CD artifact storage?

**Answer:** Store in Nexus/Artifactory → Enable RBAC → Use signed artifacts → Encrypt storage.

**Detailed interview approach:**
I protect the whole path from source to production. That means branch protection and code review, pinned dependencies, actions, and plugins, isolated ephemeral runners, and short-lived identities scoped to the minimum access needed.

On top of that I run SAST, dependency, secret, IaC, and container scans, generate an SBOM, sign the provenance record and the artifacts themselves, use protected registries, and verify everything again at deployment admission.

Scan findings get an agreed severity and SLA, plus a time-limited exception process, so the gates are strict but still usable day to day.

If I suspect compromise, I stop promotion, revoke runner and signing credentials, isolate the affected artifacts, preserve audit evidence, rebuild from a trusted runner and source, and verify signatures again before redeploying.

Regular patching, egress restrictions, audit log retention, and recovery drills cover the gaps that scanners alone can't catch.

## 2. How do you secure Docker registry in production?

**Answer:** Enable HTTPS & authentication → Use signed images (Cosign) → Restrict access via IAM.

**Detailed interview approach:**
I look at the image, the runtime configuration, and the host separately. Builds use multi-stage Dockerfiles, small pinned trusted base images, a `.dockerignore` file, dependency layers ordered for caching, and non-root runtime users.

CI scans the dependencies and the image, generates an SBOM, signs the digest so it can't be swapped later, and pushes it over TLS to a registry with tightly scoped write access. Deployment then verifies that same digest before running it.

At runtime I drop unnecessary capabilities, use seccomp, AppArmor, or SELinux, run with a read-only filesystem, set resource limits, avoid exposing the privileged Docker socket, and restrict networking.

If startup is slow or a push fails, I measure layer size and cache hits, check registry DNS, auth, and TLS, and check disk and application initialization, instead of just retrying blindly. Then I rebuild from patched base images and re-verify functionality and security findings.

## 3. How do you troubleshoot failed Docker image push to registry?

**Answer:** Check registry credentials → Validate image name/tag → Ensure repository exists → Retry with correct login.

**Detailed interview approach:**
I look at the image, the runtime configuration, and the host separately. Builds use multi-stage Dockerfiles, small pinned trusted base images, a `.dockerignore` file, dependency layers ordered for caching, and non-root runtime users.

CI scans the dependencies and the image, generates an SBOM, signs the digest so it can't be swapped later, and pushes it over TLS to a registry with tightly scoped write access. Deployment then verifies that same digest before running it.

At runtime I drop unnecessary capabilities, use seccomp, AppArmor, or SELinux, run with a read-only filesystem, set resource limits, avoid exposing the privileged Docker socket, and restrict networking.

If startup is slow or a push fails, I measure layer size and cache hits, check registry DNS, auth, and TLS, and check disk and application initialization, instead of just retrying blindly. Then I rebuild from patched base images and re-verify functionality and security findings.

