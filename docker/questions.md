## 1. Have you built Docker containers? For what use case?

**Answer:**

Yes. A typical use case is packaging a web API so it runs the same way on developer laptops, in CI, and in Kubernetes. I write a multi-stage Dockerfile, run the container as a non-root user, expose only the port the app actually needs, add a health check where it makes sense, and keep configuration outside the image.

In CI, the build starts from a pinned base image, runs the tests, generates an SBOM (a list of everything packaged inside the image), scans it with Trivy, and tags it with the commit SHA. That exact build is pushed to a private registry and never changes afterward. Kubernetes then deploys that same build with resource limits, health probes, a locked-down security context, and secrets pulled from outside the image.

Before it ships, I check image size and layer count, the scan results, startup time, health checks, logs, how it handles shutdown signals, and whether it still works with a read-only filesystem. This is what avoids "works on my machine" problems — one build, tested once, runs everywhere.

## 2. What is the lifecycle of a Docker container?

**Answer:**

An image is built or pulled. `docker create` sets up a container's writable layer and configuration without starting it. `docker start` runs the configured process. From there it can pause, restart, or stop. `docker rm` deletes the container entirely. Any data written to the container's writable layer disappears when it's removed, so anything you need to keep must live in a volume or an external service.

The container stays alive only as long as its main process (PID 1) is running. `docker stop` sends SIGTERM, waits a bit, then sends SIGKILL if the process hasn't exited — so your application needs to handle that signal and shut down cleanly.

```bash
docker pull nginx:1.27
docker create --name web nginx:1.27
docker start web
docker logs web
docker stop web
docker rm web
```

When something fails, I check the container's exit code and state, whether it was killed for using too much memory, its logs, events, configuration, mounts, network, and health status — before I just restart it and hope.

## 3. How do you create a custom Docker image?

**Answer:**

I write a Dockerfile, add a `.dockerignore` file, pin a trusted base image, then build, test, scan, and publish a versioned image.

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

I check that tests pass, that the app starts correctly, which user it runs as, what files are in the image, its size and layer count, how it handles shutdown, and its scan results. Credentials should never go into build arguments or image layers — if a private dependency truly needs a credential during the build, use a BuildKit secret mount instead, which keeps it out of the final image and its history.

## 4. How do you write a production-ready Dockerfile?

**Answer:**

I use multi-stage builds so compilers and build dependencies never end up in the runtime image. I pin an approved base image, install only what's needed, copy dependency files before the source code so the build cache works well, and run as a non-root user.

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

I use the exec form of `ENTRYPOINT`/`CMD` (the `["cmd", "arg"]` array style, not a shell string), a `.dockerignore` file, no secrets baked in, as few writable paths as possible, labels and an SBOM, and vulnerability scanning. Health checking is mostly the orchestrator's job, not the image's.

I also test the image under the same restrictions it'll run under in production — non-root, read-only filesystem, and resource limits.

## 5. What is the difference between `ADD` and `COPY` in a Dockerfile?

**Answer:**

`COPY` copies local files or directories from the build context into the image. `ADD` does that too, but also has extra behavior — it can automatically extract local tar archives and fetch some remote URLs. I prefer `COPY` because its behavior is obvious just by reading it, which makes the Dockerfile easier to audit.

```dockerfile
COPY package.json package-lock.json ./
```

For remote files, I'd rather download them in a controlled `RUN` step with TLS and a checksum check, or fetch them before the build starts. A strict `.dockerignore` file keeps large or sensitive files out of the build context in the first place.

Neither `COPY` nor `ADD` should ever pull in `.git`, local credentials, or build output you don't need.

## 6. What is the difference between `RUN`, `CMD`, and `ENTRYPOINT`?

**Answer:**

- `RUN` runs during the build and creates a new image layer.
- `ENTRYPOINT` sets the main command the container runs.
- `CMD` provides default arguments (or a default command) that are easy to override at runtime.

