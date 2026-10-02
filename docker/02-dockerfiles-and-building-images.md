# Docker: Dockerfiles and Building Images

> Dockerfile instructions, base images, build-time variables, docker init, and building and pushing images.

## Key Concepts

### Dockerfile Instructions

- `FROM`: picks the base image and starts a build stage.
- `LABEL`: adds metadata.
- `ARG`: a build-time value — never use it to hold a secret.
- `ENV`: sets a default environment variable, baked into the image and at runtime.
- `WORKDIR`: sets (and creates) the working directory.
- `COPY`: copies files from the build context; the default choice for copying.
- `ADD`: does what `COPY` does, plus it can extract local archives and fetch some remote sources — use it only when you actually need that behavior.
- `RUN`: runs a command during the build and creates a layer.
- `EXPOSE`: documents which port the container listens on; it doesn't publish that port to the host.
- `VOLUME`: declares a mount point, but who owns and manages that volume should still be explicit.
- `USER`: sets which user later steps and the running container use; production should normally run as non-root.
- `HEALTHCHECK`: reports container health, but keep the check itself lightweight and meaningful.
- `ENTRYPOINT`: the main program the container runs; `CMD`: its default arguments, or a default command on its own.
- `ONBUILD`: queues up an instruction to run later, when this image is used as someone else's base. Use it carefully — that behavior is invisible in the child Dockerfile.

Good defaults: a small, trusted, pinned base image; a `.dockerignore` file; copying dependency files before source code so the cache works well; multi-stage builds; one clear main process; the exec form of commands; a non-root user; a read-only filesystem where possible; limited capabilities and resources; secrets injected at runtime, not baked in; scanning; an SBOM; signing; and rebuilding regularly.

### docker init

`docker init` is a command-line utility that helps initialize Docker resources within a project. It creates a Dockerfile, a Compose file, and a `.dockerignore` based on the project's requirements, simplifying Docker configuration and reducing complexity.

It supports Go, Python, Node.js, Rust, ASP.NET, PHP, and Java, and is available with Docker Desktop.

#### How to use it

Go to your project directory, then run `docker init`. It scans the project, asks you to confirm the best-matching template, and prompts for project-specific information (language/platform, version, port, entrypoint) before generating the Docker assets.

You can accept the recommended defaults or provide your own values.

Example — a basic Flask app:

```bash
touch app.py requirements.txt
```

```python
# app.py
from flask import Flask

app = Flask(__name__)

@app.route('/')
def hello_docker():
    return '<h1> hello world </h1>'

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
```

```text
# requirements.txt
Flask
```

Then run `docker init` and choose Python as the application platform. It suggests recommended values (Python version, port, entrypoint) and generates the config files along with instructions for running the application.

#### Generated Dockerfile

The auto-generated Dockerfile follows performance and security best practices — pinned slim base, non-root user, cache/bind mounts for dependency install, and an explicit exposed port:

```dockerfile
# syntax=docker/dockerfile:1

ARG PYTHON_VERSION=3.11.7
FROM python:${PYTHON_VERSION}-slim as base

# Prevents Python from writing pyc files.
ENV PYTHONDONTWRITEBYTECODE=1

# Keeps Python from buffering stdout and stderr to avoid situations where
# the application crashes without emitting any logs due to buffering.
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Create a non-privileged user that the app will run under.
ARG UID=10001
RUN adduser \
    --disabled-password \
    --gecos "" \
    --home "/nonexistent" \
    --shell "/sbin/nologin" \
    --no-create-home \
    --uid "${UID}" \
    appuser

# Download dependencies as a separate step to take advantage of Docker's caching.
# Leverage a cache mount to /root/.cache/pip to speed up subsequent builds.
# Leverage a bind mount to requirements.txt to avoid having to copy it into this layer.
RUN --mount=type=cache,target=/root/.cache/pip \
    --mount=type=bind,source=requirements.txt,target=requirements.txt \
    python -m pip install -r requirements.txt

# Switch to the non-privileged user to run the application.
USER appuser

# Copy the source code into the container.
COPY . .

# Expose the port that the application listens on.
EXPOSE 5000

# Run the application.
CMD gunicorn 'app:app' --bind=0.0.0.0:5000
```

It also generates a `compose.yaml` to run the app (with database service config commented out — uncomment it, add a local secrets file, and run if you need a database) and a `.dockerignore` file.

#### Why use it

`docker init` makes dockerization easy, especially for newcomers. It eliminates the manual task of writing Dockerfiles and other configuration files, saving time and minimizing errors, and uses templates that follow industry best practices to tailor the setup to your application type.
**Note:** At the time of writing, `docker init` is available with Docker Desktop.

