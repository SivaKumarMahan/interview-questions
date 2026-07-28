# Docker Summary

## Core Model

Docker packages an application and its runtime dependencies into an image and starts isolated container processes from that image. The CLI talks to the Docker daemon/API; the daemon builds images, manages containers, volumes, and networks, and pulls/pushes through registries.

Images are immutable (not changed after creation) layered blueprints; containers add an ephemeral writable layer. Persistent application state belongs in volumes or external services.

## Dockerfile Instructions

- `FROM`: selects the base and starts a build stage.
- `LABEL`: adds metadata.
- `ARG`: build-time value; never a safe secret store.
- `ENV`: image/runtime default environment value.
- `WORKDIR`: sets and creates the working directory.
- `COPY`: copies local build-context files and is preferred for normal copying.
- `ADD`: additionally supports local archive extraction and limited remote sources; use only when that behavior is intended.
- `RUN`: executes a build step and creates a layer.
- `EXPOSE`: documents a container port; it does not publish it.
- `VOLUME`: declares a mount point but operational volume ownership should be explicit.
- `USER`: changes the user for later steps/runtime; production should normally be non-root.
- `HEALTHCHECK`: reports container health but must be lightweight and meaningful.
- `ENTRYPOINT`: main executable; `CMD`: its default command/arguments or standalone default.
- `ONBUILD`: defers an instruction until the image is used as a base; use cautiously because behavior is hidden from the child Dockerfile.

Use a trusted pinned small base, `.dockerignore`, dependency-first cache ordering, multi-stage builds, one clear process, exec-form command, non-root user, read-only filesystem where possible, limited capabilities/resources, runtime secret injection, scanning, SBOM, signing, and regular rebuilds.

## Compose and Multi-Stage Builds

Compose describes local or controlled multi-container services, networks, ports, volumes, dependencies, and environment in YAML. It is convenient for development/test; production orchestration needs clear HA, scheduling, secret, and upgrade behavior.

Multi-stage Dockerfiles compile/test in a tool-heavy stage and copy only runtime output into a small final image. This reduces size and attack surface and keeps compilers/source/dependency caches out of production.

## Scenario Reminders

- **Works locally but not in Docker:** compare configuration, files, architecture, dependencies, port/listener, filesystem permissions, DNS/network, and logs.
- **Large image:** inspect layers, build context, cache order, base, package cleanup, and multi-stage design.
- **Frequent restarts:** inspect exit/OOM/health status, logs, configuration, dependencies, and resource limits.
- **Persistent data:** use a named volume or external datastore with backup; never rely on the writable layer.
- **Multi-container communication:** use a user-defined network and service/container DNS names rather than fixed IPs.

## docker init

`docker init` is a command-line utility that helps initialize Docker resources within a project. It creates a Dockerfile, a Compose file, and a `.dockerignore` based on the project's requirements, simplifying Docker configuration and reducing complexity.

It supports Go, Python, Node.js, Rust, ASP.NET, PHP, and Java, and is available with Docker Desktop.

### How to use it

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

### Generated Dockerfile

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

### Why use it

`docker init` makes dockerization easy, especially for newcomers. It eliminates the manual task of writing Dockerfiles and other configuration files, saving time and minimizing errors, and uses templates that follow industry best practices to tailor the setup to your application type.
**Note:** At the time of writing, `docker init` is available with Docker Desktop.

## Docker Compose

Docker Compose is a tool for defining and running multi-container applications. You describe all the services in a single file (`docker-compose.yml`) and run the whole application with one command, `docker-compose up`.

### Why Docker Compose

- You define application services and their build options — networks, volumes, environment variables — in one `docker-compose.yml`.
- All services share the same network and can talk to each other internally (front-end, API, DB services, etc.).
- You build and run every service with a single command: `docker-compose up`.
- Because the whole application is one config file, it is easy to share, store in version control (GitHub), and wire into a CI/CD pipeline.

### Example: multi-container Flask + Postgres app

This example runs two containers — a Postgres database and a Flask web app that talks to it.

Create the folder structure:

```bash
mkdir docker-compose
cd docker-compose
# create files/directory to store the code
touch docker-compose.yml requirements.txt app.py Dockerfile
mkdir -p static/css
touch static/css/style.css
mkdir templates
touch templates/index.html
```

