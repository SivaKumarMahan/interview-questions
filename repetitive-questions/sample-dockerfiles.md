# Repetitive Interview Questions

## Write a sample Dockerfile and explain what you have written

### Detailed answer

A Dockerfile is a text file containing ordered instructions that Docker uses to build an immutable container image. I first ask what application I am containerizing because the correct Dockerfile depends on the language, build tool, runtime, ports, filesystem requirements and deployment platform.

For my primary project answer, I use a **Java Spring Boot application built with Maven and deployed to AKS**. I can also explain variations for a pre-built JAR, a legacy WAR application, a React frontend and a small Python API.

The five examples below are:

1. Java Spring Boot with Maven using a multi-stage build.
2. Java Spring Boot when CI has already built the JAR.
3. Java WAR deployed on Tomcat.
4. React frontend built with Node.js and served by NGINX.
5. Python FastAPI service.

The image versions below are representative examples. In a real project, I select an approved and supported version, pin it deliberately, scan it and regularly rebuild it for security fixes. For the strongest reproducibility, the CI/CD system can pin the base image by digest as well as recording the readable version tag.

---

## Answer 1: Spring Boot and Maven multi-stage Dockerfile

This is my preferred answer for a modern Java microservice because it demonstrates both the build stage and the smaller runtime stage.

Assume the Maven project is configured to produce:

```text
target/orders-service.jar
```

### Dockerfile

```dockerfile
# syntax=docker/dockerfile:1

FROM maven:3.9.9-eclipse-temurin-21 AS build

WORKDIR /workspace

COPY pom.xml ./
RUN --mount=type=cache,target=/root/.m2 \
    mvn -B -DskipTests dependency:go-offline

COPY src ./src
RUN --mount=type=cache,target=/root/.m2 \
    mvn -B clean verify

FROM eclipse-temurin:21-jre-jammy AS runtime

LABEL org.opencontainers.image.title="orders-service" \
      org.opencontainers.image.description="Orders Spring Boot API"

RUN groupadd --system --gid 10001 appgroup \
    && useradd --system --uid 10001 --gid appgroup \
       --home-dir /app --shell /usr/sbin/nologin appuser

WORKDIR /app

COPY --from=build --chown=appuser:appgroup \
     /workspace/target/orders-service.jar /app/app.jar

USER 10001:10001

EXPOSE 8080

ENTRYPOINT ["java", "-jar", "/app/app.jar"]
```

### Line-by-line explanation

#### `# syntax=docker/dockerfile:1`

This syntax directive asks BuildKit to use the current stable Dockerfile frontend features. In this example it enables the cache-mount syntax used by the Maven steps. It is a parser directive, not a normal image layer.

#### `FROM maven:... AS build`

`FROM` selects the base image and starts a build stage. This first stage contains Maven and the JDK because source code must be compiled.

I name the stage `build` so the final stage can copy from it using `COPY --from=build`. The exact base tag or digest is pinned and maintained by the project; I do not use a floating `latest` tag in Production.

#### `WORKDIR /workspace`

`WORKDIR` creates or selects the working directory for later `RUN`, `COPY` and related instructions. It is better than repeatedly writing `cd /workspace` because the setting is explicit and persists for the remaining instructions in that stage.

#### `COPY pom.xml ./`

This copies only the Maven project descriptor first. Dependencies normally change less frequently than source code, so Docker can reuse the dependency layer when only Java source files change.

I use `COPY` rather than `ADD` because I only need a predictable local-file copy. `ADD` has additional behavior, such as handling local archives and remote sources, which is unnecessary here.

#### `RUN --mount=type=cache,target=/root/.m2 ...`

`RUN` executes during the image build. Maven resolves the project dependencies, and the BuildKit cache mount preserves the local Maven repository between builds without copying that cache into the final runtime image.

`-B` enables Maven batch mode for CI. `dependency:go-offline` prepares dependencies early. Whether every plugin can be fully resolved offline depends on the project, so the actual build still remains the final verification.

#### `COPY src ./src`

This copies application source only after dependencies have been prepared. A normal source edit therefore invalidates the source and compilation layers but does not automatically invalidate the earlier dependency layer.

#### `RUN ... mvn -B clean verify`

This compiles, tests and packages the application. `verify` also runs the Maven lifecycle checks configured by the project. In CI I publish the test and quality reports rather than relying only on the Docker build output.

