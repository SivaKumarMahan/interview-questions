# Docker: Image Optimization, Multi-Stage Builds, and Bake

> Layer caching, image size reduction, multi-stage builds, and declarative builds with Docker Bake.

## Key Concepts

### Docker Bake

Docker Bake is a build orchestration tool (GA with Docker Desktop 4.38) that lets you define build stages and configuration in a declarative file instead of memorizing long `docker build` commands and flags.

It leverages BuildKit's parallelization and optimization to speed up builds — think of it as "docker build as code," versioned like Terraform templates.

#### The problem it solves

Building and pushing images for a monorepo means repeating long commands with many flags:

```bash
# Frontend build
docker build --build-arg NODE_VERSION=20 -t \
  366140438193.dkr.ecr.ap-south-1.amazonaws.com/frontend:latest \
  -f frontend/frontend.Dockerfile frontend

# Backend build
docker build --build-arg GO_VERSION=1.21 -t \
  366140438193.dkr.ecr.ap-south-1.amazonaws.com/backend:latest \
  -f backend/backend.Dockerfile backend

# Push both
docker push 366140438193.dkr.ecr.ap-south-1.amazonaws.com/frontend:latest
docker push 366140438193.dkr.ecr.ap-south-1.amazonaws.com/backend:latest
```

Those are just commands — not version-controlled, and easy to get wrong.

#### Bake it instead

Create a `docker-bake.hcl` at the repo root:

```hcl
# docker-bake.hcl
group "default" {
  targets = ["frontend", "backend"]
}

target "frontend" {
  context    = "./frontend"
  dockerfile = "frontend.Dockerfile"
  args = {
    NODE_VERSION = "20"
  }
  tags = ["366140438193.dkr.ecr.ap-south-1.amazonaws.com/frontend:latest"]
}

target "backend" {
  context    = "./backend"
  dockerfile = "backend.Dockerfile"
  args = {
    GO_VERSION = "1.21"
  }
  tags = ["366140438193.dkr.ecr.ap-south-1.amazonaws.com/backend:latest"]
}
```

Then build both images with one command, and push with `--push`:

```bash
docker buildx bake          # build all targets in the default group
docker buildx bake --push   # build and push to the remote (e.g. ECR) repositories
```

Commit `docker-bake.hcl` to Git and nobody needs to remember `docker build` flags again.

#### Targets

A **target** represents a single build invocation — it holds everything you would normally pass to `docker build` via flags. This command:

```bash
docker build \
  -f Dockerfile \
  -t myapp:latest \
  --build-arg foo=bar \
  --no-cache \
  --platform linux/amd64,linux/arm64 \
  .
```

is equivalent to this Bake target:

```hcl
# docker-bake.hcl
target "myapp" {
  context    = "."
  dockerfile = "Dockerfile"
  tags       = ["myapp:latest"]
  args = {
    foo = "bar"
  }
  no-cache  = true
  platforms = ["linux/amd64", "linux/arm64"]
}
```

- Build a specific target by name: `docker buildx bake myapp`.
- With no target argument, Bake builds the `default` target:

```hcl
target "default" {
  dockerfile = "webapp.Dockerfile"
  tags       = ["docker.io/username/webapp:latest"]
  context    = "https://github.com/username/webapp"
}
```

#### Groups

Group targets with the `group` block to build several at once:

```hcl
group "all" {
  targets = ["webapp", "api", "tests"]
}

target "webapp" {
  dockerfile = "webapp.Dockerfile"
  tags       = ["docker.io/username/webapp:latest"]
  context    = "https://github.com/username/webapp"
}

target "api" {
  dockerfile = "api.Dockerfile"
  tags       = ["docker.io/username/api:latest"]
  context    = "https://github.com/username/api"
}

target "tests" {
  dockerfile = "tests.Dockerfile"
  contexts = {
    webapp = "target:webapp",
    api    = "target:api",
  }
  output  = ["type=local,dest=build/tests"]
  context = "."
}
```

- Build multiple named targets: `docker buildx bake webapp api tests`.
- Build a whole group: `docker buildx bake all`.

#### Inheritance

Define common configuration once and reuse it across targets with `inherits`:

```hcl
target "common" {
  context   = "."
  platforms = ["linux/amd64", "linux/arm64"]
}

target "backend" {
  inherits   = ["common"]
  dockerfile = "backend.Dockerfile"
  args = {
    GO_VERSION = "1.21"
  }
}

target "frontend" {
  inherits   = ["common"]
  dockerfile = "frontend.Dockerfile"
  args = {
    NODE_VERSION = "20"
  }
}
```

An inheriting target can override any inherited attribute:

```hcl
target "base" {
  context    = "."
  dockerfile = "Dockerfile"
  args = {
    APP_ENV = "development"
  }
}

target "production" {
  inherits = ["base"]
  args = {
    APP_ENV = "production"  # overrides the inherited value
  }
}
```

#### Variables (like Terraform)

Define variables to set values, interpolate them, and do arithmetic:

```hcl
group "default" {
  targets = ["frontend"]
}

variable "NODE_VERSION" {
  default = "20"
}

variable "tag" {
  default = "latest"
}

target "frontend" {
  context    = "."
  dockerfile = "frontend.Dockerfile"
  args = {
    NODE_VERSION = NODE_VERSION
  }
  tags = ["myapp-frontend:${tag}"]
}
```