```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends curl \
 && rm -rf /var/lib/apt/lists/*
ENTRYPOINT ["/usr/local/bin/myapp"]
CMD ["--port", "8080"]
```

Running `docker run image --port 9090` overrides the `CMD` arguments while keeping the `ENTRYPOINT`. I always use the JSON/exec array form rather than a plain shell string, so the app runs directly as PID 1 and receives shutdown signals correctly. A shell-form command inserts an extra shell process in between, which can interfere with signal handling.

## 7. What is the difference between `CMD` and `ENTRYPOINT`?

**Answer:**

`ENTRYPOINT` makes the container behave like a specific program. `CMD` supplies the default arguments (or command) for it. Arguments you pass on `docker run` replace `CMD`, but replacing `ENTRYPOINT` requires the `--entrypoint` flag.

For an application image, I'd write:

```dockerfile
ENTRYPOINT ["/app/server"]
CMD ["--config", "/etc/server/config.yaml"]
```

For a general-purpose tool image, `CMD` alone is often more flexible. I avoid wrapper shell scripts unless they end with `exec "$@"`, so signals still reach the actual application instead of being swallowed by the wrapper. I also test `docker stop` directly to confirm the container shuts down cleanly.

## 8. What happens when you write `COPY .` in a Dockerfile?

**Answer:**

It copies the entire build context — everything in that directory except what `.dockerignore` excludes — into the image. That can pull in source code, Git history, credentials, test data, and large files you didn't mean to include. It also means any small change anywhere in that directory invalidates the build cache for that layer.

A strict `.dockerignore` file plus copying only what you need, in the right order, avoids this:

```dockerfile
COPY package.json package-lock.json ./
RUN npm ci
COPY src ./src
```

I check the build context size, build logs, and image layers (using `docker history` or a tool like Dive) to catch anything that shouldn't be there. If a secret ever ends up in a layer, deleting it in a later layer isn't enough — the old layer still has it in the image's history. The fix is to rotate the secret and rebuild from a clean history.

## 9. How do you optimize a Dockerfile for performance and security?

**Answer:**

I start from a small, trusted, pinned base image, use multi-stage builds, lock dependency versions, order instructions so the cache works well, use BuildKit cache mounts, add a `.dockerignore` file, run as non-root, install only what's needed, use exec-form commands, and never bake in secrets. Package caches are cleaned up in the same layer they were created in, and I avoid leaving unnecessary shells or tools in the runtime image.

CI builds the image reproducibly, tests it, generates an SBOM, scans it, signs it, and publishes a fixed, versioned build. At runtime I add a read-only root filesystem, drop capabilities, apply seccomp, set resource limits, and restrict network access where the app allows it.

I measure build time, cache hit rate, image size, startup time, vulnerability count, and actual application performance. Alpine isn't automatically the best choice — its different C library (musl) can cause subtle compatibility issues, so a "slim" or distroless image is sometimes the safer bet.

## 10. Explain Docker image layering and how it can cause cache busting.

**Answer:**

Most Dockerfile instructions create a new layer, and each layer's build cache depends on the layers before it plus its own inputs.

If `COPY . .` happens before you install dependencies, changing even one source file invalidates that layer and every layer after it — so dependencies get reinstalled from scratch every time.

A better order:

```dockerfile
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src ./src
```

Put the steps that change often (like copying source code) later in the file, and pin your dependencies. I do deliberately refresh the base image on a schedule with `--pull`, so security patches still get in even though the cache is otherwise "sticky."

Caching makes builds faster, but I don't let a stale cache block a needed patch. `docker history` and build timing help spot exactly where cache is being invalidated.

## 11. What are Docker volumes and bind mounts, and when would you use each?

**Answer:**

A named volume is managed by Docker and is the right choice for data a container needs to keep. A bind mount points at a specific path on the host — handy for local development or config files, but it ties the container tightly to the host's folder layout and permissions.

