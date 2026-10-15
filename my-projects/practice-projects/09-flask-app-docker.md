# Practice Project 9: Containerize a Flask REST API with Docker

> This guide shows how to package a small Python Flask API into a secure, small Docker image, run it locally, push it to Docker Hub, and extend it with Docker Compose and Redis.

## Key Concepts

### What you will build

You will build a Flask REST API with two endpoints:

- `GET /hello` returns a greeting in JSON.
- `GET /health` returns `{"status": "ok"}` for health checks.

You will run it with Gunicorn (a production web server) inside a Docker image based on `python:3.12-slim`, running as a non-root user. You will push the image to Docker Hub so any machine (or the next project, Azure Container Instances) can pull it.

In the bonus section you will add Redis with Docker Compose and a `GET /visits` endpoint that counts visits. The count survives container restarts because Redis stores data in a named volume.

Final result: `curl http://localhost:8000/hello` returns JSON from a container, and `docker compose up` starts the API and Redis together.

### Architecture

Base project:

```text
 Your laptop
 +-------------------------------------------------+
 |  docker run -p 8000:8000                         |
 |  +-------------------------------------------+   |
 |  | Container: flask-api                       |   |
 |  |  user: appuser (non-root)                  |   |
 |  |  gunicorn :8000 -> Flask app (app.py)      |   |
 |  +-------------------------------------------+   |
 +-------------------------------------------------+
          |
          | docker push <user>/flask-api:1.0.0
          v
   +--------------+
   |  Docker Hub  |
   +--------------+
```

Bonus with Docker Compose:

```text
 curl :8000
     |
     v
 +-----------------+   network: backend   +-----------------+
 |  web (Flask)    | -------------------> |  redis:7-alpine |
 |  port 8000      |   host "redis":6379  |  volume:        |
 +-----------------+                      |  redis-data     |
                                          +-----------------+
```

### Tools and why each one is used

| Tool | What it does here | Why this tool |
| --- | --- | --- |
| Python 3.12 + Flask | The REST API code | Small, simple, very common for APIs |
| Gunicorn | Serves the Flask app with multiple worker processes | Flask's built-in server is for development only |
| Docker | Builds and runs the image | Same environment everywhere |
| `python:3.12-slim` | Base image | Much smaller than the full Debian image, still glibc compatible |
| Docker Hub | Stores and shares the image | Free public repositories, easy login with a token |
| Docker Compose | Runs the API and Redis together | One YAML file defines multi-container apps |
| Redis | Stores the visit counter | Fast in-memory store, tiny official image |

### Prerequisites

- Docker Desktop (Windows/macOS) or Docker Engine with the Compose plugin (Linux).

```bash
docker --version          # Docker version 27.x or newer
docker compose version    # Docker Compose version v2.x
```

- Python 3.12 (only needed if you want to run the app without Docker):

```bash
python3 --version
```

- A Docker Hub account and an access token (Account settings, then Personal access tokens, Read and Write).
- Basic terminal skills.

Cost: everything runs locally. Docker Hub public repositories are free. There is no cloud cost in this project.

### Folder structure

```text
flask-api/
├── app.py                 # Flask application
├── requirements.txt       # Python dependencies
├── Dockerfile             # Image build instructions
├── .dockerignore          # Files to keep out of the image
└── docker-compose.yml     # Bonus: web + redis
```

### Step-by-step

#### Step 1: Write the Flask app

Start with a small API in one file. Gunicorn will import it as `app:app` (module `app.py`, variable `app`).

```bash
mkdir flask-api && cd flask-api
```

`app.py`:

```python
import os
import socket

from flask import Flask, jsonify

app = Flask(__name__)

APP_VERSION = os.getenv("APP_VERSION", "dev")


@app.get("/hello")
def hello():
    name = os.getenv("GREETING_NAME", "world")
    return jsonify(
        message=f"Hello, {name}!",
        version=APP_VERSION,
        hostname=socket.gethostname(),
    )


@app.get("/health")
def health():
    return jsonify(status="ok"), 200


if __name__ == "__main__":
    # Development server only. In the container we use Gunicorn.
    app.run(host="0.0.0.0", port=8000, debug=False)
```

What this does:

- `@app.get(...)` is the Flask 2+ shortcut for `@app.route(..., methods=["GET"])`.
- `jsonify` returns a proper `application/json` response.
- `hostname` shows the container ID, so you can see which container answered.
- Settings like `APP_VERSION` come from environment variables, so the same image works in every environment (12-factor style).

