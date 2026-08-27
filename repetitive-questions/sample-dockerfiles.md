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
- `COPY` adds the Maven file and source code.
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

Both should normally use JSON form:

```dockerfile
ENTRYPOINT ["java", "-jar", "/app/app.jar"]
```

This helps the process receive stop signals correctly.

## Configuration and secrets

I do not copy Production configuration or secrets into the image.

At runtime:

- Normal configuration comes from environment variables or ConfigMaps.
- Secrets come from Azure Key Vault through workload identity or the CSI driver.

The same image can then run in Development, Testing, and Production.

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