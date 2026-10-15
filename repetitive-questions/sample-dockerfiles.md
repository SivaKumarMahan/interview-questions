# Repetitive Interview Questions

## Write a sample Dockerfile and explain it

**Interviewer:** Can you write and explain a Dockerfile used in your project?

**Candidate:**

A Dockerfile contains the steps used to build a container image. My project has a React frontend and a Spring Boot backend, so I use a separate Dockerfile for each — both use a multi-stage build so the final image only contains the built output, not the build tools.

The main practices I follow are:

- Use a trusted and versioned base image.
- Use a multi-stage build when the source must be compiled.
- Copy only required files.
- Run as a non-root user.
- Keep secrets outside the image.
- Use a `.dockerignore` file.
- Scan the final image.

## Example 1: Spring Boot with Maven

```dockerfile
FROM maven:3.9.9-eclipse-temurin-21 AS build

WORKDIR /workspace

COPY pom.xml .
RUN mvn -B dependency:go-offline

COPY src ./src
RUN mvn -B clean verify

FROM eclipse-temurin:21-jre-jammy

RUN groupadd --system appgroup \
    && useradd --system --gid appgroup --uid 10001 appuser

WORKDIR /app

COPY --from=build --chown=appuser:appgroup \
  /workspace/target/orders-service.jar /app/app.jar

USER 10001

EXPOSE 8080

ENTRYPOINT ["java", "-jar", "/app/app.jar"]
```

### Explanation

- The first `FROM` stage uses Maven and Java to build and test the application.
- `WORKDIR` sets the directory for the following commands.
- `pom.xml` is copied and dependencies are downloaded before the source code. When only code changes, Docker reuses the cached dependency layer.
- `RUN mvn -B clean verify` compiles, tests, and packages the application.
- The second `FROM` starts a smaller runtime image.
- `COPY --from=build` copies only the final JAR from the build stage.
- `USER 10001` runs the application as a non-root user.
- `EXPOSE 8080` documents the application port.
- `ENTRYPOINT` starts the Spring Boot application.

The final image does not contain Maven, source code, or build files.

Build and run:

```bash
docker build -t orders-service:1.0.0 .
docker run --rm -p 8080:8080 orders-service:1.0.0
```

## Example 2: React with NGINX

```dockerfile
FROM node:22-alpine AS build

WORKDIR /workspace

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

FROM nginxinc/nginx-unprivileged:1.27-alpine

COPY --from=build --chown=101:101 \
  /workspace/dist /usr/share/nginx/html

EXPOSE 8080

CMD ["nginx", "-g", "daemon off;"]
```

### Explanation

- The Node.js stage installs dependencies and creates the static website.
- The NGINX stage receives only the built files.
- NGINX serves the files on port 8080.
- The unprivileged NGINX image avoids running as root.

If the project creates a `build` directory instead of `dist`, I change the source path to match the project.

## How the frontend talks to the backend

**Interviewer:** How is the React frontend connected to the Spring Boot backend?

**Candidate:** The React app runs in the user's browser and calls the backend REST APIs over HTTPS. It never connects to the database. In AKS, both run as separate Deployments and Services behind one ingress:

```text
User -> Application Gateway / Ingress
          /      -> frontend Service (NGINX + React files)
          /api/* -> backend Service (Spring Boot) -> PostgreSQL
```

Because both use the same host name, React simply calls `fetch("/api/orders")`. No backend URL is hard-coded in the image, and there is no CORS problem.

The pipeline builds two images (`frontend:<build-id>` and `backend:<build-id>`), pushes them to ACR, and deploys both with Helm.

## `.dockerignore`

I add a `.dockerignore` file so unnecessary or sensitive files are not sent to the Docker build:

```text
.git
.env
*.log
node_modules
target
.idea
.vscode
```

## `COPY` vs. `ADD`

I normally use `COPY` because it has simple and predictable behavior.

`ADD` has extra features, such as extracting local archives. I use it only when that behavior is intentionally required.

## `CMD` vs. `ENTRYPOINT`

- `ENTRYPOINT` defines the main executable.
- `CMD` provides the default command or arguments.
- Arguments given to `docker run` **replace** `CMD` but are **appended** to `ENTRYPOINT`.

Used together, `ENTRYPOINT` is the fixed program and `CMD` is its default argument:

```dockerfile
ENTRYPOINT ["java", "-jar", "/app/app.jar"]
CMD ["--spring.profiles.active=default"]
```

```bash
docker run orders-service                                   # uses the CMD default
docker run orders-service --spring.profiles.active=prod     # replaces CMD only
docker run --entrypoint sh -it orders-service               # replaces ENTRYPOINT
```

In Kubernetes, `command:` overrides `ENTRYPOINT` and `args:` overrides `CMD`.

Both should normally use JSON (exec) form. In shell form, `/bin/sh` becomes PID 1 and may not pass `SIGTERM` to the application, so the Pod does not shut down gracefully.

## Configuration and secrets