#### Step 2: Pin dependencies

`requirements.txt`:

```text
flask==3.1.2
gunicorn==23.0.0
```

What this does:

- Pinning exact versions makes builds reproducible. A rebuild next month installs the same versions.
- Check PyPI for the latest patch versions when you start. Tools like Dependabot or `pip-tools` can keep pins up to date.

Optional: run without Docker to make sure the code works.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
# in another terminal
curl http://localhost:8000/hello
deactivate
```

#### Step 3: Write the Dockerfile

This Dockerfile is small, cache-friendly, and runs as a non-root user.

`Dockerfile`:

```dockerfile
# syntax=docker/dockerfile:1
FROM python:3.12-slim

# Python settings for containers
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Create a non-root user and group
RUN groupadd --system appgroup && \
    useradd --system --gid appgroup --no-create-home --shell /usr/sbin/nologin appuser

# 1) Copy only requirements first, so this layer is cached
COPY requirements.txt .
RUN pip install -r requirements.txt

# 2) Copy the application code (changes often)
COPY --chown=appuser:appgroup app.py .

USER appuser

EXPOSE 8000

# slim has no curl, so use Python for the health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/health').status==200 else 1)"

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "2", "--access-logfile", "-", "app:app"]
```

What this does:

- `python:3.12-slim` is a small Debian-based image (around 120-150 MB) with Python preinstalled.
- `PYTHONDONTWRITEBYTECODE=1` stops Python from writing `.pyc` files. They are not useful in an image and add clutter.
- `PYTHONUNBUFFERED=1` sends `print` and log output straight to stdout. Without it, logs can be delayed in `docker logs`.
- `PIP_NO_CACHE_DIR=1` stops pip from keeping a download cache in the image, which saves space.
- `groupadd`/`useradd --system` create a user with no home and no login shell. `USER appuser` makes all later commands and the app run as that user.
- `COPY requirements.txt` then `pip install` before `COPY app.py` is the key caching trick (see Step 4).
- `--bind 0.0.0.0:8000` listens on all interfaces. If you bind to `127.0.0.1`, the app is unreachable from outside the container.
- `--workers 2` starts two worker processes. A common rule is `(2 x CPU cores) + 1`, but keep it small in a container with limited CPU.
- `--access-logfile -` writes access logs to stdout so `docker logs` shows them.
- `app:app` means "module `app.py`, variable `app`".
- Exec form (`["gunicorn", ...]`) makes Gunicorn PID 1 so it gets `SIGTERM` from `docker stop` and shuts down gracefully.

#### Step 4: Understand layers and layer caching

Each instruction in a Dockerfile (`FROM`, `RUN`, `COPY`, `ADD`) creates a layer. A layer is a read-only set of file changes. Docker stacks layers to build the final filesystem.

When you rebuild, Docker checks each step in order:

- If the instruction and its inputs (for `COPY`, the file contents) are the same as last time, Docker reuses the cached layer.
- As soon as one step changes, that step and every step after it are rebuilt.

```text
Layer                                   Changes when...           Cached on a code change?
FROM python:3.12-slim                   base image updated        yes
ENV ...                                 ENV edited                yes
RUN groupadd/useradd                    command edited            yes
COPY requirements.txt                   requirements change       yes
RUN pip install                         requirements change       yes   <- slow step stays cached
COPY app.py                             app.py changes            NO (rebuilt)
CMD ...                                 metadata only             rebuilt (instant)
```

Bad order (do not do this):

```dockerfile
COPY . .
RUN pip install -r requirements.txt
```

Here, any change to any file breaks the cache for `COPY . .`, so `pip install` runs again on every build.

See the layers of your image:

```bash
docker history flask-api:1.0.0
```

#### Step 5: Add a .dockerignore

The build context is everything Docker sends to the builder. A `.dockerignore` keeps it small and keeps secrets out.

`.dockerignore`:

```text
.venv
venv
__pycache__
*.pyc
.git
.gitignore
.env
*.md
.pytest_cache
.mypy_cache
Dockerfile
.dockerignore
docker-compose.yml
```

What this does:

- `.venv` can be hundreds of MB and is built for your laptop OS, not the container. Never copy it in.
- `.env` and `.git` often hold secrets or history you do not want in a layer.
- A smaller context also means faster builds.

#### Step 6: Build and run the image

```bash
docker build -t flask-api:1.0.0 .

