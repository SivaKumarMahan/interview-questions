# Docker: Fundamentals and Architecture

> What Docker is, how images, containers, and the daemon fit together, Docker versus VMs, cgroups, the container lifecycle, and everyday CLI commands.

## Key Concepts

### Core Model

Docker packages an application and its runtime dependencies into an image, then starts isolated container processes from that image. The CLI talks to the Docker daemon, which builds images, manages containers, volumes, and networks, and pulls or pushes them through registries.

An image is a stack of layers that never changes once it's built. A container adds one more layer on top that it can write to, but that writable layer is thrown away when the container is removed. Anything that needs to survive belongs in a volume or an external service, not in the container itself.

### Why Docker

20–30 years ago you had hardware with an installed operating system, and to run an application you compiled the code and resolved all dependencies by hand. Needing another application or more capacity meant buying new hardware and doing fresh installation and configuration.
Virtualization added a layer between hardware and OS — the hypervisor — letting you run multiple isolated virtual machines, each with its own OS. But you still had to install software and dependencies on every VM, and applications were not portable: they worked on some machines and not others.

### What is Docker

In simple terms, Docker is a way to package software so it can run on any machine (Windows, Mac, Linux). It made microservice-based application development practical by giving each service a consistent, portable runtime.

### How Docker works

The Docker Engine runs on top of the host operating system and includes a server process (`dockerd`) that manages containers on the host. Containers isolate applications and their dependencies so they run consistently across different environments.

Three concepts to understand:

- **Dockerfile** — a blueprint to build a Docker image.
- **Docker image** — a template for running containers; it contains all the dependencies needed to execute the code inside a container.
- **Docker container** — just a running process. One image can spin up many containers, in many places, and can be easily shared with anyone.

### Image, Runtime, and Multi-Host Notes

Keep images small. Use a minimal, approved base image, multi-stage builds, a `.dockerignore` file, and pinned dependency versions. Only include what the app needs to run — no build tools, build cache, or secrets in the final image. Having fewer layers isn't the goal by itself; what matters is ordering layers so the build cache works well, and checking that the image still works and passes its vulnerability scan.

Never run `docker system prune` carelessly on a shared or production host — it can delete things that are still needed.

Docker uses two Linux kernel features to isolate containers: namespaces, which give each container its own view of processes, mounts, and networking, and cgroups, which limit how much CPU, memory, and other resources it can use. A container is still just a process sharing the host's kernel, so run it as a non-root user, drop capabilities it doesn't need, and keep the host itself hardened.

Docker Compose is mainly a single-host tool for local development. For running containers across multiple hosts — with scheduling, networking, health checks, and failover — use an orchestrator like Kubernetes, or Docker Swarm where it's specifically supported.

`docker export` saves a container's filesystem but throws away the image's layers and metadata. Use `docker save` and `docker load` instead when you need to move an image around. Better yet, push to an authenticated registry rather than passing tar files by hand.

### Compose and Multi-Stage Builds

Compose describes a multi-container application — its services, networks, ports, volumes, dependencies, and environment variables — in one YAML file. It's convenient for development and testing. Production needs an orchestrator that handles high availability, scheduling, secrets, and upgrades properly.

A multi-stage Dockerfile compiles and tests the app in a stage that has all the build tools, then copies just the runtime output into a small final image. This keeps the image smaller, reduces its attack surface, and keeps compilers, source code, and dependency caches out of production.

### Getting started

Docker must be installed first. On Linux, use your package manager; on Mac/Windows, install Docker Desktop.

```bash
docker run -d -t --name Thor alpine
docker run -d -t busybox
```

These spin up two containers from the minimalist public images `alpine` and `busybox` (stored on Docker Hub).

- `-d` runs the container detached (in the background).
- `-t` attaches a TTY terminal to it.
- `--name` names the container (a random name is assigned if omitted).

The first `docker run` with a given image pulls it from Docker Hub to the local machine.

List containers and images:

```bash
docker ps       # running containers
docker ps -a    # all containers (running and stopped)
docker image ls # images on the local machine
```

Linux images are small compared to full distributions like Ubuntu, Amazon Linux, or CentOS.

### Interacting with containers

`docker exec` runs a command inside a running container. `-it` opens an interactive session; the shell can be `sh`, `bash`, `zsh`, etc.