What each file is for:

- **Dockerfile** — builds the web application image (a Flask/gunicorn image; see the `docker init` section above for a representative Python Dockerfile).
- **app.py** — the Flask code. It initializes SQLAlchemy, sets the PostgreSQL connection URI, defines a data model with `id` and `name` columns, and defines routes on `/` handling both GET and POST to store and render data.
- **requirements.txt** — the application dependencies (Flask, Flask-SQLAlchemy, the Postgres driver, gunicorn, etc.).
- **docker-compose.yml** — the Compose config file.
- **templates/index.html** — the HTML for the Flask app.
- **static/css/style.css** — the CSS.

The `docker-compose.yml` defines two services, `app` and `db`, on the same network, with these characteristics: `app` port 5000 is exposed to host port 5000 and `db` port 5432 to host port 5432; `app` depends on `db`; a health check on `db` ensures Postgres is ready before `app` connects; a named volume persists the database; and environment variables hold the Postgres credentials and database name.

A configuration matching that description:
```yaml
services:
  app:
    build: .
    ports:
      - "5000:5000"
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    depends_on:
      db:
        condition: service_healthy

  db:
    image: postgres:latest
    ports:
      - "5432:5432"
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 5s
      timeout: 5s
      retries: 5

volumes:
  pgdata:
```

Normally you should **not** hardcode credentials in the config file — see "Using environment variables" below.

If you would rather not write Compose files by hand, use `docker init` to generate them (see the `docker init` section above).

### Running the application

```bash
git clone https://github.com/akhileshmishrabiz/Devops-zero-to-hero
cd Devops-zero-to-hero/AWS-Projects/multi-container-app-docker-compose

docker-compose up --build
```

Check the running containers:

```text
$ docker ps
CONTAINER ID  IMAGE                              COMMAND                  STATUS                 PORTS                    NAMES
7c99c9539298  flask-app-docker-compose-app       "python app.py"          Up About a minute      0.0.0.0:5000->5000/tcp   flask-app-docker-compose-app-1
78f6a230ca24  postgres:latest                    "docker-entrypoint.s…"   Up About a minute (healthy)  0.0.0.0:5432->5432/tcp   flask-app-docker-compose-db-1
```

On a local machine, access the app at `http://localhost:5000` (`127.0.0.1`). On an EC2 instance with a public IP, use that IP on port 5000. You can connect to the Postgres DB from pgAdmin or a DB viewer.

Because the database uses a named volume, data persists across restarts:

```bash
docker-compose down
docker-compose up
```

### Installing Docker and Docker Compose (Amazon Linux 2)

Docker Desktop is the easiest option locally (it installs both Docker and Compose). On a cloud Linux VM such as an Amazon Linux 2 EC2 instance:

```bash
# Install Docker
sudo yum update -y
sudo yum install docker -y
sudo systemctl enable docker
sudo systemctl start docker
sudo usermod -a -G docker ec2-user
# Log out and back in to run docker without sudo
```

```bash
# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
# Check the installation
docker-compose version
```

### Using environment variables for credentials

Instead of hardcoding credentials in `docker-compose.yml`, use a `.env` file. Create a `.env` in the same location as `docker-compose.yml`, remove the environment values from the Compose file, and put them in `.env`.

Compose loads it automatically on `docker-compose up`.

One problem: if you commit your code to GitHub, a `.env` in the repo exposes the credentials. Keep the secrets file out of the repo (e.g. `.gitignore` it) and pass a dedicated env file explicitly:

```bash
docker-compose --env-file db-variables.env up
```

## Docker Bake

Docker Bake is a build orchestration tool (GA with Docker Desktop 4.38) that lets you define build stages and configuration in a declarative file instead of memorizing long `docker build` commands and flags.

It leverages BuildKit's parallelization and optimization to speed up builds — think of it as "docker build as code," versioned like Terraform templates.

### The problem it solves

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

### Bake it instead

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

### Targets

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

### Groups

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

### Inheritance

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

### Variables (like Terraform)

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

### Arithmetic and ternary expressions

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

### Built-in and user-defined functions

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

### Remote and alternate Bake files