```bash
docker volume create dbdata
docker run -v dbdata:/var/lib/postgresql/data postgres
docker run --mount type=bind,src="$PWD/config",dst=/app/config,readonly app
```

For anything persistent, I plan backup, restore, ownership, encryption, and capacity up front. Removing a container doesn't automatically remove its volume. In an orchestrated environment I use the platform's own persistent volumes rather than assuming a local Docker volume gives high availability.

## 12. What is Docker Compose?

**Answer:**

Docker Compose describes a multi-container application — its services, networks, volumes, environment variables, and dependencies — in one YAML file, and runs it with `docker compose`.

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

It's great for local development, integration tests, and small single-host setups. Note that `depends_on` only waits for the container to start, not for the database inside it to actually be ready — you still need a health check or a retry loop for that.

For production running across multiple nodes, an orchestrator like Kubernetes or ECS is normally what handles scheduling, high availability, secrets, and scaling.

## 13. How do you run multi-container applications in production without Compose?

**Answer:**

I use an orchestrator such as Kubernetes, ECS, or AKS. Each component gets its own image, its own Deployment or task definition, a way for other services to find it, its own configuration and identity, and its own scaling, health, and resource settings.

The delivery pipeline publishes signed, fixed images, and then Helm, plain manifests, or GitOps declares how the application should run. Databases usually run as a managed service rather than as a container, and secrets come from a dedicated secret manager.

I make sure there's redundancy, health probes, a rolling or canary rollout strategy, network policies, monitoring, logging, backups, and a disaster recovery plan. Compose is a good way to model services locally, but production needs a real cluster scheduler and the operational pieces around it.

## 14. How do you copy a file from a container to the host?

**Answer:**

```bash
docker cp mycontainer:/var/log/app/error.log ./error.log
docker cp ./config.yaml mycontainer:/tmp/config.yaml
```

The container can be running or stopped. I check the path, permissions, free disk space, and whether the file might contain secrets or personal data before copying it. For logs or data that's actively being written, a plain copy can catch it mid-write — use the application's own export or snapshot feature when that matters.

Copying a file into a running container is a debugging move, not a way to manage configuration — the change disappears the moment the container is replaced. Anything that needs to stick around belongs in the image, a config file, or a volume, deployed properly.

## 15. What are cgroups?

**Answer:**

Cgroups are a Linux feature that tracks and limits how much CPU, memory, process count, and I/O a group of processes can use. Container runtimes use cgroups for resource limits, while a separate feature, namespaces, handles isolating what a container can see — its own processes, network, and mounts.

Docker's flags translate directly into cgroup settings:

```bash
docker run --memory=512m --cpus=1.5 --pids-limit=200 app
```

Go over the memory limit and the container gets killed (an OOM kill); go over the CPU limit and it just gets throttled. I check `docker stats`, the container's state and exit code, host resource pressure, and cgroup metrics when something looks wrong. Limits protect the host, but they should be based on real measurements — set them too low and the app becomes unstable for no good reason.

## 16. What are dangling Docker objects?

**Answer:**

A dangling image is one with no tag pointing to it — usually left behind after you rebuild an image with the same tag as before. Unused containers, networks, volumes, and build cache can also pile up and use disk space, but "dangling" specifically refers to untagged images.

```bash
docker image ls --filter dangling=true
docker system df -v
docker image prune
```

I check what's there before cleaning anything up. A volume might still hold important data, and an old image might be exactly what you'd need to roll back to — so I keep some retention around and treat registry images, not local ones, as the real source of truth.

Any automated cleanup should have filters, disk thresholds, exclusions, logging, and a check that it isn't touching anything a live workload depends on.

## 17. How do you delete all Docker resources in one command?

**Answer:**

I wouldn't run a broad "delete everything" command on a shared or production host. `docker system prune -a --volumes` removes every unused container, network, image, build cache entry, and unused volume after you confirm — and that can destroy data or images you actually needed for a rollback.