docker images flask-api

docker run -d \
  --name flask-api \
  -p 8000:8000 \
  -e APP_VERSION=1.0.0 \
  -e GREETING_NAME=DevOps \
  --restart unless-stopped \
  flask-api:1.0.0
```

What this does:

- `-t flask-api:1.0.0` names and tags the image locally.
- `-d` runs the container in the background.
- `-p 8000:8000` maps host port 8000 to container port 8000.
- `-e` sets environment variables the app reads.
- `--restart unless-stopped` restarts it after a crash or Docker restart.

Test it:

```bash
curl http://localhost:8000/hello
curl http://localhost:8000/health
```

#### Step 7: Debug with logs, exec, and inspect

These three commands answer most "why is my container not working" questions.

```bash
# Follow logs (Gunicorn startup + access logs)
docker logs -f flask-api
docker logs --tail 50 --timestamps flask-api

# Open a shell inside the running container
docker exec -it flask-api bash
# inside the container:
whoami          # appuser
ls -l /app       # app.py owned by appuser
env | grep APP
exit

# Run a one-off command without a shell
docker exec flask-api python -c "import flask; print(flask.__version__)"

# Inspect config and state
docker inspect flask-api --format '{{.State.Status}} {{.State.Health.Status}}'
docker inspect flask-api --format '{{json .Config.Env}}'
docker inspect flask-api --format '{{json .NetworkSettings.Ports}}'

# Resource usage
docker stats --no-stream flask-api
```

What this does:

- `docker logs` shows stdout/stderr. Because of `PYTHONUNBUFFERED=1` and `--access-logfile -`, you see each request.
- `docker exec` runs a process inside the running container. Good for checking files, env vars, and network.
- `docker inspect` prints the full JSON config. `--format` with Go templates picks out fields.
- `.State.Health.Status` shows `starting`, `healthy`, or `unhealthy` from the `HEALTHCHECK`.

#### Step 8: Tag and push to Docker Hub

```bash
# Log in with your access token (paste the token when asked for the password)
docker login -u <your-dockerhub-username>

# Add Docker Hub tags to the local image
docker tag flask-api:1.0.0 <your-dockerhub-username>/flask-api:1.0.0
docker tag flask-api:1.0.0 <your-dockerhub-username>/flask-api:latest

# Push both tags
docker push <your-dockerhub-username>/flask-api:1.0.0
docker push <your-dockerhub-username>/flask-api:latest
```

What this does:

- An image name for Docker Hub is `<username>/<repo>:<tag>`. Without a username, Docker tries the `library/` namespace, which you cannot push to.
- `docker tag` does not copy the image. It adds another name to the same image ID.
- Push only uploads layers that the registry does not already have. A second push after a code change only uploads the small app layer.
- Use a fixed version tag (`1.0.0` or a Git SHA) for deployments. `latest` is just a convenience pointer.

Optional: build for both Intel and ARM (for example, Apple Silicon laptops and Azure Linux x86 servers):

```bash
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t <your-dockerhub-username>/flask-api:1.0.0 \
  --push .