Print the resolved configuration (with interpolated values) using `--print`:

```bash
docker buildx bake --print
```

#### Arithmetic and ternary expressions

```hcl
variable "FOO" {
  default = 3
}

variable "IS_FOO" {
  default = true
}

target "app" {
  args = {
    v1 = FOO > 5 ? "higher" : "lower"
    v2 = IS_FOO ? "yes" : "no"
  }
}
```

#### Built-in and user-defined functions

Use functions (e.g. a user-defined `generate_tag` plus the built-in `timestamp()`) to build values dynamically:

```hcl
# Define a variable for version
variable "APP_VERSION" {
  default = "1.0.0"
}

# Define a target using a custom function and a built-in function
target "myapp" {
  context    = "."
  dockerfile = "Dockerfile"
  tags       = ["myapp:${generate_tag(APP_VERSION)}"]
  args = {
    BUILD_DATE = timestamp()
  }
}
```

#### Remote and alternate Bake files

- You can build Bake files directly from a remote Git repository or HTTPS URL.
- Bake files can be written in **HCL**, **YAML** (Docker Compose files), or **JSON**.
- The filename is not fixed — pass any file with `--file`:

```bash
docker buildx bake --file ../docker/bake.hcl
```

By default Bake looks up its configuration file in a defined lookup order (e.g. `docker-bake.hcl`, `docker-bake.json`, `docker-compose.yml`, etc.).

## Interview Questions

### 1. How do you optimize a Dockerfile for performance and security?

**Answer:**

I start from a small, trusted, pinned base image, use multi-stage builds, lock dependency versions, order instructions so the cache works well, use BuildKit cache mounts, add a `.dockerignore` file, run as non-root, install only what's needed, use exec-form commands, and never bake in secrets. Package caches are cleaned up in the same layer they were created in, and I avoid leaving unnecessary shells or tools in the runtime image.

CI builds the image reproducibly, tests it, generates an SBOM, scans it, signs it, and publishes a fixed, versioned build. At runtime I add a read-only root filesystem, drop capabilities, apply seccomp, set resource limits, and restrict network access where the app allows it.

I measure build time, cache hit rate, image size, startup time, vulnerability count, and actual application performance. Alpine isn't automatically the best choice — its different C library (musl) can cause subtle compatibility issues, so a "slim" or distroless image is sometimes the safer bet.

### 2. Explain Docker image layering and how it can cause cache busting.

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

### 3. How do you reduce Docker image size for faster deployments? *(asked in interview round)*

**Answer:**
- Use a smaller base image, like Alpine.
- Use multi-stage builds.
- Remove unused packages and cache in the same layer you added them.
- Push to a private registry so pulls are fast and cached.

**Detailed interview approach:**
I start from a small, trusted base image and use multi-stage builds so build tools and source code never end up in the final image — only the compiled output does.

I keep the number of packages installed to a minimum, and I clean up package caches in the same `RUN` step that installs them, since a later `RUN rm` doesn't shrink earlier layers. I also order instructions so that things which change often (like application source) come after things that rarely change (like dependency installs), so builds stay fast.

Alpine isn't always the right choice — sometimes its different C library (musl) causes compatibility issues, so a "slim" or distroless image can be a safer trade-off.

### 4. What are Docker multi-stage builds, and how do they help optimize Docker images?

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

### 5. Docker Image Optimization for a React App

#### The Dockerfile

```dockerfile
FROM node:18

WORKDIR /app

COPY . .

RUN npm install
RUN npm run build

CMD ["npm", "start"]
```

#### Problems

1. **Ships the entire Node toolchain** (`node:18` full image, ~1GB+) into production, even though a built React app is just static HTML/CSS/JS files that don't need Node at runtime at all.
2. **No multi-stage build** — build-time dependencies (devDependencies, build tools, source files) all end up in the final image.
3. **`COPY . .` before `npm install`** breaks Docker layer caching — any source code change invalidates the cache for `npm install`, forcing a full reinstall on every build even when `package.json` didn't change.
4. **`npm start`** typically runs a dev server (e.g., `react-scripts start`), which is not meant for production — it's slower and not optimized for serving static files at scale.

#### Optimized multi-stage Dockerfile

```dockerfile
# --- Build stage ---
FROM node:18 AS build

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

# --- Production stage ---
FROM nginx:alpine

COPY --from=build /app/build /usr/share/nginx/html

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

Improvements:
- **Multi-stage build**: Node is only used to build the static files; the final image is just `nginx:alpine` (a few MB) serving static content — no Node, no source code, no `node_modules` in production.
- **Better layer caching**: copying `package*.json` first means `npm ci` only re-runs when dependencies actually change, not on every source edit.
- **`npm ci` instead of `npm install`**: faster, reproducible installs based on `package-lock.json`.
- **Nginx serves static files properly** with production-grade performance instead of a Node dev server.

#### Short interview answer

"A built React app is just static files, so shipping the full Node image to run `npm start` is unnecessarily large and uses a dev server not meant for production. I'd use a multi-stage build — build the app in a `node` stage with `npm ci`, then copy only the compiled `build` output into a lightweight `nginx:alpine` stage to actually serve it. I'd also copy `package.json` before the rest of the source so Docker can cache the dependency install layer properly."

### 6. Write and explain a multi-stage Dockerfile for a Maven application.

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