The Maven `pom.xml` in this example sets the final artifact name to `orders-service.jar`. Using an explicit artifact name avoids an ambiguous wildcard that could accidentally match multiple JAR files.

#### `FROM eclipse-temurin:21-jre-jammy AS runtime`

This starts a new stage containing only the Java runtime environment. Maven, the compiler, source code and build cache remain in the earlier stage and do not enter the final image.

That is the purpose of a multi-stage build: use a larger toolchain to build, but ship only what is required to run. It reduces image size and attack surface.

#### `LABEL ...`

`LABEL` adds metadata to the image. In CI I normally include standard OCI labels such as source repository, commit revision and image version so that an image can be traced back to its code and pipeline run.

#### `RUN groupadd ... && useradd ...`

This creates a dedicated, unprivileged runtime user and group with fixed numeric IDs. Fixed IDs make Kubernetes security settings and mounted-volume permissions more predictable.

The shell is set to `nologin` because this is a service identity, not an interactive user. I combine these related commands into one `RUN` instruction.

#### `WORKDIR /app`

This makes `/app` the runtime working directory. The application artifact and any relative application paths are now based there.

#### `COPY --from=build --chown=...`

This copies only the packaged JAR from the named build stage into the runtime stage. `--chown` gives the non-root application user ownership at copy time.

No source code, Maven executable or Maven dependency cache is copied into the runtime image.

#### `USER 10001:10001`

This makes the remaining instructions and the running container use the unprivileged identity. I use the numeric UID/GID because Kubernetes policies can validate them consistently.

Running as non-root reduces the impact of an application vulnerability, although it is only one security layer.

#### `EXPOSE 8080`

`EXPOSE` documents that the application listens on container port 8080. It does not publish the port to a Docker host and does not create an AKS Service.

For a local run, `-p 8080:8080` publishes host port 8080 to container port 8080. In AKS, the Deployment container port and Kubernetes Service provide the relevant mapping.

#### `ENTRYPOINT ["java", "-jar", "/app/app.jar"]`

`ENTRYPOINT` defines the main executable. I use JSON/exec form so Java runs directly as PID 1 and receives termination signals correctly.

This matters during an AKS rolling deployment: Kubernetes sends `SIGTERM`, waits for the configured termination grace period and then stops the Pod. The Java application must also implement graceful shutdown and readiness behavior.

### Build, inspect and run

```bash
docker build -t orders-service:1.0.0 .

docker image inspect orders-service:1.0.0

docker run --rm \
  --name orders-service \
  -p 8080:8080 \
  -e SPRING_PROFILES_ACTIVE=local \
  orders-service:1.0.0

docker logs -f orders-service
```

The profile is runtime configuration. I do not bake a Production password or environment-specific secret into the image. In AKS, normal configuration comes from approved ConfigMaps/environment settings and sensitive values come from Azure Key Vault through Workload ID.

### Why I did not add a Dockerfile `HEALTHCHECK`

For this AKS application, readiness, liveness and startup probes are defined in the Kubernetes Deployment and call approved Spring Boot Actuator endpoints. This lets Kubernetes distinguish:

- **Startup:** Has the slow-starting application initialized yet?
- **Readiness:** Is the Pod ready to receive traffic?
- **Liveness:** Is the application stuck and safe to restart?

A Docker `HEALTHCHECK` is valuable for standalone Docker, but Kubernetes does not automatically convert it into Kubernetes probes. I also avoid installing `curl` only to perform a health check because that adds packages to the runtime image. If standalone Docker is a requirement, I add an appropriate check using a tool already available or a small application-specific health-check binary.

### What enters the final image?

```text
JRE runtime
dedicated non-root user
orders-service.jar
image metadata
```

The following remain outside the final image:

```text
Maven
JDK compiler
source code
unit-test files
Maven cache
Git metadata
```

---

## Answer 2: Dockerfile for a JAR already built by CI

Sometimes the pipeline runs `mvn clean verify` first, publishes the JAR as a pipeline artifact and then builds the container from that verified artifact. In that architecture the Dockerfile does not need a Maven build stage.

### Dockerfile

