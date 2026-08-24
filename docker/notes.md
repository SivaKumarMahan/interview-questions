# Docker Detailed Interview Notes

---

## Image, Runtime, and Multi-Host Notes

Keep images small. Use a minimal, approved base image, multi-stage builds, a `.dockerignore` file, and pinned dependency versions. Only include what the app needs to run — no build tools, build cache, or secrets in the final image. Having fewer layers isn't the goal by itself; what matters is ordering layers so the build cache works well, and checking that the image still works and passes its vulnerability scan.

Never run `docker system prune` carelessly on a shared or production host — it can delete things that are still needed.

Docker uses two Linux kernel features to isolate containers: namespaces, which give each container its own view of processes, mounts, and networking, and cgroups, which limit how much CPU, memory, and other resources it can use. A container is still just a process sharing the host's kernel, so run it as a non-root user, drop capabilities it doesn't need, and keep the host itself hardened.

Docker Compose is mainly a single-host tool for local development. For running containers across multiple hosts — with scheduling, networking, health checks, and failover — use an orchestrator like Kubernetes, or Docker Swarm where it's specifically supported.

`docker export` saves a container's filesystem but throws away the image's layers and metadata. Use `docker save` and `docker load` instead when you need to move an image around. Better yet, push to an authenticated registry rather than passing tar files by hand.

### Q: If Docker containers are consuming too much disk space, how do you fix it?

**Check disk usage by Docker**

```bash
docker system df
```

This shows how much space is used by:

- Images
- Containers
- Local volumes
- Build cache

**Remove stopped containers**

```bash
docker container prune
```

**Remove unused images, volumes, networks**

```bash
docker image prune
docker volume prune
docker network prune
```

This deletes all unused containers, images, volumes, and networks.

```bash
docker system prune -a --volumes
```

**Check container log size**

```bash
sudo du -sh /var/lib/docker/containers/*/*-json.log | sort -hr | head
```

**Truncate large logs safely:**

```bash
sudo truncate -s 0 /var/lib/docker/containers/<container-id>/<container-id>-json.log
```

---

### Q: What's the difference between `docker system prune` and `docker system prune -a`?

- `docker system prune` removes unused containers, networks, and dangling images (images with no tag).
- `docker system prune -a` goes further and removes all unused images, even ones that are still tagged.

---

### Q: How do you prevent Docker from filling the disk again?

- Prune unused images regularly.
- Set logging limits so container logs can't grow forever.
- Store Docker's data on a dedicated volume or partition, separate from the rest of the OS.

---

### Q: What is the base image in Docker and which base image would you use for Python or Node.js?

A **base image** is the starting point of your Docker image — the first layer everything else is built on top of. Your app, its dependencies, and your configuration all get added on top of it. It defines the runtime environment your app needs, such as the operating system and libraries.

**Using a Python base image:**

```dockerfile
FROM python:3.10-slim
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
CMD ["python", "app.py"]
```

**Using a Node.js base image:**

```dockerfile
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
CMD ["npm", "start"]
```

- For Python, use `python:3.x-slim` or `python:3.x-alpine`.
- For Node.js, use `node:18-slim` or `node:18-alpine`.

---

### Q: How to rollback a failed deployment in Docker and Kubernetes?

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

---

### Q: How do you pass environment variables during docker build commands? What services do you use for storing Docker images?

**Passing environment variables during a Docker build:**

You can pass a value into the build using `--build-arg` with `docker build`. Here's an example:

**Dockerfile:**

```dockerfile
FROM alpine:latest
ARG APP_ENV
ENV APP_ENV=${APP_ENV}
RUN echo "Building for environment: $APP_ENV"
CMD ["sh", "-c", "echo Running in environment: $APP_ENV"]
```

**Build command:**

```bash
docker build --build-arg APP_ENV=production -t myapp:latest .
```

Here, `APP_ENV` is passed in at build time and set as an environment variable inside the container.

**Storing Docker images:**

You can store Docker images in a container registry. Some popular options:

1. **Docker Hub** — a widely used public registry for storing and sharing images.
2. **Amazon Elastic Container Registry (ECR)** — a managed registry on AWS.
3. **Google Container Registry (GCR)** — a private registry on Google Cloud.
4. **Azure Container Registry (ACR)** — a private registry on Microsoft Azure.
5. **Harbor** — an open-source registry with built-in security and identity features.
6. **JFrog Artifactory** — a general-purpose artifact repository that also supports Docker images.

Pick a registry based on how well it fits your cloud provider, its security features, and how well it scales.

---

### Q: Are you aware of security scanning tools? How do you scan Docker images — both during build and at the registry level?

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

---

### Q: What are Docker multi-stage builds, and how do they help optimize Docker images?

Multi-stage builds let you separate the build environment from the runtime environment. In the first stage, you compile or package your app using all the tools you need. In the final stage, you copy just the build output into a lightweight image, like Alpine.

This makes images much smaller, more secure, and faster to deploy. For example, I've taken a 900MB Go build image down to under 50MB using multi-stage builds.

Here's an example Dockerfile using multi-stage builds for a Go application:

```dockerfile
# Stage 1: Build the application
FROM golang:1.20 AS builder
WORKDIR /app
COPY . .
RUN go build -o myapp .   # Compiles your Go app into a single executable binary called myapp.

# Stage 2: Create a lightweight runtime image
FROM alpine:latest
WORKDIR /app
COPY --from=builder /app/myapp .   # Copies only the compiled binary from the first stage.
CMD ["./myapp"]
```

In this example:

- The first stage uses the `golang` image to compile the application.
- The second stage uses the lightweight `alpine` image and copies over only the compiled binary.
- The result is a much smaller final image that contains only what's needed to run the app.

---