My actual approach: run `docker system df -v` to see what's using space, check what's still in use, back up any volume that matters, and then prune specific object types using age or label filters. In production, I'd rather replace a host outright when it needs cleaning than run an emergency deletion on a live one.

After cleanup, I check that running containers are unaffected, disk and inode usage looks right, the app is healthy, and images can still be pulled. Anything destructive gets logged and approved beforehand.

## 18. How do you handle secrets inside containers?

**Answer:**

Secrets never go into images, into a Dockerfile's `ARG` or `ENV`, into layers, or into source code. At runtime, they come from Kubernetes Secrets combined with an external secret manager or CSI driver, from Docker secrets where that's supported, or from a short-lived mounted file.

Where possible, I use workload identity (the platform proving who the workload is) instead of a long-lived cloud access key.

Secret files get narrow file permissions and a short lifecycle, and logs and diagnostics are set up to redact them. Image scanning can catch an accidentally-included secret, but once one is found, deleting it from a later layer doesn't remove it from history — the only real fix is to rotate the secret immediately and rebuild.

I test that the image's history and any exported copy contain no secret, that only authorized workloads can read it, and that rotating a secret doesn't cause downtime.

## 19. How do you enforce policy as code for Docker security?

**Answer:**

CI checks Dockerfiles, images, and deployment configuration against a set of rules, using tools like OPA/Conftest, Checkov, Hadolint, Trivy, and Kubernetes admission policies.

Typical rules require: no root user, only approved registries and base images, images referenced by a fixed digest rather than a mutable tag, no privileged mode, dropped capabilities, a read-only filesystem, and a vulnerability threshold that must be met.

I test each rule against both compliant and non-compliant examples, version the rules themselves, give clear guidance on how to fix a violation, and allow a time-limited exception process rather than a permanent bypass. Signing and build provenance — a record of where an image came from and how it was built — get checked again at deployment time.

Policy as code works alongside runtime controls, RBAC, network segmentation, monitoring, and regular patching — it's one layer, not the whole defense. I usually start new rules in audit-only mode so I can see their impact before actually blocking anything.

## 20. How do you handle multi-cloud Docker deployments with compliance restrictions?

**Answer:**

I build one approved image in a single controlled pipeline, generate its SBOM and provenance record, scan and sign it, and then replicate that exact same digest to approved regional registries in each cloud. The image content stays identical everywhere; only cloud-specific deployment configuration differs.

Controls cover where data can live, where the registry is located and how it's encrypted, identity federation across clouds, private network connectivity, vulnerability policy, who holds the signing keys, audit log retention, and runtime security. Terraform modules and policy-as-code enforce a common baseline, and each cloud gets its own tightly scoped identities and state.

I test that unapproved regions, unapproved registries, and unsigned images all get rejected. Disaster recovery planning has to account for registry availability too — replication needs to stay trustworthy, not just fast, and can't be used as an excuse to skip compliance checks.

## 21. You need live patching of a Docker host kernel without downtime. How do you achieve it?

**Answer:**

My default approach is redundancy and rotation: take one host out of scheduling and load balancing, move its containers to healthy hosts, patch and reboot it, verify it's healthy, then bring it back. This handles any patch, including ones that require a reboot, and it also proves your failover actually works.

Kernel live-patching tools — Canonical Livepatch, kpatch, or a cloud provider's own offering — can apply some security fixes without a reboot, but not every patch qualifies for live patching. I check kernel and patch compatibility first, test it on a lower environment, monitor closely, and still schedule a periodic reboot onto a fully updated kernel.

On a single host, you can't truly guarantee zero downtime for the application — the architecture needs another instance to fail over to.

## 22. What happens if you delete `/var/lib/docker/overlay` on a Docker host?

**Answer:**

It can corrupt or destroy image data and container writable layers, and containers will start failing. I never manually delete anything inside Docker's internal storage directory while the daemon is using it.