```dockerfile
FROM eclipse-temurin:21-jre-jammy

ARG JAR_FILE=target/orders-service.jar

RUN groupadd --system --gid 10001 appgroup \
    && useradd --system --uid 10001 --gid appgroup \
       --home-dir /app --shell /usr/sbin/nologin appuser

WORKDIR /app

COPY --chown=appuser:appgroup ${JAR_FILE} /app/app.jar

USER 10001:10001

EXPOSE 8080

ENTRYPOINT ["java", "-jar", "/app/app.jar"]
```

### Explanation

- `FROM` uses a runtime-only Java image because compilation has already happened.
- `ARG JAR_FILE` provides a build-time argument with a default artifact path.
- `ARG` is not appropriate for secrets. Build arguments can be exposed through image metadata, cache or build logs.
- `RUN` creates the non-root identity.
- `COPY` adds the already verified JAR and assigns ownership.
- `USER` ensures the application does not run as root.
- `EXPOSE` documents the listening port.
- `ENTRYPOINT` starts the application directly.

Build with the default path:

```bash
mvn -B clean verify
docker build -t orders-service:1.0.0 .
```

Build with another artifact path:

```bash
docker build \
  --build-arg JAR_FILE=artifacts/orders-service.jar \
  -t orders-service:1.0.0 .
```

### When do I choose this approach?

I use it when the organization's pipeline requires the binary to be built, tested, signed or approved as a separate artifact before container packaging. It also avoids downloading Maven dependencies inside the container build.

The tradeoff is that the Docker build depends on the cleanliness and correctness of the external build workspace. The pipeline must prove which commit produced the JAR and must not allow a developer's unverified local JAR to become the Production artifact.

---

## Answer 3: Java WAR application on Tomcat

For a legacy Java web application that produces a WAR rather than an executable Spring Boot JAR, I can use a Tomcat runtime.

Assume Maven produces:

```text
target/customer-portal.war
```

### Dockerfile

```dockerfile
# syntax=docker/dockerfile:1

FROM maven:3.9.9-eclipse-temurin-21 AS build

WORKDIR /workspace
COPY pom.xml ./
RUN --mount=type=cache,target=/root/.m2 \
    mvn -B -DskipTests dependency:go-offline

COPY src ./src
RUN --mount=type=cache,target=/root/.m2 \
    mvn -B clean verify

FROM tomcat:10.1-jre21-temurin-jammy AS runtime

RUN rm -rf /usr/local/tomcat/webapps/* \
    && groupadd --system --gid 10001 appgroup \
    && useradd --system --uid 10001 --gid appgroup \
       --home-dir /usr/local/tomcat --shell /usr/sbin/nologin appuser \
    && chown -R appuser:appgroup \
       /usr/local/tomcat/logs \
       /usr/local/tomcat/temp \
       /usr/local/tomcat/webapps \
       /usr/local/tomcat/work

COPY --from=build --chown=appuser:appgroup \
     /workspace/target/customer-portal.war \
     /usr/local/tomcat/webapps/ROOT.war

USER 10001:10001

EXPOSE 8080

CMD ["catalina.sh", "run"]
```

### Explanation

The build stage is similar to the Spring Boot example: Maven downloads dependencies, tests the code and produces the WAR.

In the runtime stage:

- The Tomcat base contains the servlet container and Java runtime.
- Default web applications are removed to avoid exposing unnecessary sample/administrative content.
- A non-root user is created.
- Only Tomcat's required writable directories are assigned to that user.
- The WAR is copied to `webapps/ROOT.war`, so it is served at `/` rather than `/customer-portal`.
- `catalina.sh run` keeps Tomcat in the foreground. A container must keep its main process in the foreground; a background daemon would make the container exit.

I verify that the application and selected Tomcat major version use compatible Jakarta/Java APIs. I also externalize Tomcat/application configuration, send logs to standard output/error where possible, and define AKS probes and resource limits.

### Build and run

```bash
docker build -t customer-portal:1.0.0 .

docker run --rm \
  --name customer-portal \
  -p 8080:8080 \
  customer-portal:1.0.0
```

### Why `CMD` here and `ENTRYPOINT` in the Spring Boot example?

Both can start a container. Here `CMD` supplies the default Tomcat command and makes it easy to replace the whole command during debugging. In the Spring Boot image, `ENTRYPOINT` expresses that the image acts specifically as the Java application executable.

The choice must be deliberate. There can be only one effective `CMD`; if multiple `CMD` instructions exist, only the final one is used.