- You can build Bake files directly from a remote Git repository or HTTPS URL.
- Bake files can be written in **HCL**, **YAML** (Docker Compose files), or **JSON**.
- The filename is not fixed — pass any file with `--file`:

```bash
docker buildx bake --file ../docker/bake.hcl
```

By default Bake looks up its configuration file in a defined lookup order (e.g. `docker-bake.hcl`, `docker-bake.json`, `docker-compose.yml`, etc.).

## Docker Fundamentals

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

### Docker networking

Docker provides multiple network types.

**1. Default bridge.** When you run, say, an nginx container, the web server listens on port 80 *inside* the container.

From inside the container `curl 127.0.0.1:80` returns the page (`127.0.0.1` is the loopback address for localhost), but you cannot reach it from the host by default. Inspect the container and networks:

```bash
docker inspect nginx-container
docker network ls
docker network inspect bridge
```

The default bridge network does not expose container services automatically — you must forward ports — and it does **not** provide internal DNS name resolution, so containers can reach each other by IP but not by name.

**Port forwarding** publishes a container port to a host port:

```bash
# docker run -d -p <host port>:<container port> --name <container name> <image>
docker run -t -d -p 5000:80 --name nginx-container nginx:latest
```

**2. User-defined bridge network.** Docker recommends creating your own network rather than using the default bridge.

It provides isolation from the host network *and* name resolution between containers (they still need port forwarding to be reached from the host).

```bash
docker network create blog-network
docker run -itd --network blog-network --name nginx-con nginx
docker network inspect blog-network
docker inspect nginx-con
```

Containers on `blog-network` can now ping each other by name (e.g. `ping nginx-con`).

**3. Host network.** The container shares the host's network stack directly:

```bash
docker run -td --network host --name nginx-server nginx:latest
docker inspect nginx-server | grep IPAddress
```

The container has no IP of its own — it uses the host machine's IP.

### Docker volumes

Docker isolates a container's content from your local filesystem, so deleting a container deletes everything inside it. To persist data a container generates, use volumes.

- **Bind mount** — a file or directory on the host machine is mounted into a container.
- **Docker volume** — a location on your filesystem managed by Docker. It does not increase the size of the containers using it, and its contents live outside any single container's lifecycle.

There are two syntaxes:

- **`-v` / `--volume`** — three colon-separated fields: (1) host path (bind mount) or volume name, (2) mount path in the container, (3) optional comma-separated options such as `ro`, `z`, `Z`.
- **`--mount`** — comma-separated key-value pairs: `type` (`bind`, `volume`, or `tmpfs`), `source`, and `target` (the mount path in the container).

**Example — shared named volume across containers.** Note: `-v <name>:/path` (no leading `/`) creates a **named volume**, not a true bind mount (a bind mount requires an absolute host path like `-v /host/dir:/app/log`).

That is why the shared data below is *not* visible on the host filesystem — it lives in Docker-managed storage.
```bash
mkdir docker-bind-mount
docker run -t -d -v docker-bind-mount:/app/log --name captain-america busybox
docker run -t -d -v docker-bind-mount:/app/log --name thor busybox
docker run -t -d -v docker-bind-mount:/app/log --name hulk busybox
docker run -t -d -v docker-bind-mount:/app/log --name iron-man alpine

# equivalent with --mount
docker run -t -d --mount type=bind,source=docker-bind-mount,target=/app/log \
  --name captain-america busybox
```

Logs written under `/app/log` in any of these containers are visible to all of them. Inspect a container's `Mounts` section for details:

```bash
docker inspect hulk
```

**Example — Docker volumes.**

```bash
docker volume create thor-vol
docker volume create hulk-vol
docker volume ls
docker volume inspect thor-vol
```

Mount a volume when creating containers (with `--mount`, `type` defaults to `volume` when the source is a volume name):

```bash
docker run -d \
  --name thor-container \
  --mount type=volume,source=thor-vol,target=/app \
  nginx:latest

docker run -d \
  --name hulk-container \
  --mount source=thor-vol,target=/app \
  nginx:latest
```

Both containers share the data written under `/app`. Remove volumes with:

```bash
docker volume rm <volume-name> [<volume-name>...]
```

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