If the real problem is a full disk, the safe path is `docker system df` to see what's using space, then identifying objects, preserving volumes, and using the proper prune or removal commands with approval — not touching the internals directly.

If that directory has already been deleted, I stop making further changes, preserve logs as evidence, check whether any volumes were affected separately, and usually rebuild the host from known-good configuration and re-pull the same fixed images, rather than attempting a risky manual repair.

I then restore any persistent application data from a proper volume backup, validate the workloads, bring the host back into service, and add capacity alerts and automated cleanup so this doesn't happen again. Docker's internal storage directory is not something an operator should ever touch by hand.

## 23. How do you enter a running Docker container from the command line?

**Answer:**

I check what shell the container actually has, then use `docker exec` — not `docker attach` — for normal investigation:

```bash
docker ps
docker exec -it <container-name> /bin/sh
# Use /bin/bash only when the image contains Bash.
```

`exec` starts a brand-new process inside the container. `attach` connects directly to the container's main process, and typing into it or hitting Ctrl+C can accidentally send a signal that disrupts the app.

A minimal or distroless production image may have no shell at all. In that case, I check logs, metadata, and mounts from the host or with approved debugging tools instead of trying to modify the image from inside.

Access to the Docker socket is effectively root access to the whole host, so it's restricted and audited. If something needs fixing, I don't patch it live inside the container — I fix the Dockerfile or configuration, build a new image, redeploy it, and verify the fix.

## 24. How do you list running containers and all containers, including stopped ones?

**Answer:**

`docker ps` (or `docker container ls`) shows running containers. `docker ps -a` (or `docker container ls --all`) also shows containers that were created, exited, or are dead. I usually add formatting or filters to make the output more useful:

```bash
docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}'
docker ps -a --filter status=exited
```

The status and exit code tell me what to check next. I look at `docker inspect`, `docker logs`, and any application or host metrics before restarting or deleting anything — an exited container can hold evidence you'll need to figure out what actually went wrong.

## 25. How do you remove all containers and images safely?

**Answer:**

First, I get clear on exactly what needs removing and make sure nothing stateful gets caught up in it. Containers can be stopped and removed explicitly, and an image can only be removed once nothing depends on it:

```bash
docker container ls -aq
docker image ls -q
```

On a disposable lab machine, commands like `docker container prune` and `docker image prune -a` are safer than a broad shell one-liner, because they show you the scope and ask for confirmation.

In production, I never blindly remove every container or run `docker system prune --volumes` — a named volume might hold real application data, running services could get interrupted, and useful evidence could be lost.

Instead, I check `docker system df`, remove only the stopped containers and unused images that are actually approved for removal, confirm the registry still has the images we might need, and keep volume backups. Ongoing cleanup should run on a retention policy with disk alerts, not as an emergency measure — and in production I'd rather replace a host than deep-clean a live one.

## 26. How many `CMD` instructions can a Dockerfile contain, and what happens when there are multiple?

**Answer:**

A Dockerfile can technically contain multiple `CMD` instructions, but only the last one in the final build stage actually takes effect — the earlier ones are silently overwritten, and having more than one usually just makes the Dockerfile confusing to read.

Each stage of a multi-stage build can define its own `CMD`, but only the final stage's configuration matters at runtime.

I normally use one exec-form `ENTRYPOINT` for the actual program and one exec-form `CMD` for its default arguments:

```dockerfile
ENTRYPOINT ["java", "-jar", "/app/app.jar"]
CMD ["--spring.profiles.active=prod"]
```

Arguments passed to `docker run image ...` replace `CMD`; the `--entrypoint` flag is needed to replace `ENTRYPOINT` itself. The exec form keeps signal handling working correctly, which matters for a clean shutdown. I confirm the final result with `docker image inspect` and by actually testing `docker stop`.

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

