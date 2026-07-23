## 1. How do you ensure Docker container security at runtime?
**Answer:** Use Falco/AquaSec → Restrict root access → Apply AppArmor/SELinux profiles.

**Detailed interview approach:**
I inspect the image, runtime configuration, and host separately. Builds use multi-stage Dockerfiles, pinned small trusted bases, `.dockerignore`, dependency cache ordering, and non-root runtime users. CI scans dependencies/image, generates an SBOM, signs the immutable digest, and pushes through TLS to a least-privilege registry; deployment verifies that digest. At runtime I drop capabilities, use seccomp/AppArmor/SELinux, read-only filesystems, limits, no privileged Docker socket, and restricted networking. For slow startup or push failures I measure layer size/cache, registry DNS/auth/TLS, disk and application initialization rather than repeatedly retrying. Rebuild from patched bases and verify functionality/security findings.

## 2. How do you ensure Docker image immutability?
**Answer:** Tag images with version/commit hash → Push immutable tags to registry → Prevent latest usage in pipelines.

**Detailed interview approach:**
I inspect the image, runtime configuration, and host separately. Builds use multi-stage Dockerfiles, pinned small trusted bases, `.dockerignore`, dependency cache ordering, and non-root runtime users. CI scans dependencies/image, generates an SBOM, signs the immutable digest, and pushes through TLS to a least-privilege registry; deployment verifies that digest. At runtime I drop capabilities, use seccomp/AppArmor/SELinux, read-only filesystems, limits, no privileged Docker socket, and restricted networking. For slow startup or push failures I measure layer size/cache, registry DNS/auth/TLS, disk and application initialization rather than repeatedly retrying. Rebuild from patched bases and verify functionality/security findings.

## 3. How do you secure Docker containers in CI/CD pipelines?
**Answer:** Run image scans (Trivy/Anchore) → Use non-root users → Apply resource limits → Keep images updated.

**Detailed interview approach:**
I inspect the image, runtime configuration, and host separately. Builds use multi-stage Dockerfiles, pinned small trusted bases, `.dockerignore`, dependency cache ordering, and non-root runtime users. CI scans dependencies/image, generates an SBOM, signs the immutable digest, and pushes through TLS to a least-privilege registry; deployment verifies that digest. At runtime I drop capabilities, use seccomp/AppArmor/SELinux, read-only filesystems, limits, no privileged Docker socket, and restricted networking. For slow startup or push failures I measure layer size/cache, registry DNS/auth/TLS, disk and application initialization rather than repeatedly retrying. Rebuild from patched bases and verify functionality/security findings.

## 4. How do you debug slow Docker container startup?
**Answer:** Check image size → Optimize Dockerfile → Preload dependencies → Monitor entrypoint logs.

**Detailed interview approach:**
I inspect the image, runtime configuration, and host separately. Builds use multi-stage Dockerfiles, pinned small trusted bases, `.dockerignore`, dependency cache ordering, and non-root runtime users. CI scans dependencies/image, generates an SBOM, signs the immutable digest, and pushes through TLS to a least-privilege registry; deployment verifies that digest. At runtime I drop capabilities, use seccomp/AppArmor/SELinux, read-only filesystems, limits, no privileged Docker socket, and restricted networking. For slow startup or push failures I measure layer size/cache, registry DNS/auth/TLS, disk and application initialization rather than repeatedly retrying. Rebuild from patched bases and verify functionality/security findings.

## 5. How do you reduce Docker image size for faster deployments?
**Answer:** • Use smaller base images (alpine).
• Multi-stage builds.
• Remove unused packages and cache.
• Push to private registry for caching.

**Detailed interview approach:**
I inspect the image, runtime configuration, and host separately. Builds use multi-stage Dockerfiles, pinned small trusted bases, `.dockerignore`, dependency cache ordering, and non-root runtime users. CI scans dependencies/image, generates an SBOM, signs the immutable digest, and pushes through TLS to a least-privilege registry; deployment verifies that digest. At runtime I drop capabilities, use seccomp/AppArmor/SELinux, read-only filesystems, limits, no privileged Docker socket, and restricted networking. For slow startup or push failures I measure layer size/cache, registry DNS/auth/TLS, disk and application initialization rather than repeatedly retrying. Rebuild from patched bases and verify functionality/security findings.