---

## Answer 4: React frontend with Node.js builder and NGINX runtime

A React application needs Node.js to install packages and generate static files, but Node.js is not required to serve those files in Production. I therefore use Node.js only in the build stage and NGINX in the runtime stage.

### Dockerfile

```dockerfile
# syntax=docker/dockerfile:1

FROM node:22-alpine AS build

WORKDIR /workspace

COPY package.json package-lock.json ./
RUN --mount=type=cache,target=/root/.npm \
    npm ci

COPY . .

ARG VITE_API_BASE_URL=/api
RUN VITE_API_BASE_URL="${VITE_API_BASE_URL}" npm run build

FROM nginx:1.27-alpine AS runtime

COPY nginx.conf /etc/nginx/nginx.conf
COPY --from=build --chown=nginx:nginx \
     /workspace/dist /usr/share/nginx/html

USER nginx

EXPOSE 8080

CMD ["nginx", "-g", "daemon off;"]
```

If the project uses Create React App, the generated directory is commonly `build` rather than `dist`; I change the `COPY` path to match the actual framework.

### `nginx.conf`

```nginx
pid /tmp/nginx.pid;

events {
    worker_connections 1024;
}

http {
    access_log /dev/stdout;
    error_log  /dev/stderr warn;

    client_body_temp_path /tmp/client_temp;
    proxy_temp_path       /tmp/proxy_temp;
    fastcgi_temp_path     /tmp/fastcgi_temp;
    uwsgi_temp_path       /tmp/uwsgi_temp;
    scgi_temp_path        /tmp/scgi_temp;

    include      /etc/nginx/mime.types;
    default_type application/octet-stream;

    server {
        listen 8080;
        server_name _;

        root /usr/share/nginx/html;
        index index.html;

        location / {
            try_files $uri $uri/ /index.html;
        }
    }
}
```

### Explanation

- `node:22-alpine` provides Node.js and npm for the build.
- The lock file is copied before source code so `npm ci` can use a cached layer.
- `npm ci` installs exactly from `package-lock.json` and is preferable to an unpinned install in CI.
- `ARG VITE_API_BASE_URL` is a non-secret build setting. Frontend JavaScript is downloaded to the browser, so anything embedded in it must be considered public.
- `npm run build` generates optimized static assets.
- The final stage uses NGINX and receives only those assets, not `node_modules` or source.
- A custom NGINX configuration listens on unprivileged port 8080 and writes its PID/temp data under `/tmp`, allowing it to run as the `nginx` user.
- `try_files ... /index.html` supports client-side routes in a single-page application.
- `daemon off;` keeps NGINX in the foreground as the container's primary process.

### Build and run

```bash
docker build \
  --build-arg VITE_API_BASE_URL=/api \
  -t customer-ui:1.0.0 .

docker run --rm \
  --name customer-ui \
  -p 8080:8080 \
  customer-ui:1.0.0
```

For environment-independent promotion, I prefer runtime configuration where the frontend design supports it. Otherwise a build-time API URL creates a different image per environment, which conflicts with the build-once/promote-the-same-image principle.

---

## Answer 5: Python FastAPI service

This example is suitable for a small internal API or DevOps automation service.

### Dockerfile

```dockerfile
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN groupadd --system --gid 10001 appgroup \
    && useradd --system --uid 10001 --gid appgroup \
       --home-dir /app --shell /usr/sbin/nologin appuser

WORKDIR /app

COPY requirements.txt ./
RUN python -m pip install \
    --no-cache-dir \
    --requirement requirements.txt

COPY --chown=appuser:appgroup app ./app

USER 10001:10001

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Explanation

- `python:3.12-slim` is a smaller runtime base than a full operating-system image.
- `PYTHONDONTWRITEBYTECODE=1` avoids writing `.pyc` files inside the container.
- `PYTHONUNBUFFERED=1` sends logs immediately to standard output/error for container log collection.
- The dedicated user prevents the API from running as root.
- `requirements.txt` is copied first so dependency installation can be cached when only application code changes.
- `--no-cache-dir` prevents pip's download cache from remaining in the image layer.
- Requirements should be pinned and vulnerability-scanned; `--no-cache-dir` does not provide dependency reproducibility.
- Only the application package is copied, with the correct owner.
- Uvicorn binds to `0.0.0.0` so it is reachable through the container network. Binding only to `127.0.0.1` would normally make it inaccessible from outside the container.
- Exec-form `CMD` makes the Python process receive signals directly.

### Build and run

```bash
docker build -t automation-api:1.0.0 .