### Building and pushing an image

Build a Docker image containing a basic Flask app and push it to Docker Hub. Create three files:

```bash
touch Dockerfile app.py requirements.txt
```

```python
# app.py
from flask import Flask

app = Flask(__name__)

@app.route('/')
def hello_docker():
    return 'Hello, Docker!'

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
```

```text
# requirements.txt
Flask
```

```dockerfile
# Dockerfile
# Use an official Python runtime as a parent image
FROM python:3.11

# Copy the Python dependency file into the container at /app
COPY requirements.txt /app

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the Flask app file into the container at /app
COPY app.py /app

# Make port 5000 available outside this container
EXPOSE 5000

# Run app.py when the container launches
CMD ["python", "app.py"]
```

Build, tag, and push:

```bash
# docker build -t <image-name> <path to Dockerfile>
docker build -t flask-image .

# docker tag <local image> <docker hub username>/<repository name>:<tag>
docker tag flask-image livingdevopswithakhilesh/docker-demo-docker:1.0

docker login
docker push livingdevopswithakhilesh/docker-demo-docker:1.0
```

Delete the local image, pull it back from Docker Hub, and run a container from it:

```bash
docker pull livingdevopswithakhilesh/docker-demo-docker:1.0
docker run -td -p 8080:5000 --name flask livingdevopswithakhilesh/docker-demo-docker:1.0
```

## Interview Questions

<details><summary>Q1. [Basic] How do you create a custom Docker image?</summary>

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

</details>

<details><summary>Q2. [Intermediate] How do you write a production-ready Dockerfile?</summary>

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

</details>

<details><summary>Q3. [Intermediate] Dockerfile Security, Reliability, and Optimization</summary>

#### The Dockerfile

```dockerfile
FROM ubuntu:latest

RUN apt-get update
RUN apt-get install -y openjdk-17-jdk

COPY . /app

ENV DB_PASSWORD=Production123

WORKDIR /app

CMD ["java", "-jar", "app.jar"]
```

#### Problems

**Security:**
- `ENV DB_PASSWORD=Production123` bakes a real secret into the image layers — anyone who can pull or inspect the image (`docker history`) can see it.
- `ubuntu:latest` is an unpinned, mutable tag — the image can silently change over time, breaking reproducibility and potentially introducing vulnerabilities.
- No non-root user — the container runs as `root` by default, which is a bigger blast radius if the app is compromised.
- Installs the full JDK (includes compilers/dev tools) instead of just a JRE, growing the attack surface unnecessarily.

**Reliability:**
- `RUN apt-get update` on its own line, separate from `apt-get install`, can use a stale cached layer for `update` while installing a newer package list — a classic Docker caching pitfall. They should be combined in one `RUN`.
- No version pinning for `openjdk-17-jdk` — install could silently pull a different patch version between builds.
- `COPY . /app` copies everything, including potentially unnecessary files (`.git`, local configs, secrets) — no `.dockerignore` mentioned.

**Image size / optimization:**
- `ubuntu:latest` + full JDK is a large base; no multi-stage build to strip build-time dependencies from the final image.

#### Corrected Dockerfile

```dockerfile
FROM eclipse-temurin:17-jre-jammy

RUN groupadd -r appgroup && useradd -r -g appgroup appuser

WORKDIR /app

COPY --chown=appuser:appgroup target/app.jar /app/app.jar

USER appuser

CMD ["java", "-jar", "app.jar"]
```

The `DB_PASSWORD` should never be baked into the image — it should be injected at runtime via `docker run -e DB_PASSWORD=...` (sourced from a secrets manager), or via Kubernetes Secrets if deployed there.

#### Short interview answer

"There are three categories of problems here: security — a real secret baked into the image via `ENV`, and the container running as root; reliability — `apt-get update` and `install` split into separate `RUN` layers, which can install against a stale package index, plus an unpinned `ubuntu:latest` base; and size — using a full JDK and Ubuntu base instead of a slim JRE image. I'd switch to a pinned, JRE-only base image, add a non-root user, remove the hardcoded secret and inject it at runtime instead, and combine related `RUN` steps."

</details>

<details><summary>Q4. [Basic] What is the base image in Docker and which base image would you use for Python or Node.js?</summary>

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

</details>

<details><summary>Q5. [Basic] What is the difference between <code>ADD</code> and <code>COPY</code> in a Dockerfile?</summary>

**Answer:**

`COPY` copies local files or directories from the build context into the image. `ADD` does that too, but also has extra behavior — it can automatically extract local tar archives and fetch some remote URLs. I prefer `COPY` because its behavior is obvious just by reading it, which makes the Dockerfile easier to audit.