```bash
# docker exec -it <container id> <shell>

docker exec -t Thor ls          # run a command in the container named Thor
docker exec -t 8ad10d1d0660 free -m   # check memory usage by container id

docker exec -it 16fb1c59fbea sh # interactive shell; type "exit" to leave
```

### Starting, stopping, and deleting containers

```bash
docker stop <container name or id>   # stop a running container
docker start <container name or id>  # start a stopped container

# remove: stop first, then rm
docker stop 16fb1c59fbea
docker rm 16fb1c59fbea

docker rm -f Thor  # or force-delete a running container
```

## Interview Questions

### 1. What is Docker? *(scenario)*

Docker is a containerization platform. It packages an application together with its dependencies, libraries, and configuration into a portable **image**, which then runs as an isolated **container**.

Containers share the host machine's kernel instead of booting a full guest operating system, using two Linux features — namespaces for isolation and cgroups for resource limits. That's what makes them lightweight and able to start in milliseconds. It also solves the classic "works on my machine" problem, because the same image runs the same way everywhere, from a developer's laptop to production.

### 2. Have you built Docker containers? For what use case?

**Answer:**

Yes. A typical use case is packaging a web API so it runs the same way on developer laptops, in CI, and in Kubernetes. I write a multi-stage Dockerfile, run the container as a non-root user, expose only the port the app actually needs, add a health check where it makes sense, and keep configuration outside the image.

In CI, the build starts from a pinned base image, runs the tests, generates an SBOM (a list of everything packaged inside the image), scans it with Trivy, and tags it with the commit SHA. That exact build is pushed to a private registry and never changes afterward. Kubernetes then deploys that same build with resource limits, health probes, a locked-down security context, and secrets pulled from outside the image.

Before it ships, I check image size and layer count, the scan results, startup time, health checks, logs, how it handles shutdown signals, and whether it still works with a read-only filesystem. This is what avoids "works on my machine" problems — one build, tested once, runs everywhere.

### 3. Docker versus virtual machines: what is the difference?

**Answer:**

A virtual machine emulates hardware and runs a full guest operating system on top of a hypervisor. That gives strong isolation, but at the cost of more startup time and overhead. A container isolates a process while sharing the host's kernel, so it starts fast and packs application dependencies much more densely.

Containers don't replace every security boundary a VM gives you. Production security still relies on a hardened host, namespaces and cgroups for isolation, non-root users, tools like seccomp and AppArmor, verified image provenance, and orchestration-level policy. In practice, containers are usually run on top of VMs in cloud environments anyway.

### 4. What are cgroups?

**Answer:**

Cgroups are a Linux feature that tracks and limits how much CPU, memory, process count, and I/O a group of processes can use. Container runtimes use cgroups for resource limits, while a separate feature, namespaces, handles isolating what a container can see — its own processes, network, and mounts.

Docker's flags translate directly into cgroup settings:

```bash
docker run --memory=512m --cpus=1.5 --pids-limit=200 app
```

Go over the memory limit and the container gets killed (an OOM kill); go over the CPU limit and it just gets throttled. I check `docker stats`, the container's state and exit code, host resource pressure, and cgroup metrics when something looks wrong. Limits protect the host, but they should be based on real measurements — set them too low and the app becomes unstable for no good reason.

### 5. What is the lifecycle of a Docker container?

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

### 6. How do you list running containers and all containers, including stopped ones?

**Answer:**

`docker ps` (or `docker container ls`) shows running containers. `docker ps -a` (or `docker container ls --all`) also shows containers that were created, exited, or are dead. I usually add formatting or filters to make the output more useful:

```bash
docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}'
docker ps -a --filter status=exited
```

The status and exit code tell me what to check next. I look at `docker inspect`, `docker logs`, and any application or host metrics before restarting or deleting anything — an exited container can hold evidence you'll need to figure out what actually went wrong.

### 7. How do you enter a running Docker container from the command line?

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

### 8. How do you copy a file from a container to the host?

**Answer:**

```bash
docker cp mycontainer:/var/log/app/error.log ./error.log
docker cp ./config.yaml mycontainer:/tmp/config.yaml
```

The container can be running or stopped. I check the path, permissions, free disk space, and whether the file might contain secrets or personal data before copying it. For logs or data that's actively being written, a plain copy can catch it mid-write — use the application's own export or snapshot feature when that matters.

Copying a file into a running container is a debugging move, not a way to manage configuration — the change disappears the moment the container is replaced. Anything that needs to stick around belongs in the image, a config file, or a volume, deployed properly.
