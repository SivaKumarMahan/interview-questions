# Docker Detailed Interview Notes

---

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

- `docker system prune` → removes unused objects
- `docker system prune -a` → also removes all unused images, not just dangling ones.

---

### Q: How do you prevent Docker from filling the disk again?

- Regularly prune unused images
- Use logging limits
- Store Docker data on a dedicated volume or partition

---

### Q: What is the base image in Docker and which base image would you use for Python or Node.js?

A **base image** is the starting point or foundation layer for your Docker image.
It's the first layer in your image on top of which you install your app, dependencies and configurations.
It defines the runtime environment — such as the operating system and libraries — your app needs.

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

If a deployment using a new Docker image fails, you can rollback by running a container using a previously working image version.

**Run the previous working version**

```bash
docker run -d -p 8080:80 <image_name>:<previous_tag>
docker tag <image_name>:<previous_tag> <image_name>:stable   # tag a stable version
```

Always version your images (e.g., `myapp:v1`, `myapp:v2`) so you can easily revert.

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

**Passing Environment Variables during Docker Build:**

You can pass environment variables during the Docker build process using the `--build-arg` flag with the `docker build` command.
Here's an example:

**Dockerfile:**

```dockerfile
FROM alpine:latest
ARG APP_ENV
ENV APP_ENV=${APP_ENV}
RUN echo "Building for environment: $APP_ENV"
CMD ["sh", "-c", "echo Running in environment: $APP_ENV"]
```

**Build Command:**

```bash
docker build --build-arg APP_ENV=production -t myapp:latest .
```

In this example, the `APP_ENV` variable is passed during the build process and set as an environment variable inside the container.

**Storing Docker Images:**

You can store Docker images in various container registries. Some popular options include:

1. **Docker Hub**: A widely used public container registry that allows you to store and share Docker images.
2. **Amazon Elastic Container Registry (ECR)**: A fully managed Docker container registry provided by AWS.
3. **Google Container Registry (GCR)**: A private container registry for storing Docker images on Google Cloud Platform.
4. **Azure Container Registry (ACR)**: A private Docker registry service provided by Microsoft Azure.
5. **Harbor**: An open-source container image registry that provides security, identity, and management features.
6. **JFrog Artifactory**: A universal artifact repository manager that supports Docker images along with other package types.

Choose a registry based on your project requirements, such as integration with your cloud provider, security features, and scalability needs.

---

### Q: Are you aware of security scanning tools? How do you scan Docker images — both during build and at the registry level?

I implement vulnerability scanning at two stages — during image build and in the registry.
During build, I use **Trivy** integrated into CI/CD pipelines to scan Docker images for OS and dependency-level vulnerabilities. This ensures we catch issues before deployment.
After pushing to Azure Container Registry, I rely on **Microsoft Defender for Containers**, which automatically scans all images and surfaces CVEs in the Azure Security Center.
For enforcement, builds fail automatically if Trivy finds any High or Critical severity vulnerabilities.

**Trivy Scan during Build:**

1. Install Trivy in your CI/CD environment.
2. Add a scan step in your pipeline after building the Docker image:

```bash
# Install Trivy
sudo apt install trivy -y

# Scan Docker image after build
docker build -t myapp:latest .
trivy image myapp:latest
```

**Output Example:**

```text
myapp:latest (ubuntu 22.04)
============================
Total: 8 (CRITICAL: 2, HIGH: 3, MEDIUM: 3)
```

Integrate this step in:

- Jenkins pipeline (`stage('Security Scan')`)
- Azure DevOps YAML (`bash: trivy image $(imageName)`)
- GitHub Actions workflow

**Fail the build automatically if severity ≥ High:**

```bash
trivy image --exit-code 1 --severity HIGH,CRITICAL myapp:latest
```

**Docker Native Scan (Powered by Snyk):**

1. Use Docker's built-in scanning feature if available in your environment.
2. Run the scan command:

```bash
docker scan myapp:latest
```

Integrates natively with Docker Desktop and Docker Hub.

**Registry-Level Scanning:**

**Azure Container Registry (ACR)**

- Use Microsoft Defender for Containers to automatically scan images after push.
- It identifies CVEs and integrates with Azure Security Center.

Enable scanning:

- Go to `ACR` → `Settings` → `Defender for Cloud`
- Enable Vulnerability Assessment

Run on-demand scan:

```bash
az acr run --cmd "acr scan show --name <registry>" --registry <acrName>
```

View results under `Security` → `Vulnerabilities`

---

### Q: What are Docker multi-stage builds, and how do they help optimize Docker images?

Docker multi-stage builds let us separate the build environment from the runtime environment.
In the first stage, we compile or package our app using all necessary tools, and in the final stage, we copy only the build output into a lightweight image like Alpine.
This significantly reduces image size, improves security, and speeds up deployments.
For example, I've reduced a 900MB Go build image to under 50MB using multi-stage builds.

Here's an example `Dockerfile` using multi-stage builds for a Go application:

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

- The first stage uses the `golang` image to compile the Go application.
- The second stage uses the lightweight `alpine` image and copies only the compiled binary from the builder stage.
- This results in a much smaller final image that contains only what's necessary to run the application.

---
