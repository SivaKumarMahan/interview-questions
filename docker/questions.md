## 1. Have you built Docker containers? For what use case?

**Answer:**

Yes—a representative use case is packaging a web API consistently for developer laptops, CI, and Kubernetes. I create a multi-stage Dockerfile, run as a non-root user, expose only the application port, add a health check where suitable, and keep configuration outside the image.

CI builds from a pinned base, runs tests, generates an SBOM, scans with Trivy, tags with commit SHA, and pushes an immutable digest to a private registry. Kubernetes deploys that digest with resource limits, probes, security context, and external secrets.

I verify image size/layers, vulnerability result, startup, health, logs, signal handling, and read-only filesystem compatibility. This prevents “works on my machine” while keeping one artifact across environments.

## 2. What is the lifecycle of a Docker container?

**Answer:**

An image is created/pulled; `docker create` prepares a container writable layer and configuration; `start` runs the configured process; it may pause/restart/stop; `rm` deletes the container. Persistent data must live in volumes/external services because the writable layer disappears with removal.

The container runs while its PID 1 process runs. `docker stop` sends SIGTERM, waits, then SIGKILL; therefore the application must handle signals and shut down gracefully.

```bash
docker pull nginx:1.27
docker create --name web nginx:1.27
docker start web
docker logs web
docker stop web
docker rm web
```

For failures I inspect state/exit code/OOM, logs, events, configuration, mounts, network, and health before restarting.

## 3. How do you create a custom Docker image?

**Answer:**

I write a Dockerfile, add `.dockerignore`, pin a trusted base image, build, test, scan, and publish an immutable version.

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
USER 10001
EXPOSE 8080
CMD ["python", "app.py"]
```

```bash
docker build --pull -t registry.example.com/app:abc123 .
docker run --rm -p 8080:8080 registry.example.com/app:abc123
trivy image --severity HIGH,CRITICAL registry.example.com/app:abc123
docker push registry.example.com/app:abc123
```

I check application tests, startup, user, files, size/layers, signal handling, and vulnerabilities. Credentials never enter build arguments/layers; BuildKit secret mounts are used when a private dependency truly requires authentication.

## 4. How do you write a production-ready Dockerfile?

**Answer:**

I use multi-stage builds so compilers/dependencies do not remain in runtime, pin an approved base, install only required packages, copy dependency files before source for caching, and run as non-root.

```dockerfile
FROM node:20-alpine AS build
WORKDIR /src
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm test && npm run build

