# Docker: Security, CI/CD, and Deployments

> Runtime and image security, secrets, scanning, policy as code, immutability, Docker in CI/CD pipelines, rollbacks, and compliance-constrained deployments.

## Interview Questions

### 1. How do you ensure Docker container security at runtime? *(asked in interview round)*

**Answer:** Use Falco or AquaSec to watch for suspicious behavior. Restrict root access. Apply AppArmor or SELinux profiles.

**Detailed interview approach:**
I look at the image, the runtime setup, and the host as three separate things. For builds, I use multi-stage Dockerfiles, a small pinned base image, a `.dockerignore` file, cache-friendly dependency ordering, and a non-root user at runtime.

In CI, I scan dependencies and the image, generate an SBOM (a list of everything in the image), and sign the final build so it can't be swapped for something else later. The image is pushed over TLS to a registry with tightly scoped access, and deployment checks that signature before using it.

At runtime I drop capabilities the container doesn't need, use seccomp/AppArmor/SELinux, make the filesystem read-only where possible, set resource limits, avoid giving containers access to the Docker socket, and restrict network access.

If startup is slow or a push keeps failing, I measure things instead of guessing: layer size and cache hits, registry DNS/auth/TLS, disk space, and application startup time. Once I find the cause, I rebuild from a patched base and re-check that everything still works.

### 2. How do you handle secrets inside containers?

**Answer:**

Secrets never go into images, into a Dockerfile's `ARG` or `ENV`, into layers, or into source code. At runtime, they come from Kubernetes Secrets combined with an external secret manager or CSI driver, from Docker secrets where that's supported, or from a short-lived mounted file.

Where possible, I use workload identity (the platform proving who the workload is) instead of a long-lived cloud access key.

Secret files get narrow file permissions and a short lifecycle, and logs and diagnostics are set up to redact them. Image scanning can catch an accidentally-included secret, but once one is found, deleting it from a later layer doesn't remove it from history — the only real fix is to rotate the secret immediately and rebuild.

I test that the image's history and any exported copy contain no secret, that only authorized workloads can read it, and that rotating a secret doesn't cause downtime.

### 3. Are you aware of security scanning tools? How do you scan Docker images — both during build and at the registry level?

I scan images at two points: during the build, and again once they land in the registry.

During the build, I run **Trivy** as part of CI to catch OS-level and dependency-level vulnerabilities before the image ever gets deployed. After the image is pushed to Azure Container Registry, **Microsoft Defender for Containers** scans it automatically and surfaces any CVEs in the Azure Security Center. To enforce this, the build fails automatically if Trivy finds anything rated High or Critical.

**Trivy scan during build:**

1. Install Trivy in your CI environment.
2. Add a scan step in your pipeline after building the image:

```bash
# Install Trivy
sudo apt install trivy -y

# Scan Docker image after build
docker build -t myapp:latest .
trivy image myapp:latest
```

**Output example:**

```text
myapp:latest (ubuntu 22.04)
============================
Total: 8 (CRITICAL: 2, HIGH: 3, MEDIUM: 3)
```

You can add this step to:

- A Jenkins pipeline (`stage('Security Scan')`)
- An Azure DevOps YAML pipeline (`bash: trivy image $(imageName)`)
- A GitHub Actions workflow

**Fail the build automatically if severity is High or above:**

```bash
trivy image --exit-code 1 --severity HIGH,CRITICAL myapp:latest
```

**Docker's native scan (powered by Snyk):**

1. Use Docker's built-in scanning feature if it's available in your environment.
2. Run the scan command:

```bash
docker scan myapp:latest
```

This integrates directly with Docker Desktop and Docker Hub.

**Registry-level scanning:**

**Azure Container Registry (ACR)**

- Microsoft Defender for Containers scans images automatically after they're pushed.
- It finds CVEs and surfaces them in the Azure Security Center.

Enable scanning:

- Go to `ACR` → `Settings` → `Defender for Cloud`.
- Turn on Vulnerability Assessment.

Run an on-demand scan:

```bash
az acr run --cmd "acr scan show --name <registry>" --registry <acrName>
```

View results under `Security` → `Vulnerabilities`.

### 4. How do you enforce policy as code for Docker security?

**Answer:**

CI checks Dockerfiles, images, and deployment configuration against a set of rules, using tools like OPA/Conftest, Checkov, Hadolint, Trivy, and Kubernetes admission policies.

Typical rules require: no root user, only approved registries and base images, images referenced by a fixed digest rather than a mutable tag, no privileged mode, dropped capabilities, a read-only filesystem, and a vulnerability threshold that must be met.