docker run --rm \
  --name automation-api \
  -p 8000:8000 \
  automation-api:1.0.0
```

The number of workers depends on CPU limits, workload behavior and whether scaling is performed through multiple AKS replicas. I do not blindly place many workers in every Pod.

---

## Recommended `.dockerignore`

The build context is sent to the builder. A `.dockerignore` prevents unnecessary or sensitive files from entering that context and reduces cache invalidation.

```dockerignore
.git
.gitignore
.idea
.vscode

.env
.env.*
*.pem
*.key
*.pfx

target
build
dist
node_modules
.venv
__pycache__
*.pyc

*.log
coverage
.terraform
```

This example must be adjusted for the selected workflow. For example, Answer 2 expects a pre-built JAR under `target`, so `target` must not be ignored for that Dockerfile, or the JAR must be copied into a dedicated allowed build-context directory.

`.dockerignore` is a preventive convenience, not permission to keep real secrets in the repository. Secrets belong in Azure Key Vault or the approved secret-management system.

---

## Important Dockerfile instructions interviewers ask me to explain

| Instruction | Purpose | Important interview point |
| --- | --- | --- |
| `FROM` | Selects a base and begins a stage | Every `FROM` begins a new stage; pin and scan the base |
| `WORKDIR` | Sets the working directory | Safer and clearer than repeated `RUN cd ...` |
| `COPY` | Copies local files or files from another stage | Preferred for ordinary predictable copies |
| `ADD` | Adds local/remote content and can unpack local archives | Use only when its extra behavior is intentionally needed |
| `RUN` | Executes a command while building | Produces image filesystem changes/layers |
| `ARG` | Defines a build-time variable | Not for secrets; generally unavailable at runtime unless persisted |
| `ENV` | Sets an image/runtime environment variable | Can be overridden at runtime; also not for secrets |
| `USER` | Selects the build/runtime user | Use a non-root user in the final stage |
| `EXPOSE` | Documents a listening container port | Does not publish it |
| `ENTRYPOINT` | Defines the image's main executable | Runtime arguments are normally appended |
| `CMD` | Defines a default command or default arguments | `docker run` arguments replace it |
| `HEALTHCHECK` | Defines a Docker container health command | Separate from AKS readiness/liveness/startup probes |
| `LABEL` | Adds image metadata | Useful for source, revision, owner and version traceability |

### `RUN` versus `CMD` versus `ENTRYPOINT`

`RUN` happens while building the image:

```dockerfile
RUN mvn -B clean verify
```

`CMD` and `ENTRYPOINT` take effect when a container starts:

```dockerfile
ENTRYPOINT ["java", "-jar", "/app/app.jar"]
CMD ["--server.port=8080"]
```

Together, the default command is:

```text
java -jar /app/app.jar --server.port=8080
```

Running:

```bash
docker run orders-service:1.0.0 --server.port=9090
```

keeps the `ENTRYPOINT` but replaces `CMD`, resulting in:

```text
java -jar /app/app.jar --server.port=9090
```

The complete entrypoint can be replaced explicitly with `docker run --entrypoint ...`, mainly for controlled troubleshooting.

### Exec form versus shell form

Exec form:

```dockerfile
ENTRYPOINT ["java", "-jar", "/app/app.jar"]
```

Shell form:

```dockerfile
ENTRYPOINT java -jar /app/app.jar
```

I normally prefer exec form for the main process. It avoids an unnecessary `/bin/sh -c` wrapper and provides clearer argument and signal handling. Shell expansion is not automatically performed in exec form, so I do not expect `${VARIABLE}` inside its JSON elements to be expanded by a shell.

### `COPY` versus `ADD`

I use:

```dockerfile
COPY app.jar /app/app.jar
```

for ordinary files. `ADD` has extra behavior, including automatic extraction of a local tar archive and support for certain remote/Git sources. Those implicit behaviors can surprise readers, so I use `ADD` only when the requirement specifically needs and documents them. For remote downloads, a controlled `RUN` step can verify the checksum before installation.

### `ARG` versus `ENV`

```dockerfile
ARG BUILD_VERSION
ENV APP_MODE=production
```

- `ARG` exists for the image build and can affect build steps.
- `ENV` becomes part of the image configuration and is available to the running container unless overridden.
- Neither should hold a password, token or private key.
- BuildKit secret mounts or the CI platform's secure mechanism should be used when an authorized build genuinely needs a secret.
- Runtime secrets for my AKS workloads are obtained from Azure Key Vault through Workload ID.

### Does `EXPOSE` publish the port?

No. This:

```dockerfile
EXPOSE 8080
```

documents the container port.

This publishes a local host port:

```bash
docker run -p 9090:8080 orders-service:1.0.0
```

The application is reached at host port `9090`, which Docker forwards to port `8080` inside the container.

---

## How I take the image from source code to AKS

The Dockerfile is only one part of the delivery process:

```text
source and Dockerfile
-> pull-request review
-> unit/SAST/dependency/secret checks
-> Docker BuildKit build
-> image vulnerability scan
-> image tag with Git commit/version
-> push to Azure Container Registry
-> record immutable image digest
-> deploy that digest through Helm to AKS
-> startup/readiness/liveness verification
-> Azure Monitor and application monitoring
```

A simplified local ACR flow is:

```bash
az acr login --name <acr-name>