```dockerfile
COPY package.json package-lock.json ./
```

For remote files, I'd rather download them in a controlled `RUN` step with TLS and a checksum check, or fetch them before the build starts. A strict `.dockerignore` file keeps large or sensitive files out of the build context in the first place.

Neither `COPY` nor `ADD` should ever pull in `.git`, local credentials, or build output you don't need.

</details>

<details><summary>Q6. [Basic] What happens when you write <code>COPY .</code> in a Dockerfile?</summary>

**Answer:**

It copies the entire build context — everything in that directory except what `.dockerignore` excludes — into the image. That can pull in source code, Git history, credentials, test data, and large files you didn't mean to include. It also means any small change anywhere in that directory invalidates the build cache for that layer.

A strict `.dockerignore` file plus copying only what you need, in the right order, avoids this:

```dockerfile
COPY package.json package-lock.json ./
RUN npm ci
COPY src ./src
```

I check the build context size, build logs, and image layers (using `docker history` or a tool like Dive) to catch anything that shouldn't be there. If a secret ever ends up in a layer, deleting it in a later layer isn't enough — the old layer still has it in the image's history. The fix is to rotate the secret and rebuild from a clean history.

</details>

<details><summary>Q7. [Basic] What is the difference between <code>RUN</code>, <code>CMD</code>, and <code>ENTRYPOINT</code>?</summary>

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

</details>

<details><summary>Q8. [Basic] What is the difference between <code>CMD</code> and <code>ENTRYPOINT</code>?</summary>

**Answer:**

`ENTRYPOINT` makes the container behave like a specific program. `CMD` supplies the default arguments (or command) for it. Arguments you pass on `docker run` replace `CMD`, but replacing `ENTRYPOINT` requires the `--entrypoint` flag.

For an application image, I'd write:

```dockerfile
ENTRYPOINT ["/app/server"]
CMD ["--config", "/etc/server/config.yaml"]
```

For a general-purpose tool image, `CMD` alone is often more flexible. I avoid wrapper shell scripts unless they end with `exec "$@"`, so signals still reach the actual application instead of being swallowed by the wrapper. I also test `docker stop` directly to confirm the container shuts down cleanly.

</details>

<details><summary>Q9. [Basic] Dockerfile: what is the difference between COPY vs ADD and CMD vs ENTRYPOINT?</summary>

These are two of the most frequently asked Docker interview questions.

#### 19.1 COPY vs ADD

Both `COPY` and `ADD` copy files from the host machine into the Docker image. The difference is that `ADD` has extra features, while `COPY` simply copies files.

| Feature | COPY | ADD |
|---|---|---|
| Copy local files | Yes | Yes |
| Copy directories | Yes | Yes |
| Extract local tar files automatically | No | Yes |
| Download files from URL | No | Yes |
| Recommended for most cases | Yes | No |

**COPY**

Simply copies files or folders.

```dockerfile
COPY app.py /app/
```

Copies:

```
Host
 └── app.py

   |
   v

Container
 └── /app/app.py
```

Nothing else happens.

**ADD**

`ADD` can do everything `COPY` does, plus:

*1. Automatically extract tar files*

```dockerfile
ADD project.tar.gz /app/
```

Instead of copying the archive `project.tar.gz`, Docker extracts it automatically.

Result:

```
/app/
    src/
    config/
    images/
```

*2. Download from URL*

```dockerfile
ADD https://example.com/file.txt /tmp/
```

Docker downloads the file into the image. This is rarely recommended because it makes builds less predictable.

**Which one should you use?**

Use `COPY` by default.

Use `ADD` only when you specifically need:

- Automatic extraction of local tar archives.
- Its extra functionality (though downloading via `RUN curl` or `wget` is usually preferred for better control).

**Interview answer**

> "COPY simply copies files and directories into the image. ADD has additional features like automatically extracting local tar archives and supporting URL sources. In production, I prefer COPY because it is simpler, more predictable, and follows Docker best practices."

#### 19.2 CMD vs ENTRYPOINT

This is about how a container starts.

**CMD**

CMD provides the default command.

```dockerfile
FROM ubuntu

CMD ["echo", "Hello World"]
```

Running:

```bash
docker run myimage
```

Output:

```
Hello World
```

You can override CMD:

```bash
docker run myimage ls
```

Output:

```
bin
etc
home
tmp
```

The `echo` command is replaced by `ls`.

**ENTRYPOINT**

ENTRYPOINT defines the main executable of the container.

```dockerfile
FROM ubuntu

ENTRYPOINT ["echo"]
```

Run:

```bash
docker run myimage Hello
```

Output:

```
Hello
```

Docker appends the supplied arguments to the ENTRYPOINT command.