I test each rule against both compliant and non-compliant examples, version the rules themselves, give clear guidance on how to fix a violation, and allow a time-limited exception process rather than a permanent bypass. Signing and build provenance — a record of where an image came from and how it was built — get checked again at deployment time.

Policy as code works alongside runtime controls, RBAC, network segmentation, monitoring, and regular patching — it's one layer, not the whole defense. I usually start new rules in audit-only mode so I can see their impact before actually blocking anything.

### 5. How do you ensure Docker image immutability? *(asked in interview round)*

**Answer:** Tag images with a version or commit hash. Push that exact tag to the registry and never overwrite it. Block `latest` from being used in pipelines.

**Detailed interview approach:**
The idea is that once an image is built and tagged, it never changes. If you need a new version, you build a new tag — you don't overwrite the old one.

I tag every build with a commit hash or version number, and I reference images by their digest (a fixed hash of the exact content) rather than a mutable tag like `latest`. CI signs the digest before pushing, and deployment verifies that signature so nobody can quietly swap the image for something else.

This makes rollback simple and reliable: to go back, you just redeploy the previous tag or digest, knowing it's exactly the same bytes that were tested before.

### 6. How do you secure Docker containers in CI/CD pipelines? *(asked in interview round)*

**Answer:** Run image scans with Trivy or Anchore. Use non-root users. Apply resource limits. Keep images updated.

**Detailed interview approach:**
Security in the pipeline happens at a few checkpoints. During the build, I use a small pinned base image, a `.dockerignore` file, and a non-root user. In CI, I scan the image and its dependencies for known vulnerabilities and fail the pipeline if anything High or Critical is found. Before the image ships, I generate an SBOM and sign it.

At deploy time, containers run with dropped capabilities, a read-only filesystem where possible, resource limits, and no access to the Docker socket. I also keep base images current by rebuilding regularly, not just when something breaks.

### 7. How is Docker useful and how do you use it in a pipeline? *(scenario)*

- **Consistency:** the same image runs in CI, staging, and production.
- **Isolation and density:** you can run many containers on one host, each with its resource usage capped by cgroups.
- **Fast, reliable deploys:** once an image is built and tagged, that exact build never changes — you ship an image tag, and rolling back just means re-deploying the previous tag.
- **In a pipeline:** build the image, run unit and integration tests inside it, scan it for vulnerabilities (with a tool like Trivy or Grype), push it to a registry (like ECR or GHCR) under a fixed tag, then deploy it to Kubernetes or ECS. Multi-stage builds keep the final image small and free of build tools.

### 8. Can Docker containers be used as CI/CD agents? *(scenario)*

Yes — this is standard practice:

- **Jenkins:** the Docker and Kubernetes plugins spin up a fresh container for each build. You get a clean, reproducible environment that's thrown away afterward.
- **GitLab CI:** each job runs inside a container defined by `image:`.
- **GitHub Actions:** `container:` runs job steps inside a container, and you can also run service containers alongside it.

The benefits are isolation, reproducibility, no "snowflake" build agents that drift out of sync, and easy control over which tool versions each job uses.

### 9. How to rollback a failed deployment in Docker and Kubernetes?

If a deployment using a new image fails, you can roll back by running a container from the previous working image instead.

**Run the previous working version**

```bash
docker run -d -p 8080:80 <image_name>:<previous_tag>
docker tag <image_name>:<previous_tag> <image_name>:stable   # tag a stable version
```

Always version your images (for example, `myapp:v1`, `myapp:v2`) so you can revert easily.

**Rollback in Kubernetes**

```bash
kubectl rollout history deployment <deployment_name>              # Check rollout history
kubectl rollout undo deployment <deployment_name>                 # Rollback to the previous revision
kubectl rollout undo deployment <deployment_name> --to-revision=2 # Rollback to a specific revision
kubectl rollout status deployment <deployment_name>
kubectl get pods -o wide
```

### 10. How do you handle multi-cloud Docker deployments with compliance restrictions?

**Answer:**

I build one approved image in a single controlled pipeline, generate its SBOM and provenance record, scan and sign it, and then replicate that exact same digest to approved regional registries in each cloud. The image content stays identical everywhere; only cloud-specific deployment configuration differs.

Controls cover where data can live, where the registry is located and how it's encrypted, identity federation across clouds, private network connectivity, vulnerability policy, who holds the signing keys, audit log retention, and runtime security. Terraform modules and policy-as-code enforce a common baseline, and each cloud gets its own tightly scoped identities and state.

I test that unapproved regions, unapproved registries, and unsigned images all get rejected. Disaster recovery planning has to account for registry availability too — replication needs to stay trustworthy, not just fast, and can't be used as an excuse to skip compliance checks.