docker build \
  -t <acr-name>.azurecr.io/orders-service:<git-commit> .

docker push \
  <acr-name>.azurecr.io/orders-service:<git-commit>
```

In the real pipeline I prefer a federated service connection, workload identity or another approved short-lived authentication method rather than storing a registry password. AKS pulls from ACR through the configured managed identity/RBAC integration.

Production manifests reference an immutable digest:

```yaml
image: <acr-name>.azurecr.io/orders-service@sha256:<approved-digest>
```

Tags are convenient names, but a tag can point to different content. A digest identifies the exact image content that was scanned and approved.

---

## Security and production best practices

When I review a Dockerfile, I check that it:

- Uses an approved, trusted and supported base image.
- Pins the base deliberately and rebuilds when patches are available.
- Uses multi-stage builds when build tools are not required at runtime.
- Contains only the runtime files required by the application.
- Runs the final process as a non-root user.
- Uses exec-form `ENTRYPOINT` or `CMD` for correct signal handling.
- Does not contain credentials in `ARG`, `ENV`, `COPY` or image layers.
- Uses `.dockerignore` to reduce and protect the build context.
- Installs pinned dependencies and scans them.
- Avoids unnecessary operating-system packages and removes temporary package data.
- Writes application logs to standard output/error.
- Does not store persistent business data in the writable container layer.
- Supports a read-only root filesystem, using approved writable volumes such as `/tmp` when needed.
- Documents the application port without confusing `EXPOSE` with publishing.
- Can shut down gracefully during an AKS rolling update.
- Produces an immutable, traceable artifact with source revision metadata.
- Is scanned in CI and periodically rescanned after it is stored/deployed.

Image hardening is complemented by the AKS Pod security context:

```yaml
securityContext:
  runAsNonRoot: true
  runAsUser: 10001
  runAsGroup: 10001
  allowPrivilegeEscalation: false
  readOnlyRootFilesystem: true
  capabilities:
    drop:
      - ALL
  seccompProfile:
    type: RuntimeDefault