I do not copy Production configuration or secrets into the image.

At runtime:

- Normal configuration comes from environment variables or ConfigMaps.
- Secrets come from Azure Key Vault through workload identity or the CSI driver.

The same image can then run in Development, Testing, and Production.

### Secrets needed during the build

Sometimes the build needs a secret, for example a token for a private npm or Maven feed. I do not use `ARG` or `ENV` for it, because those values can be seen with `docker history` or in the image metadata. A multi-stage build does not fully protect it either: the build stage can still be in the build cache.

I use a BuildKit secret mount. The secret is available only for that one `RUN` step and is never written to a layer:

```dockerfile
# syntax=docker/dockerfile:1
RUN --mount=type=secret,id=npm_token \
    NPM_TOKEN=$(cat /run/secrets/npm_token) npm ci
```

```bash
docker build --secret id=npm_token,env=NPM_TOKEN -t frontend:1.0.0 .
```

In the pipeline, Trivy (with secret scanning) and Gitleaks check the image and repository for leaked credentials. If a secret ever gets into an image, I rotate the secret first. Deleting the line and rebuilding is not enough.

## Health checks in AKS

For an AKS deployment, I normally define startup, readiness, and liveness probes in the Kubernetes manifest rather than depending only on Docker `HEALTHCHECK`.

```yaml
readinessProbe:
  httpGet:
    path: /health/ready
    port: 8080
```

This prevents traffic from reaching a Pod before the application is ready.

## Image verification

```bash
docker image inspect orders-service:1.0.0
docker history orders-service:1.0.0
```

In CI/CD, I also scan the image and push it with a unique version or commit ID. I do not deploy the changing `latest` tag.

## How do you reduce Docker build time?

**Interviewer:** Your Docker build is slow. How do you make it faster?

**Candidate:** I make sure unchanged layers are reused instead of rebuilt on every commit.

- **Order layers by change frequency.** Copy `package*.json` or `pom.xml`, install dependencies, then copy the source code.
- **Use `.dockerignore`** so `.git`, `node_modules`, and `target` are not sent as build context.
- **Use BuildKit cache mounts** so the package cache survives between builds:

```dockerfile
RUN --mount=type=cache,target=/root/.m2 mvn -B clean verify
RUN --mount=type=cache,target=/root/.npm npm ci
```

The cache mount is not part of the image, so every `RUN` that needs the cache must mount it.

- **Use registry cache in CI.** Hosted pipeline agents start empty, so I keep the cache in ACR:

```bash
docker buildx build \
  --cache-from type=registry,ref=myacr.azurecr.io/orders-service:buildcache \
  --cache-to type=registry,ref=myacr.azurecr.io/orders-service:buildcache,mode=max \
  -t myacr.azurecr.io/orders-service:$(Build.BuildId) --push .
```

- **Use a slim base image** and combine `apt-get update && apt-get install ... && rm -rf /var/lib/apt/lists/*` in one `RUN`.
- **Run independent pipeline jobs in parallel**, for example unit tests, SonarQube, and dependency scans.

## Deployment to ACI takes 10 minutes. How do you make it 5?

**Interviewer:** An image deployment to Azure Container Instances takes 10 minutes. How do you bring it down to 5?

**Candidate:** First I measure where the time goes: build, push, pull, or application startup. ACI does not cache images between new container groups, so a large image is pulled in full every time.

```bash
az container show -g rg-app -n orders-api \
  --query "containers[0].instanceView.events" -o table   # Pulling -> Pulled -> Started
docker history myacr.azurecr.io/orders-api:1.4.2         # biggest layers
```

Then I fix the slow part:

- **Slow pull:** a multi-stage build, a slim base image, and `.dockerignore` make the image smaller. Use Linux containers instead of Windows if possible, because Windows images are several GB. Keep ACR in the same region as ACI, or use ACR geo-replication.
- **Slow build:** layer ordering and registry cache, as above.
- **Slow startup:** check the app for slow initialization, database migrations at startup, or waiting on a dependency.
- If start time still matters, ACI **standby pools** keep pre-created container groups ready to use.

ACI itself does not make anything faster. The time is saved by a smaller image, a closer registry, and a faster startup.

## Common mistakes I avoid

- Running the application as root.
- Copying the entire repository into the image.
- Storing passwords in `ENV` or `ARG`.
- Using a large build image as the runtime image.
- Using an unversioned base image.
- Ignoring image vulnerabilities.
- Starting a background process that immediately exits.

## Example interview explanation

For a Spring Boot service, I use a multi-stage Dockerfile. Maven builds and tests the JAR in the first stage.

The second stage contains only the Java runtime and JAR. I create a non-root user, expose port 8080, and start the application with `ENTRYPOINT`.

This produces a smaller and safer runtime image.

## In short

I select the Dockerfile from the application type, use versioned base images and multi-stage builds, copy only required files, run as non-root, and keep configuration and secrets outside the image. I build, run, inspect, and scan the image before deploying it.