```

Test the pushed image from a clean state:

```bash
docker rm -f flask-api
docker rmi <your-dockerhub-username>/flask-api:1.0.0 flask-api:1.0.0
docker run -d --name flask-api -p 8000:8000 <your-dockerhub-username>/flask-api:1.0.0
curl http://localhost:8000/hello
```

#### Step 9: Keep the image small

Check the size:

```bash
docker images <your-dockerhub-username>/flask-api
```

Tips:

- Use `-slim` images. `python:3.12` (full) is around 1 GB, `python:3.12-slim` is around 130 MB.
- Use `PIP_NO_CACHE_DIR=1` or `pip install --no-cache-dir`.
- Combine related `RUN` commands and clean apt lists in the same layer: `apt-get install -y ... && rm -rf /var/lib/apt/lists/*`. Files deleted in a later layer still take space in the earlier layer.
- Use `.dockerignore`.
- Alpine (`python:3.12-alpine`) is smaller but uses musl libc. Many Python wheels are built for glibc, so pip may need to compile from source, which makes builds slow and images bigger. `slim` is usually the better choice for Python.

Optional multi-stage build. This is useful when some packages need compilers (`gcc`, headers) to build. You build wheels in a "builder" stage and copy only the results into a clean final stage.

```dockerfile
# syntax=docker/dockerfile:1
FROM python:3.12-slim AS builder
ENV PIP_NO_CACHE_DIR=1
WORKDIR /build
RUN apt-get update && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip wheel --wheel-dir /wheels -r requirements.txt

FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
RUN groupadd --system appgroup && \
    useradd --system --gid appgroup --no-create-home appuser
COPY --from=builder /wheels /wheels
RUN pip install /wheels/* && rm -rf /wheels
COPY --chown=appuser:appgroup app.py .
USER appuser
EXPOSE 8000
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "2", "--access-logfile", "-", "app:app"]
```

What this does:

- The `builder` stage has compilers. The final stage does not, so the final image is smaller and has less attack surface.
- `COPY --from=builder` copies only the built wheels.
- For this tiny app (pure Python packages) the size gain is small, but the pattern matters for real apps with packages like `psycopg` or `numpy` built from source.

#### Step 10 (Bonus): Add Redis with Docker Compose

Now add a visit counter stored in Redis. Docker Compose starts both containers, puts them on a shared network, and gives Redis a named volume.

Add Redis to `requirements.txt`:

```text
flask==3.1.2
gunicorn==23.0.0
redis==6.4.0
```

Update `app.py` (full file):

```python
import os
import socket

import redis
from flask import Flask, jsonify

app = Flask(__name__)

APP_VERSION = os.getenv("APP_VERSION", "dev")
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

# Connection pool is created once and reused by requests
cache = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    decode_responses=True,
    socket_connect_timeout=2,
)


@app.get("/hello")
def hello():
    name = os.getenv("GREETING_NAME", "world")
    return jsonify(
        message=f"Hello, {name}!",
        version=APP_VERSION,
        hostname=socket.gethostname(),
    )


@app.get("/visits")
def visits():
    try:
        count = cache.incr("visits")
    except redis.exceptions.ConnectionError:
        return jsonify(error="Redis is not reachable"), 503
    return jsonify(visits=count, hostname=socket.gethostname())


@app.get("/health")
def health():
    return jsonify(status="ok"), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=False)
```

What this does:

- `REDIS_HOST` comes from an env var. In Compose it will be `redis`, the service name.
- `cache.incr("visits")` is atomic in Redis, so two workers cannot lose an update.
- If Redis is down, `/visits` returns `503` instead of crashing. `/health` still works, so the container is not killed just because Redis is down.

`docker-compose.yml`:

```yaml
services:
  web:
    build: .
    image: <your-dockerhub-username>/flask-api:1.1.0
    container_name: flask-web
    ports:
      - "8000:8000"
    environment:
      APP_VERSION: "1.1.0"
      GREETING_NAME: "Compose"
      REDIS_HOST: redis
      REDIS_PORT: "6379"
    depends_on:
      redis:
        condition: service_healthy
    networks:
      - backend
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    container_name: flask-redis
    command: ["redis-server", "--appendonly", "yes"]
    volumes:
      - redis-data:/data
    networks:
      - backend
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5
    restart: unless-stopped

volumes:
  redis-data:

networks:
  backend:
    driver: bridge
```

What this does:

- No top-level `version:` key. It is obsolete in Compose v2 and only prints a warning.
- `build: .` plus `image:` builds from the local Dockerfile and names the result, so you can push it later with `docker compose push`.
- `REDIS_HOST: redis` works because Compose provides DNS on the user-defined network. Each service name resolves to its container IP.
- `depends_on` with `condition: service_healthy` waits until the Redis health check passes before starting `web`. Plain `depends_on` only waits for the container to start, not to be ready.
- Redis has no `ports:` entry, so it is only reachable inside the `backend` network, not from your host. This is good security practice.
- `redis-data:/data` is a named volume. Docker manages it, and it survives `docker compose down` (but not `down -v`).
- `--appendonly yes` makes Redis write every change to disk, so the counter survives restarts.

Run it:

```bash
docker compose up -d --build
docker compose ps
curl http://localhost:8000/visits
curl http://localhost:8000/visits
docker compose logs -f web
```

Prove the volume keeps data:

```bash
docker compose down          # removes containers and network, keeps the volume
docker compose up -d
curl http://localhost:8000/visits   # count continues from before
docker volume ls | grep redis-data
```

Postgres alternative: if you need relational data, swap Redis for Postgres in the same pattern.

```yaml
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: appdb
      POSTGRES_USER: appuser
      POSTGRES_PASSWORD_FILE: /run/secrets/db_password
    secrets:
      - db_password
    volumes:
      - pg-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U appuser -d appdb"]
      interval: 5s
      timeout: 3s
      retries: 5
    networks:
      - backend
```

You would also add `pg-data:` under `volumes:`, a top-level `secrets:` block pointing to a local file (for example `db_password: { file: ./db_password.txt }`, kept out of Git), and use a driver like `psycopg` in the app. The `_FILE` variant keeps the password out of `docker inspect` output.

### Verify it works

```bash
curl -s http://localhost:8000/hello
```

Expected output:

```json
{"hostname":"3f9c1a2b4d5e","message":"Hello, DevOps!","version":"1.0.0"}
```

```bash
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/health
```

Expected output:

```text
200
```

```bash
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

Expected output:

```text
NAMES       STATUS                    PORTS
flask-api   Up 1 minute (healthy)     0.0.0.0:8000->8000/tcp
```

```bash
docker exec flask-api whoami
```

Expected output:

```text
appuser
```

Bonus (Compose):

```bash
curl -s http://localhost:8000/visits
curl -s http://localhost:8000/visits
```

Expected output:

```json
{"hostname":"flask-web","visits":1}
{"hostname":"flask-web","visits":2}
```

Note: the hostname may show the container ID instead of `flask-web`, depending on your Docker version.

### Common problems and fixes

| Problem | Likely cause | Fix |
| --- | --- | --- |
| `curl: (52) Empty reply` or connection refused | Gunicorn bound to `127.0.0.1`, or wrong port mapping | Use `--bind 0.0.0.0:8000` and `-p 8000:8000` |
| `ModuleNotFoundError: No module named 'app'` | Wrong `WORKDIR` or `app.py` not copied | Check `COPY app.py .` and `WORKDIR /app`; run `docker exec flask-api ls /app` |
| `pip install` runs on every build | Copying all files before `pip install` | Copy `requirements.txt` first, then the code |
| `denied: requested access to the resource is denied` on push | Image not tagged with your username, or not logged in | `docker tag ... <user>/flask-api:1.0.0`; `docker login` |
| No logs in `docker logs` | Python output buffering | Set `PYTHONUNBUFFERED=1`; add `--access-logfile -` |
| `Bind for 0.0.0.0:8000 failed: port is already allocated` | Another container or process uses port 8000 | `docker ps`; stop it or use `-p 8001:8000` |
| `/visits` returns 503 in Compose | `REDIS_HOST` wrong or Redis not ready | Set `REDIS_HOST: redis`; use `depends_on` with `service_healthy` |
| Counter resets after restart | No volume, or used `docker compose down -v` | Use the named volume `redis-data:/data` and avoid `-v` |
| `exec format error` when running on a server | Image built for ARM (Apple Silicon) but server is amd64 | Build with `--platform linux/amd64` or multi-platform buildx |
| Permission denied writing a file | App runs as `appuser`, folder owned by root | `COPY --chown` or `RUN mkdir /app/data && chown appuser /app/data` before `USER` |

### Clean up

```bash
# Base project
docker rm -f flask-api
docker rmi flask-api:1.0.0 <your-dockerhub-username>/flask-api:1.0.0 <your-dockerhub-username>/flask-api:latest

# Bonus (Compose): -v also deletes the named volume
docker compose down -v --rmi local

# Remove unused images, networks, and build cache
docker system prune -f
docker builder prune -f

# Log out from Docker Hub on shared machines
docker logout
```

Keep the Docker Hub image if you plan to do Project 10 (Azure Container Instances). Otherwise delete the repository in Docker Hub and revoke the access token.

### Next improvements

- Add tests with `pytest` and run them in a CI pipeline (GitHub Actions) before building the image.
- Build and push from CI with `docker/build-push-action`, tagging images with the Git SHA.
- Scan the image for CVEs with Trivy or Docker Scout and fail the build on critical issues.
- Use a distroless or Chainguard Python base image for an even smaller attack surface.
- Add a readiness endpoint that checks Redis, separate from the liveness `/health`.
- Read Gunicorn settings (workers, timeout) from env vars or a `gunicorn.conf.py`.
- Add structured JSON logging and a `/metrics` endpoint for Prometheus.
- Run it on a cloud service: Azure Container Instances (Project 10), App Service, or Kubernetes.

### How to explain this project in an interview

> "This was a hands-on practice project where I containerized a small Flask REST API with hello and health endpoints. I wrote a Dockerfile on python:3.12-slim, set PYTHONDONTWRITEBYTECODE and PYTHONUNBUFFERED so logs show up immediately, and ran the app with Gunicorn instead of the Flask dev server. The container runs as a non-root system user. I ordered the Dockerfile so requirements.txt is copied and installed before the source code, which keeps the slow pip install layer cached when only code changes. I used a .dockerignore to keep the virtualenv and secrets out of the build context. I pushed versioned tags to Docker Hub and practiced debugging with docker logs, exec, and inspect. As a bonus, I used Docker Compose to add Redis for a visit counter, with a health-check based depends_on, a private network, and a named volume so data survives restarts."

Points that impress interviewers:

- You can explain layer caching and why instruction order matters, not just that it "makes builds faster".
- You use Gunicorn, a non-root user, and exec-form `CMD`, and you know why each matters.
- You know `depends_on` alone does not wait for readiness, and you use a health check condition.
- You tag images with fixed versions for deploys and know the ARM vs amd64 platform trap.

## Interview Questions

<details><summary>Q1. [Basic] What do <code>PYTHONDONTWRITEBYTECODE</code> and <code>PYTHONUNBUFFERED</code> do, and why set them in a container?</summary>

**Answer:**

- `PYTHONDONTWRITEBYTECODE=1`: Python does not write `.pyc` bytecode files. In a container these files add clutter and, with a read-only filesystem, can cause write errors. Startup is only slightly slower.
- `PYTHONUNBUFFERED=1`: stdout and stderr are not buffered. Logs appear in `docker logs` (and in cloud log systems) immediately. Without it, logs can be delayed or lost if the container crashes before the buffer is flushed.

</details>

<details><summary>Q2. [Basic] Why use Gunicorn instead of <code>flask run</code> or <code>app.run()</code> in the container?</summary>

**Answer:**

The Flask built-in server is a development server. It is single-process by default, not tuned for performance, and Flask itself warns not to use it in production.

Gunicorn is a production WSGI server:

- Runs multiple worker processes to use more CPU and handle concurrent requests.
- Restarts workers that crash or hang (`--timeout`).
- Handles `SIGTERM` gracefully, finishing in-flight requests.
- Has proper access logging and configuration options.

In Kubernetes or a reverse-proxy setup you still often put Gunicorn behind Nginx or an ingress for TLS and buffering.

</details>

<details><summary>Q3. [Basic] What is the difference between an image and a container?</summary>

**Answer:**

- An image is a read-only template made of stacked layers plus metadata (env, default command, exposed ports). It is built once and stored in a registry.
- A container is a running (or stopped) instance of an image. Docker adds a thin writable layer on top of the image layers for that container.

You can run many containers from one image. Changes made inside a container (in its writable layer) are lost when the container is removed, unless you use volumes.

</details>

<details><summary>Q4. [Intermediate] Your Docker build reinstalls all Python packages every time you change one line of code. Why, and how do you fix it? <em>(scenario)</em></summary>

**Answer:**

The Dockerfile probably does `COPY . .` before `RUN pip install -r requirements.txt`. Docker computes the cache key for `COPY` from the file contents. Any code change changes the copied files, which invalidates that layer and every layer after it, including `pip install`.

Fix: copy only `requirements.txt` first, install, then copy the rest:

```dockerfile
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
```

Also:

- Add a `.dockerignore` so changes to unrelated files (like `.git` or `.venv`) do not break the cache.
- In CI, use a cache backend (for example `cache-from: type=gha` in `docker/build-push-action`), because each CI runner starts with an empty local cache.
- With BuildKit you can use `RUN --mount=type=cache,target=/root/.cache/pip pip install -r requirements.txt` to reuse the pip download cache across builds without storing it in the image.

</details>

<details><summary>Q5. [Intermediate] Why run the container as a non-root user, and what problems can it cause?</summary>

**Answer:**

Why: by default the process runs as root (uid 0) inside the container. If the app is exploited, root inside the container makes it easier to abuse kernel bugs, mounted volumes, or a misconfigured runtime to reach the host. Non-root follows least privilege. Many platforms (Kubernetes Pod Security Standards "restricted", OpenShift) require it.

Problems it can cause:

- Cannot bind ports below 1024 (use 8000 and map it).
- Cannot write to folders owned by root. Fix with `COPY --chown` or create and `chown` directories before `USER`.
- Bind-mounted host folders may have a different owner uid.

</details>

<details><summary>Q6. [Intermediate] In Docker Compose, the web container starts before Redis is ready and the first requests fail. How do you fix it? <em>(scenario)</em></summary>

**Answer:**

Plain `depends_on: [redis]` only controls start order. It waits for the Redis container to start, not for Redis to accept connections.

Fix:

1. Add a health check to Redis: `test: ["CMD", "redis-cli", "ping"]`.
2. Use the long form in the web service:

```yaml
depends_on:
  redis:
    condition: service_healthy
```

Also make the app resilient: catch connection errors and return `503`, and use retries with backoff. In production (Kubernetes, cloud services) there is no `depends_on`, so the app must handle dependencies that are temporarily down.

</details>

<details><summary>Q7. [Intermediate] What is the difference between a named volume, a bind mount, and the container's writable layer?</summary>

**Answer:**

- Writable layer: data written inside the container with no volume. Lost when the container is removed. Slower for heavy writes.
- Named volume (`redis-data:/data`): managed by Docker under its data directory. Survives container removal. Portable, best for databases and persistent app data. Removed only with `docker volume rm` or `docker compose down -v`.
- Bind mount (`./src:/app`): maps a specific host path. Good for local development (live code reload) or config files. Depends on the host folder structure and permissions.

For Redis in this project, a named volume is the right choice.

</details>

<details><summary>Q8. [Advanced] Your image runs on your Mac but fails on a cloud VM with <code>exec format error</code>. What happened? <em>(scenario)</em></summary>

**Answer:**

The image was built on an Apple Silicon Mac, so it is `linux/arm64`. The cloud VM is `linux/amd64`. The binaries in the image cannot run on a different CPU architecture.

Check:

```bash
docker image inspect <image> --format '{{.Architecture}}'
```

Fix:

- Build for the target platform: `docker build --platform linux/amd64 ...`.
- Or build a multi-platform image with Buildx so the registry stores a manifest list and each host pulls the right variant:

```bash
docker buildx build --platform linux/amd64,linux/arm64 -t <user>/flask-api:1.0.0 --push .
```

- Best practice: build images in CI on the same architecture as production.

</details>

<details><summary>Q9. [Advanced] How would you reduce the size and attack surface of this image further?</summary>

**Answer:**

- Keep `python:3.12-slim` and avoid installing extra OS packages. If you must, use `--no-install-recommends` and remove apt lists in the same `RUN`.
- Use a multi-stage build so compilers and headers stay in the builder stage.
- Consider distroless or hardened Python images. They have no shell or package manager, so there is less for an attacker to use. Trade-off: no `docker exec bash` for debugging.
- Use `.dockerignore`, `PIP_NO_CACHE_DIR=1`, and pinned dependencies.
- Run as non-root and consider a read-only root filesystem (`docker run --read-only --tmpfs /tmp`).
- Scan with Trivy or Docker Scout and rebuild regularly to pick up base image security patches.
- Pin the base image by digest (`python:3.12-slim@sha256:...`) for reproducibility, with Dependabot or Renovate to update it.

</details>

<details><summary>Q10. [Advanced] How do you pass secrets (for example a database password) to this container safely?</summary>

**Answer:**

Never bake secrets into the image (no `ENV PASSWORD=...` in the Dockerfile, no `.env` copied in). Anyone who pulls the image can read every layer with `docker history` or by extracting it.

Better options:

- Runtime env vars from a secure source (`docker run -e` from a CI secret). Simple, but visible in `docker inspect`.
- Docker Compose or Swarm secrets mounted as files under `/run/secrets/`, used with `_FILE` env vars as in the Postgres example.
- In the cloud: Azure Key Vault, AWS Secrets Manager, or Kubernetes Secrets (ideally with an external secrets operator), accessed with managed identity.
- For build-time secrets (like a private package index token), use BuildKit `RUN --mount=type=secret`, which does not store the secret in any layer.

</details>
