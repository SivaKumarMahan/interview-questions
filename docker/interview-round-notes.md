## 1. How do you ensure Docker container security at runtime?

**Answer:** Use Falco or AquaSec to watch for suspicious behavior. Restrict root access. Apply AppArmor or SELinux profiles.

**Detailed interview approach:**
I look at the image, the runtime setup, and the host as three separate things. For builds, I use multi-stage Dockerfiles, a small pinned base image, a `.dockerignore` file, cache-friendly dependency ordering, and a non-root user at runtime.

In CI, I scan dependencies and the image, generate an SBOM (a list of everything in the image), and sign the final build so it can't be swapped for something else later. The image is pushed over TLS to a registry with tightly scoped access, and deployment checks that signature before using it.

At runtime I drop capabilities the container doesn't need, use seccomp/AppArmor/SELinux, make the filesystem read-only where possible, set resource limits, avoid giving containers access to the Docker socket, and restrict network access.

If startup is slow or a push keeps failing, I measure things instead of guessing: layer size and cache hits, registry DNS/auth/TLS, disk space, and application startup time. Once I find the cause, I rebuild from a patched base and re-check that everything still works.

## 2. How do you ensure Docker image immutability?

**Answer:** Tag images with a version or commit hash. Push that exact tag to the registry and never overwrite it. Block `latest` from being used in pipelines.

**Detailed interview approach:**
The idea is that once an image is built and tagged, it never changes. If you need a new version, you build a new tag — you don't overwrite the old one.

I tag every build with a commit hash or version number, and I reference images by their digest (a fixed hash of the exact content) rather than a mutable tag like `latest`. CI signs the digest before pushing, and deployment verifies that signature so nobody can quietly swap the image for something else.

This makes rollback simple and reliable: to go back, you just redeploy the previous tag or digest, knowing it's exactly the same bytes that were tested before.

## 3. How do you secure Docker containers in CI/CD pipelines?

**Answer:** Run image scans with Trivy or Anchore. Use non-root users. Apply resource limits. Keep images updated.

**Detailed interview approach:**
Security in the pipeline happens at a few checkpoints. During the build, I use a small pinned base image, a `.dockerignore` file, and a non-root user. In CI, I scan the image and its dependencies for known vulnerabilities and fail the pipeline if anything High or Critical is found. Before the image ships, I generate an SBOM and sign it.

At deploy time, containers run with dropped capabilities, a read-only filesystem where possible, resource limits, and no access to the Docker socket. I also keep base images current by rebuilding regularly, not just when something breaks.

## 4. How do you debug slow Docker container startup?

**Answer:** Check the image size. Optimize the Dockerfile. Preload dependencies. Monitor entrypoint logs.

**Detailed interview approach:**
I start by measuring rather than guessing. I check the image size and layer count, how much of the build hit cache, and how long the application itself takes to initialize.

Common causes are a bloated image, dependencies being installed at container startup instead of build time, slow registry pulls, or the application doing heavy work (like loading large files or connecting to slow dependencies) before it's ready to serve traffic.

Once I find the bottleneck, I fix the Dockerfile — usually with multi-stage builds and better layer ordering — rebuild, and confirm startup time actually improved.

## 5. How do you reduce Docker image size for faster deployments?

**Answer:**
- Use a smaller base image, like Alpine.
- Use multi-stage builds.
- Remove unused packages and cache in the same layer you added them.
- Push to a private registry so pulls are fast and cached.

**Detailed interview approach:**
I start from a small, trusted base image and use multi-stage builds so build tools and source code never end up in the final image — only the compiled output does.

I keep the number of packages installed to a minimum, and I clean up package caches in the same `RUN` step that installs them, since a later `RUN rm` doesn't shrink earlier layers. I also order instructions so that things which change often (like application source) come after things that rarely change (like dependency installs), so builds stay fast.

Alpine isn't always the right choice — sometimes its different C library (musl) causes compatibility issues, so a "slim" or distroless image can be a safer trade-off.