Trying:

```bash
docker run myimage ls
```

produces:

```
ls
```

because Docker runs `echo ls`.

**CMD + ENTRYPOINT together**

This is the most common pattern.

```dockerfile
FROM ubuntu

ENTRYPOINT ["echo"]

CMD ["Hello"]
```

Run:

```bash
docker run myimage
```

Output:

```
Hello
```

Run:

```bash
docker run myimage Docker
```

Output:

```
Docker
```

Docker executes `ENTRYPOINT + CMD`, or, if arguments are provided, `ENTRYPOINT + user arguments`.

**Real production example**

```dockerfile
FROM eclipse-temurin:21

COPY app.jar app.jar

ENTRYPOINT ["java", "-jar", "app.jar"]
```

Run:

```bash
docker run myapp
```

Docker executes:

```
java -jar app.jar
```

If you need to pass JVM arguments:

```bash
docker run myapp --spring.profiles.active=prod
```

Docker executes:

```
java -jar app.jar --spring.profiles.active=prod
```

**When to use which?**

Use CMD when:

- You want to provide a default command.
- Users should be able to replace it easily.

```dockerfile
CMD ["python", "app.py"]
```

Use ENTRYPOINT when:

- The container should always run a specific application.
- Users may pass additional arguments to that application.

```dockerfile
ENTRYPOINT ["nginx", "-g", "daemon off;"]
```

**Quick comparison**

| Feature | CMD | ENTRYPOINT |
|---|---|---|
| Purpose | Default command | Main executable |
| Can be overridden by `docker run` arguments? | Yes | No (unless `--entrypoint` is used) |
| Receives runtime arguments | No - replaced by them | Yes - appends them |
| Typical use | Default behaviour | Fixed application startup |

#### 19.3 Interview answer

> "**COPY vs ADD:** COPY only copies files and directories and is the preferred choice for most Dockerfiles because it's simple and predictable. ADD provides extra features like extracting local tar archives automatically and supporting URL sources, so I use it only when those features are required.
>
> **CMD vs ENTRYPOINT:** CMD defines the default command that can be overridden when starting the container. ENTRYPOINT defines the container's main executable and is intended to always run. A common production pattern is to use ENTRYPOINT for the application (for example, `java -jar app.jar`) and CMD to provide default arguments that users can override."

</details>

<details><summary>Q10. [Basic] How many <code>CMD</code> instructions can a Dockerfile contain, and what happens when there are multiple?</summary>

**Answer:**

A Dockerfile can technically contain multiple `CMD` instructions, but only the last one in the final build stage actually takes effect — the earlier ones are silently overwritten, and having more than one usually just makes the Dockerfile confusing to read.

Each stage of a multi-stage build can define its own `CMD`, but only the final stage's configuration matters at runtime.

I normally use one exec-form `ENTRYPOINT` for the actual program and one exec-form `CMD` for its default arguments:

```dockerfile
ENTRYPOINT ["java", "-jar", "/app/app.jar"]
CMD ["--spring.profiles.active=prod"]
```

Arguments passed to `docker run image ...` replace `CMD`; the `--entrypoint` flag is needed to replace `ENTRYPOINT` itself. The exec form keeps signal handling working correctly, which matters for a clean shutdown. I confirm the final result with `docker image inspect` and by actually testing `docker stop`.

</details>

<details><summary>Q11. [Basic] How do you pass environment variables during docker build commands? What services do you use for storing Docker images?</summary>

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

</details>

<details><summary>Q12. [Intermediate] How do you inject environment values during Docker builds, and where should runtime configuration be stored?</summary>

**Answer:**

Build arguments (`ARG`) should only ever be used for non-secret build choices, because their values can end up in the image's history, build cache metadata, or provenance record. Runtime `ENV` sets defaults baked into the image, and those can still be overridden by environment variables or mounted config at deploy time.

If a build genuinely needs a secret — say, to pull a private dependency — use a BuildKit secret mount, not `ARG`. Better still, fetch secrets at runtime through workload identity and a secret manager.

I never bake separate Dev, UAT, and Prod credentials into separate images. I build one image, publish it under a fixed digest to the approved registry, and supply environment-specific but non-secret configuration through Kubernetes ConfigMaps, platform settings, or orchestrator variables. Actual secret values come from Vault, Key Vault, Secrets Manager, or an external-secret integration, scoped to only the access they need and rotated regularly.

I check `docker history`, the image's configuration, CI logs, the SBOM and provenance record, and registry access to make sure nothing sensitive leaked out. If a credential ever does end up in a layer, deleting the file later isn't enough — I rotate it immediately and rebuild without it.

</details>