The build stage has Maven, the source code, and everything needed to compile. The runtime stage only has a JRE and the final JAR — nothing else carries over. Copying `pom.xml` in before the source code means dependency downloads stay cached across builds.

A `.dockerignore` file excludes `.git`, local build output, credentials, and anything else that doesn't belong in the build context. In production, I'd pin the base images by digest, scan and sign the result, set sensible JVM and container resource limits, and test that shutdown signals and health checks both work.

## 28. What should you do when a Docker container exits immediately after startup?

**Answer:**

I check `docker ps -a` for the exit code, run `docker logs <container>`, and use `docker inspect` to look at the command, entrypoint, environment, mounts, health status, whether it was OOM-killed, and any runtime errors. Exit code 0 usually just means the main process finished normally — a container only stays running while its main process (PID 1) is still running.

Exit code 1 usually points to an application or config error, 126/127 to a bad command or permissions problem, and 137 usually means it was killed — often by SIGKILL or an out-of-memory kill.

I re-run the exact same image with the intended configuration in a safe environment, only overriding the entrypoint if I need to poke around for diagnosis.

Common causes: a shell-form command that breaks signal handling, a wrong file path, a missing config value or secret, a CPU architecture mismatch, a bind mount accidentally hiding files that should be there, a permissions error, a failed dependency, or the app trying to daemonize itself instead of staying in the foreground.

Once I find the cause, I fix the image or deployment config, rebuild, and re-verify startup, health, logs, clean shutdown, and the restart policy. I never just run `tail -f /dev/null` to paper over a broken main process.

## 29. How do you inject environment values during Docker builds, and where should runtime configuration be stored?

**Answer:**

Build arguments (`ARG`) should only ever be used for non-secret build choices, because their values can end up in the image's history, build cache metadata, or provenance record. Runtime `ENV` sets defaults baked into the image, and those can still be overridden by environment variables or mounted config at deploy time.

If a build genuinely needs a secret — say, to pull a private dependency — use a BuildKit secret mount, not `ARG`. Better still, fetch secrets at runtime through workload identity and a secret manager.

I never bake separate Dev, UAT, and Prod credentials into separate images. I build one image, publish it under a fixed digest to the approved registry, and supply environment-specific but non-secret configuration through Kubernetes ConfigMaps, platform settings, or orchestrator variables. Actual secret values come from Vault, Key Vault, Secrets Manager, or an external-secret integration, scoped to only the access they need and rotated regularly.

I check `docker history`, the image's configuration, CI logs, the SBOM and provenance record, and registry access to make sure nothing sensitive leaked out. If a credential ever does end up in a layer, deleting the file later isn't enough — I rotate it immediately and rebuild without it.

## 30. Docker versus virtual machines: what is the difference?

**Answer:**

A virtual machine emulates hardware and runs a full guest operating system on top of a hypervisor. That gives strong isolation, but at the cost of more startup time and overhead. A container isolates a process while sharing the host's kernel, so it starts fast and packs application dependencies much more densely.

Containers don't replace every security boundary a VM gives you. Production security still relies on a hardened host, namespaces and cgroups for isolation, non-root users, tools like seccomp and AppArmor, verified image provenance, and orchestration-level policy. In practice, containers are usually run on top of VMs in cloud environments anyway.

## 31. What Docker network types exist, and which is common in production?

**Answer:**

The common Docker network drivers are `bridge` for single-host container networking, `host` for sharing the host's own network stack directly, `none` for no networking at all, and `overlay` for multi-host networking under Swarm. `macvlan` and `ipvlan` can put containers directly on the physical network, but they add real operational complexity.

A user-defined bridge network is a sensible default for local or single-host work, since it gives you both DNS-based service discovery and isolation.

In production, platforms like Kubernetes and ECS usually bring their own networking layer (a CNI plugin or VPC networking) instead of exposing Docker's raw network types directly. The right choice comes down to isolation needs, service discovery, policy requirements, observability, and how failures should be contained.