```

The Dockerfile and Kubernetes manifest must agree. For example, a read-only root filesystem requires the application to write temporary data only to explicitly mounted writable paths.

---

## Common follow-up questions and answers

### Why do you use multi-stage builds?

The build stage requires Maven, the JDK and source code, but the running service requires only the JRE and JAR. Multi-stage builds keep build-only content out of the final image, reducing size and attack surface while preserving a repeatable build.

### Why copy the dependency file before source code?

Docker reuses unchanged layers. Dependency descriptors such as `pom.xml`, `package-lock.json` or `requirements.txt` usually change less often than source. Copying and resolving them first prevents every source edit from forcing all dependencies to be downloaded again.

### Why should a container run as non-root?

It limits what a compromised application process can do inside the container and helps satisfy restricted Kubernetes security policies. It does not make the application automatically secure, so I still use least privilege, network controls, read-only filesystems, dropped capabilities and runtime monitoring.

### Why not use `latest`?

`latest` is a mutable tag and does not prove which code is deployed. I tag an image with a release version or Git commit, then promote and deploy the approved digest. The readable tag helps people; the digest gives exact content identity.

### How do you reduce image size?

I use a suitable minimal runtime base, multi-stage builds, `.dockerignore`, only required artifacts, no package-manager cache, and no unnecessary diagnostic/build tools. I measure and inspect the image instead of assuming that Alpine is always the best choice; compatibility, security support and operational debugging also matter.

### Where do you keep configuration and secrets?

The same image is promoted across environments. Normal runtime configuration is supplied through Helm values, ConfigMaps or environment settings. Secrets are stored in Azure Key Vault and accessed using Workload ID. They are not baked into the image.

### What happens if the application runs in the background?

The container remains alive only while its main PID 1 process is running. Therefore, NGINX uses `daemon off`, Tomcat uses `catalina.sh run`, and Java runs directly in the foreground.

### What is the difference between an image and a container?

An image is the immutable packaged template containing filesystem layers and configuration. A container is a running instance of that image with a writable runtime layer, process, network and resource settings.

### What is a Docker layer?

Most filesystem-changing build instructions create immutable layers. Docker can share and cache them. Layer ordering affects cache efficiency, and deleting a secret in a later layer does not safely remove it from an earlier layer.

### Can I pass a password using `--build-arg`?

No. Build arguments are not a secret store and may appear in metadata, cache or logs. I use BuildKit secret mounts for an authorized build-time secret and Azure Key Vault/Workload ID for runtime secrets.

### How do you troubleshoot a container that exits immediately?

I check:

```bash
docker ps -a
docker logs <container-name>
docker inspect <container-name>
```

I verify the exit code, `ENTRYPOINT`/`CMD`, artifact path, file permission, non-root access, environment variables, listening address and required dependencies. I reproduce with the same immutable image and do not modify the Production container as the permanent fix.

### How do you verify the image user?

```bash
docker run --rm --entrypoint id orders-service:1.0.0
```

I expect the configured non-root UID/GID. In CI, policy checks also reject images or Kubernetes workloads that violate the approved security standard.

### How do you see image history and size?

```bash
docker image inspect orders-service:1.0.0
docker image history orders-service:1.0.0
docker image ls orders-service
```

These help inspect configuration, layers and size, but security scanning and SBOM/provenance controls provide additional evidence.

### Why not install debugging tools in the Production image?

Every unnecessary package increases size, patching work and possible attack surface. I use logs, metrics, traces, ephemeral debugging facilities or a separately controlled diagnostic image. If a tool is operationally required, I document and maintain it rather than adding it casually.

---

## Common mistakes I avoid

- Using a floating `latest` base or application image.
- Copying the entire repository before dependency restoration.
- Using `ADD` where simple `COPY` is sufficient.
- Baking passwords, certificates or tokens into image layers.
- Running the final process as root.
- Shipping Maven, compilers, source and test data in the runtime image.
- Starting the application as a background daemon.
- Using shell-form startup without understanding PID 1 and signal behavior.
- Assuming `EXPOSE` makes the application publicly reachable.
- Keeping application data only in the container writable layer.
- Installing many tools in the Production image for convenience.
- Ignoring `.dockerignore`.
- Building different untraceable images for every deployment stage.
- Scanning only once and never rebuilding when new vulnerabilities are found.
- Using an image tag in Production without recording the approved digest.

---

## Concise interview answer

For my Java Spring Boot application, I normally write a multi-stage Dockerfile. In the first stage I use a Maven image, set the working directory, copy `pom.xml` first for dependency-layer caching, then copy the source and run `mvn clean verify`. In the second stage I use only a Java runtime image and copy the built JAR from the first stage.

I create a fixed non-root user, set `/app` as the working directory, expose the application's documented port 8080 and use exec-form `ENTRYPOINT ["java", "-jar", "/app/app.jar"]`. This gives the Java process correct signal handling for graceful AKS termination. Maven, source code and build cache do not enter the final image, so the result is smaller and has less attack surface.

I also maintain a `.dockerignore`, never put secrets in `ARG`, `ENV` or image layers, scan the image, tag it using the release or Git commit, push it to Azure Container Registry and deploy the approved immutable digest to AKS. Configuration is supplied at runtime and sensitive values come from Azure Key Vault through Workload ID.