FROM nginx:1.27-alpine
COPY --from=build /src/dist /usr/share/nginx/html
USER 101
```

I use exec-form ENTRYPOINT/CMD, `.dockerignore`, no embedded secrets, minimal writable paths, labels/SBOM, scanning, and deterministic dependencies. Health belongs mainly to the orchestrator. I test the image under the same non-root/read-only/resource restrictions used in production.

## 5. What is the difference between `ADD` and `COPY` in a Dockerfile?

**Answer:**

`COPY` copies local build-context files/directories. `ADD` also has special behavior such as automatically extracting local tar archives and accepting supported remote sources. I prefer `COPY` because intent is explicit and easier to audit.

```dockerfile
COPY package.json package-lock.json ./
```

For remote files I download in a controlled `RUN` step with TLS and checksum verification or fetch them before build. I avoid accidentally adding large/sensitive context using `.dockerignore`. Neither command should copy `.git`, local credentials, or unnecessary build output.

## 6. What is the difference between `RUN`, `CMD`, and `ENTRYPOINT`?

**Answer:**

- `RUN` executes during image build and creates a layer.
- `ENTRYPOINT` defines the main runtime executable.
- `CMD` provides the default command or arguments and is easily overridden.

```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends curl \
 && rm -rf /var/lib/apt/lists/*
ENTRYPOINT ["/usr/local/bin/myapp"]
CMD ["--port", "8080"]
```

`docker run image --port 9090` overrides CMD arguments while preserving ENTRYPOINT. I use JSON/exec form so the app receives signals correctly as PID 1; shell form introduces a shell and can affect signal/argument handling.

## 7. What is the difference between `CMD` and `ENTRYPOINT`?

**Answer:**

ENTRYPOINT makes the container behave like a specific executable; CMD supplies default executable/arguments. Runtime arguments replace CMD, while `--entrypoint` is needed to replace ENTRYPOINT.

For an application image I use:

```dockerfile
ENTRYPOINT ["/app/server"]
CMD ["--config", "/etc/server/config.yaml"]
```

For a general base/tool image, CMD alone may be more flexible. I avoid wrapper scripts unless they use `exec "$@"` so signals reach the application. I test `docker stop` to confirm graceful shutdown.

## 8. What happens when you write `COPY .` in a Dockerfile?

**Answer:**

It copies the entire build context, except `.dockerignore` exclusions, into the destination. This can include source, Git history, credentials, test data, and large artifacts; any change can also invalidate cache.

I use a strict `.dockerignore` and copy only required files in cache-friendly order:

```dockerfile
COPY package.json package-lock.json ./
RUN npm ci
COPY src ./src
```

I inspect context size/build logs and image layers with `docker history` or tools such as Dive. If a secret was copied into a layer, deleting it in a later layer is insufficient—I rotate it and rebuild from clean history/context.

## 9. How do you optimize a Dockerfile for performance and security?

**Answer:**

I use a minimal trusted pinned base, multi-stage builds, lock files, cache-friendly ordering, BuildKit cache mounts, `.dockerignore`, non-root user, minimal packages, exec form, and no secrets. I remove package caches in the same layer and avoid unnecessary shells/tools in runtime.

CI builds reproducibly, tests, generates SBOM, scans, signs, and publishes an immutable digest. Runtime adds read-only root filesystem, dropped capabilities, seccomp, resource limits, and restricted network where compatible.

I measure build time, cache hit, image size, startup, CVEs, and application performance. Alpine is not automatically best—musl compatibility/debuggability may make slim/distroless alternatives safer.

## 10. Explain Docker image layering and how it can cause cache busting.

**Answer:**

Most Dockerfile instructions create content-addressed layers. Build cache for an instruction depends on previous layers and inputs. If `COPY . .` occurs before dependency installation, changing one source file invalidates that copy and every later layer, causing dependencies to reinstall.

Better:

```dockerfile
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src ./src
```

Frequently changing steps go later. I pin dependencies and deliberately refresh base/security updates with scheduled `--pull` builds. Cache improves speed, but I do not let stale cache prevent required patching. `docker history` and build timing identify invalidation.

## 11. What are Docker volumes and bind mounts, and when would you use each?

**Answer:**

A named volume is managed by Docker and suited to persistent container data. A bind mount maps a specific host path and is useful for development/configuration but tightly couples container to host layout/permissions.

```bash
docker volume create dbdata
docker run -v dbdata:/var/lib/postgresql/data postgres
docker run --mount type=bind,src="$PWD/config",dst=/app/config,readonly app
```

I define backup, restore, ownership, encryption, capacity, and lifecycle for persistent data. Removing a container does not necessarily remove a volume. In orchestration I use platform persistent volumes rather than assuming local Docker volumes provide HA.

## 12. What is Docker Compose?

**Answer:**

Docker Compose defines a multi-container application—services, networks, volumes, environment, and dependencies—in YAML and runs it with `docker compose`.

```yaml
services:
  api:
    build: .
    ports: ["8080:8080"]
    depends_on: [db]
  db:
    image: postgres:16
    volumes: ["dbdata:/var/lib/postgresql/data"]
volumes: { dbdata: {} }
```

It is excellent for local development, integration tests, and small single-host use. `depends_on` does not automatically prove database readiness, so health/retry is needed. For multi-node production, Kubernetes/ECS/another orchestrator normally provides scheduling, HA, secrets, and scaling.

## 13. How do you run multi-container applications in production without Compose?

**Answer:**

I use an orchestrator such as Kubernetes, ECS, AKS, or another approved platform. Each component has its own image, Deployment/task, Service/discovery, configuration, identity, scaling, health, and resource policy.

The delivery pipeline publishes immutable signed images, then Helm/manifests or GitOps declares the application. Databases usually use managed services or a carefully designed stateful platform. Secrets come from a secret manager.

I configure redundancy, probes, rolling/canary delivery, network policies, monitoring, logs, backups, and disaster recovery. Compose concepts help model services, but production requires cluster scheduling and operational controls.

## 14. How do you copy a file from a container to the host?

**Answer:**

```bash
docker cp mycontainer:/var/log/app/error.log ./error.log
docker cp ./config.yaml mycontainer:/tmp/config.yaml
```

The container can be running or stopped. I verify path, permissions, free space, and whether the file contains secrets/personal data. For active logs/data, a raw copy may be inconsistent; use application-supported export/snapshot where needed.

Copying files into a running container is normally a debugging action, not configuration management—the change disappears when the container is replaced. Permanent changes go into image/config/volume and are redeployed.

## 15. What are cgroups?

**Answer:**

Linux control groups account for and limit resource usage such as CPU, memory, PIDs, and I/O for process groups. Container runtimes use cgroups; namespaces provide isolation of views such as processes/network/mounts.

Docker flags translate into cgroup settings:

```bash
docker run --memory=512m --cpus=1.5 --pids-limit=200 app
```

Exceeding memory can cause OOM kill; CPU limits generally throttle. I inspect `docker stats`, container state/exit code, host pressure, and cgroup metrics. Limits protect the host but must be based on measurement; too-low limits create instability.

## 16. What are dangling Docker objects?

**Answer:**

Dangling images are untagged layers/images not referenced by a tag, often left after rebuilds. Unused containers, networks, volumes, and build cache can also consume disk, but “dangling” is most commonly used for images.

```bash
docker image ls --filter dangling=true
docker system df -v
docker image prune
```

I inspect before cleanup. Volumes may contain critical data, and images may be rollback inputs, so I use retention and registry-based immutable artifacts. Automated cleanup has filters, disk thresholds, exclusions, logging, and validation that active workloads are unaffected.

## 17. How do you delete all Docker resources in one command?

**Answer:**

I would not recommend a broad “delete everything” command on a shared or production host. `docker system prune -a --volumes` removes unused containers, networks, images, build cache, and unused volumes after confirmation; it can destroy recoverable data and rollback images.

My approach is `docker system df -v`, identify ownership/active references, back up required volumes, then prune specific object types with age/label filters. In production I use immutable hosts and controlled garbage collection rather than emergency deletion.

After cleanup I verify running containers, disk/inodes, application health, and image pull capacity. Material deletion is logged and approved.

## 18. How do you handle secrets inside containers?

**Answer:**

I never bake secrets into images, Dockerfile `ARG`/`ENV`, layers, or source. Runtime retrieves them through Kubernetes Secrets plus external secret manager/CSI, Docker secrets where supported, or a mounted short-lived file. Workload identity is preferable to static cloud keys.

Secret files have narrow permissions and memory/lifecycle scope; logs and diagnostics redact values. Registry/image scans help detect accidental inclusion, but a discovered secret is rotated immediately because deleting it in a later layer does not remove history.

I test that image history/export contains no secret, unauthorized workloads cannot access it, and rotation is consumed without downtime.

## 19. How do you enforce policy as code for Docker security?

**Answer:**

CI evaluates Dockerfiles/images and deployment configuration using tools such as OPA/Conftest, Checkov, Hadolint, Trivy, and admission policies. Rules can require non-root, approved registries/base images, immutable digest, no privileged mode, dropped capabilities, read-only filesystem, and vulnerability thresholds.

I test policies with compliant/non-compliant fixtures, version them, provide clear remediation, and use an expiring exception process. Artifact signing/provenance is verified at deployment.

Policy is layered with runtime controls, RBAC, network segmentation, monitoring, and patching. I begin in audit mode where possible to understand impact before enforcement.

## 20. How do you handle multi-cloud Docker deployments with compliance restrictions?

**Answer:**

I build one approved image in a controlled pipeline, generate SBOM/provenance, scan/sign it, and replicate/promote by digest to approved regional cloud registries. Cloud-specific deployment configuration remains separate while image content is identical.

Controls cover data residency, registry location/encryption, identity federation, private connectivity, vulnerability policy, signing keys, audit retention, and runtime security. Terraform/modules and policy as code enforce baseline; each cloud uses separate least-privilege identities/state.

I test that unapproved regions/registries and unsigned images are denied. DR considers registry availability and trusted replication without bypassing compliance.

## 21. You need live patching of a Docker host kernel without downtime. How do you achieve it?

**Answer:**

My preferred strategy is workload redundancy and host rotation: cordon/drain or remove one host from scheduling/load balancing, move containers to healthy hosts, patch/reboot, validate, and return it. This handles patches that require reboot and tests recovery.

Kernel live-patching services such as Canonical Livepatch, kpatch, or cloud offerings can apply supported security fixes without reboot, but not every patch qualifies. I verify kernel/support compatibility, test in lower ring, monitor, and still schedule periodic reboot to a fully updated kernel.

On a single host, true application zero downtime cannot be guaranteed; architecture must provide another instance.

## 22. What happens if you delete `/var/lib/docker/overlay` on a Docker host?

**Answer:**

It can corrupt/destroy image and container writable-layer data and make containers fail. I never manually delete Docker storage internals while daemon uses them.

If disk is full, I use `docker system df`, identify objects, preserve volumes/data, and use supported prune/removal commands with approval. If the directory was deleted, I stop changes, preserve logs/evidence, assess volumes separately, and normally rebuild the host from known configuration and repull immutable images rather than trying unsafe repair.

I restore persistent application data from proper volume backup, validate workloads, rotate host into service, and add controlled cleanup/capacity alerts. Docker’s internal directory is not an operator-managed cache.

## 23. How do you enter a running Docker container from the command line?

**Answer:**

I list the container, identify its available shell, and use `docker exec`, not `docker attach` for normal investigation:

```bash
docker ps
docker exec -it <container-name> /bin/sh
# Use /bin/bash only when the image contains Bash.
```

`exec` starts a new process inside the container. `attach` connects to the main process and can accidentally send signals or disrupt it. Minimal/distroless production images may have no shell; in that case I inspect logs, metadata, mounts, and namespaces from approved host/debug tooling rather than modifying the image.

Access to the Docker socket is effectively root-equivalent, so it is restricted and audited. I do not install packages or make a manual “fix” inside the container; I correct the Dockerfile or configuration, build a new immutable image, redeploy, and verify it.

## 24. How do you list running containers and all containers, including stopped ones?

**Answer:**

`docker ps` or `docker container ls` shows running containers. `docker ps -a` or `docker container ls --all` includes created, exited, and dead containers. I often add `--format` or filters to make the result useful:

```bash
docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}'
docker ps -a --filter status=exited
```

The status and exit code guide the next check. I use `docker inspect`, `docker logs`, and the application/host metrics before restarting or deleting anything, because an exited container can contain evidence needed for root-cause analysis.

## 25. How do you remove all containers and images safely?

**Answer:**

I first resolve exact scope and protect stateful data. Containers can be stopped and removed explicitly; images can be removed only after dependent containers are gone:

```bash
docker container ls -aq
docker image ls -q
```

For a disposable lab host, commands such as `docker container prune` and `docker image prune -a` are safer than opaque shell substitutions because they show scope and request confirmation. In production I do not blindly remove all containers or use `docker system prune --volumes`: named volumes may hold application data, running services may be interrupted, and evidence may be lost.

I review `docker system df`, remove only approved stopped containers and unused images, verify required digests are available in the registry, and retain volume backups. Host cleanup should be automated through retention policy, disk alerts, and immutable host replacement.

## 26. How many `CMD` instructions can a Dockerfile contain, and what happens when there are multiple?

**Answer:**

A Dockerfile can contain multiple `CMD` instructions syntactically, but only the last `CMD` in the final build stage is effective. Earlier ones are overwritten and usually indicate a confusing Dockerfile. Each stage of a multi-stage build can have its own metadata, but only the selected final image configuration matters at runtime.

I normally use one exec-form `ENTRYPOINT` for the executable and one exec-form `CMD` for default arguments:

```dockerfile
ENTRYPOINT ["java", "-jar", "/app/app.jar"]
CMD ["--spring.profiles.active=prod"]
```

Arguments supplied to `docker run image ...` replace `CMD`; `--entrypoint` replaces the entrypoint. Exec form preserves signal handling, which matters for graceful shutdown. I confirm the result with `docker image inspect` and a stop/termination test.

## 27. Write and explain a multi-stage Dockerfile for a Maven application.

**Answer:**

```dockerfile
# syntax=docker/dockerfile:1
FROM maven:3.9-eclipse-temurin-21 AS build
WORKDIR /src
COPY pom.xml .
RUN --mount=type=cache,target=/root/.m2 mvn -B dependency:go-offline
COPY src ./src
RUN --mount=type=cache,target=/root/.m2 mvn -B test package

FROM eclipse-temurin:21-jre
RUN useradd --system --uid 10001 appuser
WORKDIR /app
COPY --from=build --chown=appuser:appuser /src/target/*.jar app.jar
USER 10001
ENTRYPOINT ["java", "-jar", "/app/app.jar"]
```

The build stage contains Maven, source, and compiler dependencies; the runtime stage contains only a JRE and the built JAR. Copying `pom.xml` before source preserves the dependency cache. A `.dockerignore` excludes `.git`, local targets, credentials, and other unnecessary context. In production I pin approved base-image digests, scan and sign the result, set appropriate JVM/container limits, and test signal handling and health.

## 28. What should you do when a Docker container exits immediately after startup?

**Answer:**

I inspect `docker ps -a`, the exit code, `docker logs <container>`, and `docker inspect` for command, entrypoint, environment, mounts, health, OOM status, and runtime error. Exit 0 often means the main process completed normally; a container stays alive only while PID 1 runs. Exit 1 suggests application/configuration failure, 126/127 command or permission problems, and 137 often indicates SIGKILL or OOM.

I rerun the exact image with the intended configuration in a safe environment, overriding the entrypoint only for diagnosis. Common causes are a shell-form command, wrong path, missing config/secret, architecture mismatch, bind-mount hiding files, permission error, dependency failure, or an application daemonizing itself.

I correct the image or deployment definition, rebuild an immutable version, and verify startup, health, logs, graceful stop, and restart policy. I do not use `tail -f /dev/null` to hide a broken main process.

## 29. How do you inject environment values during Docker builds, and where should runtime configuration be stored?

**Answer:**

Build arguments are appropriate only for non-secret build choices because `ARG` values can appear in image history, cache metadata, or provenance. Runtime `ENV` defines defaults baked into the image; deployment-time environment variables or mounted configuration override those defaults. Secrets must use BuildKit secret mounts for a required build operation or, preferably, be fetched at runtime through workload identity and a secret manager.

I never bake Dev/UAT/Prod credentials into separate images. I build once, publish an immutable digest to the approved registry, and provide environment-specific non-secret configuration through Kubernetes ConfigMaps, platform settings, or orchestrator variables. Secret values come from Vault/Key Vault/Secrets Manager/external-secret integration with least privilege and rotation.

I verify `docker history`, image configuration, CI logs, SBOM/provenance, and registry access to ensure values were not exposed. If a credential entered a layer, deleting a later file is insufficient; I rotate it and rebuild without the secret.

## 30. Docker versus virtual machines: what is the difference?

**Answer:**

Virtual machines emulate hardware and run a full guest operating system on a hypervisor, giving strong isolation but more startup time and overhead. Containers isolate processes while sharing the host kernel, so they start quickly and package application dependencies more densely. Containers do not replace VM boundaries for every security or operating-system requirement; production isolation also relies on a hardened host, namespaces/cgroups, non-root users, seccomp/AppArmor, image provenance and orchestration policy. Containers are commonly run on VMs in cloud environments.

## 31. What Docker network types exist, and which is common in production?

**Answer:**

Common Docker drivers are `bridge` for single-host container networking, `host` to share the host network namespace, `none` for no network, and `overlay` for multi-host Swarm networking. `macvlan`/`ipvlan` can present containers directly on a physical network but add operational complexity. A user-defined bridge is a sensible default for local or single-host work because it provides DNS and isolation. In production Kubernetes/ECS/service platforms usually provide their own CNI/VPC networking rather than exposing raw Docker network choices; I choose based on isolation, service discovery, policy, observability and failure-domain needs.
